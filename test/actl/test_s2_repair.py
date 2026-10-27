from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

from actl.schemas import load_expected

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


def test_p13_non_execution_canary_across_unpack_replay_promote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """Proves F-04 & S2-R12.1: non-execution canary passes through unpack, replay, and promote without executing."""
    try:
        from actl import cli
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R12.1: actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    pwn_unpack = tmp_path / "pwn_unpack"
    pwn_replay = tmp_path / "pwn_replay"
    pwn_promote = tmp_path / "pwn_promote"

    good_chal = (GOLDEN_DIR / "responses" / "good_challenger.txt").read_text(encoding="utf-8")
    injected = good_chal.replace(
        'echo "OK: probe"',
        f'touch "{pwn_unpack}" "{pwn_replay}" "{pwn_promote}"\necho "OK: probe"',
    )
    inj_file = tmp_path / "inj.txt"
    inj_file.write_text(injected, encoding="utf-8")

    # 1. Unpack
    rc1 = cli.main(["unpack", "challenger", "--sprint", TAG, "--turn", "challenger-1", "-f", str(inj_file), "--json"])
    assert rc1 == 0
    assert not pwn_unpack.exists(), "SECURITY VIOLATION: unpack executed shell code!"

    # 2. Replay
    rc2 = cli.main(["replay", "challenger-1", "--sprint", TAG, "--json"])
    assert rc2 == 0
    assert not pwn_replay.exists(), "SECURITY VIOLATION: replay executed shell code!"

    # 3. Promote
    rc3 = cli.main(["promote", "challenger", "--sprint", TAG, "--json"])
    assert rc3 == 0
    assert not pwn_promote.exists(), "SECURITY VIOLATION: promote executed shell code!"
