#!/usr/bin/env bash
set -euo pipefail

if ! command -v codex >/dev/null 2>&1; then
    echo "🚨 [ERROR] 'codex' CLI not found in PATH." >&2
    exit 127
fi

MODEL="${1:-gpt-5-codex}"
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

exec codex run --model "$MODEL" --approval-mode full-auto --prompt "$PROMPT"
