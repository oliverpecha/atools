from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
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
    return Layout(root)


def test_turns_ledger_allocation_and_resolution(tmp_path: Path):
    try:
        from actl.turns import allocate_turn, latest_turn, resolve_turn
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R1.2: actl.turns could not be imported: {e}")

    layout = _setup_sprint(tmp_path)

    assert latest_turn(layout, TAG, "architect") is None
    assert latest_turn(layout, TAG, "challenger") is None
    assert latest_turn(layout, TAG, "curator") is None

    n1, p1 = allocate_turn(layout, TAG, "architect")
    assert n1 == 1 and p1 == layout.turns_dir(TAG) / "architect-1"
    assert p1.is_dir()
    assert stat.S_IMODE(os.lstat(p1).st_mode) == 0o755

    n2, p2 = allocate_turn(layout, TAG, "architect")
    assert n2 == 2 and p2 == layout.turns_dir(TAG) / "architect-2"

    nc1, pc1 = allocate_turn(layout, TAG, "challenger")
    assert nc1 == 1 and pc1 == layout.turns_dir(TAG) / "challenger-1"

    assert latest_turn(layout, TAG, "architect") == (2, p2)
    assert latest_turn(layout, TAG, "challenger") == (1, pc1)
    assert resolve_turn(layout, TAG, "architect-1") == p1
    assert resolve_turn(layout, TAG, "architect-2") == p2
    assert resolve_turn(layout, TAG, "challenger-1") == pc1

    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(lambda _: allocate_turn(layout, TAG, "architect"), range(8)))
    nums = sorted(r[0] for r in results)
    assert nums == list(range(3, 11)), f"Concurrent allocate_turn produced {nums}"

    for bad_role in ("implementer", "invalid", "", "../architect"):
        with pytest.raises(ValueError):
            allocate_turn(layout, TAG, bad_role)
        with pytest.raises(ValueError):
            latest_turn(layout, TAG, bad_role)

    for bad_id in ("architect-0", "architect-01", "implementer-1", "architect", "../architect-1", "architect--1"):
        with pytest.raises(ValueError):
            resolve_turn(layout, TAG, bad_id)

    with pytest.raises(FileNotFoundError):
        resolve_turn(layout, TAG, "architect-99")
