#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-11: Sentinel equals bundle_sha256[:8]; another bundle's sentinel is rejected (Addendum P-S2-11, D-44).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

if ! python3 -m pytest "$REPO_DIR/test/actl/test_s2_bundle.py" -k "test_p11" -q -rf; then
echo "FAIL: S2-R2/S2-R3: P-S2-11 bundle sentinel digest verification failed"
exit 1
fi
