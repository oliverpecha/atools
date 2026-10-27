#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-04: bad_testcount.patch fails G4 when test/test_users.py is thawed via
# scope_overrides/bad_testcount.txt; valid added test passes G4 (S1-R3.4, SA-6).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p04_bad" "bad_testcount.patch")"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p04_ok" "good.patch")"

TAG="2026-10-16_public-profiles"
# Apply the golden scope override thawing test/test_users.py (per SA-6)
for sdir in "$SDIR_BAD" "$SDIR_OK"; do
  cp "${REPO_DIR}/fixtures/golden/sprint/scope_overrides/bad_testcount.txt" \
     "${sdir}/records/target-repo/${TAG}/oracle-003/scope.txt"
done

python3 - "$SDIR_OK" "$WT_OK" "$SDIR_BAD" "$WT_BAD" <<'PY'
import sys
from pathlib import Path

sdir_ok, wt_ok, sdir_bad, wt_bad = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.verify import check_guards
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R3.4: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

exp = schemas.load_expected()["cases"]["bad_testcount"]["expect"]
tag = "2026-10-16_public-profiles"

# 1. Positive control: thawed test/test_users.py with all 4 tests intact passes G4
res_ok = check_guards(Layout(sdir_ok), tag, wt_ok)
g4_ok = next((r for r in res_ok if r.id == "G4"), None)
if g4_ok is None or g4_ok.exit_code != 0:
    print(f"FAIL: S1-R3.4: Expected G4 exit_code 0 when test count preserved, got {g4_ok}")
    sys.exit(1)

# 2. Negative control: bad_testcount.patch drops a test -> G4 fails with expected substring
res_bad = check_guards(Layout(sdir_bad), tag, wt_bad)
g4_bad = next((r for r in res_bad if r.id == "G4"), None)
if g4_bad is None or g4_bad.exit_code != exp["exit"]:
    print(f"FAIL: S1-R3.4: Expected G4 exit_code {exp['exit']} on bad_testcount.patch, got {g4_bad}")
    sys.exit(1)
if exp["failing_line_contains"] not in (g4_bad.failing_line or ""):
    print(f"FAIL: S1-R3.4: G4 failing_line missing {exp['failing_line_contains']!r}: {g4_bad.failing_line!r}")
    sys.exit(1)
PY
