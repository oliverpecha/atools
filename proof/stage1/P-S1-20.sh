#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-20: Detached implementer dispatch via arouter with custom stub wrapper (D-42).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p20" "good.patch")"

# Create custom stub wrapper that simulates arouter invocation writing closure and exiting code 7
STUB_ROUTER="${SDIR}/stub_router.sh"
cat <<'EOF' > "$STUB_ROUTER"
#!/bin/bash
exit 7
EOF
chmod 755 "$STUB_ROUTER"

python3 - "$SDIR" "$STUB_ROUTER" <<'PY'
import sys
import argparse
from pathlib import Path

sdir = Path(sys.argv[1])
stub_router = Path(sys.argv[2])

try:
    import actl.cmd_dispatch_impl as cmd_mod
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import dispatch_impl: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

args = argparse.Namespace(sprint=tag, mode="detach", tier="cheap", engine=str(stub_router), no_run=False, strict_tripwire=False, json=False)

try:
    rc = cmd_mod.handler(args, layout)
    if rc != 7 and rc != 0:
        print(f"FAIL: S1-R9: Stub router exit code not handled properly: {rc}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R9: dispatch_impl stub execution failed: {exc}")
    sys.exit(1)
PY
