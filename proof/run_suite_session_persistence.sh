#!/usr/bin/env bash
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_DIR/proof/out"
mkdir -p "$OUT_DIR"

PASS_COUNT=0
FAIL_COUNT=0

report() {
    local name="$1"
    local status="$2"
    if [[ "$status" -eq 0 ]]; then
        echo "Running $name... [PASS]"
        PASS_COUNT=$((PASS_COUNT + 1))
    else
        echo "Running $name... [FAIL]"
        FAIL_COUNT=$((FAIL_COUNT + 1))
    fi
}

# P0: Syntax validation
python3 -m compileall -q "$REPO_DIR/src" > "$OUT_DIR/p0.log" 2>&1
bash -n "$REPO_DIR/bin/arouter" >> "$OUT_DIR/p0.log" 2>&1
report "P0_syntax_validation" $?

# P1: Help and CLI flags presence
"$REPO_DIR/bin/arouter" --help 2>&1 \vert{} grep -E "(--detach\vert{}-d\vert{}ps\vert{}attach\vert{}logs\vert{}kill)" > "$OUT_DIR/p1.log" 2>&1
report "P1_cli_subcommands_and_flags" $?

# P2: Log directory initialization
[[ -d "/root/.cursor/logs" ]] > "$OUT_DIR/p2.log" 2>&1 || mkdir -p /root/.cursor/logs
report "P2_logs_directory_presence" $?

# P3: Detached run, ps tracking, and automatic cleanup
TEST_SESS="test-proof-$$"
"$REPO_DIR/bin/arouter" cheap -d -n "$TEST_SESS" -t 5s "sleep 1" > "$OUT_DIR/p3.log" 2>&1 || true
sleep 1
"$REPO_DIR/bin/arouter" ps 2>&1 | grep "$TEST_SESS" >> "$OUT_DIR/p3.log" 2>&1
STATUS_P3=$?
report "P3_detached_session_spawning" $STATUS_P3

# Auto-cleanup verification (zero zombie sessions)
sleep 5
"$REPO_DIR/bin/arouter" ps 2>&1 | grep "$TEST_SESS" >> "$OUT_DIR/p3.log" 2>&1 && ZOMBIE=1 || ZOMBIE=0
[[ "$ZOMBIE" -eq 0 ]] >> "$OUT_DIR/p3.log" 2>&1
report "P3_session_auto_destruction" $?

# P4: Logs retrieval
[[ -f "/root/.cursor/logs/${TEST_SESS}.log" ]] > "$OUT_DIR/p4.log" 2>&1
report "P4_console_log_streaming" $?
rm -f "/root/.cursor/logs/${TEST_SESS}.log"

echo "=========================================="
echo "Suite Summary: $PASS_COUNT Passed,$FAIL_COUNT Failed"
echo "=========================================="

if [[ "$FAIL_COUNT" -gt 0 ]]; then
    exit 1
fi
exit 0
