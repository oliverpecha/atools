"""Pytest suite for Stage 1 session helpers and tripwires (S1-R9, S1-R10, S1-R14, S1-R15).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from test_verify_s1 import REPO_ROOT, TAG, _setup_golden_sandbox


def test_session_module_importable_and_dynamic_timeout(tmp_path: Path) -> None:
    """S1-R9, S1-R14, D-45: actl.session exports required functions and derives dynamic wait timeout (wall_clock + grace + 30s = 2733s)."""
    try:
        import actl.session as sess_mod
        from actl.layout import Layout
        from actl.sprint import load_sprint_toml
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R9: actl.session cannot be imported: {exc}")

    for fn in ("start_session", "wait_session", "archive_session_log", "scan_tripwires"):
        assert callable(getattr(sess_mod, fn, None)), f"FAIL: S1-R9: actl.session lacks {fn}"

    sdir, _wt = _setup_golden_sandbox(tmp_path, None)
    layout = Layout(sdir)
    sprint_cfg = load_sprint_toml(layout, TAG)
    helper = getattr(sess_mod, "compute_wait_timeout", None)
    assert callable(helper), "FAIL: S1A-3: actl.session.compute_wait_timeout is required"
    assert helper(sprint_cfg) == 2733


def test_wait_session_deterministic_polling_and_grace(tmp_path: Path) -> None:
    """S1-R14.1..R14.4: Deterministic unit test of wait_session polling, exit code reading, and disappearance grace."""
    try:
        from actl.session import wait_session
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R14: actl.session missing: {exc}")

    log_dir = tmp_path / "logs"
    sess_dir = tmp_path / "sess"
    log_dir.mkdir()
    sess_dir.mkdir()
    os.environ["ATOOLS_LOG_DIR"] = str(log_dir)
    os.environ["ATOOLS_SESSION_DIR"] = str(sess_dir)

    (log_dir / "impl-unit-001.log").write_bytes(b"hello log\n")

    # Simulate session running on poll 1, then exiting with code 0 on poll 2
    active_seq = [{"impl-unit-001": 100.0}, {}]

    def fake_active():
        return active_seq.pop(0) if active_seq else {}

    with patch("router.process.list_active_tmux_sessions", side_effect=fake_active), patch("shutil.which", return_value="/usr/bin/tmux"):
        # .exit is absent on the first polls and appears after the session disappears
        def fake_read(_name):
            if (sess_dir / "impl-unit-001.exit").is_file():
                return 0
            (sess_dir / "impl-unit-001.exit").write_text("0\n", encoding="utf-8")
            return 0

        with patch("router.process.read_exit_code", side_effect=fake_read):
            res = wait_session("impl-unit-001", timeout_s=5, poll_interval_s=0.05)

    assert res["name"] == "impl-unit-001"
    assert res["exit_code"] == 0
    assert res["hard_cap"] is False
    assert res["lost"] is False
    assert isinstance(res["log_sha256"], str) and len(res["log_sha256"]) == 64


def test_tripwire_scanner_clean_dirty_and_governance(tmp_path: Path) -> None:
    """S1-R10.1..R10.3: scan_tripwires flags oracle/proofs access and respects provenance-safe governance exclusions."""
    try:
        from actl.session import scan_tripwires
        from actl.layout import Layout
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R10: actl.session missing: {exc}")

    sdir, _wt = _setup_golden_sandbox(tmp_path, None)
    layout = Layout(sdir)
    os.environ["ATOOLS_CURSOR_HOME"] = str(tmp_path / "empty_cursor_home")
    (tmp_path / "empty_cursor_home").mkdir()

    # 1. Pure governance reference -> []
    gov_log = tmp_path / "gov.log"
    gov_log.write_text(
        "skills/actl-implementer/SKILL.md\n"
        '{"failing_step": "O1:01_public.sh"}\n',
        encoding="utf-8",
    )
    assert scan_tripwires(layout, TAG, 6, log_path=gov_log) == []

    # 2. Oracle path access -> flagged
    dirty_log = tmp_path / "dirty.log"
    dirty_log.write_text("cat records/target-repo/2026-10-16_public-profiles/oracle-003/proofs/01_public.sh\n", encoding="utf-8")
    hits = scan_tripwires(layout, TAG, 6, log_path=dirty_log)
    assert len(hits) >= 1 and hits[0]["source"] == "log"
