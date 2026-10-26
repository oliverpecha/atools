# Authored-by: Vela-OPB (actl build assistant instance), as reported by the Owner, 2026-10-26
"""Contract-level hermetic tests for actl.doctor.run_doctor: strict command vectors, exact keys, cleanup on error."""
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

HEAD = "0123456789abcdef0123456789abcdef01234567"
ANCESTORS = ["5cb7f30", "759a0ca", "a9b3a4e", "4da9394"]
ENGINES = ["agent", "codex", "claude", "agy", "aider", "vibe"]
SUITE_KEYS = {"present", "exit_code", "tail"}
AUDIT_KEYS = {"present", "exit_code", "pass", "fail", "skip", "warn", "self_test_exit_code", "tail"}
TOP = {
    "version", "head_sha", "git_dirty", "git_status_porcelain", "ancestors", "tool_versions",
    "python_packages", "engine_clis", "timeout_available", "effective_user", "actl_root",
    "log_dir", "metadata_dir", "linger_state", "router_has_read_exit_code", "suites", "audit",
    "installed_sync_diffs", "warnings",
}


def _cp(cmd, rc=0, out="", err=""):
    return subprocess.CompletedProcess(cmd, returncode=rc, stdout=out, stderr=err)


class _Strict:
    def __init__(self, repo):
        self.git = ["git", "-C", str(repo)]
        self.calls = []
        self.handler = None

    def __call__(self, cmd, **kw):
        c = list(cmd)
        self.calls.append((c, kw))
        if self.handler is not None:
            res = self.handler(c, kw)
            if res is not None:
                return res
        g = self.git
        if c == g + ["rev-parse", "HEAD"]:
            return _cp(c, out=HEAD + "\n")
        if c == g + ["status", "--porcelain"]:
            return _cp(c)
        if len(c) == 7 and c[:5] == g + ["merge-base", "--is-ancestor"]:
            if c[5] in ANCESTORS and c[6] == "HEAD":
                return _cp(c, rc=1)
        if c in (["python3", "--version"], ["git", "--version"], ["bash", "--version"]):
            return _cp(c, out="tool 1.0\n")
        raise AssertionError("unexpected command: %r" % (c,))


class _Rig:
    def __init__(self, tmp, mp):
        self.tmp, self.mp = tmp, mp
        self.repo = tmp / "repo"
        self.repo.mkdir()
        (self.repo / "VERSION").write_text("v0.1.4\n", encoding="utf-8")
        self.run = _Strict(self.repo)
        self.layout = Layout(tmp / "actl_root")
        self.asked = []
        self.hits = set()

    def which(self, name):
        self.asked.append(name)
        return "/bin/" + name if name in self.hits else None

    def go(self, refresh=True):
        return doctor.run_doctor(self.layout, refresh=refresh)


def _path_stub(is_file=False, exists=False, home=None):
    def fake(p):
        assert str(p) in {"/usr/bin/timeout", "/root/.cursor"}
        return types.SimpleNamespace(is_file=lambda: is_file, exists=lambda: exists)

    fake.home = lambda: home
    return fake


@pytest.fixture
def rig(tmp_path, monkeypatch):
    r = _Rig(tmp_path, monkeypatch)
    monkeypatch.setattr(doctor, "REPO_ROOT", r.repo)
    monkeypatch.setattr(doctor, "_run", r.run)
    monkeypatch.setattr(doctor, "getpass", types.SimpleNamespace(getuser=lambda: "tester"))
    monkeypatch.setattr(
        doctor, "shutil", types.SimpleNamespace(which=r.which, rmtree=shutil.rmtree)
    )
    monkeypatch.setattr(doctor, "SYNC_TARGETS", {})
    monkeypatch.setenv("ATOOLS_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("ATOOLS_SESSION_DIR", str(tmp_path / "sess"))
    return r


def test_report_has_the_documented_shape_and_git_derived_values(rig):
    rig.hits = {"codex", "aider"}
    git = ["git", "-C", str(rig.repo)]

    def handler(c, kw):
        if c == git + ["status", "--porcelain"]:
            return _cp(c, out=" M a.txt\n?? b.txt\n")

    rig.run.handler = handler
    r = rig.go()
    assert set(r) == TOP
    assert r["head_sha"] == HEAD
    assert r["git_status_porcelain"] == " M a.txt\n?? b.txt"
    assert r["git_dirty"] is True
    assert r["actl_root"] == str(rig.layout.root)
    assert r["engine_clis"] == {
        "agent": False, "codex": True, "claude": False, "agy": False, "aider": True, "vibe": False,
    }
    assert set(rig.asked) >= set(ENGINES)
    assert list(r["ancestors"]) == ANCESTORS
    assert set(r["tool_versions"]) == {"python3", "git", "tmux", "bash"}
    assert set(r["python_packages"]) == {"pytest", "jsonschema"}
    assert set(r["suites"]) == {"engines", "session_persistence", "exit_code"}
    assert all(set(v) == SUITE_KEYS for v in r["suites"].values())
    assert set(r["audit"]) == AUDIT_KEYS
    assert set(r["installed_sync_diffs"]) == set()
    vectors = [c for c, _ in rig.run.calls]
    assert git + ["rev-parse", "HEAD"] in vectors
    assert git + ["status", "--porcelain"] in vectors
    for sha in ANCESTORS:
        assert git + ["merge-base", "--is-ancestor", sha, "HEAD"] in vectors
    for tool in ("python3", "git", "bash"):
        assert [tool, "--version"] in vectors


def test_clean_git_tree_is_not_dirty(rig):
    r = rig.go()
    assert r["git_status_porcelain"] == ""
    assert r["git_dirty"] is False


def test_suite_and_audit_calls_carry_a_positive_finite_timeout(rig):
    for rel in (
        "proof/run_suite_engines.sh",
        "proof/run_suite_session_persistence.sh",
        "proof/run_suite_exit_code.sh",
        "audit/atools-compliance_audit.sh",
    ):
        p = rig.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/bin/bash\n", encoding="utf-8")
    rig.run.handler = lambda c, kw: _cp(c) if c[0] == "bash" and c[1] != "--version" else None
    rig.go()
    heavy = [(c, kw) for c, kw in rig.run.calls if c[0] == "bash" and c[1] != "--version"]
    assert len(heavy) == 5
    assert all(0 < kw["timeout"] < float("inf") for _, kw in heavy)
    assert all(kw["cwd"] == str(rig.repo) for _, kw in heavy)
    expected = [
        ["bash", str(rig.repo / rel)]
        for rel in (
            "proof/run_suite_engines.sh",
            "proof/run_suite_session_persistence.sh",
            "proof/run_suite_exit_code.sh",
        )
    ] + [
        ["bash", str(rig.repo / "audit/atools-compliance_audit.sh"), flag]
        for flag in ("--cursor", "--self-test")
    ]
    assert sorted(c for c, _ in heavy) == sorted(expected)


def test_sync_diff_compares_the_repo_copy_with_the_installed_copy(rig):
    inst = rig.tmp / "inst"
    inst.mkdir()
    (inst / "x").write_text("x", encoding="utf-8")
    rig.mp.setattr(doctor, "SYNC_TARGETS", {"hooks/pre-commit": inst / "x"})

    def handler(c, kw):
        if c[:2] == ["diff", "-u"]:
            return _cp(c, rc=1, out="d")

    rig.run.handler = handler
    rig.go()
    expected = ["diff", "-u", str(rig.repo / "hooks/pre-commit"), str(inst / "x")]
    assert expected in [c for c, _ in rig.run.calls]


def test_timeout_probe_looks_at_usr_bin_timeout(rig):
    seen = []

    def fake(p):
        assert str(p) == "/usr/bin/timeout"
        seen.append(str(p))
        return types.SimpleNamespace(is_file=lambda: True, exists=lambda: False)

    fake.home = lambda: rig.tmp / "home"
    rig.mp.setattr(doctor, "Path", fake)
    assert rig.go()["timeout_available"] is True
    assert "/usr/bin/timeout" in seen


@pytest.mark.parametrize("root_cursor", [True, False])
def test_empty_environment_values_fall_back_to_the_cursor_directories(rig, root_cursor):
    home = rig.tmp / "home"
    rig.mp.setenv("ATOOLS_LOG_DIR", "")
    rig.mp.setenv("ATOOLS_SESSION_DIR", "")
    rig.mp.setattr(doctor, "Path", _path_stub(exists=root_cursor, home=home))
    r = rig.go()
    want = "/root/.cursor/logs" if root_cursor else str(home / ".cursor" / "logs")
    assert r["log_dir"] == want
    assert r["metadata_dir"] == str(home / ".cursor" / "sessions")


@pytest.mark.parametrize("existed", [True, False])
def test_proof_out_is_cleaned_up_when_a_command_raises(rig, existed):
    po = rig.repo / "proof" / "out"
    if existed:
        po.mkdir(parents=True)
        (po / "keep.txt").write_bytes(b"orig")

    def handler(c, kw):
        po.mkdir(parents=True, exist_ok=True)
        (po / "new.txt").write_bytes(b"n")
        if existed:
            (po / "keep.txt").write_bytes(b"changed")
        raise RuntimeError("boom-from-command")

    rig.run.handler = handler
    with pytest.raises(RuntimeError, match="boom-from-command"):
        rig.go()
    assert not (po / "new.txt").exists()
    if existed:
        assert (po / "keep.txt").read_bytes() == b"orig"
    else:
        assert not po.exists()
