#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-09: Tampered oracle fails G1 with exit 3 halt (integrity_mismatch).
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

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p09_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)
wt = root / "wt_tamper"
wt.mkdir(parents=True, exist_ok=True)

try:
    results = check_guards(layout, "2026-10-16_public-profiles", wt)
    g1 = next((r for r in results if r.id == "G1"), None)
    if not g1 or g1.exit_code != 3:
        print(f"FAIL: S1-R3: Expected G1 halt code 3, got {getattr(g1, 'exit_code', None)}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards invocation failed: {exc}")
    sys.exit(1)
PY
