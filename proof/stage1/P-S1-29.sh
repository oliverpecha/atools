#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-29: bad_regression_o2.patch fails O2 at test_get_user_unknown_returns_none.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    from actl.verify import run_o2
except ImportError as exc:
    print(f"FAIL: S1-R6: cannot import actl.verify.run_o2: {exc}")
    sys.exit(1)
PY
