#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-07: good.patch passes all O1 steps in lexical order; bad_proof_o1.patch
# passes O1:01_public.sh and fails O1:02_no_email.sh with expected line (GD-01 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p07_ok" "good.patch")"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p07_bad" "bad_proof_o1.patch")"

python3 - "$SDIR_OK" "$WT_OK" "$SDIR_BAD" "$WT_BAD" <<'PY'
import sys
from pathlib import Path

sdir_ok, wt_ok, sdir_bad, wt_bad = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.verify import run_o1
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R5: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

exp = schemas.load_expected()["cases"]["bad_proof_o1"]["expect"]
tag = "2026-10-16_public-profiles"
oracle_ok = Layout(sdir_ok).sprint_dir(tag) / "oracle-003"
oracle_bad = Layout(sdir_bad).sprint_dir(tag) / "oracle-003"

# 1. Positive control: good.patch must execute all 4 O1 scripts in lexical order + probe.sh last and pass all
steps_ok = run_o1(oracle_ok, wt_ok)
expected_order = ["O1:01_public.sh", "O1:02_no_email.sh", "O1:03_private_404.sh", "O1:probe.sh"]
if [s.id for s in steps_ok] != expected_order:
    print(f"FAIL: S1-R5.1: Expected lexical O1 step order {expected_order}, got {[s.id for s in steps_ok]}")
    sys.exit(1)
if any(s.exit_code != 0 for s in steps_ok):
    print(f"FAIL: S1-R5.1: Expected all O1 steps to pass on good.patch, got {steps_ok}")
    sys.exit(1)

# 2. Negative control: bad_proof_o1.patch must pass 01_public.sh and fail 02_no_email.sh
steps_bad = run_o1(oracle_bad, wt_bad)
step1 = next((s for s in steps_bad if s.id == "O1:01_public.sh"), None)
step2 = next((s for s in steps_bad if s.id == exp["failing_step"]), None)
if step1 is None or step1.exit_code != 0:
    print(f"FAIL: S1-R5.1: Expected O1:01_public.sh to pass (exit 0) on bad_proof_o1.patch, got {step1}")
    sys.exit(1)
if step2 is None or step2.exit_code == 0:
    print(f"FAIL: S1-R5.1: Expected {exp['failing_step']} to fail on bad_proof_o1.patch, got {step2}")
    sys.exit(1)
if exp["failing_line_contains"] not in (step2.failing_line or ""):
    print(f"FAIL: S1-R5.3: failing_line missing {exp['failing_line_contains']!r}: {step2.failing_line!r}")
    sys.exit(1)
PY
