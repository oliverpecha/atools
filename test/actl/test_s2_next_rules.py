# test/actl/test_s2_next_rules.py - P-S2-15: phase 1-2 next rules
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
import pytest

def test_next_rules_phase12_priority_and_decisions():
    try:
        import actl.next_rules.phase12 as p12
        assert getattr(p12, "PRIORITY", None) == 10
    except (ImportError, AssertionError, AttributeError) as e:
        pytest.fail(f"FAIL: S2-R10.1: actl.next_rules.phase12 missing or PRIORITY != 10: {e}")
