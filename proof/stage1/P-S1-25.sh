#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-25: Active session name collision in dispatch-impl halts with exit 3.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import os
import sys
import argparse
from pathlib import Path

try:
    import actl.cmd_dispatch_impl as cmd_mod
    from actl.layout import Layout
    from actl.exceptions import StateIntegrityError
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl modules: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p25_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)
args = argparse.Namespace(sprint="2026-10-16_public-profiles", mode="detach", tier="cheap", engine=None, no_run=False, strict_tripwire=False, json=False)

# Mock active collision detector
def mock_check_active(name):
    return True

try:
    rc = cmd_mod.handler(args, layout, active_session_checker=mock_check_active)
    if rc != 3:
        print(f"FAIL: S1-R9.2: Expected exit code 3 on active session collision, got {rc}")
        sys.exit(1)
except StateIntegrityError:
    pass # Expected integrity halt
except Exception as exc:
    print(f"FAIL: S1-R9.2: Unexpected exception on collision check: {exc}")
    sys.exit(1)
PY
