# Authored-by: Vela-OPB (actl build assistant instance), as reported by the Owner, 2026-10-26
"""Hermetic tests for suites, audit, baseline writing and proof/out handling in actl.doctor."""
import json
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

SUITES = {
    "engines": "proof/run_suite_engines.sh",
    "session_persistence": "proof/run_suite_session_persistence.sh",
    "exit_code": "proof/run_suite_exit_code.sh",
}
RC = {"engines": 0, "session_persistence": 5, "exit_code": 9}


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


def _picky_rmtree(path, ignore_errors=False, **kw):
    if not ignore_errors:
        raise OSError("rmtree called without ignore_errors")
    shutil.rmtree(path, ignore_errors=True)


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


def test_missing_suite_scripts_are_recorded_and_only_exit_code_warns(rig):
    report = rig.go()
    for key in SUITES:
        assert report["suites"][key] == {"present": False, "exit_code": None, "tail": ""}
    assert "suite script missing: proof/run_suite_exit_code.sh" in report["warnings"]
    others = [w for w in report["warnings"] if w.startswith("suite script missing")]
    assert others == ["suite script missing: proof/run_suite_exit_code.sh"]
    assert not any(c[0] == "bash" and c[1] != "--version" for c, _ in rig.run.calls)


def test_present_suites_record_exit_code_and_tail(rig):
    for rel in SUITES.values():
        p = rig.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("#!/bin/bash\n", encoding="utf-8")

    def handler(cmd, kw):
        if cmd[0] == "bash":
            for key, rel in SUITES.items():
                if cmd[1] == str(rig.repo / rel):
                    return _cp(cmd, rc=RC[key], out="o1\no2\n", err="e1\n")

    rig.run.handler = handler
    report = rig.go()
    for key in SUITES:
        assert report["suites"][key] == {
            "present": True,
            "exit_code": RC[key],
            "tail": "o1\no2\ne1",
        }
    assert not any(w.startswith("suite script missing") for w in report["warnings"])
    bash_calls = [(c, kw) for c, kw in rig.run.calls if c[0] == "bash" and c[1] != "--version"]
    assert [c[1] for c, _ in bash_calls] == [str(rig.repo / rel) for rel in SUITES.values()]
    assert all(kw["cwd"] == str(rig.repo) for _, kw in bash_calls)


def test_absent_audit_script_gives_the_default_record(rig):
    assert rig.go()["audit"] == {
        "present": False,
        "exit_code": None,
        "pass": 0,
        "fail": 0,
        "skip": 0,
        "warn": 0,
        "self_test_exit_code": None,
        "tail": "",
    }


def test_present_audit_records_both_runs(rig):
    script = rig.repo / "audit" / "atools-compliance_audit.sh"
    script.parent.mkdir()
    script.write_text("#!/bin/bash\n", encoding="utf-8")

    def handler(cmd, kw):
        if cmd[:2] == ["bash", str(script)]:
            if cmd[2] == "--cursor":
                return _cp(cmd, rc=7, out="pass: 10 warn: 1\n", err="fail: 5 skip: 2\n")
            if cmd[2] == "--self-test":
                return _cp(cmd, rc=9, out="self ok\n")

    rig.run.handler = handler
    report = rig.go()
    assert report["audit"] == {
        "present": True,
        "exit_code": 7,
        "pass": 10,
        "fail": 5,
        "skip": 2,
        "warn": 1,
        "self_test_exit_code": 9,
        "tail": "pass: 10 warn: 1\nfail: 5 skip: 2",
    }
    audit_calls = [(c, kw) for c, kw in rig.run.calls if c[:2] == ["bash", str(script)]]
    assert [c[2] for c, _ in audit_calls] == ["--cursor", "--self-test"]
    assert all(kw["cwd"] == str(rig.repo) for _, kw in audit_calls)


def test_baseline_is_written_when_missing_even_without_refresh(rig):
    report = rig.go(refresh=False)
    text = rig.layout.baseline_file.read_text(encoding="utf-8")
    assert text == json.dumps(report, indent=2) + "\n"
    assert json.loads(text) == report


def test_baseline_is_kept_without_refresh_and_replaced_with_refresh(rig):
    rig.layout.root.mkdir(parents=True, exist_ok=True)
    base = rig.layout.baseline_file
    base.write_text("SENTINEL\n", encoding="utf-8")
    rig.go(refresh=False)
    assert base.read_text(encoding="utf-8") == "SENTINEL\n"
    report = rig.go(refresh=True)
    assert base.read_text(encoding="utf-8") == json.dumps(report, indent=2) + "\n"


def test_baseline_creates_a_missing_root_with_its_parents(rig):
    deep = Layout(rig.tmp / "a" / "b" / "root")
    doctor.run_doctor(deep, refresh=True)
    assert deep.baseline_file.is_file()


def test_baseline_tolerates_an_existing_root(rig):
    rig.layout.root.mkdir(parents=True, exist_ok=True)
    rig.go(refresh=True)
    assert rig.layout.baseline_file.is_file()


def _proof_out(rig):
    po = rig.repo / "proof" / "out"
    po.mkdir(parents=True)
    return po


def test_proof_out_restores_changes_and_removes_new_entries(rig):
    po = _proof_out(rig)
    (po / "keep.txt").write_bytes(b"orig")
    (po / "P-S0-01.log").write_bytes(b"proof-orig")

    def handler(cmd, kw):
        (po / "keep.txt").write_bytes(b"changed")
        (po / "P-S0-01.log").write_bytes(b"proof-changed")
        (po / "new.txt").write_bytes(b"n")
        (po / "newdir").mkdir(exist_ok=True)
        (po / "newdir" / "f").write_bytes(b"n")

    rig.run.handler = handler
    rig.go()
    assert (po / "keep.txt").read_bytes() == b"orig"
    assert (po / "P-S0-01.log").read_bytes() == b"proof-changed"
    assert not (po / "new.txt").exists()
    assert not (po / "newdir").exists()


def test_proof_out_created_during_the_run_is_removed(rig):
    po = rig.repo / "proof" / "out"

    def handler(cmd, kw):
        po.mkdir(parents=True, exist_ok=True)
        (po / "x.log").write_bytes(b"x")

    rig.run.handler = handler
    rig.go()
    assert not po.exists()


def test_cleanup_of_new_directories_ignores_errors(rig):
    rig.mp.setattr(doctor, "shutil", _shutil_proxy(rmtree=_picky_rmtree))
    po = _proof_out(rig)
    (po / "keep.txt").write_bytes(b"orig")

    def handler(cmd, kw):
        (po / "newdir").mkdir(exist_ok=True)
        (po / "newdir" / "f").write_bytes(b"n")

    rig.run.handler = handler
    rig.go()
    assert not (po / "newdir").exists()
    assert (po / "keep.txt").read_bytes() == b"orig"


def test_cleanup_of_a_new_proof_out_ignores_errors(rig):
    rig.mp.setattr(doctor, "shutil", _shutil_proxy(rmtree=_picky_rmtree))
    po = rig.repo / "proof" / "out"

    def handler(cmd, kw):
        po.mkdir(parents=True, exist_ok=True)
        (po / "x").write_bytes(b"x")

    rig.run.handler = handler
    rig.go()
    assert not po.exists()
