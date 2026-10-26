#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-25: Active session name collision in dispatch-impl halts with exit 3.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
import argparse
try:
    import actl.cmd_dispatch_impl as cmd_mod
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl.cmd_dispatch_impl: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
args = argparse.Namespace(sprint="2026-10-16_public-profiles", mode="detach", tier="cheap", engine=None, no_run=False, strict_tripwire=False, json=False)
try:
    cmd_mod.handler(args, layout)
except Exception as exc:
    print(f"FAIL: S1-R9: dispatch_impl collision check failed: {exc}")
    sys.exit(1)
PY
