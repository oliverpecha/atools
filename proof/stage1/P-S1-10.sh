#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-10: Prove G3 delegates directly to actl.scope.match (via spy wrapper)
# and converts ValueError from scope.match into red G3 exit_code=1 (GD-01 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p10" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path
from unittest.mock import patch

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.verify import check_guards
    from actl.layout import Layout
    import actl.scope as scope
except ImportError as exc:
    print(f"FAIL: S1-R3.3: cannot import actl modules: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# 1. Spy on actl.scope.match during check_guards on good.patch (touches api/profile.py)
observed_paths: list[str] = []
orig_match = scope.match

def spy_match(rules, path):
    observed_paths.append(path)
    return orig_match(rules, path)

with patch("actl.scope.match", side_effect=spy_match):
    results = check_guards(layout, tag, wt)

g3 = next((r for r in results if r.id == "G3"), None)
if g3 is None or g3.exit_code != 0:
    print(f"FAIL: S1-R3.3: Expected G3 exit_code 0 on good.patch, got {g3}")
    sys.exit(1)
if "api/profile.py" not in observed_paths:
    print(f"FAIL: S1-R3.3: G3 did not delegate to actl.scope.match for 'api/profile.py'; observed={observed_paths}")
    sys.exit(1)

# 2. When actl.scope.match raises ValueError, G3 catches it and returns red (exit_code=1)
def raising_match(rules, path):
    raise ValueError("simulated invalid path character")

with patch("actl.scope.match", side_effect=raising_match):
    res_err = check_guards(layout, tag, wt)

g3_err = next((r for r in res_err if r.id == "G3"), None)
if g3_err is None or g3_err.exit_code != 1:
    print(f"FAIL: S1-R3.3: G3 must convert scope.match ValueError into exit_code=1, got {g3_err}")
    sys.exit(1)
PY
