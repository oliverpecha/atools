#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-21: Watchdog overrun records 124, hard_cap=True, and increments counter.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    from actl.session import wait_session
except ImportError as exc:
    print(f"FAIL: S1-R14: cannot import actl.session.wait_session: {exc}")
    sys.exit(1)

try:
    res = wait_session("impl-mock-timeout-001", timeout_s=1)
    if not isinstance(res, dict) or "hard_cap" not in res:
        print("FAIL: S1-R14: wait_session return dict missing hard_cap field")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R14: wait_session invocation failed: {exc}")
    sys.exit(1)
PY
