#!/usr/bin/env bash
set -euo pipefail
if ! command -v aider >/dev/null 2>&1; then
    echo "🚨 [ERROR] 'aider' CLI not found in PATH." >&2; exit 127
fi
MODEL="${1:-gemini/gemini-2.5-flash}"; shift || true
exec aider --model "$MODEL" --yes-always --no-auto-commits --message "$*"
