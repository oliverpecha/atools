#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-26: Instruction argument ceiling (100,000 bytes JSON-escaped) enforced.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.session import start_session
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl.session.start_session: {exc}")
    sys.exit(1)

huge_instruction = "A" * 105000
try:
    start_session("impl-large-prompt-001", Path("/tmp"), huge_instruction)
    print("FAIL: S1-R9: start_session must reject instruction exceeding 100,000 bytes")
    sys.exit(1)
except ValueError:
    pass # Expected boundary enforcement
except Exception as exc:
    print(f"FAIL: S1-R9: start_session invocation failed: {exc}")
    sys.exit(1)
PY
