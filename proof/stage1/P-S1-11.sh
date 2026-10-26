#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-11: G4 AST analysis rejects hollow tests (pass, ellipsis, docstring only).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.verify import check_guards
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
try:
    results = check_guards(layout, "2026-10-16_public-profiles", Path("/tmp/wt-hollow"))
    g4 = next((r for r in results if r.id == "G4"), None)
    if not g4 or g4.exit_code != 1:
        print("FAIL: S1-R3: G4 did not fail as expected on hollow test body")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards invocation failed: {exc}")
    sys.exit(1)
PY
