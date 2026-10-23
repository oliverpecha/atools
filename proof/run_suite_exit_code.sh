#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# proof/run_suite_exit_code.sh - Workstream 0B gating suite, S0-R16, P-S0-16..25 = E1..E10.
# Isolated: private tmux server (TMUX_TMPDIR), private ATOOLS_LOG_DIR / ATOOLS_SESSION_DIR, stub agent + loginctl first in PATH.
# Exit: 0 all green; 1 any check red (expected on the fork point: no .exit file is ever written);
#       4 environment error (tmux/arouter/stubs unusable) - never reported as a red check.
# Differences from the addendum reference (spec-S0.md SA-9..SA-12): every check owns its session; E7 also requires the
# .exit to appear after the kill; E10 requires a recorded 129/130/143 (a missing file is NOT accepted).
set -uo pipefail
REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="$REPO_DIR/proof/out"; mkdir -p "$OUT_DIR"
STUBS="$REPO_DIR/fixtures/golden/stubs"
PASS=0; FAIL=0

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }
[[ -x "$REPO_DIR/bin/arouter" ]] || { echo "FAIL: $REPO_DIR/bin/arouter missing or not executable (environment error)"; exit 4; }
[[ -x "$STUBS/agent" && -x "$STUBS/loginctl" ]] || { echo "FAIL: stubs missing in $STUBS (environment error)"; exit 4; }

unset TMUX
T="$(mktemp -d /tmp/s0b.XXXXXX)"
export TMUX_TMPDIR="$T/tmux" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess"
mkdir -p "$TMUX_TMPDIR" "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR" "$T/bin"
cp "$STUBS/agent" "$STUBS/loginctl" "$T/bin/"; chmod +x "$T/bin/agent" "$T/bin/loginctl"
export PATH="$T/bin:$PATH"
trap 'tmux kill-server >/dev/null 2>&1; rm -rf "$T"' EXIT

"$T/bin/agent" EXIT7; [[ $? -eq 7 ]] || { echo "FAIL: stub agent misbehaves (environment error)"; exit 4; }
tmux new-session -d -s preflight "sleep 1" 2>/dev/null || { echo "FAIL: cannot start a private tmux server (environment error)"; exit 4; }
tmux kill-server >/dev/null 2>&1

check() { local n="$1"; shift
  if "$@" > "$OUT_DIR/$n.log" 2>&1; then echo "Running $n... [PASS]"; PASS=$((PASS+1))
  else echo "Running $n... [FAIL] (see $OUT_DIR/$n.log)"; sed -n '1,3p' "$OUT_DIR/$n.log" | sed 's/^/    /'; FAIL=$((FAIL+1)); fi; }
wait_gone() { local s="$1" n=$(( ${2:-20} * 10 )); while (( n-- > 0 )); do tmux has-session -t "$s" 2>/dev/null || return 0; sleep 0.1; done; return 1; }
wait_up()   { local s="$1" n=50; while (( n-- > 0 )); do tmux has-session -t "$s" 2>/dev/null && return 0; sleep 0.1; done; return 1; }
run_detached() { "$REPO_DIR/bin/arouter" cheap -d -n "$1" -t "$2" "$3" < /dev/null; }
exit_file() { echo "$ATOOLS_SESSION_DIR/$1.exit"; }
exit_of() { cat "$(exit_file "$1")" 2>/dev/null; }
need_exit() { [[ -e "$(exit_file "$1")" ]] || { echo "FAIL: $1.exit was not written (S0-R16.1: cleanup must persist the exit status)"; return 1; }; }
expect_val() { local s="$1" want="$2" got; need_exit "$s" || return 1; got="$(exit_of "$s")"
  [[ "$got" == "$want" ]] || { echo "FAIL: $s.exit holds '$got', expected '$want'"; return 1; }; }

t_zero()    { run_detached e1-ok 20s OK && wait_gone e1-ok && expect_val e1-ok 0; }
t_nonzero() { run_detached e2-7 20s EXIT7 && wait_gone e2-7 && expect_val e2-7 7; }
t_timeout() { run_detached e3-to 2s SLEEP && wait_gone e3-to 25 && expect_val e3-to 124; }
t_format()  { run_detached e4-f 20s EXIT7 && wait_gone e4-f && need_exit e4-f || return 1
  local f; f="$(exit_file e4-f)"
  [[ "$(wc -l < "$f")" -eq 1 ]] || { echo "FAIL: .exit must be exactly one line"; return 1; }
  [[ "$(cat "$f")" =~ ^[0-9]+$ ]] || { echo "FAIL: .exit must be a bare integer"; return 1; }
  ! ls "$ATOOLS_SESSION_DIR"/*.exit.tmp >/dev/null 2>&1 || { echo "FAIL: leftover .exit.tmp"; return 1; }; }
t_cleanup() { run_detached e5-c 20s OK && wait_gone e5-c && need_exit e5-c || return 1
  [[ ! -e "$ATOOLS_SESSION_DIR/e5-c.run.sh" ]] || { echo "FAIL: runner script not removed"; return 1; }
  [[ ! -e "$ATOOLS_SESSION_DIR/e5-c.json" ]] || { echo "FAIL: metadata json not removed"; return 1; }; }
t_stale()   { echo 99 > "$(exit_file e6-s)"; : > "$(exit_file e6-s).tmp"
  run_detached e6-s 20s OK && wait_gone e6-s && expect_val e6-s 0 && [[ ! -e "$(exit_file e6-s).tmp" ]] || { echo "FAIL: stale .exit/.exit.tmp not replaced/removed"; return 1; }; }
t_running() { run_detached e7-r 30s SLEEP && wait_up e7-r && sleep 1 || { echo "FAIL: session did not start"; return 1; }
  [[ ! -e "$(exit_file e7-r)" ]] || { echo "FAIL: .exit exists while the session is still running"; return 1; }
  "$REPO_DIR/bin/arouter" kill e7-r >/dev/null 2>&1; wait_gone e7-r 10; sleep 0.5
  need_exit e7-r; }
t_kill()    { run_detached e8-k 30s SLEEP && wait_up e8-k && sleep 1 || { echo "FAIL: session did not start"; return 1; }
  "$REPO_DIR/bin/arouter" kill e8-k >/dev/null 2>&1; wait_gone e8-k 10 && sleep 0.5 && need_exit e8-k || return 1
  local v; v="$(exit_of e8-k)"; [[ "$v" =~ ^[0-9]+$ ]] && (( v == 143 )) || { echo "FAIL: arouter kill recorded '$v', expected exactly 143 (kill path overwrites; a HUP trap would leave 129)"; return 1; }; }
t_helper()  { run_detached e9-h 20s EXIT7 && wait_gone e9-h && need_exit e9-h || return 1
  PYTHONPATH="$REPO_DIR/src" python3 - <<'PY'
import os, sys
try:
    from router.process import read_exit_code, get_exit_path
except ImportError as e:
    print("FAIL: router.process.read_exit_code/get_exit_path missing: %s" % e); sys.exit(1)
def chk(c, m):
    if not c: print("FAIL: " + m); sys.exit(1)
chk(read_exit_code("e9-h") == 7, "read_exit_code('e9-h') != 7")
chk(read_exit_code("does-not-exist") is None, "missing file must give None")
p = get_exit_path("e9-h")
chk(str(p) == os.path.join(os.environ["ATOOLS_SESSION_DIR"], "e9-h.exit"), "get_exit_path wrong: %s" % p)
open(str(p), "w").write("12abc\n"); chk(read_exit_code("e9-h") is None, "non-integer content must give None")
open(str(p), "w").write("-3\n");    chk(read_exit_code("e9-h") is None, "negative must give None")
open(str(p), "w").write("7\n");     chk(read_exit_code("e9-h") == 7, "clean integer must parse")
PY
}
t_signalled() { run_detached e10-st 30s SLEEP && wait_up e10-st && sleep 1 || { echo "FAIL: session did not start"; return 1; }
  local pid; pid="$(pgrep -f "e10-st.run.sh" | head -1)"; [[ -n "$pid" ]] || { echo "FAIL: runner process not found (harness)"; return 1; }
  kill -TERM "$pid"; pkill -TERM -P "$pid" 2>/dev/null
  wait_gone e10-st 15 || { echo "FAIL: session survived SIGTERM"; return 1; }
  sleep 0.5
  need_exit e10-st || return 1
  local v; v="$(exit_of e10-st)"
  [[ "$v" =~ ^(129|130|143)$ ]] || { echo "FAIL: externally signalled runner recorded '$v', expected 129, 130 or 143 (never 0)"; return 1; }; }

check E1_exit_zero t_zero;            check E2_exit_nonzero t_nonzero
check E3_exit_timeout_124 t_timeout;  check E4_exit_file_format t_format
check E5_runner_removed_exit_kept t_cleanup; check E6_stale_exit_replaced t_stale
check E7_no_exit_while_running t_running;    check E8_kill_records_signal_exit t_kill
check E9_read_exit_code_helper t_helper;     check E10_signalled_runner_never_zero t_signalled
echo "=========================================="; echo "Suite Summary: $PASS Passed, $FAIL Failed"; echo "=========================================="
[[ $FAIL -eq 0 ]] || exit 1
