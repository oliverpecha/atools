# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

import json
from pathlib import Path
import re
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


def _bad_response_cases() -> list[tuple[str, dict]]:
    expected = load_expected(GOLDEN_DIR / "expected.d")["responses"]
    return [(k, v) for k, v in sorted(expected.items()) if k.startswith("bad_")]


@pytest.mark.parametrize("case_name,meta", _bad_response_cases())
def test_p03_all_bad_responses_matrix(
    case_name: str, meta: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    try:
        from actl import cli
        import actl.envelope  # noqa: F401
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R3/S2-R4: actl.envelope or actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    purpose = meta["purpose"]
    turn_id = meta["turn"]
    want_exit = meta["expect"]["exit"]
    want_code = meta["expect"]["error_code"]
    role = "challenger" if purpose == "challenger" else "architect"

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
    assert doc["ok"] is False
    assert len(doc["errors"]) >= 1
    got_code = doc["errors"][0]["code"]
    assert got_code == want_code, f"Case {case_name}: expected {want_code!r}, got {got_code!r}"
    assert doc["outputs"] == []
    assert [p.name for p in outbox.iterdir()] == [".untouched_canary"]


def test_p03_compound_error_precedence_full_pipeline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves R4-05 & S2-R4.6: compound fault precedence across framing, bundle, path, dup, size, patch, and schema."""
    try:
        from actl import cli
        import actl.envelope  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R4.6: actl.envelope missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    turn_dir = layout.turns_dir(TAG) / "architect-1"

    def _eval(payload: str) -> str:
        for f in ("response.txt", "unpack.json", "repair.txt"):
            if (turn_dir / f).exists():
                (turn_dir / f).unlink()
        p = tmp_path / "comp.txt"
        p.write_text(payload, encoding="utf-8")
        cli.main(["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(p), "--json"])
        doc = json.loads((turn_dir / "unpack.json").read_text(encoding="utf-8"))
        return doc["errors"][0]["code"]

    # 1. Framing (E_SYNTAX_MARKER) beats valid 8-hex bundle mismatch (E_BUNDLE_MISMATCH) and E_PATH
    code1 = _eval('<<<FILE path="../escape.txt">>>\ndata\n<<<END_FILE>>>\n<<<END_RESPONSE bundle=wrong>>>\n')
    assert code1 == "E_SYNTAX_MARKER"

    # 2. Valid 8-hex bundle mismatch beats E_PATH
    code2 = _eval('<<<FILE path="../escape.txt">>>\ndata\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="00000000">>>\n')
    assert code2 == "E_BUNDLE_MISMATCH"

    # 3. E_PATH beats E_DUPLICATE
    code3 = _eval(
        '<<<FILE path="../escape.txt">>>\ndata\n<<<END_FILE>>>\n'
        '<<<FILE path="../escape.txt">>>\ndata\n<<<END_FILE>>>\n'
        '<<<END_RESPONSE bundle="1f13e141">>>\n'
    )
    assert code3 == "E_PATH"

    # 4. E_DUPLICATE beats E_SIZE
    code4 = _eval(
        '<<<FILE path="sprint.toml">>>\n' + ("A" * 1050000) + '\n<<<END_FILE>>>\n'
        '<<<FILE path="sprint.toml">>>\nshort\n<<<END_FILE>>>\n'
        '<<<END_RESPONSE bundle="1f13e141">>>\n'
    )
    assert code4 == "E_DUPLICATE"

    # 5. E_SIZE beats patch synthesis (E_SEARCH_NOMATCH)
    code5 = _eval(
        '<<<FILE path="sprint.toml">>>\n' + ("A" * 1050000) + '\n<<<END_FILE>>>\n'
        '<<<PATCH out="solution_key.patch" file="api/users.py">>>\n'
        '<<<<<<< SEARCH\nNONEXISTENT_FUNC_XYZ\n=======\nREPLACE\n>>>>>>> REPLACE\n'
        '<<<END_PATCH>>>\n'
        '<<<END_RESPONSE bundle="1f13e141">>>\n'
    )
    assert code5 == "E_SIZE"

    # 6. Patch synthesis (E_SEARCH_NOMATCH) beats post-parse schema error (E_SCHEMA)
    code6 = _eval(
        '<<<FILE path="sprint-proposal.toml">>>\nunknown_key = 123\n<<<END_FILE>>>\n'
        '<<<PATCH out="solution_key.patch" file="api/users.py">>>\n'
        '<<<<<<< SEARCH\nNONEXISTENT_FUNC_XYZ\n=======\nREPLACE\n>>>>>>> REPLACE\n'
        '<<<END_PATCH>>>\n'
        '<<<END_RESPONSE bundle="1f13e141">>>\n'
    )
    assert code6 == "E_SEARCH_NOMATCH"


def test_p05_path_attacks_and_symlinks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves R4-02: committed symlink E_PATH distinct from missing-file; full path attack corpus."""
    try:
        from actl import cli
        import actl.envelope  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R3/S2-R12: actl.envelope missing: {e}")

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

    # 1. Real symlink committed into target repository BEFORE base_sha is pinned.
    # Distinguishes symlink rejection from ordinary missing-file rejection.
    outside = tmp_path / "outside_secret.txt"
    outside.write_text("SECRET=1\n", encoding="utf-8")
    sym = layout.target_repo / "api" / "sym_target.py"
    try:
        if sym.exists() or sym.is_symlink():
            sym.unlink()
        sym.symlink_to(outside)
        assert sym.is_symlink(), "precondition: sym_target.py must be a symlink"
        subprocess.run(["git", "-C", str(layout.target_repo), "config", "core.hooksPath", "/dev/null"], check=True)
        subprocess.run(["git", "-C", str(layout.target_repo), "add", "api/sym_target.py"], check=True)
        subprocess.run(["git", "-C", str(layout.target_repo), "commit", "-m", "add symlink"], check=True)
        head_sha = subprocess.check_output(["git", "-C", str(layout.target_repo), "rev-parse", "HEAD"], text=True).strip()
        # Prove the blob exists in the committed tree (scratch checkout at base_sha will see it)
        ls = subprocess.run(
            ["git", "-C", str(layout.target_repo), "ls-tree", head_sha, "api/sym_target.py"],
            capture_output=True, text=True, check=True,
        )
        assert "sym_target.py" in ls.stdout, "symlink must be present in base_sha tree"
        assert "120000" in ls.stdout.split()[0] or ls.stdout.split()[0].startswith("120"), (
            f"git ls-tree must show symlink mode for sym_target.py, got: {ls.stdout!r}"
        )
        b_json = turn_dir / "bundle.json"
        b_data = json.loads(b_json.read_text(encoding="utf-8"))
        b_data["base_sha"] = head_sha
        b_json.write_text(json.dumps(b_data), encoding="utf-8")

        rc_sym, doc_sym = _run_chal(
            '<<<PATCH out="oracle-draft/mutants/s.patch" file="api/sym_target.py">>>\n'
            '<<<<<<< SEARCH\nSECRET=1\n=======\nSECRET=2\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n'
            '<<<END_RESPONSE bundle="b7eb659a">>>\n'
        )
        assert rc_sym == 2 and doc_sym["errors"][0]["code"] == "E_PATH"

        # Control: missing non-symlink path must not be confused with the symlink case.
        # A missing target yields E_PATH or a search error; message/detail must differ from symlink.
        rc_miss, doc_miss = _run_chal(
            '<<<PATCH out="oracle-draft/mutants/missing.patch" file="api/definitely_absent_r402.py">>>\n'
            '<<<<<<< SEARCH\nSECRET=1\n=======\nSECRET=2\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n'
            '<<<END_RESPONSE bundle="b7eb659a">>>\n'
        )
        assert rc_miss == 2
        miss_err = doc_miss["errors"][0]
        sym_err = doc_sym["errors"][0]
        assert miss_err["code"] in ("E_PATH", "E_SEARCH_NOMATCH", "E_EXISTS")
        # Distinguish: symlink rejection cites the symlink path as a symlink / link fault,
        # or at minimum the two error records are not byte-identical.
        if miss_err["code"] == "E_PATH":
            assert (miss_err.get("message"), miss_err.get("detail")) != (
                sym_err.get("message"), sym_err.get("detail")
            ), "missing-file E_PATH must not be identical to symlink E_PATH (false-green risk)"
    except OSError as err:
        pytest.fail(f"Filesystem unable to create symlink: {err}")

    # 2. Syntax / bound attacks on output paths (NUL, backslash, absolute, overlong, empty/dot)
    overlong_seg = "x" * 101
    overlong_total = "oracle-draft/" + ("a" * 250) + ".sh"
    assert len(overlong_total) > 255
    bad_paths = (
        "../escape.sh",
        "/etc/passwd",
        "oracle-draft/./01.sh",
        "oracle-draft//01.sh",
        "oracle-draft/proofs/",
        "oracle-draft/proofs/bad\x00path.sh",
        "oracle-draft\\01.sh",
        f"oracle-draft/{overlong_seg}.sh",
        overlong_total,
    )
    for bad in bad_paths:
        rc, doc = _run_chal(f'<<<FILE path="{bad}">>>\ndata\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="b7eb659a">>>\n')
        assert rc == 2 and doc["errors"][0]["code"] == "E_PATH", f"Path {bad!r} must fail with E_PATH"

    # 3. Target-file attacks: case-insensitive .git, NUL, backslash, absolute, overlong, case-collision dup
    bad_files = (
        "../escape.py",
        "/etc/passwd",
        "api/./users.py",
        "api//users.py",
        "api/users.py/",
        "api/users\x00.py",
        "api\\users.py",
        "api/.git/HEAD",
        "api/.GIT/config",
        "api/.Git/hooks/x",
        f"api/{overlong_seg}.py",
        "api/" + ("b" * 250) + ".py",
    )
    for bad_file in bad_files:
        rc, doc = _run_chal(
            f'<<<PATCH out="oracle-draft/mutants/m.patch" file="{bad_file}">>>\n'
            '<<<<<<< SEARCH\na\n=======\nb\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n'
            '<<<END_RESPONSE bundle="b7eb659a">>>\n'
        )
        assert rc == 2 and doc["errors"][0]["code"] == "E_PATH", f"File {bad_file!r} must fail with E_PATH"

    # Case-collision duplicates on output paths (same path ignoring case) -> E_DUPLICATE or E_PATH
    rc_cc, doc_cc = _run_chal(
        '<<<FILE path="oracle-draft/Proofs/01.sh">>>\n#!/bin/sh\necho ok\n<<<END_FILE>>>\n'
        '<<<FILE path="oracle-draft/proofs/01.sh">>>\n#!/bin/sh\necho ok\n<<<END_FILE>>>\n'
        '<<<END_RESPONSE bundle="b7eb659a">>>\n'
    )
    assert rc_cc == 2 and doc_cc["errors"][0]["code"] in ("E_DUPLICATE", "E_PATH"), (
        f"case-collision duplicate paths must be rejected, got {doc_cc['errors'][0]['code']}"
    )

def test_p03_all_six_adjacent_precedence_pairs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves normative linear pipeline precedence across all 6 adjacent stage pairs (S2-R4.6)."""
    from actl import cli
    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    td = layout.turns_dir(TAG) / "architect-1"

    def _eval(payload: str) -> str:
        for f in ("response.txt", "unpack.json", "repair.txt"):
            if (td / f).exists(): (td / f).unlink()
        (tmp_path / "in.txt").write_text(payload, encoding="utf-8")
        cli.main(["unpack", "architect-intake", "--sprint", TAG, "--turn", "architect-1", "-f", str(tmp_path / "in.txt"), "--json"])
        return json.loads((td / "unpack.json").read_text(encoding="utf-8"))["errors"][0]["code"]

    # Pair 1 (framing-versus-bundle mismatch): valid 8-hex prefix != real prefix (R4-05).
    # Real architect-1 golden prefix is 1f13e141; deadbeef is valid hex and unequal.
    _mismatch_prefix = "deadbeef"
    assert re.fullmatch(r"[0-9a-fA-F]{8}", _mismatch_prefix)
    assert _mismatch_prefix.lower() != "1f13e141"
    assert _eval(
        '<<<FILE path="sprint.toml">>>\nlive_run="none"\n<<<END_FILE>>>\n'
        f'<<<END_RESPONSE bundle="{_mismatch_prefix}">>>\n'
    ) == "E_BUNDLE_MISMATCH"
    # Separate framing-only fault (invalid non-hex sentinel) still yields E_SYNTAX_MARKER.
    assert _eval('<<<FILE path="sprint.toml">>>\nlive_run="none"\n<<<END_FILE>>>\n<<<END_RESPONSE bundle=badprefix>>>\n') == "E_SYNTAX_MARKER"
    # Pair 2 (Stage 2 Bundle Mismatch > Stage 3 Path Bounds)
    assert _eval('<<<FILE path="../escape.txt">>>\ndata\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="00000000">>>\n') == "E_BUNDLE_MISMATCH"
    # Pair 3 (Stage 3 Path Bounds > Stage 4 Duplicate Paths)
    assert _eval('<<<FILE path="../escape.txt">>>\na\n<<<END_FILE>>>\n<<<FILE path="../escape.txt">>>\nb\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="1f13e141">>>\n') == "E_PATH"
    # Pair 4 (Stage 4 Duplicate Paths > Stage 5 Size Limits)
    assert _eval('<<<FILE path="sprint.toml">>>\n' + ("A"*1050000) + '\n<<<END_FILE>>>\n<<<FILE path="sprint.toml">>>\nshort\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="1f13e141">>>\n') == "E_DUPLICATE"
    # Pair 5 (Stage 5 Size Limits > Stage 6 Patch Synthesis)
    assert _eval('<<<FILE path="sprint.toml">>>\n' + ("A"*1050000) + '\n<<<END_FILE>>>\n<<<PATCH out="solution_key.patch" file="api/users.py">>>\n<<<<<<< SEARCH\nNONEXISTENT\n=======\nR\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n<<<END_RESPONSE bundle="1f13e141">>>\n') == "E_SIZE"
    # Pair 6 (Stage 6 Patch Synthesis > Stage 7 Post-Parse Schema)
    assert _eval('<<<FILE path="sprint-proposal.toml">>>\nbad_key=123\n<<<END_FILE>>>\n<<<PATCH out="solution_key.patch" file="api/users.py">>>\n<<<<<<< SEARCH\nNONEXISTENT\n=======\nR\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n<<<END_RESPONSE bundle="1f13e141">>>\n') == "E_SEARCH_NOMATCH"
