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

    for fn in ("start_session", "wait_session", "archive_session_log", "scan_tripwires"):
        assert hasattr(sess_mod, fn), f"FAIL: S1-R9: actl.session lacks {fn}"


def test_tripwire_scanner_finds_oracle_access(tmp_path: Path) -> None:
    """S1-R10: scan_tripwires detects access to proofs/ or probe.sh in logs and transcripts."""
    try:
        from actl.session import scan_tripwires
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R10: actl modules missing")

    layout = Layout(tmp_path / "root")
    dirty_log = tmp_path / "dirty.log"
    dirty_log.write_text("Checking /records/oracle-003/proofs/01.sh for answers\n")

    hits = scan_tripwires(layout, "2026-10-16_test", 1, log_path=dirty_log)
    assert isinstance(hits, list), "FAIL: S1-R10: scan_tripwires must return a list"
    assert len(hits) > 0, "FAIL: S1-R10: Expected tripwire match on proofs/ reference"
    assert hits[0]["source"] == "log", "FAIL: S1-R10: Expected source='log'"


def test_tripwire_scanner_ignores_governance_inputs(tmp_path: Path) -> None:
    """S1-R10.2: scan_tripwires excludes SKILL.md, contract, and prior_attempt tokens."""
    try:
        from actl.session import scan_tripwires
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R10: actl modules missing")

    layout = Layout(tmp_path / "root")
    clean_log = tmp_path / "clean.log"
    clean_log.write_text("Instruction from skills/actl-implementer/SKILL.md executed\nO1:01_public.sh in prior_attempt\n")

    hits = scan_tripwires(layout, "2026-10-16_test", 1, log_path=clean_log)
    assert hits == [], f"FAIL: S1-R10.2: Governance tokens must not trigger tripwire: {hits}"
