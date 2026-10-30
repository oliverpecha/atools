# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
from pathlib import Path
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
    assert "__target-repo__2026-10-16_public-profiles__architect-1__architect-intake" in drawers[0].name
    assert (drawers[0] / "bundle.txt").is_file()

def test_s2_r34_proposal_filename_contract():
    """R4-01: Both sprint-proposal.toml and sprint.toml accepted; others rejected."""
    from actl import turns
    for v in ("sprint-proposal.toml", "sprint.toml"):
        assert turns.is_valid_proposal_filename(v) is True
    for inv in ("sprint_proposal.toml", "proposal.toml", "sprint.yaml", "sprint.json"):
        assert turns.is_valid_proposal_filename(inv) is False


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


def test_s2_r34_alias_only_and_conflict_policy_outputs():
    """R4-01: alias-only OK; both omitted / both present are not.

    Self-test: a checker that still required the literal name
    sprint-proposal.toml would reject the alias-only set below.
    """
    alias_only = {"sprint.toml", "solution_key.patch", "spec-draft.md"}
    canonical = {"sprint-proposal.toml", "solution_key.patch", "spec-draft.md"}
    omitted = {"solution_key.patch", "spec-draft.md"}
    conflicting = {
        "sprint.toml",
        "sprint-proposal.toml",
        "solution_key.patch",
        "spec-draft.md",
    }

    # Old contradictory required-output clause (literal sprint-proposal.toml only)
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

    # Implementation helper must agree with the normative oracle when present.
    try:
        from actl import turns
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R3.4: actl.turns missing: {e}")
    check = getattr(turns, "architect_intake_required_status", None)
    assert callable(check), (
        "FAIL: S2-R3.4: turns.architect_intake_required_status missing; "
        "alias-only / omit-both / conflict cases are unenforced"
    )
    assert check(alias_only) is None
    assert check(canonical) is None
    assert check(omitted) == "E_MISSING_REQUIRED"
    assert check(conflicting) == "E_DUPLICATE"


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

