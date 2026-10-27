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

# Control self-check first: reject no-fsync and unrelated-fsync counterfeits without importing actl.
python3 - <<'PY'
import os
import tempfile
from pathlib import Path


class FdMap:
    def __init__(self):
        self.fd_to_path = {}
        self.events = []
        self.real_open = os.open
        self.real_fsync = os.fsync
        self.real_replace = os.replace
        self.real_unlink = os.unlink
        self.real_close = os.close

    def open(self, path, flags, mode=0o777, *args, **kwargs):
        fd = self.real_open(path, flags, mode, *args, **kwargs)
        self.fd_to_path[fd] = str(path)
        return fd

    def close(self, fd):
        self.fd_to_path.pop(fd, None)
        return self.real_close(fd)

    def fsync(self, fd):
        self.events.append(("fsync", self.fd_to_path.get(fd, f"fd:{fd}")))
        return self.real_fsync(fd)

    def replace(self, src, dst):
        self.events.append(("replace", str(src), str(dst)))
        return self.real_replace(src, dst)

    def unlink(self, path):
        self.events.append(("unlink", str(path)))
        return self.real_unlink(path)


def assert_durability_order(events, dest, src_log, src_exit, replace_src=None):
    """Require fsync of the exact replace-src temp path (or mapped fd) before replace dest.
    Reject any other pre-replace fsync. Then dest-dir fsync, unlink log, unlink exit.
    """
    dest = os.path.abspath(str(dest))
    src_log = os.path.abspath(str(src_log))
    src_exit = os.path.abspath(str(src_exit))
    dest_dir_abs = os.path.abspath(str(Path(dest).parent))
    replace_src_abs = os.path.abspath(str(replace_src)) if replace_src is not None else None

    abs_events = []
    for ev in events:
        k = ev[0]
        if k == "replace":
            # ("replace", src, dst) or legacy ("replace", dst)
            if len(ev) == 3:
                abs_events.append(("replace", os.path.abspath(ev[1]), os.path.abspath(ev[2])))
            else:
                abs_events.append(("replace", None, os.path.abspath(ev[1])))
        elif k == "fsync":
            p = ev[1]
            if str(p).startswith("fd:"):
                abs_events.append((k, p))
            else:
                abs_events.append((k, os.path.abspath(p)))
        else:
            p = ev[1]
            abs_events.append((k, os.path.abspath(p) if not str(p).startswith("fd:") else p))

    replace_idxs = [
        i for i, e in enumerate(abs_events)
        if e[0] == "replace" and e[-1] == dest
    ]
    if not replace_idxs:
        raise AssertionError("replace of verification destination never observed")
    ri = replace_idxs[0]
    rep = abs_events[ri]
    observed_src = rep[1] if len(rep) == 3 else None
    if replace_src_abs is None and observed_src is not None:
        replace_src_abs = observed_src
    if replace_src_abs is None:
        raise AssertionError("replace-src temp path unknown; cannot verify temp fsync")

    pre = abs_events[:ri]
    # Exact temp-path fsync (or fd mapped to that path) required before replace.
    temp_fsync_idxs = []
    for i, e in enumerate(pre):
        if e[0] != "fsync":
            continue
        p = e[1]
        if str(p).startswith("fd:"):
            # fd without path mapping cannot prove exact temp; reject
            continue
        if os.path.abspath(p) == replace_src_abs:
            temp_fsync_idxs.append(i)
    if not temp_fsync_idxs:
        raise AssertionError(
            f"no fsync of exact replace-src temp path {replace_src_abs} before replace"
        )
    # Reject any other pre-replace fsync that is not the temp path and not an unmapped fd
    # that we already skipped; any concrete non-temp path fsync is a counterfeit.
    for i, e in enumerate(pre):
        if e[0] != "fsync":
            continue
        p = e[1]
        if str(p).startswith("fd:"):
            raise AssertionError(f"unmapped fd fsync before replace is not proof of temp fsync: {p}")
        if os.path.abspath(p) != replace_src_abs:
            raise AssertionError(
                f"unrelated pre-replace fsync of {p}; only {replace_src_abs} is allowed"
            )

    post = abs_events[ri + 1:]
    dir_fsync_idxs = [
        i for i, e in enumerate(post)
        if e[0] == "fsync" and not str(e[1]).startswith("fd:") and os.path.abspath(e[1]) == dest_dir_abs
    ]
    if not dir_fsync_idxs:
        raise AssertionError("containing-directory fsync not observed after replace")
    di = dir_fsync_idxs[0]
    after_dir = post[di + 1:]
    unlinks = [(e[0], e[1]) for e in after_dir if e[0] == "unlink"]
    log_i = next((i for i, e in enumerate(unlinks) if e[1] == src_log), None)
    exit_i = next((i for i, e in enumerate(unlinks) if e[1] == src_exit), None)
    if log_i is None or exit_i is None:
        raise AssertionError(f"expected unlinks of {src_log} and {src_exit} after dir fsync, got {unlinks}")
    if not (log_i < exit_i):
        raise AssertionError("original log unlink must precede original exit unlink")


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    dest = td / "verification-006.json"
    src_log = td / "sess.log"
    src_exit = td / "sess.exit"
    other = td / "unrelated.dat"
    src_log.write_bytes(b"log\n")
    src_exit.write_bytes(b"0\n")
    other.write_bytes(b"x\n")

    # Counterfeit 1: no fsync at all before replace
    tracer = FdMap()
    tmp = td / "verification-006.json.tmp"
    tmp.write_text("{}", encoding="utf-8")
    tracer.replace(str(tmp), str(dest))
    tracer.unlink(str(src_log))
    tracer.unlink(str(src_exit))
    try:
        assert_durability_order(tracer.events, dest, src_log, src_exit, replace_src=tmp)
    except AssertionError:
        pass
    else:
        print("FAIL: S1-R15.3: no-fsync counterfeit was accepted by the durability oracle")
        raise SystemExit(1)
    print("OK: no-fsync counterfeit rejected by durability oracle.")

    # Counterfeit 2: unrelated-file fsync then replace dest (must be rejected)
    if dest.exists():
        dest.unlink()
    src_log.write_bytes(b"log\n")
    src_exit.write_bytes(b"0\n")
    tracer2 = FdMap()
    tmp2 = td / "verification-006.json.tmp2"
    tmp2.write_text("{}", encoding="utf-8")
    # Simulate fsync(other) via recording the unrelated path, then replace
    tracer2.events.append(("fsync", str(other)))
    tracer2.replace(str(tmp2), str(dest))
    ofd = os.open(str(td), os.O_RDONLY)
    try:
        tracer2.events.append(("fsync", str(td)))
    finally:
        os.close(ofd)
    tracer2.unlink(str(src_log))
    tracer2.unlink(str(src_exit))
    try:
        assert_durability_order(tracer2.events, dest, src_log, src_exit, replace_src=tmp2)
    except AssertionError:
        pass
    else:
        print("FAIL: S1-R15.3: unrelated-fsync counterfeit was accepted by the durability oracle")
        raise SystemExit(1)
    print("OK: unrelated-fsync counterfeit rejected by durability oracle.")
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
fd_to_path: dict[int, str] = {}
events: list = []
real_open = os.open
real_fsync = os.fsync
real_replace = os.replace
real_unlink = os.unlink
real_close = os.close


def spy_open(path, flags, mode=0o777, *args, **kwargs):
    fd = real_open(path, flags, mode, *args, **kwargs)
    fd_to_path[fd] = str(path)
    return fd


def spy_close(fd):
    fd_to_path.pop(fd, None)
    return real_close(fd)


def spy_fsync(fd):
    events.append(("fsync", fd_to_path.get(fd, f"fd:{fd}")))
    return real_fsync(fd)


def spy_replace(src, dst):
    events.append(("replace", str(src), str(dst)))
    return real_replace(src, dst)


def spy_unlink(path):
    events.append(("unlink", str(path)))
    return real_unlink(path)


def assert_durability_order(ev, dest, slog, sexit, replace_src=None):
    dest = os.path.abspath(str(dest))
    slog = os.path.abspath(str(slog))
    sexit = os.path.abspath(str(sexit))
    dest_dir_abs = os.path.abspath(str(Path(dest).parent))
    replace_src_abs = os.path.abspath(str(replace_src)) if replace_src is not None else None
    abs_events = []
    for item in ev:
        k = item[0]
        if k == "replace":
            if len(item) == 3:
                abs_events.append(("replace", os.path.abspath(item[1]), os.path.abspath(item[2])))
            else:
                abs_events.append(("replace", None, os.path.abspath(item[1])))
        elif k == "fsync":
            p = item[1]
            if str(p).startswith("fd:"):
                abs_events.append((k, p))
            else:
                abs_events.append((k, os.path.abspath(p)))
        else:
            p = item[1]
            abs_events.append((k, os.path.abspath(p) if not str(p).startswith("fd:") else p))
    replace_idxs = [i for i, e in enumerate(abs_events) if e[0] == "replace" and e[-1] == dest]
    if not replace_idxs:
        raise AssertionError("replace of verification destination never observed")
    ri = replace_idxs[0]
    rep = abs_events[ri]
    observed_src = rep[1] if len(rep) == 3 else None
    if replace_src_abs is None and observed_src is not None:
        replace_src_abs = observed_src
    if replace_src_abs is None:
        raise AssertionError("replace-src temp path unknown; cannot verify temp fsync")
    pre = abs_events[:ri]
    temp_ok = False
    for e in pre:
        if e[0] != "fsync":
            continue
        p = e[1]
        if str(p).startswith("fd:"):
            raise AssertionError(f"unmapped fd fsync before replace is not proof of temp fsync: {p}")
        if os.path.abspath(p) == replace_src_abs:
            temp_ok = True
        else:
            raise AssertionError(
                f"unrelated pre-replace fsync of {p}; only {replace_src_abs} is allowed"
            )
    if not temp_ok:
        raise AssertionError(f"no fsync of exact replace-src temp path {replace_src_abs} before replace")
    post = abs_events[ri + 1:]
    dir_idxs = [
        i for i, e in enumerate(post)
        if e[0] == "fsync" and not str(e[1]).startswith("fd:") and os.path.abspath(e[1]) == dest_dir_abs
    ]
    if not dir_idxs:
        raise AssertionError("containing-directory fsync not observed after replace")
    after_dir = post[dir_idxs[0] + 1:]
    unlinks = [(e[0], e[1]) for e in after_dir if e[0] == "unlink"]
    log_i = next((i for i, e in enumerate(unlinks) if e[1] == slog), None)
    exit_i = next((i for i, e in enumerate(unlinks) if e[1] == sexit), None)
    if log_i is None or exit_i is None or not (log_i < exit_i):
        raise AssertionError(f"unlink order after dir fsync invalid: {unlinks}")


def originals_intact():
    return (
        src_log.is_file()
        and src_exit.is_file()
        and src_log.read_bytes() == log_bytes
        and src_exit.read_bytes() == exit_bytes
    )


# --- Failure injection at every persistence boundary ---
# Track the temp path seen at replace so temp-fsync injection can target it.
last_replace_src = {"path": None}


def track_replace(src, dst):
    last_replace_src["path"] = str(src)
    return real_replace(src, dst)


boundaries = []

# 1) temp fsync failure
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
temp_fsync_reached = {"n": 0}
pending_temp = {"path": None}


def fail_temp_fsync(fd):
    # Infer temp path from open map: any open write target under dest_dir that is not dest_dir itself
    p = fd_to_path.get(fd, "")
    if p and os.path.abspath(p) != os.path.abspath(str(dest_dir)) and str(dest_dir) in os.path.abspath(p):
        if "verification-" in os.path.basename(p) or p.endswith(".tmp") or ".tmp" in os.path.basename(p):
            temp_fsync_reached["n"] += 1
            pending_temp["path"] = p
            raise OSError("Simulated disk failure at verification temp fsync")
    # Also: if replace has not happened yet and this is an fsync of a file in dest_dir
    if p and os.path.dirname(os.path.abspath(p)) == os.path.abspath(str(dest_dir)):
        if os.path.abspath(p) != os.path.abspath(str(dest_dir)):
            temp_fsync_reached["n"] += 1
            raise OSError("Simulated disk failure at verification temp fsync")
    return real_fsync(fd)


fd_to_path.clear()
with patch("os.open", side_effect=spy_open), patch("os.close", side_effect=spy_close), \
     patch("os.fsync", side_effect=fail_temp_fsync):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass
if temp_fsync_reached["n"] < 1:
    print("FAIL: S1-R15.3: temp fsync failure injection was never reached")
    sys.exit(1)
if not originals_intact():
    print("FAIL: S1-R15.3: originals changed after temp-fsync failure")
    sys.exit(1)
boundaries.append("temp_fsync")

# 2) replace failure
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
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

# 3) dir fsync failure (after successful replace)
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
dir_fsync_reached = {"n": 0}
replaced_once = {"n": 0}


def spy_replace_then_fail_dir_fsync_replace(src, dst):
    if "verification-" in str(dst):
        replaced_once["n"] += 1
        last_replace_src["path"] = str(src)
    return real_replace(src, dst)


def fail_dir_fsync(fd):
    p = fd_to_path.get(fd, "")
    if replaced_once["n"] >= 1 and (
        p == str(dest_dir) or os.path.abspath(p) == os.path.abspath(str(dest_dir))
    ):
        dir_fsync_reached["n"] += 1
        raise OSError("Simulated disk failure at runs-dir fsync")
    return real_fsync(fd)


fd_to_path.clear()
with patch("os.open", side_effect=spy_open), patch("os.close", side_effect=spy_close), \
     patch("os.replace", side_effect=spy_replace_then_fail_dir_fsync_replace), \
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

# 4) unlink log failure (after durable write)
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
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

# 5) unlink exit failure
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
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
events.clear()
fd_to_path.clear()
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
with patch("os.open", side_effect=spy_open), patch("os.fsync", side_effect=spy_fsync), \
     patch("os.replace", side_effect=spy_replace), patch("os.unlink", side_effect=spy_unlink), \
     patch("os.close", side_effect=spy_close):
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
