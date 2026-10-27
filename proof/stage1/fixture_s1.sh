#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# proof/stage1/fixture_s1.sh - Isolated testbed builder for Stage 1 proofs.
# Builds hermetic ACTL_ROOT, installs golden sprint, clones target worktree at
# exact contract base_sha, and fails closed if a requested patch is missing or fails.
set -euo pipefail

create_stage1_sandbox() {
  local sandbox_name="$1"
  local patch_name="${2:-}"
  local sdir="${ACTL_ROOT:-/tmp}/s1_sandboxes/${sandbox_name}"
  rm -rf "$sdir"
  mkdir -p "$sdir"

  local repo_dir="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  local tag="2026-10-16_public-profiles"

  # 1. Install sprint layout and target repo at base_sha
  local built_sha
  built_sha="$(bash "${repo_dir}/fixtures/golden/build_golden.sh" --install-sprint "$sdir" --tag "$tag" | tail -n 1)"

  # Verify contract base_sha matches built_sha
  local contract_file="${sdir}/records/target-repo/${tag}/contract-005.json"
  if [[ ! -f "$contract_file" ]]; then
    echo "FAIL: fixture_s1: contract-005.json missing at $contract_file" >&2
    return 2
  fi
  local contract_base_sha
  contract_base_sha="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_sha"])' "$contract_file")"
  if [[ "$built_sha" != "$contract_base_sha" ]]; then
    echo "FAIL: fixture_s1: built_sha ($built_sha) != contract base_sha ($contract_base_sha)" >&2
    return 2
  fi

  # 2. Create isolated candidate worktree at exact contract base_sha on wip/006
  local wt="${sdir}/sprints/target-repo/${tag}/workspaces/implementer-006"
  mkdir -p "$(dirname "$wt")"
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
    git -c core.hooksPath=/dev/null clone -q --local --no-hardlinks "${sdir}/repos/target-repo" "$wt"
  (
    cd "$wt"
    GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
      git -c core.hooksPath=/dev/null checkout -q -b "wip/006" "$contract_base_sha"
    local head_sha
    head_sha="$(git rev-parse HEAD)"
    if [[ "$head_sha" != "$contract_base_sha" ]]; then
      echo "FAIL: fixture_s1: worktree HEAD ($head_sha) != base_sha ($contract_base_sha)" >&2
      exit 2
    fi
    if [[ -n "$patch_name" ]]; then
      local patch_file="${repo_dir}/fixtures/golden/implementations/${patch_name}"
      if [[ ! -f "$patch_file" ]]; then
        echo "FAIL: fixture_s1: requested golden patch does not exist: $patch_file" >&2
        exit 2
      fi
      GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
        git -c core.hooksPath=/dev/null apply "$patch_file"
      GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
        git -c core.hooksPath=/dev/null add -A
      GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \
        GIT_AUTHOR_NAME="Candidate" GIT_AUTHOR_EMAIL="cand@example.test" GIT_AUTHOR_DATE="2026-01-02T00:00:00+0000" \
        GIT_COMMITTER_NAME="Candidate" GIT_COMMITTER_EMAIL="cand@example.test" GIT_COMMITTER_DATE="2026-01-02T00:00:00+0000" \
        git -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "feat(actl): apply ${patch_name} (WI-S1-TEST)"
    fi
  ) || return 2

  echo "$sdir|$wt"
}

# Retarget contract["scope"]["path"] to sprint_dir/scope_overrides/<name>
# without mutating the locked oracle directory (G1 must stay green).
apply_scope_override() {
  local sdir="$1"
  local override_name="${2:-bad_testcount.txt}"
  local tag="2026-10-16_public-profiles"
  local repo_dir="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
  local sprint="${sdir}/records/target-repo/${tag}"
  local src="${repo_dir}/fixtures/golden/sprint/scope_overrides/${override_name}"
  if [[ ! -f "$src" ]]; then
    echo "FAIL: fixture_s1: missing golden scope override $src" >&2
    return 4
  fi
  mkdir -p "${sprint}/scope_overrides"
  cp "$src" "${sprint}/scope_overrides/${override_name}"
  python3 - "$sprint/contract-005.json" "scope_overrides/${override_name}" <<'PY'
import json
import sys
from pathlib import Path

p = Path(sys.argv[1])
doc = json.loads(p.read_text(encoding="utf-8"))
doc.setdefault("scope", {})["path"] = sys.argv[2]
p.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
PY
}
