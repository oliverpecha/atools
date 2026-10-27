#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-15: Produced proofs/*.sh executable, pass bash -n, bad shell -> E_SHELL_SYNTAX, scope & coverage (Addendum P-S2-15, S2-R6).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_postparse.py" -k "not test_p16_stage0_module_reuse" -q -rf; then
echo "FAIL: S2-R6: P-S2-15 post-parse shell syntax, scope, or coverage validation failed"
exit 1
fi
