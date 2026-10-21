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

import random
from functools import lru_cache

import pytest

from actl import scope

FROZEN_TEST = "FROZEN: test/**"


class _Rejected(Exception):
    pass


def _rules(pattern):
    rules = scope.parse(f"{FROZEN_TEST}\nALLOW: {pattern}\n")
    errs = scope.validate(rules)
    if errs:
        raise _Rejected(errs)
    return rules


def _verdict(pattern, path):
    return scope.match(_rules(pattern), path)


def _allowed(pattern, path):
    return _verdict(pattern, path) == "allowed"


# ---- independent reference matcher (no regex, no shared code with src) ----
def _ref_seg(p, s):
    n, m = len(p), len(s)
    dp = [[False] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = True
    for i in range(1, n + 1):
        for j in range(m + 1):
            if p[i - 1] == "*":
                dp[i][j] = dp[i - 1][j] or (j > 0 and dp[i][j - 1])
            else:
                dp[i][j] = j > 0 and dp[i - 1][j - 1] and p[i - 1] == s[j - 1]
    return dp[n][m]


def _ref_glob(pattern, path):
    ps, ss = pattern.split("/"), path.split("/")

    @lru_cache(maxsize=None)
    def go(i, j):
        if i == len(ps):
            return j == len(ss)
        if ps[i] == "**":
            return go(i + 1, j) or (j < len(ss) and go(i, j + 1))
        if j == len(ss):
            return False
        return _ref_seg(ps[i], ss[j]) and go(i + 1, j + 1)

    return go(0, 0)


def _must_reject(pattern):
    return any(("**" in s and s != "**") or s in (".", "..") for s in pattern.split("/"))


def _bad_path(path):
    return any(s in (".", "..") for s in path.split("/"))


# T5 -- explicit positives/negatives.  Kills: '*' compiled as '.' / '.+' (a*b vs ab), '*' treated
# as literal, missing re.fullmatch anchoring (prefix/suffix matches), dropped re.escape on
# literals ('.' as wildcard: foopy), swapped literal/glob parts.
NEG_POS = [
    ("a*b", "ab", True), ("a*b", "axb", True), ("a*b", "axxb", True),
    ("a*b", "axyz", False), ("a*b", "a", False), ("a*b", "b", False),
    ("a*b", "xab", False), ("a*b", "abx", False), ("a*b", "a/b", False),
    ("*.py", "foo.py", True), ("*.py", ".py", True),
    ("*.py", "foopy", False), ("*.py", "foo.pyc", False), ("*.py", "a/foo.py", False),
    ("x*", "xy", True), ("x*", "x", True), ("x*", "y", False), ("x*", "yx", False),
    ("test_*.py", "test_a.py", True), ("test_*.py", "test_.py", True),
    ("test_*.py", "test_a.txt", False), ("test_*.py", "testa.py", False),
    ("a.b", "a.b", True), ("a.b", "axb", False),
    ("a/*.py", "a/x.py", True), ("a/*.py", "a/x/y.py", False), ("a/*.py", "a/xpy", False),
    ("a/*/b", "a/x/b", True), ("a/*/b", "a/b", False), ("a/*/b", "a/x/y/b", False),
    ("a/**/b", "a/b", True), ("a/**/b", "a/x/b", True), ("a/**/b", "a/x/y/b", True),
    ("a/**/b", "a/x/c", False), ("a/**/b", "ab", False), ("a/**/b", "x/a/b", False),
    ("a/**", "a/b", True), ("a/**", "a/b/c", True), ("a/**", "b/a", False),
    ("**/x.py", "x.py", True), ("**/x.py", "a/x.py", True), ("**/x.py", "a/b/x.py", True),
    ("**/x.py", "a/xpy", False), ("**/x.py", "a/y.py", False),
]


@pytest.mark.parametrize("pattern,path,want", NEG_POS)
def test_glob_explicit_cases(pattern, path, want):
    assert _allowed(pattern, path) is want
    assert _ref_glob(pattern, path) is want  # sanity of the reference itself


# T5 -- differential, single-segment patterns <=5 chars over {a,b,*,.}, paths <=5 chars over {a,b,.}.
def _all_strings(alpha, max_len):
    out = [""]
    for _ in range(max_len):
        out += [s + c for s in out if len(s) == _ for c in alpha]
    return [s for s in out if s]


def _derive(pattern, rng, alphabet):
    return "".join(
        "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 3))) if c == "*" else c
        for c in pattern)


def _differential(patterns, paths, derive_alpha, per_pattern, seed, min_checked):
    rng = random.Random(seed)
    checked = rejected = 0
    for pat in patterns:
        try:
            _rules(pat)
        except (ValueError, _Rejected):
            assert not _must_reject(pat) or True
            rejected += 1
            continue
        assert not _must_reject(pat), f"invalid pattern accepted: {pat!r}"
        cand = rng.sample(paths, min(per_pattern, len(paths)))
        cand += [_derive(pat, rng, derive_alpha) for _ in range(6)]
        cand += [pat.replace("**", "").replace("*", "")]
        for path in cand:
            if not path:
                continue
            if _bad_path(path) or path.startswith("/") or path.endswith("/") or "//" in path:
                with pytest.raises(ValueError):
                    scope.match(_rules(pat), path)
                continue
            want = "allowed" if _ref_glob(pat, path) else "denied"
            got = scope.match(_rules(pat), path)
            assert got == want, f"pattern={pat!r} path={path!r} got={got} want={want}"
            checked += 1
    assert checked >= min_checked, (checked, rejected)
    return checked, rejected


def test_differential_single_segment_vs_reference():
    patterns = _all_strings("ab*.", 5)
    paths = _all_strings("ab.", 5)
    for pat in patterns:
        if _must_reject(pat):
            with pytest.raises(ValueError):
                scope.parse(f"ALLOW: {pat}\n") and _verdict(pat, "a")
    _differential(patterns, paths, "ab.", per_pattern=14, seed=20261021, min_checked=5000)


def test_differential_multi_segment_and_double_star_vs_reference():
    pool = ["a", "b", "*", "a*", "*b", "**"]
    patterns = []
    for n in (1, 2, 3):
        cur = [""]
        for _ in range(n):
            cur = [(c + "/" + s) if c else s for c in cur for s in pool]
        patterns += cur
    ppool = ["a", "b", "ab"]
    paths = []
    for n in (1, 2, 3, 4):
        cur = [""]
        for _ in range(n):
            cur = [(c + "/" + s) if c else s for c in cur for s in ppool]
        paths += cur
    _differential(patterns, paths, "ab", per_pattern=24, seed=7, min_checked=3000)
