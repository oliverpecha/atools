#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-11: G4 AST analysis rejects hollow tests (pass, ellipsis, docstring only).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p11" "good.patch")"

# Introduce hollow test into candidate worktree
cat <<'EOF' >> "${WT}/test/test_public.py"

def test_hollow_pass():
    """Docstring only."""
    pass

def test_hollow_ellipsis():
    ...

def test_hollow_assert_true():
    assert True
EOF
(cd "$WT" && git -c core.hooksPath=/dev/null commit -q -a -m "candidate: add hollow tests")

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
wt = Path(sys.argv[2])

try:
    from actl.verify import check_guards
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

try:
    results = check_guards(layout, tag, wt)
    g4 = next((r for r in results if r.id == "G4"), None)
    if not g4 or g4.exit_code != 1:
        print("FAIL: S1-R3: G4 did not fail as expected on hollow test body")
        sys.exit(1)
    if "hollow" not in (g4.failing_line or "").lower() and "count" not in (g4.failing_line or "").lower():
        print(f"FAIL: S1-R3: G4 failing_line missing expected rejection text: {g4.failing_line}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards invocation failed: {exc}")
    sys.exit(1)
PY
