# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-15 / S0-R14: expected.d fragment loader."""
import json
import shutil

import pytest

from helpers import *  # noqa


def _load():
    return need_attr(need("actl.schemas"), "load_expected")


def test_real_expected_dir_loads_base():
    d = _load()(GOLDEN / "expected.d")
    base = json.loads((GOLDEN / "expected.d" / "base.json").read_text())
    if d["base_sha"] != base["base_sha"] or d["base_sha"] != BASE_SHA: fail("base_sha not loaded")
    if d["cases"] != base["cases"]: fail("cases not loaded from base.json")
    if set(d) != {"base_sha", "cases", "responses"}: fail("merged dict keys must be base_sha/cases/responses, got %s" % sorted(d))
    if d["responses"] != {}: fail("responses defaults to {} when no fragment defines them")


def test_merges_base_s1_s2(tmp_path):
    ed = tmp_path / "expected.d"; ed.mkdir()
    shutil.copy(GOLDEN / "expected.d" / "base.json", ed / "base.json")
    s1 = {"cases": {"s1_case": {"applies_on": "base", "expect": {"step": "O1", "exit": 1, "failing_step": "O1:x.sh", "failing_line_contains": None}}}}
    s2 = {"responses": {"r1": {"purpose": "architect-intake", "turn": "architect-1", "expect": {"exit": 0, "error_code": None, "output_hashes": {}}}}}
    (ed / "s1.json").write_text(json.dumps(s1)); (ed / "s2.json").write_text(json.dumps(s2))
    d = _load()(ed)
    base = json.loads((GOLDEN / "expected.d" / "base.json").read_text())
    if set(d["cases"]) != set(base["cases"]) | {"s1_case"}: fail("cases from base and s1 must be unioned")
    if d["responses"] != s2["responses"]: fail("responses from s2 not merged")
    if d["base_sha"] != BASE_SHA: fail("base_sha lost")


def test_duplicate_key_malformed_and_missing(tmp_path):
    ed = tmp_path / "e"; ed.mkdir()
    shutil.copy(GOLDEN / "expected.d" / "base.json", ed / "base.json")
    (ed / "s1.json").write_text(json.dumps({"cases": {"good": {"applies_on": "base", "expect": {"step": "O2", "exit": 0, "failing_step": None, "failing_line_contains": None}}}}))
    with pytest.raises(ValueError): _load()(ed)
    (ed / "s1.json").write_text("{not json")
    with pytest.raises(ValueError): _load()(ed)
    with pytest.raises(FileNotFoundError): _load()(tmp_path / "absent")
    only = tmp_path / "o"; only.mkdir()
    (only / "base.json").write_text(json.dumps({"base_sha": "a" * 40}))
    (only / "s1.json").write_text(json.dumps({"base_sha": "b" * 40}))
    with pytest.raises(ValueError): _load()(only)


def test_lexical_order_is_deterministic(tmp_path):
    ed = tmp_path / "e"; ed.mkdir()
    (ed / "base.json").write_text(json.dumps({"base_sha": "a" * 40, "cases": {"z": {}, "a": {}}}))
    (ed / "s2.json").write_text(json.dumps({"cases": {"m": {}}}))
    (ed / "s1.json").write_text(json.dumps({"cases": {"b": {}}}))
    d1 = _load()(ed)
    if list(d1["cases"]) != ["z", "a", "b", "m"]: fail("fragments must merge in lexical filename order (base, s1, s2); got %s" % list(d1["cases"]))
