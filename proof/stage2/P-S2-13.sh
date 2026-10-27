#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-13: unpack never executes response content ($(touch ...) canary); repair prompt confidentiality (Addendum P-S2-13, S2-R7).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_repair.py" -q -rf; then
echo "FAIL: S2-R7/S2-R12: P-S2-13 repair prompt synthesis or non-execution canary failed"
exit 1
fi
