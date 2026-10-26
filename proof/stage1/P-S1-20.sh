#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-20: Detached implementer dispatch via arouter with custom stub wrapper (D-42).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

python3 - <<'PY'
import sys
try:
    import actl.cmd_dispatch_impl as cmd_mod
    from actl.verify import verify_impl
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import dispatch_impl or verify_impl: {exc}")
    sys.exit(1)
PY
