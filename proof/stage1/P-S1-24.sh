#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-24: Observable durability order for verification write:
# temp-file fsync -> replace dest -> directory fsync -> unlink log -> unlink exit.
# A no-fsync counterfeit MUST fail this oracle (S1-R15.2).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

# Control self-check first: reject a no-fsync counterfeit without importing actl.
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
        self.events.append(("replace", str(dst)))
        return self.real_replace(src, dst)

    def unlink(self, path):
        self.events.append(("unlink", str(path)))
        return self.real_unlink(path)


def assert_durability_order(events, dest, src_log, src_exit):
    dest = str(dest)
    src_log = str(src_log)
    src_exit = str(src_exit)
    dest_dir = str(Path(dest).parent)

    def kind_path(ev):
        return ev[0], os.path.abspath(ev[1]) if not str(ev[1]).startswith("fd:") else ev[1]

    abs_events = [kind_path(e) for e in events]
    dest_abs = os.path.abspath(dest)
    dest_dir_abs = os.path.abspath(dest_dir)
    log_abs = os.path.abspath(src_log)
    exit_abs = os.path.abspath(src_exit)

    replace_idxs = [i for i, e in enumerate(abs_events) if e == ("replace", dest_abs)]
    if not replace_idxs:
        raise AssertionError("replace of verification destination never observed")
    ri = replace_idxs[0]

    pre = abs_events[:ri]
    if not any(k == "fsync" and os.path.abspath(p) != dest_dir_abs and not str(p).startswith("fd:") for k, p in pre):
        # Accept fsync of a temp path in dest_dir, or fsync of an fd that is not the directory.
        temp_fsync = [i for i, (k, p) in enumerate(pre) if k == "fsync"]
        if not temp_fsync:
            raise AssertionError("no fsync of verification temporary file before replace")

    post = abs_events[ri + 1:]
    dir_fsync_idxs = [
        i for i, (k, p) in enumerate(post)
        if k == "fsync" and (p == dest_dir_abs or os.path.abspath(p) == dest_dir_abs)
    ]
    if not dir_fsync_idxs:
        raise AssertionError("containing-directory fsync not observed after replace")
    di = dir_fsync_idxs[0]
    after_dir = post[di + 1:]
    unlinks = [(k, p) for k, p in after_dir if k == "unlink"]
    log_i = next((i for i, e in enumerate(unlinks) if e[1] == log_abs), None)
    exit_i = next((i for i, e in enumerate(unlinks) if e[1] == exit_abs), None)
    if log_i is None or exit_i is None:
        raise AssertionError(f"expected unlinks of {log_abs} and {exit_abs} after dir fsync, got {unlinks}")
    if not (log_i < exit_i):
        raise AssertionError("original log unlink must precede original exit unlink")


with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    dest = td / "verification-006.json"
    src_log = td / "sess.log"
    src_exit = td / "sess.exit"
    src_log.write_bytes(b"log\n")
    src_exit.write_bytes(b"0\n")
    tracer = FdMap()
    tmp = td / "verification-006.json.tmp"
    tmp.write_text("{}", encoding="utf-8")
    tracer.replace(str(tmp), str(dest))
    tracer.unlink(str(src_log))
    tracer.unlink(str(src_exit))
    try:
        assert_durability_order(tracer.events, dest, src_log, src_exit)
    except AssertionError:
        pass
    else:
        print("FAIL: S1-R15.3: no-fsync counterfeit was accepted by the durability oracle")
        raise SystemExit(1)

print("OK: no-fsync counterfeit rejected by durability oracle.")
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
src_log.write_bytes(log_bytes)
src_exit.write_bytes(b"0\n")
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
events: list[tuple[str, str]] = []
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
    events.append(("replace", str(dst)))
    return real_replace(src, dst)


def spy_unlink(path):
    events.append(("unlink", str(path)))
    return real_unlink(path)


def assert_durability_order(ev, dest, slog, sexit):
    dest = os.path.abspath(str(dest))
    slog = os.path.abspath(str(slog))
    sexit = os.path.abspath(str(sexit))
    dest_dir_abs = os.path.abspath(str(Path(dest).parent))
    abs_events = []
    for k, p in ev:
        if str(p).startswith("fd:"):
            abs_events.append((k, p))
        else:
            abs_events.append((k, os.path.abspath(p)))
    replace_idxs = [i for i, e in enumerate(abs_events) if e == ("replace", dest)]
    if not replace_idxs:
        raise AssertionError("replace of verification destination never observed")
    ri = replace_idxs[0]
    pre = abs_events[:ri]
    if not any(k == "fsync" for k, _p in pre):
        raise AssertionError("no temporary-file fsync before replace")
    post = abs_events[ri + 1:]
    dir_idxs = [i for i, (k, p) in enumerate(post) if k == "fsync" and p == dest_dir_abs]
    if not dir_idxs:
        raise AssertionError("containing-directory fsync not observed after replace")
    after_dir = post[dir_idxs[0] + 1:]
    unlinks = [(k, p) for k, p in after_dir if k == "unlink"]
    log_i = next((i for i, e in enumerate(unlinks) if e[1] == slog), None)
    exit_i = next((i for i, e in enumerate(unlinks) if e[1] == sexit), None)
    if log_i is None or exit_i is None or not (log_i < exit_i):
        raise AssertionError(f"unlink order after dir fsync invalid: {unlinks}")


# Injected failure at replace: originals remain, replace was reached.
replace_reached = {"n": 0}

def fail_on_verification_replace(src, dst):
    if "verification-" in str(dst):
        replace_reached["n"] += 1
        raise OSError("Simulated disk failure before verification commit")
    return real_replace(src, dst)

src_log.write_bytes(log_bytes)
src_exit.write_bytes(b"0\n")
with patch("os.replace", side_effect=fail_on_verification_replace):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass
if replace_reached["n"] < 1:
    print("FAIL: S1-R15.3: replace spy was never reached on the failure injection")
    sys.exit(1)
if not src_log.is_file() or not src_exit.is_file():
    print("FAIL: S1-R15.3: Source .log/.exit were unlinked BEFORE verification artifact was durably committed")
    sys.exit(1)

# Happy path under the tracer.
events.clear()
fd_to_path.clear()
src_log.write_bytes(log_bytes)
src_exit.write_bytes(b"0\n")
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
PY
