# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-26 / S0-R15: signature introspection against the machine-readable block of src/actl/INTERFACES.md."""
import importlib
import inspect
import json
import os
import re
import types

from helpers import *  # noqa

MD = REPO / "src" / "actl" / "INTERFACES.md"
KINDS = {"class", "function", "method", "property"}
STAGES = {"0A", "0B", "1", "2"}


def load_manifest():
    text = MD.read_text(encoding="utf-8")
    sec = text[text.index("## 4. Machine-Readable Interface Manifest"):]
    blocks = re.findall(r"```json\n(.*?)\n```", sec, re.S)
    assert len(blocks) == 1, "FAIL: section 4 must contain exactly one fenced json block, found %d" % len(blocks)
    return json.loads(blocks[0])


MANIFEST = load_manifest()


def check_entry(entry, module):
    """Return a list of problems (empty = conforms). Pure so it can be self-tested."""
    problems = []
    name = entry["name"]; kind = entry["kind"]; want = [p["name"] for p in entry["params"]]
    try:
        if kind == "property":
            cls_name, prop = name.split(".", 1)
            obj = inspect.getattr_static(getattr(module, cls_name), prop)
            if not isinstance(obj, property): return ["%s is not a property" % name]
            if obj.fget is None or "return" not in getattr(obj.fget, "__annotations__", {}): problems.append("%s: property getter lacks a return annotation" % name)
            return problems
        if kind == "class":
            cls = getattr(module, name)
            if not inspect.isclass(cls): return ["%s is not a class" % name]
            if name in ("UsageError", "StateIntegrityError", "EnvError") and not issubclass(cls, Exception): problems.append("%s must subclass Exception" % name)
            init = cls.__init__
            params = list(inspect.signature(init).parameters.values())[1:]
            if "return" not in getattr(init, "__annotations__", {}): problems.append("%s.__init__ lacks a return annotation" % name)
        elif kind in ("function", "method"):
            if kind == "method":
                cls_name, meth = name.split(".", 1)
                fn = inspect.getattr_static(getattr(module, cls_name), meth)
                if isinstance(fn, (staticmethod, classmethod)): fn = fn.__func__
                sig = inspect.signature(fn); params = list(sig.parameters.values())[1:]
            else:
                fn = getattr(module, name)
                if not callable(fn): return ["%s is not callable" % name]
                sig = inspect.signature(fn); params = list(sig.parameters.values())
            if sig.return_annotation is inspect.Signature.empty: problems.append("%s lacks a return annotation" % name)
        else:
            return ["unknown kind %r" % kind]
    except (AttributeError, KeyError, TypeError, ValueError) as e:
        return ["%s: cannot introspect (%s: %s)" % (name, type(e).__name__, e)]
    got = [p.name for p in params]
    if got != want: problems.append("%s: parameter names/order %s != manifest %s" % (name, got, want))
    return problems


def _should_check(e):
    st = e["stage"]
    if st in set(os.environ.get("ACTL_CHECK_STAGES", "0A").split(",")): return True
    if st == "0B":
        try:
            import router.process as rp
            return hasattr(rp, "read_exit_code")
        except ImportError:
            return False
    if st in ("1", "2"):
        try:
            importlib.import_module(e["module"]); return True
        except ImportError:
            return False
    return False


def test_manifest_is_well_formed():
    assert isinstance(MANIFEST, list) and len(MANIFEST) >= 71, "FAIL: manifest too small"
    seen = set()
    for e in MANIFEST:
        assert set(e) == {"module", "name", "kind", "stage", "params", "returns"}, "FAIL: bad keys %s" % e
        assert e["kind"] in KINDS and e["stage"] in STAGES, "FAIL: bad kind/stage %s" % e
        key = (e["module"], e["name"]); assert key not in seen, "FAIL: duplicate %s" % (key,); seen.add(key)
        assert all(set(p) == {"name", "type"} for p in e["params"]), "FAIL: bad param %s" % e
    required = {("actl.layout", "Layout"), ("actl.seq", "reserve"), ("actl.seq", "reconstruct"), ("actl.hashing", "manifest_sha256"),
                ("actl.schemas", "validate"), ("actl.scope", "match"), ("actl.next", "decide_next"), ("actl.cli", "main"),
                ("router.process", "read_exit_code")}
    assert required <= seen, "FAIL: manifest lacks %s" % sorted(required - seen)


def test_checker_detects_wrong_signatures():
    """Non-vacuity: the checker itself must reject drift."""
    m = types.ModuleType("fake")
    def f(b: int, a: int) -> int: return 1
    def g(a: int, b: int): return 1
    class C:
        def __init__(self, x): pass
        @property
        def p(self): return 1
    m.f, m.g, m.C = f, g, C
    ok = {"module": "fake", "name": "f", "kind": "function", "stage": "0A", "params": [{"name": "b", "type": "int"}, {"name": "a", "type": "int"}], "returns": "int"}
    assert check_entry(ok, m) == [], "FAIL: checker rejects a conforming function"
    assert check_entry({**ok, "params": [{"name": "a", "type": "int"}, {"name": "b", "type": "int"}]}, m), "FAIL: checker accepts swapped params"
    assert check_entry({**ok, "name": "g"}, m), "FAIL: checker accepts a missing return annotation"
    assert check_entry({**ok, "name": "missing"}, m), "FAIL: checker accepts a missing name"
    assert check_entry({**ok, "name": "C.p", "kind": "property", "params": []}, m), "FAIL: checker accepts a property without return annotation"
    assert check_entry({**ok, "name": "C", "kind": "class", "params": [{"name": "x", "type": "int"}]}, m), "FAIL: checker accepts __init__ without return annotation"


def test_every_listed_name_exists_with_compatible_signature():
    checked = 0; problems = []
    for e in MANIFEST:
        if not _should_check(e): continue
        mod = need(e["module"])
        problems += check_entry(e, mod); checked += 1
    if checked < 56: fail("only %d entries were checked; stage 0A alone has 56 entries" % checked)
    if problems: fail("%d interface problem(s):\n  " % len(problems) + "\n  ".join(problems[:40]))
