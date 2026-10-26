#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-25: Active session name collision in dispatch-impl halts with exit 3.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p25" "")"

python3 - "$SDIR" <<'PY'
import sys
import argparse
from pathlib import Path

sdir = Path(sys.argv[1])

try:
    import actl.cmd_dispatch_impl as cmd_mod
    from actl.layout import Layout
    from actl.exceptions import StateIntegrityError
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl modules: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# First dispatch stages attempt 001
args1 = argparse.Namespace(sprint=tag, mode="detach", tier="cheap", engine=None, no_run=True, strict_tripwire=False, json=False)
try:
    rc1 = cmd_mod.handler(args1, layout)
    if rc1 != 0:
        print(f"FAIL: S1-R9: Initial setup dispatch failed with code {rc1}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R9: dispatch_impl handler failed: {exc}")
    sys.exit(1)

# Second dispatch with identical session name collision must halt with exit 3 or StateIntegrityError
args2 = argparse.Namespace(sprint=tag, mode="detach", tier="cheap", engine=None, no_run=False, strict_tripwire=False, json=False)
try:
    rc2 = cmd_mod.handler(args2, layout)
    if rc2 != 3:
        print(f"FAIL: S1-R9.2: Expected exit code 3 on active session collision, got {rc2}")
        sys.exit(1)
except StateIntegrityError:
    pass # Expected state integrity halt
except Exception as exc:
    print(f"FAIL: S1-R9.2: Unexpected exception on collision check: {exc}")
    sys.exit(1)
PY
