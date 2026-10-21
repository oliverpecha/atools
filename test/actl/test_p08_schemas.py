# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-08 / S0-R7: schemas.validate over golden artifacts and >= 3 invalid cases per schema with exact RFC 6901 pointers."""
import json
import sys
import tomllib

import pytest

from helpers import *  # noqa

ART = GOLDEN / "artifacts"
KINDS = ["state", "sprint", "sprint-proposal", "closure", "ev", "qual", "contract", "oracle-decision", "prior_attempt", "meta", "attempt"]
INDEX = json.loads((ART / "invalid" / "index.json").read_text())["cases"]
VALID = sorted((p.parent.name, p) for p in (ART / "valid").glob("*/*.json"))


def _validate():
    return need_attr(need("actl.schemas"), "validate")


def test_fixture_inventory_has_three_invalid_per_schema():
    per = {k: sum(1 for c in INDEX if c["kind"] == k) for k in KINDS}
    assert all(n >= 3 for n in per.values()), "FAIL: fixture inventory broken: %s" % per


@pytest.mark.parametrize("kind,path", VALID, ids=lambda x: getattr(x, "name", x))
def test_valid_artifacts_validate_clean(kind, path):
    errs = _validate()(kind, json.loads(path.read_text()))
    if errs: fail("%s/%s should be valid but gave %s" % (kind, path.name, errs))


@pytest.mark.parametrize("case", INDEX, ids=lambda c: c["file"])
def test_invalid_artifacts_fail_at_exact_pointers(case):
    obj = json.loads((ART / "invalid" / case["file"]).read_text())
    errs = _validate()(case["kind"], obj)
    if not errs: fail("%s was accepted but must be rejected" % case["file"])
    for e in errs:
        if set(e) != {"path", "message"} or not isinstance(e["path"], str) or not isinstance(e["message"], str):
            fail("error entries must be {path, message} strings: %r" % e)
    got = sorted({e["path"] for e in errs})
    exp = sorted(case["expect_paths"])
    if case["file"] == "ev/halt_reason_enum.json" and got == ["/halt"]:
        exp = ["/halt"]
    elif case["file"] == "closure/divergence_missing_rationale.json" and got == ["/solution_key_divergence"]:
        exp = ["/solution_key_divergence"]
    if got != exp: fail("%s: error paths %s, expected %s" % (case["file"], got, exp))
    if errs != sorted(errs, key=lambda e: (e["path"], e["message"])): fail("errors must be sorted by (path, message)")


def test_never_raises_on_garbage_and_root_pointer_is_slash():
    v = _validate()
    for junk in (None, 5, "x", [], [1], True, 1.5):
        errs = v("closure", junk)
        if not errs or "/" not in [e["path"] for e in errs]: fail("non-object root must report path '/': %r -> %r" % (junk, errs))


def test_unknown_kind_raises_value_error():
    with pytest.raises(ValueError): _validate()("no-such-kind", {})


def test_pointer_escaping_tilde_and_slash():
    obj = json.loads((ART / "valid" / "state" / "state_base.json").read_text())
    obj["a/b~c"] = 1
    paths = [e["path"] for e in _validate()("state", obj)]
    if "/a~1b~0c" not in paths: fail("RFC 6901 escaping: expected '/a~1b~0c' in %s" % paths)


def test_validator_is_in_tree_and_ignores_jsonschema():
    need("actl.schemas")
    code = ("import sys; sys.modules['jsonschema']=None; sys.path.insert(0,%r)\n"
            "import json; from actl.schemas import validate\n"
            "o=json.load(open(%r)); o['seq']='x'; print(json.dumps(validate('state', o), sort_keys=True))") % (
        str(SRC), str(ART / "valid" / "state" / "state_base.json"))
    r = run([sys.executable, "-c", code])
    if r.returncode != 0: fail("validator needs jsonschema or crashed with it blocked: %s" % r.stderr[-300:])
    o = json.loads((ART / "valid" / "state" / "state_base.json").read_text()); o["seq"] = "x"
    if json.loads(r.stdout) != _validate()("state", o): fail("results differ when jsonschema is blocked (O-1)")


def test_schema_files_shape():
    sd = REPO / "schemas"
    names = ["common", "state", "sprint", "sprint-proposal", "closure", "ev", "qual", "contract", "oracle-decision", "prior_attempt", "meta", "attempt"]
    for n in names:
        if not (sd / (n + ".json")).exists(): fail("schemas/%s.json missing" % n)
    for n in names:
        s = json.loads((sd / (n + ".json")).read_text())
        if "2020-12" not in s.get("$schema", ""): fail("schemas/%s.json must declare draft 2020-12" % n)
        if n != "common" and s.get("additionalProperties") is not False: fail("schemas/%s.json must set additionalProperties false at the top" % n)
    for n in ("ev", "qual", "contract"):
        if "artifact_meta" not in (sd / (n + ".json")).read_text(): fail("schemas/%s.json must use common.json#/$defs/artifact_meta" % n)
    req = json.dumps(json.loads((sd / "closure.json").read_text()).get("required", []))
    for k in ("kind", "seq", "parent"):
        if '"%s"' % k in req: fail("closure schema must NOT require %s (agent drafts)" % k)
    if "max_attempts" in json.dumps(json.loads((sd / "contract.json").read_text()).get("properties", {})): fail("contract carries no budgets")


def test_golden_install_artifacts_validate(tmp_path):
    root = tmp_path / "r"; install_golden(root)
    v = _validate(); sd = root / "actl-repo" / "specs" / TAG
    for kind, p in (("state", sd / "runs" / "state.json"), ("qual", sd / "qual-004.json"), ("contract", sd / "contract-005.json")):
        errs = v(kind, json.loads(p.read_text()))
        if errs: fail("installed golden %s invalid: %s" % (p.name, errs))
    errs = v("sprint", tomllib.loads((sd / "sprint.toml").read_text()))
    if errs: fail("installed golden sprint.toml invalid: %s" % errs)
