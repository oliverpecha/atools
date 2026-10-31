#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# P-S2-10: bundle static before dynamic, header hashes, max-chars abort table, refuses records/outside-repo (Addendum P-S2-10).

set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="$REPO_DIR/src:${PYTHONPATH:-}"

rc=0
python3 -m pytest "$REPO_DIR/test/actl/test_s2_bundle.py" -k "test_p10" -q -rf || rc=$?
if (( rc == 4 )); then echo "FAIL: pytest reported environment error (exit 4)"; exit 4;
elif (( rc != 0 )); then
echo "FAIL: S2-R2/S2-R12: P-S2-10 bundle assembly, limits, or path refusal failed"
exit 1
fi
