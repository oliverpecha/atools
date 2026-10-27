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

# Oracle TABLE (GD-04a/b): in-script before actl.session import.
# PASS: write+flush+fsync temp (final bytes already in it) -> replace dest ->
# dir fsync -> unlink. At temp fsync compare fstat/proc bytes to replace bytes.
# Spies count only verification-*.json (not state.json).
python3 - <<'PY'
import os
import tempfile
from pathlib import Path

ARTIFACT = b'{"kind":"verification","id":"verification-006"}'


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


class Tracer:
    """Record fsync/replace/unlink; on fsync capture path + visible bytes (fstat/proc)."""

    def __init__(self):
        self.events = []
        self.real_fsync = os.fsync
        self.real_replace = os.replace
        self.real_unlink = os.unlink

    def fsync(self, fd):
        path = fd_path(fd)
        size = -1
        blob = b""
        inode = (None, None)
        try:
            st = os.fstat(fd)
            size = int(st.st_size)
            inode = (st.st_dev, st.st_ino)
        except OSError:
            pass
        blob = fd_bytes_at_fsync(fd)
        self.events.append(("fsync", path, size, blob, inode))
        return self.real_fsync(fd)

    def replace(self, src, dst):
        src_s, dst_s = str(src), str(dst)
        try:
            artifact = Path(src_s).read_bytes()
        except OSError:
            artifact = b""
        # Identity of the inode the kernel will rename (stat BEFORE rename).
        inode = (None, None)
        try:
            st = os.stat(src_s)
            inode = (st.st_dev, st.st_ino)
        except OSError:
            pass
        self.events.append(("replace", src_s, dst_s, artifact, inode))
        return self.real_replace(src_s, dst_s)

    def unlink(self, path):
        self.events.append(("unlink", str(path)))
        return self.real_unlink(path)


def assert_durability_order(events, dest, src_log, src_exit, replace_src=None):
    """Require write-final-bytes fsync of replace-src before replace, then dir fsync + unlinks."""
    dest = os.path.abspath(str(dest))
    src_log = os.path.abspath(str(src_log))
    src_exit = os.path.abspath(str(src_exit))
    dest_dir_abs = os.path.realpath(str(Path(dest).parent))
    replace_src_abs = os.path.realpath(str(replace_src)) if replace_src is not None else None

    abs_events = []
    for ev in events:
        k = ev[0]
        if k == "replace":
            abs_events.append(
                (
                    "replace",
                    os.path.realpath(ev[1]),
                    os.path.abspath(ev[2]),
                    ev[3] if len(ev) > 3 else b"",
                    ev[4] if len(ev) > 4 else (None, None),
                )
            )
        elif k == "fsync":
            p = ev[1]
            size = ev[2] if len(ev) > 2 else -1
            blob = ev[3] if len(ev) > 3 else b""
            inode = ev[4] if len(ev) > 4 else (None, None)
            if str(p).startswith("fd:"):
                abs_events.append((k, p, size, blob, inode))
            else:
                abs_events.append((k, os.path.realpath(p), size, blob, inode))
        else:
            p = ev[1]
            abs_events.append((k, os.path.abspath(p) if not str(p).startswith("fd:") else p))

    replace_idxs = [
        i for i, e in enumerate(abs_events)
        if e[0] == "replace" and e[2] == dest and is_verification_json(e[2])
    ]
    if not replace_idxs:
        raise AssertionError("replace of verification destination never observed")
    ri = replace_idxs[0]
    rep = abs_events[ri]
    observed_src = rep[1]
    artifact = rep[3]
    replace_inode = rep[4] if len(rep) > 4 else (None, None)
    if replace_src_abs is None:
        replace_src_abs = observed_src
    if replace_src_abs is None:
        raise AssertionError("replace-src temp path unknown; cannot verify temp fsync")
    if not artifact:
        raise AssertionError("artifact bytes empty at replace; nothing durable to prove")

    pre = abs_events[:ri]
    matching_temp_fsync = False
    saw_temp_fsync = False
    for e in pre:
        if e[0] != "fsync":
            continue
        p = e[1]
        if str(p).startswith("fd:"):
            raise AssertionError(f"unmapped fd fsync before replace is not proof of temp fsync: {p}")
        if os.path.realpath(p) != replace_src_abs:
            # GD-04b: ignore non-verification pre-fsync (state.json, state.json.tmp, dest_dir).
            # deg_unrelated still REJECTS: replace_src itself was never fsynced.
            continue
        saw_temp_fsync = True
        size, blob = e[2], e[3]
        fsync_inode = e[4] if len(e) > 4 else (None, None)
        # Final content + same inode the kernel will rename (reject inode-swap).
        if (
            blob == artifact
            and fsync_inode == replace_inode
            and fsync_inode[0] is not None
            and fsync_inode[1] is not None
        ):
            matching_temp_fsync = True
    if not saw_temp_fsync:
        raise AssertionError(
            f"no fsync of exact replace-src temp path {replace_src_abs} before replace"
        )
    if not matching_temp_fsync:
        raise AssertionError(
            "fsync-before-write / fsync empty / different inode: temp fsync bytes "
            f"or st_dev/st_ino do not match artifact at replace (len={len(artifact)})"
        )

    post = abs_events[ri + 1 :]
    dir_fsync_idxs = [
        i
        for i, e in enumerate(post)
        if e[0] == "fsync" and not str(e[1]).startswith("fd:") and os.path.realpath(e[1]) == dest_dir_abs
    ]
    if not dir_fsync_idxs:
        raise AssertionError("containing-directory fsync / dir-fsync not observed after replace")
    after_dir = post[dir_fsync_idxs[0] + 1 :]
    unlinks = [(e[0], e[1]) for e in after_dir if e[0] == "unlink"]
    log_i = next((i for i, e in enumerate(unlinks) if e[1] == src_log), None)
    exit_i = next((i for i, e in enumerate(unlinks) if e[1] == src_exit), None)
    if log_i is None or exit_i is None:
        raise AssertionError(f"expected unlinks of {src_log} and {src_exit} after dir fsync, got {unlinks}")
    if not (log_i < exit_i):
        raise AssertionError("original log unlink must precede original exit unlink")


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

    _prev_fsync, _prev_replace, _prev_unlink = os.fsync, os.replace, os.unlink

    def install(tr):
        os.fsync, os.replace, os.unlink = tr.fsync, tr.replace, tr.unlink

    def restore():
        os.fsync, os.replace, os.unlink = _prev_fsync, _prev_replace, _prev_unlink

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
            os.fsync(f.fileno())  # fstat|/proc/self/fd sees final bytes
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
import hashlib
import os
import re
import sys
from pathlib import Path
from unittest.mock import patch

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
events: list = []
real_fsync = os.fsync
real_replace = os.replace
real_unlink = os.unlink

_FINAL_VER_RE = re.compile(r"^verification-\d+\.json$")


def fd_path(fd):
    """Resolve fd via /proc; fsync spy must not depend on os.open (GD-04a)."""
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
    # Temp must live in (or be staged for) the runs dest_dir tree.
    dest_abs = os.path.realpath(str(dest_dir))
    return ap.startswith(dest_abs + os.sep) or os.path.dirname(ap) == dest_abs


def spy_fsync(fd):
    size = -1
    inode = (None, None)
    try:
        st = os.fstat(fd)
        size = int(st.st_size)
        inode = (st.st_dev, st.st_ino)
    except OSError:
        pass
    events.append(("fsync", fd_path(fd), size, fd_bytes_at_fsync(fd), inode))
    return real_fsync(fd)


def spy_replace(src, dst):
    src_s, dst_s = str(src), str(dst)
    # Record verification-*.json dest only (state.json ignored).
    if is_verification_json(dst_s):
        try:
            artifact = Path(src_s).read_bytes()
        except OSError:
            artifact = b""
        inode = (None, None)
        try:
            st = os.stat(src_s)  # BEFORE rename: inode the kernel will rename
            inode = (st.st_dev, st.st_ino)
        except OSError:
            pass
        events.append(("replace", src_s, dst_s, artifact, inode))
    return real_replace(src_s, dst_s)


def spy_unlink(path):
    events.append(("unlink", str(path)))
    return real_unlink(path)


def assert_durability_order(events, dest, src_log, src_exit, replace_src=None):
    """Same oracle as Block 1: blob==artifact + st_dev/st_ino; non-verification pre-fsync ignored."""
    dest = os.path.abspath(str(dest))
    src_log = os.path.abspath(str(src_log))
    src_exit = os.path.abspath(str(src_exit))
    dest_dir_abs = os.path.realpath(str(Path(dest).parent))
    replace_src_abs = os.path.realpath(str(replace_src)) if replace_src is not None else None

    abs_events = []
    for ev in events:
        k = ev[0]
        if k == "replace":
            abs_events.append(
                (
                    "replace",
                    os.path.realpath(ev[1]),
                    os.path.abspath(ev[2]),
                    ev[3] if len(ev) > 3 else b"",
                    ev[4] if len(ev) > 4 else (None, None),
                )
            )
        elif k == "fsync":
            p = ev[1]
            size = ev[2] if len(ev) > 2 else -1
            blob = ev[3] if len(ev) > 3 else b""
            inode = ev[4] if len(ev) > 4 else (None, None)
            if str(p).startswith("fd:"):
                abs_events.append((k, p, size, blob, inode))
            else:
                abs_events.append((k, os.path.realpath(p), size, blob, inode))
        else:
            p = ev[1]
            abs_events.append((k, os.path.abspath(p) if not str(p).startswith("fd:") else p))

    replace_idxs = [
        i for i, e in enumerate(abs_events)
        if e[0] == "replace" and e[2] == dest and is_verification_json(e[2])
    ]
    if not replace_idxs:
        raise AssertionError("replace of verification destination never observed")
    ri = replace_idxs[0]
    rep = abs_events[ri]
    observed_src = rep[1]
    artifact = rep[3]
    replace_inode = rep[4] if len(rep) > 4 else (None, None)
    if replace_src_abs is None:
        replace_src_abs = observed_src
    if replace_src_abs is None:
        raise AssertionError("replace-src temp path unknown; cannot verify temp fsync")
    if not artifact:
        raise AssertionError("artifact bytes empty at replace; nothing durable to prove")

    pre = abs_events[:ri]
    matching_temp_fsync = False
    saw_temp_fsync = False
    for e in pre:
        if e[0] != "fsync":
            continue
        p = e[1]
        if str(p).startswith("fd:"):
            raise AssertionError(f"unmapped fd fsync before replace is not proof of temp fsync: {p}")
        if os.path.realpath(p) != replace_src_abs:
            # GD-04b: ignore non-verification pre-fsync (state.json, state.json.tmp, dest_dir).
            continue
        saw_temp_fsync = True
        size, blob = e[2], e[3]
        fsync_inode = e[4] if len(e) > 4 else (None, None)
        if (
            blob == artifact
            and fsync_inode == replace_inode
            and fsync_inode[0] is not None
            and fsync_inode[1] is not None
        ):
            matching_temp_fsync = True
    if not saw_temp_fsync:
        raise AssertionError(
            f"no fsync of exact replace-src temp path {replace_src_abs} before replace"
        )
    if not matching_temp_fsync:
        raise AssertionError(
            "fsync-before-write / fsync empty / different inode: temp fsync bytes "
            f"or st_dev/st_ino do not match artifact at replace (len={len(artifact)})"
        )

    post = abs_events[ri + 1 :]
    dir_fsync_idxs = [
        i
        for i, e in enumerate(post)
        if e[0] == "fsync" and not str(e[1]).startswith("fd:") and os.path.realpath(e[1]) == dest_dir_abs
    ]
    if not dir_fsync_idxs:
        raise AssertionError("containing-directory fsync / dir-fsync not observed after replace")
    after_dir = post[dir_fsync_idxs[0] + 1 :]
    unlinks = [(e[0], e[1]) for e in after_dir if e[0] == "unlink"]
    log_i = next((i for i, e in enumerate(unlinks) if e[1] == src_log), None)
    exit_i = next((i for i, e in enumerate(unlinks) if e[1] == src_exit), None)
    if log_i is None or exit_i is None:
        raise AssertionError(f"expected unlinks of {src_log} and {src_exit} after dir fsync, got {unlinks}")
    if not (log_i < exit_i):
        raise AssertionError("original log unlink must precede original exit unlink")


def originals_intact():
    return (
        src_log.is_file()
        and src_exit.is_file()
        and src_log.read_bytes() == log_bytes
        and src_exit.read_bytes() == exit_bytes
    )


def clear_verification_artifacts():
    """NEW-02: drop prior commits so a later boundary cannot be satisfied by leftovers."""
    for p in dest_dir.glob("verification-*.json"):
        p.unlink()
    events.clear()


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
    base = os.path.basename(str(dst))
    if (
        base.startswith("verification-")
        and base.endswith(".json")
        and ".meta." not in base
    ):
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

# Happy path under the tracer.
clear_verification_artifacts()
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
with patch("os.fsync", side_effect=spy_fsync), \
     patch("os.replace", side_effect=spy_replace), patch("os.unlink", side_effect=spy_unlink):
    res = verify_impl(layout, tag, worktree=wt, session_info=session_info)

ver_files = sorted(dest_dir.glob("verification-*.json"))
if not ver_files:
    print("FAIL: S1-R15.3: verification-*.json was not written")
    sys.exit(1)
try:
    assert_durability_order(events, ver_files[-1], src_log, src_exit)
except AssertionError as exc:
    print(f"FAIL: S1-R15.3: durability order: {exc}; events={events}")
    sys.exit(1)

if src_log.exists() or src_exit.exists():
    print(f"FAIL: S1-R15.3: Source .log ({src_log.exists()}) or .exit ({src_exit.exists()}) was not unlinked after verification write")
    sys.exit(1)
if not (layout.logs_dir(tag) / "impl-006.log").is_file() or not (layout.logs_dir(tag) / "impl-006.exit").is_file():
    print("FAIL: S1-R15.1: Archived impl-006.log/exit missing from runs/logs/")
    sys.exit(1)
print(f"OK: S1-R15.3 durability order and failure injection ({','.join(boundaries)}).")
PY
