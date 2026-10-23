# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2, proof text only; not executed.
import hashlib
import os
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for _p in (REPO / "src", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from actl import ids  # noqa: E402

TAG = "2026-10-16_public-profiles"


def h4(tag):
    return hashlib.sha256(tag.encode("utf-8")).hexdigest()[:4]


def test_format_session_name_with_tag_shape():
    n = ids.format_session_name("impl", "demo", 7, TAG)
    assert n == f"impl-demo-{h4(TAG)}-007"
    assert len(n) <= 41
    assert ids.validate_session_name(n) is True


def test_format_session_name_without_tag_shape():
    n = ids.format_session_name("impl", "demo", 7)
    assert n == "impl-demo-007"
    assert ids.validate_session_name(n) is True


def test_seq_wider_than_three_digits():
    n = ids.format_session_name("impl", "demo", 1234)
    assert n == "impl-demo-1234"
    s = ids.format_session_name("impl", "a" * 40, 1234)
    assert s == "impl-" + "a" * 31 + "-1234"
    assert len(s) == 41 and ids.validate_session_name(s)


def test_trimming_40_char_slug_with_tag_is_exactly_41():
    n = ids.format_session_name("impl", "a" * 40, 1, TAG)
    assert n == "impl-" + "a" * 27 + f"-{h4(TAG)}-001"
    assert len(n) == 41
    assert ids.validate_session_name(n)


def test_trimming_41_char_slug_with_tag():
    n = ids.format_session_name("impl", "b" * 41, 1, TAG)
    assert n == "impl-" + "b" * 27 + f"-{h4(TAG)}-001"
    assert len(n) == 41


def test_trimming_40_char_slug_without_tag_is_exactly_41():
    n = ids.format_session_name("impl", "a" * 40, 1)
    assert n == "impl-" + "a" * 32 + "-001"
    assert len(n) == 41
    assert ids.validate_session_name(n)


def test_trimming_strips_trailing_hyphen():
    slug = "a" * 26 + "-" + "b" * 13
    assert ids.validate_slug(slug) and len(slug) == 40
    n = ids.format_session_name("impl", slug, 1, TAG)
    assert n == "impl-" + "a" * 26 + f"-{h4(TAG)}-001"
    assert "--" not in n


def test_max_slug_one_allowed_with_tag():
    prefix = "p" * 30
    n = ids.format_session_name(prefix, "abc", 1, TAG)
    assert n == prefix + "-a" + f"-{h4(TAG)}-001"
    assert len(n) == 41 and ids.validate_session_name(n)


def test_max_slug_zero_rejected_with_tag():
    with pytest.raises(ValueError):
        ids.format_session_name("p" * 31, "abc", 1, TAG)


def test_max_slug_one_allowed_without_tag():
    prefix = "p" * 35
    n = ids.format_session_name(prefix, "abc", 1)
    assert n == prefix + "-a-001"
    assert len(n) == 41 and ids.validate_session_name(n)


def test_max_slug_zero_rejected_without_tag():
    with pytest.raises(ValueError):
        ids.format_session_name("p" * 36, "abc", 1)


def test_prefix_longer_than_budget_rejected():
    with pytest.raises(ValueError):
        ids.format_session_name("p" * 41, "abc", 1)


@pytest.mark.parametrize("prefix", ["", "Impl", "-impl", "im_pl", "x" * 42, "im pl", "impl\n"])
def test_invalid_prefix(prefix):
    with pytest.raises(ValueError):
        ids.format_session_name(prefix, "demo", 1)


@pytest.mark.parametrize("slug", ["", "a", "-ab", "AB", "a_b", "a" * 42, "ab\n", "\u00e4b"])
def test_invalid_slug(slug):
    with pytest.raises(ValueError):
        ids.format_session_name("impl", slug, 1)


@pytest.mark.parametrize("seq", [0, -1, True, False, "1", 1.0, None])
def test_invalid_seq(seq):
    with pytest.raises(ValueError):
        ids.format_session_name("impl", "demo", seq)


@pytest.mark.parametrize("tag", ["", "bad", "2026-02-30_abc", "2026-13-01_abc", "2026-10-16_a",
                                 TAG + "\n", 123, b"2026-10-16_abc"])
def test_invalid_tag(tag):
    with pytest.raises(ValueError):
        ids.format_session_name("impl", "demo", 1, tag)


@pytest.mark.parametrize("bad", [None, 20261016, b"2026-10-16_abc", ["2026-10-16_abc"], {"t": 1}, 1.5, True])
def test_validate_sprint_tag_false_for_non_str(bad):
    assert ids.validate_sprint_tag(bad) is False


@pytest.mark.parametrize("tag", ["2026-02-30_abc", "2026-13-01_abc", "2026-00-10_abc", "2026-02-29_abc",
                                 "2026-04-31_abc"])
def test_validate_sprint_tag_false_for_impossible_dates(tag):
    assert ids.validate_sprint_tag(tag) is False


@pytest.mark.parametrize("tag", ["", "nodate_abc", "2026-10-16_", "2026-10-16_a", "2026-10-16_-ab",
                                 "2026-10-16_Ab", TAG + "\n", "2026-10-16abc"])
def test_validate_sprint_tag_false_for_pattern_mismatch(tag):
    assert ids.validate_sprint_tag(tag) is False


@pytest.mark.parametrize("tag", [TAG, "2028-02-29_leap", "2026-10-16_" + "a" * 41])
def test_validate_sprint_tag_true(tag):
    assert ids.validate_sprint_tag(tag) is True


def test_validate_session_name_bounds():
    assert ids.validate_session_name("a" * 41) is True
    assert ids.validate_session_name("a" * 42) is False
    assert ids.validate_session_name("") is False
    assert ids.validate_session_name("-a") is False
    assert ids.validate_session_name(None) is False
