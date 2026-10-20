# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-07 / S0-R6: canonical hashing against independently computed vectors (vectors/hashing.json, spot-checked with sha256sum)."""
import json
import os
import shutil
import subprocess

import pytest

from helpers import *  # noqa

VEC = json.loads((GOLDEN / "vectors" / "hashing.json").read_text())


def _h():
    return need("actl.hashing")


def test_vector_inventory_has_at_least_six():
    n = len(VEC["file_sha256"]) + len(VEC["canonical_json"]) + 1
    assert n >= 6, "FAIL: fewer than six vectors"


@pytest.mark.parametrize("v", VEC["file_sha256"], ids=lambda v: v["name"])
def test_file_sha256_vectors_and_sha256sum_agree(tmp_path, v):
    h = _h(); p = tmp_path / "f"; p.write_bytes(bytes.fromhex(v["hex"]))
    got = need_attr(h, "file_sha256")(p)
    if got != v["sha256"]: fail("file_sha256(%s) = %s, vector %s" % (v["name"], got, v["sha256"]))
    if need_attr(h, "file_sha256")(str(p)) != got: fail("str and Path inputs must agree")
    if shutil.which("sha256sum"):
        ref = subprocess.run(["sha256sum", str(p)], capture_output=True, text=True).stdout.split()[0]
        if ref != got: fail("file_sha256 disagrees with sha256sum")
    if got != got.lower() or len(got) != 64: fail("digest must be 64 lowercase hex chars")


@pytest.mark.parametrize("v", VEC["canonical_json"], ids=lambda v: v["name"])
def test_canonical_json_vectors(v):
    h = _h(); b = need_attr(h, "canonical_json")(v["obj"])
    if not isinstance(b, bytes): fail("canonical_json must return bytes")
    if b.hex() != v["canonical_utf8_hex"]: fail("canonical_json(%s) = %r" % (v["name"], b))
    if need_attr(h, "json_sha256")(v["obj"]) != v["sha256"]: fail("json_sha256(%s) wrong" % v["name"])


def test_canonical_json_errors():
    h = _h(); cj = need_attr(h, "canonical_json")
    for bad in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(ValueError): cj({"x": bad})
    with pytest.raises(TypeError): cj({1: "a"})
    with pytest.raises(ValueError): cj({"x": "\ud800"})
    with pytest.raises(TypeError): cj({"x": object()})
    with pytest.raises((ValueError, TypeError)): need_attr(h, "json_sha256")({"x": float("nan")})


def _mk(root, files):
    for f in files:
        p = root / f["path"]; p.parent.mkdir(parents=True, exist_ok=True); p.write_bytes(f["content"].encode("utf-8"))
        p.chmod(0o755 if f["exec"] else 0o644)


def test_manifest_vector_exec_bit_empty_dirs_and_symlinks(tmp_path):
    h = _h(); m = need_attr(h, "manifest_sha256"); fs = need_attr(h, "file_sha256")
    root = tmp_path / "t"; _mk(root, VEC["manifest"]["files"])
    got = m(root)
    if got != VEC["manifest"]["sha256"]: fail("manifest_sha256 = %s, vector %s" % (got, VEC["manifest"]["sha256"]))
    (root / "emptydir").mkdir()
    if m(root) != got: fail("empty directories must be ignored")
    os.chmod(root / "a.b", 0o644)
    changed = m(root)
    if changed == got: fail("changing only the exec bit must change the manifest hash")
    if changed != VEC["manifest"]["sha256_if_no_exec_bits"]: fail("manifest without exec bits must equal the second vector")
    os.chmod(root / "a.b", 0o755)
    if m(root) != got: fail("restoring the exec bit must restore the hash")
    os.chmod(root / "a.b", 0o700)
    if m(root) != got: fail("any of the 0o111 bits counts as exec")
    os.chmod(root / "a.b", 0o755)
    os.symlink("a/b", root / "link")
    with pytest.raises(ValueError): m(root)
    with pytest.raises(ValueError): fs(root / "link")
    os.unlink(root / "link")
    os.mkfifo(root / "fifo")
    with pytest.raises(ValueError): m(root)
    os.unlink(root / "fifo")
    os.symlink(root, tmp_path / "dirlink")
    with pytest.raises(ValueError): m(tmp_path / "dirlink")
    with pytest.raises(FileNotFoundError): m(tmp_path / "absent")
    with pytest.raises(FileNotFoundError): fs(tmp_path / "absent")
    with pytest.raises(ValueError): fs(root)


def test_manifest_text_hex_documents_the_line_format():
    txt = bytes.fromhex(VEC["manifest"]["manifest_text_hex"])
    lines = txt.split(b"\n")[:-1]
    assert all(l.count(b"\0") == 2 for l in lines), "FAIL: vector malformed"
    assert [l.split(b"\0")[0] for l in lines] == sorted(l.split(b"\0")[0] for l in lines), "FAIL: vector not bytewise sorted"
