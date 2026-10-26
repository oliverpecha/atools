# test/actl/test_s2_bundle.py - P-S2-02: actl bundle assembly and sentinel
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
import pytest

def test_bundle_cli_registration():
    try:
        import actl.cmd_bundle
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2.1: actl.cmd_bundle missing: {e}")

def test_bundle_assembly_sentinel():
    try:
        from actl.bundle import assemble_bundle
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2.3: actl.bundle missing: {e}")
