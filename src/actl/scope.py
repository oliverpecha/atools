"""ALLOW/FROZEN scope rules parsing and matching."""
from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class ScopeRule:
    kind: str
    pattern: str
    is_literal: bool
    line_no: int


def _seg_match(p_seg: str, s_seg: str) -> bool:
    parts: list[str] = []
    i = 0
    while i < len(p_seg):
        if p_seg[i] == "*":
            parts.append("[^/]*")
            i += 1
        else:
            j = i
            while j < len(p_seg) and p_seg[j] != "*":
                j += 1
            parts.append(re.escape(p_seg[i:j]))
            i = j
    return re.fullmatch("".join(parts), s_seg) is not None


def _glob_match(pattern: str, path: str) -> bool:
    pat_segs = pattern.split("/")
    path_segs = path.split("/")

    def dp(i: int, j: int) -> bool:
        if i == len(pat_segs) and j == len(path_segs):
            return True
        if i == len(pat_segs):
            return False
        if pat_segs[i] == "**":
            # match 0 or more path segments
            if dp(i + 1, j):
                return True
            if j < len(path_segs) and dp(i, j + 1):
                return True
            return False
        if j == len(path_segs):
            return False
        if _seg_match(pat_segs[i], path_segs[j]):
            return dp(i + 1, j + 1)
        return False

    return dp(0, 0)


def _pattern_syntax_errors(pat: str) -> str | None:
    if "\x00" in pat or "\\" in pat or "#" in pat:
        return "illegal character"
    if pat.startswith("/") or pat.endswith("/") or "//" in pat:
        return "illegal slash placement"
    if any(c in pat for c in "?[]{}"):
        return "illegal metacharacter"
    for seg in pat.split("/"):
        if seg in (".", ".."):
            return "dot segment"
        if "**" in seg and seg != "**":
            return "partial **"
    return None


def parse(text: str) -> list[ScopeRule]:
    if not isinstance(text, str):
        raise ValueError("scope text must be a string")
    rules: list[ScopeRule] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        if line.strip() == "" or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^(ALLOW|FROZEN):\s+(\S.*)$", line)
        if not m:
            raise ValueError(f"Line {line_no}: invalid syntax")
        kind, pat = m.group(1), m.group(2)
        err = _pattern_syntax_errors(pat)
        if err:
            raise ValueError(f"Line {line_no}: invalid pattern ({err})")
        is_literal = "*" not in pat
        rules.append(ScopeRule(kind=kind, pattern=pat, is_literal=is_literal, line_no=line_no))
    return rules


def _match_unchecked(rules: list[ScopeRule], path: str) -> str:
    for r in rules:
        if r.kind == "ALLOW" and r.is_literal and r.pattern == path:
            return "allowed"
    for r in rules:
        if r.kind == "FROZEN" and _glob_match(r.pattern, path):
            return "frozen"
    for r in rules:
        if r.kind == "ALLOW" and not r.is_literal and _glob_match(r.pattern, path):
            return "allowed"
    return "denied"


def validate(rules: list[ScopeRule]) -> list[str]:
    errs: list[str] = []
    if not any(r.kind == "ALLOW" for r in rules):
        errs.append("at least one ALLOW rule required")
    if not any(r.kind == "FROZEN" and r.pattern == "test/**" for r in rules):
        errs.append('missing required FROZEN: test/**')
    literals: dict[str, str] = {}
    for r in rules:
        if r.is_literal:
            prev = literals.get(r.pattern)
            if prev is not None and prev != r.kind:
                errs.append(f"literal conflict on {r.pattern!r}")
            literals[r.pattern] = r.kind
        syn = _pattern_syntax_errors(r.pattern)
        if syn:
            errs.append(f"invalid pattern {r.pattern!r}: {syn}")
    allow_globs = [r for r in rules if r.kind == "ALLOW" and not r.is_literal]
    for probe in ("__root_probe__", "test/__probe__.py", "test/sub/__probe__.py"):
        if _match_unchecked(allow_globs, probe) == "allowed":
            errs.append(f"blanket ALLOW matches probe {probe!r}")
            break
    return errs


def match(rules: list[ScopeRule], path: str) -> str:
    if not isinstance(path, str) or path == "":
        raise ValueError("invalid path")
    if path.startswith("/") or path.endswith("/") or "//" in path:
        raise ValueError("invalid path")
    if "\\" in path or "\x00" in path:
        raise ValueError("invalid path")
    segs = path.split("/")
    if any(s in (".", "..") for s in segs):
        raise ValueError("invalid path")
    if validate(rules) != []:
        raise ValueError("Invalid scope ruleset")
    return _match_unchecked(rules, path)
