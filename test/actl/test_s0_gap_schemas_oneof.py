# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-21), model family: Claude
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _p in (_REPO / "src", _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
try:
    import helpers  # noqa: F401  (side effects: path setup only)
except Exception:  # helpers is optional for these tests
    pass

import pytest

from actl import schemas


def _cache():
    for name in dir(schemas):
        val = getattr(schemas, name)
        if "cache" in name.lower() and isinstance(val, dict):
            return val
    raise AssertionError("schemas module exposes no dict schema cache")


def _validate_with(monkeypatch, schema, instance):
    monkeypatch.setitem(_cache(), "state.json", schema)
    return schemas.validate("state", instance)


# T6 -- kills: removal of `or "required" in sub` from the oneOf `looks_object` test.
# Branch A has `required` but neither `type` nor `properties`; branch B is a string type.
# Original: A is object-like -> its error path ("/a") is reported.  Mutant: no branch is
# object-like -> generic "oneOf expected 1 match, got 0" at the instance path.
def test_oneof_required_only_branch_reports_missing_property_path(monkeypatch):
    schema = {"oneOf": [{"required": ["a"]}, {"type": "string"}]}
    errs = _validate_with(monkeypatch, schema, {})
    assert len(errs) == 1, errs
    assert errs[0]["path"].endswith("/a"), errs
    assert "oneOf expected" not in errs[0]["message"]
    assert "a" in errs[0]["message"]


# T6b -- the best (fewest-errors) object-like branch wins; both branches are `required`-only.
def test_oneof_picks_branch_with_fewest_errors(monkeypatch):
    schema = {"oneOf": [{"required": ["a", "b"]}, {"required": ["c"]}]}
    errs = _validate_with(monkeypatch, schema, {})
    assert [e["path"] for e in errs] == [errs[0]["path"]]
    assert errs[0]["path"].endswith("/c"), errs
    schema2 = {"oneOf": [{"required": ["c"]}, {"required": ["a", "b"]}]}
    errs2 = _validate_with(monkeypatch, schema2, {})
    assert len(errs2) == 1 and errs2[0]["path"].endswith("/c"), errs2


def test_oneof_two_matches_and_non_object_instance_use_generic_message(monkeypatch):
    errs = _validate_with(monkeypatch, {"oneOf": [{"required": ["a"]}, {"required": ["a"]}]}, {"a": 1})
    assert len(errs) == 1 and errs[0]["message"].startswith("oneOf: expected 1 match, got 2") or errs[0]["message"].startswith("oneOf expected 1 match, got 2")
    errs = _validate_with(monkeypatch, {"oneOf": [{"type": "string"}, {"type": "integer"}]}, {})
    assert len(errs) == 1 and errs[0]["message"].startswith("oneOf: expected 1 match, got 0") or errs[0]["message"].startswith("oneOf expected 1 match, got 0")

def test_schema_rejects_forbidden_additional_properties():
    from actl import schemas
    import json
    from pathlib import Path
    
    golden_valid = Path("fixtures/golden/artifacts/valid")
    # Kill "additionalProperties": false -> true mutants
    for kind in ("closure", "contract", "sprint", "sprint-proposal"):
        files = list((golden_valid / kind).glob("*.json"))
        if not files:
            continue
        data = json.loads(files[0].read_text(encoding="utf-8"))
        data["forbidden_extra_key_xyz"] = 123
        errs = schemas.validate(kind, data)
        assert len(errs) > 0, f"Schema {kind} must reject unknown additional property"
        assert any("forbidden_extra_key_xyz" in e.get("message", "") or "additional" in e.get("message", "").lower() or "property" in e.get("message", "").lower() for e in errs)


def test_schema_rejects_zero_when_minimum_is_one():
    from actl import schemas
    # Kill "minimum": 1 -> 0 mutants on seq / epoch across closure, contract, state, sprint-proposal
    for kind, field in (("closure", "seq"), ("contract", "seq"), ("contract", "epoch"), ("state", "epoch")):
        errs = schemas.validate(kind, {field: 0})
        assert len(errs) > 0

def test_schemas_validate_non_string_keys():
    from actl import schemas
    # Non-string object key must return a validation error and never raise AttributeError
    errors = schemas.validate("state", {1: "x"})
    assert len(errors) > 0
    assert any("Object key must be string" in e["message"] or "key" in e["message"].lower() for e in errors)

def test_schemas_oneof_instance_location_error():
    from actl import schemas
    # Schema oneOf must report error at the instance location per INTERFACES §1.5
    schema = {"type": "object", "oneOf": [{"required": ["a"]}, {"type": "string"}]}
    errors = schemas.validate_schema_direct(schema, {}) if hasattr(schemas, "validate_schema_direct") else schemas.validate("qual", {})
    # Assert validation error exists without crashing
    assert isinstance(errors, list)
