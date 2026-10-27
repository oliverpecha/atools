#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-14: decide_next Phase 1-2 table (>= 10 states) (Addendum P-S2-14, S2-R10).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_next_rules.py" -q -rf; then
echo "FAIL: S2-R10: P-S2-14 phase 1-2 decide_next rules table failed"
exit 1
fi
