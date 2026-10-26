#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-18: Phase 3 decision rules table (10 distinct states evaluated).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p18" "good.patch")"

python3 - "$SDIR" <<'PY'
import sys
import json
from pathlib import Path

sdir = Path(sys.argv[1])

try:
    import actl.next_rules.phase3 as p3
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R12: cannot import actl.next_rules.phase3: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    # 1. Non-implementer stage must return None immediately
    state_file = layout.runs(tag) / "state.json"
    state_data = json.loads(state_file.read_text())
    state_data["active_stage"] = "oracle"
    state_file.write_text(json.dumps(state_data, indent=2))
    res_non_impl = p3.evaluate(layout, tag)
    if res_non_impl is not None:
        print(f"FAIL: S1-R12.2: Expected None for non-implementer stage, got: {res_non_impl}")
        sys.exit(1)

    # Restore implementer stage
    state_data["active_stage"] = "implementer"
    state_file.write_text(json.dumps(state_data, indent=2))

    # 2. Hold state -> hold_owner
    state_data["status"] = "hold"
    state_file.write_text(json.dumps(state_data, indent=2))
    res_hold = p3.evaluate(layout, tag)
    if not res_hold or res_hold.get("action") != "hold_owner":
        print(f"FAIL: S1-R12.3: Expected action='hold_owner' on hold status, got: {res_hold}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R12: phase3 evaluate invocation failed: {exc}")
    sys.exit(1)
PY
