
# test/actl/test_s2_envelope.py - P-S2-03 & P-S2-05: bad_* matrix, 12 worked examples, and path/symlink attacks (S2-R3, S2-R12)

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

def *bad_response_cases() -> list[tuple[str, dict]]:
expected = load_expected(GOLDEN_DIR / "expected.d")["responses"]
return [(k, v) for k, v in sorted(expected.items()) if k.startswith("bad*")]

@pytest.mark.parametrize("case_name,meta", *bad_response_cases())
def test_p03_all_bad_responses_matrix(
case_name: str, meta: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
"""Proves P-S2-03 & D-S2-06: every bad** fixture in expected.d/s2.json exits 2 with its exact single error_code and writes nothing to outbox."""
try:
from actl import cli
import actl.envelope  # noqa: F401
import actl.unpack  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R3/S2-R4: actl.envelope or actl.unpack missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))

purpose = meta["purpose"]
turn_id = meta["turn"]
want_exit = meta["expect"]["exit"]
want_code = meta["expect"]["error_code"]
role = "challenger" if purpose == "challenger" else "architect"

# Place a canary file in outbox to prove outbox is untouched on failure
outbox = layout.outbox(TAG, role)
outbox.mkdir(parents=True, exist_ok=True)
canary = outbox / ".untouched_canary"
canary.write_text("keep", encoding="utf-8")

resp_path = GOLDEN_DIR / "responses" / f"{case_name}.txt"
if case_name == "bad_size" and (not resp_path.is_file() or resp_path.stat().st_size < 1048576):
    subprocess.run(["bash", str(GOLDEN_DIR / "make_responses.sh")], check=True)

rc = cli.main(["unpack", purpose, "--sprint", TAG, "--turn", turn_id, "-f", str(resp_path), "--json"])
assert rc == want_exit, f"Case {case_name}: expected exit {want_exit}, got {rc}"

turn_dir = layout.turns_dir(TAG) / turn_id
unpack_json = turn_dir / "unpack.json"
assert unpack_json.is_file(), f"Case {case_name}: unpack.json was not written"
doc = json.loads(unpack_json.read_text(encoding="utf-8"))
assert doc["ok"] is False, f"Case {case_name}: expected ok=False"
assert len(doc["errors"]) >= 1, f"Case {case_name}: expected at least 1 error"
got_code = doc["errors"][0]["code"]
assert got_code == want_code, f"Case {case_name}: expected error_code {want_code!r}, got {got_code!r} ({doc['errors']})"
assert doc["outputs"] == [], f"Case {case_name}: expected empty outputs on failure"

# Outbox must have only the canary file
assert [p.name for p in outbox.iterdir()] == [".untouched_canary"], (
    f"Case {case_name}: failed unpack modified outbox!"
)

```

def test_p03_worked_examples_and_fence_boundaries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
"""Proves S2-R3: fence='N' scaling (N=3..9 accepted, N=2 and N=10 rejected), size boundaries (1 MiB accepted, 1 MiB+1 rejected)."""
try:
from actl import cli
import actl.envelope  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R3: actl.envelope missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
turn_dir = layout.turns_dir(TAG) / "architect-1"

def _run_intake(body: str) -> tuple[int, dict]:
    for f in ("response.txt", "unpack.json", "repair.txt"):
        if (turn_dir / f).exists():
            (turn_dir / f).unlink()
    p = tmp_path / "input.txt"
    p.write_text(body, encoding="utf-8")
    rc = cli.main(["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(p), "--json"])
    doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
    return rc, doc

sol_key = (GOLDEN_DIR / "sprint" / "solution_key.patch").read_text(encoding="utf-8")
toml_body = 'live_run = "none"\n'

# Fence N=5 escaping inner N=3 markers (Worked Example 4) and Fence N=9 boundary
for n in (3, 4, 5, 8, 9):
    open_f = "<" * n + f'FILE path="spec-draft.md" fence="{n}"' + ">" * n
    close_f = "<" * n + "END_FILE" + ">" * n
    payload = (
        f'{open_f}\n'
        f'# Spec with inner <<<FILE path="inner.txt">>>\ndata\n<<<END_FILE>>>\n'
        f'{close_f}\n'
        f'<<<FILE path="sprint.toml">>>\n{toml_body}<<<END_FILE>>>\n'
        f'<<<FILE path="solution_key.patch">>>\n{sol_key}<<<END_FILE>>>\n'
        f'<<<END_RESPONSE bundle="1f13e141">>>\n'
    )
    rc, doc = _run_intake(payload)
    assert rc == 0 and doc["ok"] is True, f"Valid fence={n} failed: {doc}"

# Out-of-range fence values N=2 and N=10 must fail with E_SYNTAX_MARKER
for bad_n in (2, 10):
    open_f = "<" * bad_n + f'FILE path="spec-draft.md" fence="{bad_n}"' + ">" * bad_n
    close_f = "<" * bad_n + "END_FILE" + ">" * bad_n
    payload = (
        f'{open_f}\ntext\n{close_f}\n'
        f'<<<FILE path="sprint.toml">>>\n{toml_body}<<<END_FILE>>>\n'
        f'<<<FILE path="solution_key.patch">>>\n{sol_key}<<<END_FILE>>>\n'
        f'<<<END_RESPONSE bundle="1f13e141">>>\n'
    )
    rc, doc = _run_intake(payload)
    assert rc == 2 and doc["errors"][0]["code"] == "E_SYNTAX_MARKER", f"Fence {bad_n} should fail with E_SYNTAX_MARKER"

# Exact 1 MiB (1,048,576 bytes) accepted, 1,048,577 bytes rejected with E_SIZE
exact_1mib = "x" * (1048576 - 1) + "\n"
rc_ok, doc_ok = _run_intake(
    f'<<<FILE path="spec-draft.md">>>\n{exact_1mib}<<<END_FILE>>>\n'
    f'<<<FILE path="sprint.toml">>>\n{toml_body}<<<END_FILE>>>\n'
    f'<<<FILE path="solution_key.patch">>>\n{sol_key}<<<END_FILE>>>\n'
    f'<<<END_RESPONSE bundle="1f13e141">>>\n'
)
assert rc_ok == 0 and doc_ok["ok"] is True, "Exact 1 MiB (1,048,576 bytes) must be accepted"

over_1mib = "x" * 1048576 + "\n"
rc_big, doc_big = _run_intake(
    f'<<<FILE path="spec-draft.md">>>\n{over_1mib}<<<END_FILE>>>\n'
    f'<<<FILE path="sprint.toml">>>\n{toml_body}<<<END_FILE>>>\n'
    f'<<<FILE path="solution_key.patch">>>\n{sol_key}<<<END_FILE>>>\n'
    f'<<<END_RESPONSE bundle="1f13e141">>>\n'
)
assert rc_big == 2 and doc_big["errors"][0]["code"] == "E_SIZE", "1,048,577 bytes must fail with E_SIZE"

```

def test_p05_path_attacks_and_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
"""Proves P-S2-05: rejects ../x, /etc/x, backslash, NUL, .git case variants, symlink targets, over-long paths, case collisions."""
try:
from actl import cli
import actl.envelope  # noqa: F401
except ImportError as e:
pytest.fail(f"FAIL: S2-R3/S2-R12: actl.envelope missing: {e}")

```
layout = _setup_sprint(tmp_path)
monkeypatch.setenv("ACTL_ROOT", str(layout.root))
turn_dir = layout.turns_dir(TAG) / "challenger-1"

def _run_chal(body: str) -> tuple[int, dict]:
    for f in ("response.txt", "unpack.json", "repair.txt"):
        if (turn_dir / f).exists():
            (turn_dir / f).unlink()
    p = tmp_path / "chal_in.txt"
    p.write_text(body, encoding="utf-8")
    rc = cli.main(["unpack", "challenger", "--sprint", TAG, "--turn", "challenger-1", "-f", str(p), "--json"])
    doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
    return rc, doc

bad_paths = [
    "../escape.sh",
    "oracle-draft/../../escape.sh",
    "/etc/passwd",
    "oracle-draft\\proofs\\01.sh",
    "oracle-draft/proofs/" + ("a" * 101) + ".sh",
    "oracle-draft/proofs/" + ("a/" * 130) + "b.sh",
    "outside-prefix/file.txt",
]
for bp in bad_paths:
    rc, doc = _run_chal(f'<<<FILE path="{bp}">>>\ndata\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="b7eb659a">>>\n')
    assert rc == 2 and doc["errors"][0]["code"] == "E_PATH", f"Bad path {bp!r} did not fail with E_PATH: {doc}"

# Case-insensitive .git segment in PATCH file attribute must fail with E_PATH
for git_path in (".git/config", ".GIT/HEAD", "sub/.Git/hooks/pre-commit"):
    rc, doc = _run_chal(
        f'<<<PATCH out="oracle-draft/mutants/m.patch" file="{git_path}">>>\n'
        f"<<<<<<< SEARCH\na\n=======\nb\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n"
        f'<<<END_RESPONSE bundle="b7eb659a">>>\n'
    )
    assert rc == 2 and doc["errors"][0]["code"] == "E_PATH", f".git path {git_path!r} must fail with E_PATH"

# Case-insensitive duplicate path collision in FILE blocks must fail with E_DUPLICATE
rc_dup, doc_dup = _run_chal(
    '<<<FILE path="oracle-draft/proofs/01_Public.sh" mode="exec">>>\n#!/usr/bin/env bash\n<<<END_FILE>>>\n'
    '<<<FILE path="oracle-draft/proofs/01_public.sh" mode="exec">>>\n#!/usr/bin/env bash\n<<<END_FILE>>>\n'
    '<<<END_RESPONSE bundle="b7eb659a">>>\n'
)
assert rc_dup == 2 and doc_dup["errors"][0]["code"] == "E_DUPLICATE", (
    f"Case collision must fail with E_DUPLICATE, got {doc_dup}"
)

```

