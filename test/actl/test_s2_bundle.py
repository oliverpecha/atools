from __future__ import annotations

import hashlib
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
    return Layout(root)


def test_p10_bundle_order_limits_and_safety(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    try:
        from actl import cli
        import actl.bundle  # noqa: F401
        import actl.cmd_bundle  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2: actl.bundle or actl.cmd_bundle missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))
    courier_dir = tmp_path / "courier"
    courier_dir.mkdir()
    monkeypatch.setenv("ACTL_COURIER_DIR", str(courier_dir))

    capsys.readouterr()
    out_file = tmp_path / "out_bundle.txt"
    rc = cli.main(
        [
            "bundle",
            "architect-intake",
            "--sprint",
            TAG,
            "--include",
            "api/users.py",
            "--out",
            str(out_file),
            "--model",
            "gpt-6-sol",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    assert rc == 0, f"Expected exit 0 for valid bundle, got {rc}: {captured.err}"
    data = json.loads(captured.out)
    for k in (
        "turn_id",
        "role",
        "purpose",
        "turn_dir",
        "bundle_path",
        "bundle_sha256",
        "sentinel",
        "chars",
        "files",
        "model_hint",
    ):
        assert k in data, f"Missing key {k} in bundle --json output"
    assert data["turn_id"] == "architect-1"
    assert data["role"] == "architect"
    assert data["purpose"] == "architect-intake"
    assert data["model_hint"] == "gpt-6-sol"

    drawers = list(courier_dir.iterdir())
    assert len(drawers) == 1, f"Expected 1 courier drawer, got {drawers}"
    assert "__target-repo__2026-10-16_public-profiles__architect-1__architect-intake" in drawers[0].name
    assert (drawers[0] / "bundle.txt").is_file()

    bundle_text = Path(data["bundle_path"]).read_text(encoding="utf-8")
    assert "api/users.py" in bundle_text
    users_sha = hashlib.sha256((GOLDEN_DIR / "target-repo" / "api" / "users.py").read_bytes()).hexdigest()
    assert users_sha in bundle_text, "Header must list included file SHA-256"

    rc_chal = cli.main(["bundle", "challenger", "--sprint", TAG, "--json"])
    cap_chal = capsys.readouterr()
    assert rc_chal == 0
    chal_doc = json.loads(cap_chal.out)
    chal_text = Path(chal_doc["bundle_path"]).read_text(encoding="utf-8")
    idx_spec = chal_text.find("spec-001.md")
    idx_qual = chal_text.find("qualification-004.json")
    assert idx_spec != -1 and idx_qual != -1 and idx_spec < idx_qual, (
        "Static spec-001.md must precede dynamic qualification-004.json"
    )

    rc_cur = cli.main(["bundle", "curator", "--sprint", TAG, "--json"])
    cap_cur = capsys.readouterr()
    assert rc_cur == 2, f"Expected exit 2 for curator stub, got {rc_cur}"
    assert "Stage 5" in (cap_cur.out + cap_cur.err)

    rc_mutex = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--out", "-", "--json"])
    capsys.readouterr()
    assert rc_mutex == 2, "Expected exit 2 when combining --out - and --json"

    rc_max = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--max-chars", "50"])
    cap_max = capsys.readouterr()
    assert rc_max == 2, f"Expected exit 2 when bundle exceeds --max-chars 50, got {rc_max}"
    assert "spec-001.md" in (cap_max.out + cap_max.err) or "api/" in (cap_max.out + cap_max.err)

    for bad_inc in ("../outside.txt", "/etc/passwd", "records/target-repo/sprint.toml", "nonexistent_file.py"):
        rc_inc = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--include", bad_inc, "--json"])
        capsys.readouterr()
        assert rc_inc == 2, f"Expected exit 2 for disallowed --include {bad_inc!r}, got {rc_inc}"


def test_p11_sentinel_hash_and_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    try:
        from actl import cli
        import actl.bundle  # noqa: F401
        import actl.unpack  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2/S2-R3: actl.bundle or actl.unpack missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    capsys.readouterr()
    rc = cli.main(["bundle", "architect-review", "--sprint", TAG, "--json"])
    captured = capsys.readouterr()
    assert rc == 0
    doc = json.loads(captured.out)

    raw_bytes = Path(doc["bundle_path"]).read_bytes()
    lines = raw_bytes.splitlines(keepends=True)
    assert len(lines) >= 2
    last_line = lines[-1].decode("utf-8")
    preceding_bytes = b"".join(lines[:-1])
    computed_sha = hashlib.sha256(preceding_bytes).hexdigest().lower()

    assert doc["bundle_sha256"] == computed_sha, "bundle_sha256 must match SHA-256 of bytes preceding sentinel"
    expected_sentinel = f'<<<END_RESPONSE bundle="{computed_sha[:8]}">>>'
    assert last_line.strip() == expected_sentinel
    assert doc["sentinel"] == expected_sentinel

    wrong_resp = tmp_path / "wrong_sentinel.txt"
    wrong_resp.write_text(
        '<<<FILE path="oracle-decision.json">>>\n'
        '{"decision": "lock_oracle", "feedback": "ok"}\n'
        '<<<END_FILE>>>\n'
        '<<<END_RESPONSE bundle="ffffffff">>>\n',
        encoding="utf-8",
    )
    rc_bad = cli.main(
        ["unpack", "architect-review", "--sprint", TAG, "--turn", doc["turn_id"], "-f", str(wrong_resp), "--json"]
    )
    capsys.readouterr()
    assert rc_bad == 2
    unpack_doc = json.loads((Path(doc["turn_dir"]) / "unpack.json").read_text(encoding="utf-8"))
    assert unpack_doc["ok"] is False
    assert unpack_doc["errors"][0]["code"] == "E_BUNDLE_MISMATCH"
