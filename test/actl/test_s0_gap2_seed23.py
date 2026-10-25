import json
import os
import subprocess
import sys
import types
import argparse
from pathlib import Path
import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for p in (REPO / "src", HERE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from actl.layout import Layout
from actl import seq, schemas, sprint, cli, hashing

TAG = "2026-10-16_gap2-s23"

def _lay(p):
    l = Layout(p / "root")
    l.ensure_sprint_tree(TAG)
    return l

def _init_state(l):
    st = {
        "run_id": "run-123456789012",
        "sprint_tag": TAG,
        "seq": 1,
        "epoch": 1,
        "status": "draft",
        "active_stage": None,
        "active_spec": None,
        "active_solution_key": None,
        "active_oracle_draft": None,
        "active_oracle": None,
        "active_contract": None,
        "attempts": {"curator": 0, "implementer": 0, "live": 0, "oracle": 0},
        "closures_submitted": 0,
        "hard_caps_tripped": 0,
        "grants": {"curator": 0, "implementer": 0, "live": 0, "oracle": 0},
        "tmux_sessions": ["s1"],
    }
    l.state_file(TAG).write_text(json.dumps(st))

# 1. Kill hashing.py:71 (allow_nan=False -> True)
def test_hashing_nan_inf():
    for v in (float("nan"), float("inf")):
        with pytest.raises(ValueError):
            hashing.canonical_json({"v": v})

# 2. Kill seq.py:35 (if not locks: -> if locks:)
def test_seq_clear_locks():
    seq._tls.locks = None
    seq._clear_locks_after_fork()
    assert seq._tls.locks == {}

# 3. Kill seq.py:144 (and -> or in non-attempts/grants dict overwrite)
def test_seq_updates_no_merge(tmp_path):
    l = _lay(tmp_path)
    _init_state(l)
    # 1. attempts dict merge must work properly
    with pytest.raises(ValueError, match="Invalid state update"):
        seq.update_state(l, TAG, {"attempts": 123})
    # 2. non-attempts/grants list must overwrite completely, not attempt dict merge
    res = seq.update_state(l, TAG, {"tmux_sessions": ["s2"]})
    assert res["tmux_sessions"] == ["s2"]

# 4. Kill seq.py:169 (ValueError highwater fallback 0 -> 1)
def test_seq_corrupt_hw(tmp_path):
    l = _lay(tmp_path)
    l.state_file(TAG).write_text(json.dumps({"seq": 0, "status": "draft"}))
    (l.runs_dir(TAG) / "seq.highwater").write_text("bad\n")
    assert seq.reserve(l, TAG, "ev") == 1

# 5. Kill seq.py:310 (or -> and in contract epoch validation)
def test_seq_contract_epoch(tmp_path):
    l = _lay(tmp_path)
    (l.sprint_dir(TAG) / "spec-001.md").write_text("s")
    for bad in (0, True):
        (l.sprint_dir(TAG) / "contract-002.json").write_text(json.dumps({"epoch": bad}))
        with pytest.raises(ValueError, match="Invalid contract epoch"):
            seq.reconstruct(l, TAG)

# 6. Kill seq.py:391 (== -> != for active_contract update)
def test_seq_active_contract(tmp_path):
    l = _lay(tmp_path)
    (l.sprint_dir(TAG) / "spec-001.md").write_text("s")
    # Artifact with kind != "contract" must NOT set active_contract
    (l.runs_dir(TAG) / "verification-002.json").write_text(json.dumps({"stage": "live", "hard_cap": True}))
    (l.runs_dir(TAG) / "verification-002.meta.json").write_text(json.dumps({"kind": "notes", "seq": 2}))
    seq.reconstruct(l, TAG)
    state = seq.read_state(l, TAG)
    assert state.get("active_contract") is None

# 7. Kill schemas.py:142 (as_schema=True -> False for properties subschema)
def test_schemas_supported_as_schema():
    with pytest.raises(ValueError, match="Unsupported schema keyword"):
        schemas._check_supported({"properties": [{"$unsupported": 1}]}, where="test", as_schema=True)

# 8. Kill schemas.py:214 (return False -> True in _type_ok)
def test_schemas_type_ok_unknown():
    assert schemas._type_ok("val", "unknown_type") is False
    assert schemas._type_ok(123, "unknown_type") is False

# 9. Kill schemas.py:354 (matches == 0 -> matches == 1 in oneOf error message)
def test_schemas_oneof_zero_msg():
    errors = []
    schemas._validate_schema(
        instance="toolong",
        schema={"oneOf": [{"type": "string", "maxLength": 2}, {"type": "integer"}]},
        ptr="",
        errors=errors,
        current_doc={},
        doc_name="test",
    )
    assert len(errors) == 1
    assert "oneOf: expected 1 match, got 0 (" in errors[0]["message"]

# 10. Kill sprint.py:211 (and -> or in default branch symbolic-ref)
def test_sprint_default_branch(tmp_path, monkeypatch):
    l = Layout(tmp_path / "root")
    (l.target_repo / ".git").mkdir(parents=True)
    orig_run = subprocess.run
    def mock_run(cmd, *a, **kw):
        if "symbolic-ref" in cmd:
            return subprocess.CompletedProcess(cmd, 1, stdout="nonexistent-ref\n", stderr="")
        if "rev-parse" in cmd and "refs/heads/main" in cmd:
            return subprocess.CompletedProcess(cmd, 0, stdout="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef\n", stderr="")
        if "rev-parse" in cmd and "nonexistent-ref" in cmd:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="fatal")
        return orig_run(cmd, *a, **kw)
    monkeypatch.setattr(subprocess, "run", mock_run)
    res = sprint.create_sprint(l, "slug-test")
    assert res is not None

# 11. Kill cli.py:21 (and -> or in command loading)
def test_cli_load_commands_retain():
    fake = types.SimpleNamespace(__file__=__file__)
    sys.modules["actl.cmd_fake_preserve"] = fake
    try:
        cli.discover_commands(argparse.ArgumentParser().add_subparsers())
        assert "actl.cmd_fake_preserve" in sys.modules
    finally:
        sys.modules.pop("actl.cmd_fake_preserve", None)
