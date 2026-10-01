#!/usr/bin/env bash
set -euo pipefail
if ! command -v vibe >/dev/null 2>&1; then
    echo "🚨 [ERROR] 'vibe' CLI not found in PATH." >&2; exit 127
fi
MODEL="${1:-codestral-latest}"; shift || true
exec vibe --model "$MODEL" --yes --non-interactive "$*"
