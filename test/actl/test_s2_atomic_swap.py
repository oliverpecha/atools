# Authored-by: Gemini 3.1 Pro (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
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

    # Mock rename/replace with resolved-path equality to target outbox
    real_rename = os.rename
    real_replace = os.replace
    def faulty_rename(src, dst):
        if Path(dst).resolve() == Path(outbox).resolve():
            raise OSError("Injected disk failure during atomic rename")
        return real_rename(src, dst)
    def faulty_replace(src, dst):
        if Path(dst).resolve() == Path(outbox).resolve():
            raise OSError("Injected disk failure during atomic replace")
        return real_replace(src, dst)

    monkeypatch.setattr(os, "rename", faulty_rename)
    monkeypatch.setattr(os, "replace", faulty_replace)

    good_resp = GOLDEN_DIR / "responses" / "good_architect_intake.txt"
    with pytest.raises(OSError):
        cli.main(["unpack", "architect-intake", "--sprint", TAG, "-f", str(good_resp), "--json"])

    # Rollback must leave outbox intact with original file
    assert outbox.is_dir()
    assert (outbox / "preserved.txt").is_file()
    assert (outbox / "preserved.txt").read_text(encoding="utf-8") == "prior_valid_state\n"


def test_atomic_swap_spy_path_restriction(tmp_path: Path):
    """Self-test: os.replace spy only triggers on target outbox."""
    outbox = tmp_path / "outbox"
    outbox.mkdir()
    staging = tmp_path / "staging"
    staging.mkdir()
    unrelated_src = tmp_path / "unrelated_src"
    unrelated_src.mkdir()
    unrelated_dst = tmp_path / "unrelated_dst"

    orig_replace = os.replace
    def _spy_replace(src, dst):
        if Path(dst).resolve() == Path(outbox).resolve():
            raise OSError("simulated atomic swap failure")
        return orig_replace(src, dst)

    # Unrelated replace must pass without raising
    _spy_replace(str(unrelated_src), str(unrelated_dst))
    assert unrelated_dst.is_dir()

    # Target outbox replace must raise OSError
    try:
        _spy_replace(str(staging), str(outbox))
        assert False, "Expected OSError on target outbox"
    except OSError:
        pass
