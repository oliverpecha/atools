#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-03: bad_scope.patch fails G3 with expected line.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import os
import sys
from pathlib import Path

try:
    from actl.verify import check_guards
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p03_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)
wt = root / "wt_scope"
wt.mkdir(parents=True, exist_ok=True)

try:
    results = check_guards(layout, "2026-10-16_public-profiles", wt)
    g3 = next((r for r in results if r.id == "G3"), None)
    if not g3 or g3.exit_code != 1:
        print("FAIL: S1-R3: G3 did not fail as expected on bad scope")
        sys.exit(1)
    if "api/cli.py" not in (g3.failing_line or ""):
        print(f"FAIL: S1-R3: G3 failing_line missing expected path: {g3.failing_line}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards invocation failed: {exc}")
    sys.exit(1)
PY
