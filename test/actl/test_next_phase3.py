"""Pytest suite for Stage 1 Phase 3 next rules (S1-R12).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest


def test_phase3_rule_discovered_and_priority() -> None:
    """S1-R12.1: src/actl/next_rules/phase3.py exists and exports PRIORITY=30."""
    try:
        import actl.next_rules.phase3 as p3
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R12: actl.next_rules.phase3 missing: {exc}")

    assert getattr(p3, "PRIORITY", None) == 30, "FAIL: S1-R12: PRIORITY must be 30"
    assert hasattr(p3, "evaluate"), "FAIL: S1-R12: evaluate() function missing"


def test_phase3_stage_applicability_entry_guard(tmp_path: Path) -> None:
    """S1-R12.2: Non-implementer stages fall through immediately (returns None)."""
    try:
        from actl.layout import Layout
        import actl.next_rules.phase3 as p3
    except ImportError:
        pytest.fail("FAIL: S1-R12: phase3 module missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"
    state_file = layout.runs(tag) / "state.json"
    state_file.parent.mkdir(parents=True, exist_ok=True)

    for other_stage in ["curator", "oracle", "live", "audit"]:
        state_file.write_text(json.dumps({"active_stage": other_stage, "status": "running"}))
        res = p3.evaluate(layout, tag)
        assert res is None, f"FAIL: S1-R12.2: Stage {other_stage} must return None, got {res}"


def test_phase3_unverified_blocked_closure_enters_verification(tmp_path: Path) -> None:
    """S1-R12.3: Unverified closure with reason='blocked' enters verification first, NOT hold_owner."""
    try:
        from actl.layout import Layout
        import actl.next_rules.phase3 as p3
    except ImportError:
        pytest.fail("FAIL: S1-R12: phase3 module missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"

    outbox = layout.outbox(tag, "implementer")
    outbox.mkdir(parents=True, exist_ok=True)
    (outbox / "closure.json").write_text(json.dumps({
        "schema_version": 1,
        "sprint_tag": tag,
        "attempt_seq": 1,
        "reason": "blocked",
        "notes": "cannot reproduce",
        "backlog": ["issue-1"],
        "blocking_step": "O1:02.sh"
    }))

    res = p3.evaluate(layout, tag)
    assert res is not None, "FAIL: S1-R12.3: Expected rule action for unverified closure"
    assert res.get("action") == "verify", f"FAIL: S1-R12.3: Unverified blocked closure must trigger verify, got: {res.get('action')}"
    assert "--closure" in res.get("command", ""), "FAIL: S1-R12.3: Command must specify --closure"


def test_phase3_verified_blocked_closure_triggers_hold_owner(tmp_path: Path) -> None:
    """S1-R12.3: Verified blocked closure (with confirmed blocking failure) triggers hold_owner."""
    try:
        from actl.layout import Layout
        import actl.next_rules.phase3 as p3
    except ImportError:
        pytest.fail("FAIL: S1-R12: phase3 module missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"

    runs = layout.runs(tag)
    runs.mkdir(parents=True, exist_ok=True)
    (runs / "verification-001.json").write_text(json.dumps({
        "schema_version": 1,
        "id": "verification-001",
        "sprint_tag": tag,
        "seq": 1,
        "parent": "closure-001.json",
        "exit_code": 1,
        "failing_step": "O1:02.sh",
        "blocked_confirmed": True
    }))

    res = p3.evaluate(layout, tag)
    assert res is not None and res.get("action") == "hold_owner", f"FAIL: S1-R12.3: Verified blocked must trigger hold_owner, got: {res}"


def test_phase3_attempt_exhaustion_and_grants(tmp_path: Path) -> None:
    """S1-R12.3: Red verification triggers escalate_attempts on 0 grants, dispatch on >0 grants."""
    try:
        from actl.layout import Layout
        import actl.next_rules.phase3 as p3
    except ImportError:
        pytest.fail("FAIL: S1-R12: phase3 module missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"
    runs = layout.runs(tag)
    runs.mkdir(parents=True, exist_ok=True)
    state_file = runs / "state.json"

    state_file.write_text(json.dumps({
        "active_stage": "implementer",
        "status": "running",
        "attempts": {"implementer": 3},
        "grants": {"implementer": 0}
    }))
    (runs / "verification-001.json").write_text(json.dumps({"exit_code": 1, "seq": 1}))

    res_esc = p3.evaluate(layout, tag)
    assert res_esc is not None and res_esc.get("action") == "escalate_attempts", f"Expected escalate_attempts, got {res_esc}"

    state_file.write_text(json.dumps({
        "active_stage": "implementer",
        "status": "running",
        "attempts": {"implementer": 3},
        "grants": {"implementer": 1}
    }))
    res_disp = p3.evaluate(layout, tag)
    assert res_disp is not None and res_disp.get("action") == "dispatch", f"Expected dispatch, got {res_disp}"

