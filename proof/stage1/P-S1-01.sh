#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-01: Golden good.patch green, exit 0, verification record schema-valid,
# contrasted with bad_scope.patch failing (kills constant-pass / constant-fail stand-ins).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_GOOD WT_GOOD <<< "$(create_stage1_sandbox "p01_good" "good.patch")"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p01_bad" "bad_scope.patch")"

python3 - "$SDIR_GOOD" "$WT_GOOD" "$SDIR_BAD" "$WT_BAD" <<'PY'
import json
import sys
from pathlib import Path

sdir_good, wt_good, sdir_bad, wt_bad = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.verify import verify_impl
    from actl.layout import Layout
    import actl.schemas as schemas
    from actl.seq import read_state
except ImportError as exc:
    print(f"FAIL: S1-R1.1: cannot import actl.verify: {exc}")
    sys.exit(1)

expected = schemas.load_expected()
good_exp = expected["cases"]["good"]["expect"]
bad_exp = expected["cases"]["bad_scope"]["expect"]
tag = "2026-10-16_public-profiles"

# 1. Positive control: good.patch with valid closure
layout_good = Layout(sdir_good)
closure_good = sdir_good / "good_closure.json"
closure_good.write_text(json.dumps({
    "reason": "done",
    "blocking_step": None,
    "notes": ["Implemented public profiles per spec"],
    "backlog": [],
    "solution_key_divergence": None,
}), encoding="utf-8")

try:
    res = verify_impl(layout_good, tag, closure_path=closure_good, worktree=wt_good)
except Exception as exc:
    print(f"FAIL: S1-R1.3: verify_impl failed on good.patch: {exc}")
    sys.exit(1)

if not isinstance(res, dict):
    print(f"FAIL: S1-R1.3: verify_impl did not return a dict: {res!r}")
    sys.exit(1)

errs = schemas.validate("verification", res)
if errs:
    print(f"FAIL: S1-R1.3: verification schema invalid: {errs}")
    sys.exit(1)

if res.get("exit_code") != good_exp["exit"]:
    print(f"FAIL: S1-R1.3: expected exit_code {good_exp['exit']}, got {res.get('exit_code')}")
    sys.exit(1)
if res.get("failing_step") is not None or res.get("failing_line") is not None:
    print(f"FAIL: S1-R1.6: expected failing_step/line None, got {res.get('failing_step')}/{res.get('failing_line')}")
    sys.exit(1)

step_ids = [s.get("id") for s in res.get("steps", [])]
required_order = ["G1", "G2", "G3", "G4", "G5", "G6", "O1:01_public.sh", "O1:02_no_email.sh", "O1:03_private_404.sh", "O1:probe.sh", "O2"]
for req_id in required_order:
    if req_id not in step_ids:
        print(f"FAIL: S1-R2.1: expected executed step {req_id} in steps, got {step_ids}")
        sys.exit(1)
order_pos = [step_ids.index(x) for x in required_order]
if order_pos != sorted(order_pos):
    print(f"FAIL: S1-R2.1: pipeline order is not G1..G6, O1*, O2: {step_ids}")
    sys.exit(1)

runs_dir = layout_good.runs_dir(tag)
stamped_closure = runs_dir / "closure-006.json"
ver_file = runs_dir / "verification-007.json"
if not stamped_closure.is_file():
    print(f"FAIL: S1-R1.4: stamped closure-006.json not written to {stamped_closure}")
    sys.exit(1)
if res.get("parent") != "closure-006.json":
    print(f"FAIL: S1-R1.4: expected parent='closure-006.json', got {res.get('parent')}")
    sys.exit(1)
if not ver_file.is_file():
    print(f"FAIL: S1-R7.1: verification-007.json not written to {ver_file}")
    sys.exit(1)

state_after = read_state(layout_good, tag)
if state_after.get("closures_submitted") != 1 or state_after.get("attempts", {}).get("implementer") != 1:
    print(f"FAIL: S1-R1.4: state counters not updated properly: {state_after}")
    sys.exit(1)

# 2. Negative control: valid closure so G2 is green; bad_scope.patch fails at G3
layout_bad = Layout(sdir_bad)
closure_bad = sdir_bad / "bad_closure.json"
closure_bad.write_text(closure_good.read_text(encoding="utf-8"), encoding="utf-8")
res_bad = verify_impl(layout_bad, tag, closure_path=closure_bad, worktree=wt_bad)
if res_bad.get("exit_code") != bad_exp["exit"] or res_bad.get("failing_step") != bad_exp["failing_step"]:
    print(f"FAIL: S1-R1.5: negative control bad_scope did not fail at G3: {res_bad}")
    sys.exit(1)
PY
