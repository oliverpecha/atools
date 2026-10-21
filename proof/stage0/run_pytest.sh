#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# run_pytest.sh <test-file>...  - run pytest proofs and map the outcome to the proof convention:
#   0 pass | 1 red (a FAIL: line is printed) | 4 environment/harness problem (ENVFAIL, collection error, no tests, pytest missing)
set -uo pipefail
REPO="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
command -v python3 >/dev/null 2>&1 || { echo "FAIL: python3 not installed (environment error)"; exit 4; }
python3 -c 'import pytest' 2>/dev/null || { echo "FAIL: pytest not installed (environment error)"; exit 4; }
out="$(cd "$REPO" && ACTL_REPO="$REPO" PYTHONDONTWRITEBYTECODE=1 python3 -m pytest "$@" -q --color=no -p no:cacheprovider 2>&1)"; rc=$?
printf '%s\n' "$out" | tail -n 60
case $rc in
  0) exit 0 ;;
  1) if printf '%s\n' "$out" | grep -q 'ENVFAIL:'; then echo "FAIL: environment problem reported by a test (ENVFAIL)"; exit 4; fi
     printf '%s\n' "$out" | grep -q 'FAIL:' || echo "FAIL: pytest reported failures without a FAIL: line"
     exit 1 ;;
  *) echo "FAIL: harness error (pytest exit $rc: collection error, usage error, or no tests collected)"; exit 4 ;;
esac
