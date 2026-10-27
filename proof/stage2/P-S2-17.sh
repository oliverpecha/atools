#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-17: Role prompts/*.md content checklist and single-source _output_contract.md verification (S2-R11).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_prompts.py" -q -rf; then
echo "FAIL: S2-R11: P-S2-17 role prompts content checklist failed"
exit 1
fi
