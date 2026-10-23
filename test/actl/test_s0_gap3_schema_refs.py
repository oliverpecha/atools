"""S37-08 (schemas.py:270 `>=` -> `>`), S37-09 (:179) and S37-10 (:170) `or` -> `and`."""
import json

import pytest

from actl import schemas


def _msgs(errors):
    return [e["message"] for e in errors]


def _install(monkeypatch, **docs):
    for name, doc in docs.items():
        monkeypatch.setitem(schemas._schema_cache, name, doc)


# ---- S37-08 -------------------------------------------------------------

def test_exclusive_maximum_boundary(monkeypatch):
    _install(monkeypatch, **{"meta.json": {
        "type": "object",
        "properties": {"n": {"type": "number", "exclusiveMaximum": 10}},
    }})
    for bad in (10, 10.0, 11):
        errs = schemas.validate("meta", {"n": bad})
        assert [e["path"] for e in errs] == ["/n"], bad
        assert any(m.startswith("Value not below exclusiveMaximum") for m in _msgs(errs)), bad
    for good in (9, 9.999, 0, -5):
        assert schemas.validate("meta", {"n": good}) == [], good


def test_exclusive_minimum_boundary(monkeypatch):
    _install(monkeypatch, **{"meta.json": {
        "type": "object",
        "properties": {"n": {"type": "number", "exclusiveMinimum": 5}},
    }})
    for bad in (5, 5.0, 4, -1):
        errs = schemas.validate("meta", {"n": bad})
        assert [e["path"] for e in errs] == ["/n"], bad
        assert any(m.startswith("Value not above exclusiveMinimum") for m in _msgs(errs)), bad
    for good in (5.001, 6, 100):
        assert schemas.validate("meta", {"n": good}) == [], good


# ---- S37-09 / S37-10: non-empty fragments (these kill the mutants) -------

def test_cross_file_fragment_ref_enforces_target(monkeypatch):
    _install(monkeypatch, **{
        "meta.json": {"type": "object",
                      "properties": {"a": {"$ref": "s0gap3_other.json#/$defs/x"}}},
        "s0gap3_other.json": {"$defs": {"x": {"type": "string"}}},
    })
    errs = schemas.validate("meta", {"a": 5})
    assert [e["path"] for e in errs] == ["/a"]
    assert any(m.startswith("Type mismatch") for m in _msgs(errs))
    assert schemas.validate("meta", {"a": "ok"}) == []


def test_local_fragment_ref_enforces_target(monkeypatch):
    _install(monkeypatch, **{"meta.json": {
        "$defs": {"x": {"type": "string"}},
        "type": "object",
        "properties": {"a": {"$ref": "#/$defs/x"}},
    }})
    errs = schemas.validate("meta", {"a": 5})
    assert [e["path"] for e in errs] == ["/a"]
    assert schemas.validate("meta", {"a": "ok"}) == []


def test_resolve_ref_fragment_returns_def_not_root():
    doc = {"$defs": {"x": {"type": "string"}}, "marker": "root"}
    target, new_doc, name = schemas._resolve_ref("#/$defs/x", doc, "d.json")
    assert target == {"type": "string"} and new_doc is doc and name == "d.json"


# ---- whole-document refs: equivalent for both mutants, regression guards --

def test_whole_document_file_ref_resolves_to_root(monkeypatch):
    other = {"type": "string"}
    _install(monkeypatch, **{
        "meta.json": {"type": "object", "properties": {"a": {"$ref": "s0gap3_whole.json"}}},
        "s0gap3_whole.json": other,
    })
    target, new_doc, name = schemas._resolve_ref("s0gap3_whole.json", {}, "meta.json")
    assert target is other and new_doc is other and name == "s0gap3_whole.json"
    assert [e["path"] for e in schemas.validate("meta", {"a": 5})] == ["/a"]
    assert schemas.validate("meta", {"a": "s"}) == []


def test_hash_ref_resolves_to_root(monkeypatch):
    root = {"type": "object", "properties": {"a": {"$ref": "#"}}}
    _install(monkeypatch, **{"meta.json": root})
    target, new_doc, _ = schemas._resolve_ref("#", root, "meta.json")
    assert target is root and new_doc is root
    assert [e["path"] for e in schemas.validate("meta", {"a": 5})] == ["/a"]
    assert schemas.validate("meta", {"a": {}}) == []
    assert schemas.validate("meta", {"a": {"a": {}}}) == []


# ---- lint over the real schemas ------------------------------------------

def _refs(node):
    if isinstance(node, dict):
        for k, v in node.items():
            if k == "$ref" and isinstance(v, str):
                yield v
            else:
                yield from _refs(v)
    elif isinstance(node, list):
        for v in node:
            yield from _refs(v)


_FILES = sorted(schemas.SCHEMAS_DIR.glob("*.json"))


def test_schemas_dir_has_refs():
    assert _FILES
    assert sum(len(list(_refs(json.loads(p.read_text(encoding="utf-8"))))) for p in _FILES) >= 1


@pytest.mark.parametrize("path", _FILES, ids=lambda p: p.name)
def test_every_ref_has_nonempty_defs_fragment_that_resolves(path):
    doc = json.loads(path.read_text(encoding="utf-8"))
    for ref in _refs(doc):
        assert "#" in ref, f"{path.name}: ref without fragment: {ref}"
        frag = ref.split("#", 1)[1]
        assert frag.startswith("/$defs/") and len(frag) > len("/$defs/"), f"{path.name}: {ref}"
        target, _, _ = schemas._resolve_ref(ref, doc, path.name)
        assert isinstance(target, dict), f"{path.name}: {ref} does not resolve to a schema"


# ---- allOf + real artifact_meta ------------------------------------------

def test_allof_ref_artifact_meta_rejects_missing_seq(monkeypatch):
    ref = "common.json#/$defs/artifact_meta"
    target, _, _ = schemas._resolve_ref(ref, {}, "meta.json")
    assert "seq" in target.get("required", []), "premise: artifact_meta requires seq"
    _install(monkeypatch, **{"meta.json": {"allOf": [{"$ref": ref}]}})
    errs = schemas.validate("meta", {})
    assert any(e["path"] == "/seq" and e["message"].startswith("Missing required property") for e in errs), errs
