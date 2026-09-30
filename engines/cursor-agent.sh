#!/usr/bin/env bash
set -euo pipefail

if ! command -v agent >/dev/null 2>&1; then
    echo "🚨 [ERROR] Cursor Agent CLI ('agent') not found in PATH." >&2
    echo "   Install via: curl https://cursor.com/install.sh | bash" >&2
    exit 127
fi

MODEL="${1:-auto}"
shift || true

PIPED_INPUT=""
if [[ ! -t 0 ]]; then
    PIPED_INPUT=$(cat)
fi

PROMPT="$*"
if [[ -n "$PIPED_INPUT" ]]; then
    if [[ -n "$PROMPT" ]]; then
        PROMPT="${PROMPT}

Context / Piped Input:
${PIPED_INPUT}"
    else
        PROMPT="$PIPED_INPUT"
    fi
fi

if [[ -n "$PROMPT" ]]; then
    exec agent --auto-review --trust --model "$MODEL" "$PROMPT"
else
    exec agent --auto-review --trust --model "$MODEL"
fi
