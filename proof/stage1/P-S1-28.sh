#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-28: CLI exit code table (0, 1, 2, 3, 4) via actl.cli.main for
# verify-impl, selftest, and wait, plus S1-R13 determinism verification (GD-01 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p28_ok" "good.patch")"
IFS='|' read -r SDIR_RED WT_RED <<< "$(create_stage1_sandbox "p28_red" "bad_scope.patch")"
IFS='|' read -r SDIR_HALT WT_HALT <<< "$(create_stage1_sandbox "p28_halt" "good.patch")"

python3 - "$SDIR_OK" "$WT_OK" "$SDIR_RED" "$WT_RED" "$SDIR_HALT" "$WT_HALT" <<'PY'
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

sdir_ok, wt_ok, sdir_red, wt_red, sdir_halt, wt_halt = [Path(x) for x in sys.argv[1:7]]

try:
    from actl.cli import main as cli_main
    from actl.verify import verify_impl
    import actl.cmd_verify_impl  # ensure Stage 1 CLI modules exist
    import actl.cmd_selftest
    import actl.cmd_wait
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R11: cannot import Stage 1 CLI modules: {exc}")
    sys.exit(1)

tag = "2026-10-16_public-profiles"
closure_ok = sdir_ok / "closure_ok.json"
closure_ok.write_text(json.dumps({
    "reason": "done",
    "blocking_step": None,
    "notes": ["ok"],
    "backlog": [],
    "solution_key_divergence": None,
}), encoding="utf-8")

# 1. Exit 0: actl selftest --json & actl verify-impl on good.patch
os.environ["ACTL_ROOT"] = str(sdir_ok)
rc_st = cli_main(["selftest", "--json"])
if rc_st != 0:
    print(f"FAIL: S1-R11.2: Expected actl selftest exit 0, got {rc_st}")
    sys.exit(1)

rc_0 = cli_main(["verify-impl", "--sprint", tag, "--closure", str(closure_ok), "--worktree", str(wt_ok), "--json"])
if rc_0 != 0:
    print(f"FAIL: S1-R11.1: Expected exit 0 on good.patch, got {rc_0}")
    sys.exit(1)

# 2. S1-R13 Determinism: run verify_impl a second time on wt_ok and compare normalized records
ver1 = json.loads((Layout(sdir_ok).runs_dir(tag) / "verification-007.json").read_text(encoding="utf-8"))
ver2 = verify_impl(Layout(sdir_ok), tag, closure_path=closure_ok, worktree=wt_ok)
for k in ("exit_code", "stage", "oracle", "contract", "head", "steps", "failing_step", "failing_line", "tripwires", "halt"):
    if ver1.get(k) != ver2.get(k):
        print(f"FAIL: S1-R13.2: Non-deterministic verification field {k!r}: {ver1.get(k)} != {ver2.get(k)}")
        sys.exit(1)

# 3. Exit 1: actl verify-impl on bad_scope.patch
os.environ["ACTL_ROOT"] = str(sdir_red)
closure_red = sdir_red / "closure_red.json"
closure_red.write_text(closure_ok.read_text(encoding="utf-8"), encoding="utf-8")
rc_1 = cli_main(["verify-impl", "--sprint", tag, "--closure", str(closure_red), "--worktree", str(wt_red), "--json"])
if rc_1 != 1:
    print(f"FAIL: S1-R11.1: Expected exit 1 on bad_scope.patch, got {rc_1}")
    sys.exit(1)

# 4. Exit 2: UsageError on non-existent --closure path or missing required flags
rc_2a = cli_main(["verify-impl", "--sprint", tag, "--closure", str(sdir_ok / "missing.json"), "--worktree", str(wt_ok), "--json"])
rc_2b = cli_main(["verify-impl", "--json"])
if rc_2a != 2 or rc_2b != 2:
    print(f"FAIL: S1-R11.1: Expected exit 2 on usage errors, got {rc_2a}, {rc_2b}")
    sys.exit(1)

# 5. Exit 3: Halt on tampered oracle
os.environ["ACTL_ROOT"] = str(sdir_halt)
probe = Layout(sdir_halt).sprint_dir(tag) / "oracle-003" / "probe.sh"
probe.write_bytes(probe.read_bytes() + b"\n# tamper\n")
closure_halt = sdir_halt / "closure_halt.json"
closure_halt.write_text(closure_ok.read_text(encoding="utf-8"), encoding="utf-8")
rc_3 = cli_main(["verify-impl", "--sprint", tag, "--closure", str(closure_halt), "--worktree", str(wt_halt), "--json"])
if rc_3 != 3:
    print(f"FAIL: S1-R11.1: Expected exit 3 on tampered oracle halt, got {rc_3}")
    sys.exit(1)

# 6. Exit 4: Environment error when tmux is missing in actl wait
with patch("shutil.which", return_value=None):
    rc_4 = cli_main(["wait", "impl-test-001", "--json"])
if rc_4 != 4:
    print(f"FAIL: S1-R11.1: Expected exit 4 when tmux is missing, got {rc_4}")
    sys.exit(1)
PY
