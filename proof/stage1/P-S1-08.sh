#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-08: Guard self-tests pass on valid config (covering G1..G6); corrupting
# config/secrets.toml in a scratch copy causes run_selftests() to return exit_code 3
# and verify_impl to halt with selftest_failed (GD-01 fix: no TypeError swallow).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p08" "good.patch")"

python3 - "$REPO_DIR" "$SDIR" "$WT" <<'PY'
import shutil
import subprocess
import sys
from pathlib import Path

repo_dir, sdir, wt = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

try:
    from actl.verify import run_selftests, verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3.7: cannot import actl.verify.run_selftests: {exc}")
    sys.exit(1)

# 1. Positive control: clean repository self-tests cover G1..G6 and all pass with exit_code == 0
results = run_selftests()
if not isinstance(results, list) or len(results) < 6:
    print(f"FAIL: S1-R3.7: Expected at least 6 StepResults (G1..G6) from run_selftests(), got {results!r}")
    sys.exit(1)

ids_text = " ".join(r.id for r in results)
for g in ("G1", "G2", "G3", "G4", "G5", "G6"):
    if g not in ids_text:
        print(f"FAIL: S1-R3.7: Guard {g} missing from run_selftests() results: {[r.id for r in results]}")
        sys.exit(1)

for r in results:
    if r.exit_code != 0:
        print(f"FAIL: S1-R3.7: Clean self-test failed on {r.id}: exit={r.exit_code}, line={r.failing_line}")
        sys.exit(1)

# 2. Negative control: copy src/ and config/ to a scratch tree, corrupt config/secrets.toml,
# and run in a subprocess so module-level REPO_ROOT resolves to the corrupted config.
scratch_repo = sdir / "corrupt_repo"
scratch_repo.mkdir(parents=True, exist_ok=True)
shutil.copytree(repo_dir / "src", scratch_repo / "src")
shutil.copytree(repo_dir / "schemas", scratch_repo / "schemas")
(scratch_repo / "config").mkdir(parents=True, exist_ok=True)
if (repo_dir / "config" / "graph.toml").is_file():
    shutil.copy2(repo_dir / "config" / "graph.toml", scratch_repo / "config" / "graph.toml")
# Write invalid TOML to config/secrets.toml
(scratch_repo / "config" / "secrets.toml").write_text("[[rules\ninvalid_toml = [\n", encoding="utf-8")
(scratch_repo / "config" / "forbidden.toml").write_text("[[rules]]\n", encoding="utf-8")

check_code = """
import sys
from pathlib import Path
from actl.verify import run_selftests, verify_impl
from actl.layout import Layout

res = run_selftests()
if not isinstance(res, list) or not any(r.exit_code == 3 for r in res):
    print(f"FAIL: S1-R3.7: Expected exit_code 3 from run_selftests() on corrupt secrets.toml, got {res!r}")
    sys.exit(1)

layout = Layout(Path(sys.argv[1]))
ver = verify_impl(layout, "2026-10-16_public-profiles", worktree=Path(sys.argv[2]))
if ver.get("exit_code") is not None or ver.get("halt") != {"reason": "selftest_failed"}:
    print(f"FAIL: S1-R2.2: Expected halt=selftest_failed and exit_code=None, got {ver!r}")
    sys.exit(1)
"""
proc = subprocess.run(
    [sys.executable, "-c", check_code, str(sdir), str(wt)],
    env={"PYTHONPATH": str(scratch_repo / "src"), "PATH": "/usr/bin:/bin"},
    capture_output=True,
    text=True,
)
if proc.returncode != 0:
    print(proc.stdout + proc.stderr)
    sys.exit(1)
PY
