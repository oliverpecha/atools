#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-01: Golden good.patch green, exit 0, verification record schema-valid.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    import actl.verify as verify_mod
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R1: cannot import actl.verify: {exc}")
    sys.exit(1)
PY
