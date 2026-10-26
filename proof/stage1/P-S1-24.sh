#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-24: Original log unlinked only after verification artifact fsync.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    from actl.verify import verify_impl
except ImportError as exc:
    print(f"FAIL: S1-R15: cannot import actl.verify.verify_impl: {exc}")
    sys.exit(1)
PY
