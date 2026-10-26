"""Pytest suite for Stage 1 session handling, dispatch-impl, and tripwires (S1-R8..S1-R10, S1-R14, S1-R15).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_session_module_importable() -> None:
    """S1-R9, S1-R10, S1-R14, S1-R15: actl.session must exist with public functions."""
    try:
        import actl.session as sess_mod
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R9: actl.session cannot be imported: {exc}")

    assert hasattr(sess_mod, "start_session"), "FAIL: S1-R9: actl.session lacks start_session"
    assert hasattr(sess_mod, "wait_session"), "FAIL: S1-R14: actl.session lacks wait_session"
    assert hasattr(sess_mod, "archive_session_log"), "FAIL: S1-R15: actl.session lacks archive_session_log"
    assert hasattr(sess_mod, "scan_tripwires"), "FAIL: S1-R10: actl.session lacks scan_tripwires"


def test_tripwire_scanner_finds_oracle_access(tmp_path: Path) -> None:
    """S1-R10: scan_tripwires detects access to proofs/ or probe.sh in logs and transcripts."""
    try:
        from actl.session import scan_tripwires
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R10: actl modules missing")

    layout = Layout(tmp_path / "root")
    # Tripwires must find violations in dirty fixture files while ignoring clean ones
