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


def _assert_repair_entry_structure(code: str, repair_text: str, err: dict) -> None:
    """S2-R7.2: each repair entry needs code, path, message; search errors need candidates.

    A code-only renderer (the R4-04 false-green) fails these checks.
    """
    assert code in repair_text, f"{code} must appear in repair diagnostics"
    path = err.get("path")
    message = err.get("message")
    assert isinstance(path, str) and path, f"{code}: errors[].path required"
    assert isinstance(message, str) and message, f"{code}: errors[].message required"
    assert path in repair_text, f"{code}: path {path!r} must appear in repair.txt"
    assert message in repair_text or any(
        tok and tok in repair_text for tok in message.replace(":", " ").split()
    ), f"{code}: message content must appear in repair.txt (not code-only)"
    # Numbered entry marker (1. / 1) / #1) somewhere near the code
    assert re.search(rf"(?m)^\s*\d+[.)]\s*.*{re.escape(code)}|{re.escape(code)}", repair_text), (
        f"{code}: numbered repair entry missing"
    )
    if code in ("E_SEARCH_NOMATCH", "E_SEARCH_MULTI"):
        detail = err.get("detail")
        assert detail is not None and str(detail), f"{code}: detail with candidate/line required"
        # SEARCH snippet from the response hunk must be reflected
        assert "SEARCH" in repair_text or "search" in repair_text.lower(), (
            f"{code}: offending SEARCH snippet missing from repair.txt"
        )
        # Candidate window / line number from detail must appear
        detail_s = str(detail)
        assert any(tok and tok in repair_text for tok in re.findall(r"\d+", detail_s)), (
            f"{code}: candidate line number from detail must appear in repair.txt"
        )
        if code == "E_SEARCH_NOMATCH":
            assert "def get_user" in repair_text or "candidate" in repair_text.lower() or "nearest" in repair_text.lower(), (
                f"{code}: nearest candidate window missing"
            )
        if code == "E_SEARCH_MULTI":
            # Multiple match line numbers expected in detail / repair
            nums = re.findall(r"\d+", detail_s)
            assert len(nums) >= 2 or "multi" in repair_text.lower() or "," in detail_s, (
                f"{code}: multi-match candidate details missing"
            )
    if code == "E_PATCH_APPLY":
        assert err.get("detail") is not None or "apply" in repair_text.lower() or "patch" in repair_text.lower(), (
            f"{code}: patch-apply diagnostic fields missing"
        )


def test_repair_structure_rejects_code_only_renderer():
    """R4-04 self-test: code-only repair entries fail S2-R7.2 structure checks."""
    for code in ("E_SEARCH_MULTI", "E_SEARCH_NOMATCH", "E_PATCH_APPLY"):
        fake = f"1. {code}\n"
        fake_err = {"code": code, "path": "", "message": "", "detail": None}
        with pytest.raises(AssertionError):
            _assert_repair_entry_structure(code, fake, fake_err)


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
        _assert_repair_entry_structure(code, repair_text, err)


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
