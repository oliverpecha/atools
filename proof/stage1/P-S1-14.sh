#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-14: O1 runs under strict environment allowlist; witness file proves the
# injected probe ran, caller secret env vars were purged, and HOME/TMPDIR are
# throwaway directories removed after run_o1 (GD-01 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p14" "good.patch")"

export FORBIDDEN_VAR_TEST="must_not_leak_12345"
export AWS_SECRET_ACCESS_KEY="super_secret_caller_env"

python3 - "$SDIR" "$WT" <<'PY'
import os
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

probe = oracle / "probe.sh"
probe.write_text(
    probe.read_text(encoding="utf-8")
    + f'\npython3 -c \'import json,os; open({str(env_dump)!r},"w").write(json.dumps(dict(os.environ)))\'\n',
    encoding="utf-8",
)

steps = run_o1(oracle, wt, target_cmd="python3 -m api.cli")
if not isinstance(steps, list) or len(steps) != 4 or any(s.exit_code != 0 for s in steps):
    print(f"FAIL: S1-R5.2: Expected 4 passing O1 steps, got {steps!r}")
    sys.exit(1)

if not env_dump.is_file():
    print("FAIL: S1-R5.2: Injected probe.sh did not execute (env_dump.txt missing)")
    sys.exit(1)

import json
child_env = json.loads(env_dump.read_text(encoding="utf-8"))
allowed_keys = {"PATH", "LANG", "LC_ALL", "HOME", "TMPDIR", "ACTL_TARGET_CMD", "PYTHONDONTWRITEBYTECODE", "PWD", "SHLVL", "_"}
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
PY
