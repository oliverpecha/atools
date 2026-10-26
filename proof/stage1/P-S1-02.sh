#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-02: Additive-change rule and PB-2 immutability from baseline 4e16cc3.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR"

BASE_SHA="4e16cc3"
if ! git rev-parse -q --verify "$BASE_SHA" >/dev/null; then
  echo "FAIL: S1-R16: Base commit $BASE_SHA missing (environment error)"
  exit 4
fi

# 1. Reject empty diff on authoring branch
TOTAL_CHANGES=$(git diff --name-only "$BASE_SHA"..HEAD | wc -l)
if [[ "$TOTAL_CHANGES" -eq 0 ]]; then
  echo "FAIL: S1-R16: Branch has zero changes relative to $BASE_SHA"
  exit 1
fi

# 2. Assert zero diff on PB-2 frozen paths relative to baseline 4e16cc3
FROZEN_DIFF=$(git diff --name-only "$BASE_SHA"..HEAD -- proof/stage0 fixtures/golden/expected.d/base.json tools src/actl/INTERFACES.md)
if [[ -n "$FROZEN_DIFF" ]]; then
  echo "FAIL: S1-R16: PB-2 frozen files modified relative to $BASE_SHA: $FROZEN_DIFF"
  exit 1
fi

# 3. Check modification allowlist for implementer files
MOD_FILES=$(git diff --name-only --diff-filter=M "$BASE_SHA"..HEAD)
ALLOWED_MODS="src/core/config.py src/sessions/storage.py install.sh README.md docs/plan/spec-S1.md proof/run_suite_actl_s1.sh test/actl/test_guards_s1.py test/actl/test_session_s1.py test/actl/test_next_phase3.py"
for mf in $MOD_FILES; do
  if [[ ! " $ALLOWED_MODS " =~ " $mf " ]]; then
    echo "FAIL: S1-R16: Disallowed file modified: $mf"
    exit 1
  fi
done
