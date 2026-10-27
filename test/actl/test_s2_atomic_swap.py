
# test/actl/test_s2_atomic_swap.py - P-S2-08: atomic outbox swap, mode 0o770, recovery & rollback (S2-R4, D-46, D-S2-10)

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

from **future** import annotations

import json
import os
import stat
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(**file**).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "fixtures" / "golden"
TAG = "2026-10-16_public-profiles"

def _setup_sprint(tmp_path: Path):
from actl.layout import Layout

```
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

```

def test_outbox_staging_mode_and_stale_file_removal(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
"""Proves S2-R4.7 & D-46: outbox swap applies 0o770 to outbox, 0o644/0o755 to files, and removes old turn files."""
try:
from actl import cli
import actl.cmd_unpack  # noqa: F401
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R4.7: actl.unpack or actl.cmd_unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))

outbox = layout.outbox(TAG, "architect")
outbox.mkdir(parents=True, exist_ok=True)
stale_file = outbox / "stale_leftover_from_previous_turn.txt"
stale_file.write_text("must be removed by atomic directory swap\n", encoding="utf-8")

# Also plant a stale .architect-outbox.prev to verify cleanup
prev_dir = layout.mailboxes(TAG) / ".architect-outbox.prev"
prev_dir.mkdir(parents=True, exist_ok=True)
(prev_dir / "old.txt").write_text("old", encoding="utf-8")

good_resp = GOLDEN_DIR / "responses" / "good_architect_intake.txt"
rc = cli.main(["unpack", "architect-intake", "--sprint", TAG, "-f", str(good_resp), "--json"])
assert rc == 0, f"Expected exit 0 on good_architect_intake, got {rc}"

# Verify outbox exists, has mode 0o770, contains expected files, and stale file is gone
assert outbox.is_dir(), "outbox directory missing after swap"
outbox_mode = stat.S_IMODE(os.lstat(outbox).st_mode)
assert outbox_mode == 0o770, f"Expected outbox mode 0o770 (D-46), got {oct(outbox_mode)}"
assert not stale_file.exists(), "Stale file from prior turn leaked into new outbox"
assert not prev_dir.exists(), ".architect-outbox.prev was not cleaned up after swap"
assert not list(layout.mailboxes(TAG).glob(".architect-staging-*")), "Staging directory was not cleaned up"

for fname in ("sprint.toml", "solution_key.patch"):
    fpath = outbox / fname
    assert fpath.is_file(), f"Expected output {fname} missing in outbox"
    fmode = stat.S_IMODE(os.lstat(fpath).st_mode)
    assert fmode == 0o644, f"Expected regular file mode 0o644 on {fname}, got {oct(fmode)}"

```

def test_outbox_untouched_on_failed_unpack_and_interrupted_recovery(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves S2-R4.7 & D-S2-10: failed unpack leaves outbox byte-identical; interrupted .prev is recovered."""
try:
from actl import cli
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R4.7: actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))

outbox = layout.outbox(TAG, "architect")
outbox.mkdir(parents=True, exist_ok=True)
sentinel_file = outbox / "prior_valid.txt"
sentinel_file.write_text("intact_before_bad_unpack\n", encoding="utf-8")

# 1. Run a failing unpack and verify outbox is untouched
bad_resp = GOLDEN_DIR / "responses" / "bad_toml.txt"
rc = cli.main(["unpack", "architect-intake", "--sprint", TAG, "-f", str(bad_resp), "--json"])
assert rc == 2, f"Expected exit 2 on bad_toml, got {rc}"
assert sentinel_file.is_file() and sentinel_file.read_text(encoding="utf-8") == "intact_before_bad_unpack\n"
assert not (outbox / "sprint.toml").exists(), "Failed unpack must not write to outbox"
assert not list(layout.mailboxes(TAG).glob(".architect-staging-*")), "Failed unpack left staging dir behind"

# 2. Simulate an interrupted swap where outbox was moved to .architect-outbox.prev and outbox is missing,
# then a subsequent failed unpack occurs: recovery must restore .prev to outbox
prev_dir = layout.mailboxes(TAG) / ".architect-outbox.prev"
if prev_dir.exists():
    import shutil
    shutil.rmtree(prev_dir)
os.rename(outbox, prev_dir)
assert not outbox.exists() and prev_dir.is_dir()

# Reset turn architect-1 response so unpack runs again
for f in (layout.turns_dir(TAG) / "architect-1").glob("response*"):
    f.unlink()
for f in (layout.turns_dir(TAG) / "architect-1").glob("unpack*"):
    f.unlink()

good_resp = GOLDEN_DIR / "responses" / "good_architect_intake.txt"
rc2 = cli.main(["unpack", "architect-intake", "--sprint", TAG, "-f", str(good_resp), "--json"])
assert rc2 == 0
assert outbox.is_dir() and not prev_dir.exists()
assert (outbox / "sprint.toml").is_file()

```

