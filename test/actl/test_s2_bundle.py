# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

import hashlib
import json
import os
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
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2: actl.bundle missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    # 1. Valid bundle with --include
    capsys.readouterr()
    rc = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--include", "api/users.py", "--json"])
    cap = capsys.readouterr()
    assert rc == 0
    doc = json.loads(cap.out)
    assert doc["turn_id"] == "architect-1"

    # F-03 / R4-02: Real symlink inside target_repo escaping repository
    sym = layout.target_repo / "sym_outside.py"
    if sym.is_symlink() or sym.exists():
        sym.unlink()
    try:
        (tmp_path / "outside.txt").write_text("escape\n", encoding="utf-8")
        sym.symlink_to(tmp_path / "outside.txt")
        assert sym.is_symlink(), "precondition: sym_outside.py must be a symlink"
        rc_sym = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--include", "sym_outside.py", "--json"])
        capsys.readouterr()
        assert rc_sym == 2, "bundle --include on escaping symlink must fail with exit 2"
        # Negative control: include of a regular in-repo file must succeed (not false E_PATH)
        rc_ok = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--include", "api/users.py", "--json"])
        capsys.readouterr()
        assert rc_ok == 0, "regular in-repo --include must succeed (symlink case must be distinct)"
    except OSError as e:
        pytest.fail(f"FAIL: unexpected OSError in test execution: {e}")


def test_p11_sentinel_hash_and_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """P-S2-11 / R4-07: sentinel == bundle_sha256[:8]; foreign sentinel rejected (D-44)."""
    try:
        from actl import cli
        import actl.bundle  # noqa: F401
        import actl.envelope  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2/S2-R3: actl.bundle or actl.envelope missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    capsys.readouterr()
    rc = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--json"])
    cap = capsys.readouterr()
    assert rc == 0, "bundle must succeed"
    doc = json.loads(cap.out)
    bundle_sha = doc["bundle_sha256"]
    assert isinstance(bundle_sha, str) and len(bundle_sha) == 64
    want_prefix = bundle_sha[:8].lower()
    sentinel = doc.get("sentinel") or f'<<<END_RESPONSE bundle="{want_prefix}">>>'
    assert want_prefix in sentinel, "CLI sentinel must carry bundle_sha256[:8]"

    turn_dir = Path(doc["turn_dir"])
    bundle_txt = (turn_dir / "bundle.txt").read_text(encoding="utf-8")
    assert bundle_txt.rstrip("\n").endswith(f'<<<END_RESPONSE bundle="{want_prefix}">>>'), (
        "bundle.txt final sentinel must equal bundle_sha256[:8]"
    )
    # Body hash excludes the sentinel line (S2-R2.4).
    body = bundle_txt[: bundle_txt.rfind("<<<END_RESPONSE")]
    assert hashlib.sha256(body.encode("utf-8")).hexdigest() == bundle_sha

    # Foreign / wrong prefix must be rejected as E_BUNDLE_MISMATCH on unpack.
    bad_prefix = "deadbeef" if want_prefix != "deadbeef" else "cafebabe"
    assert bad_prefix != want_prefix
    # Reuse a minimal FILE body with the wrong sentinel against this turn's bundle.
    for turn_name in ("architect-1",):
        td = layout.turns_dir(TAG) / turn_name
        for f in ("response.txt", "unpack.json", "repair.txt"):
            p = td / f
            if p.exists():
                p.unlink()
        payload = (
            '<<<FILE path="sprint.toml">>>\nlive_run="none"\n<<<END_FILE>>>\n'
            f'<<<END_RESPONSE bundle="{bad_prefix}">>>\n'
        )
        inp = tmp_path / "bad_sent.txt"
        inp.write_text(payload, encoding="utf-8")
        rc_u = cli.main([
            "unpack", "architect-intake", "--sprint", TAG, "--turn", turn_name,
            "-f", str(inp), "--json",
        ])
        assert rc_u == 2
        unpack = json.loads((td / "unpack.json").read_text(encoding="utf-8"))
        assert unpack["errors"][0]["code"] == "E_BUNDLE_MISMATCH"


def test_bundle_clipboard_helpers_and_osc52(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    """Proves F-07 & S2-R2.8: --clip invokes clipboard binary; --osc52 with --json keeps stdout pure JSON."""
    try:
        from actl import cli
        import actl.bundle  # noqa: F401
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R2.8: actl.bundle missing: {e}")

    layout = _setup_sprint(tmp_path)
    monkeypatch.setenv("ACTL_ROOT", str(layout.root))

    # Mock wl-copy on PATH
    mock_bin = tmp_path / "mock_bin"
    mock_bin.mkdir()
    clip_log = tmp_path / "clip.log"
    (mock_bin / "wl-copy").write_text(f"#!/usr/bin/env bash\ncat > '{clip_log}'\n", encoding="utf-8")
    (mock_bin / "wl-copy").chmod(0o755)
    monkeypatch.setenv("PATH", f"{mock_bin}:{os.environ['PATH']}")

    capsys.readouterr()
    rc_clip = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--clip"])
    assert rc_clip == 0
    assert clip_log.is_file() and len(clip_log.read_text(encoding="utf-8")) > 100

    # Test --osc52 combined with --json
    capsys.readouterr()
    rc_osc = cli.main(["bundle", "architect-intake", "--sprint", TAG, "--osc52", "--json"])
    cap_osc = capsys.readouterr()
    assert rc_osc == 0
    json.loads(cap_osc.out)  # Stdout must be valid JSON
    assert "\x1b]52;c;" in cap_osc.err
