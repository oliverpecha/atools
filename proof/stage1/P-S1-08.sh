#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-08: Guard self-tests pass; corrupted config halts with exit 3.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
try:
    from actl.verify import run_selftests
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl.verify.run_selftests: {exc}")
    sys.exit(1)

try:
    results = run_selftests()
    for r in results:
        if r.exit_code != 0:
            print(f"FAIL: S1-R3: run_selftests check failed: {r.id}")
            sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: run_selftests invocation failed: {exc}")
    sys.exit(1)
PY
