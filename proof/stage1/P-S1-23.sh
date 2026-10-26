#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-23: archive_session_log copies raw log and .exit, verifying SHA-256.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p23" "good.patch")"

python3 - "$SDIR" <<'PY'
import sys
import hashlib
from pathlib import Path

sdir = Path(sys.argv[1])

try:
    from actl.session import archive_session_log
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R15: cannot import actl.session.archive_session_log: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# Set up mock raw session log and .exit in sprint runs/logs
raw_logs_dir = sdir / "sprints" / "target-repo" / tag / "runs" / "logs"
raw_logs_dir.mkdir(parents=True, exist_ok=True)
sess_name = "test-sess-001"
raw_log = raw_logs_dir / f"{sess_name}.log"
raw_data = b"synthetic session log output\nexit line\n"
raw_log.write_bytes(raw_data)
expected_sha = hashlib.sha256(raw_data).hexdigest()

raw_exit = raw_logs_dir / f"{sess_name}.exit"
raw_exit.write_text("0\n")

try:
    sha = archive_session_log(layout, tag, 1, sess_name)
    if sha != expected_sha:
        print(f"FAIL: S1-R15: Returned archive SHA-256 {sha} != expected {expected_sha}")
        sys.exit(1)

    dest_log = raw_logs_dir / "impl-001.log"
    dest_exit = raw_logs_dir / "impl-001.exit"
    if not dest_log.exists():
        print(f"FAIL: S1-R15: Destination archive log does not exist: {dest_log}")
        sys.exit(1)
    if not dest_exit.exists():
        print(f"FAIL: S1-R15: Destination archive exit does not exist: {dest_exit}")
        sys.exit(1)

    actual_dest_sha = hashlib.sha256(dest_log.read_bytes()).hexdigest()
    if actual_dest_sha != expected_sha:
        print(f"FAIL: S1-R15: Destination content SHA {actual_dest_sha} != expected {expected_sha}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R15: archive_session_log invocation failed: {exc}")
    sys.exit(1)
PY
