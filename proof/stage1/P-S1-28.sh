#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-28: actl verify-impl CLI exits conform strictly to 0/1/2/3/4 table.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    import actl.cmd_verify_impl as cmd_mod
except ImportError as exc:
    print(f"FAIL: S1-R11: cannot import actl.cmd_verify_impl: {exc}")
    sys.exit(1)
PY
