#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-15: prior_attempt.json has strictly 4 keys and leaks no oracle tests.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p15" "bad_scope.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
import json
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])

try:
    from actl.verify import verify_impl
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R7: cannot import actl modules: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    res = verify_impl(layout, tag, worktree=wt)
    if res.get("exit_code") != 1:
        print(f"FAIL: S1-R7: Expected exit_code 1 for bad_scope, got {res.get('exit_code')}")
        sys.exit(1)
    prior_path = layout.inbox(tag, "implementer") / "prior_attempt.json"
    if not prior_path.exists():
        print(f"FAIL: S1-R7: verify_impl failed to write prior_attempt.json on exit_code 1: {prior_path}")
        sys.exit(1)
    data = json.loads(prior_path.read_text())
    expected_keys = {"diff", "failing_step", "failing_line", "closures_submitted"}
    if set(data.keys()) != expected_keys:
        print(f"FAIL: S1-R7: prior_attempt.json keys {set(data.keys())} != {expected_keys}")
        sys.exit(1)
    errs = schemas.validate("prior_attempt", data)
    if errs:
        print(f"FAIL: S1-R7: prior_attempt schema invalid: {errs}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R7: verify_impl invocation failed: {exc}")
    sys.exit(1)
PY
