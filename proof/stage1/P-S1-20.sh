#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-20: Detached implementer dispatch via private tmux server + stub agent (S1-R9, D-42):
# - Case A: stub agent applies good.patch, writes outbox closure.json, exits 0 -> verification green, session.exit_code=0
# - Case B: stub agent applies good.patch, writes outbox closure.json, exits 7 -> verification green, session.exit_code=7
# - Case C (D-42 poison test): stub agent writes closure-draft.json in worktree ONLY (no outbox closure) -> G2 red (exit 1)
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed (environment error)"; exit 4; }

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_A WT_A <<< "$(create_stage1_sandbox "p20_a" "")"
IFS='|' read -r SDIR_B WT_B <<< "$(create_stage1_sandbox "p20_b" "")"
IFS='|' read -r SDIR_C WT_C <<< "$(create_stage1_sandbox "p20_c" "")"
rm -rf "$WT_A" "$WT_B" "$WT_C"

T="$(mktemp -d)"
export TMUX_TMPDIR="$T/tmux" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess"
mkdir -p "$TMUX_TMPDIR" "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR" "$T/bin"
trap 'tmux kill-server >/dev/null 2>&1 || true; rm -rf "$T"' EXIT

printf '#!/usr/bin/env bash\nexit 0\n' > "$T/bin/loginctl"
chmod +x "$T/bin/loginctl"

# Stub agent inspects the current working directory (which is sprints/<repo>/<tag>/workspaces/implementer-006)
# to find its sprint root and determine whether to run Case A, B, or C.
cat > "$T/bin/agent" <<EOF
#!/usr/bin/env bash
set -euo pipefail
WT="\$(pwd)"
echo "\$WT" > "$T/agent_last_pwd.txt"
SPRINT_ROOT="\$(cd "\$WT/../.." && pwd)"
OUTBOX="\$SPRINT_ROOT/mailboxes/implementer/outbox"

GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \\
  git -c core.hooksPath=/dev/null apply "${REPO_DIR}/fixtures/golden/implementations/good.patch"
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \\
  git -c core.hooksPath=/dev/null add -A
GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null \\
  GIT_AUTHOR_NAME="Stub" GIT_AUTHOR_EMAIL="s@example.test" \\
  GIT_COMMITTER_NAME="Stub" GIT_COMMITTER_EMAIL="s@example.test" \\
  git -c core.hooksPath=/dev/null -c commit.gpgsign=false commit -q -m "feat(actl): stub impl (WI-S1-STUB)"

if [[ "\$WT" == *"p20_a"* ]]; then
  cat > "\$OUTBOX/closure.json" <<'JSON'
{"reason":"done","blocking_step":null,"notes":["done A"],"backlog":[],"solution_key_divergence":null}
JSON
  exit 0
elif [[ "\$WT" == *"p20_b"* ]]; then
  cat > "\$OUTBOX/closure.json" <<'JSON'
{"reason":"done","blocking_step":null,"notes":["done B despite exit 7"],"backlog":[],"solution_key_divergence":null}
JSON
  exit 7
elif [[ "\$WT" == *"p20_c"* ]]; then
  # D-42 poison: write closure-draft.json and closure.json inside worktree, NOTHING in outbox
  cat > "\$WT/closure-draft.json" <<'JSON'
{"reason":"done","blocking_step":null,"notes":["poison worktree draft"],"backlog":[],"solution_key_divergence":null}
JSON
  cat > "\$WT/closure.json" <<'JSON'
{"reason":"done","blocking_step":null,"notes":["poison worktree closure"],"backlog":[],"solution_key_divergence":null}
JSON
  exit 0
fi
EOF
chmod +x "$T/bin/agent"
export PATH="$T/bin:$PATH"

python3 - "$SDIR_A" "$SDIR_B" "$SDIR_C" "$T" <<'PY'
import json
import os
import sys
from pathlib import Path

sdir_a, sdir_b, sdir_c, t_dir = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.cli import main as cli_main
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl modules: {exc}")
    sys.exit(1)

tag = "2026-10-16_public-profiles"

# Case A: Normal completion (exit 0 + valid outbox closure) -> CLI exit 0, session.exit_code == 0
os.environ["ACTL_ROOT"] = str(sdir_a)
rc_a = cli_main(["dispatch-impl", "--sprint", tag, "--mode", "detach", "--tier", "cheap"])
if rc_a != 0:
    print(f"FAIL: S1-R9 (Case A): Expected dispatch-impl exit 0, got {rc_a}")
    sys.exit(1)

pwd_file = t_dir / "agent_last_pwd.txt"
if not pwd_file.is_file():
    print("FAIL: S1-R9 (Case A): Stub agent never executed!")
    sys.exit(1)
expected_ws_a = Layout(sdir_a).workspace("implementer-006", tag)
if Path(pwd_file.read_text(encoding="utf-8").strip()).resolve() != expected_ws_a.resolve():
    print(f"FAIL: S1-R9 (P-S1-25 cwd): Agent cwd {pwd_file.read_text()} != {expected_ws_a}")
    sys.exit(1)

runs_a = Layout(sdir_a).runs_dir(tag)
ver_files_a = sorted(runs_a.glob("verification-*.json"))
if not ver_files_a:
    print("FAIL: S1-R9 (Case A): No verification-*.json written after dispatch-impl")
    sys.exit(1)
ver_a = json.loads(ver_files_a[-1].read_text(encoding="utf-8"))
if ver_a.get("exit_code") != 0 or (ver_a.get("session") or {}).get("exit_code") != 0:
    print(f"FAIL: S1-R9 (Case A): Expected verification exit_code=0 and session.exit_code=0, got {ver_a}")
    sys.exit(1)

# Case B: Engine exits 7 with valid outbox closure -> verification still green (exit 0), session.exit_code == 7
os.environ["ACTL_ROOT"] = str(sdir_b)
rc_b = cli_main(["dispatch-impl", "--sprint", tag, "--mode", "detach", "--tier", "cheap"])
if rc_b != 0:
    print(f"FAIL: S1-R14 (Case B): Nonzero engine exit with valid closure must still pass verification (exit 0), got {rc_b}")
    sys.exit(1)
runs_b = Layout(sdir_b).runs_dir(tag)
ver_b = json.loads(sorted(runs_b.glob("verification-*.json"))[-1].read_text(encoding="utf-8"))
if ver_b.get("exit_code") != 0 or (ver_b.get("session") or {}).get("exit_code") != 7:
    print(f"FAIL: S1-R14 (Case B): Expected verification.exit_code=0 and session.exit_code=7, got {ver_b}")
    sys.exit(1)

# Case C (D-42): Worktree poison closure-draft.json ignored; missing outbox closure fails G2 red (exit 1)
os.environ["ACTL_ROOT"] = str(sdir_c)
rc_c = cli_main(["dispatch-impl", "--sprint", tag, "--mode", "detach", "--tier", "cheap"])
if rc_c != 1:
    print(f"FAIL: D-42 (Case C): Expected red exit 1 when outbox closure missing (despite worktree closure-draft.json), got {rc_c}")
    sys.exit(1)
runs_c = Layout(sdir_c).runs_dir(tag)
ver_c = json.loads(sorted(runs_c.glob("verification-*.json"))[-1].read_text(encoding="utf-8"))
if ver_c.get("exit_code") != 1 or ver_c.get("failing_step") != "G2":
    print(f"FAIL: D-42 (Case C): Expected failing_step='G2' and exit_code=1, got {ver_c}")
    sys.exit(1)
PY
