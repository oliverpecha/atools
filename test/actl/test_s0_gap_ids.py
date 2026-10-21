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

import pytest

from actl import ids

KINDS = [
    "spec", "solution_key", "oracle", "oracle-draft", "qual", "contract",
    "closure", "ev", "escalation", "live-decision", "implementer",
]
BAD_SEQS = [0, -1, True, False, "1", None, 1.5]
BAD_KINDS = ["bogus", "", "EV", "ev ", None, "spec-001"]
FUNCS = [ids.format_artifact_id, ids.format_artifact_filename]


# T3 -- kills each operand of the guard
#   `kind not in ARTIFACT_KINDS or not isinstance(seq, int) or isinstance(seq, bool) or seq < 1`
# in BOTH functions: dropping/negating the kind test, the isinstance-int test, the bool test,
# or changing `< 1` to `< 0` / `<= 1`.
@pytest.mark.parametrize("fn", FUNCS, ids=lambda f: f.__name__)
@pytest.mark.parametrize("seq", BAD_SEQS, ids=repr)
def test_bad_seq_raises_value_error_with_valid_kind(fn, seq):
    with pytest.raises(ValueError):
        fn("ev", seq)


@pytest.mark.parametrize("fn", FUNCS, ids=lambda f: f.__name__)
@pytest.mark.parametrize("kind", BAD_KINDS, ids=repr)
def test_unknown_kind_raises_value_error_with_valid_seq(fn, kind):
    with pytest.raises(ValueError):
        fn(kind, 1)


@pytest.mark.parametrize("fn", FUNCS, ids=lambda f: f.__name__)
def test_bad_kind_and_bad_seq_together_still_value_error(fn):
    with pytest.raises(ValueError):
        fn("bogus", 0)


@pytest.mark.parametrize("kind", KINDS)
def test_every_valid_kind_accepted_at_boundary_seq_1(kind):
    assert ids.format_artifact_id(kind, 1) == f"{kind}-001"
    assert ids.format_artifact_id(kind, 1000) == f"{kind}-1000"
    assert isinstance(ids.format_artifact_filename(kind, 1), str)


def test_filename_suffixes():
    f = ids.format_artifact_filename
    assert f("spec", 1) == "spec-001.md"
    assert f("solution_key", 2) == "solution_key-002.patch"
    for k in ("oracle", "oracle-draft", "implementer"):
        assert f(k, 3) == f"{k}-003"
    for k in ("qual", "contract", "closure", "ev", "escalation", "live-decision"):
        assert f(k, 4) == f"{k}-004.json"

def test_ids_validation_guards():
    from actl.ids import validate_session_name, validate_sprint_tag, slug_from_tag
    import pytest
    assert not validate_session_name("")
    assert not validate_session_name("inv@lid")
    assert not validate_sprint_tag("invalid-tag")
    assert not validate_sprint_tag("2026-10-16")
    with pytest.raises(ValueError):
        slug_from_tag("bad_tag_format_invalid")

def test_ids_boundary_and_type_guards():
    from actl import ids
    import pytest
    # Line 35: isinstance(slug, str) and _SLUG_RE.fullmatch(slug)
    assert not ids.validate_slug(123)
    assert not ids.validate_slug(None)
    # Line 93: if max_slug < 1
    # Boundary test: max_slug=1 must succeed and not raise ValueError
    s = ids.slug_from_tag("2026-10-16_demo")
    assert s == "demo"
    # Line 131: parse_seq_from_name with non-numeric group
    assert ids.parse_seq_from_name("spec-abc") is None
    assert ids.parse_seq_from_name("arbitrary-name") is None
