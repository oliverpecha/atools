"""S37-13/16/17/19/20 against router.process, using PATH stubs for tmux and kill."""
import importlib
import os
import time

import pytest

process = importlib.import_module("router.process")

TMUX_STUB = """#!/bin/sh
printf '%s\\n' "$1" >> "$STUB_LOG"
case "$1" in
list-sessions) printf '%s\\n' "$STUB_SESSIONS"; exit 0;;
list-panes)
  if [ -n "$STUB_PANES_ERR" ]; then printf '%s\\n' "$STUB_PANES_ERR" >&2; fi
  if [ -n "$STUB_PANES_OUT" ]; then printf '%s\\n' "$STUB_PANES_OUT"; fi
  exit "${STUB_PANES_RC:-0}";;
*) exit "${STUB_OTHER_RC:-0}";;
esac
"""


def _install(tmp_path, monkeypatch, sessions, panes_out="", panes_err="", panes_rc="0"):
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in (("tmux", TMUX_STUB), ("kill", "#!/bin/sh\nexit 0\n")):
        p = bindir / name
        p.write_text(body)
        p.chmod(0o755)
    log = tmp_path / "tmux.log"
    log.write_text("")
    meta_dir = tmp_path / "sessions"
    log_dir = tmp_path / "logs"
    meta_dir.mkdir()
    log_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bindir}{os.pathsep}{os.environ.get('PATH', '')}")
    monkeypatch.setenv("ATOOLS_SESSION_DIR", str(meta_dir))
    monkeypatch.setenv("ATOOLS_LOG_DIR", str(log_dir))
    monkeypatch.setenv("STUB_LOG", str(log))
    monkeypatch.setenv("STUB_SESSIONS", sessions)
    monkeypatch.setenv("STUB_PANES_OUT", panes_out)
    monkeypatch.setenv("STUB_PANES_ERR", panes_err)
    monkeypatch.setenv("STUB_PANES_RC", panes_rc)
    return meta_dir, log_dir, log


# ---- S37-16: list-panes exits 1 -------------------------------------------

@pytest.mark.parametrize("panes_err", ["can't find session: sess-a", "boom", ""])
def test_kill_session_list_panes_failure_is_not_fatal(tmp_path, monkeypatch, capsys, panes_err):
    _, _, log = _install(tmp_path, monkeypatch, "sess-a|1700000000", panes_err=panes_err, panes_rc="1")
    rc = process.kill_session("sess-a")
    out = capsys.readouterr().out
    assert rc == 0
    assert log.read_text().split() == ["list-sessions", "list-panes", "kill-session"]
    assert process.read_exit_code("sess-a") == 143
    assert "terminated" in out


# ---- S37-13: default manual=False ------------------------------------------

def test_kill_session_default_message_is_not_manual(tmp_path, monkeypatch, capsys):
    _install(tmp_path, monkeypatch, "sess-c|1700000000")
    assert process.kill_session("sess-c") == 0
    out = capsys.readouterr().out
    assert "Session 'sess-c' terminated." in out
    assert "manually" not in out


def test_kill_session_manual_message(tmp_path, monkeypatch, capsys):
    _install(tmp_path, monkeypatch, "sess-d|1700000000")
    assert process.kill_session("sess-d", manual=True) == 0
    assert "manually terminated" in capsys.readouterr().out


# ---- S37-17: _wait_pids_gone ------------------------------------------------

def test_wait_permission_error_returns_false_after_timeout(monkeypatch):
    calls = []

    def fake_kill(pid, sig):
        calls.append((pid, sig))
        raise PermissionError(1, "denied")

    monkeypatch.setattr(process.os, "kill", fake_kill)
    t0 = time.monotonic()
    assert process._wait_pids_gone(["123"], timeout=0.3) is False
    dt = time.monotonic() - t0
    assert 0.25 <= dt < 2.0
    assert calls and set(calls) == {(123, 0)}


def test_wait_process_lookup_error_means_gone(monkeypatch):
    def fake_kill(pid, sig):
        raise ProcessLookupError(3, "no such process")

    monkeypatch.setattr(process.os, "kill", fake_kill)
    t0 = time.monotonic()
    assert process._wait_pids_gone(["123", "456"], timeout=2.0) is True
    assert time.monotonic() - t0 < 1.0


@pytest.mark.parametrize("bad", ["abc", "", "1.5", " "])
def test_wait_bad_pid_string_counts_as_gone_without_os_kill(monkeypatch, bad):
    calls = []
    monkeypatch.setattr(process.os, "kill", lambda pid, sig: calls.append((pid, sig)))
    # a bad string raises ValueError inside int(); only "1.5"/"abc"/""/" " are used, none is a valid int
    assert process._wait_pids_gone([bad], timeout=1.0) is True
    assert calls == []


def test_wait_mixed_permission_and_gone_is_false(monkeypatch):
    def fake_kill(pid, sig):
        if pid == 1:
            raise ProcessLookupError()
        raise PermissionError()

    monkeypatch.setattr(process.os, "kill", fake_kill)
    assert process._wait_pids_gone(["abc", "1", "2"], timeout=0.2) is False


def test_wait_other_oserror_propagates(monkeypatch):
    def fake_kill(pid, sig):
        raise OSError(22, "invalid")

    monkeypatch.setattr(process.os, "kill", fake_kill)
    with pytest.raises(OSError):
        process._wait_pids_gone(["123"], timeout=0.2)


def test_wait_no_pids_is_true():
    assert process._wait_pids_gone([], timeout=0.5) is True


def test_kill_session_permission_error_leaves_no_exit_file(tmp_path, monkeypatch, capsys):
    meta_dir, _, _ = _install(tmp_path, monkeypatch, "sess-b|1700000000", panes_out="4242")
    exit_path = process.get_exit_path("sess-b")
    tmp_exit = exit_path.with_suffix(".exit.tmp")
    exit_path.write_text("129\n")
    tmp_exit.write_text("129\n")

    def fake_kill(pid, sig):
        raise PermissionError(1, "denied")

    monkeypatch.setattr(process.os, "kill", fake_kill)
    assert process.kill_session("sess-b") == 0
    assert not exit_path.exists()
    assert not tmp_exit.exists()
    assert process.read_exit_code("sess-b") is None


@pytest.mark.parametrize("pane", ["4242", "notapid"])
def test_kill_session_gone_or_bad_pid_records_143_over_stale_129(tmp_path, monkeypatch, capsys, pane):
    _install(tmp_path, monkeypatch, "sess-e|1700000000", panes_out=pane)
    process.get_exit_path("sess-e").write_text("129\n")

    def fake_kill(pid, sig):
        raise ProcessLookupError()

    monkeypatch.setattr(process.os, "kill", fake_kill)
    assert process.kill_session("sess-e") == 0
    assert process.read_exit_code("sess-e") == 143


# ---- S37-19: bare line without "|" -----------------------------------------

def test_list_active_tmux_sessions_tolerates_line_without_pipe(tmp_path, monkeypatch):
    _install(tmp_path, monkeypatch, "bare\nnamed|123\nbadts|abc")
    res = process.list_active_tmux_sessions()
    now = time.time()
    assert set(res) == {"bare", "named", "badts"}
    assert res["named"] == 123.0
    assert abs(res["bare"] - now) < 120
    assert abs(res["badts"] - now) < 120


# ---- S37-20: get_running_sessions filter -----------------------------------

def test_get_running_sessions_filter(tmp_path, monkeypatch):
    meta_dir, log_dir, _ = _install(
        tmp_path, monkeypatch, "foreign|1\narun-bare|1\nwithmeta|1\nwithlog|1"
    )
    (meta_dir / "withmeta.json").write_text(
        '{"tier": "t", "model": "m", "engine": "e", "start_time": 1.0}'
    )
    (log_dir / "withlog.log").write_text("x")
    names = {s["session"] for s in process.get_running_sessions()}
    assert names == {"arun-bare", "withmeta", "withlog"}
