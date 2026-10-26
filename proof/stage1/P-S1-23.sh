#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-23: archive_session_log copies raw log and .exit, verifying SHA-256.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import os
import sys
import hashlib
from pathlib import Path

try:
    from actl.session import archive_session_log
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R15: cannot import actl.session.archive_session_log: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p23_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)

# Create mock source log
raw_log = root / "raw.log"
raw_data = b"synthetic session log output\nline 2\n"
raw_log.write_bytes(raw_data)
expected_sha = hashlib.sha256(raw_data).hexdigest()

try:
    sha = archive_session_log(layout, "2026-10-16_public-profiles", 1, "test-sess-001", log_src=raw_log)
    if sha != expected_sha:
        print(f"FAIL: S1-R15: Returned archive SHA-256 {sha} != expected {expected_sha}")
        sys.exit(1)
    dest_log = layout.runs("2026-10-16_public-profiles") / "logs" / "impl-001.log"
    if not dest_log.exists():
        print(f"FAIL: S1-R15: Destination archive log does not exist: {dest_log}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R15: archive_session_log invocation failed: {exc}")
    sys.exit(1)
PY
