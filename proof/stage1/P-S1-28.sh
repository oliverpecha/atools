#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-28: actl verify-impl CLI exits conform strictly to 0/1/2/3/4 table.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
import argparse
try:
    import actl.cmd_verify_impl as cmd_mod
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R11: cannot import actl.cmd_verify_impl: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
args = argparse.Namespace(sprint="2026-10-16_public-profiles", closure=Path("/tmp/closure.json"), worktree=None, no_fail_fast=False, strict_tripwire=False, json=False)
try:
    rc = cmd_mod.handler(args, layout)
    if rc not in (0, 1, 2, 3, 4):
        print(f"FAIL: S1-R11: Invalid CLI exit code: {rc}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R11: cmd_verify_impl handler invocation failed: {exc}")
    sys.exit(1)
PY
