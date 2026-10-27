
# test/actl/test_s2_unpack.py - P-S2-01, P-S2-02, P-S2-07, P-S2-08: unpack channels, normalization, --amend, and fixture truth (S2-R4)

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

from **future** import annotations

import hashlib
import io
import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from actl.schemas import load_expected

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

def test_p01_good_architect_intake_unpack_and_proof_preview(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-01: good_architect_intake unpacks; solution_key.patch passes git apply --check and turns golden proofs green."""
try:
from actl import cli
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R4: actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
expected = load_expected(GOLDEN_DIR / "expected.d")["responses"]["good_architect_intake"]

resp_file = GOLDEN_DIR / "responses" / "good_architect_intake.txt"
rc = cli.main(["unpack", "architect-intake", "--sprint", TAG, "-f", str(resp_file), "--json"])
assert rc == 0

outbox = layout.outbox(TAG, "architect")
for rel, want_sha in expected["expect"]["output_hashes"].items():
    got_sha = hashlib.sha256((outbox / rel).read_bytes()).hexdigest()
    assert got_sha == want_sha, f"Hash mismatch for {rel}"

# Verify solution_key.patch applies on base_sha and turns golden proofs green (Q1/Q3 preview)
work = tmp_path / "q1-preview"
subprocess.run(
    ["git", "-c", "core.hooksPath=/dev/null", "clone", "-q", str(layout.target_repo), str(work)],
    check=True,
)
key_patch = outbox / "solution_key.patch"
subprocess.run(["git", "-C", str(work), "apply", "--check", str(key_patch)], check=True)
subprocess.run(["git", "-C", str(work), "apply", str(key_patch)], check=True)

for proof_sh in sorted((GOLDEN_DIR / "sprint" / "oracle" / "proofs").glob("*.sh")):
    r_p = subprocess.run(["bash", str(proof_sh)], cwd=str(work), capture_output=True, text=True)
    assert r_p.returncode == 0, f"Proof {proof_sh.name} failed after applying unpacked solution_key: {r_p.stdout}"

```

def test_p02_good_challenger_unpack_and_mutant_apply(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-02: good_challenger unpacks into oracle-draft/ with exec bits; every mutant applies on base+key."""
try:
from actl import cli
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R4: actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
expected = load_expected(GOLDEN_DIR / "expected.d")["responses"]["good_challenger"]

resp_file = GOLDEN_DIR / "responses" / "good_challenger.txt"
rc = cli.main(["unpack", "challenger", "--sprint", TAG, "-f", str(resp_file), "--json"])
assert rc == 0

outbox = layout.outbox(TAG, "challenger")
for rel, want_sha in expected["expect"]["output_hashes"].items():
    fpath = outbox / rel
    assert fpath.is_file(), f"Missing challenger output {rel}"
    got_sha = hashlib.sha256(fpath.read_bytes()).hexdigest()
    assert got_sha == want_sha, f"Hash mismatch on {rel}"
    if rel.endswith(".sh"):
        assert stat.S_IMODE(os.lstat(fpath).st_mode) == 0o755

# Every unpacked mutant must apply cleanly on base + solution_key
work = tmp_path / "base-plus-key"
subprocess.run(
    ["git", "-c", "core.hooksPath=/dev/null", "clone", "-q", str(layout.target_repo), str(work)],
    check=True,
)
subprocess.run(
    ["git", "-C", str(work), "apply", str(GOLDEN_DIR / "sprint" / "solution_key.patch")],
    check=True,
)
for mpatch in sorted((outbox / "oracle-draft" / "mutants").glob("*.patch")):
    r_m = subprocess.run(
        ["git", "-C", str(work), "apply", "--check", str(mpatch)],
        capture_output=True,
        text=True,
    )
    assert r_m.returncode == 0, f"Mutant {mpatch.name} failed git apply --check on base+key: {r_m.stderr}"

```

def test_p07_normalization_variants_and_channels(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-07 & S2-R4.3: variant_fenced, variant_crlf_bom, --paste channel, and --drawer channel produce exact expected hashes."""
try:
from actl import cli
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R4: actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
expected = load_expected(GOLDEN_DIR / "expected.d")["responses"]

# 1. variant_fenced
rc1 = cli.main(
    ["unpack", "architect-intake", "--sprint", TAG, "-f", str(GOLDEN_DIR / "responses" / "variant_fenced.txt"), "--json"]
)
assert rc1 == 0
for rel, want_sha in expected["variant_fenced"]["expect"]["output_hashes"].items():
    got = hashlib.sha256((layout.outbox(TAG, "architect") / rel).read_bytes()).hexdigest()
    assert got == want_sha

# 2. variant_crlf_bom via --drawer mode (verifies drawer cleanup after success)
drawer = tmp_path / "courier_drawer"
drawer.mkdir()
(drawer / "bundle.txt").write_bytes((GOLDEN_DIR / "turns" / "architect-2" / "bundle.txt").read_bytes())
raw_crlf_bom = (GOLDEN_DIR / "responses" / "variant_crlf_bom.txt").read_bytes()
(drawer / "response.txt").write_bytes(raw_crlf_bom)

rc2 = cli.main(
    ["unpack", "architect-review", "--sprint", TAG, "--turn", "architect-2", "--drawer", str(drawer), "--json"]
)
assert rc2 == 0
# Raw response.txt in ledger must preserve exact CRLF+BOM bytes, while unpacked output has normalized LF hashes
assert (layout.turns_dir(TAG) / "architect-2" / "response.txt").read_bytes() == raw_crlf_bom
for rel, want_sha in expected["variant_crlf_bom"]["expect"]["output_hashes"].items():
    got = hashlib.sha256((layout.outbox(TAG, "architect") / rel).read_bytes()).hexdigest()
    assert got == want_sha
assert not drawer.exists(), "Successful --drawer unpack must remove the empty drawer directory"

# 3. --paste channel stops at top-level sentinel without reading trailing EOF noise
for f in ("response.txt", "unpack.json"):
    (layout.turns_dir(TAG) / "architect-2" / f).unlink()
paste_stream = (
    (GOLDEN_DIR / "responses" / "good_architect_review_revise.txt").read_text(encoding="utf-8")
    + "TRAILING_UNREAD_LINE_AFTER_SENTINEL\n"
)
monkeypatch.setattr(sys, "stdin", io.StringIO(paste_stream))
rc3 = cli.main(["unpack", "architect-review", "--sprint", TAG, "--turn", "architect-2", "--paste", "--json"])
assert rc3 == 0
for rel, want_sha in expected["good_architect_review_revise"]["expect"]["output_hashes"].items():
    got = hashlib.sha256((layout.outbox(TAG, "architect") / rel).read_bytes()).hexdigest()
    assert got == want_sha

```

def test_p08_amend_fold_replaces_only_named_blocks(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-08 (S2-R4.8): initial bad_missing_required response followed by --amend supplying sprint.toml validates the union and writes amend-1.txt."""
try:
from actl import cli
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R4.8: actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
turn_dir = layout.turns_dir(TAG) / "architect-1"
expected = load_expected(GOLDEN_DIR / "expected.d")["responses"]["good_architect_intake"]

# Step 1: unpack bad_missing_required.txt (has solution_key.patch, missing sprint.toml) -> fails with exit 2
bad_req = GOLDEN_DIR / "responses" / "bad_missing_required.txt"
rc1 = cli.main(["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(bad_req), "--json"])
assert rc1 == 2
assert (turn_dir / "response.txt").is_file()
assert (turn_dir / "repair.txt").is_file()

# Step 2: --amend with only the missing sprint.toml block + sentinel -> union validates and succeeds!
sprint_toml_block = (
    '<<<FILE path="sprint.toml">>>\n'
    'live_run = "none"\n'
    'approval_live_run = "architect"\n'
    'solution_key_exposure = "full"\n'
    'min_attempts_before_block = 2\n'
    'max_epochs = 3\n\n'
    '[max_attempts]\n'
    'oracle = 3\n'
    'implementer = 2\n'
    'live = 2\n'
    'curator = 2\n\n'
    '[hard_cap.implementer]\n'
    'wall_clock = "45m"\n'
    'turns = 60\n'
    '<<<END_FILE>>>\n'
    '<<<END_RESPONSE bundle="1f13e141">>>\n'
)
amend_file = tmp_path / "amend_toml.txt"
amend_file.write_text(sprint_toml_block, encoding="utf-8")

rc2 = cli.main(
    ["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "--amend", "-f", str(amend_file), "--json"]
)
assert rc2 == 0, f"Expected --amend union to succeed with exit 0, got {rc2}"
assert (turn_dir / "amend-1.txt").read_text(encoding="utf-8") == sprint_toml_block
unpack_doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
assert unpack_doc["ok"] is True
assert unpack_doc["amended"] is True

for rel, want_sha in expected["expect"]["output_hashes"].items():
    got = hashlib.sha256((layout.outbox(TAG, "architect") / rel).read_bytes()).hexdigest()
    assert got == want_sha

```

