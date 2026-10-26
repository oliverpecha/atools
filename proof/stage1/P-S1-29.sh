#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-29: bad_regression_o2.patch fails O2 at test_get_user_unknown_returns_none.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.verify import run_o2
except ImportError as exc:
    print(f"FAIL: S1-R6: cannot import actl.verify.run_o2: {exc}")
    sys.exit(1)

try:
    results = run_o2(Path("/tmp/wt-regression"))
    o2 = results[0] if results else None
    if not o2 or o2.exit_code == 0:
        print("FAIL: S1-R6: O2 did not fail on regression as expected")
        sys.exit(1)
    if "test_get_user_unknown_returns_none" not in o2.id:
        print(f"FAIL: S1-R6: O2 id missing expected test node: {getattr(o2, 'id', None)}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R6: run_o2 invocation failed: {exc}")
    sys.exit(1)
PY
