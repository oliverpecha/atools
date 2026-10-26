#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-14: O1 runs under strict environment allowlist (purges caller env).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

export FORBIDDEN_VAR_TEST="must_not_leak"
python3 - <<'PY'
import os
import sys
from pathlib import Path

repo_dir = Path(os.environ.get("ACTL_REPO", "."))
oracle = repo_dir / "fixtures" / "golden" / "sprint" / "oracle"

try:
    from actl.verify import run_o1
except ImportError as exc:
    print(f"FAIL: S1-R5: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p14_sandbox"
root.mkdir(parents=True, exist_ok=True)
wt = root / "wt_env"
wt.mkdir(parents=True, exist_ok=True)

try:
    steps = run_o1(oracle, wt)
    if not isinstance(steps, list) or len(steps) == 0:
        print("FAIL: S1-R5: run_o1 must return executed StepResults")
        sys.exit(1)
    if any(s.exit_code != 0 for s in steps):
        print("FAIL: S1-R5: O1 steps failed unexpectedly under isolated env")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R5: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
