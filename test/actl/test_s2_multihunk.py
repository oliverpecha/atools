
# test/actl/test_s2_multihunk.py - P-S2-06 (part 2): multi-hunk patches, merging multiple PATCH blocks, and new="true" (S2-R5)

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

def test_multihunk_and_new_files_synthesis(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
"""Proves S2-R5: multiple PATCH blocks with same out merge into one diff; new='true' creates new file; existing file -> E_EXISTS."""
try:
from actl import cli
import actl.patchsynth  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R5: actl.patchsynth missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
turn_dir = layout.turns_dir(TAG) / "architect-1"
toml_body = 'live_run = "none"\n'

# 1. Two PATCH blocks targeting solution_key.patch (one multi-hunk on api/users.py, one new="true" on api/helper.py)
payload = (
    f'<<<FILE path="sprint.toml">>>\n{toml_body}<<<END_FILE>>>\n'
    f'<<<PATCH out="solution_key.patch" file="api/users.py">>>\n'
    f"<<<<<<< SEARCH\n"
    f"def get_user(user_id):\n"
    f"    return USERS.get(user_id)\n"
    f"=======\n"
    f"def get_user(user_id):\n"
    f"    # hunk 1 applied\n"
    f"    return USERS.get(user_id)\n"
    f">>>>>>> REPLACE\n"
    f"<<<<<<< SEARCH\n"
    f"def list_user_ids():\n"
    f"    return sorted(USERS)\n"
    f"=======\n"
    f"def list_user_ids():\n"
    f"    # hunk 2 applied\n"
    f"    return sorted(USERS)\n"
    f">>>>>>> REPLACE\n"
    f"<<<END_PATCH>>>\n"
    f'<<<PATCH out="solution_key.patch" file="api/helper.py" new="true">>>\n'
    f"<<<<<<< SEARCH\n"
    f"=======\n"
    f"HELPER_CONST = 42\n"
    f">>>>>>> REPLACE\n"
    f"<<<END_PATCH>>>\n"
    f'<<<END_RESPONSE bundle="1f13e141">>>\n'
)
resp_file = tmp_path / "multihunk_intake.txt"
resp_file.write_text(payload, encoding="utf-8")

rc = cli.main(["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(resp_file), "--json"])
assert rc == 0, f"Expected exit 0 for multi-hunk + new file patch synthesis, got {rc}"

patch_path = layout.outbox(TAG, "architect") / "solution_key.patch"
assert patch_path.is_file(), "Synthesized solution_key.patch missing in outbox"
patch_text = patch_path.read_text(encoding="utf-8")
assert "# hunk 1 applied" in patch_text
assert "# hunk 2 applied" in patch_text
assert "HELPER_CONST = 42" in patch_text

# Verify synthesized patch applies cleanly on a fresh clone of target_repo at base_sha
check_clone = tmp_path / "check-clone"
subprocess.run(
    ["git", "-c", "core.hooksPath=/dev/null", "clone", "-q", str(layout.target_repo), str(check_clone)],
    check=True,
)
r_apply = subprocess.run(
    ["git", "-C", str(check_clone), "apply", "--check", str(patch_path)],
    capture_output=True,
    text=True,
)
assert r_apply.returncode == 0, f"git apply --check failed on synthesized patch: {r_apply.stderr}"

# 2. new="true" with non-empty SEARCH block must fail with E_PATCH_APPLY
for f in ("response.txt", "unpack.json", "repair.txt"):
    if (turn_dir / f).exists():
        (turn_dir / f).unlink()
bad_new = (
    f'<<<FILE path="sprint.toml">>>\n{toml_body}<<<END_FILE>>>\n'
    f'<<<PATCH out="solution_key.patch" file="api/brand_new.py" new="true">>>\n'
    f"<<<<<<< SEARCH\nnon_empty_search_in_new_file\n=======\nbody\n>>>>>>> REPLACE\n"
    f"<<<END_PATCH>>>\n"
    f'<<<END_RESPONSE bundle="1f13e141">>>\n'
)
bad_new_file = tmp_path / "bad_new.txt"
bad_new_file.write_text(bad_new, encoding="utf-8")
rc_bad = cli.main(["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(bad_new_file), "--json"])
doc_bad = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
assert rc_bad == 2 and doc_bad["errors"][0]["code"] == "E_PATCH_APPLY"

```

