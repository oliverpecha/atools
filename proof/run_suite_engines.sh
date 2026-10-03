#!/usr/bin/env bash
set -uo pipefail

mkdir -p proof/out
PASS=0; FAIL=0

run_check() {
    local name="$1"; shift
    local log="proof/out/${name}.log"
    echo -n "Running ${name}... "
    if "$@" > "$log" 2>&1; then
        echo "[PASS]"
        ((PASS++))
    else
        echo "[FAIL] (see $log)"
        ((FAIL++))
    fi
}

run_check "P0_syntax_validation" bash -c '
    bash -n bin/arouter
    for f in engines/*.sh; do
        bash -n "$f"
    done
'

run_check "P1_permissions_and_layout" bash -c '
    set -e
    test -x bin/arouter
    test -x engines/cursor-agent.sh
    test -x engines/openai-codex.sh
    test -x engines/claude-code.sh
    test -x engines/google-agy.sh
    test -x engines/aider.sh
    test -x engines/mistral-vibe.sh
'

run_check "P2_exit_127_on_missing_bins" bash -c '
    PATH="/usr/bin:/bin" engines/cursor-agent.sh auto "ping" >/dev/null 2>&1
    [ $? -eq 127 ] || exit 1
    PATH="/usr/bin:/bin" engines/openai-codex.sh auto "ping" >/dev/null 2>&1
    [ $? -eq 127 ] || exit 1
    PATH="/usr/bin:/bin" engines/claude-code.sh auto "ping" >/dev/null 2>&1
    [ $? -eq 127 ] || exit 1
'

run_check "P3_cursor_adapter_flags" bash -c '
    TMP_DIR=$(mktemp -d)
    cat <<EOF > "$TMP_DIR/agent"
#!/usr/bin/env bash
echo "AGENT_INVOKED:\$*"
EOF
    chmod +x "$TMP_DIR/agent"
    OUT=$(PATH="$TMP_DIR:$PATH" engines/cursor-agent.sh test-model "do refactor")
    rm -rf "$TMP_DIR"
    [[ "$OUT" =~ --auto-review ]] && [[ "$OUT" =~ --trust ]] && [[ "$OUT" =~ test-model ]]
'

test_p4_dispatch() {
    local tmp_dir; tmp_dir=$(mktemp -d)
    cat <<'EOF_CODEX' > "$tmp_dir/codex"
#!/usr/bin/env bash
echo "CODEX_CALLED:$*"
EOF_CODEX
    cat <<'EOF_CLAUDE' > "$tmp_dir/claude"
#!/usr/bin/env bash
echo "CLAUDE_CALLED:$*"
EOF_CLAUDE
    chmod +x "$tmp_dir/codex" "$tmp_dir/claude"

    local out_codex; out_codex=$(PATH="$tmp_dir:$PATH" bin/arouter --engine openai-codex cheap "task" 2>&1)
    local out_claude; out_claude=$(PATH="$tmp_dir:$PATH" bin/arouter --engine claude-code smart "task" 2>&1)
    rm -rf "$tmp_dir"

    echo "$out_codex" | grep -q "CODEX_CALLED" || { echo "CODEX failed: $out_codex"; return 1; }
    echo "$out_claude" | grep -q "CLAUDE_CALLED" || { echo "CLAUDE failed: $out_claude"; return 1; }
}
run_check "P4_router_engine_routing" test_p4_dispatch

echo "=========================================="
echo "Suite Summary: $PASS Passed, $FAIL Failed"
echo "=========================================="
[[ $FAIL -eq 0 ]] || exit 1
