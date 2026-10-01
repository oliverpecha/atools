#!/usr/bin/env bash
set -euo pipefail

if ! command -v claude >/dev/null 2>&1; then
    echo "🚨 [ERROR] 'claude' CLI not found in PATH." >&2
    exit 127
fi

MODEL="${1:-claude-3-7-sonnet}"
shift || true

PIPED_INPUT=""
if [[ ! -t 0 ]]; then
    PIPED_INPUT=$(cat)
fi

PROMPT="$*"
if [[ -n "$PIPED_INPUT" ]]; then
    PROMPT="${PROMPT}

Context / Piped Input:
${PIPED_INPUT}"
fi

exec claude -p "$PROMPT" --model "$MODEL" --dangerously-skip-permissions
