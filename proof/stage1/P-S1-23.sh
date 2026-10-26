#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-23: archive_session_log copies raw log and .exit, verifying SHA-256.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    from actl.session import archive_session_log
except ImportError as exc:
    print(f"FAIL: S1-R15: cannot import actl.session.archive_session_log: {exc}")
    sys.exit(1)
PY
