
# test/actl/test_s2_truncation.py - P-S2-04: truncation property test at 20 seeded random offsets (Seed 79) (S2-R3, D-S2-02)

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

from **future** import annotations

import json
import random
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
for turn_name in ("architect-1", "challenger-1"):
    src_turn = GOLDEN_DIR / "turns" / turn_name
    dst_turn = layout.turns_dir(TAG) / turn_name
    dst_turn.mkdir(parents=True, exist_ok=True)
    for f in ("bundle.json", "bundle.txt"):
        (dst_turn / f).write_bytes((src_turn / f).read_bytes())
return layout

```

def test_truncation_rejection_at_20_seeded_offsets_and_intact_control(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-04 & D-S2-02: intact response succeeds (exit 0), while 20 random truncations (Seed 79) all fail with exit 2 and E_TRUNCATED."""
try:
from actl import cli
import actl.envelope  # noqa: F401
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R3.1: actl.envelope or actl.unpack missing for truncation test: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
turn_dir = layout.turns_dir(TAG) / "architect-1"

full_text = (GOLDEN_DIR / "responses" / "good_architect_intake.txt").read_text(encoding="utf-8")
sentinel_line = '<<<END_RESPONSE bundle="1f13e141">>>\n'
assert full_text.endswith(sentinel_line)

# 1. Positive control: intact response must pass (exit 0, ok=True) — kills always-fail stand-in!
intact_file = tmp_path / "intact.txt"
intact_file.write_text(full_text, encoding="utf-8")
rc_control = cli.main(
    ["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(intact_file), "--json"]
)
assert rc_control == 0, f"Intact control response failed with exit {rc_control}"
control_doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
assert control_doc["ok"] is True

# 2. Property test: 20 distinct random offsets in [1, len(full_text) - 5] with Seed 79
rng = random.Random(79)
max_cut = len(full_text) - 5
offsets = sorted(rng.sample(range(1, max_cut), 20))
assert len(offsets) == 20

for idx, cut in enumerate(offsets):
    for f in ("response.txt", "unpack.json", "repair.txt"):
        if (turn_dir / f).exists():
            (turn_dir / f).unlink()
    truncated = full_text[:cut]
    trunc_file = tmp_path / f"trunc_{idx}_{cut}.txt"
    trunc_file.write_text(truncated, encoding="utf-8")

    rc = cli.main(
        ["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(trunc_file), "--json"]
    )
    assert rc == 2, f"Truncated response at offset {cut} (#{idx}) unexpectedly returned exit {rc}"
    doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
    assert doc["ok"] is False
    assert doc["errors"][0]["code"] == "E_TRUNCATED", (
        f"Truncated response at offset {cut} (#{idx}) returned {doc['errors'][0]['code']} instead of E_TRUNCATED"
    )

```

