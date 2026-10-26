#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-13: O1 stages oracle proofs into sibling scratch dir and cleans up in finally.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import os
import sys
from pathlib import Path

repo_dir = Path(os.environ.get("ACTL_REPO", "."))
oracle = repo_dir / "fixtures" / "golden" / "sprint" / "oracle"

try:
    from actl.verify import run_o1
except ImportError as exc:
    print(f"FAIL: S1-R4: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p13_sandbox"
root.mkdir(parents=True, exist_ok=True)
wt = root / "wt_staging"
wt.mkdir(parents=True, exist_ok=True)

try:
    run_o1(oracle, wt)
    stage_dir = root / "wt_staging.oracle-stage"
    if stage_dir.exists():
        print(f"FAIL: S1-R4: Staging directory was not removed in finally block: {stage_dir}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R4: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
