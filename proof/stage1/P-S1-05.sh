#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-05: bad_secret.patch fails G5 with expected substring; good.patch passes G5 (S1-R3.5).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p05_ok" "good.patch")"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p05_bad" "bad_secret.patch")"

python3 - "$SDIR_OK" "$WT_OK" "$SDIR_BAD" "$WT_BAD" <<'PY'
import sys
from pathlib import Path

sdir_ok, wt_ok, sdir_bad, wt_bad = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.verify import check_guards
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R3.5: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

exp = schemas.load_expected()["cases"]["bad_secret"]["expect"]
tag = "2026-10-16_public-profiles"

# 1. Positive control: good.patch passes G5
res_ok = check_guards(Layout(sdir_ok), tag, wt_ok)
g5_ok = next((r for r in res_ok if r.id == "G5"), None)
if g5_ok is None or g5_ok.exit_code != 0:
    print(f"FAIL: S1-R3.5: Expected G5 exit_code 0 on good.patch, got {g5_ok}")
    sys.exit(1)

# 2. Negative control: bad_secret.patch fails G5
res_bad = check_guards(Layout(sdir_bad), tag, wt_bad)
g5_bad = next((r for r in res_bad if r.id == "G5"), None)
if g5_bad is None or g5_bad.exit_code != exp["exit"]:
    print(f"FAIL: S1-R3.5: Expected G5 exit_code {exp['exit']} on bad_secret.patch, got {g5_bad}")
    sys.exit(1)
if exp["failing_line_contains"] not in (g5_bad.failing_line or ""):
    print(f"FAIL: S1-R3.5: G5 failing_line missing {exp['failing_line_contains']!r}: {g5_bad.failing_line!r}")
    sys.exit(1)
PY
