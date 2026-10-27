
# test/actl/test_s2_patchsynth.py - P-S2-06 (part 1): hermetic patch synthesis 0/1/2 matches, difflib candidate, baselines (S2-R5)

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

from **future** import annotations

import json
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

def test_patch_synthesis_exact_matching_and_difflib_candidate(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-06: 0 matches -> E_SEARCH_NOMATCH + difflib candidate in repair.txt; >=2 matches -> E_SEARCH_MULTI with line numbers; challenger mutant synthesized on base+key."""
try:
from actl import cli
import actl.patchsynth  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R5: actl.patchsynth missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
turn_arch = layout.turns_dir(TAG) / "architect-1"

# 1. 0 matches (near-miss function name in api/users.py) -> E_SEARCH_NOMATCH, repair.txt has nearest candidate "def get_user(user_id):"
rc_no = cli.main(
    [
        "unpack",
        "architect-intake",
        "--sprint",
        TAG,
        "--turn",
        "architect-1",
        "-f",
        str(GOLDEN_DIR / "responses" / "bad_search_nomatch.txt"),
        "--json",
    ]
)
assert rc_no == 2
doc_no = json.loads((turn_arch / "unpack.json").read_text(encoding="utf-8"))
assert doc_no["errors"][0]["code"] == "E_SEARCH_NOMATCH"
repair_no = (turn_arch / "repair.txt").read_text(encoding="utf-8")
assert "E_SEARCH_NOMATCH" in repair_no
assert "get_user_nonexistent_xyz" in repair_no
assert "def get_user(user_id):" in repair_no, (
    f"Repair prompt must contain nearest difflib candidate 'def get_user(user_id):', got:\n{repair_no}"
)

# 2. >=2 matches (bad_search_multi.txt searches for "    return \n" which occurs on lines 19 and 23 of api/users.py)
for f in ("response.txt", "unpack.json", "repair.txt"):
    if (turn_arch / f).exists():
        (turn_arch / f).unlink()
rc_multi = cli.main(
    [
        "unpack",
        "architect-intake",
        "--sprint",
        TAG,
        "--turn",
        "architect-1",
        "-f",
        str(GOLDEN_DIR / "responses" / "bad_search_multi.txt"),
        "--json",
    ]
)
assert rc_multi == 2
doc_multi = json.loads((turn_arch / "unpack.json").read_text(encoding="utf-8"))
assert doc_multi["errors"][0]["code"] == "E_SEARCH_MULTI"
detail_multi = str(doc_multi["errors"][0].get("detail") or "") + doc_multi["errors"][0]["message"]
assert "19" in detail_multi and "23" in detail_multi, (
    f"E_SEARCH_MULTI must report matching line numbers 19 and 23, got: {detail_multi}"
)

# 3. Challenger PATCH block for oracle-draft/mutants/contact_leak.patch synthesized against base_sha + solution_key
turn_chal = layout.turns_dir(TAG) / "challenger-1"
good_chal_text = (GOLDEN_DIR / "responses" / "good_challenger.txt").read_text(encoding="utf-8")
# Replace the FILE block for contact_leak.patch with a PATCH block targeting api/profile.py (which only matches on base+key!)
patch_block = (
    '<<<PATCH out="oracle-draft/mutants/contact_leak.patch" file="api/profile.py">>>\n'
    "<<<<<<< SEARCH\n"
    '        "photo_count": len(user["photos"]),\n'
    "=======\n"
    '        "photo_count": len(user["photos"]),\n'
    '        "contact": user["email"],\n'
    ">>>>>>> REPLACE\n"
    "<<<END_PATCH>>>"
)
import re
chal_with_patch = re.sub(
    r'<<<FILE path="oracle-draft/mutants/contact_leak\.patch">>>.*?<<<END_FILE>>>',
    patch_block,
    good_chal_text,
    flags=re.DOTALL,
)
chal_file = tmp_path / "chal_patchsynth.txt"
chal_file.write_text(chal_with_patch, encoding="utf-8")

rc_chal = cli.main(
    ["unpack", "challenger", "--sprint", TAG, "--turn", "challenger-1", "-f", str(chal_file), "--json"]
)
assert rc_chal == 0, f"Challenger mutant PATCH synthesis on base+key failed: {(turn_chal / 'unpack.json').read_text()}"
synth_mutant = layout.outbox(TAG, "challenger") / "oracle-draft" / "mutants" / "contact_leak.patch"
assert synth_mutant.is_file()
assert '+        "contact": user["email"],' in synth_mutant.read_text(encoding="utf-8")

```

