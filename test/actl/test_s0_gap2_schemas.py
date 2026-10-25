# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2, proof text only; not executed.
import copy
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

from actl import schemas  # noqa: E402

SCHEMA_DIR = REPO / "schemas"
FIXTURES = REPO / "fixtures" / "golden" / "artifacts"
KINDS = [k for k in schemas.VALID_KINDS if k != "common"]
FREEFORM = set()  # (kind, pointer) of nodes deliberately open; must stay empty unless Owner approves


# ---------- independent resolver (does not use actl.schemas internals) ----------

def jload(name):
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


def unesc(t):
    return t.replace("~1", "/").replace("~0", "~")


def esc(t):
    return str(t).replace("~", "~0").replace("/", "~1")


def join_ptr(tokens):
    return "/" + "/".join(esc(t) for t in tokens) if tokens else "/"


def walk_ptr(doc, pointer):
    cur = doc
    body = pointer.lstrip("/")
    for raw in (body.split("/") if body else []):
        cur = cur[unesc(raw)]
    return cur


def resolve_ref(ref, doc, name):
    if ref.startswith("#"):
        return walk_ptr(doc, ref[1:]), doc, name
    f, _, frag = ref.partition("#")
    f = Path(f).name
    d = jload(f)
    return (walk_ptr(d, frag) if frag else d), d, f


def expand(schema, doc, name):
    out, intro, stack, guard = [], False, [(schema, doc, name)], 0
    while stack and guard < 500:
        s, d, n = stack.pop()
        if not isinstance(s, dict):
            continue
        guard += 1
        out.append((s, d, n))
        if "$ref" in s:
            t, d2, n2 = resolve_ref(s["$ref"], d, n)
            stack.append((t, d2, n2))
        for sub in s.get("allOf", []):
            stack.append((sub, d, n))
        for k in ("oneOf", "anyOf"):
            for sub in s.get(k, []):
                intro = True
                stack.append((sub, d, n))
        for k in ("then", "else"):
            if isinstance(s.get(k), dict):
                stack.append((s[k], d, n))
    return out, intro


def child_schemas(sets, token, inst):
    out = []
    for s, d, n in sets:
        if isinstance(inst, list):
            i, pre = int(token), (s.get("prefixItems") or [])
            if i < len(pre):
                out.append((pre[i], d, n))
            elif isinstance(s.get("items"), dict):
                out.append((s["items"], d, n))
        else:
            props = s.get("properties") or {}
            if token in props:
                out.append((props[token], d, n))
            elif isinstance(s.get("additionalProperties"), dict):
                out.append((s["additionalProperties"], d, n))
    return out


def resolve_at(kind, tokens, doc):
    root = jload(f"{kind}.json")
    sets, intro = expand(root, root, f"{kind}.json")
    comps = [join_ptr([])] if intro else []
    inst, seen = doc, []
    for t in tokens:
        kids = child_schemas(sets, t, inst)
        inst = inst[int(t)] if isinstance(inst, list) else inst[t]
        seen.append(t)
        sets = []
        for k, d, n in kids:
            ex, i2 = expand(k, d, n)
            sets.extend(ex)
            if i2:
                comps.append(join_ptr(seen))
    return sets, comps


def dict_nodes(doc, tokens=()):
    if isinstance(doc, dict):
        yield list(tokens), doc
        for k, v in doc.items():
            yield from dict_nodes(v, tokens + (k,))
    elif isinstance(doc, list):
        for i, v in enumerate(doc):
            yield from dict_nodes(v, tokens + (str(i),))


def get_node(doc, tokens):
    cur = doc
    for t in tokens:
        cur = cur[int(t)] if isinstance(cur, list) else cur[t]
    return cur


def set_path(doc, tokens, value):
    cur = doc
    for t in tokens[:-1]:
        if t not in cur or not isinstance(cur[t], dict):
            cur[t] = {}
        cur = cur[t]
    cur[tokens[-1]] = value


_CASES = None


def cases():
    global _CASES
    if _CASES is None:
        out = []
        for p in sorted(FIXTURES.rglob("*.json")):
            if "invalid" in p.relative_to(FIXTURES).parts:
                continue
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            if not isinstance(d, dict):
                continue
            for kind in KINDS:
                if schemas.validate(kind, d) == []:
                    out.append((kind, p, d))
        _CASES = out
    return _CASES


def doc_of(kind):
    for k, _, d in cases():
        if k == kind:
            return copy.deepcopy(d)
    pytest.fail(f"FAIL: no valid fixture validates as {kind}", pytrace=False)


def errs_at(kind, doc):
    return [(e["path"], e["message"]) for e in schemas.validate(kind, doc)]


# ---------- (a) zz_extra at every dict node ----------

def test_fixture_inventory():
    have = {k for k, _, _ in cases()}
    for k in ("state", "sprint", "sprint-proposal", "closure", "verification", "qualification", "contract"):
        assert k in have, f"no valid fixture for {k}"


def test_zz_extra_rejected_at_every_dict_node():
    failures = []
    for kind, p, doc in cases():
        for tokens, _ in dict_nodes(doc):
            if (kind, join_ptr(tokens)) in FREEFORM:
                continue
            m = copy.deepcopy(doc)
            get_node(m, tokens)["zz_extra"] = 1
            want = join_ptr(tokens + ["zz_extra"])
            _, comps = resolve_at(kind, tokens, doc)
            got = {e["path"] for e in schemas.validate(kind, m)}
            if want not in got and not (set(comps) & got):
                failures.append(f"{kind} {p.name} node {join_ptr(tokens)}: no error at {want} (got {sorted(got)})")
    assert not failures, "\n".join(failures)


# ---------- (b) resolver-driven boundary tests (cannot detect a lowered bound by themselves) ----------

def leaf_constraints(kind, tokens, doc):
    sets, _ = resolve_at(kind, tokens, doc)
    found = {}
    for s, d, n in sets:
        for prop, sub in (s.get("properties") or {}).items():
            for e, _, _ in expand(sub, d, n)[0]:
                for kw in ("minimum", "maximum", "maxLength"):
                    if kw in e and isinstance(e[kw], (int, float)) and not isinstance(e[kw], bool):
                        found.setdefault((prop, kw), e[kw])
    return found


MSG = {"minimum": "below minimum", "maximum": "above maximum", "maxLength": "longer than maxLength"}


def probe(kind, doc, tokens, prop, kw, val):
    base = tokens + [prop]
    path = join_ptr(base)
    _, comps = resolve_at(kind, tokens, doc)
    bad = {"minimum": val - 1, "maximum": val + 1, "maxLength": "a" * (int(val) + 1)}[kw]
    good = {"minimum": val, "maximum": val, "maxLength": "a" * int(val)}[kw]
    problems = []
    m = copy.deepcopy(doc)
    get_node(m, tokens)[prop] = bad
    hit = [e for e in errs_at(kind, m) if MSG[kw] in e[1] and (e[0] == path or e[0] in comps)]
    if not hit:
        problems.append(f"{kind} {path}: no '{MSG[kw]}' error for {bad!r}")
    m = copy.deepcopy(doc)
    get_node(m, tokens)[prop] = good
    if [e for e in errs_at(kind, m) if e[0] == path and MSG[kw] in e[1]]:
        problems.append(f"{kind} {path}: boundary value {good!r} wrongly rejected")
    return problems


def test_resolver_driven_numeric_and_length_boundaries():
    problems, checked = [], 0
    for kind, p, doc in cases():
        for tokens, _ in dict_nodes(doc):
            for (prop, kw), val in leaf_constraints(kind, tokens, doc).items():
                problems += probe(kind, doc, tokens, prop, kw, val)
                checked += 1
    assert checked > 0
    assert not problems, "\n".join(problems)


# ---------- pinned bounds (independent of the schema files; INTERFACES.md section 3 is normative) ----------

PINNED = [
    ("state", ["seq"], "minimum", 0), ("state", ["epoch"], "minimum", 1),
    ("state", ["closures_submitted"], "minimum", 0), ("state", ["hard_caps_tripped"], "minimum", 0),
    ("closure", ["seq"], "minimum", 1), ("verification", ["seq"], "minimum", 1), ("qualification", ["seq"], "minimum", 1),
    ("contract", ["seq"], "minimum", 1), ("contract", ["epoch"], "minimum", 1),
    ("meta", ["seq"], "minimum", 1), ("attempt", ["seq"], "minimum", 1),
    ("verification", ["exit_code"], "minimum", 0), ("verification", ["exit_code"], "maximum", 255),
] + [(k, [name], "minimum", 1) for k in ("sprint", "sprint-proposal")
     for name in ("min_attempts_before_block", "max_epochs")] \
  + [(k, ["max_attempts", r], "minimum", 1) for k in ("sprint", "sprint-proposal")
     for r in ("oracle", "implementer", "live", "curator")]


@pytest.mark.parametrize("kind,tokens,kw,val", PINNED, ids=[f"{k}:{'/'.join(t)}:{kw}" for k, t, kw, _ in PINNED])
def test_pinned_bounds(kind, tokens, kw, val):
    doc = doc_of(kind)
    path = join_ptr(tokens)
    bad = val - 1 if kw == "minimum" else val + 1
    m = copy.deepcopy(doc)
    set_path(m, tokens, bad)
    assert [e for e in errs_at(kind, m) if e[0] == path and MSG[kw] in e[1]], f"{kind} {path}={bad} not rejected"
    m = copy.deepcopy(doc)
    set_path(m, tokens, val)
    assert not [e for e in errs_at(kind, m) if e[0] == path and MSG[kw] in e[1]], f"{kind} {path}={val} rejected"


@pytest.mark.parametrize("kind", ["ev", "qual"])
def test_old_kind_names_rejected_as_schemas(kind):
    with pytest.raises(ValueError):
        schemas.validate(kind, {})


# ---------- static lints over the raw schema files ----------

def all_nodes(obj, path=()):
    if isinstance(obj, dict):
        yield path, obj
        for k, v in obj.items():
            yield from all_nodes(v, path + (k,))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from all_nodes(v, path + (str(i),))


def test_lint_no_additional_properties_true():
    bad = []
    for f in sorted(SCHEMA_DIR.glob("*.json")):
        for path, node in all_nodes(jload(f.name)):
            if node.get("additionalProperties") is True:
                bad.append(f"{f.name}:/{'/'.join(path)}")
    assert not bad, bad


def test_lint_one_minimum_names():
    bad = []
    for f in sorted(SCHEMA_DIR.glob("*.json")):
        for path, node in all_nodes(jload(f.name)):
            props = node.get("properties")
            if not isinstance(props, dict):
                continue
            for name, sub in props.items():
                if not isinstance(sub, dict) or "minimum" not in sub:
                    continue
                state_seq = f.name == "state.json" and name == "seq" and path == ()
                in_max_attempts = bool(path) and path[-1] == "max_attempts"
                if (name in {"seq", "epoch", "max_epochs", "min_attempts_before_block"} and not state_seq) \
                        or in_max_attempts:
                    if sub["minimum"] != 1:
                        bad.append(f"{f.name}:/{'/'.join(path)}/{name} minimum={sub['minimum']}")
    assert not bad, bad
