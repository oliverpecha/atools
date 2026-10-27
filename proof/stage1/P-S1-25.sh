#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-25: Live tmux session collision refuses with UsageError exit 2 only
# (not 3); live session is independently asserted; --no-run succeeds after (S1-R9.2).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p25" "")"
rm -rf "$WT"

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

LIVE_SESS="impl-public-profiles-005"
"$REPO_DIR/bin/arouter" cheap -d -n "$LIVE_SESS" -t 60s SLEEP < /dev/null

python3 - "$SDIR" "$LIVE_SESS" <<'PY'
import os
import subprocess
import sys
from pathlib import Path

sdir = Path(sys.argv[1])
live_sess = sys.argv[2]

try:
    from actl.cli import main as cli_main
    from actl.layout import Layout
    from actl.seq import read_state, update_state
except ImportError as exc:
    print(f"FAIL: S1-R9.2: cannot import actl modules: {exc}")
    sys.exit(1)

os.environ["ACTL_ROOT"] = str(sdir)
layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

listed = subprocess.run(
    ["tmux", "list-sessions", "-F", "#{session_name}"],
    capture_output=True, text=True,
)
if listed.returncode != 0 or live_sess not in listed.stdout.splitlines():
    print(f"FAIL: S1-R9.2: live tmux session {live_sess} was not independently observed: {listed.stdout!r}")
    sys.exit(1)

update_state(layout, tag, {"tmux_sessions": [live_sess]})
seq_before = read_state(layout, tag)["seq"]

rc_collision = cli_main(["dispatch-impl", "--sprint", tag, "--no-run"])
if rc_collision != 2:
    print(f"FAIL: S1-R9.2: Expected exit code 2 on active tmux session collision, got {rc_collision}")
    sys.exit(1)

seq_after = read_state(layout, tag)["seq"]
if seq_after != seq_before:
    print(f"FAIL: S1-R9.2: Active session collision must not advance seq ({seq_before} -> {seq_after})")
    sys.exit(1)

subprocess.run(["tmux", "kill-session", "-t", live_sess], check=False)
update_state(layout, tag, {"tmux_sessions": []})

rc_ok = cli_main(["dispatch-impl", "--sprint", tag, "--no-run"])
if rc_ok != 0:
    print(f"FAIL: S1-R9.2: Expected dispatch-impl --no-run to succeed (exit 0) once no live session exists, got {rc_ok}")
    sys.exit(1)
PY
