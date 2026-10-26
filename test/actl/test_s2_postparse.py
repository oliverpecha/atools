# test/actl/test_s2_postparse.py - P-S2-09, P-S2-10, P-S2-11: validation
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
import pytest

def test_postparse_schema_and_scope():
    try:
        from actl.validate_outputs import validate_outputs
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R6.1: actl.validate_outputs missing: {e}")

def test_postparse_shell_syntax():
    try:
        from actl.validate_outputs import check_shell_syntax
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R6.3: shell syntax check missing: {e}")

def test_postparse_coverage_bijection():
    try:
        from actl.validate_outputs import check_coverage_bijection
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R6.2: coverage bijection check missing: {e}")
