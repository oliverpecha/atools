"""Pytest suite for Stage 1 Phase 3 next rules (S1-R12).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from test_verify_s1 import TAG, _setup_golden_sandbox


def test_phase3_rule_discovered_and_priority() -> None:
    """S1-R12.1: src/actl/next_rules/phase3.py exists and exports PRIORITY=30 and evaluate()."""
    try:
        import actl.next_rules.phase3 as p3
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R12: actl.next_rules.phase3 missing: {exc}")

    assert getattr(p3, "PRIORITY", None) == 30
    assert callable(getattr(p3, "evaluate", None))


def test_phase3_stage_applicability_entry_guard(tmp_path: Path) -> None:
    """S1-R12.2: Non-implementer stages return None on a schema-valid sprint state."""
    try:
        from actl.layout import Layout
        from actl.seq import update_state
        import actl.next_rules.phase3 as p3
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R12: phase3 module missing: {exc}")

    sdir, _wt = _setup_golden_sandbox(tmp_path, None)
    layout = Layout(sdir)

    for other_stage in ("intake", "oracle", "live", "curator", "closeout", None):
        update_state(layout, TAG, {"active_stage": other_stage, "status": "running"})
        assert p3.evaluate(layout, TAG) is None


def test_phase3_unverified_vs_verified_blocked_closure(tmp_path: Path) -> None:
    """S1-R12.3, S1A-10: Unverified blocked closure enters verify first; confirmed blocked_check verification triggers hold_owner."""
    try:
        from actl.layout import Layout
        from actl.next import decide_next
        from actl.seq import update_state
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R12: phase3 module missing: {exc}")

    sdir, _wt = _setup_golden_sandbox(tmp_path, None)
    layout = Layout(sdir)
    update_state(layout, TAG, {"active_stage": "implementer", "status": "running"})

    outbox = layout.outbox(TAG, "implementer")
    outbox.mkdir(parents=True, exist_ok=True)
    closure_path = outbox / "closure.json"
    closure_path.write_text(json.dumps({
        "reason": "blocked",
        "blocking_step": "O1:01_public.sh",
        "notes": ["cannot satisfy R1"],
        "backlog": ["issue-1"],
        "solution_key_divergence": {"requirement_id": "R1", "rationale": "schema locked"},
    }), encoding="utf-8")

    # 1. Unverified blocked closure in outbox -> action == 'verify' with --closure
    res_unverified = decide_next(layout, TAG)
    assert res_unverified["action"] == "verify"
    assert "--closure" in res_unverified["command"]
    from actl.cli import main as cli_main
    import os
    import shlex
    os.environ["ACTL_ROOT"] = str(sdir)
    argv = shlex.split(res_unverified["command"])
    if argv[0] == "actl":
        argv = argv[1:]
    rc = cli_main(argv)
    assert rc != 2, "generated verify-impl --closure <outbox> must not be usage exit 2"

    # 2. After verification confirms blocked_check (stage == 'blocked_check', failing_step != 'G2') -> hold_owner
    closure_path.unlink()
    runs = layout.runs_dir(TAG)
    (runs / "closure-006.json").write_text(json.dumps({
        "kind": "closure",
        "seq": 6,
        "parent": "contract-005.json",
        "reason": "blocked",
        "blocking_step": "O1:01_public.sh",
        "notes": ["cannot satisfy R1"],
        "backlog": ["issue-1"],
        "solution_key_divergence": {"requirement_id": "R1", "rationale": "schema locked"},
    }), encoding="utf-8")
    (runs / "verification-007.json").write_text(json.dumps({
        "kind": "verification",
        "seq": 7,
        "parent": "closure-006.json",
        "id": "verification-007",
        "stage": "blocked_check",
        "oracle": "oracle-003",
        "contract": "contract-005",
        "head": "01d880bc3176cdd8f31d72e67bb3eba54d634378",
        "exit_code": 1,
        "steps": [],
        "failing_step": "O1:01_public.sh",
        "failing_line": "FAIL: public profile",
        "tripwires": [],
        "halt": None,
        "session": None,
    }), encoding="utf-8")

    res_verified = decide_next(layout, TAG)
    assert res_verified["action"] == "hold_owner"
    assert res_verified["command"] == ""


def test_phase3_missing_closure_omits_closure_flag(tmp_path: Path) -> None:
    """S1A-16: finished workspace without outbox closure emits verify-impl without --closure."""
    try:
        from actl.layout import Layout
        from actl.next import decide_next
        from actl.seq import update_state
        from actl.cli import main as cli_main
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R12: phase3 module missing: {exc}")

    sdir, _wt = _setup_golden_sandbox(tmp_path, None)
    layout = Layout(sdir)
    update_state(layout, TAG, {"active_stage": "implementer", "status": "running", "tmux_sessions": []})
    ws = sdir / "sprints" / "target-repo" / TAG / "workspaces" / "implementer-006"
    ws.mkdir(parents=True, exist_ok=True)
    res = decide_next(layout, TAG)
    assert res["action"] == "verify"
    assert "verify-impl" in res["command"]
    assert "--closure" not in res["command"]
    import os
    import shlex
    os.environ["ACTL_ROOT"] = str(sdir)
    argv = shlex.split(res["command"])
    if argv[0] == "actl":
        argv = argv[1:]
    rc = cli_main(argv)
    assert rc != 2, "missing-closure verify-impl must not be usage exit 2"


def test_phase3_attempt_exhaustion_and_grants(tmp_path: Path) -> None:
    """S1-R12.3: Red verification triggers escalate_attempts when attempts >= max_attempts + grants, and dispatch when grants > 0."""
    try:
        from actl.layout import Layout
        from actl.next import decide_next
        from actl.seq import update_state
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R12: phase3 module missing: {exc}")

    sdir, _wt = _setup_golden_sandbox(tmp_path, None)
    layout = Layout(sdir)
    runs = layout.runs_dir(TAG)
    (runs / "verification-007.json").write_text(json.dumps({
        "kind": "verification",
        "seq": 7,
        "parent": "closure-006.json",
        "id": "verification-007",
        "stage": "offline",
        "oracle": "oracle-003",
        "contract": "contract-005",
        "head": "01d880bc3176cdd8f31d72e67bb3eba54d634378",
        "exit_code": 1,
        "steps": [],
        "failing_step": "G3",
        "failing_line": "Scope violation",
        "tripwires": [],
        "halt": None,
        "session": None,
    }), encoding="utf-8")

    update_state(layout, TAG, {"active_stage": "implementer", "status": "running", "attempts": {"implementer": 2}, "grants": {"implementer": 0}})
    assert decide_next(layout, TAG)["action"] == "escalate_attempts"

    update_state(layout, TAG, {"attempts": {"implementer": 2}, "grants": {"implementer": 1}})
    res_disp = decide_next(layout, TAG)
    assert res_disp["action"] == "dispatch"
    assert f"actl dispatch-impl --sprint {TAG}" in res_disp["command"]
