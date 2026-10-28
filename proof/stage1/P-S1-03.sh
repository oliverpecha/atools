#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-03: bad_scope.patch fails G3 with expected line; good.patch passes G3;
# symlink mode 120000 fails G3 (S1-R3.3).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_GOOD WT_GOOD <<< "$(create_stage1_sandbox "p03_good" "good.patch")"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p03_bad" "bad_scope.patch")"
IFS='|' read -r SDIR_SYM WT_SYM <<< "$(create_stage1_sandbox "p03_sym" "good.patch")"

# Add a symlink in WT_SYM (mode 120000 must fail G3 even on an allowed path)
(
  cd "$WT_SYM"
  ln -s profile.py api/link_profile.py
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    git -c core.hooksPath=/dev/null add api/link_profile.py
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    GIT_AUTHOR_NAME="Cand" GIT_AUTHOR_EMAIL="c@example.test" GIT_AUTHOR_DATE="2026-01-02T00:00:00+0000" \
    GIT_COMMITTER_NAME="Cand" GIT_COMMITTER_EMAIL="c@example.test" GIT_COMMITTER_DATE="2026-01-02T00:00:00+0000" \
    git -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "feat(actl): add symlink (WI-S1-TEST)"
)

python3 - "$SDIR_GOOD" "$WT_GOOD" "$SDIR_BAD" "$WT_BAD" "$SDIR_SYM" "$WT_SYM" <<'PY'
import sys
from pathlib import Path

sdir_good, wt_good, sdir_bad, wt_bad, sdir_sym, wt_sym = [Path(x) for x in sys.argv[1:7]]

try:
    from actl.verify import check_guards
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R3.3: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

exp = schemas.load_expected()["cases"]["bad_scope"]["expect"]
tag = "2026-10-16_public-profiles"

# 1. Positive control: good.patch passes G3
res_good = check_guards(Layout(sdir_good), tag, wt_good)
g3_good = next((r for r in res_good if r.id == "G3"), None)
if g3_good is None or g3_good.exit_code != 0:
    print(f"FAIL: S1-R3.3: Expected G3 exit_code 0 on good.patch, got {g3_good}")
    sys.exit(1)

# 2. Negative control: bad_scope.patch fails G3 with expected substring from expected.d
res_bad = check_guards(Layout(sdir_bad), tag, wt_bad)
g3_bad = next((r for r in res_bad if r.id == "G3"), None)
if g3_bad is None or g3_bad.exit_code != exp["exit"]:
    print(f"FAIL: S1-R3.3: Expected G3 exit_code {exp['exit']} on bad_scope.patch, got {g3_bad}")
    sys.exit(1)
if exp["failing_line_contains"] not in (g3_bad.failing_line or ""):
    print(f"FAIL: S1-R3.3: G3 failing_line missing {exp['failing_line_contains']!r}: {g3_bad.failing_line!r}")
    sys.exit(1)

# 3. Symlink mode 120000 fails G3 on a path that is otherwise allowed (api/ is green on good.patch)
import subprocess
ls = subprocess.run(
    ["git", "-C", str(wt_sym), "ls-files", "-s", "api/link_profile.py"],
    capture_output=True, text=True, check=True,
)
if "120000" not in ls.stdout:
    print(f"FAIL: S1-R3.3: expected git mode 120000 for api/link_profile.py, got {ls.stdout!r}")
    sys.exit(1)
res_sym = check_guards(Layout(sdir_sym), tag, wt_sym)
g3_sym = next((r for r in res_sym if r.id == "G3"), None)
if g3_sym is None or g3_sym.exit_code != 1:
    print(f"FAIL: S1-R3.3: Expected G3 to reject symlink mode 120000, got {g3_sym}")
    sys.exit(1)
if "api/link_profile.py" not in (g3_sym.failing_line or ""):
    print(f"FAIL: S1-R3.3: symlink failing_line must name the otherwise-allowed path, got {g3_sym.failing_line!r}")
    sys.exit(1)
PY
