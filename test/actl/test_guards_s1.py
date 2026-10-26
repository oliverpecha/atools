"""Pytest suite for Stage 1 guards G1-G6 and run_selftests (S1-R3).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest


def test_guards_importable() -> None:
    """S1-R3: check_guards and run_selftests must be exposed."""
    try:
        from actl.verify import check_guards, run_selftests
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R3: actl.verify guards missing: {exc}")


def test_run_selftests_passes_on_unmodified_configs() -> None:
    """S1-R3: run_selftests returns exit_code=0 on valid config files."""
    try:
        from actl.verify import run_selftests
    except ImportError:
        pytest.fail("FAIL: S1-R3: actl.verify missing")

    results = run_selftests()
    assert isinstance(results, list), "FAIL: S1-R3.7: run_selftests must return list"
    assert len(results) > 0, "FAIL: S1-R3.7: run_selftests must return test results"
    for r in results:
        assert r.exit_code == 0, f"FAIL: S1-R3.7: Guard self-test failed: {r.id} ({r.failing_line})"


def test_g4_hollow_test_detection(tmp_path: Path) -> None:
    """S1-R3.4: G4 rejects hollow test bodies like pass, ellipsis, docstring only, assert True."""
    hollow_code =
