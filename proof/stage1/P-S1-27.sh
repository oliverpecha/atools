#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-27: Tripwire scanner honors ATOOLS_CURSOR_HOME override.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p27" "good.patch")"

# Use unique per-test directory under SDIR for isolated cursor home
CUSTOM_HOME="${SDIR}/custom_cursor_home"
mkdir -p "$CUSTOM_HOME"
export ATOOLS_CURSOR_HOME="$CUSTOM_HOME"

cat <<'EOF' > "${CUSTOM_HOME}/transcript.jsonl"
{"role": "assistant", "content": "Let me inspect records/oracle/proofs/01.sh"}
EOF

python3 - "$SDIR" "$CUSTOM_HOME" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
custom_home = Path(sys.argv[2])

try:
    from actl.session import scan_tripwires
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R10: cannot import actl.session.scan_tripwires: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    hits = scan_tripwires(layout, tag, 1)
    if not isinstance(hits, list) or len(hits) == 0:
        print("FAIL: S1-R10.4: scan_tripwires failed to discover transcript under ATOOLS_CURSOR_HOME")
        sys.exit(1)
    if hits[0].get("pattern") not in ("proofs/", "oracle", "records/"):
        print(f"FAIL: S1-R10.4: Unexpected matched pattern: {hits[0]}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R10.4: scan_tripwires invocation failed: {exc}")
    sys.exit(1)
PY
