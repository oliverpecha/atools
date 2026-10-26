#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-02: Additive-change rule and PB-2 immutability (fork at layout-transition-verified).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR"

FORK_TAG="layout-transition-verified"
if ! git rev-parse -q --verify "$FORK_TAG" >/dev/null; then
  echo "FAIL: S1-R16: Fork tag $FORK_TAG missing (environment error)"
  exit 4
fi

# 1. Reject empty diff on authoring branch
TOTAL_ADDS=$(git diff --name-only "$FORK_TAG"..HEAD | wc -l)
if [[ "$TOTAL_ADDS" -eq 0 ]]; then
  echo "FAIL: S1-R16: Branch has zero changes relative to $FORK_TAG"
  exit 1
fi

# 2. Assert zero diff on PB-2 frozen paths without error suppression
FROZEN_DIFF=$(git diff --name-only "$FORK_TAG"..HEAD -- proof/stage0 fixtures/golden/expected.d/base.json tools src/actl/INTERFACES.md)
if [[ -n "$FROZEN_DIFF" ]]; then
  echo "FAIL: S1-R16: PB-2 frozen files modified: $FROZEN_DIFF"
  exit 1
fi

# 3. Check modification allowlist
MOD_FILES=$(git diff --name-only --diff-filter=M "$FORK_TAG"..HEAD)
ALLOWED_MODS="src/core/config.py src/sessions/storage.py install.sh README.md"
for mf in $MOD_FILES; do
  if [[ ! " $ALLOWED_MODS " =~ " $mf " ]]; then
    echo "FAIL: S1-R16: Disallowed file modified: $mf"
    exit 1
  fi
done
