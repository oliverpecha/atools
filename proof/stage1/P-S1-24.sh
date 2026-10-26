#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-24: Original log unlinked only after verification artifact fsync.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p24" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])

try:
    from actl.verify import verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R15: cannot import actl.verify.verify_impl: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# Stage pre-existing session log
raw_logs_dir = sdir / "sprints" / "target-repo" / tag / "runs" / "logs"
raw_logs_dir.mkdir(parents=True, exist_ok=True)
sess_name = "test-session-001"
source_log = raw_logs_dir / f"{sess_name}.log"
source_log.write_text("session active output\n")

try:
    res = verify_impl(layout, tag, worktree=wt)
    ver_path = layout.runs(tag) / "verification-001.json"
    if not ver_path.exists():
        print(f"FAIL: S1-R15: verification-001.json must exist on disk: {ver_path}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R15: verify_impl invocation failed: {exc}")
    sys.exit(1)
PY
