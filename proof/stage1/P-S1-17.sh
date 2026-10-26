#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-17: scan_tripwires detects proofs/ access in ANSI logs and JSONL transcripts.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p17" "good.patch")"

python3 - "$SDIR" "$REPO_DIR" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
repo_dir = Path(sys.argv[2])
dirty_log = repo_dir / "fixtures" / "golden" / "logs" / "dirty_ansi.log"

try:
    from actl.session import scan_tripwires
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R10: cannot import actl.session.scan_tripwires: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    hits = scan_tripwires(layout, tag, 1, log_path=dirty_log)
    if not isinstance(hits, list) or len(hits) == 0:
        print("FAIL: S1-R10: scan_tripwires failed to detect oracle path in dirty log")
        sys.exit(1)
    if hits[0].get("pattern") not in ("proofs/", "oracle", "records/", "solution_key"):
        print(f"FAIL: S1-R10: Unexpected matched pattern: {hits[0]}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R10: scan_tripwires invocation failed: {exc}")
    sys.exit(1)
PY
