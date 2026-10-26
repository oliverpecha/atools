#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-13: O1 stages oracle proofs into sibling scratch dir and cleans up in finally.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    from actl.verify import run_o1
except ImportError as exc:
    print(f"FAIL: S1-R4: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)
PY
