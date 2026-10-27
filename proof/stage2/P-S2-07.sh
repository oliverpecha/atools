#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-07: Fence-wrapped, CRLF, BOM and trailing-space variants unpack to identical output hashes (Addendum P-S2-07).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_unpack.py" -k "test_p07" -q -rf; then
echo "FAIL: S2-R4: P-S2-07 normalization variants failed"
exit 1
fi
