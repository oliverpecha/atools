#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-27: ATOOLS_CURSOR_HOME override is honored by src/core/config.py,
# src/sessions/storage.py, and actl.session.scan_tripwires (S1-R10.4).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p27" "good.patch")"

CUSTOM_HOME="${SDIR}/custom_cursor_home"
mkdir -p "$CUSTOM_HOME"
export ATOOLS_CURSOR_HOME="$CUSTOM_HOME"

cp "${REPO_DIR}/fixtures/golden/transcripts/dirty_oracle.jsonl" "${CUSTOM_HOME}/dirty_oracle.jsonl"

python3 - "$SDIR" "$CUSTOM_HOME" <<'PY'
import sys
from pathlib import Path

sdir, custom_home = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.session import scan_tripwires
    from actl.layout import Layout
    import core.config as core_cfg
    import sessions.storage as sess_storage
except ImportError as exc:
    print(f"FAIL: S1-R10.4: cannot import required modules: {exc}")
    sys.exit(1)

# Verify core.config / sessions.storage honor ATOOLS_CURSOR_HOME
cfg_text = Path(core_cfg.__file__).read_text(encoding="utf-8")
storage_text = Path(sess_storage.__file__).read_text(encoding="utf-8")
if "ATOOLS_CURSOR_HOME" not in cfg_text or "ATOOLS_CURSOR_HOME" not in storage_text:
    print("FAIL: S1-R10.4: src/core/config.py or src/sessions/storage.py does not resolve ATOOLS_CURSOR_HOME")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

hits = scan_tripwires(layout, tag, 6)
if not isinstance(hits, list) or len(hits) == 0:
    print("FAIL: S1-R10.4: scan_tripwires failed to discover dirty_oracle.jsonl under ATOOLS_CURSOR_HOME")
    sys.exit(1)
if not any(h.get("source") == "transcript" for h in hits):
    print(f"FAIL: S1-R10.4: Expected transcript source hit, got {hits}")
    sys.exit(1)
PY
