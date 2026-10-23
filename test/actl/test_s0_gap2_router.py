# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2 (workstream 0B), not executed.
# Function names/signatures of router.process are inferred; see SURVIVOR_ANALYSIS.md "unverified".
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for _p in (REPO / "src", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from router import process  # noqa: E402

DEAD_PID = "2147483000"


@pytest.fixture
def dirs(tmp_path, monkeypatch):
    sess, logs = tmp_path / "sess", tmp_path / "logs"
    sess.mkdir()
    logs.mkdir()
    monkeypatch.setenv("ATOOLS_SESSION_DIR", str(sess))
    monkeypatch.setenv("ATOOLS_LOG_DIR", str(logs))
    return sess, logs


def cp(cmd, rc=0, out="", err=""):
    return subprocess.CompletedProcess(cmd, rc, out, err)


class FakeTmux:
    def __init__(self, active, ks_rc=0, ks_err=""):
        self.active, self.ks_rc, self.ks_err = active, ks_rc, ks_err

    def __call__(self, cmd, *a, **k):
        c = list(cmd) if not isinstance(cmd, str) else cmd.split()
        if c[:2] == ["tmux", "list-sessions"]:
            return cp(c, 0 if self.active else 1, "".join(s + "\n" for s in self.active))
        if c[:2] == ["tmux", "list-panes"]:
            return cp(c, 0, DEAD_PID + "\n")
        if c[:2] == ["tmux", "kill-session"]:
            return cp(c, self.ks_rc, "", self.ks_err)
        return cp(c, 0)


def rec():
    f = getattr(process, "_record_exit", None) or getattr(process, "record_exit", None)
    if f is None:
        pytest.fail("FAIL: router.process has no _record_exit/record_exit", pytrace=False)
    return f


def test_record_exit_creates_missing_parent_directory(tmp_path, monkeypatch):
    # process.py:87 mkdir(parents=True, ...): mutation parents=True -> False fails here.
    monkeypatch.setenv("ATOOLS_SESSION_DIR", str(tmp_path / "x" / "y"))
    rec()("gap2-a", 143, overwrite=True)
    assert process.read_exit_code("gap2-a") == 143


def test_record_exit_with_existing_parent_directory(dirs):
    # process.py:87 mkdir(..., exist_ok=True): mutation exist_ok=True -> False fails here.
    rec()("gap2-b", 5, overwrite=True)
    rec()("gap2-b", 7, overwrite=True)
    assert process.read_exit_code("gap2-b") == 7


def test_kill_unknown_session_returns_1(dirs, monkeypatch, capsys):
    monkeypatch.setattr(process.subprocess, "run", FakeTmux([]))
    monkeypatch.setattr(process, "list_active_tmux_sessions", lambda: [], raising=False)
    assert process.kill_session("zz-gap2-unknown") == 1  # line 526
    assert "No active session" in capsys.readouterr().err


def test_kill_finished_session_with_log_returns_0(dirs, monkeypatch):
    _, logs = dirs
    (logs / "zz-gap2-done.log").write_text("x")
    monkeypatch.setattr(process.subprocess, "run", FakeTmux([]))
    monkeypatch.setattr(process, "list_active_tmux_sessions", lambda: [], raising=False)
    assert process.kill_session("zz-gap2-done") == 0


def test_kill_tmux_failure_returns_1_and_writes_no_exit(dirs, monkeypatch):
    name = "zz-gap2-fail"
    monkeypatch.setattr(process.subprocess, "run", FakeTmux([name], ks_rc=1, ks_err="weird unexpected failure"))
    monkeypatch.setattr(process, "list_active_tmux_sessions", lambda: [name], raising=False)
    assert process.kill_session(name) == 1  # line 557
    assert process.read_exit_code(name) is None


@pytest.mark.parametrize("ks_rc,ks_err", [(0, ""), (1, "no server running on /tmp/tmux-1/default")],
                         ids=["kill-session-ok", "server-already-gone"])
def test_kill_overwrites_129_with_143(dirs, monkeypatch, ks_rc, ks_err):
    # line 535 overwrite=True -> False leaves the HUP-trap value 129 in place.
    sess, _ = dirs
    name = "zz-gap2-hup"
    (sess / f"{name}.exit").write_text("129\n")
    monkeypatch.setattr(process.subprocess, "run", FakeTmux([name], ks_rc=ks_rc, ks_err=ks_err))
    monkeypatch.setattr(process, "list_active_tmux_sessions", lambda: [name], raising=False)
    assert process.kill_session(name, manual=True) == 0
    assert process.read_exit_code(name) == 143


def test_cli_kill_unknown_session_exit_1(tmp_path):
    if shutil.which("tmux") is None:
        pytest.fail("ENVFAIL: tmux not installed", pytrace=False)
    env = dict(os.environ, TMUX_TMPDIR=str(tmp_path), ATOOLS_LOG_DIR=str(tmp_path / "l"),
               ATOOLS_SESSION_DIR=str(tmp_path / "s"))
    env.pop("TMUX", None)
    (tmp_path / "l").mkdir()
    (tmp_path / "s").mkdir()
    r = subprocess.run([str(REPO / "bin" / "arouter"), "kill", "zz-gap2-unknown"], env=env,
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 1, (r.stdout, r.stderr)
