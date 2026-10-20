# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-12 / S0-R12: scope.py parser, validator, matcher (>= 15 glob cases)."""
import itertools

import pytest

from helpers import *  # noqa

R0 = "FROZEN: test/**\nALLOW: api/profile.py\nALLOW: api/users.py\n"
THAW = R0 + "ALLOW: test/test_users.py\n"
STAR = "FROZEN: test/**\nALLOW: api/*.py\n"
MID = "FROZEN: test/**\nALLOW: src/**/gen.py\n"
NEST = "FROZEN: test/**\nALLOW: api/**\nFROZEN: api/secret/**\n"
NEST_THAW = NEST + "ALLOW: api/secret/key.txt\n"
MATCH = [
    (R0, "api/profile.py", "allowed"), (R0, "api/users.py", "allowed"), (R0, "api/cli.py", "denied"),
    (R0, "test/test_users.py", "frozen"), (R0, "test/sub/deep/x.py", "frozen"), (R0, "README.md", "denied"),
    (R0, "api/profile.py.bak", "denied"), (R0, "xapi/profile.py", "denied"),
    (THAW, "test/test_users.py", "allowed"), (THAW, "test/other.py", "frozen"),
    (STAR, "api/x.py", "allowed"), (STAR, "api/sub/x.py", "denied"), (STAR, "api/.hidden.py", "allowed"), (STAR, "api/x.txt", "denied"),
    (MID, "src/gen.py", "allowed"), (MID, "src/a/b/gen.py", "allowed"), (MID, "src/a/gen.pyc", "denied"), (MID, "gen.py", "denied"),
    (NEST, "api/secret/k", "frozen"), (NEST, "api/ok/k", "allowed"), (NEST, "api/top.py", "allowed"),
    (NEST_THAW, "api/secret/key.txt", "allowed"), (NEST_THAW, "api/secret/other", "frozen"),
]
INVALID_RULESETS = [
    "ALLOW: **\nFROZEN: test/**\n", "ALLOW: test/**\nFROZEN: test/**\n", "ALLOW: **/*\nFROZEN: test/**\n", "ALLOW: */**\nFROZEN: test/**\n",
    "ALLOW: **/*.py\nFROZEN: test/**\n", "ALLOW: *\nFROZEN: test/**\n", "ALLOW: api/profile.py\n", "FROZEN: test/**\n",
    "ALLOW: a.py\nFROZEN: a.py\nFROZEN: test/**\n", "",
]
PARSE_ERRORS = ["ALLOW /x", "ALLOW api/x.py", "DENY: x", "ALLOW:", "ALLOW: /abs", "ALLOW: a//b", "ALLOW: a/./b", "ALLOW: ./a", "ALLOW: ../x", "ALLOW: a/..",
                "ALLOW: a\\b", "ALLOW: a # c", "ALLOW: a?b", "ALLOW: a[1]", "ALLOW: a{b}", "ALLOW: a**b", "ALLOW: a/", "ALLOW: a\x00b", "allow: a"]


def _s():
    return need("actl.scope")


@pytest.mark.parametrize("rules,path,want", MATCH)
def test_match_table(rules, path, want):
    s = _s(); rs = s.parse(rules)
    if s.validate(rs) != []: fail("ruleset should be valid: %r -> %s" % (rules, s.validate(rs)))
    got = s.match(rs, path)
    if got != want: fail("match(%r, %r) = %r, expected %r" % (rules, path, got, want))


def test_match_is_independent_of_rule_order():
    s = _s(); lines = NEST_THAW.strip().split("\n")
    paths = ["api/secret/key.txt", "api/secret/other", "api/ok/k", "test/a.py", "zzz"]
    ref = None
    for perm in itertools.permutations(lines):
        rs = s.parse("\n".join(perm) + "\n")
        res = [s.match(rs, p) for p in paths]
        ref = ref or res
        if res != ref: fail("rule order changed results: %s vs %s" % (res, ref))
    if ref != ["allowed", "frozen", "allowed", "frozen", "denied"]: fail("unexpected reference results %s" % ref)


def test_parse_structure_comments_and_whitespace():
    s = _s(); rs = s.parse("# c\n\nALLOW: a.py   \n  \nFROZEN: test/**\t\nALLOW: x/*.py\n")
    got = [(r.kind, r.pattern, r.is_literal, r.line_no) for r in rs]
    if got != [("ALLOW", "a.py", True, 3), ("FROZEN", "test/**", False, 5), ("ALLOW", "x/*.py", False, 6)]: fail("parse result wrong: %s" % got)
    if s.parse("") != [] or s.parse("# only\n\n") != []: fail("empty/comment-only text must parse to []")


@pytest.mark.parametrize("text", PARSE_ERRORS)
def test_parse_rejects(text):
    with pytest.raises(ValueError): _s().parse(text + "\n")


@pytest.mark.parametrize("text", INVALID_RULESETS)
def test_validate_rejects(text):
    s = _s(); errs = s.validate(s.parse(text))
    if not errs or not all(isinstance(e, str) and e for e in errs): fail("validate must report a non-empty list of strings for %r, got %r" % (text, errs))


@pytest.mark.parametrize("text", [R0, THAW, NEST, "FROZEN: test/**\nALLOW: api/**\n"])
def test_validate_accepts(text):
    s = _s()
    if s.validate(s.parse(text)) != []: fail("valid ruleset rejected: %r -> %s" % (text, s.validate(s.parse(text))))


@pytest.mark.parametrize("path", ["", "/abs", "../x", "a/../b", "a\\b", "a\x00b", "a//b", "./a"])
def test_match_rejects_bad_paths(path):
    s = _s(); rs = s.parse(R0)
    with pytest.raises(ValueError): s.match(rs, path)


def test_match_refuses_invalid_rules():
    s = _s()
    with pytest.raises(ValueError): s.match(s.parse("ALLOW: **\nFROZEN: test/**\n"), "a.py")


def test_deleted_frozen_file_is_still_frozen():
    s = _s()
    if s.match(s.parse(R0), "test/test_users.py") != "frozen": fail("path-based match must treat a deleted frozen file as frozen")
