#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-26: start_session instruction validation:
# - Positive control: valid session name and <100,000-byte ASCII instruction succeeds (returns 0)
# - Negative controls: >=100,000 JSON-escaped bytes, non-ASCII, 'help', and invalid
#   session name each raise ValueError BEFORE invoking arouter (GD-01 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

T="$(mktemp -d)"
export TMUX_TMPDIR="$T/tmux" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess"
mkdir -p "$TMUX_TMPDIR" "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR" "$T/bin" "$T/wt"
trap 'tmux kill-server >/dev/null 2>&1 || true; rm -rf "$T"' EXIT

printf '#!/usr/bin/env bash\nexit 0\n' > "$T/bin/loginctl"
cat > "$T/bin/agent" <<'EOF'
#!/usr/bin/env bash
echo "agent_ran" >> "$ATOOLS_LOG_DIR/agent_invocations.txt"
exit 0
EOF
chmod +x "$T/bin/loginctl" "$T/bin/agent"
export PATH="$T/bin:$PATH"

python3 - "$T/wt" "$ATOOLS_LOG_DIR/agent_invocations.txt" <<'PY'
import json
import sys
import time
from pathlib import Path

wt = Path(sys.argv[1])
inv_file = Path(sys.argv[2])

try:
    from actl.session import start_session
except ImportError as exc:
    print(f"FAIL: S1-R9.4: cannot import actl.session.start_session: {exc}")
    sys.exit(1)

# 1. Negative controls MUST raise ValueError and NEVER invoke agent/arouter
bad_cases = [
    ("overflow_100k", "impl-valid-001", "A" * 99999),  # json.dumps adds 2 quote bytes -> 100001 >= 100000
    ("non_ascii", "impl-valid-001", "Implement caf? feature"),
    ("exact_help", "impl-valid-001", "help"),
    ("bad_sess_name", "Invalid_Session_Name!", "Valid ASCII prompt"),
]

for label, sname, instr in bad_cases:
    try:
        start_session(sname, wt, instr, mode="foreground", tier="cheap")
        print(f"FAIL: S1-R9.4: start_session failed to reject {label}")
        sys.exit(1)
    except ValueError:
        pass
    except Exception as exc:
        print(f"FAIL: S1-R9.4: Expected ValueError on {label}, got {type(exc).__name__}: {exc}")
        sys.exit(1)

if inv_file.exists():
    print("FAIL: S1-R9.4: arouter/agent was invoked despite invalid start_session arguments!")
    sys.exit(1)

# 2. Positive control: valid below-limit instruction (99,990 JSON-escaped bytes) returns 0 and runs agent
valid_instr = "B" * 99988
assert len(json.dumps(valid_instr)) < 100000
rc = start_session("impl-valid-001", wt, valid_instr, mode="foreground", tier="cheap")
if rc != 0:
    print(f"FAIL: S1-R9.4: Positive control start_session returned {rc}, expected 0")
    sys.exit(1)
if not inv_file.is_file():
    print("FAIL: S1-R9.4: Positive control start_session returned 0 without invoking arouter/agent")
    sys.exit(1)
PY
