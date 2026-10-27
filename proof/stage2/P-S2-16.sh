#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-16: Stage 2 reuses scope.py, seq.state_lock, schemas.validate, layout and registers only via registries (Addendum P-S2-16).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_postparse.py" -k "test_p16_stage0_module_reuse" -q -rf; then
echo "FAIL: S2-R12: P-S2-16 Stage 0 shared module and registry reuse check failed"
exit 1
fi
