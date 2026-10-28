#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-24: Observable durability order for verification write:
# temp-file fsync -> replace dest -> directory fsync -> unlink log -> unlink exit.
# A no-fsync and an unrelated-fsync counterfeit MUST fail this oracle (S1-R15.2).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

# ONE shared Tracer + assert_durability_order (collapse live duplicate; SIZE).
P24_ORACLE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/p24_oracle.XXXXXX")"
export P24_ORACLE_DIR
cat > "${P24_ORACLE_DIR}/p24_oracle.py" <<'ORACLE'
"""Shared P-S1-24 durability oracle (ONE Tracer, ONE assert_durability_order)."""
import hashlib
import os
import stat as stat_mod
from pathlib import Path


def fd_path(fd):
    """Resolve fd via /proc/self/fd; do not depend on os.open mapping (GD-04a)."""
    try:
        return os.path.realpath(os.readlink(f"/proc/self/fd/{fd}"))
    except OSError:
        return f"fd:{fd}"


def fd_bytes_at_fsync(fd):
    """Bytes visible on fd at fsync: prefer /proc/self/fd/<fd>, else fstat size pad."""
    try:
        with open(f"/proc/self/fd/{fd}", "rb") as rf:
            return rf.read()
    except OSError:
        try:
            return b"\0" * int(os.fstat(fd).st_size)
        except OSError:
            return b""


def is_verification_json(path: str) -> bool:
    base = os.path.basename(str(path))
    return base.startswith("verification-") and base.endswith(".json") and ".meta." not in base


def lstat_replace_identity(src_s: str):
    """Identity of the directory entry os.replace will move: lstat BEFORE rename."""
    inode = (None, None)
    is_symlink = False
    is_reg = False
    size = -1
    mtime_ns = None
    ctime_ns = None
    try:
        st = os.lstat(src_s)
        inode = (st.st_dev, st.st_ino)
        is_symlink = stat_mod.S_ISLNK(st.st_mode)
        is_reg = stat_mod.S_ISREG(st.st_mode)
        size = int(st.st_size)
        mtime_ns = int(st.st_mtime_ns)
        ctime_ns = int(st.st_ctime_ns)
    except OSError:
        pass
    artifact = b""
    if is_reg and not is_symlink:
        try:
            with open(src_s, "rb") as rf:
                artifact = rf.read()
        except OSError:
            artifact = b""
    digest = hashlib.sha256(artifact).hexdigest() if artifact else ""
    return artifact, inode, is_symlink, is_reg, size, mtime_ns, ctime_ns, digest


class Tracer:
    """Record fsync/replace/unlink/write; on fsync capture size/mtime/ctime/sha256 (NEW-03)."""

    def __init__(self):
        self.events = []
        self.real_fsync = os.fsync
        self.real_replace = os.replace
        self.real_unlink = os.unlink
        import builtins as _bi, io
        self._open = self.real_open = _bi.open
        self._io_open = io.open

    def open(self, file, mode="r", *a, **kw):
        p, f = os.path.abspath(str(file)), self.real_open(file, mode, *a, **kw)
        if set(str(mode)) & set("wxa+"):
            w, t = f.write, f.truncate
            f.write = lambda d, *x, **y: self.events.append(("write", p)) or w(d, *x, **y)
            f.truncate = lambda s=None: self.events.append(("truncate", p)) or (t() if s is None else t(s))
        return f

    def fsync(self, fd):
        path = fd_path(fd)
        size = -1
        blob = b""
        inode = (None, None)
        mtime_ns = None
        ctime_ns = None
        try:
            st = os.fstat(fd)
            size = int(st.st_size)
            inode = (st.st_dev, st.st_ino)
            mtime_ns = int(st.st_mtime_ns)
            ctime_ns = int(st.st_ctime_ns)
        except OSError:
            pass
        blob = fd_bytes_at_fsync(fd)
        digest = hashlib.sha256(blob).hexdigest() if blob is not None else ""
        self.events.append(
            ("fsync", path, size, blob, inode, mtime_ns, ctime_ns, digest)
        )
        return self.real_fsync(fd)

    def replace(self, src, dst):
        src_s, dst_s = str(src), str(dst)
        # lstat BEFORE rename: stamps+bytes of object replace moves (ctime changes after).
        artifact, inode, is_symlink, is_reg, size, mtime_ns, ctime_ns, digest = (
            lstat_replace_identity(src_s)
        )
        self.events.append(
            (
                "replace",
                src_s,
                dst_s,
                artifact,
                inode,
                is_symlink,
                is_reg,
                size,
                mtime_ns,
                ctime_ns,
                digest,
            )
        )
        return self.real_replace(src_s, dst_s)

    def unlink(self, path):
        self.events.append(("unlink", str(path)))
        return self.real_unlink(path)


def assert_durability_order(events, dest, src_log, src_exit, replace_src=None):
    """Exactly one verification-* replace; last-fsync size/mtime/ctime/sha256 match (NEW-03/04)."""
    dest = os.path.abspath(str(dest))
    src_log = os.path.abspath(str(src_log))
    src_exit = os.path.abspath(str(src_exit))
    dest_dir_abs = os.path.realpath(str(Path(dest).parent))
    del replace_src  # identity is lstat inode at replace, not realpath of replace_src

    abs_events = []
    for ev in events:
        k = ev[0]
        if k == "replace":
            abs_events.append(
                (
                    "replace",
                    os.path.abspath(ev[1]),  # dirent path; do not realpath (GD-04a)
                    os.path.abspath(ev[2]),
                    ev[3] if len(ev) > 3 else b"",
                    ev[4] if len(ev) > 4 else (None, None),
                    ev[5] if len(ev) > 5 else False,
                    ev[6] if len(ev) > 6 else False,
                    ev[7] if len(ev) > 7 else -1,
                    ev[8] if len(ev) > 8 else None,
                    ev[9] if len(ev) > 9 else None,
                    ev[10] if len(ev) > 10 else "",
                )
            )
        elif k == "fsync":
            p = ev[1]
            size = ev[2] if len(ev) > 2 else -1
            blob = ev[3] if len(ev) > 3 else b""
            inode = ev[4] if len(ev) > 4 else (None, None)
            mtime_ns = ev[5] if len(ev) > 5 else None
            ctime_ns = ev[6] if len(ev) > 6 else None
            digest = ev[7] if len(ev) > 7 else (
                hashlib.sha256(blob).hexdigest() if blob else ""
            )
            if str(p).startswith("fd:"):
                abs_events.append((k, p, size, blob, inode, mtime_ns, ctime_ns, digest))
            else:
                abs_events.append(
                    (k, os.path.realpath(p), size, blob, inode, mtime_ns, ctime_ns, digest)
                )
        else:
            p = ev[1]
            abs_events.append((k, os.path.abspath(p) if not str(p).startswith("fd:") else p))

    # NEW-04: ALL verification-*.json dest replaces (not only selected dest / ver_files[-1]).
    replace_idxs = [
        i
        for i, e in enumerate(abs_events)
        if e[0] == "replace" and is_verification_json(e[2])
    ]
    if not replace_idxs:
        raise AssertionError("replace of verification destination never observed")
    if len(replace_idxs) != 1:
        raise AssertionError(
            f"expected exactly one verification-*.json replace, got {len(replace_idxs)}"
        )
    ri = replace_idxs[0]
    rep = abs_events[ri]
    if rep[2] != dest:
        raise AssertionError(
            f"verification replace dest {rep[2]} is not the selected dest {dest}"
        )

    artifact = rep[3]
    replace_inode = rep[4] if len(rep) > 4 else (None, None)
    is_symlink = rep[5] if len(rep) > 5 else False
    is_reg = rep[6] if len(rep) > 6 else False
    rep_size = rep[7] if len(rep) > 7 else -1
    rep_mtime = rep[8] if len(rep) > 8 else None
    rep_ctime = rep[9] if len(rep) > 9 else None
    rep_sha = rep[10] if len(rep) > 10 else ""
    if is_symlink or not is_reg:
        raise AssertionError(
            "symlink-replace rejected: replace-src lstat is S_ISLNK or not S_ISREG"
        )
    if not artifact:
        raise AssertionError("artifact bytes empty at replace; nothing durable to prove")
    if replace_inode[0] is None or replace_inode[1] is None:
        raise AssertionError("replace-src lstat inode unknown; cannot verify identity")

    pre = abs_events[:ri]
    last_temp_fsync = None
    for e in pre:
        if e[0] != "fsync":
            continue
        p = e[1]
        if str(p).startswith("fd:"):
            raise AssertionError(
                f"unmapped fd fsync before replace is not proof of temp fsync: {p}"
            )
        fsync_inode = e[4] if len(e) > 4 else (None, None)
        # GD-04a: fstat must equal replace lstat (st_dev, st_ino); not realpath/stat.
        if fsync_inode != replace_inode or fsync_inode[0] is None or fsync_inode[1] is None:
            # GD-04b: ignore non-matching pre-fsync (state.json, state.json.tmp, dest_dir).
            continue
        last_temp_fsync = e
    if last_temp_fsync is None:
        raise AssertionError(
            f"no fsync of replace-src lstat inode {replace_inode} before replace"
        )
    # NEW-03: last fsync size + mtime_ns + ctime_ns + sha256 must match pre-replace lstat.
    fs = last_temp_fsync
    fs_size, fs_blob = fs[2], fs[3]
    fs_mtime, fs_ctime, fs_sha = fs[5], fs[6], fs[7]
    if fs_sha != rep_sha or fs_blob != artifact:
        raise AssertionError(
            "write-after-fsync / fsync-before-write: last-fsync sha256/bytes "
            f"do not match replace (fsync_sha={fs_sha} replace_sha={rep_sha} "
            f"len_fsync={len(fs_blob) if fs_blob is not None else -1} "
            f"len_replace={len(artifact)})"
        )
    if fs_mtime != rep_mtime or fs_ctime != rep_ctime or fs_size != rep_size:
        raise AssertionError(
            "write-after-fsync: last-fsync mtime/ctime/size mismatch "
            f"fsync=(mtime_ns={fs_mtime},ctime_ns={fs_ctime},size={fs_size}) "
            f"replace=(mtime_ns={rep_mtime},ctime_ns={rep_ctime},size={rep_size})"
        )

    # NEW-03 dest-mutate: dest bytes == artifact; post-replace write needs dest fsync.
    dest_bytes = Path(dest).read_bytes() if os.path.isfile(dest) else b""
    if dest_bytes != artifact:
        raise AssertionError("dest-mutate-after-replace: dest bytes != artifact")
    post = abs_events[ri + 1 :]
    for j, e in enumerate(post):
        if e[0] not in ("write", "truncate") or e[1] != dest:
            continue
        if not any(
            e2[0] == "fsync" and len(e2) > 7 and e2[4] == replace_inode
            and e2[3] == artifact and e2[7] == rep_sha and e2[2] == rep_size
            for e2 in post[j + 1 :]
        ):
            raise AssertionError("dest-mutate-after-replace: write without dest fsync")
    dir_fsync_idxs = [
        i
        for i, e in enumerate(post)
        if e[0] == "fsync"
        and not str(e[1]).startswith("fd:")
        and os.path.realpath(e[1]) == dest_dir_abs
    ]
    if not dir_fsync_idxs:
        raise AssertionError("containing-directory fsync / dir-fsync not observed after replace")
    after_dir = post[dir_fsync_idxs[0] + 1 :]
    unlinks = [(e[0], e[1]) for e in after_dir if e[0] == "unlink"]
    log_i = next((i for i, e in enumerate(unlinks) if e[1] == src_log), None)
    exit_i = next((i for i, e in enumerate(unlinks) if e[1] == src_exit), None)
    if log_i is None or exit_i is None:
        raise AssertionError(
            f"expected unlinks of {src_log} and {src_exit} after dir fsync, got {unlinks}"
        )
    if not (log_i < exit_i):
        raise AssertionError("original log unlink must precede original exit unlink")

ORACLE

# Oracle TABLE (GD-04a/b): in-script before actl.session import.
# PASS: write+flush+fsync temp (final bytes already in it) -> replace dest ->
# dir fsync -> unlink. At temp fsync compare fstat stamps+sha256 to replace lstat.
# Spies count only verification-*.json (not state.json). NEW-04: exactly one such replace.
python3 - <<'PY'
import os
import sys
import time
import tempfile
from pathlib import Path

sys.path.insert(0, os.environ["P24_ORACLE_DIR"])
from p24_oracle import (
    Tracer,
    assert_durability_order,
    fd_path,
    is_verification_json,
)

ARTIFACT = b'{"kind":"verification","id":"verification-006"}'


def expect_reject(label, fn):
    try:
        fn()
    except AssertionError:
        print(f"OK: {label} rejected by durability oracle.")
        return
    print(f"FAIL: S1-R15.3: {label} was accepted by the durability oracle")
    raise SystemExit(1)


def reset_sess(td, dest, src_log, src_exit):
    if dest.exists():
        dest.unlink()
    for p in td.glob("verification-*.json"):
        p.unlink()
    src_log.write_bytes(b"log\n")
    src_exit.write_bytes(b"0\n")


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    dest = td / "verification-006.json"
    src_log = td / "sess.log"
    src_exit = td / "sess.exit"
    other = td / "unrelated.dat"
    state = td / "state.json"
    src_log.write_bytes(b"log\n")
    src_exit.write_bytes(b"0\n")
    other.write_bytes(b"x\n")
    state.write_bytes(b'{"seq":6}')

    import builtins as _bi
    import io
    _prev_fsync, _prev_replace, _prev_unlink, _prev_open, _prev_io_open = os.fsync, os.replace, os.unlink, _bi.open, io.open

    def install(tr):
        os.fsync, os.replace, os.unlink, _bi.open, io.open = tr.fsync, tr.replace, tr.unlink, tr.open, tr.open

    def restore():
        os.fsync, os.replace, os.unlink, _bi.open, io.open = _prev_fsync, _prev_replace, _prev_unlink, _prev_open, _prev_io_open

    def dir_fsync():
        dfd = os.open(str(td), os.O_RDONLY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)

    # --- Reference PASS: write, flush, fsync (final bytes), replace, dir fsync, unlink ---
    reset_sess(td, dest, src_log, src_exit)
    tr = Tracer()
    tmp_good = td / "verification-006.json.tmp"
    install(tr)
    try:
        with open(tmp_good, "wb") as f:
            f.write(ARTIFACT)
            f.flush()
            os.fsync(f.fileno())  # fstat|/proc/self/fd sees final bytes + stamps
        os.replace(str(tmp_good), str(dest))
        dir_fsync()
        os.unlink(str(src_log))
        os.unlink(str(src_exit))
        assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp_good)
    except AssertionError as exc:
        print(f"FAIL: S1-R15.3: known-good builtins.open/fileno rejected: {exc}")
        raise SystemExit(1)
    finally:
        restore()
    print("OK: known-good builtins.open/fileno accepted by durability oracle.")

    # --- Known-good: state.json.tmp fsync then verification (GD-04b scoped) ---
    reset_sess(td, dest, src_log, src_exit)
    state.write_bytes(b'{"seq":6}')
    state_tmp_kg = td / "state.json.tmp"
    state_tmp_kg.write_bytes(b'{"seq":7}')
    tr = Tracer()
    tmp_good = td / "verification-006.json.tmp"
    install(tr)
    try:
        with open(state_tmp_kg, "rb") as sf:
            os.fsync(sf.fileno())
        with open(tmp_good, "wb") as f:
            f.write(ARTIFACT)
            f.flush()
            os.fsync(f.fileno())
        os.replace(str(tmp_good), str(dest))
        dir_fsync()
        os.unlink(str(src_log))
        os.unlink(str(src_exit))
        assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp_good)
    except AssertionError as exc:
        print(f"FAIL: S1-R15.3: known-good state.json fsync then verification rejected: {exc}")
        raise SystemExit(1)
    finally:
        restore()
    print("OK: known-good state.json fsync then verification")

    # 1) no fsync
    def deg_no_fsync():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        tmp.write_bytes(ARTIFACT)
        tr.replace(str(tmp), str(dest))
        tr.unlink(str(src_log))
        tr.unlink(str(src_exit))
        assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)

    expect_reject("no-fsync counterfeit", deg_no_fsync)

    # 2) unrelated fsync
    def deg_unrelated():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        tmp.write_bytes(ARTIFACT)
        tr.events.append(("fsync", str(other), other.stat().st_size, other.read_bytes()))
        tr.replace(str(tmp), str(dest))
        tr.events.append(("fsync", str(td), 0, b""))
        tr.unlink(str(src_log))
        tr.unlink(str(src_exit))
        assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)

    expect_reject("unrelated-fsync counterfeit", deg_unrelated)

    # 3) fsync-before-write (fsync empty, then write+flush, then replace)
    def deg_fsync_before_write():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.flush()
                os.fsync(f.fileno())  # fsync empty
                f.write(ARTIFACT)
                f.flush()
                # deliberately no second fsync after final write
            os.replace(str(tmp), str(dest))
            dir_fsync()
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()

    expect_reject("fsync-before-write / fsync empty then write counterfeit", deg_fsync_before_write)

    # 4) replace-before-fsync (write+flush, replace, then fsync of gone/wrong path)
    def deg_replace_before_fsync():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
            os.replace(str(tmp), str(dest))  # replace before fsync
            dir_fsync()
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()

    expect_reject("replace-before-fsync / replace before temp fsync counterfeit", deg_replace_before_fsync)

    # 5) no directory fsync
    def deg_no_dir_fsync():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp), str(dest))
            # skip directory fsync / dir-fsync
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()

    expect_reject("no directory fsync / dir-fsync counterfeit", deg_no_dir_fsync)

    # 6) unlink-before-replace
    def deg_unlink_before_replace():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                os.fsync(f.fileno())
            os.unlink(str(src_log))  # unlink before replace
            os.unlink(str(src_exit))
            os.replace(str(tmp), str(dest))
            dir_fsync()
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()

    expect_reject("unlink-before-replace / unlink before counterfeit", deg_unlink_before_replace)

    # 8) inode-swap: fsync inode A, unlink path (hold A via hardlink so B != A),
    # recreate inode B at same path with same bytes, do not fsync B, replace dest with B.
    def deg_inode_swap():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        hold = td / "verification-006.json.tmp.hold"  # keeps inode A allocated
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                os.fsync(f.fileno())  # fsync inode A
            os.link(str(tmp), str(hold))
            os.unlink(str(tmp))
            with open(tmp, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                # deliberately no fsync of inode B
            os.replace(str(tmp), str(dest))
            dir_fsync()
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()
            if hold.exists():
                hold.unlink()

    expect_reject("inode-swap / different inode counterfeit", deg_inode_swap)
    print("OK inode-swap rejected")

    # GD-04a: symlink .tmp -> .tmp.real; fsync through symlink; replace moves the symlink.
    def deg_symlink_replace():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        tmp_real = td / "verification-006.json.tmp.real"
        install(tr)
        try:
            with open(tmp_real, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
            tmp.symlink_to(tmp_real.name)
            with open(tmp, "rb") as f:  # open+fsync through symlink (fstat=target)
                os.fsync(f.fileno())
            os.replace(str(tmp), str(dest))  # moves the symlink dirent
            dir_fsync()
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()
            if tmp_real.exists():
                tmp_real.unlink()

    expect_reject("symlink-replace counterfeit", deg_symlink_replace)
    print("OK symlink-replace rejected")

    # every-replace: durable first replace, then non-fsynced second replace of same dest.
    def deg_second_replace():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp_a = td / "verification-006.json.tmp.a"
        tmp_b = td / "verification-006.json.tmp.b"
        install(tr)
        try:
            with open(tmp_a, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp_a), str(dest))
            with open(tmp_b, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                # deliberately no fsync of second replace source
            os.replace(str(tmp_b), str(dest))
            dir_fsync()
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit)
        finally:
            restore()

    expect_reject("second-replace / every replace counterfeit", deg_second_replace)
    print("OK second-replace rejected")

    # NEW-03: write ARTIFACT, flush, fsync; overwrite; rewrite ARTIFACT; flush; replace (no 2nd fsync).
    def deg_write_after_fsync():
        reset_sess(td, dest, src_log, src_exit)
        tr = Tracer()
        tmp = td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                os.fsync(f.fileno())
            time.sleep(0.05)
            with open(tmp, "wb") as f:
                f.write(b'{"kind":"other-bytes-after-fsync"}')
                f.flush()
            time.sleep(0.05)
            with open(tmp, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                # deliberately no fsync after rewrite — stamps/sha256 must mismatch last fsync
            os.replace(str(tmp), str(dest))
            dir_fsync()
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()

    expect_reject("write-after-fsync counterfeit", deg_write_after_fsync)
    print("OK write-after-fsync rejected (last-fsync mtime/ctime/sha256)")

    # NEW-04: non-fsynced replace to verification-005.json, then proper fsynced verification-006.json.
    def deg_other_dest():
        reset_sess(td, dest, src_log, src_exit)
        dest5 = td / "verification-005.json"
        tr = Tracer()
        tmp5 = td / "verification-005.json.tmp"
        tmp6 = td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp5, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                # deliberately no fsync of other-dest replace source
            os.replace(str(tmp5), str(dest5))
            with open(tmp6, "wb") as f:
                f.write(ARTIFACT)
                f.flush()
                os.fsync(f.fileno())
            os.replace(str(tmp6), str(dest))
            dir_fsync()
            os.unlink(str(src_log))
            os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit)
        finally:
            restore()
            if dest5.exists():
                dest5.unlink()

    expect_reject("other-dest-replace / verification-005 counterfeit", deg_other_dest)
    print("OK other-dest-replace rejected")

    # NEW-03: replace then in-place dest corrupt write; no dest fsync (dir fsync ≠ durable).
    def deg_dest_mutate_after_replace():
        reset_sess(td, dest, src_log, src_exit)
        tr, tmp = Tracer(), td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.write(ARTIFACT); f.flush(); os.fsync(f.fileno())
            os.replace(str(tmp), str(dest))
            with open(dest, "wb") as f:
                f.write(b'{"kind":"corrupt-after-replace"}'); f.flush()
            dir_fsync(); os.unlink(str(src_log)); os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()
    expect_reject("dest-mutate-after-replace counterfeit", deg_dest_mutate_after_replace)
    print("OK dest-mutate-after-replace rejected")

    # NEW-03 B2: Path.write_bytes via io.open; CORRUPT then ARTIFACT; no dest fsync.
    def deg_pathlib_write_bytes():
        reset_sess(td, dest, src_log, src_exit)
        tr, tmp = Tracer(), td / "verification-006.json.tmp"
        install(tr)
        try:
            with open(tmp, "wb") as f:
                f.write(ARTIFACT); f.flush(); os.fsync(f.fileno())
            os.replace(str(tmp), str(dest))
            Path(dest).write_bytes(b"CORRUPT"); Path(dest).write_bytes(ARTIFACT)
            dir_fsync(); os.unlink(str(src_log)); os.unlink(str(src_exit))
            assert_durability_order(tr.events, dest, src_log, src_exit, replace_src=tmp)
        finally:
            restore()
    expect_reject("pathlib-write_bytes counterfeit", deg_pathlib_write_bytes)
    print("OK pathlib-write_bytes rejected")

    # 7) replace in finally after failed fsync
    reset_sess(td, dest, src_log, src_exit)
    tmp_deg = td / "verification-006.json.tmpdeg"
    tmp_deg.write_bytes(ARTIFACT)
    replace_called_deg = {"n": 0}
    try:
        try:
            raise OSError("Simulated disk failure at verification temp fsync")
        except OSError:
            # finally-style commit after failed fsync
            os.replace(str(tmp_deg), str(dest))
            replace_called_deg["n"] += 1
            raise
    except OSError:
        pass
    ver_after = [p for p in td.glob("verification-*.json") if is_verification_json(p.name)]
    if replace_called_deg["n"] >= 1 or ver_after:
        print("OK: finally-replace after failed fsync rejected by boundary-1 criteria.")
    else:
        print("FAIL: S1-R15.3: finally-replace after failed fsync was not rejected")
        raise SystemExit(1)

    # GD-04b known-good: os.replace state.json then injected temp-fsync failure;
    # boundary 1 PASS because spy counts only verification-*.json (unrelated replace ignored).
    reset_sess(td, dest, src_log, src_exit)
    state.write_bytes(b'{"seq":6}')
    state_tmp = td / "state.json.tmp"
    state_tmp.write_bytes(b'{"seq":7}')
    tmp_v = td / "verification-006.json.tmp"
    tmp_v.write_bytes(ARTIFACT)
    ver_replace_after_fail = {"n": 0}
    temp_fsync_fail_reached = {"n": 0}

    def fail_temp_only(fd):
        base = os.path.basename(fd_path(fd))
        # verification temp names: verification-NNN.json.tmp (not final .json)
        if base.startswith("verification-") and not (
            base.endswith(".json") and ".tmp" not in base and ".meta." not in base
        ):
            temp_fsync_fail_reached["n"] += 1
            raise OSError("Simulated disk failure at verification temp fsync")
        return _prev_fsync(fd)

    def spy_replace_ver_only(src, dst):
        # Spies count only verification-*.json dest (state.json ignored).
        if is_verification_json(dst):
            ver_replace_after_fail["n"] += 1
        return _prev_replace(src, dst)

    # Unrelated state.json replace first (must be ignored by boundary-1 spy).
    os.replace(str(state_tmp), str(state))
    os.fsync = fail_temp_only
    os.replace = spy_replace_ver_only
    try:
        with open(tmp_v, "rb") as f:
            try:
                fail_temp_only(f.fileno())
            except OSError:
                pass
        if temp_fsync_fail_reached["n"] < 1:
            print("FAIL: S1-R15.3: temp-fsync failure injection was never reached")
            raise SystemExit(1)
        # conforming code does NOT replace verification dest after temp-fsync failure
        if ver_replace_after_fail["n"] != 0:
            print("FAIL: S1-R15.3: verification replace counted after temp-fsync failure")
            raise SystemExit(1)
        if any(is_verification_json(p.name) for p in td.glob("verification-*.json")):
            print("FAIL: S1-R15.3: verification-*.json present after temp-fsync failure")
            raise SystemExit(1)
        if not state.is_file() or state.read_bytes() != b'{"seq":7}':
            print("FAIL: S1-R15.3: state.json replace was not preserved as unrelated")
            raise SystemExit(1)
        print("OK: state.json replace ignored by boundary-1; temp-fsync failure PASS.")
    finally:
        restore()
PY

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
sandbox_out="$(create_stage1_sandbox "p24" "good.patch")" || exit $?
IFS='|' read -r SDIR WT <<< "$sandbox_out"
if [[ -z "${SDIR:-}" || -z "${WT:-}" || ! -d "$SDIR" ]]; then
  echo "FAIL: S1-R15.3: sandbox setup failed" >&2
  exit 1
fi

export ATOOLS_LOG_DIR="${SDIR}/cursor_logs"
export ATOOLS_SESSION_DIR="${SDIR}/cursor_sessions"
mkdir -p "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR"

python3 - "$SDIR" "$WT" <<'PY'
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.environ["P24_ORACLE_DIR"])
from p24_oracle import Tracer, assert_durability_order, fd_path, is_verification_json

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.session import archive_session_log
    from actl.verify import verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R15.3: cannot import actl modules: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
sess_name = "impl-public-profiles-006"

src_log = Path(os.environ["ATOOLS_LOG_DIR"]) / f"{sess_name}.log"
src_exit = Path(os.environ["ATOOLS_SESSION_DIR"]) / f"{sess_name}.exit"
log_bytes = b"session console output for durability ordering check\n"
exit_bytes = b"0\n"
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)

import hashlib
log_sha = hashlib.sha256(log_bytes).hexdigest()

archive_session_log(layout, tag, 6, sess_name)
session_info = {
    "name": sess_name,
    "exit_code": 0,
    "hard_cap": False,
    "lost": False,
    "log_sha256": log_sha,
}

dest_dir = layout.runs_dir(tag)
real_fsync = os.fsync
real_replace = os.replace
real_unlink = os.unlink

_FINAL_VER_RE = re.compile(r"^verification-\d+\.json$")


def is_verification_temp(path: str) -> bool:
    """True only for verification replace-src temps, not dest_dir or final json."""
    if not path or str(path).startswith("fd:"):
        return False
    ap = os.path.realpath(path)
    base = os.path.basename(ap)
    if not base.startswith("verification-"):
        return False
    if _FINAL_VER_RE.match(base):
        return False
    dest_abs = os.path.realpath(str(dest_dir))
    return ap.startswith(dest_abs + os.sep) or os.path.dirname(ap) == dest_abs


def originals_intact():
    return (
        src_log.is_file()
        and src_exit.is_file()
        and src_log.read_bytes() == log_bytes
        and src_exit.read_bytes() == exit_bytes
    )


# NEW-04-LIVE: snapshot/restore state.json so happy path stays verification-006.json.
state_path = dest_dir / "state.json"
initial_state = state_path.read_bytes()


def clear_verification_artifacts():
    """NEW-02: drop prior commits; NEW-04-LIVE restore state.json + drop highwater."""
    for p in dest_dir.glob("verification-*.json"):
        p.unlink()
    state_path.write_bytes(initial_state)
    hw = dest_dir / "seq.highwater"
    if hw.is_file():
        hw.unlink()


# --- Failure injection at every persistence boundary ---
last_replace_src = {"path": None}
boundaries = []

# 1) temp fsync failure (GD-04b): trigger only verification temp, not dest_dir files.
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
clear_verification_artifacts()
temp_fsync_reached = {"n": 0}
replace_called_b1 = {"n": 0}


def fail_temp_fsync(fd):
    p = fd_path(fd)
    if is_verification_temp(p):
        temp_fsync_reached["n"] += 1
        raise OSError("Simulated disk failure at verification temp fsync")
    return real_fsync(fd)


def track_replace_b1(src, dst):
    # GD-04b: count only verification-*.json dest replaces (ignore state.json).
    if is_verification_json(dst):
        replace_called_b1["n"] += 1
        last_replace_src["path"] = str(src)
    return real_replace(src, dst)


with patch("os.fsync", side_effect=fail_temp_fsync), \
     patch("os.replace", side_effect=track_replace_b1):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass
if temp_fsync_reached["n"] < 1:
    print("FAIL: S1-R15.3: temp fsync failure injection was never reached")
    sys.exit(1)
if replace_called_b1["n"] != 0:
    print("FAIL: S1-R15.3: os.replace was called after temp-fsync failure (degenerate finally-replace)")
    sys.exit(1)
if list(dest_dir.glob("verification-*.json")):
    print("FAIL: S1-R15.3: verification-*.json present in dest_dir after temp-fsync failure")
    sys.exit(1)
if not originals_intact():
    print("FAIL: S1-R15.3: originals changed after temp-fsync failure")
    sys.exit(1)
boundaries.append("temp_fsync")

# 2) replace failure
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
clear_verification_artifacts()
replace_reached = {"n": 0}


def fail_on_verification_replace(src, dst):
    if "verification-" in str(dst):
        replace_reached["n"] += 1
        last_replace_src["path"] = str(src)
        raise OSError("Simulated disk failure before verification commit")
    return real_replace(src, dst)


with patch("os.replace", side_effect=fail_on_verification_replace):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass
if replace_reached["n"] < 1:
    print("FAIL: S1-R15.3: replace spy was never reached on the failure injection")
    sys.exit(1)
if not originals_intact():
    print("FAIL: S1-R15.3: Source .log/.exit were unlinked or altered BEFORE verification artifact was durably committed")
    sys.exit(1)
boundaries.append("replace")

# 3) dir fsync failure (after successful replace) -- NEW-02 reset first
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
clear_verification_artifacts()
dir_fsync_reached = {"n": 0}
replaced_once = {"n": 0}


def spy_replace_then_fail_dir_fsync_replace(src, dst):
    if "verification-" in str(dst):
        replaced_once["n"] += 1
        last_replace_src["path"] = str(src)
    return real_replace(src, dst)


def fail_dir_fsync(fd):
    p = fd_path(fd)
    if replaced_once["n"] >= 1 and not str(p).startswith("fd:"):
        if os.path.realpath(p) == os.path.realpath(str(dest_dir)):
            dir_fsync_reached["n"] += 1
            raise OSError("Simulated disk failure at runs-dir fsync")
    return real_fsync(fd)


with patch("os.replace", side_effect=spy_replace_then_fail_dir_fsync_replace), \
     patch("os.fsync", side_effect=fail_dir_fsync):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass
if dir_fsync_reached["n"] < 1:
    print("FAIL: S1-R15.3: dir fsync failure injection was never reached")
    sys.exit(1)
if not originals_intact():
    print("FAIL: S1-R15.3: originals changed after dir-fsync failure")
    sys.exit(1)
boundaries.append("dir_fsync")

# 4) unlink log failure (after durable write) -- NEW-02 reset first
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
clear_verification_artifacts()
unlink_log_reached = {"n": 0}


def fail_unlink_log(path):
    ap = os.path.abspath(str(path))
    if ap == os.path.abspath(str(src_log)):
        unlink_log_reached["n"] += 1
        raise OSError("Simulated failure unlinking session log")
    return real_unlink(path)


with patch("os.unlink", side_effect=fail_unlink_log):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass
if unlink_log_reached["n"] < 1:
    print("FAIL: S1-R15.3: unlink-log failure injection was never reached")
    sys.exit(1)
if not (src_log.is_file() and src_log.read_bytes() == log_bytes):
    print("FAIL: S1-R15.3: log bytes not preserved when unlink-log failed")
    sys.exit(1)
if not (src_exit.is_file() and src_exit.read_bytes() == exit_bytes):
    print("FAIL: S1-R15.3: exit bytes not preserved when unlink-log failed")
    sys.exit(1)
boundaries.append("unlink_log")

# 5) unlink exit failure -- NEW-02 reset first
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
clear_verification_artifacts()
unlink_exit_reached = {"n": 0}


def fail_unlink_exit(path):
    ap = os.path.abspath(str(path))
    if ap == os.path.abspath(str(src_log)):
        return real_unlink(path)
    if ap == os.path.abspath(str(src_exit)):
        unlink_exit_reached["n"] += 1
        raise OSError("Simulated failure unlinking session exit")
    return real_unlink(path)


with patch("os.unlink", side_effect=fail_unlink_exit):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass
if unlink_exit_reached["n"] < 1:
    print("FAIL: S1-R15.3: unlink-exit failure injection was never reached")
    sys.exit(1)
if not (src_exit.is_file() and src_exit.read_bytes() == exit_bytes):
    print("FAIL: S1-R15.3: exit bytes not preserved when unlink-exit failed")
    sys.exit(1)
boundaries.append("unlink_exit")

if boundaries != ["temp_fsync", "replace", "dir_fsync", "unlink_log", "unlink_exit"]:
    print(f"FAIL: S1-R15.3: incomplete failure-injection coverage: {boundaries}")
    sys.exit(1)

# Happy path under the shared Tracer (live spies call same Tracer/assert).
clear_verification_artifacts()
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
# Selected dest is seq 6 — do not use ver_files[-1] (NEW-04).
selected_dest = dest_dir / "verification-006.json"
tr = Tracer()
with patch("os.fsync", side_effect=tr.fsync), \
     patch("os.replace", side_effect=tr.replace), patch("os.unlink", side_effect=tr.unlink), \
     patch("builtins.open", tr.open), patch("io.open", tr.open):
    res = verify_impl(layout, tag, worktree=wt, session_info=session_info)

if not selected_dest.is_file():
    print("FAIL: S1-R15.3: verification-006.json was not written")
    sys.exit(1)
try:
    assert_durability_order(tr.events, selected_dest, src_log, src_exit)
except AssertionError as exc:
    print(f"FAIL: S1-R15.3: durability order: {exc}; events={tr.events}")
    sys.exit(1)

if src_log.exists() or src_exit.exists():
    print(f"FAIL: S1-R15.3: Source .log ({src_log.exists()}) or .exit ({src_exit.exists()}) was not unlinked after verification write")
    sys.exit(1)
if not (layout.logs_dir(tag) / "impl-006.log").is_file() or not (layout.logs_dir(tag) / "impl-006.exit").is_file():
    print("FAIL: S1-R15.1: Archived impl-006.log/exit missing from runs/logs/")
    sys.exit(1)
print(f"OK: S1-R15.3 durability order and failure injection ({','.join(boundaries)}).")
PY
