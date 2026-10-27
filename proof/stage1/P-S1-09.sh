#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-09: Untampered oracle passes G1; 1-byte tamper in oracle-003/probe.sh
# halts G1 with exit_code 3, sets verification.exit_code=None, halt.reason="integrity_mismatch",
# sets state.status="hold", and consumes 0 implementer attempts (S1-R3.1, S1-R2.2).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p09" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import sys
from pathlib import Path

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.verify import check_guards, verify_impl
    from actl.layout import Layout
    from actl.seq import read_state
except ImportError as exc:
    print(f"FAIL: S1-R3.1: cannot import actl.verify: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# 1. Positive control: untampered oracle passes G1
res_clean = check_guards(layout, tag, wt)
g1_clean = next((r for r in res_clean if r.id == "G1"), None)
if g1_clean is None or g1_clean.exit_code != 0:
    print(f"FAIL: S1-R3.1: Untampered oracle failed G1: {g1_clean}")
    sys.exit(1)

# 2. Tamper 1 byte in oracle-003/probe.sh
probe_path = layout.sprint_dir(tag) / "oracle-003" / "probe.sh"
probe_path.write_bytes(probe_path.read_bytes() + b"\n")

res_tampered = check_guards(layout, tag, wt)
if len(res_tampered) != 1 or res_tampered[0].id != "G1" or res_tampered[0].exit_code != 3:
    print(f"FAIL: S1-R3.1: Expected check_guards to stop immediately at G1 with exit_code 3, got {res_tampered}")
    sys.exit(1)

ver = verify_impl(layout, tag, worktree=wt)
if ver.get("exit_code") is not None:
    print(f"FAIL: S1-R2.2: Expected verification.exit_code None on halt, got {ver.get('exit_code')}")
    sys.exit(1)
if ver.get("halt") != {"reason": "integrity_mismatch"}:
    print(f"FAIL: S1-R2.2: Expected halt={{'reason': 'integrity_mismatch'}}, got {ver.get('halt')}")
    sys.exit(1)

st = read_state(layout, tag)
if st.get("attempts", {}).get("implementer") != 0:
    print(f"FAIL: S1-R2.2: Halt must not increment attempts.implementer, got {st.get('attempts')}")
    sys.exit(1)
if st.get("status") != "hold":
    print(f"FAIL: S1-R2.2: Halt must transition sprint status to 'hold', got {st.get('status')}")
    sys.exit(1)
PY
