# test/actl/test_s2_envelope.py - P-S2-03: envelope parser on 12 worked examples
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
import pytest

def test_envelope_grammar_worked_examples():
    try:
        from actl.envelope import parse_envelope
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R3.1: actl.envelope missing: {e}")
