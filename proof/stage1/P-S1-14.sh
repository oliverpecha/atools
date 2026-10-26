#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-14: O1 runs under strict environment allowlist (purges caller env).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p14" "good.patch")"

# Inject probe asserting that caller dirty env var is absent from execution env
ORACLE_DIR="${SDIR}/records/target-repo/2026-10-16_public-profiles/oracle-003"
cat <<'EOF' >> "${ORACLE_DIR}/probe.sh"
if [[ -n "${FORBIDDEN_VAR_TEST:-}" ]]; then
  echo "FAIL: FORBIDDEN_VAR_TEST leaked into O1 child environment" >&2
  exit 1
fi
EOF

export FORBIDDEN_VAR_TEST="must_not_leak"

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
    if not isinstance(steps, list) or len(steps) == 0:
        print("FAIL: S1-R5: run_o1 must return executed StepResults")
        sys.exit(1)
    if any(s.exit_code != 0 for s in steps):
        failing = [s for s in steps if s.exit_code != 0][0]
        print(f"FAIL: S1-R5: O1 step failed under isolated env: {failing.id} ({failing.failing_line})")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R5: run_o1 invocation failed: {exc}")
    sys.exit(1)
PY
