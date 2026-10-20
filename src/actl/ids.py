"""Slug, sprint-tag, session-name, and artifact ID helpers."""
from __future__ import annotations

import hashlib
import os
import re
from datetime import date

ARTIFACT_KINDS = (
    "spec",
    "solution_key",
    "oracle",
    "oracle-draft",
    "qual",
    "contract",
    "closure",
    "ev",
    "escalation",
    "live-decision",
    "implementer",
)

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,40}\Z")
_TAG_RE = re.compile(r"^([0-9]{4}-[0-9]{2}-[0-9]{2})_([a-z0-9][a-z0-9-]{1,40})\Z")
_SESSION_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,40}\Z")
_PARSE_RE = re.compile(
    r"^(?:(spec)-([0-9]{3,})\.md|"
    r"(solution_key)-([0-9]{3,})\.patch|"
    r"(oracle|oracle-draft|implementer)-([0-9]{3,})|"
    r"(qual|contract|closure|ev|escalation|live-decision)-([0-9]{3,})\.json)\Z"
)


def validate_slug(slug: str) -> bool:
    return bool(isinstance(slug, str) and _SLUG_RE.fullmatch(slug))


def mint_sprint_tag(slug: str, today: date | None = None) -> str:
    if not validate_slug(slug):
        raise ValueError(f"Invalid slug: {slug!r}")
    if today is not None:
        if not isinstance(today, date):
            raise ValueError(f"Invalid today: {today!r}")
        resolved = today
    elif os.environ.get("ACTL_TODAY"):
        resolved = date.fromisoformat(os.environ["ACTL_TODAY"])
    else:
        resolved = date.today()
    return f"{resolved.isoformat()}_{slug}"


def validate_sprint_tag(tag: str) -> bool:
    if not isinstance(tag, str):
        return False
    m = _TAG_RE.fullmatch(tag)
    if not m:
        return False
    try:
        date.fromisoformat(m.group(1))
    except ValueError:
        return False
    return True


def slug_from_tag(tag: str) -> str:
    if not validate_sprint_tag(tag):
        raise ValueError(f"Invalid sprint tag: {tag!r}")
    return tag.split("_", 1)[1]


def validate_session_name(name: str) -> bool:
    return bool(isinstance(name, str) and _SESSION_RE.fullmatch(name))


def format_session_name(
    prefix: str, slug: str, seq: int, tag: str | None = None
) -> str:
    if not validate_session_name(prefix):
        raise ValueError(f"Invalid session prefix: {prefix!r}")
    if not validate_slug(slug):
        raise ValueError(f"Invalid slug: {slug!r}")
    if not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        raise ValueError(f"Invalid seq: {seq!r}")
    if tag is not None and not validate_sprint_tag(tag):
        raise ValueError(f"Invalid sprint tag: {tag!r}")
    seq_str = f"{seq:03d}"
    if tag is not None:
        h4 = hashlib.sha256(tag.encode("utf-8")).hexdigest()[:4]
        suffix = f"-{h4}-{seq_str}"
    else:
        suffix = f"-{seq_str}"
    max_slug = 41 - len(prefix) - 1 - len(suffix)
    if max_slug < 1:
        raise ValueError("Session name components too long")
    slug_trimmed = slug[:max_slug].rstrip("-")
    if not slug_trimmed:
        raise ValueError("Trimmed slug is empty")
    candidate = f"{prefix}-{slug_trimmed}{suffix}"
    if not validate_session_name(candidate):
        raise ValueError(f"Invalid session name: {candidate!r}")
    return candidate


def format_artifact_id(kind: str, seq: int) -> str:
    if kind not in ARTIFACT_KINDS or not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        raise ValueError(f"Invalid artifact kind/seq: {kind!r}, {seq!r}")
    return f"{kind}-{seq:03d}"


def format_artifact_filename(kind: str, seq: int) -> str:
    if kind not in ARTIFACT_KINDS or not isinstance(seq, int) or isinstance(seq, bool) or seq < 1:
        raise ValueError(f"Invalid artifact kind/seq: {kind!r}, {seq!r}")
    if kind == "spec":
        return f"spec-{seq:03d}.md"
    if kind == "solution_key":
        return f"solution_key-{seq:03d}.patch"
    if kind in ("oracle", "oracle-draft", "implementer"):
        return f"{kind}-{seq:03d}"
    if kind in ("qual", "contract", "closure", "ev", "escalation", "live-decision"):
        return f"{kind}-{seq:03d}.json"
    raise ValueError(f"Invalid artifact kind: {kind!r}")


def parse_seq_from_name(name: str) -> int | None:
    if not isinstance(name, str):
        return None
    m = _PARSE_RE.fullmatch(name)
    if not m:
        return None
    for g in m.groups():
        if g is not None and g.isdigit():
            return int(g)
    return None
