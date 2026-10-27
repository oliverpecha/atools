#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-08: --amend replaces only named blocks, union validates; atomic outbox swap 0o770 & rollback (Addendum P-S2-08, D-46).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

rc=0
python3 -m pytest "$REPO_DIR/test/actl/test_s2_unpack.py" "$REPO_DIR/test/actl/test_s2_atomic_swap.py" -k "test_p08 or test_outbox" -q -rf || rc=$?
if (( rc == 4 )); then echo "FAIL: pytest reported environment error (exit 4)"; exit 4;
elif (( rc != 0 )); then
echo "FAIL: S2-R4: P-S2-08 --amend union or atomic outbox swap failed"
exit 1
fi
