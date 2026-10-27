#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-06: Patch synthesis 0/1/2 matches, difflib nearest candidate, multi-hunk and new="true" (Addendum P-S2-06).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_patchsynth.py" "$REPO_DIR/test/actl/test_s2_multihunk.py" -q -rf; then
echo "FAIL: S2-R5: P-S2-06 hermetic patch synthesis or multi-hunk verification failed"
exit 1
fi
