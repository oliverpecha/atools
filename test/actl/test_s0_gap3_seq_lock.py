"""S37-07: seq.state_lock re-entrancy (seq.py:94 `depth -= 1` -> `-= 2`)."""
import fcntl
import os

import pytest

from actl import seq
from actl.layout import Layout

TAG = "2026-01-02_lock-demo"


@pytest.fixture
def env(tmp_path):
    lay = Layout(tmp_path / "g")
    lay.ensure_sprint_tree(TAG)
    path = lay.state_lock(TAG)
    yield lay, path
    assert str(path) not in seq._locks()


def _probe(path):
    fd = os.open(str(path), os.O_RDWR)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return True
    else:
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def _assert_held(path):
    assert _probe(path) is True, "lock should still be held"


def _assert_free(path):
    assert _probe(path) is False, "lock should be free"


def test_nested_inner_exit_keeps_outer_lock(env):
    lay, path = env
    with seq.state_lock(lay, TAG):
        _assert_held(path)
        with seq.state_lock(lay, TAG):
            _assert_held(path)
        _assert_held(path)
    _assert_free(path)


def test_three_levels_deep(env):
    lay, path = env
    with seq.state_lock(lay, TAG):
        with seq.state_lock(lay, TAG):
            with seq.state_lock(lay, TAG):
                _assert_held(path)
            _assert_held(path)
        _assert_held(path)
    _assert_free(path)


def test_exception_in_inner_block_does_not_release_outer(env):
    lay, path = env
    with seq.state_lock(lay, TAG):
        with pytest.raises(RuntimeError):
            with seq.state_lock(lay, TAG):
                raise RuntimeError("inner")
        _assert_held(path)
    _assert_free(path)


def test_exception_propagating_through_all_levels_releases(env):
    lay, path = env
    with pytest.raises(RuntimeError):
        with seq.state_lock(lay, TAG):
            with seq.state_lock(lay, TAG):
                with seq.state_lock(lay, TAG):
                    raise RuntimeError("deep")
    _assert_free(path)


def test_lock_is_reacquirable_after_full_release(env):
    lay, path = env
    for _ in range(2):
        with seq.state_lock(lay, TAG):
            with seq.state_lock(lay, TAG):
                _assert_held(path)
        _assert_free(path)
