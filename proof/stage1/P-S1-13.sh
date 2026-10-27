#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-13: O1 stages ONLY proofs/ and probe.sh into sibling <worktree>.oracle-stage/
# with mode 0550, executes from there with cwd=worktree, and removes staging dir
# in finally even on timeout/failure (GD-01 fix: witness file proves execution).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p13" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import os
import stat
import sys
from pathlib import Path

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.verify import run_o1
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R4: cannot import actl.verify.run_o1: {exc}")
    sys.exit(1)

tag = "2026-10-16_public-profiles"
oracle = Layout(sdir).sprint_dir(tag) / "oracle-003"
witness_file = sdir / "staging_witness.txt"
stage_dir = wt.parent / f"{wt.name}.oracle-stage"

# Inject a proof script that inspects its own path, permissions, sibling contents, and cwd
inspector_script = oracle / "proofs" / "00_inspect_stage.sh"
inspector_script.write_text(f"""#!/usr/bin/env bash
set -euo pipefail
SELF_PATH="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)/$(basename "${{BASH_SOURCE[0]}}")"
STAGE_ROOT="$(cd "$(dirname "${{BASH_SOURCE[0]}}")/.." && pwd)"
MODE_OCT="$(stat -c '%a' "$SELF_PATH")"
HAS_MUTANTS="no"
[[ -e "$STAGE_ROOT/mutants" || -e "$STAGE_ROOT/solution_key.patch" || -e "$STAGE_ROOT/coverage.md" ]] && HAS_MUTANTS="yes"
HAS_WT_LEAK="no"
[[ -e "{wt}/proofs" || -e "{wt}/probe.sh" ]] && HAS_WT_LEAK="yes"
printf 'cwd=%s\\nstage=%s\\nmode=%s\\nmutants=%s\\nwt_leak=%s\\n' "$(pwd)" "$STAGE_ROOT" "$MODE_OCT" "$HAS_MUTANTS" "$HAS_WT_LEAK" > "{witness_file}"
""", encoding="utf-8")
os.chmod(inspector_script, 0o755)

steps = run_o1(oracle, wt)
if not isinstance(steps, list) or len(steps) < 5:
    print(f"FAIL: S1-R4.1: Expected 5 executed O1 steps, got {steps!r}")
    sys.exit(1)
if not witness_file.is_file():
    print("FAIL: S1-R4.1: Injected staging inspector proof was never executed (no witness file)")
    sys.exit(1)

kv = dict(line.split("=", 1) for line in witness_file.read_text(encoding="utf-8").strip().splitlines())
if Path(kv["cwd"]).resolve() != wt.resolve():
    print(f"FAIL: S1-R5.3: O1 cwd {kv['cwd']} != worktree {wt}")
    sys.exit(1)
if Path(kv["stage"]).resolve() != stage_dir.resolve():
    print(f"FAIL: S1-R4.1: O1 script did not run from sibling {stage_dir}, ran from {kv['stage']}")
    sys.exit(1)
if kv["mode"] != "550":
    print(f"FAIL: S1-R4.3: Expected mode 550 on staged proof, got {kv['mode']}")
    sys.exit(1)
if kv["mutants"] != "no" or kv["wt_leak"] != "no":
    print(f"FAIL: S1-R4.2: Non-proof oracle files leaked into staging or worktree: {kv}")
    sys.exit(1)
if stage_dir.exists():
    print(f"FAIL: S1-R4.4: Sibling staging dir was not removed after run_o1: {stage_dir}")
    sys.exit(1)

# 2. Verify cleanup in finally block even when a proof times out
timeout_script = oracle / "proofs" / "99_timeout.sh"
timeout_script.write_text("#!/usr/bin/env bash\nsleep 10\n", encoding="utf-8")
os.chmod(timeout_script, 0o755)
steps_to = run_o1(oracle, wt, timeout_s=1)
to_step = next((s for s in steps_to if s.id == "O1:99_timeout.sh"), None)
if to_step is None or to_step.exit_code != 124:
    print(f"FAIL: S1-R5.4: Expected exit_code 124 on O1 timeout, got {to_step}")
    sys.exit(1)
if stage_dir.exists():
    print(f"FAIL: S1-R4.4: Staging directory survived after timeout: {stage_dir}")
    sys.exit(1)
PY
