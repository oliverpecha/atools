#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-21: Watchdog overrun on real private tmux session records exit 124,
# hard_cap=True, lost=False, marks G2 red in verify_impl, and increments
# state.hard_caps_tripped; contrasts with normal exit 0 session (GD-03 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p21" "good.patch")"

T="$(mktemp -d)"
export TMUX_TMPDIR="$T/tmux" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess"
mkdir -p "$TMUX_TMPDIR" "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR" "$T/bin"
trap 'tmux kill-server >/dev/null 2>&1 || true; rm -rf "$T"' EXIT

printf '#!/usr/bin/env bash\nexit 0\n' > "$T/bin/loginctl"
cat > "$T/bin/agent" <<'EOF'
#!/usr/bin/env bash
case "$*" in
  *SLEEP*) exec sleep 60 ;;
  *)       exit 0 ;;
esac
EOF
chmod +x "$T/bin/loginctl" "$T/bin/agent"
export PATH="$T/bin:$PATH"

# 1. Spawn a fast-finishing session (positive control) and a sleeping session (watchdog timeout 2s)
"$REPO_DIR/bin/arouter" cheap -d -n impl-p21-ok-006 -t 20s OK < /dev/null
"$REPO_DIR/bin/arouter" cheap -d -n impl-p21-to-006 -t 2s SLEEP < /dev/null
"$REPO_DIR/bin/arouter" cheap -d -n impl-p21-ws-006 -t 60s SLEEP < /dev/null

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.session import wait_session
    from actl.verify import verify_impl
    from actl.layout import Layout
    from actl.seq import read_state
except ImportError as exc:
    print(f"FAIL: S1-R14: cannot import actl modules: {exc}")
    sys.exit(1)

# 1. Positive control: normal session finishes with exit_code=0, hard_cap=False, lost=False
res_ok = wait_session("impl-p21-ok-006", timeout_s=15, poll_interval_s=0.2)
if res_ok.get("exit_code") != 0 or res_ok.get("hard_cap") is not False or res_ok.get("lost") is not False:
    print(f"FAIL: S1-R14: Expected exit_code=0, hard_cap=False, lost=False on normal session, got {res_ok}")
    sys.exit(1)

# 2. Negative control: watchdog timeout session finishes with exit_code in (124, 137), hard_cap=True, lost=False
res_to = wait_session("impl-p21-to-006", timeout_s=15, poll_interval_s=0.2)
if res_to.get("hard_cap") is not True or res_to.get("lost") is not False:
    print(f"FAIL: S1-R14.3: Expected hard_cap=True, lost=False on watchdog timeout, got {res_to}")
    sys.exit(1)
if res_to.get("exit_code") not in (124, 137):
    print(f"FAIL: S1-R14.3: Expected exit_code 124 or 137, got {res_to.get('exit_code')}")
    sys.exit(1)

# 3. Passing session_info with hard_cap=True into verify_impl forces G2 red and increments hard_caps_tripped
layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
ver = verify_impl(layout, tag, worktree=wt, session_info=res_to)
if ver.get("exit_code") != 1 or ver.get("failing_step") != "G2":
    print(f"FAIL: S1-R2.4: Expected G2 red on hard_cap=True session, got {ver}")
    sys.exit(1)

st = read_state(layout, tag)
if st.get("hard_caps_tripped") != 1:
    print(f"FAIL: S1-R2.4: Expected state.hard_caps_tripped == 1, got {st.get('hard_caps_tripped')}")
    sys.exit(1)

# 4. wait_session's own timeout-and-kill path (session still running, timeout_s=2)
res_ws = wait_session("impl-p21-ws-006", timeout_s=2, poll_interval_s=0.2)
if res_ws.get("hard_cap") is not True or res_ws.get("lost") is not False:
    print(f"FAIL: S1-R14.2: wait_session own timeout must set hard_cap=True, got {res_ws}")
    sys.exit(1)
if res_ws.get("exit_code") not in (124, 137):
    print(f"FAIL: S1-R14.2: wait_session own kill expected 124 or 137, got {res_ws.get('exit_code')}")
    sys.exit(1)
PY
