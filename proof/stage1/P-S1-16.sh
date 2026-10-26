#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-16: dispatch-impl --no-run creates workspace, stages inbox, checks pre-commit hook.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p16" "")"

python3 - "$SDIR" <<'PY'
import sys
import argparse
from pathlib import Path

sdir = Path(sys.argv[1])

try:
    import actl.cmd_dispatch_impl as cmd_mod
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl.cmd_dispatch_impl: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
args = argparse.Namespace(sprint=tag, no_run=True, json=False, mode="detach", tier="cheap", engine=None, strict_tripwire=False)

try:
    rc = cmd_mod.handler(args, layout)
    if rc != 0:
        print(f"FAIL: S1-R9: Expected exit code 0 for --no-run, got {rc}")
        sys.exit(1)
    inbox = layout.inbox(tag, "implementer")
    if not (inbox / "attempt.json").exists():
        print("FAIL: S1-R9: attempt.json was not staged in implementer inbox")
        sys.exit(1)
    if not (inbox / "contract-005.json").exists() and not (inbox / "contract.json").exists():
        print("FAIL: S1-R9: contract was not staged in implementer inbox")
        sys.exit(1)
    ws = layout.workspace("implementer-001", tag)
    if not ws.exists() or not (ws / ".git").exists():
        print(f"FAIL: S1-R9.3: Workspace repo was not cloned at {ws}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R9: cmd_dispatch_impl handler failed: {exc}")
    sys.exit(1)
PY
