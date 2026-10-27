#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-26: start_session instruction validation. Non-ASCII uses U+00E9 and
# asserts not instr.isascii() before expecting ValueError (S1-R9.4).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

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
from pathlib import Path

wt = Path(sys.argv[1])
inv_file = Path(sys.argv[2])

try:
    from actl.session import start_session
except ImportError as exc:
    print(f"FAIL: S1-R9.4: cannot import actl.session.start_session: {exc}")
    sys.exit(1)

non_ascii = "Implement caf\u00e9 feature"
if non_ascii.isascii():
    print("FAIL: S1-R9.4: non_ascii fixture is ASCII; use an unambiguous non-ASCII code point")
    sys.exit(1)

bad_cases = [
    ("overflow_100k", "impl-valid-001", "A" * 99999),
    ("non_ascii", "impl-valid-001", non_ascii),
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
    print("FAIL: S1-R9.4: arouter/agent was invoked despite invalid start_session arguments")
    sys.exit(1)

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
