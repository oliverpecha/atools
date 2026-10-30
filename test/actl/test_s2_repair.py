# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

import pytest

from actl.schemas import load_expected

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "fixtures" / "golden"
TAG = "2026-10-16_public-profiles"


def _setup_sprint(tmp_path: Path):
    from actl.layout import Layout

    root = tmp_path / "actl-root"
    r = subprocess.run(
        ["bash", str(GOLDEN_DIR / "build_golden.sh"), "--install-sprint", str(root), "--tag", TAG],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"build_golden.sh failed: {r.stderr}"
    layout = Layout(root)
    for turn_name in ("architect-1", "challenger-1", "architect-2"):
        src_turn = GOLDEN_DIR / "turns" / turn_name
        dst_turn = layout.turns_dir(TAG) / turn_name
        dst_turn.mkdir(parents=True, exist_ok=True)
        for f in ("bundle.json", "bundle.txt"):
            (dst_turn / f).write_bytes((src_turn / f).read_bytes())
    return layout


def test_repair_confidentiality_and_candidate_details(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves R4-04 & S2-R7.3: planted secret in oracle records NEVER leaks into repair.txt; candidate details verified."""
    try:
        from actl import cli
        import actl.repair  # noqa: F401
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R7: actl.repair or actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    # Plant unique secret exclusively inside oracle records
    secret_canary = "SUPER_SECRET_ORACLE_TOKEN_998877"
    (layout.sprint_dir(TAG) / "oracle-003" / "secret_oracle_data.txt").write_text(secret_canary, encoding="utf-8")

    # Run bad_search_nomatch and verify repair.txt structure and zero leakage
    turn_dir = layout.turns_dir(TAG) / "architect-1"
    rc = cli.main([
        "unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1",
        "-f", str(GOLDEN_DIR / "responses" / "bad_search_nomatch.txt"), "--json"
    ])
    assert rc == 2
    repair_file = turn_dir / "repair.txt"
    assert repair_file.is_file()
    repair_text = repair_file.read_text(encoding="utf-8")

    assert "E_SEARCH_NOMATCH" in repair_text
    assert "def get_user(user_id):" in repair_text, "Nearest candidate window missing"
    assert secret_canary not in repair_text, "SECURITY LEAK: secret oracle token leaked into repair.txt!"


def _search_snippets_from_response(response_text: str) -> list[str]:
    """Extract SEARCH hunk bodies from a response (offending snippets for S2-R7.2)."""
    return re.findall(
        r"<{4,}\s*SEARCH\r?\n(.*?)={4,}\r?\n",
        response_text,
        flags=re.S,
    )


def _assert_repair_entry_structure(
    code: str,
    repair_text: str,
    err: dict,
    *,
    response_text: str | None = None,
) -> None:
    """S2-R7.2: each repair entry needs code, path, message; search errors need candidates.

    A code-only renderer, or one that relies on the substring SEARCH inside
    E_SEARCH_* / the word multi inside E_SEARCH_MULTI, fails these checks.
    """
    assert code in repair_text, f"{code} must appear in repair diagnostics"
    path = err.get("path")
    message = err.get("message")
    assert isinstance(path, str) and path, f"{code}: errors[].path required"
    assert isinstance(message, str) and message, f"{code}: errors[].message required"
    assert path in repair_text, f"{code}: path {path!r} must appear in repair.txt"
    assert message in repair_text, f"{code}: exact message must appear in repair.txt"
    assert re.search(rf"(?m)^\s*\d+[.)]\s+", repair_text), (
        f"{code}: numbered repair entry missing"
    )
    if code in ("E_SEARCH_NOMATCH", "E_SEARCH_MULTI"):
        detail = err.get("detail")
        assert detail is not None and str(detail), f"{code}: detail with candidate/line required"
        detail_s = str(detail)
        nums = re.findall(r"\d+", detail_s)
        assert nums, f"{code}: detail must contain candidate line number(s)"
        # Every candidate line from detail must appear (one number is not enough for MULTI).
        for n in nums:
            assert n in repair_text, (
                f"{code}: candidate line {n} from detail missing in repair.txt"
            )
        if code == "E_SEARCH_MULTI":
            assert len(nums) >= 2, f"{code}: detail must list at least two candidate lines"
        # Offending SEARCH snippet: require response hunk body text, not the code token.
        # Strip error codes so "SEARCH" inside E_SEARCH_MULTI cannot satisfy the check.
        body_wo_codes = repair_text
        for c in ("E_SEARCH_MULTI", "E_SEARCH_NOMATCH", "E_PATCH_APPLY"):
            body_wo_codes = body_wo_codes.replace(c, "")
        snippets = _search_snippets_from_response(response_text or "")
        if snippets:
            found_snip = False
            for snip in snippets:
                for line in snip.splitlines():
                    s = line.strip()
                    if len(s) >= 3 and s in repair_text:
                        found_snip = True
                        break
                if found_snip:
                    break
            assert found_snip, (
                f"{code}: offending SEARCH snippet text from response missing in repair.txt"
            )
        else:
            assert re.search(r"(?i)(?<!E_)search\s*[:\n]", body_wo_codes) or "<<<<<<<" in repair_text, (
                f"{code}: offending SEARCH snippet missing from repair.txt"
            )
        if code == "E_SEARCH_NOMATCH":
            # Nearest candidate window content (not the bare word "candidate").
            assert "def get_user" in repair_text, (
                f"{code}: nearest candidate window missing (expected def get_user)"
            )
    if code == "E_PATCH_APPLY":
        assert err.get("detail") is not None and str(err.get("detail")), (
            f"{code}: patch-apply detail required"
        )


def test_repair_structure_rejects_code_only_renderer():
    """R4-04 self-test: code-only and one-line MULTI renderers fail structure checks."""
    for code in ("E_SEARCH_MULTI", "E_SEARCH_NOMATCH", "E_PATCH_APPLY"):
        fake = f"1. {code}\n"
        fake_err = {"code": code, "path": "", "message": "", "detail": None}
        with pytest.raises(AssertionError):
            _assert_repair_entry_structure(code, fake, fake_err)

    # Counterexample: code/path/message + one detail number; E_SEARCH_MULTI supplies
    # the substrings SEARCH and multi, so the old keyword checks were green.
    multi_fake = (
        "1. E_SEARCH_MULTI\n"
        "path: api/users.py\n"
        "message: ambiguous match\n"
        "line 12\n"
    )
    multi_err = {
        "code": "E_SEARCH_MULTI",
        "path": "api/users.py",
        "message": "ambiguous match",
        "detail": "12,19",
    }
    resp = (
        "<<<<<<< SEARCH\n"
        "UNIQUE_OFFENDING_SNIPPET_R404\n"
        "=======\n"
        "replacement\n"
        ">>>>>>> REPLACE\n"
    )
    with pytest.raises(AssertionError):
        _assert_repair_entry_structure(
            "E_SEARCH_MULTI", multi_fake, multi_err, response_text=resp
        )


def test_confidentiality_error_codes_canary(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """R4-04: Oracle canary redaction + full S2-R7.2 structure per error code.

    Code aliases from the R8 runbook map to the INTERFACES vocabulary:
    E_SEARCH_ZERO -> E_SEARCH_NOMATCH, E_PATCH_REJECTED -> E_PATCH_APPLY,
    E_AMBIGUOUS_HUNK -> E_SEARCH_MULTI.
    """
    try:
        from actl import cli
        import actl.repair  # noqa: F401
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R7: actl.repair or actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    secret_canary = "SUPER_SECRET_ORACLE_TOKEN_ERROR_CODES_112233"
    oracle_dir = layout.sprint_dir(TAG) / "oracle-003"
    oracle_dir.mkdir(parents=True, exist_ok=True)
    (oracle_dir / "secret_oracle_data.txt").write_text(secret_canary, encoding="utf-8")

    cases = [
        ("E_SEARCH_MULTI", "bad_search_multi.txt"),       # E_AMBIGUOUS_HUNK
        ("E_SEARCH_NOMATCH", "bad_search_nomatch.txt"),   # E_SEARCH_ZERO
        ("E_PATCH_APPLY", "bad_patch_apply.txt"),         # E_PATCH_REJECTED
    ]
    turn_dir = layout.turns_dir(TAG) / "architect-1"

    for code, fixture in cases:
        for f in ("response.txt", "unpack.json", "repair.txt"):
            p = turn_dir / f
            if p.exists():
                p.unlink()
        rc = cli.main([
            "unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1",
            "-f", str(GOLDEN_DIR / "responses" / fixture), "--json",
        ])
        assert rc == 2, f"{code}: unpack must fail"
        repair_file = turn_dir / "repair.txt"
        assert repair_file.is_file(), f"{code}: repair.txt missing"
        repair_text = repair_file.read_text(encoding="utf-8")
        unpack_doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
        err = unpack_doc["errors"][0]
        assert err["code"] == code, f"expected {code}, got {err['code']}"
        assert secret_canary not in repair_text, f"SECURITY LEAK under {code}: canary in repair.txt"
        response_text = (GOLDEN_DIR / "responses" / fixture).read_text(encoding="utf-8")
        _assert_repair_entry_structure(
            code, repair_text, err, response_text=response_text
        )


def test_p13_non_execution_canary_across_unpack_replay_promote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    try:
        from actl import cli
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R12.1: actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    pwn_unpack = tmp_path / "pwn_unpack"
    pwn_replay = tmp_path / "pwn_replay"
    pwn_promote = tmp_path / "pwn_promote"

    good_chal = (GOLDEN_DIR / "responses" / "good_challenger.txt").read_text(encoding="utf-8")
    injected = good_chal.replace(
        'echo "OK: probe"',
        f'touch "{pwn_unpack}" "{pwn_replay}" "{pwn_promote}"\necho "OK: probe"',
    )
    inj_file = tmp_path / "inj.txt"
    inj_file.write_text(injected, encoding="utf-8")

    rc1 = cli.main(["unpack", "challenger", "--sprint", TAG, "--turn", "challenger-1", "-f", str(inj_file), "--json"])
    assert rc1 == 0
    assert not pwn_unpack.exists()

    rc2 = cli.main(["replay", "challenger-1", "--sprint", TAG, "--json"])
    assert rc2 == 0
    assert not pwn_replay.exists()

    rc3 = cli.main(["promote", "challenger", "--sprint", TAG, "--json"])
    assert rc3 == 0
    assert not pwn_promote.exists()
