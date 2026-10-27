#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-01: Turn ledger allocation/resolution (S2-R1) & good architect-intake unpack + key apply (Addendum P-S2-01).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_turns.py" "$REPO_DIR/test/actl/test_s2_unpack.py" -k "test_turns or test_courier or test_p01" -q -rf; then
echo "FAIL: S2-R1/S2-R4: P-S2-01 turn ledger or good architect-intake unpack failed"
exit 1
fi
