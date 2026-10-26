#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-13: O1 stages oracle proofs into sibling scratch dir and cleans up in finally.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p13" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])
oracle = sdir / "records" / "target-repo" / "2026-10-16_public-profiles" / "oracle-003"

try:
    from actl.verify import run_o1
except ImportError as exc:
    print(f"FAIL: S1-R4: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

stage_dir = Path(f"{wt}.oracle-stage")
try:
    steps = run_o1(oracle, wt)
    if stage_dir.exists():
        print(f"FAIL: S1-R4: Staging directory was not removed in finally block: {stage_dir}")
        sys.exit(1)
    if (wt / "proofs").exists() or (wt / "probe.sh").exists():
        print("FAIL: S1-R4.2: Oracle files leaked into candidate worktree")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R4: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
