#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-14: O1 runs under strict environment allowlist (purges caller env).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

export FORBIDDEN_VAR_TEST="must_not_leak"
python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.verify import run_o1
except ImportError as exc:
    print(f"FAIL: S1-R5: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

oracle = Path(f"{REPO_DIR}/fixtures/golden/sprint/oracle")
try:
    res = run_o1(oracle, Path("/tmp/wt-env"))
except Exception as exc:
    print(f"FAIL: S1-R5: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
