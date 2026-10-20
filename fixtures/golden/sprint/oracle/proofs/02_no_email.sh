#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# R2: never expose email - sentinel scan of the RAW payload, any key name (catches 'contact' renames).
set -uo pipefail
CMD="${ACTL_TARGET_CMD:-python3 -m api.cli}"
for id in 1 2 3; do
  out="$($CMD profile "$id" 2>/dev/null)" || { echo "FAIL: profile $id did not exit 0"; exit 1; }
  for needle in "ada@example.test" "grace@example.test" "linus@example.test" "@example.test" "@"; do
    if printf '%s' "$out" | grep -qF -- "$needle"; then echo "FAIL: body contains seeded email material ($needle) for id $id"; exit 1; fi
  done
done
echo "OK: 02_no_email"
