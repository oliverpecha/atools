# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2, proof text only; not executed.
import json
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for _p in (REPO / "src", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from actl import schemas, scope  # noqa: E402


def run_synth(monkeypatch, tmp_path, schema, instance):
    errors = []
    schemas._validate_schema(instance, schema, "/", errors, schema, "synth.json")
    seen = set()
    unique = []
    for e in errors:
        key = (e["path"], e["message"])
        if key not in seen:
            seen.add(key)
            unique.append(e)
    unique.sort(key=lambda e: (e["path"], e["message"]))
    return unique


PREFIX = {"type": "array", "prefixItems": [{"type": "integer"}, {"type": "string"}]}


@pytest.mark.parametrize("inst", [[], [1], [1, "a"]])
def test_prefix_items_shorter_or_equal_instance_is_valid(monkeypatch, tmp_path, inst):
    assert run_synth(monkeypatch, tmp_path, PREFIX, inst) == []  # schemas.py:280 '<' -> '<=' raises IndexError


def test_prefix_items_errors_at_index(monkeypatch, tmp_path):
    errs = run_synth(monkeypatch, tmp_path, PREFIX, [1, 5])
    assert [e["path"] for e in errs] == ["/1"]
    errs = run_synth(monkeypatch, tmp_path, PREFIX, ["a"])
    assert [e["path"] for e in errs] == ["/0"]


def test_prefix_items_then_items(monkeypatch, tmp_path):
    schema = dict(PREFIX, items={"type": "boolean"})
    assert run_synth(monkeypatch, tmp_path, schema, [1, "a", True]) == []
    assert [e["path"] for e in run_synth(monkeypatch, tmp_path, schema, [1, "a", 5])] == ["/2"]


def test_not_keyword(monkeypatch, tmp_path):
    schema = {"not": {"type": "string"}}
    assert run_synth(monkeypatch, tmp_path, schema, 5) == []  # schemas.py:361 'not be' -> 'be'
    errs = run_synth(monkeypatch, tmp_path, schema, "x")
    assert len(errs) == 1 and errs[0]["path"] == "/"


def test_not_keyword_nested_path(monkeypatch, tmp_path):
    schema = {"type": "object", "properties": {"a": {"not": {"type": "integer"}}}}
    assert run_synth(monkeypatch, tmp_path, schema, {"a": "s"}) == []
    assert [e["path"] for e in run_synth(monkeypatch, tmp_path, schema, {"a": 3})] == ["/a"]


TEXT = "ALLOW: src/a.py\nFROZEN: test/**\nALLOW: lib/*.py\n"


def test_scope_rule_list_string_indexing():
    rules = scope.parse(TEXT)
    assert rules["allow"] == ["src/a.py", "lib/*.py"]
    assert rules["ALLOWED"] == ["src/a.py", "lib/*.py"]
    assert rules["frozen"] == ["test/**"]
    assert rules["Freeze"] == ["test/**"]
    assert rules["bogus"] == []  # scope.py:80 '==' -> '!=' returns every pattern


def test_scope_rule_list_int_and_slice_indexing():
    rules = scope.parse(TEXT)
    assert rules[0].kind == "ALLOW" and rules[0].pattern == "src/a.py" and rules[0].line_no == 1
    assert rules[-1].pattern == "lib/*.py"
    sl = rules[0:2]
    assert isinstance(sl, list) and len(sl) == 2
    with pytest.raises(IndexError):
        _ = rules[99]
