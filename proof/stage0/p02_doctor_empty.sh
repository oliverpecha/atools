#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# P-S0-28 (extra, S0-R1.5/R1.6): `actl doctor` against an UNINITIALISED root (no init, no sprint, root dir absent).
# Must exit 0, print one JSON object, write only $ACTL_ROOT/baseline.json, create no sprint/handoff tree, and not touch the repo.
set -uo pipefail
REPO="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
for t in git python3 tmux; do command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed (environment error)"; exit 4; }; done
[[ -f "$REPO/audit/atools-compliance_audit.sh" ]] || { echo "FAIL: audit script not found (environment error, D-9)"; exit 4; }
[[ -x "$REPO/bin/actl" ]] || { echo "FAIL: bin/actl is missing or not executable (S0-R1 / D-2)"; exit 1; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
ROOT="$T/never-initialised"
before="$(git -C "$REPO" status --porcelain 2>/dev/null)"
out="$(ACTL_ROOT="$ROOT" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess" "$REPO/bin/actl" doctor --json 2>"$T/err")"; rc=$?
[[ $rc -eq 0 ]] || { echo "FAIL: doctor on an uninitialised root exited $rc, expected 0: $(tail -c 300 "$T/err")"; exit 1; }
printf '%s' "$out" | python3 -c 'import json,sys; d=json.load(sys.stdin); assert isinstance(d,dict) and d.get("head_sha") and "audit" in d' 2>/dev/null || { echo "FAIL: stdout is not the baseline JSON object"; exit 1; }
[[ -f "$ROOT/baseline.json" ]] || { echo "FAIL: baseline.json was not written to the new root"; exit 1; }
extra="$(find "$ROOT" -mindepth 1 ! -name baseline.json | head -3)"
[[ -z "$extra" ]] || { echo "FAIL: doctor created more than baseline.json: $extra"; exit 1; }
[[ "$(git -C "$REPO" status --porcelain 2>/dev/null)" == "$before" ]] || { echo "FAIL: doctor modified the repository"; exit 1; }
echo "OK: doctor on an uninitialised root"
