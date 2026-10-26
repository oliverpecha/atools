#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-09: Tampered oracle fails G1 with exit 3 halt (integrity_mismatch).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p09" "good.patch")"

# Tamper with the active oracle proof
ORACLE_DIR="${SDIR}/records/target-repo/2026-10-16_public-profiles/oracle-003"
echo "# tampered" >> "${ORACLE_DIR}/probe.sh"

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])

try:
    from actl.verify import check_guards
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    results = check_guards(layout, tag, wt)
    g1 = next((r for r in results if r.id == "G1"), None)
    if not g1 or g1.exit_code != 3:
        print(f"FAIL: S1-R3: Expected G1 halt code 3 on tampered oracle, got {getattr(g1, 'exit_code', None)}")
        sys.exit(1)
    if "integrity_mismatch" not in (g1.failing_line or ""):
        print(f"FAIL: S1-R3: Expected integrity_mismatch in failing_line, got: {g1.failing_line}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards invocation failed: {exc}")
    sys.exit(1)
PY
