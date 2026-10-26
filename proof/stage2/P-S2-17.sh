#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
# proof/stage2/P-S2-17.sh - Stage 2 per-stage additions gate (D-41).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR"

for mod in src/actl/turns.py src/actl/cmd_bundle.py src/actl/cmd_unpack.py src/actl/cmd_replay.py src/actl/cmd_promote.py src/actl/next_rules/phase12.py prompts/architect.md; do
    if [[ ! -e "$mod" ]]; then
        echo "FAIL: S2-R13: Stage 2 implementation module missing on base: $mod"
        exit 1
    fi
done

echo "OK: P-S2-17"
