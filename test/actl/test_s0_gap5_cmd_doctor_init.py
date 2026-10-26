# Authored-by: Gemini Flash 3.8 High (Google), as reported by the Owner, 2026-10-26
# Revised-by: Vela-OPB, 2026-10-26, applying the GPT 6.1 Sol review conditions (sys.path restore, Layout guard, direct rc asserts, narrow patches, hermetic doctor)
"""cmd_init created flag and cmd_doctor human-readable output."""
import argparse
import json
import subprocess
import sys
import types
from pathlib import Path

_SAVED_PATH = list(sys.path)
_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from actl import cmd_doctor, cmd_init  # noqa: E402
from actl.layout import Layout  # noqa: E402

sys.path[:] = _SAVED_PATH

SHA = "0123456789abcdef0123456789abcdef01234567"


def test_cmd_init_created_flag_reflects_existed(tmp_path, monkeypatch, capsys):
    layout = Layout(tmp_path / "actl_root", repo="target-repo")
    target_git = layout.target_repo / ".git"
    assert not target_git.exists()

    def fake_init_target(lay, target):
        lay.target_repo.mkdir(parents=True, exist_ok=True)
        return lay.target_repo

    def fake_run(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout=SHA + "\n", stderr="")

    monkeypatch.setattr(cmd_init, "init_target", fake_init_target)
    monkeypatch.setattr(cmd_init, "subprocess", types.SimpleNamespace(run=fake_run))

    args_json = argparse.Namespace(target="/fake/source", name="target-repo", json=True)
    assert cmd_init.handler(args_json, layout) == 0
    doc1 = json.loads(capsys.readouterr().out)
    assert doc1["created"] is True
    assert doc1["base_sha"] == SHA

    target_git.mkdir(parents=True, exist_ok=True)
    assert cmd_init.handler(args_json, layout) == 0
    doc2 = json.loads(capsys.readouterr().out)
    assert doc2["created"] is False

    args_text = argparse.Namespace(target="/fake/source", name="target-repo", json=False)
    assert cmd_init.handler(args_text, layout) == 0
    assert "created=False" in capsys.readouterr().out


def test_cmd_doctor_human_output_tool_versions_and_head_sha(tmp_path, monkeypatch, capsys):
    root = tmp_path / "actl_root"
    layout = Layout(root)
    fake_report = {
        "version": "v0.1.4",
        "head_sha": SHA,
        "actl_root": str(root),
        "tool_versions": {"tmux": "tmux 3.2a"},
        "audit": {"present": True},
        "warnings": ["sample_warning"],
    }
    monkeypatch.setattr(cmd_doctor, "run_doctor", lambda lay, refresh=False: fake_report)

    args = argparse.Namespace(refresh=False, json=False)
    assert cmd_doctor.handler(args, layout) == 0
    out = capsys.readouterr().out

    assert f"actl doctor v0.1.4 @ {SHA[:12]}\n" in out
    assert SHA[:13] not in out
    assert "tmux=tmux 3.2a\n" in out
    assert "tmux=None" not in out
    assert "warning: sample_warning\n" in out
