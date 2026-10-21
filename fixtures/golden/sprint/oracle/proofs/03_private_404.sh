#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# R3: private profiles return 404 and leak nothing about the owner.
set -uo pipefail
CMD="${ACTL_TARGET_CMD:-python3 -m api.cli}"
out="$($CMD profile 3 2>/dev/null)" || { echo "FAIL: profile 3 did not exit 0"; exit 1; }
printf '%s' "$out" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
except Exception as e:
    print("FAIL: output is not JSON: %s" % e); sys.exit(1)
if d.get("status") != 404: print("FAIL: private profile status %r != 404" % d.get("status")); sys.exit(1)
raw = json.dumps(d)
for leak in ("Linus", "Keeps to himself", "linus"):
    if leak in raw: print("FAIL: private profile leaks %r" % leak); sys.exit(1)
' || exit 1
echo "OK: 03_private_404"
