# Authored-by: Flash 3.8 High
from __future__ import annotations

import json
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
    layout = Layout(root)
    for turn_name in ("architect-1", "challenger-1", "architect-2"):
        src_turn = GOLDEN_DIR / "turns" / turn_name
        dst_turn = layout.turns_dir(TAG) / turn_name
        dst_turn.mkdir(parents=True, exist_ok=True)
        for f in ("bundle.json", "bundle.txt"):
            (dst_turn / f).write_bytes((src_turn / f).read_bytes())
    return layout


def test_postparse_shell_syntax_and_warnings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    try:
        from actl import cli
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R6.3: actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    turn_chal = layout.turns_dir(TAG) / "challenger-1"

    rc_good = cli.main(
        [
            "unpack",
            "challenger",
            "--sprint",
            TAG,
            "--turn",
            "challenger-1",
            "-f",
            str(GOLDEN_DIR / "responses" / "good_challenger.txt"),
            "--json",
        ]
    )
    assert rc_good == 0
    doc_good = json.loads((turn_chal / "unpack.json").read_text(encoding="utf-8"))
    assert doc_good["ok"] is True
    # S2-R6.3: set -uo pipefail and set -euo pipefail are both acceptable standards; no warning expected on good_challenger
    pipefail_warnings = [w for w in doc_good.get("warnings", []) if "pipefail" in w]
    assert len(pipefail_warnings) == 0, f"set -uo pipefail should not emit warning: {pipefail_warnings}"

    for script_rel in ("oracle-draft/probe.sh", "oracle-draft/proofs/01_public.sh"):
        sp = layout.outbox(TAG, "challenger") / script_rel
        assert sp.is_file()
        assert stat.S_IMODE(os.lstat(sp).st_mode) == 0o755

    for f in ("response.txt", "unpack.json", "repair.txt"):
        if (turn_chal / f).exists():
            (turn_chal / f).unlink()
    rc_bad = cli.main(
        [
            "unpack",
            "challenger",
            "--sprint",
            TAG,
            "--turn",
            "challenger-1",
            "-f",
            str(GOLDEN_DIR / "responses" / "bad_shell_syntax.txt"),
            "--json",
        ]
    )
    assert rc_bad == 2
    doc_bad = json.loads((turn_chal / "unpack.json").read_text(encoding="utf-8"))
    assert doc_bad["errors"][0]["code"] == "E_SHELL_SYNTAX"


def test_postparse_coverage_bijection_and_2digit_shorthand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    try:
        from actl import cli
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R6.2: actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    turn_chal = layout.turns_dir(TAG) / "challenger-1"
    good_text = (GOLDEN_DIR / "responses" / "good_challenger.txt").read_text(encoding="utf-8")

    shorthand_text = good_text.replace("R1 -> 01_public.sh, probe.sh", "R1 : 01, probe.sh")
    shorthand_file = tmp_path / "shorthand.txt"
    shorthand_file.write_text(shorthand_text, encoding="utf-8")
    rc_ok = cli.main(
        ["unpack", "challenger", "--sprint", TAG, "--turn", "challenger-1", "-f", str(shorthand_file), "--json"]
    )
    assert rc_ok == 0

    for f in ("response.txt", "unpack.json", "repair.txt"):
        if (turn_chal / f).exists():
            (turn_chal / f).unlink()
    bad_cov_text = good_text.replace("R1 -> 01_public.sh, probe.sh", "R1 -> 99_missing.sh")
    bad_cov_file = tmp_path / "bad_cov_ref.txt"
    bad_cov_file.write_text(bad_cov_text, encoding="utf-8")
    rc_bad = cli.main(
        ["unpack", "challenger", "--sprint", TAG, "--turn", "challenger-1", "-f", str(bad_cov_file), "--json"]
    )
    doc_bad = json.loads((turn_chal / "unpack.json").read_text(encoding="utf-8"))
    assert rc_bad == 2 and doc_bad["errors"][0]["code"] == "E_COVERAGE"


def test_p16_stage0_module_reuse(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    try:
        from actl import cli, schemas, scope, seq
        import actl.unpack  # noqa: F401
        import actl.turns  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R12.3: Stage 2 modules missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    calls = {"scope_parse": 0, "scope_validate": 0, "schemas_validate": 0, "state_lock": 0}
    orig_parse = scope.parse
    orig_validate = scope.validate
    orig_schema_val = schemas.validate
    orig_lock = seq.state_lock

    def spy_parse(text: str):
        calls["scope_parse"] += 1
        return orig_parse(text)

    def spy_validate(rules):
        calls["scope_validate"] += 1
        return orig_validate(rules)

    def spy_schema_val(kind: str, obj):
        calls["schemas_validate"] += 1
        return orig_schema_val(kind, obj)

    def spy_lock(lay, t: str):
        calls["state_lock"] += 1
        return orig_lock(lay, t)

    monkeypatch.setattr(scope, "parse", spy_parse)
    monkeypatch.setattr(scope, "validate", spy_validate)
    monkeypatch.setattr(schemas, "validate", spy_schema_val)
    monkeypatch.setattr(seq, "state_lock", spy_lock)

    from actl.turns import allocate_turn
    allocate_turn(layout, TAG, "architect")
    assert calls["state_lock"] >= 1, "allocate_turn must reuse actl.seq.state_lock"

    rc = cli.main(
        [
            "unpack",
            "challenger",
            "--sprint",
            TAG,
            "--turn",
            "challenger-1",
            "-f",
            str(GOLDEN_DIR / "responses" / "good_challenger.txt"),
            "--json",
        ]
    )
    assert rc == 0
    assert calls["scope_parse"] >= 1 and calls["scope_validate"] >= 1, "Must reuse actl.scope"

    rc2 = cli.main(
        [
            "unpack",
            "architect-review",
            "--sprint",
            TAG,
            "--turn",
            "architect-2",
            "-f",
            str(GOLDEN_DIR / "responses" / "good_architect_review_lock.txt"),
            "--json",
        ]
    )
    assert rc2 == 0
    assert calls["schemas_validate"] >= 1, "Must reuse actl.schemas.validate"
