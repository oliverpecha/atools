"""Pytest suite for Stage 1 verifier engine (S1-R1, S1-R2, S1-R4..S1-R7, S1-R11, S1-R13).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest


def test_verify_module_importable() -> None:
    """S1-R1: actl.verify must exist and re-export StepResult."""
    try:
        import actl.verify as verify_mod
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R1: actl.verify cannot be imported: {exc}")

    assert hasattr(verify_mod, "StepResult"), "FAIL: S1-R1: actl.verify lacks StepResult"
    assert hasattr(verify_mod, "verify_impl"), "FAIL: S1-R1: actl.verify lacks verify_impl"
    assert hasattr(verify_mod, "run_o1"), "FAIL: S1-R5: actl.verify lacks run_o1"
    assert hasattr(verify_mod, "run_o2"), "FAIL: S1-R6: actl.verify lacks run_o2"


def test_stepresult_to_verification_step() -> None:
    """S1-R1: StepResult.to_verification_step() produces exact 4-key dictionary."""
    try:
        from actl.verify import StepResult
    except ImportError:
        pytest.fail("FAIL: S1-R1: actl.verify missing")

    sr = StepResult(
        id="G3",
        cmd="git diff",
        exit_code=1,
        output_sha256="0" * 64,
        output_tail="failing line",
        duration_ms=45,
        failing_line="failing line",
    )
    d = sr.to_verification_step()
    assert d == {
        "id": "G3",
        "cmd": "git diff",
        "exit_code": 1,
        "output_sha256": "0" * 64,
    }, f"FAIL: S1-R1.2: Unexpected verification step structure: {d}"


def test_o1_staging_outside_worktree(tmp_path: Path) -> None:
    """S1-R4: run_o1 stages oracle files outside worktree and cleans up in finally."""
    try:
        from actl.verify import run_o1
    except ImportError:
        pytest.fail("FAIL: S1-R4: actl.verify missing")

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "init", "-q", str(worktree)], check=True)

    oracle = tmp_path / "oracle"
    proofs = oracle / "proofs"
    proofs.mkdir(parents=True)
    p1 = proofs / "01_pass.sh"
    p1.write_text("#!/usr/bin/env bash\nexit 0\n")
    p1.chmod(0o755)
    probe = oracle / "probe.sh"
    probe.write_text("#!/usr/bin/env bash\nexit 0\n")
    probe.chmod(0o755)

    results = run_o1(oracle, worktree)
    assert len(results) == 2, f"FAIL: S1-R5: Expected 2 steps, got {len(results)}"
    assert all(r.exit_code == 0 for r in results), "FAIL: S1-R5: Expected exit 0 for all steps"

    stage_dir = tmp_path / "worktree.oracle-stage"
    assert not stage_dir.exists(), "FAIL: S1-R4.4: Staging directory not cleaned up"
    assert not (worktree / "proofs").exists(), "FAIL: S1-R4.2: Oracle leaked into worktree"


def test_o2_argv_allowlist(tmp_path: Path) -> None:
    """S1-R6: run_o2 refuses repo_test_cmd not starting with python3 or pytest."""
    try:
        from actl.verify import run_o2
    except ImportError:
        pytest.fail("FAIL: S1-R6: actl.verify missing")

    worktree = tmp_path / "worktree"
    worktree.mkdir()

    with pytest.raises((ValueError, Exception)) as excinfo:
        run_o2(worktree, repo_test_cmd="bash run_tests.sh")
    assert "pytest" in str(excinfo.value) or "python3" in str(excinfo.value) or "allow" in str(excinfo.value).lower(), (
        "FAIL: S1-R6.3: Non-allowlisted command must raise error"
    )


def test_prior_attempt_strictly_four_keys(tmp_path: Path) -> None:
    """S1-R7: prior_attempt.json has strictly four keys."""
    try:
        import actl.schemas as schemas
    except ImportError:
        pytest.fail("FAIL: S1-R7: actl.schemas missing")

    valid_prior = {
        "diff": "diff --git a/file b/file\n",
        "failing_step": "G3",
        "failing_line": "prohibited file added",
        "closures_submitted": 1,
    }
    errs = schemas.validate("prior_attempt", valid_prior)
    assert errs == [], f"FAIL: S1-R7.3: Valid prior_attempt rejected: {errs}"

    invalid_prior = dict(valid_prior)
    invalid_prior["extra_key"] = "forbidden"
    errs_extra = schemas.validate("prior_attempt", invalid_prior)
    assert len(errs_extra) > 0, "FAIL: S1-R7: Extra keys must be rejected in prior_attempt.json"
