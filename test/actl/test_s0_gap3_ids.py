"""S37-03: ids.mint_sprint_tag explicit-date branch (ids.py:42, `not` deleted)."""
from datetime import date

import pytest

from actl import ids


@pytest.mark.parametrize("with_env", [False, True])
def test_explicit_valid_date_is_used(monkeypatch, with_env):
    if with_env:
        monkeypatch.setenv("ACTL_TODAY", "1999-09-09")
    else:
        monkeypatch.delenv("ACTL_TODAY", raising=False)
    tag = ids.mint_sprint_tag("demo", date(2026, 1, 2))
    assert tag == "2026-01-02_demo"
    assert ids.validate_sprint_tag(tag)


@pytest.mark.parametrize("with_env", [False, True])
@pytest.mark.parametrize(
    "bad", ["2026-01-02", 20260102, 0, "", 1.5, b"2026-01-02", (2026, 1, 2), [2026]]
)
def test_explicit_wrong_type_raises_value_error(monkeypatch, bad, with_env):
    if with_env:
        monkeypatch.setenv("ACTL_TODAY", "1999-09-09")
    else:
        monkeypatch.delenv("ACTL_TODAY", raising=False)
    with pytest.raises(ValueError, match="Invalid today"):
        ids.mint_sprint_tag("demo", bad)


def test_none_still_falls_back_to_env(monkeypatch):
    monkeypatch.setenv("ACTL_TODAY", "1999-09-09")
    assert ids.mint_sprint_tag("demo", None) == "1999-09-09_demo"
