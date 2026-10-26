"""Pytest suite for Stage 1 verifier engine (S1-R1, S1-R2, S1-R4..S1-R7, S1-R11, S1-R13).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest


def test_verify_module_and_schema_reexport() -> None:
    """S1-R1.1: actl.verify must exist, export verify_impl, run_o1, run_o2, and re-export StepResult."""
    try:
        import actl.verify as verify_mod
        from actl.schemas import StepResult as OriginalStepResult
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R1.1: actl.verify cannot be imported: {exc}")

    assert hasattr(verify_mod, "StepResult"), "FAIL: S1-R1.1: actl.verify lacks StepResult"
    assert verify_mod.StepResult is OriginalStepResult, "FAIL: S1-R1.1: StepResult must be re-exported from schemas"
    assert hasattr(verify_mod, "verify_impl"), "FAIL: S1-R1.3: verify_impl missing"
    assert hasattr(verify_mod, "run_o1"), "FAIL: S1-R5: run_o1 missing"
    assert hasattr(verify_mod, "run_o2"), "FAIL: S1-R6: run_o2 missing"


def test_stepresult_field_defaults_and_conversion() -> None:
    """S1-R1.1, S1-R1.2: StepResult field defaults and conversion to 4-key dict."""
    try:
        from actl.verify import StepResult
    except ImportError:
        pytest.fail("FAIL: S1-R1: actl.verify missing")

    sr = StepResult(id="G1", cmd="manifest_check", exit_code=0, output_sha256="a" * 64)
    assert sr.output_tail == "", "FAIL: S1-R1.1: default output_tail must be empty string"
    assert sr.duration_ms == 0, "FAIL: S1-R1.1: default duration_ms must be 0"
    assert sr.failing_line is None, "FAIL: S1-R1.1: default failing_line must be None"

    d = sr.to_verification_step()
    assert d == {
        "id": "G1",
        "cmd": "manifest_check",
        "exit_code": 0,
        "output_sha256": "a" * 64,
    }, f"FAIL: S1-R1.2: to_verification_step() must have strictly 4 keys: {d}"


def test_verification_parent_and_stamping_linkage(tmp_path: Path) -> None:
    """S1-R1.4, S1-R7.2: verify_impl stamps closure with matching seq and links verification.parent."""
    try:
        from actl.verify import verify_impl
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R1.4: actl.verify missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"
    closure_file = tmp_path / "closure.json"
    closure_file.write_text(json.dumps({
        "schema_version": 1,
        "sprint_tag": tag,
        "attempt_seq": 1,
        "reason": "completed",
        "notes": "all tests pass",
        "backlog": []
    }))

    res = verify_impl(layout, tag, closure_path=closure_file)
    assert res.get("parent") == "closure-001.json", f"FAIL: S1-R1.4: verification.parent mismatch: {res.get('parent')}"
    stamped_closure = layout.runs(tag) / "closure-001.json"
    assert stamped_closure.exists(), "FAIL: S1-R7.2: Stamped closure was not written to runs/"


def test_no_closure_verification_behavior(tmp_path: Path) -> None:
    """S1-R1.4: verify_impl without closure sets parent=null and neutral G2 step."""
    try:
        from actl.verify import verify_impl
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R1.4: actl.verify missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"

    res = verify_impl(layout, tag, closure_path=None)
    assert res.get("parent") is None, "FAIL: S1-R1.4: Expected parent=null when no closure provided"
    g2 = next((s for s in res.get("steps", []) if s.get("id") == "G2"), None)
    assert g2 is not None and g2.get("exit_code") == 0, "FAIL: S1-R1.4: G2 must record neutral pass on missing closure"


def test_halt_precedence_over_session_flags(tmp_path: Path) -> None:
    """S1-R2.2, S1-R2.4: G1 tamper or self-test halt takes precedence over session_info hard_cap/lost."""
    try:
        from actl.verify import verify_impl
        from actl.layout import Layout
    except ImportError:
        pytest.fail("FAIL: S1-R2.2: actl.verify missing")

    layout = Layout(tmp_path / "root")
    tag = "2026-10-16_test"

    res = verify_impl(layout, tag, session_info={"hard_cap": True, "lost": False})
    assert res.get("exit_code") is None, "FAIL: S1-R2.2: Halt must set verification.exit_code = null"
    assert res.get("halt") is not None, "FAIL: S1-R2.2: Halt block must be present in verification record"


def test_failing_line_sanitization_rules() -> None:
    """S1-R1.7: failing_line strips ANSI escape sequences, control chars < 0x20, and truncates to 300 chars."""
    try:
        from actl.verify import sanitize_failing_line
    except ImportError:
        pytest.fail("FAIL: S1-R1.7: sanitize_failing_line function missing in actl.verify")

    esc = chr(27)
    tab = chr(9)
    nl = chr(10)
    raw_line = esc + "[31;1mError:" + esc + "[0m Failed at " + tab + " line " + nl + ("x" * 350)
    cleaned = sanitize_failing_line(raw_line)
    assert esc not in cleaned, "FAIL: S1-R1.7: ANSI escape sequence leaked"
    assert nl not in cleaned and tab not in cleaned, "FAIL: S1-R1.7: Control characters not replaced with spaces"
    assert len(cleaned) <= 300, f"FAIL: S1-R1.7: Line length {len(cleaned)} exceeds 300 code points"


def test_o2_command_grammar_validation(tmp_path: Path) -> None:
    """S1-R6.3: run_o2 strictly requires pytest or python3 -m pytest."""
    try:
        from actl.verify import run_o2
    except ImportError:
        pytest.fail("FAIL: S1-R6: actl.verify missing")

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    for disallowed in ["bash run.sh", "python3 test.py", "pytest; echo evil", "cat /etc/passwd"]:
        with pytest.raises((ValueError, Exception)):
            run_o2(worktree, repo_test_cmd=disallowed)

