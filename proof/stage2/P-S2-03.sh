#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-03: Each responses/bad_* gives expected single error code, exit 2, untouched outbox; 12 worked examples (Addendum P-S2-03).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

BAD_SIZE="$REPO_DIR/fixtures/golden/responses/bad_size.txt"
if [[ ! -f "$BAD_SIZE" ]] || (( $(wc -c < "$BAD_SIZE") < 1048576 )); then
if [[ -f "$REPO_DIR/fixtures/golden/make_responses.sh" ]]; then
bash "$REPO_DIR/fixtures/golden/make_responses.sh" >/dev/null
fi
fi

rc=0
python3 -m pytest "$REPO_DIR/test/actl/test_s2_envelope.py" -k "test_p03" -q -rf || rc=$?
if (( rc == 4 )); then echo "FAIL: pytest reported environment error (exit 4)"; exit 4;
elif (( rc != 0 )); then
echo "FAIL: S2-R3/S2-R4: P-S2-03 bad_* response matrix or worked examples failed"
exit 1
fi
