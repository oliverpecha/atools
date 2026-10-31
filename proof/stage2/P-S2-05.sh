#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-05: Path attacks (../x, /etc/x, backslash, NUL, .git, symlink, case collision, over-long) rejected (Addendum P-S2-05).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

rc=0
python3 -m pytest "$REPO_DIR/test/actl/test_s2_envelope.py" -k "test_p05" -q -rf || rc=$?
if (( rc == 4 )); then echo "FAIL: pytest reported environment error (exit 4)"; exit 4;
elif (( rc != 0 )); then
echo "FAIL: S2-R3/S2-R12: P-S2-05 path attack and containment rejection failed"
exit 1
fi
