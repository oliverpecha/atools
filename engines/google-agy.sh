#!/usr/bin/env bash
set -euo pipefail
if ! command -v agy >/dev/null 2>&1; then
    echo "🚨 [ERROR] 'agy' CLI not found in PATH." >&2; exit 127
fi
MODEL="${1:-gemini-2.5-flash}"; shift || true
exec agy --model "$MODEL" --headless --non-interactive "$@"
