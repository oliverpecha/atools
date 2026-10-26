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
    assert hasattr(p3, "evaluate") or hasattr(p3, "match"), "FAIL: S1-R12: evaluate() function missing"
