#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-12: promote naming, .meta.json, state.json pointers, 7 keys, idempotence, read-only staging (Addendum P-S2-12, D-43).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

rc=0
python3 -m pytest "$REPO_DIR/test/actl/test_s2_promote.py" -q -rf || rc=$?
if (( rc == 4 )); then echo "FAIL: pytest reported environment error (exit 4)"; exit 4;
elif (( rc != 0 )); then
echo "FAIL: S2-R9: P-S2-12 role promotion verification failed"
exit 1
fi
