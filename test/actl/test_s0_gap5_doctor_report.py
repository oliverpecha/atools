# Authored-by: Vela-OPB (actl build assistant instance), as reported by the Owner, 2026-10-26
"""Hermetic tests for the report fields built by actl.doctor.run_doctor."""
import shutil
import subprocess
import sys
import types
from pathlib import Path

import pytest

_SAVED_PATH = list(sys.path)
_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from actl import doctor  # noqa: E402
from actl.layout import Layout  # noqa: E402

sys.path[:] = _SAVED_PATH


def _cp(cmd, rc=0, out="", err=""):
    return subprocess.CompletedProcess(cmd, returncode=rc, stdout=out, stderr=err)


class _Run:
    def __init__(self):
        self.calls = []
        self.handler = None

    def __call__(self, cmd, **kw):
        self.calls.append((list(cmd), kw))
        if self.handler is not None:
            res = self.handler(list(cmd), kw)
            if res is not None:
                return res
        return _cp(cmd)


def _shutil_proxy(which=None, rmtree=None):
    return types.SimpleNamespace(
        which=which or (lambda name: None), rmtree=rmtree or shutil.rmtree
    )


def _path_stub(is_file=False, exists=False, home=None):
    def fake(p):
        return types.SimpleNamespace(is_file=lambda: is_file, exists=lambda: exists)

    fake.home = lambda: home
    return fake


class _Rig:
    def __init__(self, tmp, mp):
        self.tmp, self.mp = tmp, mp
        self.repo = tmp / "repo"
        self.repo.mkdir()
        (self.repo / "VERSION").write_text("v0.1.4\n", encoding="utf-8")
        self.run = _Run()
        self.layout = Layout(tmp / "actl_root")

    def go(self, refresh=True):
        return doctor.run_doctor(self.layout, refresh=refresh)


@pytest.fixture
def rig(tmp_path, monkeypatch):
    r = _Rig(tmp_path, monkeypatch)
    monkeypatch.setattr(doctor, "REPO_ROOT", r.repo)
    monkeypatch.setattr(doctor, "_run", r.run)
    monkeypatch.setattr(doctor, "getpass", types.SimpleNamespace(getuser=lambda: "tester"))
    monkeypatch.setattr(doctor, "shutil", _shutil_proxy())
    monkeypatch.setattr(doctor, "SYNC_TARGETS", {})
    monkeypatch.setenv("ATOOLS_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("ATOOLS_SESSION_DIR", str(tmp_path / "sess"))
    return r


@pytest.mark.parametrize(
    "version,warns",
    [
        ("v0.1.3", True),
        ("v0.1.4", False),
        ("v0.1.9", False),
        ("v0.2.0", False),
        ("v1.0.0", False),
        ("v0.0.9", True),
    ],
)
def test_version_below_minimum_adds_a_warning(rig, version, warns):
    (rig.repo / "VERSION").write_text(version + "\n", encoding="utf-8")
    report = rig.go()
    assert report["version"] == version
    assert ("VERSION %s is below v0.1.4" % version in report["warnings"]) is warns


def test_ancestors_follow_the_merge_base_exit_codes(rig):
    codes = {"5cb7f30": 0, "759a0ca": 1, "a9b3a4e": 2}

    def handler(cmd, kw):
        if "merge-base" in cmd:
            return _cp(cmd, rc=codes.get(cmd[-2], 1))

    rig.run.handler = handler
    assert rig.go()["ancestors"] == {
        "5cb7f30": True,
        "759a0ca": False,
        "a9b3a4e": False,
        "4da9394": False,
    }


@pytest.mark.parametrize(
    "out,err,expected",
    [("Python 3.12.3\n", "", "Python 3.12.3"), ("", "Python 2.7.18\n", "Python 2.7.18")],
)
def test_python_version_comes_from_stdout_then_stderr(rig, out, err, expected):
    def handler(cmd, kw):
        if cmd[:2] == ["python3", "--version"]:
            return _cp(cmd, out=out, err=err)

    rig.run.handler = handler
    assert rig.go()["tool_versions"]["python3"] == expected


def test_tool_versions_come_from_each_tool(rig):
    rig.mp.setattr(
        doctor, "shutil", _shutil_proxy(which=lambda n: "/bin/tmux" if n == "tmux" else None)
    )
    outs = {
        ("python3", "--version"): "Python 3.12.3\n",
        ("git", "--version"): "git version 2.43.0\n",
        ("bash", "--version"): "GNU bash, version 5.2.21\nsecond line\n",
        ("tmux", "-V"): "tmux 3.4\n",
    }

    def handler(cmd, kw):
        if tuple(cmd[:2]) in outs:
            return _cp(cmd, out=outs[tuple(cmd[:2])])

    rig.run.handler = handler
    report = rig.go()
    assert report["tool_versions"] == {
        "python3": "Python 3.12.3",
        "git": "git version 2.43.0",
        "bash": "GNU bash, version 5.2.21",
        "tmux": "tmux 3.4",
    }
    assert report["effective_user"] == "tester"


def test_tmux_is_none_when_not_on_path(rig):
    assert rig.go()["tool_versions"]["tmux"] is None


def _find_spec_for(available):
    def find_spec(name):
        return object() if name in available else None

    return types.SimpleNamespace(util=types.SimpleNamespace(find_spec=find_spec))


def test_python_packages_follow_find_spec(rig):
    rig.mp.setattr(doctor, "importlib", _find_spec_for({"jsonschema"}))
    assert rig.go()["python_packages"] == {"pytest": False, "jsonschema": True}
    rig.mp.setattr(doctor, "importlib", _find_spec_for({"pytest"}))
    assert rig.go()["python_packages"] == {"pytest": True, "jsonschema": False}


@pytest.mark.parametrize(
    "on_path,at_usr_bin,expected",
    [(True, False, True), (False, True, True), (False, False, False), (True, True, True)],
)
def test_timeout_is_available_on_path_or_at_usr_bin(rig, on_path, at_usr_bin, expected):
    rig.mp.setattr(
        doctor,
        "shutil",
        _shutil_proxy(which=lambda n: "/x/timeout" if (n == "timeout" and on_path) else None),
    )
    rig.mp.setattr(doctor, "Path", _path_stub(is_file=at_usr_bin, home=rig.tmp / "home"))
    assert rig.go()["timeout_available"] is expected


def test_log_and_metadata_dirs_prefer_the_environment(rig):
    report = rig.go()
    assert report["log_dir"] == str(rig.tmp / "logs")
    assert report["metadata_dir"] == str(rig.tmp / "sess")


def test_log_and_metadata_dirs_fall_back_to_the_home_directory(rig):
    home = rig.tmp / "home"
    rig.mp.delenv("ATOOLS_LOG_DIR")
    rig.mp.delenv("ATOOLS_SESSION_DIR")
    rig.mp.setattr(doctor, "Path", _path_stub(exists=False, home=home))
    report = rig.go()
    assert report["log_dir"] == str(home / ".cursor" / "logs")
    assert report["metadata_dir"] == str(home / ".cursor" / "sessions")


def _with_loginctl(rig, rc, out):
    rig.mp.setattr(
        doctor,
        "shutil",
        _shutil_proxy(which=lambda n: "/bin/loginctl" if n == "loginctl" else None),
    )

    def handler(cmd, kw):
        if cmd[:2] == ["loginctl", "show-user"]:
            return _cp(cmd, rc=rc, out=out)

    rig.run.handler = handler


def test_linger_state_reads_the_loginctl_output(rig):
    _with_loginctl(rig, 0, "Linger=yes\n")
    assert rig.go()["linger_state"] == "Linger=yes"
    assert ["loginctl", "show-user", "tester", "-p", "Linger"] in [c for c, _ in rig.run.calls]


def test_linger_state_is_unknown_when_loginctl_fails(rig):
    _with_loginctl(rig, 1, "Linger=yes\n")
    assert rig.go()["linger_state"] == "unknown"


def test_linger_state_is_unknown_without_loginctl(rig):
    assert rig.go()["linger_state"] == "unknown"


@pytest.mark.parametrize(
    "body,expected",
    [
        (None, False),
        ("def other():\n    pass\n", False),
        ("def read_exit_code(name):\n    return None\n", True),
    ],
    ids=["no-file", "no-def", "has-def"],
)
def test_router_read_exit_code_probe(rig, body, expected):
    if body is not None:
        p = rig.repo / "src" / "router" / "process.py"
        p.parent.mkdir(parents=True)
        p.write_text(body, encoding="utf-8")
    report = rig.go()
    assert report["router_has_read_exit_code"] is expected
    msg = "router.process.read_exit_code is not present"
    assert (msg in report["warnings"]) is (not expected)


def test_installed_sync_diffs_record_missing_same_and_differing_copies(rig):
    inst = rig.tmp / "inst"
    inst.mkdir()
    for name in ("same", "out", "err", "none"):
        (inst / name).write_text(name, encoding="utf-8")
    rig.mp.setattr(
        doctor,
        "SYNC_TARGETS",
        {
            "a/missing": inst / "nope",
            "b/same": inst / "same",
            "c/out": inst / "out",
            "d/err": inst / "err",
            "e/none": inst / "none",
        },
    )
    replies = {
        "same": _cp([], 0),
        "out": _cp([], 1, out="DIFFTEXT"),
        "err": _cp([], 2, err="trouble"),
        "none": _cp([], 1),
    }

    def handler(cmd, kw):
        if cmd[:2] == ["diff", "-u"]:
            return replies[Path(cmd[-1]).name]

    rig.run.handler = handler
    report = rig.go()
    assert report["installed_sync_diffs"] == {
        "a/missing": "MISSING",
        "b/same": "",
        "c/out": "DIFFTEXT",
        "d/err": "trouble",
        "e/none": "DIFF",
    }
    warnings = report["warnings"]
    assert "installed sync target missing: a/missing" in warnings
    for rel in ("c/out", "d/err", "e/none"):
        assert "installed sync target differs: %s" % rel in warnings
    assert not any("b/same" in w for w in warnings)
