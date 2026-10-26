#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-07: bad_proof_o1.patch fails O1 at 02_no_email.sh.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p07" "bad_proof_o1.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])
oracle = sdir / "records" / "target-repo" / "2026-10-16_public-profiles" / "oracle-003"

try:
    from actl.verify import run_o1
except ImportError as exc:
    print(f"FAIL: S1-R5: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

try:
    steps = run_o1(oracle, wt)
    step2 = next((s for s in steps if "02_no_email.sh" in s.id), None)
    if not step2 or step2.exit_code == 0:
        print("FAIL: S1-R5: O1 02_no_email.sh did not fail as expected")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R5: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
