#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-22: Real private tmux session killed via tmux kill-server (no .exit written)
# waits disappearance grace window and records lost=True, exit_code=None,
# forcing G2 red in verify_impl (GD-03 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p22" "good.patch")"

T="$(mktemp -d)"
export TMUX_TMPDIR="$T/tmux" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess"
mkdir -p "$TMUX_TMPDIR" "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR" "$T/bin"
trap 'tmux kill-server >/dev/null 2>&1 || true; rm -rf "$T"' EXIT

printf '#!/usr/bin/env bash\nexit 0\n' > "$T/bin/loginctl"
cat > "$T/bin/agent" <<'EOF'
#!/usr/bin/env bash
exec sleep 60
EOF
chmod +x "$T/bin/loginctl" "$T/bin/agent"
export PATH="$T/bin:$PATH"

"$REPO_DIR/bin/arouter" cheap -d -n impl-p22-lost-006 -t 60s SLEEP < /dev/null
sleep 0.4
# Abruptly kill the private tmux server and remove any .exit so the session vanishes without .exit
tmux kill-server >/dev/null 2>&1 || true
rm -f "$ATOOLS_SESSION_DIR/impl-p22-lost-006.exit" "$ATOOLS_SESSION_DIR/impl-p22-lost-006.exit.tmp"

python3 - "$SDIR" "$WT" <<'PY'
import json
import sys
import time
from pathlib import Path

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.session import wait_session
    from actl.verify import verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R14.4: cannot import actl modules: {exc}")
    sys.exit(1)

t0 = time.monotonic()
res = wait_session("impl-p22-lost-006", timeout_s=2, poll_interval_s=0.2)
elapsed = time.monotonic() - t0

if res.get("lost") is not True or res.get("exit_code") is not None or res.get("hard_cap") is not False:
    print(f"FAIL: S1-R14.4: Expected lost=True, exit_code=None, hard_cap=False, got {res}")
    sys.exit(1)
if elapsed < 1.0:
    print(f"FAIL: S1-R14.4: wait_session did not poll disappearance grace window (elapsed={elapsed:.3f}s, expected >= 1.0s for timeout_s=2)")
    sys.exit(1)

# Delayed .exit recovery: session already gone; .exit appears during the grace window
import os
import threading
recover_name = "impl-p22-recover-006"
exit_path = Path(os.environ["ATOOLS_SESSION_DIR"]) / f"{recover_name}.exit"

def _write_exit_later():
    time.sleep(0.4)
    exit_path.write_text("0\n", encoding="utf-8")

threading.Thread(target=_write_exit_later, daemon=True).start()
t1 = time.monotonic()
res_rec = wait_session(recover_name, timeout_s=3, poll_interval_s=0.1)
elapsed_rec = time.monotonic() - t1
if res_rec.get("lost") is not False or res_rec.get("exit_code") != 0:
    print(f"FAIL: S1-R14.4: delayed .exit must recover lost=False exit_code=0, got {res_rec}")
    sys.exit(1)
if elapsed_rec < 0.4:
    print(f"FAIL: S1-R14.4: delayed .exit recovery returned too fast ({elapsed_rec:.3f}s)")
    sys.exit(1)

# Even if a valid closure exists on disk, session.lost=True MUST force G2 red (S1-R2.4)
layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
closure_path = sdir / "valid_closure.json"
closure_path.write_text(json.dumps({
    "reason": "done",
    "blocking_step": None,
    "notes": ["valid closure"],
    "backlog": [],
    "solution_key_divergence": None,
}), encoding="utf-8")

ver = verify_impl(layout, tag, closure_path=closure_path, worktree=wt, session_info=res)
if ver.get("exit_code") != 1 or ver.get("failing_step") != "G2":
    print(f"FAIL: S1-R2.4: session_lost must force G2 red even with valid closure, got {ver}")
    sys.exit(1)
PY
