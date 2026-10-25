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

import json
import re

import pytest

REPO = _REPO
SCHEMAS = REPO / "schemas"


# ---------- INTERFACES.md section 3 ----------
def _interfaces_text():
    for cand in (REPO / "src" / "actl" / "INTERFACES.md", REPO / "INTERFACES.md"):
        if cand.is_file():
            return cand.read_text(encoding="utf-8")
    for p in sorted(REPO.rglob("INTERFACES.md")):
        if ".git" not in p.parts and "node_modules" not in p.parts:
            return p.read_text(encoding="utf-8")
    pytest.fail("INTERFACES.md not found in the repository")


def _section3():
    text = _interfaces_text()
    start = re.search(r"^#{1,6}\s+3\.?\s", text, re.M)
    assert start, "no '3.' heading in INTERFACES.md"
    end = re.compile(r"^#{1,6}\s+4\.?\s", re.M).search(text, start.end())
    return text[start.start(): end.start() if end else len(text)]


SECTION3 = None


def _lines():
    global SECTION3
    if SECTION3 is None:
        SECTION3 = _section3().splitlines()
    return SECTION3


def _windows(prop):
    rx = re.compile(r"(?<![A-Za-z0-9_])" + re.escape(prop) + r"(?![A-Za-z0-9_])")
    ls = _lines()
    return ["\n".join(ls[i:i + 2]) for i, l in enumerate(ls) if rx.search(l)]


def _has_token(window, value):
    return re.search(r"(?<![A-Za-z0-9_-])" + re.escape(value) + r"(?![A-Za-z0-9_-])", window) is not None


# ---------- schema walking ($ref / allOf / anyOf / oneOf / items aware) ----------
def _load(name):
    return json.loads((SCHEMAS / f"{name}.json").read_text(encoding="utf-8"))


def _follow(ref, name, doc):
    file_part, _, frag = ref.partition("#")
    if file_part:
        name = file_part.rsplit("/", 1)[-1].removesuffix(".json")
        doc = _load(name)
    node = doc
    for tok in [t.replace("~1", "/").replace("~0", "~") for t in frag.split("/") if t]:
        node = node[tok]
    return node, name, doc


def _norm(ctx):
    node, name, doc = ctx
    while isinstance(node, dict) and "$ref" in node:
        node, name, doc = _follow(node["$ref"], name, doc)
    return node, name, doc


def _subs(ctx):
    node, name, doc = _norm(ctx)
    out = [(node, name, doc)]
    if not isinstance(node, dict):
        return out
    for kw in ("allOf", "anyOf", "oneOf"):
        for s in node.get(kw, []):
            out += _subs((s, name, doc))
    if isinstance(node.get("items"), dict):
        out += _subs((node["items"], name, doc))
    return out


def _prop(schema_name, dotted):
    doc = _load(schema_name)
    ctx = (doc, schema_name, doc)
    for key in dotted.split("."):
        for node, nm, d in _subs(ctx):
            props = node.get("properties", {}) if isinstance(node, dict) else {}
            if key in props:
                ctx = _norm((props[key], nm, d))
                break
        else:
            pytest.fail(f"schemas/{schema_name}.json has no property {dotted!r} (missing {key!r})")
    return ctx


def _collect(ctx, kw):
    return [n[kw] for n, _, _ in _subs(ctx) if isinstance(n, dict) and kw in n]


def _norm_tok(v):
    return re.sub(r"[^a-z0-9]", "", str(v).lower())


# ---------- curated table: (schema, dotted property, expected enum members) ----------
ENUMS = [
    ("sprint", "owner_review_triggers",
     {"grantattempts", "waivemutant", "updatescope", "reopenoracle", "retrylive"}),
    ("sprint", "status", {"draft", "frozen"}),
    ("state", "status", {"draft", "running", "hold", "done", "aborted"}),
    ("state", "active_stage", {"intake", "oracle", "implementer", "live", "curator", "closeout"}),
    ("verification", "stage", {"guards", "offline", "live", "blockedcheck"}),
    ("verification", "halt.reason",
     {"integritymismatch", "selftestfailed", "wrapperrejected", "unsupportedcap", "architectunavailable"}),
    ("qualification", "diagnostic_case", {"none", "pureoraclefailure", "solutionkeyconflict"}),
    ("closure", "reason", {"done", "blocked"}),
]


@pytest.mark.parametrize("schema,prop,expected", ENUMS, ids=lambda x: x if isinstance(x, str) else "")
def test_enum_schema_and_section3_agree(schema, prop, expected):
    ctx = _prop(schema, prop)
    members = [m for lst in _collect(ctx, "enum") for m in lst if m is not None]
    assert members, f"{schema}.{prop} has no enum"
    assert {_norm_tok(m) for m in members} == expected, (schema, prop, sorted(map(str, members)))
    leaf = prop.split(".")[-1]
    wins = _windows(leaf)
    assert wins, f"section 3 never mentions {leaf!r}"
    assert any(all(_has_token(w, str(m)) for m in members) for w in wins), (
        f"no section-3 line for {leaf!r} lists exactly the schema members {sorted(map(str, members))}")


# ---------- numeric bounds ----------
def _num(ctx, kw):
    vals = _collect(ctx, kw)
    return vals[0] if vals else None


def _eff_min(ctx):
    lo = _num(ctx, "minimum")
    ex = _num(ctx, "exclusiveMinimum")
    return lo if ex is None else (ex + 1 if lo is None else max(lo, ex + 1))


NUMERIC = [
    ("verification", "exit_code", 0, 255),
    ("state", "seq", 0, None),
    ("state", "epoch", 1, None),
    ("contract", "seq", 1, None),
    ("sprint", "min_attempts_before_block", 1, None),
    ("sprint", "max_epochs", 1, None),
]


@pytest.mark.parametrize("schema,prop,lo,hi", NUMERIC, ids=lambda x: x if isinstance(x, str) else "")
def test_numeric_bounds_schema_and_section3_agree(schema, prop, lo, hi):
    ctx = _prop(schema, prop)
    types = {t for ts in _collect(ctx, "type") for t in (ts if isinstance(ts, list) else [ts])}
    assert "integer" in types, (schema, prop, types)
    assert _eff_min(ctx) == lo, (schema, prop, "minimum")
    got_hi = _num(ctx, "maximum")
    assert got_hi == hi, (schema, prop, "maximum")
    wins = _windows(prop)
    assert wins, f"section 3 never mentions {prop!r}"
    if hi is not None:
        assert any(re.search(r"(?<!\d)%d(?!\d)" % hi, w) and re.search(r"(?<!\d)%d(?!\d)" % lo, w)
                   for w in wins), f"section 3 bounds for {prop!r} differ from schema {lo}..{hi}"
    else:
        assert any(re.search(r"(?<!\d)%d(?!\d)" % lo, w) for w in wins)


def test_ev_exit_code_is_nullable():
    types = {t for ts in _collect(_prop("verification", "exit_code"), "type") for t in (ts if isinstance(ts, list) else [ts])}
    assert "null" in types or any(
        isinstance(n, dict) and n.get("type") == "null" for n, _, _ in _subs(_prop("verification", "exit_code")))


# ---------- sha patterns ----------
SHAS = [
    ("verification", "head", 40), ("qualification", "base_sha", 40), ("contract", "base_sha", 40), ("sprint", "base_sha", 40),
    ("qualification", "manifest_sha256", 64), ("meta", "sha256", 64),
]


def _hex(n):
    return ("0123456789abcdef" * 8)[:n]


@pytest.mark.parametrize("schema,prop,n", SHAS, ids=lambda x: x if isinstance(x, str) else "")
def test_sha_pattern_schema_and_section3_agree(schema, prop, n):
    ctx = _prop(schema, prop)
    pats = _collect(ctx, "pattern")
    assert pats, f"{schema}.{prop} has no pattern"
    pat = pats[0]
    assert pat.startswith("^") and (pat.endswith("$") or pat.endswith(r"\Z")), f"pattern must be anchored: {pat!r}"
    rx = re.compile(pat)
    assert rx.search(_hex(n))
    for bad in (_hex(n - 1), _hex(n + 1), _hex(n).upper(), "g" * n, "x" + _hex(n), _hex(n) + "x", ""):
        assert not rx.search(bad), (pat, bad)
    leaf = prop.split(".")[-1]
    wins = _windows(leaf)
    assert any(re.search(r"\{%d\}" % n, w) and "0-9a-f" in w for w in wins), (
        f"section 3 has no line for {leaf!r} with a [0-9a-f]{{{n}}} pattern")
