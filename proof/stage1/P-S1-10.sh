#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-10: G3 delegates strictly to actl.scope.match.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p10" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])

try:
    from actl.verify import check_guards
    from actl.layout import Layout
    import actl.scope as scope
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl modules: {exc}")
    sys.exit(1)

rules = scope.parse("ALLOW: src/**\nFROZEN: test/**\n")
if scope.match(rules, "test/foo.py") != "frozen":
    print("FAIL: S1-R3: scope.match frozen rule failed")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    results = check_guards(layout, tag, wt)
    g3 = next((r for r in results if r.id == "G3"), None)
    if not g3 or g3.exit_code != 0:
        print("FAIL: S1-R3: G3 failed unexpectedly on good.patch")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards execution failed: {exc}")
    sys.exit(1)
PY
