# Authored-by: Gemini 2.5 Pro (Google), model family: Gemini
"""Tests killing surviving mutants from seed 41 baseline."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from helpers import need, need_attr


# S41-hashing:57: math.isnan(obj) or math.isinf(obj) -> 'and'
# With 'and', single nan or inf floats pass validation because no float is both nan AND inf.
def test_canonical_json_rejects_top_level_nan_and_inf():
    hashing = need("actl.hashing")
    canonical_json = need_attr(hashing, "canonical_json")

    for val in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError, match="NaN/Infinity not allowed"):
            canonical_json(val)
        with pytest.raises(ValueError, match="NaN/Infinity not allowed"):
            canonical_json({"score": val})


# S41-schemas:274 & 276: minItems and maxItems exact boundary checks
# '< -> <=' and '> -> >='
# For minItems: len == minItems must be valid. Mutant '<=' rejects it.
# For maxItems: len == maxItems must be valid. Mutant '>=' rejects it.
def test_schema_min_max_items_exact_boundaries():
    schemas = need("actl.schemas")
    _validate_schema = need_attr(schemas, "_validate_schema")

    schema = {
        "type": "array",
        "minItems": 2,
        "maxItems": 4,
    }

    # Exactly at minItems (2) -> valid
    errs = []
    _validate_schema([1, 2], schema, "/", errs, schema, "test.json")
    assert len(errs) == 0, f"minItems boundary failed: {errs}"

    # Exactly at maxItems (4) -> valid
    errs = []
    _validate_schema([1, 2, 3, 4], schema, "/", errs, schema, "test.json")
    assert len(errs) == 0, f"maxItems boundary failed: {errs}"

    # Below minItems (1) -> invalid
    errs = []
    _validate_schema([1], schema, "/", errs, schema, "test.json")
    assert any("Array shorter than minItems" in e["message"] for e in errs)

    # Above maxItems (5) -> invalid
    errs = []
    _validate_schema([1, 2, 3, 4, 5], schema, "/", errs, schema, "test.json")
    assert any("Array longer than maxItems" in e["message"] for e in errs)


# S41-sprint:40: if not p.is_file(): raise FileNotFoundError
# Mutant flips 'not p.is_file()' to 'p.is_file()', so an existing sprint.toml raises FileNotFoundError!
def test_load_sprint_toml_with_existing_file(tmp_path):
    sprint_mod = need("actl.sprint")
    load_sprint_toml = need_attr(sprint_mod, "load_sprint_toml")
    layout_mod = need("actl.layout")
    Layout = need_attr(layout_mod, "Layout")

    lay = Layout(tmp_path / "root")
    tag = "2026-10-16_demo-sprint"
    lay.ensure_sprint_tree(tag)

    toml_path = lay.sprint_toml(tag)
    toml_path.write_text('sprint_tag = "2026-10-16_demo-sprint"\nstatus = "draft"\n', encoding="utf-8")

    data = load_sprint_toml(lay, tag)
    assert data["sprint_tag"] == "2026-10-16_demo-sprint"


# S41-seq:239: if isinstance(candidate, dict) and not schemas.validate("state", candidate):
# Mutant flips 'not' to '', causing valid state candidates to be ignored and invalid ones accepted!
def test_reconstruct_retains_valid_state_file_data(tmp_path):
    seq_mod = need("actl.seq")
    reconstruct = need_attr(seq_mod, "reconstruct")
    read_state = need_attr(seq_mod, "read_state")
    layout_mod = need("actl.layout")
    Layout = need_attr(layout_mod, "Layout")

    lay = Layout(tmp_path / "root")
    tag = "2026-10-16_demo-sprint"
    lay.ensure_sprint_tree(tag)

    custom_run_id = "run-custom-123456"
    valid_state = {
        "run_id": custom_run_id,
        "sprint_tag": tag,
        "seq": 0,
        "epoch": 1,
        "status": "draft",
        "active_stage": None,
        "active_spec": None,
        "active_solution_key": None,
        "active_oracle_draft": None,
        "active_oracle": None,
        "active_contract": None,
        "attempts": {"oracle": 0, "implementer": 0, "live": 0, "curator": 0},
        "closures_submitted": 0,
        "hard_caps_tripped": 0,
        "grants": {"oracle": 0, "implementer": 0, "live": 0, "curator": 0},
        "tmux_sessions": [],
    }
    lay.state_file(tag).write_text(json.dumps(valid_state), encoding="utf-8")

    reconstruct(lay, tag)
    st = read_state(lay, tag)
    assert st["run_id"] == custom_run_id


# S41-seq:356: if state.get("status") == "hold": state["status"] = "running"
# Mutant flips '==' to '!='. When status is "hold", mutant does NOT set it to "running".
def test_reconstruct_resolved_escalation_clears_hold_status(tmp_path):
    seq_mod = need("actl.seq")
    reconstruct = need_attr(seq_mod, "reconstruct")
    read_state = need_attr(seq_mod, "read_state")
    layout_mod = need("actl.layout")
    Layout = need_attr(layout_mod, "Layout")

    lay = Layout(tmp_path / "root")
    tag = "2026-10-16_demo-sprint"
    lay.ensure_sprint_tree(tag)

    # 1. ev artifact with halt=True puts state["status"] into "hold" (seq.py line 374)
    ev_doc = {
        "seq": 1,
        "stage": "implementer",
        "halt": True,
    }
    (lay.runs_dir(tag) / "ev-001.json").write_text(json.dumps(ev_doc), encoding="utf-8")

    # 2. Subsequent escalation with status="resolved" reaches line 356:
    # elif esc.get("status") == "resolved":
    #     if state.get("status") == "hold":
    #         state["status"] = "running"
    esc_doc = {
        "seq": 2,
        "status": "resolved",
        "resolution": {},
    }
    (lay.runs_dir(tag) / "escalation-002.json").write_text(json.dumps(esc_doc), encoding="utf-8")

    reconstruct(lay, tag)
    st = read_state(lay, tag)
    assert st["status"] == "running", f"Resolved escalation must transition hold -> running, got: {st['status']}"


# S41-seq:378 & 383: cand.is_file() and cand != p, and mkind == "spec"
# Mutants: '!=' -> '==' (treats p as its own meta file) or 'mkind == "spec"' -> '!='
def test_reconstruct_sidecar_meta_sets_active_spec(tmp_path):
    seq_mod = need("actl.seq")
    reconstruct = need_attr(seq_mod, "reconstruct")
    read_state = need_attr(seq_mod, "read_state")
    layout_mod = need("actl.layout")
    Layout = need_attr(layout_mod, "Layout")

    lay = Layout(tmp_path / "root")
    tag = "2026-10-16_demo-sprint"
    lay.ensure_sprint_tree(tag)

    # Create an artifact file and its companion sidecar meta file
    art = lay.sprint_dir(tag) / "spec-001.md"
    art.write_text("# Spec Content", encoding="utf-8")

    meta = {
        "kind": "spec",
        "seq": 1,
        "sha256": "0" * 64,
    }
    sidecar = lay.sprint_dir(tag) / "spec-001.md.meta.json"
    sidecar.write_text(json.dumps(meta), encoding="utf-8")

    reconstruct(lay, tag)
    st = read_state(lay, tag)
    assert st["active_spec"] == "spec-001.md", "Sidecar meta must set active_spec"
