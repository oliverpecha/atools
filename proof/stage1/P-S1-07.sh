#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-07: bad_proof_o1.patch fails O1 at 02_no_email.sh.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

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
    steps = run_o1(oracle, Path("/tmp/wt-o1"))
    step2 = next((s for s in steps if "02_no_email.sh" in s.id), None)
    if not step2 or step2.exit_code == 0:
        print("FAIL: S1-R5: O1 02_no_email.sh did not fail as expected")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R5: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
