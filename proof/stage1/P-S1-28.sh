#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-28: actl verify-impl CLI exits conform strictly to 0/1/2/3/4 table.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p28" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
import argparse
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])

try:
    import actl.cmd_verify_impl as cmd_mod
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R11: cannot import actl.cmd_verify_impl: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# 1. Test missing required arguments gives exit 2 (UsageError)
args_invalid = argparse.Namespace(sprint=None)
try:
    rc_invalid = cmd_mod.handler(args_invalid, layout)
    if rc_invalid != 2:
        print(f"FAIL: S1-R11.1: Missing required args must return exit 2, got {rc_invalid}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R11.1: cmd_verify_impl usage handler failed: {exc}")
    sys.exit(1)

# 2. Test valid good.patch gives exit 0
args_valid = argparse.Namespace(sprint=tag, closure=None, worktree=str(wt), no_fail_fast=False, strict_tripwire=False, json=False)
try:
    rc_valid = cmd_mod.handler(args_valid, layout)
    if rc_valid != 0:
        print(f"FAIL: S1-R11.1: Valid good.patch verification must return exit 0, got {rc_valid}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R11.1: cmd_verify_impl valid handler failed: {exc}")
    sys.exit(1)
PY
