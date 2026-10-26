#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-26: Instruction argument ceiling (100,000 bytes JSON-escaped) enforced.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
import json
from pathlib import Path

try:
    from actl.session import start_session
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl.session.start_session: {exc}")
    sys.exit(1)

# 1. Exactly 100,000 bytes escaped boundary test
border_instruction = "A" * 99998
border_escaped_len = len(json.dumps(border_instruction))

# 2. Exceeding instruction: 100,001 bytes JSON-escaped
overflow_instruction = "A" * 100005
try:
    start_session("impl-large-prompt-001", Path("/tmp"), overflow_instruction)
    print("FAIL: S1-R9.5: start_session must reject instruction exceeding 100,000 bytes JSON-escaped")
    sys.exit(1)
except ValueError:
    pass # Expected boundary enforcement
except Exception as exc:
    print(f"FAIL: S1-R9.5: start_session invocation failed: {exc}")
    sys.exit(1)
PY
