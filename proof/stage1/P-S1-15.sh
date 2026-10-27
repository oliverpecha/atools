#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-15: prior_attempt.json has strictly 4 keys with real diff and closures_submitted
# on exit_code 1, and is removed when a subsequent verification passes (S1-R7.3, S1-R7.4).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT_BAD <<< "$(create_stage1_sandbox "p15" "bad_scope.patch")"
# Also create a clean good worktree inside the same sprint sandbox
WT_GOOD="${SDIR}/sprints/target-repo/2026-10-16_public-profiles/workspaces/implementer-007"
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
  git -c core.hooksPath=/dev/null clone -q --local --no-hardlinks "${SDIR}/repos/target-repo" "$WT_GOOD"
(
  cd "$WT_GOOD"
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    git -c core.hooksPath=/dev/null checkout -q -b "wip/007"
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    git -c core.hooksPath=/dev/null apply "${REPO_DIR}/fixtures/golden/implementations/good.patch"
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    git -c core.hooksPath=/dev/null add -A
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    GIT_AUTHOR_NAME="Cand" GIT_AUTHOR_EMAIL="c@example.test" GIT_AUTHOR_DATE="2026-01-02T00:00:00+0000" \
    GIT_COMMITTER_NAME="Cand" GIT_COMMITTER_EMAIL="c@example.test" GIT_COMMITTER_DATE="2026-01-02T00:00:00+0000" \
    git -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "feat(actl): apply good.patch (WI-S1-TEST)"
)

python3 - "$SDIR" "$WT_BAD" "$WT_GOOD" <<'PY'
import json
import sys
from pathlib import Path

sdir, wt_bad, wt_good = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

try:
    from actl.verify import verify_impl
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R7.3: cannot import actl modules: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
closure_file = sdir / "closure.json"
closure_file.write_text(json.dumps({
    "reason": "done",
    "blocking_step": None,
    "notes": ["attempt 1"],
    "backlog": [],
    "solution_key_divergence": None,
}), encoding="utf-8")

# 1. Red verification writes prior_attempt.json with exact 4 keys and non-empty diff
res_bad = verify_impl(layout, tag, closure_path=closure_file, worktree=wt_bad)
if res_bad.get("exit_code") != 1:
    print(f"FAIL: S1-R7.3: Expected exit_code 1 on bad_scope, got {res_bad.get('exit_code')}")
    sys.exit(1)

prior_path = layout.inbox(tag, "implementer") / "prior_attempt.json"
if not prior_path.is_file():
    print(f"FAIL: S1-R7.3: prior_attempt.json not written at {prior_path}")
    sys.exit(1)

data = json.loads(prior_path.read_text(encoding="utf-8"))
if set(data.keys()) != {"diff", "failing_step", "failing_line", "closures_submitted"}:
    print(f"FAIL: S1-R7.3: prior_attempt.json keys mismatch: {set(data.keys())}")
    sys.exit(1)
if schemas.validate("prior_attempt", data) != []:
    print(f"FAIL: S1-R7.3: prior_attempt schema validation failed: {schemas.validate('prior_attempt', data)}")
    sys.exit(1)
import subprocess
contract_sha = json.loads((layout.sprint_dir(tag) / "contract-005.json").read_text(encoding="utf-8"))["base_sha"]
real_diff = subprocess.check_output(
    ["git", "-C", str(wt_bad), "diff", f"{contract_sha}..HEAD"],
    text=True,
)
if data["diff"] != real_diff:
    print("FAIL: S1-R7.3: prior_attempt.diff is not equal to git diff {base_sha}..HEAD")
    sys.exit(1)
if data["failing_step"] != "G3" or data["closures_submitted"] != 1:
    print(f"FAIL: S1-R7.3: prior_attempt content inaccurate: {data}")
    sys.exit(1)

# 2. Subsequent green verification removes prior_attempt.json (S1-R7.4)
res_good = verify_impl(layout, tag, closure_path=closure_file, worktree=wt_good)
if res_good.get("exit_code") != 0:
    print(f"FAIL: S1-R7.4: Expected exit_code 0 on good.patch, got {res_good.get('exit_code')}")
    sys.exit(1)
if prior_path.exists():
    print("FAIL: S1-R7.4: prior_attempt.json was not removed after green verification")
    sys.exit(1)
PY
