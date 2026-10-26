#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-10: G3 delegates strictly to actl.scope.match.
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
    import actl.scope as scope
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl modules: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p10_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)

rules = scope.parse("ALLOW: src/**\nFROZEN: test/**\n")
if scope.match(rules, "test/foo.py") != "frozen":
    print("FAIL: S1-R3: scope.match frozen rule failed")
    sys.exit(1)

try:
    results = check_guards(layout, "2026-10-16_public-profiles", root)
    g3 = next((r for r in results if r.id == "G3"), None)
    if not g3:
        print("FAIL: S1-R3: check_guards must return a G3 step result")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards execution failed: {exc}")
    sys.exit(1)
PY
