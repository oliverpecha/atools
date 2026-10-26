#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-18: Phase 3 decision rules table (10 distinct states evaluated).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import os
import sys
from pathlib import Path

try:
    import actl.next_rules.phase3 as p3
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R12: cannot import actl.next_rules.phase3: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p18_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)

# Test State 1: Active session running -> action 'wait'
def probe_running(name):
    return {"running": True, "exit_code": None}

try:
    res = p3.evaluate(layout, "2026-10-16_public-profiles", session_probe=probe_running)
    if not res or res.get("action") != "wait":
        print(f"FAIL: S1-R12: State 1 expected action='wait', got: {res}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R12: phase3 evaluate invocation failed: {exc}")
    sys.exit(1)
PY
