#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-18: Phase 3 decision table, green -> done (not promote), and execute
# generated verify-impl commands (S1A-16, S1-R12).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p18" "good.patch")"

python3 - "$SDIR" "$WT" <<'PY'
import json
import os
import shlex
import sys
from pathlib import Path

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    import actl.next_rules.phase3 as p3
    from actl.next import decide_next
    from actl.layout import Layout
    from actl.seq import read_state, update_state
    from actl.cli import main as cli_main
except ImportError as exc:
    print(f"FAIL: S1-R12: cannot import actl.next_rules.phase3: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
runs = layout.runs_dir(tag)
outbox = layout.outbox(tag, "implementer")
outbox.mkdir(parents=True, exist_ok=True)
ws_dir = sdir / "sprints" / "target-repo" / tag / "workspaces"
os.environ["ACTL_ROOT"] = str(sdir)


def clean_runs_and_outbox() -> None:
    for f in runs.glob("verification-*.json"):
        f.unlink()
    for f in runs.glob("closure-*.json"):
        f.unlink()
    for f in outbox.glob("*.json"):
        f.unlink()
    if ws_dir.exists():
        import shutil
        for d in list(ws_dir.iterdir()):
            if d.is_dir():
                shutil.rmtree(d)


def make_ver(seq_n, exit_code, stage="offline", failing_step=None, parent=None, halt=None):
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


def run_generated(command: str) -> int:
    argv = shlex.split(command)
    if argv and argv[0] == "actl":
        argv = argv[1:]
    os.environ["ACTL_ROOT"] = str(sdir)
    return cli_main(argv)


update_state(layout, tag, {"active_stage": "oracle", "status": "running", "tmux_sessions": []})
if p3.evaluate(layout, tag) is not None:
    print("FAIL: S1-R12.2: Non-implementer stage must return None")
    sys.exit(1)

update_state(layout, tag, {"active_stage": "implementer", "status": "running", "tmux_sessions": []})

clean_runs_and_outbox()
update_state(layout, tag, {"attempts": {"implementer": 0}, "grants": {"implementer": 0}, "tmux_sessions": []})
r1 = decide_next(layout, tag)
if r1.get("action") != "dispatch" or f"actl dispatch-impl --sprint {tag}" not in r1.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 10 initial dispatch): got {r1}")
    sys.exit(1)

update_state(layout, tag, {"tmux_sessions": ["impl-public-profiles-006"]})
r2 = decide_next(layout, tag, session_probe=lambda s: {"running": True, "exit_code": None, "lost": False})
if r2.get("action") != "wait" or "impl-public-profiles-006" not in r2.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 1 active session): got {r2}")
    sys.exit(1)

def assert_red_g2_artifact(label: str, before_attempts: int, failing_line_substr: str) -> None:
    """Lost-session / missing-outbox: rc==1, new verification-NNN.json, parent null, G2."""
    vers = sorted(runs.glob("verification-*.json"))
    if not vers:
        print(f"FAIL: S1A-16: {label}: expected new verification-*.json, none written")
        sys.exit(1)
    doc = json.loads(vers[-1].read_text(encoding="utf-8"))
    if doc.get("parent") is not None:
        print(f"FAIL: S1A-16: {label}: verification.parent must be null, got {doc.get('parent')!r}")
        sys.exit(1)
    if doc.get("failing_step") != "G2":
        print(f"FAIL: S1A-16: {label}: failing_step must be G2, got {doc.get('failing_step')!r}")
        sys.exit(1)
    fl = doc.get("failing_line") or ""
    if failing_line_substr not in fl:
        print(f"FAIL: S1A-16: {label}: failing_line must contain {failing_line_substr!r}, got {fl!r}")
        sys.exit(1)
    if doc.get("exit_code") != 1:
        print(f"FAIL: S1A-16: {label}: verification.exit_code must be 1, got {doc.get('exit_code')!r}")
        sys.exit(1)
    st = read_state(layout, tag)
    impl_attempts = st.get("attempts", {}).get("implementer", 0)
    if impl_attempts != before_attempts + 1:
        print(
            f"FAIL: S1A-16: {label}: attempts.implementer must increment "
            f"{before_attempts}->+1, got {impl_attempts}"
        )
        sys.exit(1)


r3 = decide_next(layout, tag, session_probe=lambda s: {"running": False, "exit_code": None, "lost": True})
if r3.get("action") != "verify" or "verify-impl" not in r3.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 2 session lost): got {r3}")
    sys.exit(1)
if "--closure" in r3.get("command", ""):
    print(f"FAIL: S1A-16: lost-session command must omit --closure, got {r3}")
    sys.exit(1)
attempts_before_lost = read_state(layout, tag).get("attempts", {}).get("implementer", 0)
for f in runs.glob("verification-*.json"):
    f.unlink()
rc_lost = run_generated(r3["command"])
if rc_lost != 1:
    print(f"FAIL: S1A-16: lost-session verify-impl must exit 1 (red G2), got {rc_lost}")
    sys.exit(1)
assert_red_g2_artifact("lost-session", attempts_before_lost, "Session lost")

# Explicit bad --closure path stays usage exit 2 (not conflated with omit --closure).
rc_bad_path = run_generated(f"actl verify-impl --sprint {tag} --closure {sdir / 'no-such-closure.json'}")
if rc_bad_path != 2:
    print(f"FAIL: S1A-16: explicit missing --closure path must be usage exit 2, got {rc_bad_path}")
    sys.exit(1)

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
rc_cl = run_generated(r4["command"])
if rc_cl == 2:
    print("FAIL: S1A-16: verify-impl --closure <existing outbox> must not be usage exit 2")
    sys.exit(1)

(outbox / "closure.json").unlink()
for f in runs.glob("verification-*.json"):
    f.unlink()
r5 = decide_next(layout, tag)
if r5.get("action") != "verify" or "verify-impl" not in r5.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 4 finished without closure): got {r5}")
    sys.exit(1)
if "--closure" in r5.get("command", ""):
    print(f"FAIL: S1A-16: missing-outbox command must omit --closure, got {r5}")
    sys.exit(1)
attempts_before_miss = read_state(layout, tag).get("attempts", {}).get("implementer", 0)
rc_miss = run_generated(r5["command"])
if rc_miss != 1:
    print(f"FAIL: S1A-16: missing-outbox verify-impl must exit 1 (red G2), got {rc_miss}")
    sys.exit(1)
assert_red_g2_artifact("missing-outbox", attempts_before_miss, "Missing implementer closure")

(runs / "verification-007.json").write_text(
    json.dumps(make_ver(7, 1, stage="blocked_check", failing_step="O1:01_public.sh", parent="closure-006.json")),
    encoding="utf-8",
)
r6 = decide_next(layout, tag)
if r6.get("action") != "hold_owner" or r6.get("command") != "":
    print(f"FAIL: S1-R12.3 (Row 5 confirmed blocked): got {r6}")
    sys.exit(1)

(runs / "verification-007.json").write_text(
    json.dumps(make_ver(7, 0, stage="offline", failing_step=None, parent="closure-006.json")),
    encoding="utf-8",
)
r7 = decide_next(layout, tag)
if r7.get("action") != "done" or r7.get("command") != "":
    print(f"FAIL: S1-R12.3 (Row 6 green verification must be done, not promote): got {r7}")
    sys.exit(1)

(runs / "verification-007.json").write_text(
    json.dumps(make_ver(7, 1, stage="offline", failing_step="G3", parent="closure-006.json")),
    encoding="utf-8",
)
update_state(layout, tag, {"attempts": {"implementer": 1}, "grants": {"implementer": 0}})
r8 = decide_next(layout, tag)
if r8.get("action") != "dispatch" or f"actl dispatch-impl --sprint {tag}" not in r8.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 9 retry dispatch): got {r8}")
    sys.exit(1)

update_state(layout, tag, {"attempts": {"implementer": 2}, "grants": {"implementer": 0}})
r9 = decide_next(layout, tag)
if r9.get("action") != "escalate_attempts" or r9.get("command") != "":
    print(f"FAIL: S1-R12.3 (Row 7 escalate_attempts): got {r9}")
    sys.exit(1)

update_state(layout, tag, {"attempts": {"implementer": 2}, "grants": {"implementer": 1}})
r10 = decide_next(layout, tag)
if r10.get("action") != "dispatch" or f"actl dispatch-impl --sprint {tag}" not in r10.get("command", ""):
    print(f"FAIL: S1-R12.3 (Row 8 granted dispatch): got {r10}")
    sys.exit(1)

update_state(layout, tag, {"status": "hold"})
r11 = decide_next(layout, tag)
if r11.get("action") != "hold_owner" or r11.get("command") != "":
    print(f"FAIL: S1-R12.3 (hold status): got {r11}")
    sys.exit(1)
PY
