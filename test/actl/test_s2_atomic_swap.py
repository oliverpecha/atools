# Authored-by: Flash 3.8 High
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
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
    layout = Layout(root)
    for turn_name in ("architect-1", "challenger-1", "architect-2"):
        src_turn = GOLDEN_DIR / "turns" / turn_name
        dst_turn = layout.turns_dir(TAG) / turn_name
        dst_turn.mkdir(parents=True, exist_ok=True)
        for f in ("bundle.json", "bundle.txt"):
            (dst_turn / f).write_bytes((src_turn / f).read_bytes())
    return layout


def test_outbox_swap_rollback_on_rename_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves F-06: injected rename failure triggers rollback, restoring original outbox byte-for-byte."""
    try:
        from actl import cli
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R4.7: actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    outbox = layout.outbox(TAG, "architect")
    outbox.mkdir(parents=True, exist_ok=True)
    orig_file = outbox / "preserved.txt"
    orig_file.write_text("prior_valid_state\n", encoding="utf-8")

    # Mock os.rename so the staging -> outbox rename raises OSError
    real_rename = os.rename
    def faulty_rename(src, dst):
        if ".architect-staging" in str(src) and str(dst).endswith("outbox"):
            raise OSError("Injected disk failure during atomic rename")
        return real_rename(src, dst)

    monkeypatch.setattr(os, "rename", faulty_rename)

    good_resp = GOLDEN_DIR / "responses" / "good_architect_intake.txt"
    with pytest.raises(OSError):
        cli.main(["unpack", "architect-intake", "--sprint", TAG, "-f", str(good_resp), "--json"])

    # Rollback must leave outbox intact with original file
    assert outbox.is_dir()
    assert (outbox / "preserved.txt").is_file()
    assert (outbox / "preserved.txt").read_text(encoding="utf-8") == "prior_valid_state\n"
