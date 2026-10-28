# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

import json
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
    layout = Layout(root)
    for turn_name in ("architect-1", "challenger-1", "architect-2"):
        src_turn = GOLDEN_DIR / "turns" / turn_name
        dst_turn = layout.turns_dir(TAG) / turn_name
        dst_turn.mkdir(parents=True, exist_ok=True)
        for f in ("bundle.json", "bundle.txt"):
            (dst_turn / f).write_bytes((src_turn / f).read_bytes())
    return layout


def test_turn_replay_match_and_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    try:
        from actl import cli
        import actl.cmd_replay  # noqa: F401
        import actl.replay  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R8: actl.replay or actl.cmd_replay missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    assert cli.main(["unpack", "architect-intake", "--sprint", TAG, "-f", str(GOLDEN_DIR / "responses" / "good_architect_intake.txt"), "--json"]) == 0
    assert cli.main(["unpack", "challenger", "--sprint", TAG, "-f", str(GOLDEN_DIR / "responses" / "good_challenger.txt"), "--json"]) == 0
    assert cli.main(["unpack", "architect-review", "--sprint", TAG, "-f", str(GOLDEN_DIR / "responses" / "good_architect_review_lock.txt"), "--json"]) == 0

    outbox_marker = layout.outbox(TAG, "architect") / ".replay_must_not_touch"
    outbox_marker.write_text("untouched", encoding="utf-8")

    for turn_id, args in (
        ("architect-1", ["replay", "architect-1", "--sprint", TAG, "--json"]),
        ("challenger-1", ["replay", "challenger-1", "--sprint", TAG, "--json"]),
        ("architect-2", ["replay", "architect-2", "--json"]),
    ):
        capsys.readouterr()
        rc = cli.main(args)
        cap = capsys.readouterr()
        assert rc == 0, f"Expected replay exit 0 on {turn_id}, got {rc}: {cap.err}"
        doc = json.loads(cap.out)
        assert doc["turn_id"] == turn_id
        assert doc["match"] is True
        assert doc["stored_ok"] is True and doc["replayed_ok"] is True
        assert doc["diffs"] == []

    assert outbox_marker.is_file(), "replay must never modify outbox"

    unpack_path = layout.turns_dir(TAG) / "architect-2" / "unpack.json"
    stored_doc = json.loads(unpack_path.read_text(encoding="utf-8"))
    stored_doc["outputs"][0]["sha256"] = "0" * 64
    unpack_path.write_text(json.dumps(stored_doc, indent=2) + "\n", encoding="utf-8")

    capsys.readouterr()
    rc_diff = cli.main(["replay", "architect-2", "--sprint", TAG, "--json"])
    cap_diff = capsys.readouterr()
    assert rc_diff == 1, f"Expected exit 1 when unpack.json hash differs, got {rc_diff}"
    diff_doc = json.loads(cap_diff.out)
    assert diff_doc["match"] is False
    assert len(diff_doc["diffs"]) >= 1
