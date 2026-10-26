#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-19: Baseline suites clean; implementer skill satisfies governance checklist.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

SKILL="${REPO_DIR}/skills/actl-implementer/SKILL.md"
if [[ ! -f "$SKILL" ]]; then
  echo "FAIL: S1-R8: skills/actl-implementer/SKILL.md missing"
  exit 1
fi

# Required instruction checklist
for req in "mailboxes/implementer/inbox" "attempt.json" "mailboxes/implementer/outbox/closure.json" "wip/" "git status"; do
  if ! grep -q "$req" "$SKILL"; then
    echo "FAIL: S1-R8.2: Required instruction missing in SKILL.md: $req"
    exit 1
  fi
done

# Forbidden instruction checklist
for forb in "proof/" "records/" "oracle" "solution_key.patch"; do
  if grep -q "$forb" "$SKILL"; then
    echo "FAIL: S1-R8.3: Forbidden instruction present in SKILL.md: $forb"
    exit 1
  fi
done
