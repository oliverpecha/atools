#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-04: Truncation at 20 seeded random offsets (Seed 79) never succeeds (Addendum P-S2-04).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_truncation.py" -q -rf; then
echo "FAIL: S2-R3: P-S2-04 truncation property test (seed 79) failed"
exit 1
fi
