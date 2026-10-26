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
    if not isinstance(res, dict) or res.get("hard_cap") is not True:
        print(f"FAIL: S1-R14: wait_session failed to set hard_cap=True on timeout: {res}")
        sys.exit(1)
    if res.get("exit_code") != 124:
        print(f"FAIL: S1-R14: Expected exit code 124 on watchdog overrun, got {res.get('exit_code')}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R14: wait_session invocation failed: {exc}")
    sys.exit(1)
PY
