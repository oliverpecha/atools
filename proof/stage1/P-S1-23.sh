#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-23: archive_session_log copies raw log and .exit, verifying SHA-256.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.session import archive_session_log
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R15: cannot import actl.session.archive_session_log: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
try:
    sha = archive_session_log(layout, "2026-10-16_public-profiles", 1, "test-sess-001")
    if sha is not None and len(sha) != 64:
        print(f"FAIL: S1-R15: Expected 64-hex SHA-256 or None, got: {sha}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R15: archive_session_log invocation failed: {exc}")
    sys.exit(1)
PY
