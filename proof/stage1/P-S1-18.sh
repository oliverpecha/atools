#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-18: Phase 3 decision rules table  --  evaluates all 10 distinct states
# plus non-implementer stage fall-through on a valid golden sprint (GD-01 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p18" "good.patch")"

python3 - "$SDIR" <<'PY'
import json
import sys
from pathlib import Path

sdir = Path(sys.argv[1])

try:
    import actl.next_rules.phase3 as p3
    from actl.next import decide_next
    from actl.layout import Layout
    from actl.seq import read_state, update_state
except ImportError as exc:
    print(f"FAIL: S1-R12: cannot import actl.next_rules.phase3: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
runs = layout.runs_dir(tag)
outbox = layout.outbox(tag, "implementer")
outbox.mkdir(parents=True, exist_ok=True)
ws_dir = sdir / "sprints" / "target-repo" / tag / "workspaces"


def clean_runs_and_outbox() -> None:
    for f in runs.glob("verification-*.json"):
        f.unlink()
    for f in runs.glob("closure-*.json"):
        f.unlink()
    for f in outbox.glob("*.json"):
        f.unlink()
    if ws_dir.exists():
        for d in ws_dir.iterdir():
            if d.is_dir():
                import shutil
                shutil.rmtree(d)


def make_ver(seq_n: int, exit_code: int | None, stage: str = "offline", failing_step: str | None = None, parent: str | None = None, halt: dict | None = None) -> dict:
    return {
        "kind": "verification",
        "seq": seq_n,
        "parent": parent,
        "id": f"verification-{seq_n:03d}",
        "stage": stage,
        "oracle": "oracle-003",
        "contract": "contract-005",
        "head": "01d880bc3176cdd8f31d72e67bb3eba54d634378",
        "exit_code": exit_code,
        "steps": [],
        "failing_step": failing_step,
        "failing_line": "failed" if failing_step else None,
        "tripwires": [],
        "halt": halt,
        "session": None,
    }


# 0. Non-implementer stage returns None
update_state(layout, tag, {"active_stage": "oracle", "status": "running", "tmux_sessions": []})
if p3.evaluate(layout, tag) is not None:
    print("FAIL: S1-R12.2: Non-implementer stage must return None")
    sys.exit(1)

# Restore active_stage = implementer
update_state(layout, tag, {"active_stage": "implementer", "status": "running", "tmux_sessions": []})

# State 1: Initial dispatch (no workspaces, no verifications, attempts=0)
clean_runs_and_outbox()
update_state(layout, tag, {"attempts": {"implementer": 0}, "grants": {"implementer": 0}, "tmux_sessions": []})
r1 = decide_next(layout, tag)
if r1.get("action") != "dispatch" or f"actl dispatch-impl --sprint {tag}" not in r1.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 10 initial dispatch): got {r1}")
    sys.exit(1)

# State 2: Active tmux session running -> wait
update_state(layout, tag, {"tmux_sessions": ["impl-public-profiles-006"]})
r2 = decide_next(layout, tag, session_probe=lambda s: {"running": True, "exit_code": None, "lost": False})
if r2.get("action") != "wait" or "impl-public-profiles-006" not in r2.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 1 active session): got {r2}")
    sys.exit(1)

# State 3: Session lost (not running, exit_code=None, lost=True) -> verify (to record red G2)
r3 = decide_next(layout, tag, session_probe=lambda s: {"running": False, "exit_code": None, "lost": True})
if r3.get("action") != "verify" or "verify-impl" not in r3.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 2 session lost): got {r3}")
    sys.exit(1)

# State 4: Session finished, unverified closure in outbox (even with reason='blocked') -> verify with --closure
update_state(layout, tag, {"tmux_sessions": []})
(ws_dir / "implementer-006").mkdir(parents=True, exist_ok=True)
(outbox / "closure.json").write_text(json.dumps({
    "reason": "blocked",
    "blocking_step": "O1:01_public.sh",
    "notes": ["blocked note"],
    "backlog": [],
    "solution_key_divergence": {"requirement_id": "R1", "rationale": "conflict"},
}), encoding="utf-8")
r4 = decide_next(layout, tag)
if r4.get("action") != "verify" or "--closure" not in r4.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 3 unverified closure): got {r4}")
    sys.exit(1)

# State 5: Session finished, workspace exists, no closure in outbox, unverified -> verify
(outbox / "closure.json").unlink()
r5 = decide_next(layout, tag)
if r5.get("action") != "verify" or "verify-impl" not in r5.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 4 finished without closure): got {r5}")
    sys.exit(1)

# State 6: Verified blocked closure confirmed (stage='blocked_check', failing_step='O1:01_public.sh' != 'G2') -> hold_owner
(runs / "verification-007.json").write_text(
    json.dumps(make_ver(7, 1, stage="blocked_check", failing_step="O1:01_public.sh", parent="closure-006.json")),
    encoding="utf-8",
)
r6 = decide_next(layout, tag)
if r6.get("action") != "hold_owner" or r6.get("command") != "":
    print(f"FAIL: S1-R12.3 (Row 5 confirmed blocked): got {r6}")
    sys.exit(1)

# State 7: Last verification green (exit_code == 0) -> done (or promote)
(runs / "verification-007.json").write_text(
    json.dumps(make_ver(7, 0, stage="offline", failing_step=None, parent="closure-006.json")),
    encoding="utf-8",
)
r7 = decide_next(layout, tag)
if r7.get("action") not in ("done", "promote"):
    print(f"FAIL: S1-R12.3 (Row 6 green verification): got {r7}")
    sys.exit(1)

# State 8: Last verification red, attempts (1) < max_attempts (2) -> dispatch retry
(runs / "verification-007.json").write_text(
    json.dumps(make_ver(7, 1, stage="offline", failing_step="G3", parent="closure-006.json")),
    encoding="utf-8",
)
update_state(layout, tag, {"attempts": {"implementer": 1}, "grants": {"implementer": 0}})
r8 = decide_next(layout, tag)
if r8.get("action") != "dispatch" or f"actl dispatch-impl --sprint {tag}" not in r8.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 9 retry dispatch): got {r8}")
    sys.exit(1)

# State 9: Last verification red, attempts (2) >= max_attempts (2), grants == 0 -> escalate_attempts
update_state(layout, tag, {"attempts": {"implementer": 2}, "grants": {"implementer": 0}})
r9 = decide_next(layout, tag)
if r9.get("action") != "escalate_attempts" or r9.get("command") != "":
    print(f"FAIL: S1-R12.3 (Row 7 escalate_attempts): got {r9}")
    sys.exit(1)

# State 10: Last verification red, attempts (2) >= max_attempts (2), grants (1) > 0 -> dispatch granted attempt
update_state(layout, tag, {"attempts": {"implementer": 2}, "grants": {"implementer": 1}})
r10 = decide_next(layout, tag)
if r10.get("action") != "dispatch" or f"actl dispatch-impl --sprint {tag}" not in r10.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 8 granted dispatch): got {r10}")
    sys.exit(1)

# State 11: Sprint status == 'hold' -> hold_owner
update_state(layout, tag, {"status": "hold"})
r11 = decide_next(layout, tag)
if r11.get("action") != "hold_owner" or r11.get("command") != "":
    print(f"FAIL: S1-R12.3 (Row 2 hold status): got {r11}")
    sys.exit(1)
PY
