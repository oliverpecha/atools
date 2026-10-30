# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
import re
import stat
import subprocess

import pytest

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
    return Layout(root)


def test_turns_ledger_allocation_and_resolution(tmp_path: Path):
    try:
        from actl.turns import allocate_turn, latest_turn, resolve_turn
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R1.2: actl.turns could not be imported: {e}")

    layout = _setup_sprint(tmp_path)

    assert latest_turn(layout, TAG, "architect") is None
    assert latest_turn(layout, TAG, "challenger") is None
    assert latest_turn(layout, TAG, "curator") is None

    n1, p1 = allocate_turn(layout, TAG, "architect")
    assert n1 == 1 and p1 == layout.turns_dir(TAG) / "architect-1"
    assert p1.is_dir()
    assert stat.S_IMODE(os.lstat(p1).st_mode) == 0o755

    n2, p2 = allocate_turn(layout, TAG, "architect")
    assert n2 == 2 and p2 == layout.turns_dir(TAG) / "architect-2"

    nc1, pc1 = allocate_turn(layout, TAG, "challenger")
    assert nc1 == 1 and pc1 == layout.turns_dir(TAG) / "challenger-1"

    assert latest_turn(layout, TAG, "architect") == (2, p2)
    assert latest_turn(layout, TAG, "challenger") == (1, pc1)
    assert resolve_turn(layout, TAG, "architect-1") == p1
    assert resolve_turn(layout, TAG, "architect-2") == p2
    assert resolve_turn(layout, TAG, "challenger-1") == pc1

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda _: allocate_turn(layout, TAG, "architect"), range(8)))
    nums = sorted(r[0] for r in results)
    assert nums == list(range(3, 11)), f"Concurrent allocate_turn produced {nums}"

    for bad_role in ("implementer", "invalid", "", "../architect"):
        with pytest.raises(ValueError):
            allocate_turn(layout, TAG, bad_role)
        with pytest.raises(ValueError):
            latest_turn(layout, TAG, bad_role)

    for bad_id in ("architect-0", "architect-01", "implementer-1", "architect", "../architect-1", "architect--1"):
        with pytest.raises(ValueError):
            resolve_turn(layout, TAG, bad_id)

    with pytest.raises(FileNotFoundError):
        resolve_turn(layout, TAG, "architect-99")


def test_courier_drawer_creation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves R4-07 & S2-R1.5: ACTL_COURIER_DIR creates outgoing drawer with bundle.txt."""
    try:
        from actl import cli
        import actl.bundle  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R1.5: actl.bundle missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    courier_dir = tmp_path / "courier_out"
    courier_dir.mkdir()
    monkeypatch.setenv("ACTL_COURIER_DIR", str(courier_dir))

    rc = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--json"])
    assert rc == 0
    drawers = list(courier_dir.iterdir())
    assert len(drawers) == 1
    # S2-R1.5: stamp is UTC YYYYMMDDTHHMMZ; substring checks accept BADSTAMP__.
    assert re.fullmatch(
        r"\d{8}T\d{4}Z__target-repo__2026-10-16_public-profiles__architect-1__architect-intake",
        drawers[0].name,
    ), f"courier drawer name must use UTC YYYYMMDDTHHMMZ stamp, got {drawers[0].name!r}"
    assert (drawers[0] / "bundle.txt").is_file()


def test_courier_stamp_rejects_bad_prefix():
    """R4-07 self-test: arbitrary prefix must not satisfy the stamp fullmatch."""
    bad = "BADSTAMP__target-repo__2026-10-16_public-profiles__architect-1__architect-intake"
    assert "__target-repo__2026-10-16_public-profiles__architect-1__architect-intake" in bad
    assert re.fullmatch(
        r"\d{8}T\d{4}Z__target-repo__2026-10-16_public-profiles__architect-1__architect-intake",
        bad,
    ) is None


_SPRINT_PROPOSAL_BODY = (
    'live_run = "none"\n'
    'approval_live_run = "architect"\n'
    'solution_key_exposure = "full"\n'
    "min_attempts_before_block = 2\n"
    "max_epochs = 3\n"
    "\n"
    "[max_attempts]\n"
    "oracle = 3\n"
    "implementer = 2\n"
    "live = 2\n"
    "curator = 2\n"
    "\n"
    "[hard_cap.implementer]\n"
    'wall_clock = "45m"\n'
    "turns = 60\n"
)

def test_s2_r34_proposal_filename_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """R4-01: Both sprint-proposal.toml and sprint.toml accepted; others rejected.

    Drives unpack once with an invalid policy filename so a helper-only
    is_valid_proposal_filename stub cannot be the sole coverage (standing i).
    """
    import json

    try:
        from actl import turns
        from actl import cli
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R3.4: actl.turns/unpack missing: {e}")
    for v in ("sprint-proposal.toml", "sprint.toml"):
        assert turns.is_valid_proposal_filename(v) is True
    for inv in ("sprint_proposal.toml", "proposal.toml", "sprint.yaml", "sprint.json"):
        assert turns.is_valid_proposal_filename(inv) is False

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    turn_dir = layout.turns_dir(TAG) / "architect-1"
    key_body = (GOLDEN_DIR / "sprint" / "solution_key.patch").read_text(encoding="utf-8")
    payload = (
        '<<<FILE path="sprint_proposal.toml">>>\n'
        f"{_SPRINT_PROPOSAL_BODY}"
        "<<<END_FILE>>>\n"
        f'<<<FILE path="solution_key.patch">>>\n{key_body}<<<END_FILE>>>\n'
        '<<<FILE path="spec-draft.md">>>\n# draft\n<<<END_FILE>>>\n'
        '<<<END_RESPONSE bundle="1f13e141">>>\n'
    )
    inp = tmp_path / "r34_bad_name.txt"
    inp.write_text(payload, encoding="utf-8")
    rc = cli.main([
        "unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1",
        "-f", str(inp), "--json",
    ])
    assert rc == 2
    doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
    # Invalid policy name is not an accepted alias; unpack must not succeed.
    assert doc.get("ok") is False
    assert doc["errors"], "expected at least one unpack error for invalid policy filename"


def _architect_intake_required_status(output_names: set[str]) -> str | None:
    """Normative S2-R3.4/D-51 policy-output rule used as the R4-01 oracle.

    Returns None when required outputs are satisfied, otherwise the expected
    error code. Either policy alias alone counts; both together conflict.
    """
    has_key = "solution_key.patch" in output_names
    has_spec = "spec-draft.md" in output_names
    has_prop = "sprint-proposal.toml" in output_names
    has_alias = "sprint.toml" in output_names
    if has_prop and has_alias:
        return "E_DUPLICATE"
    if not has_prop and not has_alias:
        return "E_MISSING_REQUIRED"
    if not has_key or not has_spec:
        return "E_MISSING_REQUIRED"
    return None



def test_s2_r34_alias_only_and_conflict_policy_outputs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """R4-01: unpack parser accepts alias-only; omit-both / both-present fail.

    Drives actl unpack (not only a helper). Self-test: a literal-name-only
    required clause rejects alias-only; the unpack path must not.
    """
    import json

    alias_only = {"sprint.toml", "solution_key.patch", "spec-draft.md"}
    canonical = {"sprint-proposal.toml", "solution_key.patch", "spec-draft.md"}
    omitted = {"solution_key.patch", "spec-draft.md"}
    conflicting = {
        "sprint.toml",
        "sprint-proposal.toml",
        "solution_key.patch",
        "spec-draft.md",
    }

    def _old_literal_required(names: set[str]) -> str | None:
        if "sprint-proposal.toml" not in names:
            return "E_MISSING_REQUIRED"
        if "solution_key.patch" not in names or "spec-draft.md" not in names:
            return "E_MISSING_REQUIRED"
        return None

    assert _old_literal_required(alias_only) == "E_MISSING_REQUIRED", (
        "red-on-old: alias-only must fail the pre-fix literal required clause"
    )
    assert _architect_intake_required_status(alias_only) is None
    assert _architect_intake_required_status(canonical) is None
    assert _architect_intake_required_status(omitted) == "E_MISSING_REQUIRED"
    assert _architect_intake_required_status(conflicting) == "E_DUPLICATE"

    try:
        from actl import cli
        import actl.unpack  # noqa: F401
        import actl.turns  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R3.4: actl.unpack/turns missing: {e}")

    check = getattr(__import__("actl.turns", fromlist=["*"]), "architect_intake_required_status", None)
    if callable(check):
        assert check(alias_only) is None
        assert check(canonical) is None
        assert check(omitted) == "E_MISSING_REQUIRED"
        assert check(conflicting) == "E_DUPLICATE"

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    turn_dir = layout.turns_dir(TAG) / "architect-1"
    key_body = (GOLDEN_DIR / "sprint" / "solution_key.patch").read_text(encoding="utf-8")
    spec_body = "# R4-01 alias policy draft\n"

    def _file_block(path: str, body: str) -> str:
        return f'<<<FILE path="{path}">>>\n{body}<<<END_FILE>>>\n'

    def _run_unpack(names: set[str]) -> tuple[int, dict]:
        for f in ("response.txt", "unpack.json", "repair.txt"):
            p = turn_dir / f
            if p.exists():
                p.unlink()
        parts: list[str] = []
        for name in sorted(names):
            if name in ("sprint.toml", "sprint-proposal.toml"):
                parts.append(_file_block(name, _SPRINT_PROPOSAL_BODY))
            elif name == "solution_key.patch":
                parts.append(_file_block(name, key_body))
            elif name == "spec-draft.md":
                parts.append(_file_block(name, spec_body))
        parts.append('<<<END_RESPONSE bundle="1f13e141">>>\n')
        payload = "".join(parts)
        inp = tmp_path / "r401_in.txt"
        inp.write_text(payload, encoding="utf-8")
        rc = cli.main([
            "unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1",
            "-f", str(inp), "--json",
        ])
        doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
        return rc, doc

    # Alias-only through the real unpack parser (not a helper-only check).
    rc_alias, doc_alias = _run_unpack(alias_only)
    assert rc_alias == 0, (
        f"alias-only sprint.toml+key+spec-draft must unpack ok, got rc={rc_alias} "
        f"errors={doc_alias.get('errors')}"
    )
    assert doc_alias.get("ok") is True
    err_codes_alias = [e["code"] for e in doc_alias.get("errors") or []]
    assert "E_MISSING_REQUIRED" not in err_codes_alias

    rc_omit, doc_omit = _run_unpack(omitted)
    assert rc_omit == 2
    assert doc_omit["errors"][0]["code"] == "E_MISSING_REQUIRED"

    rc_both, doc_both = _run_unpack(conflicting)
    assert rc_both == 2
    assert doc_both["errors"][0]["code"] == "E_DUPLICATE"


def test_s2_r34_spec_text_either_alias_satisfies_required():
    """R4-01: normative S2-R3.4 text must not require only sprint-proposal.toml."""
    text = (REPO_ROOT / "docs" / "plan" / "spec-S2.md").read_text(encoding="utf-8")
    # Pin the architect-intake required-outputs sentence.
    marker = "`architect-intake`: allowed outputs"
    start = text.index(marker)
    chunk = text[start : start + 700]
    assert "either name alone satisfies the single policy-output requirement" in chunk
    assert "E_MISSING_REQUIRED" in chunk and "E_DUPLICATE" in chunk
    # Must not still say Required outputs: ... `sprint-proposal.toml`, and ...
    # without the either-alias satisfaction clause.
    assert "Required outputs: `solution_key.patch`, `sprint-proposal.toml`, and" not in chunk

    # Selector gap self-test: P-S2-01 -k must collect the matrix-named r34 cases.
    import subprocess
    r = subprocess.run(
        [
            "python3", "-m", "pytest",
            str(REPO_ROOT / "test/actl/test_s2_turns.py"),
            str(REPO_ROOT / "test/actl/test_s2_unpack.py"),
            "-k", "test_turns or test_courier or test_p01 or test_s2_r34",
            "--collect-only", "-q",
        ],
        capture_output=True, text=True, cwd=str(REPO_ROOT),
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "src")},
    )
    collected = r.stdout + r.stderr
    for name in (
        "test_s2_r34_alias_only_and_conflict_policy_outputs",
        "test_s2_r34_proposal_filename_contract",
        "test_courier_drawer_creation",
        "test_p01_good_architect_intake_unpack_and_proof_preview",
    ):
        assert name in collected, f"P-S2-01 filter must collect {name}"

