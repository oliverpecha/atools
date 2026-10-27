#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-23: archive_session_log copies raw <ATOOLS_LOG_DIR>/<sess>.log and
# <ATOOLS_SESSION_DIR>/<sess>.exit to runs/logs/impl-{seq:03d}.{log,exit},
# verifies SHA-256 of both, and leaves source files intact before verify_impl (S1-R15).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p23" "good.patch")"

export ATOOLS_LOG_DIR="${SDIR}/cursor_logs"
export ATOOLS_SESSION_DIR="${SDIR}/cursor_sessions"
mkdir -p "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR"

python3 - "$SDIR" <<'PY'
import hashlib
import os
import sys
from pathlib import Path

sdir = Path(sys.argv[1])

try:
    from actl.session import archive_session_log
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R15.1: cannot import actl.session.archive_session_log: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
sess_name = "impl-public-profiles-006"

src_log = Path(os.environ["ATOOLS_LOG_DIR"]) / f"{sess_name}.log"
src_exit = Path(os.environ["ATOOLS_SESSION_DIR"]) / f"{sess_name}.exit"

log_bytes = b"line 1: starting implementer\nline 2: finished\n"
exit_bytes = b"0\n"
src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)

expected_log_sha = hashlib.sha256(log_bytes).hexdigest()
expected_exit_sha = hashlib.sha256(exit_bytes).hexdigest()

# 1. Missing session returns None
if archive_session_log(layout, tag, 99, "impl-nonexistent-099") is not None:
    print("FAIL: S1-R15.1: Expected None when session log does not exist")
    sys.exit(1)

# 2. Existing session copies both .log and .exit and returns exact SHA-256 without unlinking sources
ret_sha = archive_session_log(layout, tag, 6, sess_name)
if ret_sha != expected_log_sha:
    print(f"FAIL: S1-R15.1: Returned SHA {ret_sha} != expected {expected_log_sha}")
    sys.exit(1)

dst_log = layout.logs_dir(tag) / "impl-006.log"
dst_exit = layout.logs_dir(tag) / "impl-006.exit"
if not dst_log.is_file() or not dst_exit.is_file():
    print(f"FAIL: S1-R15.1: Expected archived {dst_log} and {dst_exit} to exist")
    sys.exit(1)

if hashlib.sha256(dst_log.read_bytes()).hexdigest() != expected_log_sha:
    print("FAIL: S1-R15.2: Archived .log SHA-256 mismatch")
    sys.exit(1)
if hashlib.sha256(dst_exit.read_bytes()).hexdigest() != expected_exit_sha:
    print("FAIL: S1-R15.2: Archived .exit SHA-256 mismatch")
    sys.exit(1)

# Source files MUST still exist after archive_session_log (unlink is verify_impl's responsibility)
if not src_log.is_file() or not src_exit.is_file():
    print("FAIL: S1-R15.3: archive_session_log prematurely unlinked source .log or .exit")
    sys.exit(1)

# Observe archive fsync of destination log and exit files
from unittest.mock import patch
fsync_paths = []
fd_map = {}
real_open, real_fsync, real_close = os.open, os.fsync, os.close

def spy_open(path, flags, mode=0o777, *a, **k):
    fd = real_open(path, flags, mode, *a, **k)
    fd_map[fd] = str(path)
    return fd

def spy_fsync(fd):
    fsync_paths.append(fd_map.get(fd, f"fd:{fd}"))
    return real_fsync(fd)

def spy_close(fd):
    fd_map.pop(fd, None)
    return real_close(fd)

src_log.write_bytes(log_bytes)
src_exit.write_bytes(exit_bytes)
with patch("os.open", side_effect=spy_open), patch("os.fsync", side_effect=spy_fsync), patch("os.close", side_effect=spy_close):
    archive_session_log(layout, tag, 7, sess_name)
abs_fsync = [os.path.abspath(p) if not str(p).startswith("fd:") else p for p in fsync_paths]
dst_log_7 = os.path.abspath(str(layout.logs_dir(tag) / "impl-007.log"))
dst_exit_7 = os.path.abspath(str(layout.logs_dir(tag) / "impl-007.exit"))
if dst_log_7 not in abs_fsync or dst_exit_7 not in abs_fsync:
    print(f"FAIL: S1-R15.1: archive_session_log did not fsync dest log/exit; observed {abs_fsync}")
    sys.exit(1)
PY
