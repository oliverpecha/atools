#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-13: O1 stages oracle proofs into sibling scratch dir and cleans up in finally.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.verify import run_o1
except ImportError as exc:
    print(f"FAIL: S1-R4: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

oracle = Path(f"{REPO_DIR}/fixtures/golden/sprint/oracle")
worktree = Path("/tmp/wt-staging-test")
worktree.mkdir(parents=True, exist_ok=True)
try:
    run_o1(oracle, worktree)
    stage_dir = Path("/tmp/wt-staging-test.oracle-stage")
    if stage_dir.exists():
        print(f"FAIL: S1-R4: Staging directory was not removed in finally block: {stage_dir}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R4: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
