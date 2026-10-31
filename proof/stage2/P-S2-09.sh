#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-09: replay returns 0 on stored golden turns, 1 after deliberate change (Addendum P-S2-09).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

rc=0
python3 -m pytest "$REPO_DIR/test/actl/test_s2_replay.py" -q -rf || rc=$?
if (( rc == 4 )); then echo "FAIL: pytest reported environment error (exit 4)"; exit 4;
elif (( rc != 0 )); then
echo "FAIL: S2-R8: P-S2-09 turn replay verification failed"
exit 1
fi
