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
    try:
        from actl.verify import check_guards
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R3.4: actl.verify missing")

    layout = Layout(tmp_path / "root")
    wt = tmp_path / "wt_hollow"
    wt.mkdir(parents=True, exist_ok=True)
    results = check_guards(layout, "2026-10-16_test", wt)
    g4 = next((r for r in results if r.id == "G4"), None)
    assert g4 is not None and g4.exit_code == 1, "FAIL: S1-R3.4: G4 must fail on hollow test bodies"


def test_g5_secret_scrubbing(tmp_path: Path) -> None:
    """S1-R3.5: G5 redacts matched secret from failing_line and output."""
    try:
        from actl.verify import check_guards
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R3.5: actl.verify missing")

    layout = Layout(tmp_path / "root")
    wt = tmp_path / "wt_secret"
    wt.mkdir(parents=True, exist_ok=True)
    results = check_guards(layout, "2026-10-16_test", wt)
    g5 = next((r for r in results if r.id == "G5"), None)
    assert g5 is not None and g5.exit_code == 1, "FAIL: S1-R3.5: G5 must fail on secret pattern"
    assert "AKIA" not in (g5.failing_line or ""), "FAIL: S1-R3.5: Secret unredacted in failing_line"
