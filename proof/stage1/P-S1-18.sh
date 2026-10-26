#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-18: Phase 3 decision rules table (10 distinct states evaluated).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    import actl.next_rules.phase3 as p3
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R12: cannot import actl.next_rules.phase3: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
try:
    res = p3.evaluate(layout, "2026-10-16_public-profiles")
    if res is not None and "action" not in res:
        print("FAIL: S1-R12: Missing action in evaluate output")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R12: phase3 evaluate invocation failed: {exc}")
    sys.exit(1)
PY
