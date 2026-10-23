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

from actl import hashing  # noqa: E402


@pytest.mark.parametrize("ch", ["\ud800", "\udbff", "\udc00", "\udfff"])
def test_lone_surrogates_rejected_by_validator_not_by_encoder(ch):
    # U+DFFF would still fail at .encode() with UnicodeEncodeError (a ValueError subclass),
    # so the contract "ValueError before UTF-8 encoding" is asserted via type and message.
    for obj in (ch, "x" + ch, [ch], {"k": ch}, {"a": [{"b": ch}]}):
        with pytest.raises(ValueError) as ei:
            hashing.canonical_json(obj)
        assert not isinstance(ei.value, UnicodeError), repr(obj)
        assert "urrogate" in str(ei.value)
    with pytest.raises(ValueError) as ei:
        hashing.json_sha256([ch])
    assert not isinstance(ei.value, UnicodeError)


@pytest.mark.parametrize("ch", ["\ud7ff", "\ue000", "\uffff", "\U0010ffff"])
def test_neighbours_of_surrogate_range_accepted(ch):
    assert hashing.canonical_json(ch) == b'"' + ch.encode("utf-8") + b'"'
    assert hashing.canonical_json({"k": [ch]}) == b'{"k":["' + ch.encode("utf-8") + b'"]}'


def test_manifest_sorted_bytewise_with_prefix_paths(tmp_path):
    d = tmp_path / "m"
    files = {"a-b": b"1", "a.b": b"2", "a/b": b"3", "a0": b"4"}
    for rel, data in files.items():
        p = d / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        os.chmod(p, 0o644)
    lines = b"".join(
        ("%s\0-\0%s\n" % (rel, hashlib.sha256(files[rel]).hexdigest())).encode("utf-8")
        for rel in sorted(files, key=lambda r: r.encode("utf-8"))
    )
    assert hashing.manifest_sha256(d) == hashlib.sha256(lines).hexdigest()
