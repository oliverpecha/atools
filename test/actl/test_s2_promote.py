
# test/actl/test_s2_promote.py - P-S2-12: actl promote command, 7 keys, deduplication, and read-only staging (S2-R9, D-43)

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

from **future** import annotations

import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(**file**).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "fixtures" / "golden"

def _create_fresh_sprint(tmp_path: Path):
from actl.layout import Layout
from actl.sprint import create_sprint, init_target

```
root = tmp_path / "actl-root"
target_src = tmp_path / "target-src"
subprocess.run(["bash", str(GOLDEN_DIR / "build_golden.sh"), str(target_src)], check=True)
layout = Layout(root)
init_target(layout, str(target_src))
info = create_sprint(layout, "promote-test")
return layout, info["sprint_tag"]

```

def test_promote_role_seven_keys_dedup_and_staging_modes(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
"""Proves P-S2-12 & D-43: promote_role returns 7 keys, writes .meta.json, deduplicates by (kind, parent, sha256), and stages 0o440/0o550."""
try:
from actl import cli, schemas
import actl.cmd_promote  # noqa: F401
from actl.promote import promote_role
from actl.seq import read_state
except ImportError as e:
pytest.fail(f"FAIL: S2-R9: actl.promote or actl.cmd_promote missing: {e}")

```
monkeypatch.setenv("ACTL_TODAY", "2026-10-16")
layout, tag = _create_fresh_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))

# Populate architect outbox
arch_out = layout.outbox(tag, "architect")
spec_bytes = (GOLDEN_DIR / "sprint" / "spec-001.md").read_bytes()
key_bytes = (GOLDEN_DIR / "sprint" / "solution_key.patch").read_bytes()
(arch_out / "spec-draft.md").write_bytes(spec_bytes)
(arch_out / "solution_key.patch").write_bytes(key_bytes)

# 1. First architect promotion allocates seq 1 (spec-001.md) and seq 2 (solution_key-002.patch)
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
assert set(res1.keys()) == expected_keys, f"Expected exact 7 keys (D-43), got {set(res1.keys())}"
assert res1["active_spec"] == "spec-001.md"
assert res1["active_solution_key"] == "solution_key-002.patch"
assert res1["active_oracle_draft"] is None
assert res1["staged_to"] == str(layout.inbox(tag, "challenger"))

# Verify records artifacts & sidecars validate against schemas/meta.json
sdir = layout.sprint_dir(tag)
assert (sdir / "spec-001.md").read_bytes() == spec_bytes
assert (sdir / "solution_key-002.patch").read_bytes() == key_bytes
spec_meta = json.loads((sdir / "spec-001.md.meta.json").read_text(encoding="utf-8"))
key_meta = json.loads((sdir / "solution_key-002.patch.meta.json").read_text(encoding="utf-8"))
assert schemas.validate("meta", spec_meta) == []
assert schemas.validate("meta", key_meta) == []
assert spec_meta["parent"] is None
assert key_meta["parent"] == "spec-001.md"

# Verify challenger inbox staging has read-only 0o440 modes
chal_in = layout.inbox(tag, "challenger")
for staged_name in ("spec-001.md", "solution_key-002.patch"):
    sp = chal_in / staged_name
    assert sp.is_file(), f"Staged file {staged_name} missing in challenger inbox"
    assert stat.S_IMODE(os.lstat(sp).st_mode) == 0o440

# 2. Idempotence: promoting identical architect outbox content allocates NO new seq
seq_before = read_state(layout, tag)["seq"]
res_idem = promote_role(layout, tag, "architect")
seq_after = read_state(layout, tag)["seq"]
assert seq_after == seq_before == 2, f"Expected idempotent seq=2, got {seq_after}"
assert res_idem["active_spec"] == "spec-001.md"
assert res_idem["active_solution_key"] == "solution_key-002.patch"

# 3. Parent-sensitive deduplication: if spec changes (spec-003.md), identical solution_key bytes get a NEW seq (solution_key-004.patch) because parent changed!
(arch_out / "spec-draft.md").write_bytes(spec_bytes + b"\n# Revised R4\n")
res_new_parent = promote_role(layout, tag, "architect")
assert res_new_parent["active_spec"] == "spec-003.md"
assert res_new_parent["active_solution_key"] == "solution_key-004.patch", (
    "Identical solution_key under a new active_spec parent must allocate a new seq"
)

# 4. Challenger promotion via CLI --json: staged_to is records/target-repo/<tag>/oracle-draft-005 (D-43)
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

```

