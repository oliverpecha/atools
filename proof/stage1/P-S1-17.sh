#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-17: scan_tripwires detects proofs/ access in ANSI logs and JSONL transcripts.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

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
dirty_log = Path(f"{REPO_DIR}/fixtures/golden/logs/dirty_ansi.log")
try:
    hits = scan_tripwires(layout, "2026-10-16_public-profiles", 1, log_path=dirty_log)
    if not hits:
        print("FAIL: S1-R10: scan_tripwires failed to detect oracle path in dirty log")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R10: scan_tripwires invocation failed: {exc}")
    sys.exit(1)
PY
