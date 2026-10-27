#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-02: Good challenger response unpacks with exec bits and mutants apply on base+key (Addendum P-S2-02).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_unpack.py" -k "test_p02" -q -rf; then
echo "FAIL: S2-R4/S2-R6: P-S2-02 good challenger unpack or mutant apply verification failed"
exit 1
fi
