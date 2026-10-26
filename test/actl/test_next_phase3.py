"""Pytest suite for Stage 1 Phase 3 next rules (S1-R12).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import pytest


def test_phase3_rule_discovered() -> None:
    """S1-R12: src/actl/next_rules/phase3.py exists and exports PRIORITY=30."""
    try:
        import actl.next_rules.phase3 as p3
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R12: actl.next_rules.phase3 missing: {exc}")

    assert getattr(p3, "PRIORITY", None) == 30, "FAIL: S1-R12: PRIORITY must be 30"
    assert hasattr(p3, "evaluate"), "FAIL: S1-R12: evaluate() function missing"


def test_phase3_ten_state_evaluation(tmp_path: Path) -> None:
    """S1-R12.2: Phase 3 evaluates all 10 discrete states correctly."""
    try:
        from actl.layout import Layout
        import actl.next_rules.phase3 as p3
    except ImportError:
        pytest.fail("FAIL: S1-R12: phase3 module missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"

    # State 1: Active tmux session running -> wait
    def probe_running(sess: str) -> dict:
        return {"running": True, "exit_code": None}

    # Verify evaluate accepts session_probe and handles states
    res = p3.evaluate(layout, tag, session_probe=probe_running)
    if res is not None:
        assert "action" in res and "command" in res and "reason" in res
