#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# End-to-end recomputation: photo_count must equal len(photos) recomputed from RAW data (api.users.USERS).
set -uo pipefail
CMD="${ACTL_TARGET_CMD:-python3 -m api.cli}"
for id in 1 2; do
  raw="$(python3 -c "from api.users import USERS; print(len(USERS[$id]['photos']))" 2>/dev/null)" || { echo "FAIL: cannot read raw data"; exit 1; }
  out="$($CMD profile "$id" 2>/dev/null)" || { echo "FAIL: profile $id did not exit 0"; exit 1; }
  got="$(printf '%s' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin)["body"]["photo_count"])' 2>/dev/null)" || { echo "FAIL: no body.photo_count for $id"; exit 1; }
  if [[ "$got" != "$raw" ]]; then echo "FAIL: photo_count $got != recomputed $raw for id $id"; exit 1; fi
done
echo "OK: probe"
