# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-15 / S0-R14: expected.d fragment loader."""
import json
import shutil

import pytest

from helpers import *  # noqa


def _load():
    return need_attr(need("actl.schemas"), "load_expected")


def test_real_expected_dir_loads_base():
    """Merged expected.d keeps every base case; fragments may add cases/responses (S0-R14)."""
    d = _load()(GOLDEN / "expected.d")
    base = json.loads((GOLDEN / "expected.d" / "base.json").read_text())
    if d["base_sha"] != base["base_sha"] or d["base_sha"] != BASE_SHA: fail("base_sha not loaded")
    if set(d) != {"base_sha", "cases", "responses"}: fail("merged dict keys must be base_sha/cases/responses, got %s" % sorted(d))
    for key, val in base.get("cases", {}).items():
        if key not in d["cases"]: fail("base case missing: %s" % key)
        if d["cases"][key] != val: fail("base case altered: %s" % key)
    union_resp = {}
    union_cases = {}
    ed = GOLDEN / "expected.d"
    for frag in sorted(ed.glob("*.json"), key=lambda x: x.name):
        if frag.name == "base.json":
            continue
        doc = json.loads(frag.read_text())
        if not isinstance(doc, dict):
            continue
        if isinstance(doc.get("responses"), dict):
            union_resp.update(doc["responses"])
        if isinstance(doc.get("cases"), dict):
            for key, val in doc["cases"].items():
                if key in union_cases or key in base.get("cases", {}):
                    fail("duplicate case in fragments: %s" % key)
                union_cases[key] = val
    if d["responses"] != union_resp: fail("responses must be the union of non-base fragments")
    for key, val in union_cases.items():
        if key not in d["cases"]: fail("fragment case missing: %s" % key)
        if d["cases"][key] != val: fail("fragment case altered: %s" % key)
    if set(d["cases"]) != set(base.get("cases", {})) | set(union_cases):
        fail("merged cases keys must be base union fragment cases")


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

def test_duplicate_case_across_non_base_fragments(tmp_path):
    """S0-R14.2: duplicate case key in any two non-base fragments is ValueError (D28-01, D28-02)."""
    case1 = {"applies_on": "base", "expect": {"step": "O1", "exit": 1, "failing_step": "O1:x.sh", "failing_line_contains": None}}
    case2 = {"applies_on": "base", "expect": {"step": "O2", "exit": 0, "failing_step": None, "failing_line_contains": None}}
    ed = tmp_path / "adj"
    ed.mkdir()
    shutil.copy(GOLDEN / "expected.d" / "base.json", ed / "base.json")
    (ed / "s1.json").write_text(json.dumps({"cases": {"s1_only": case1}}))
    (ed / "s2.json").write_text(json.dumps({"cases": {"s1_only": case2}}))
    with pytest.raises(ValueError):
        _load()(ed)
    ed2 = tmp_path / "nonadj"
    ed2.mkdir()
    shutil.copy(GOLDEN / "expected.d" / "base.json", ed2 / "base.json")
    (ed2 / "s1.json").write_text(json.dumps({"cases": {"duplicate_across_files": case1}}))
    (ed2 / "s2.json").write_text(json.dumps({"cases": {"middle_only": case1}}))
    (ed2 / "s3.json").write_text(json.dumps({"cases": {"duplicate_across_files": case2}}))
    with pytest.raises(ValueError):
        _load()(ed2)
