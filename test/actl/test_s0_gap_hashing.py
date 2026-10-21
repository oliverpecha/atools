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

import hashlib
import os

import pytest

from actl import hashing


# T1 -- kills: removal/inversion of the S_ISDIR guard in manifest_sha256 (regular file accepted),
# and any mutant that converts the lstat() FileNotFoundError into ValueError / swallows it.
def test_manifest_on_regular_file_raises_value_error(tmp_path):
    f = tmp_path / "plain.txt"
    f.write_text("x")
    with pytest.raises(ValueError):
        hashing.manifest_sha256(f)
    with pytest.raises(ValueError):
        hashing.manifest_sha256(str(f))


def test_manifest_missing_dir_raises_file_not_found_not_value_error(tmp_path):
    with pytest.raises(FileNotFoundError) as ei:
        hashing.manifest_sha256(tmp_path / "does-not-exist")
    assert not isinstance(ei.value, ValueError)


def test_manifest_symlink_to_dir_raises_value_error(tmp_path):
    real = tmp_path / "real"
    real.mkdir()
    (real / "a").write_text("a")
    link = tmp_path / "link"
    os.symlink(real, link)
    with pytest.raises(ValueError):
        hashing.manifest_sha256(link)
    assert len(hashing.manifest_sha256(real)) == 64


# T2 -- kills: sort_keys=True -> False, separators changed, ensure_ascii flipped,
# or sorting applied only at the top level.
def test_canonical_json_sorts_top_level_keys():
    assert hashing.canonical_json({"b": 1, "a": 2}) == b'{"a":2,"b":1}'
    assert hashing.canonical_json({"a": 2, "b": 1}) == b'{"a":2,"b":1}'


def test_canonical_json_sorts_nested_dicts_and_dicts_in_lists():
    obj = {"z": {"y": 1, "x": {"d": 4, "c": 3}}, "a": [{"q": 1, "p": 2}], "m": 0}
    expected = b'{"a":[{"p":2,"q":1}],"m":0,"z":{"x":{"c":3,"d":4},"y":1}}'
    assert hashing.canonical_json(obj) == expected


def test_canonical_json_is_compact_and_utf8_not_escaped():
    out = hashing.canonical_json({"k": "\u00e9", "l": [1, 2]})
    assert out == '{"k":"\u00e9","l":[1,2]}'.encode("utf-8")


def test_json_sha256_matches_digest_of_canonical_bytes():
    expected = hashlib.sha256(b'{"a":2,"b":1}').hexdigest()
    assert hashing.json_sha256({"b": 1, "a": 2}) == expected
