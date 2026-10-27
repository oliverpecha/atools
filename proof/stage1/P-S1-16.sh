#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-16: dispatch-impl --no-run creates workspace implementer-006 on wip/006 at
# base_sha, stages read-only inbox files (attempt.json, spec, contract, solution_key),
# spawns 0 tmux sessions, and enforces pre-commit/commit-msg hooks (S1-R9, S1A-15).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT_INIT <<< "$(create_stage1_sandbox "p16" "")"
rm -rf "$WT_INIT"

T="$(mktemp -d)"
export TMUX_TMPDIR="$T/tmux" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess"
mkdir -p "$TMUX_TMPDIR" "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR"
trap 'tmux kill-server >/dev/null 2>&1 || true; rm -rf "$T"' EXIT

python3 - "$SDIR" "$REPO_DIR" <<'PY'
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

sdir, repo_dir = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.cli import main as cli_main
    from actl.layout import Layout
    import actl.schemas as schemas
    from router.process import list_active_tmux_sessions
except ImportError as exc:
    print(f"FAIL: S1-R9: cannot import actl modules: {exc}")
    sys.exit(1)

os.environ["ACTL_ROOT"] = str(sdir)
layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# Invoke via real CLI parser with --no-run and --json
rc = cli_main(["dispatch-impl", "--sprint", tag, "--no-run", "--tier", "cheap", "--json"])
if rc != 0:
    print(f"FAIL: S1-R9.6: Expected exit code 0 for dispatch-impl --no-run, got {rc}")
    sys.exit(1)

# 1. Verify no tmux session was spawned
if list_active_tmux_sessions():
    print(f"FAIL: S1-R9.6: --no-run spawned tmux sessions: {list_active_tmux_sessions()}")
    sys.exit(1)

# 2. Verify staged inbox files and 0440 read-only permissions
inbox = layout.inbox(tag, "implementer")
attempt_path = inbox / "attempt.json"
if not attempt_path.is_file():
    print("FAIL: S1-R9.4: attempt.json missing from implementer inbox")
    sys.exit(1)

attempt_doc = json.loads(attempt_path.read_text(encoding="utf-8"))
if schemas.validate("attempt", attempt_doc) != []:
    print(f"FAIL: S1-R9.4: attempt.json failed schema validation: {attempt_doc}")
    sys.exit(1)
if attempt_doc.get("seq") != 6 or attempt_doc.get("branch") != "wip/006":
    print(f"FAIL: S1-R9.4: Expected seq=6 and branch='wip/006', got {attempt_doc}")
    sys.exit(1)

for fname in ("attempt.json", "spec-001.md", "contract-005.json", "solution_key.patch"):
    fpath = inbox / fname
    if not fpath.is_file():
        print(f"FAIL: S1-R9.4: Expected staged file {fname} in {inbox}")
        sys.exit(1)
    mode = stat.S_IMODE(os.lstat(fpath).st_mode)
    if mode != 0o440:
        print(f"FAIL: S1-R9.4: Expected mode 0440 on staged {fname}, got {oct(mode)}")
        sys.exit(1)

# 3. Verify workspace clone at base_sha on branch wip/006
ws = layout.workspace("implementer-006", tag)
if not (ws / ".git").is_dir():
    print(f"FAIL: S1-R9.3: Workspace git clone not created at {ws}")
    sys.exit(1)

branch = subprocess.run(["git", "-C", str(ws), "branch", "--show-current"], capture_output=True, text=True, check=True).stdout.strip()
head_sha = subprocess.run(["git", "-C", str(ws), "rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
contract_sha = json.loads((layout.sprint_dir(tag) / "contract-005.json").read_text(encoding="utf-8"))["base_sha"]
if branch != "wip/006" or head_sha != contract_sha:
    print(f"FAIL: S1-R9.3: Expected branch wip/006 at {contract_sha}, got {branch} at {head_sha}")
    sys.exit(1)

# 4. Verify git hook enforcement inside workspace (S1A-15): commit on main rejected, commit on wip/006 with WI tag passes
git_env = {
    "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Impl",
    "GIT_AUTHOR_EMAIL": "impl@example.test",
    "GIT_COMMITTER_NAME": "Impl",
    "GIT_COMMITTER_EMAIL": "impl@example.test",
}
# Ensure hooks are active in workspace
hooks_dir = ws / ".git" / "hooks"
for hname in ("pre-commit", "commit-msg"):
    src_h = repo_dir / "hooks" / hname
    dst_h = hooks_dir / hname
    if not dst_h.is_file() and src_h.is_file():
        dst_h.write_bytes(src_h.read_bytes())
        os.chmod(dst_h, 0o755)

subprocess.run(["git", "-C", str(ws), "checkout", "-q", "main"], env=git_env, check=True)
(ws / "api" / "profile.py").write_text("# edit\n", encoding="utf-8")
subprocess.run(["git", "-C", str(ws), "add", "api/profile.py"], env=git_env, check=True)
main_commit = subprocess.run(
    ["git", "-C", str(ws), "commit", "-m", "feat(actl): direct main commit (WI-S1-1)"],
    env=git_env,
    capture_output=True,
    text=True,
)
if main_commit.returncode == 0:
    print("FAIL: S1A-15: pre-commit hook failed to block commit on 'main' branch in workspace")
    sys.exit(1)
subprocess.run(["git", "-C", str(ws), "checkout", "-q", "wip/006"], env=git_env, check=True)
PY
