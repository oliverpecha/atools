#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-05: bad_secret.patch fails G5 with secret pattern line.
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

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p05_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)
wt = root / "wt_secret"
wt.mkdir(parents=True, exist_ok=True)

try:
    results = check_guards(layout, "2026-10-16_public-profiles", wt)
    g5 = next((r for r in results if r.id == "G5"), None)
    if not g5 or g5.exit_code != 1:
        print("FAIL: S1-R3: G5 did not fail as expected on secret addition")
        sys.exit(1)
    if "secret pattern" not in (g5.failing_line or ""):
        print(f"FAIL: S1-R3: G5 failing_line missing expected text: {g5.failing_line}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards invocation failed: {exc}")
    sys.exit(1)
PY
