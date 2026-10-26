#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-27: Tripwire scanner honors ATOOLS_CURSOR_HOME override.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

export ATOOLS_CURSOR_HOME="/tmp/mock-cursor-home"
python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.session import scan_tripwires
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R10: cannot import actl.session.scan_tripwires: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
try:
    hits = scan_tripwires(layout, "2026-10-16_public-profiles", 1)
except Exception as exc:
    print(f"FAIL: S1-R10: scan_tripwires invocation failed: {exc}")
    sys.exit(1)
PY
