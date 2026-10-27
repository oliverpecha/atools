
# test/actl/test_s2_repair.py - P-S2-13: repair prompt synthesis, zero oracle leak, and non-execution canary (S2-R7, S2-R12)

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

from **future** import annotations

import json
import subprocess
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

def test_repair_prompt_all_bad_responses_and_zero_oracle_leak(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves S2-R7 & D-S2-05: repair.txt for every bad_* response contains error code, path, sentinel, and never leaks hidden oracle secrets."""
try:
from actl import cli
import actl.repair  # noqa: F401
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R7: actl.repair or actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))

# Plant a secret canary inside records/.../oracle-003/ that must NEVER appear in any repair.txt
secret_canary = "TOP_SECRET_ORACLE_CANARY_99887766"
(layout.sprint_dir(TAG) / "oracle-003" / "secret_note.txt").write_text(secret_canary, encoding="utf-8")

expected = load_expected(GOLDEN_DIR / "expected.d")["responses"]
for case_name, meta in sorted(expected.items()):
    if not case_name.startswith("bad_"):
        continue
    purpose = meta["purpose"]
    turn_id = meta["turn"]
    want_code = meta["expect"]["error_code"]
    turn_dir = layout.turns_dir(TAG) / turn_id
    for f in ("response.txt", "unpack.json", "repair.txt"):
        if (turn_dir / f).exists():
            (turn_dir / f).unlink()

    resp_path = GOLDEN_DIR / "responses" / f"{case_name}.txt"
    rc = cli.main(["unpack", purpose, "--sprint", TAG, "--turn", turn_id, "-f", str(resp_path), "--json"])
    assert rc == 2

    repair_file = turn_dir / "repair.txt"
    assert repair_file.is_file(), f"Case {case_name}: repair.txt not created"
    repair_text = repair_file.read_text(encoding="utf-8")
    bundle_meta = json.loads((turn_dir / "bundle.json").read_text(encoding="utf-8"))
    prefix8 = bundle_meta["bundle_sha256"][:8]

    assert want_code in repair_text, f"Case {case_name}: repair.txt missing error code {want_code}"
    assert f'<<<END_RESPONSE bundle="{prefix8}">>>' in repair_text, (
        f"Case {case_name}: repair.txt missing closing sentinel reminder"
    )
    assert secret_canary not in repair_text, f"Case {case_name}: repair.txt leaked hidden oracle content!"

```

def test_p13_unpack_never_executes_model_content_canary(
tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-13 (S2-R12.1): a $(touch ) payload in proof scripts, filenames, or patches is NEVER executed."""
try:
from actl import cli
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R12.1: actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
pwned_file = tmp_path / "pwned_canary_file"

good_chal = (GOLDEN_DIR / "responses" / "good_challenger.txt").read_text(encoding="utf-8")
injected = good_chal.replace(
    'echo "OK: probe"',
    f'touch "{pwned_file}"\n$(touch "{pwned_file}")\n`touch "{pwned_file}"`\necho "OK: probe"',
)
injected_file = tmp_path / "injected_chal.txt"
injected_file.write_text(injected, encoding="utf-8")

rc = cli.main(
    ["unpack", "challenger", "--sprint", TAG, "--turn", "challenger-1", "-f", str(injected_file), "--json"]
)
assert rc == 0
assert not pwned_file.exists(), "SECURITY VIOLATION: unpack executed shell commands from model response!"

```

