#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-29: O2 execution:
# - Positive control: good.patch returns StepResult(id='O2', exit_code=0) with normalized --junitxml=<tmp_xml>
# - Negative control: bad_regression_o2.patch returns id='O2:test_users::test_get_user_unknown_returns_none', exit_code=1
# - Grammar control: disallowed commands raise ValueError (S1-R6).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p29_ok" "good.patch")"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p29_bad" "bad_regression_o2.patch")"

python3 - "$WT_OK" "$WT_BAD" <<'PY'
import sys
from pathlib import Path

wt_ok, wt_bad = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.verify import run_o2
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R6: cannot import actl.verify.run_o2: {exc}")
    sys.exit(1)

exp = schemas.load_expected()["cases"]["bad_regression_o2"]["expect"]

# 1. Positive control: good.patch passes O2 with id == 'O2' and normalized cmd
res_ok = run_o2(wt_ok)
if not isinstance(res_ok, list) or len(res_ok) != 1:
    print(f"FAIL: S1-R6.1: Expected single-element list from run_o2, got {res_ok!r}")
    sys.exit(1)
if res_ok[0].id != "O2" or res_ok[0].exit_code != 0:
    print(f"FAIL: S1-R6.4: Expected id='O2' and exit_code=0 on good.patch, got {res_ok[0]}")
    sys.exit(1)
if "--junitxml=<tmp_xml>" not in res_ok[0].cmd:
    print(f"FAIL: S1-R13.2: Expected normalized '--junitxml=<tmp_xml>' in O2 cmd, got {res_ok[0].cmd!r}")
    sys.exit(1)

# 2. Negative control: bad_regression_o2.patch fails with exact expected step ID
res_bad = run_o2(wt_bad)
if not isinstance(res_bad, list) or len(res_bad) != 1:
    print(f"FAIL: S1-R6.4: Expected single-element list from run_o2 on failure, got {res_bad!r}")
    sys.exit(1)
o2_bad = res_bad[0]
if o2_bad.exit_code != 1 or o2_bad.id != exp["failing_step"]:
    print(f"FAIL: S1-R6.4: Expected id={exp['failing_step']!r} and exit_code 1, got id={o2_bad.id!r} exit={o2_bad.exit_code}")
    sys.exit(1)
if exp["failing_line_contains"] not in (o2_bad.failing_line or ""):
    print(f"FAIL: S1-R6.4: failing_line missing {exp['failing_line_contains']!r}: {o2_bad.failing_line!r}")
    sys.exit(1)

# 3. Disallowed command grammar raises ValueError specifically
for bad_cmd in ("bash run.sh", "python3 -c 'print(1)'", "pytest; echo pwned"):
    try:
        run_o2(wt_ok, repo_test_cmd=bad_cmd)
        print(f"FAIL: S1-R6.2: Disallowed repo_test_cmd was not rejected: {bad_cmd!r}")
        sys.exit(1)
    except ValueError:
        pass
PY
