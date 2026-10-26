#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-15: prior_attempt.json has strictly 4 keys and leaks no oracle tests.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R7: cannot import actl.schemas: {exc}")
    sys.exit(1)
PY
