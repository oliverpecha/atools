#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-24: Original <ATOOLS_LOG_DIR>/<sess>.log and <ATOOLS_SESSION_DIR>/<sess>.exit
# are unlinked ONLY AFTER verification-{seq:03d}.json is durably written; if
# verification write fails, originals remain on disk (GD-01 / GD-03 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p24" "good.patch")"

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

# 1. Negative durability control: if os.replace raises OSError when writing verification-*.json,
# source .log and .exit MUST NOT be unlinked.
real_replace = os.replace

def fail_on_verification_replace(src, dst):
    if "verification-" in str(dst):
        raise OSError("Simulated disk failure before verification commit")
    return real_replace(src, dst)

with patch("os.replace", side_effect=fail_on_verification_replace):
    try:
        verify_impl(layout, tag, worktree=wt, session_info=session_info)
    except OSError:
        pass

if not src_log.is_file() or not src_exit.is_file():
    print("FAIL: S1-R15.3: Source .log/.exit were unlinked BEFORE verification artifact was durably committed!")
    sys.exit(1)

# 2. Positive ordering control: observe state at the moment verification-*.json is replaced onto disk
unlinked_before_replace = False

def spy_replace(src, dst):
    global unlinked_before_replace
    if "verification-" in str(dst):
        if not src_log.is_file() or not src_exit.is_file():
            unlinked_before_replace = True
    return real_replace(src, dst)

with patch("os.replace", side_effect=spy_replace):
    res = verify_impl(layout, tag, worktree=wt, session_info=session_info)

if unlinked_before_replace:
    print("FAIL: S1-R15.3: Source .log/.exit were unlinked prior to os.replace of verification artifact")
    sys.exit(1)

ver_files = sorted(layout.runs_dir(tag).glob("verification-*.json"))
if not ver_files:
    print("FAIL: S1-R15.3: verification-*.json was not written")
    sys.exit(1)

if src_log.exists() or src_exit.exists():
    print(f"FAIL: S1-R15.3: Source .log ({src_log.exists()}) or .exit ({src_exit.exists()}) was not unlinked after verification write")
    sys.exit(1)

# Archived copies in runs/logs/ must still exist
if not (layout.logs_dir(tag) / "impl-006.log").is_file() or not (layout.logs_dir(tag) / "impl-006.exit").is_file():
    print("FAIL: S1-R15.1: Archived impl-006.log/exit missing from runs/logs/")
    sys.exit(1)
PY
