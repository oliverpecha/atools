#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# proof/stage1/fixture_s1.sh - Isolated testbed builder for Stage 1 proofs.
# Builds hermetic ACTL_ROOT, installs golden sprint, clones target worktree,
# and applies specified golden patches.
set -euo pipefail

create_stage1_sandbox() {
  local sandbox_name="$1"
  local patch_name="${2:-}"
  local sdir="${ACTL_ROOT:-/tmp}/s1_sandboxes/${sandbox_name}"
  rm -rf "$sdir"
  mkdir -p "$sdir"

  local repo_dir="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

  # 1. Install sprint layout and target repo at base_sha
  bash "${repo_dir}/fixtures/golden/build_golden.sh" --install-sprint "$sdir" --tag "2026-10-16_public-profiles" >/dev/null

  # 2. Create isolated candidate worktree
  local wt="${sdir}/worktrees/${sandbox_name}"
  mkdir -p "$(dirname "$wt")"
  git -c core.hooksPath=/dev/null clone -q -b main "${sdir}/repos/target-repo" "$wt"
  (
    cd "$wt"
    git -c core.hooksPath=/dev/null checkout -q -b "wip/001"
    if [[ -n "$patch_name" ]]; then
      local patch_file="${repo_dir}/fixtures/golden/implementations/${patch_name}"
      if [[ -f "$patch_file" ]]; then
        git -c core.hooksPath=/dev/null apply "$patch_file"
        git -c core.hooksPath=/dev/null add -A
        git -c core.hooksPath=/dev/null commit -q -m "candidate: applied ${patch_name}"
      fi
    fi
  )

  echo "$sdir|$wt"
}
