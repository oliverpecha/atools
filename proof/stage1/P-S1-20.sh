#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-20: Detached implementer dispatch via arouter with custom stub wrapper (D-42).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

python3 - <<'PY'
import os
import sys
import argparse
from pathlib import Path

try:
    import actl.cmd_dispatch_impl as cmd_mod
    from actl.verify import verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import dispatch_impl or verify_impl: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p20_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)

# Controlled stub wrapper writing mock closure and exiting with code 7 (D-42)
stub_bin = root / "stub_router.sh"
stub_bin.write_text("#!/bin/sh\nexit 7\n")
stub_bin.chmod(0o755)

args = argparse.Namespace(sprint="2026-10-16_public-profiles", mode="detach", tier="cheap", engine=str(stub_bin), no_run=False, strict_tripwire=False, json=False)

try:
    rc = cmd_mod.handler(args, layout)
    if rc not in (0, 7):
        print(f"FAIL: S1-R9: Stub wrapper exit code 7 not propagated, got: {rc}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R9: dispatch_impl stub execution failed: {exc}")
    sys.exit(1)
PY
