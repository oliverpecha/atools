#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-14: O1 runs under strict environment allowlist; witness script is a
# separate file (no nested shell quoting); timeout returns 124 (S1-R5.2/S1-R5.4).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p14" "good.patch")"

export FORBIDDEN_VAR_TEST="must_not_leak_12345"
export AWS_SECRET_ACCESS_KEY="super_secret_caller_env"

python3 - "$SDIR" "$WT" <<'PY'
import json
import os
import stat
import sys
from pathlib import Path

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.verify import run_o1
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R5.2: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

tag = "2026-10-16_public-profiles"
oracle = Layout(sdir).sprint_dir(tag) / "oracle-003"
env_dump = sdir / "o1_env_dump.txt"
witness_py = sdir / "dump_o1_env.py"
witness_py.write_text(
    "import json, os, sys\n"
    "open(sys.argv[1], 'w', encoding='utf-8').write(json.dumps(dict(os.environ)))\n",
    encoding="utf-8",
)
os.chmod(witness_py, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)

probe = oracle / "probe.sh"
probe.write_text(
    probe.read_text(encoding="utf-8")
    + "\npython3 "
    + str(witness_py)
    + " "
    + str(env_dump)
    + "\n",
    encoding="utf-8",
)

# The generated probe body must be valid shell (no nested-quote SyntaxError).
import subprocess
chk = subprocess.run(["bash", "-n", str(probe)], capture_output=True, text=True)
if chk.returncode != 0:
    print(f"FAIL: S1-R5.2: generated probe.sh failed bash -n: {chk.stderr}")
    sys.exit(1)

steps = run_o1(oracle, wt, target_cmd="python3 -m api.cli")
if not isinstance(steps, list) or len(steps) != 4 or any(s.exit_code != 0 for s in steps):
    print(f"FAIL: S1-R5.2: Expected 4 passing O1 steps, got {steps!r}")
    sys.exit(1)

if not env_dump.is_file():
    print("FAIL: S1-R5.2: Injected probe.sh did not execute (env_dump.txt missing)")
    sys.exit(1)

child_env = json.loads(env_dump.read_text(encoding="utf-8"))
allowed_keys = {
    "PATH", "LANG", "LC_ALL", "HOME", "TMPDIR",
    "ACTL_TARGET_CMD", "PYTHONDONTWRITEBYTECODE", "PWD", "SHLVL", "_",
}
extra_keys = set(child_env.keys()) - allowed_keys
if extra_keys:
    print(f"FAIL: S1-R5.2: Unallowlisted env vars leaked into O1 execution: {sorted(extra_keys)}")
    sys.exit(1)

if "FORBIDDEN_VAR_TEST" in child_env or "AWS_SECRET_ACCESS_KEY" in child_env:
    print("FAIL: S1-R5.2: Caller secret env vars leaked into O1")
    sys.exit(1)

child_home = Path(child_env["HOME"])
child_tmp = Path(child_env["TMPDIR"])
if child_home.resolve() == Path.home().resolve():
    print(f"FAIL: S1-R5.2: O1 HOME was not a throwaway directory: {child_home}")
    sys.exit(1)
if child_home.exists() or child_tmp.exists():
    print(f"FAIL: S1-R4.4: Throwaway HOME ({child_home}) or TMPDIR ({child_tmp}) was not cleaned up")
    sys.exit(1)

# Timeout control: a sleeping proof is killed and returns exit_code 124.
timeout_script = oracle / "proofs" / "99_sleep.sh"
timeout_script.write_text("#!/usr/bin/env bash\nexec sleep 30\n", encoding="utf-8")
os.chmod(timeout_script, 0o755)
steps_to = run_o1(oracle, wt, timeout_s=1, target_cmd="python3 -m api.cli")
to_step = next((s for s in steps_to if s.id == "O1:99_sleep.sh"), None)
if to_step is None or to_step.exit_code != 124:
    print(f"FAIL: S1-R5.4: Expected O1 timeout exit_code 124, got {to_step}")
    sys.exit(1)
PY
