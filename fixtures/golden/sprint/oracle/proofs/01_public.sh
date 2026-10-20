#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# R1: guests see name, bio and a photo_count for public profiles (avatar value deliberately NOT asserted - see oracle-critique.md).
set -uo pipefail
CMD="${ACTL_TARGET_CMD:-python3 -m api.cli}"
for id in 1 2; do
  if ! out="$($CMD profile "$id" 2>/dev/null)"; then echo "FAIL: profile $id did not exit 0"; exit 1; fi
  printf '%s' "$out" | python3 -c '
import json, sys
exp = {"1": ("Ada Lovelace", "Mathematician"), "2": ("Grace Hopper", "Compiler pioneer")}[sys.argv[1]]
try:
    d = json.load(sys.stdin)
except Exception as e:
    print("FAIL: output is not JSON: %s" % e); sys.exit(1)
b = d.get("body") or {}
if d.get("status") != 200: print("FAIL: public profile %s status %r != 200" % (sys.argv[1], d.get("status"))); sys.exit(1)
if b.get("name") != exp[0]: print("FAIL: name mismatch for %s" % sys.argv[1]); sys.exit(1)
if b.get("bio") != exp[1]: print("FAIL: bio mismatch for %s" % sys.argv[1]); sys.exit(1)
pc = b.get("photo_count")
if not isinstance(pc, int) or isinstance(pc, bool) or pc < 0: print("FAIL: photo_count missing or not a non-negative int"); sys.exit(1)
' "$id" || exit 1
done
echo "OK: 01_public"
