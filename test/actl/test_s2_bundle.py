# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "fixtures" / "golden"
TAG = "2026-10-16_public-profiles"


def _setup_sprint(tmp_path: Path):
    from actl.layout import Layout

    root = tmp_path / "actl-root"
    r = subprocess.run(
        ["bash", str(GOLDEN_DIR / "build_golden.sh"), "--install-sprint", str(root), "--tag", TAG],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, f"build_golden.sh failed: {r.stderr}"
    return Layout(root)


def test_p10_bundle_order_limits_and_safety(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    try:
        from actl import cli
        import actl.bundle  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2: actl.bundle missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    # 1. Valid bundle with --include
    capsys.readouterr()
    rc = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--include", "api/users.py", "--json"])
    cap = capsys.readouterr()
    assert rc == 0
    doc = json.loads(cap.out)
    assert doc["turn_id"] == "architect-1"

    # F-03: Real symlink inside target_repo escaping repository
    sym = layout.target_repo / "sym_outside.py"
    if sym.is_symlink() or sym.exists():
        sym.unlink()
    try:
        sym.symlink_to(tmp_path / "outside.txt")
        rc_sym = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--include", "sym_outside.py", "--json"])
        capsys.readouterr()
        assert rc_sym == 2, "bundle --include on escaping symlink must fail with exit 2"
    except OSError as e:
        pytest.fail(f"FAIL: unexpected OSError in test execution: {e}")


def test_bundle_clipboard_helpers_and_osc52(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Proves F-07 & S2-R2.8: --clip invokes clipboard binary; --osc52 with --json keeps stdout pure JSON."""
    try:
        from actl import cli
        import actl.bundle  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2.8: actl.bundle missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    # Mock wl-copy on PATH
    mock_bin = tmp_path / "mock_bin"
    mock_bin.mkdir()
    clip_log = tmp_path / "clip.log"
    (mock_bin / "wl-copy").write_text(f"#!/usr/bin/env bash\ncat > '{clip_log}'\n", encoding="utf-8")
    (mock_bin / "wl-copy").chmod(0o755)
    monkeypatch.setenv("PATH", f"{mock_bin}:{os.environ['PATH']}")

    capsys.readouterr()
    rc_clip = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--clip"])
    assert rc_clip == 0
    assert clip_log.is_file() and len(clip_log.read_text(encoding="utf-8")) > 100

    # Test --osc52 combined with --json
    capsys.readouterr()
    rc_osc = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--osc52", "--json"])
    cap_osc = capsys.readouterr()
    assert rc_osc == 0
    json.loads(cap_osc.out)  # Stdout must be valid JSON
    assert "\x1b]52;c;" in cap_osc.err
