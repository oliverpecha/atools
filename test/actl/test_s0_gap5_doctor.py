# Authored-by: Gemini Flash 3.8 High (Google), as reported by the Owner, 2026-10-26
# Revised-by: Vela-OPB, 2026-10-26, applying the GPT 6.1 Sol review conditions (sys.path restore, Layout guard, direct rc asserts, narrow patches, hermetic doctor)
"""actl.doctor: baseline default, linger parsing, audit aggregation, proof/out restore."""
import inspect
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


def _shutil_proxy(which):
    return types.SimpleNamespace(which=which, rmtree=shutil.rmtree)


@pytest.fixture(autouse=True)
def _hermetic(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, "getpass", types.SimpleNamespace(getuser=lambda: "tester"))
    monkeypatch.setattr(doctor, "shutil", _shutil_proxy(lambda name: None))
    monkeypatch.setattr(doctor, "SYNC_TARGETS", {})
    monkeypatch.setenv("ATOOLS_LOG_DIR", str(tmp_path / "logs"))
    monkeypatch.setenv("ATOOLS_SESSION_DIR", str(tmp_path / "sess"))


def _setup_fake_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    (repo / "VERSION").write_text("v0.1.4\n", encoding="utf-8")
    return repo


def _ok(cmd, stdout="", stderr=""):
    return subprocess.CompletedProcess(cmd, returncode=0, stdout=stdout, stderr=stderr)


def test_doctor_default_refresh_is_false(tmp_path, monkeypatch):
    sig = inspect.signature(doctor.run_doctor)
    assert sig.parameters["refresh"].default is False

    monkeypatch.setattr(doctor, "REPO_ROOT", _setup_fake_repo(tmp_path))
    monkeypatch.setattr(doctor, "_run", lambda cmd, **kw: _ok(cmd))

    layout = Layout(tmp_path / "actl_root")
    layout.root.mkdir(parents=True, exist_ok=True)
    sentinel_text = '{\n  "custom": "sentinel_value"\n}\n'
    layout.baseline_file.write_text(sentinel_text, encoding="utf-8")

    doctor.run_doctor(layout)
    assert layout.baseline_file.read_text(encoding="utf-8") == sentinel_text


def test_doctor_linger_state_from_loginctl_returncode(tmp_path, monkeypatch):
    monkeypatch.setattr(doctor, "REPO_ROOT", _setup_fake_repo(tmp_path))
    monkeypatch.setattr(
        doctor,
        "shutil",
        _shutil_proxy(lambda name: "/bin/loginctl" if name == "loginctl" else None),
    )

    def fake_run(cmd, **kw):
        if len(cmd) >= 2 and cmd[0] == "loginctl" and cmd[1] == "show-user":
            return _ok(cmd, stdout="Linger=yes\n")
        return _ok(cmd)

    monkeypatch.setattr(doctor, "_run", fake_run)

    report = doctor.run_doctor(Layout(tmp_path / "actl_root"), refresh=True)
    assert report["linger_state"] == "Linger=yes"


def test_doctor_audit_counts_concatenates_stdout_and_stderr(tmp_path, monkeypatch):
    fake_repo = _setup_fake_repo(tmp_path)
    audit_script = fake_repo / "audit" / "atools-compliance_audit.sh"
    audit_script.parent.mkdir(parents=True, exist_ok=True)
    audit_script.write_text("#!/bin/bash\n", encoding="utf-8")
    monkeypatch.setattr(doctor, "REPO_ROOT", fake_repo)

    def fake_run(cmd, **kw):
        if "--cursor" in cmd:
            return _ok(
                cmd,
                stdout="compliance summary pass: 10 warn: 1\n",
                stderr="audit anomalies fail: 5 skip: 2\n",
            )
        return _ok(cmd)

    monkeypatch.setattr(doctor, "_run", fake_run)

    report = doctor.run_doctor(Layout(tmp_path / "actl_root"), refresh=True)
    assert report["audit"]["present"] is True
    assert report["audit"]["pass"] == 10
    assert report["audit"]["fail"] == 5
    assert report["audit"]["warn"] == 1
    assert report["audit"]["skip"] == 2


def test_doctor_proof_out_restores_modified_file(tmp_path, monkeypatch):
    fake_repo = _setup_fake_repo(tmp_path)
    proof_out = fake_repo / "proof" / "out"
    proof_out.mkdir(parents=True, exist_ok=True)
    target_file = proof_out / "audit_cache.txt"
    initial_bytes = b"original_snapshot_content"
    target_file.write_bytes(initial_bytes)
    monkeypatch.setattr(doctor, "REPO_ROOT", fake_repo)

    def fake_run_mutating(cmd, **kw):
        target_file.write_bytes(b"mutated_snapshot_content")
        return _ok(cmd)

    monkeypatch.setattr(doctor, "_run", fake_run_mutating)

    doctor.run_doctor(Layout(tmp_path / "actl_root"), refresh=True)
    assert target_file.read_bytes() == initial_bytes
