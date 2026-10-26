#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-01: Golden good.patch green, exit 0, verification record schema-valid.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p01" "good.patch")"

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
    print(f"FAIL: S1-R1: cannot import actl.verify: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    res = verify_impl(layout, tag, worktree=wt)
    errs = schemas.validate("verification", res)
    if errs:
        print(f"FAIL: S1-R1.3: Verification schema validation failed: {errs}")
        sys.exit(1)
    if res.get("exit_code") != 0:
        print(f"FAIL: S1-R1: Expected exit_code 0 for good.patch, got {res.get('exit_code')}")
        sys.exit(1)
    if res.get("failing_step") is not None:
        print(f"FAIL: S1-R1.6: Expected failing_step None, got {res.get('failing_step')}")
        sys.exit(1)
    ver_path = layout.runs(tag) / "verification-001.json"
    if not ver_path.exists():
        print(f"FAIL: S1-R7.1: verification-001.json was not written to {ver_path}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R1: verify_impl invocation failed: {exc}")
    sys.exit(1)
PY
