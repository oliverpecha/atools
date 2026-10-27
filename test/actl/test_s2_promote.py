from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "fixtures" / "golden"


def _create_fresh_sprint(tmp_path: Path):
    from actl.layout import Layout
    from actl.sprint import create_sprint, init_target

    root = tmp_path / "actl-root"
    target_src = tmp_path / "target-src"
    subprocess.run(["bash", str(GOLDEN_DIR / "build_golden.sh"), str(target_src)], check=True)
    layout = Layout(root)
    init_target(layout, str(target_src))
    info = create_sprint(layout, "promote-test")
    return layout, info["sprint_tag"]


def test_promote_role_seven_keys_dedup_and_staging_modes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    try:
        from actl import cli, schemas
        import actl.cmd_promote  # noqa: F401
        from actl.promote import promote_role
        from actl.seq import read_state
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R9: actl.promote or actl.cmd_promote missing: {e}")

    monkeypatch.setenv("ACTL_TODAY", "2026-10-16")
    layout, tag = _create_fresh_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    arch_out = layout.outbox(tag, "architect")
    spec_bytes = (GOLDEN_DIR / "sprint" / "spec-001.md").read_bytes()
    key_bytes = (GOLDEN_DIR / "sprint" / "solution_key.patch").read_bytes()
    (arch_out / "spec-draft.md").write_bytes(spec_bytes)
    (arch_out / "solution_key.patch").write_bytes(key_bytes)

    res1 = promote_role(layout, tag, "architect")
    expected_keys = {
        "sprint_tag",
        "role",
        "promoted",
        "staged_to",
        "active_spec",
        "active_solution_key",
        "active_oracle_draft",
    }
    assert set(res1.keys()) == expected_keys, f"Expected 7 keys (D-43), got {set(res1.keys())}"
    assert res1["active_spec"] == "spec-001.md"
    assert res1["active_solution_key"] == "solution_key-002.patch"
    assert res1["active_oracle_draft"] is None
    assert res1["staged_to"] == str(layout.inbox(tag, "challenger"))

    sdir = layout.sprint_dir(tag)
    assert (sdir / "spec-001.md").read_bytes() == spec_bytes
    assert (sdir / "solution_key-002.patch").read_bytes() == key_bytes
    spec_meta = json.loads((sdir / "spec-001.md.meta.json").read_text(encoding="utf-8"))
    key_meta = json.loads((sdir / "solution_key-002.patch.meta.json").read_text(encoding="utf-8"))
    assert schemas.validate("meta", spec_meta) == []
    assert schemas.validate("meta", key_meta) == []
    assert spec_meta["parent"] is None
    assert key_meta["parent"] == "spec-001.md"

    chal_in = layout.inbox(tag, "challenger")
    for staged_name in ("spec-001.md", "solution_key-002.patch"):
        sp = chal_in / staged_name
        assert sp.is_file(), f"Staged file {staged_name} missing"
        assert stat.S_IMODE(os.lstat(sp).st_mode) == 0o440

    seq_before = read_state(layout, tag)["seq"]
    res_idem = promote_role(layout, tag, "architect")
    seq_after = read_state(layout, tag)["seq"]
    assert seq_after == seq_before == 2, f"Expected idempotent seq=2, got {seq_after}"
    assert res_idem["active_spec"] == "spec-001.md"
    assert res_idem["active_solution_key"] == "solution_key-002.patch"

    (arch_out / "spec-draft.md").write_bytes(spec_bytes + b"\n# Revised R4\n")
    res_new_parent = promote_role(layout, tag, "architect")
    assert res_new_parent["active_spec"] == "spec-003.md"
    assert res_new_parent["active_solution_key"] == "solution_key-004.patch"

    chal_out_draft = layout.outbox(tag, "challenger") / "oracle-draft"
    shutil.copytree(GOLDEN_DIR / "sprint" / "oracle", chal_out_draft)
    capsys.readouterr()
    rc_chal = cli.main(["promote", "challenger", "--sprint", tag, "--json"])
    cap_chal = capsys.readouterr()
    assert rc_chal == 0
    chal_doc = json.loads(cap_chal.out)
    assert set(chal_doc.keys()) == expected_keys
    assert chal_doc["active_oracle_draft"] == "oracle-draft-005"
    expected_staged = str(sdir / "oracle-draft-005")
    assert chal_doc["staged_to"] == expected_staged

    promoted_draft = Path(expected_staged)
    assert promoted_draft.is_dir()
    assert stat.S_IMODE(os.lstat(promoted_draft / "probe.sh").st_mode) == 0o550
    assert stat.S_IMODE(os.lstat(promoted_draft / "scope.txt").st_mode) == 0o440
    draft_meta = json.loads((sdir / "oracle-draft-005.meta.json").read_text(encoding="utf-8"))
    assert schemas.validate("meta", draft_meta) == []
    assert draft_meta["parent"] == "spec-003.md"

def test_promote_policy_merge_preserves_frozen_fields(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves R4-07 & S2-R9.3: promotion merges policy fields but preserves frozen sprint_tag, base_sha, repo, repo_test_cmd."""
    from actl.promote import promote_role
    from actl.sprint import load_sprint_toml
    monkeypatch.setenv("ACTL_TODAY", "2026-10-16")
    layout, tag = _create_fresh_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    arch_out = layout.outbox(tag, "architect")
    (arch_out / "spec-draft.md").write_text("# Spec\nR1: ok\n", encoding="utf-8")
    (arch_out / "solution_key.patch").write_text("diff\n", encoding="utf-8")
    # Propose new policy values while trying to tamper with frozen base_sha
    (arch_out / "sprint-proposal.toml").write_text('live_run="none"\nmax_epochs=99\nbase_sha="0000000000000000000000000000000000000000"\n', encoding="utf-8")

    promote_role(layout, tag, "architect")
    merged = load_sprint_toml(layout, tag)
    assert merged["max_epochs"] == 99, "Proposable policy field max_epochs was not merged"
    assert merged["base_sha"] != "0000000000000000000000000000000000000000", "Frozen base_sha must never be overwritten by promotion"
    assert merged["sprint_tag"] == tag
