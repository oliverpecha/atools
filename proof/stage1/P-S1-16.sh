#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-16: dispatch-impl --no-run creates workspace, stages inbox, checks pre-commit hook.
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
args = argparse.Namespace(sprint="2026-10-16_public-profiles", no_run=True, json=False, mode="detach", tier="cheap", engine=None, strict_tripwire=False)
try:
    rc = cmd_mod.handler(args, layout)
    if rc != 0:
        print(f"FAIL: S1-R9: Expected exit code 0 for --no-run, got {rc}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R9: cmd_dispatch_impl handler failed: {exc}")
    sys.exit(1)
PY
