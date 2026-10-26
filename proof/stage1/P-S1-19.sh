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
