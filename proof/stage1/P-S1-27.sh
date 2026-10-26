#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-27: Tripwire scanner honors ATOOLS_CURSOR_HOME override.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

export ATOOLS_CURSOR_HOME="/tmp/mock-cursor-home"
python3 - <<'PY'
import os
import sys
from pathlib import Path

try:
    from actl.session import scan_tripwires
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R10: cannot import actl.session.scan_tripwires: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p27_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)

custom_home = Path("/tmp/mock-cursor-home")
custom_home.mkdir(parents=True, exist_ok=True)
dirty_transcript = custom_home / "dirty.jsonl"
dirty_transcript.write_text('{"message": "reading records/oracle/proofs/01.sh"}\n')

try:
    hits = scan_tripwires(layout, "2026-10-16_public-profiles", 1)
    if not isinstance(hits, list) or len(hits) == 0:
        print("FAIL: S1-R10.4: scan_tripwires failed to discover transcript under ATOOLS_CURSOR_HOME")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R10.4: scan_tripwires invocation failed: {exc}")
    sys.exit(1)
finally:
    import shutil
    shutil.rmtree(custom_home, ignore_errors=True)
PY
