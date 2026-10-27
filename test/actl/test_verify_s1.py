"""Pytest suite for Stage 1 verifier engine (S1-R1, S1-R2, S1-R4..S1-R7, S1-R11, S1-R13).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
TAG = "2026-10-16_public-profiles"


def _setup_golden_sandbox(tmp_path: Path, patch_name: str | None = "good.patch") -> tuple[Path, Path]:
    """Install a real hermetic golden sprint and candidate worktree in tmp_path."""
    sdir = tmp_path / "actl_root"
    sdir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["bash", str(REPO_ROOT / "fixtures" / "golden" / "build_golden.sh"), "--install-sprint", str(sdir), "--tag", TAG],
        check=True,
        capture_output=True,
    )
    wt = sdir / "sprints" / "target-repo" / TAG / "workspaces" / "implementer-006"
    wt.parent.mkdir(parents=True, exist_ok=True)
    env = {
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_AUTHOR_DATE": "2026-01-02T00:00:00+0000",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@example.test",
        "GIT_COMMITTER_DATE": "2026-01-02T00:00:00+0000",
    }
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "clone", "-q", "--local", "--no-hardlinks", str(sdir / "repos" / "target-repo"), str(wt)],
        env=env,
        check=True,
    )
    subprocess.run(["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "checkout", "-q", "-b", "wip/006"], env=env, check=True)
    if patch_name:
        patch_path = REPO_ROOT / "fixtures" / "golden" / "implementations" / patch_name
        subprocess.run(["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "apply", str(patch_path)], env=env, check=True)
        subprocess.run(["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "add", "-A"], env=env, check=True)
        subprocess.run(
            ["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "commit", "-q", "-m", f"feat(actl): apply {patch_name} (WI-S1-TEST)"],
            env=env,
            check=True,
        )
    return sdir, wt


def test_verify_module_and_schema_reexport() -> None:
    """S1-R1.1: actl.verify exports verify_impl, run_o1, run_o2, check_guards, run_selftests, and re-exports StepResult."""
    try:
        import actl.verify as verify_mod
        from actl.schemas import StepResult as OriginalStepResult
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R1.1: actl.verify cannot be imported: {exc}")

    assert getattr(verify_mod, "StepResult", None) is OriginalStepResult, "FAIL: S1-R1.1: StepResult must be re-exported from actl.schemas"
    for fn in ("verify_impl", "check_guards", "run_selftests", "run_o1", "run_o2"):
        assert callable(getattr(verify_mod, fn, None)), f"FAIL: S1-R1: {fn} missing in actl.verify"


def test_stepresult_field_defaults_and_conversion() -> None:
    """S1-R1.1, S1-R1.2: StepResult field defaults and conversion to 4-key dict."""
    try:
        from actl.verify import StepResult
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R1.1: actl.verify missing: {exc}")

    sr = StepResult(id="G1", cmd="manifest_check", exit_code=0, output_sha256="a" * 64)
    assert sr.output_tail == ""
    assert sr.duration_ms == 0
    assert sr.failing_line is None
    assert sr.to_verification_step() == {
        "id": "G1",
        "cmd": "manifest_check",
        "exit_code": 0,
        "output_sha256": "a" * 64,
    }


def test_verification_parent_and_stamping_linkage(tmp_path: Path) -> None:
    """S1-R1.4, S1-R7.2: verify_impl stamps valid closure into runs/closure-006.json and links verification.parent."""
    try:
        from actl.verify import verify_impl
        from actl.layout import Layout
        import actl.schemas as schemas
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R1.4: actl.verify missing: {exc}")

    sdir, wt = _setup_golden_sandbox(tmp_path, "good.patch")
    layout = Layout(sdir)
    closure_file = tmp_path / "closure.json"
    closure_file.write_text(json.dumps({
        "reason": "done",
        "blocking_step": None,
        "notes": ["all tests pass"],
        "backlog": [],
        "solution_key_divergence": None,
    }), encoding="utf-8")

    res = verify_impl(layout, TAG, closure_path=closure_file, worktree=wt)
    assert res.get("exit_code") == 0, f"FAIL: S1-R1.4: Expected green verification, got {res}"
    assert res.get("parent") == "closure-006.json", f"FAIL: S1-R1.4: Expected parent='closure-006.json', got {res.get('parent')}"
    stamped_closure = layout.runs_dir(TAG) / "closure-006.json"
    assert stamped_closure.is_file(), "FAIL: S1-R7.2: Stamped closure-006.json was not written to runs_dir"
    stamped_doc = json.loads(stamped_closure.read_text(encoding="utf-8"))
    assert schemas.validate("closure", stamped_doc) == []
    assert stamped_doc.get("kind") == "closure" and stamped_doc.get("seq") == 6 and stamped_doc.get("parent") == "contract-005.json"


def test_no_closure_and_blocked_closure_verification(tmp_path: Path) -> None:
    """S1-R1.4, S1-R3.2: verify_impl with closure_path=None vs early/confirmed blocked closures."""
    try:
        from actl.verify import verify_impl
        from actl.layout import Layout
        from actl.seq import read_state, update_state
        import actl.schemas as schemas
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R1.4: actl.verify missing: {exc}")

    sdir, wt_null = _setup_golden_sandbox(tmp_path, None)  # null base fails O1:01_public.sh
    layout = Layout(sdir)
    exp_cases = schemas.load_expected()["cases"]

    # 1. closure_path=None -> parent is None, closures_submitted stays 0
    res_none = verify_impl(layout, TAG, closure_path=None, worktree=wt_null)
    assert res_none.get("parent") is None
    assert read_state(layout, TAG)["closures_submitted"] == 0

    # 2. Blocked closure submitted too early (closures_submitted == 1 < min_attempts_before_block == 2) -> fails G2
    blocked_closure = tmp_path / "blocked.json"
    blocked_closure.write_text(json.dumps({
        "reason": "blocked",
        "blocking_step": "O1:01_public.sh",
        "notes": ["R1 conflicts with locked schema"],
        "backlog": ["clarify R1"],
        "solution_key_divergence": {"requirement_id": "R1", "rationale": "schema locked"},
    }), encoding="utf-8")

    res_early = verify_impl(layout, TAG, closure_path=blocked_closure, worktree=wt_null)
    assert res_early.get("exit_code") == 1
    assert res_early.get("failing_step") == exp_cases["closure_blocked_early"]["expect"]["failing_step"]
    assert exp_cases["closure_blocked_early"]["expect"]["failing_line_contains"] in (res_early.get("failing_line") or "")
    assert read_state(layout, TAG)["status"] == "running"

    # 3. Second blocked closure (closures_submitted reaches 2 >= min_attempts_before_block) -> confirmed blocked_check, status='hold'
    res_valid_block = verify_impl(layout, TAG, closure_path=blocked_closure, worktree=wt_null)
    assert res_valid_block.get("stage") == "blocked_check"
    assert res_valid_block.get("failing_step") == exp_cases["closure_blocked_valid"]["expect"]["failing_step"]
    assert read_state(layout, TAG)["status"] == "hold"


def test_halt_precedence_over_session_flags(tmp_path: Path) -> None:
    """S1-R2.2, S1-R2.4: G1 oracle tamper halt takes precedence over session_info hard_cap=True."""
    try:
        from actl.verify import verify_impl
        from actl.layout import Layout
        from actl.seq import read_state
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R2.2: actl.verify missing: {exc}")

    sdir, wt = _setup_golden_sandbox(tmp_path, "good.patch")
    layout = Layout(sdir)

    # Inject real 1-byte tamper into active oracle probe.sh
    probe_path = layout.sprint_dir(TAG) / "oracle-003" / "probe.sh"
    probe_path.write_bytes(probe_path.read_bytes() + b"\n# tamper\n")

    res = verify_impl(
        layout,
        TAG,
        worktree=wt,
        session_info={"name": "impl-006", "exit_code": 124, "hard_cap": True, "lost": False, "log_sha256": None},
    )
    assert res.get("exit_code") is None, f"FAIL: S1-R2.2: Halt must set verification.exit_code = None, got {res}"
    assert res.get("halt") == {"reason": "integrity_mismatch"}, f"FAIL: S1-R2.2: Expected integrity_mismatch halt, got {res.get('halt')}"
    st = read_state(layout, TAG)
    assert st["attempts"]["implementer"] == 0, "FAIL: S1-R2.2: Halt must not consume an implementer attempt"
    assert st["status"] == "hold", "FAIL: S1-R2.2: Halt must set sprint status to 'hold'"


def test_failing_line_sanitization_rules() -> None:
    """S1-R1.7, O-8: failing_line strips ANSI CSI and OSC sequences, replaces control chars, and truncates to 300 chars."""
    try:
        from actl.verify import sanitize_failing_line
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R1.7: sanitize_failing_line missing in actl.verify: {exc}")

    raw = (
        "\x1b]0;Window Title\x07"
        "\x1b[31;1mFAIL:\x1b[0m\tline1\r\n"
        "bad\x00char\x7fhere "
        + ("Z" * 350)
    )
    cleaned = sanitize_failing_line(raw)
    assert "\x1b" not in cleaned and "Window Title" not in cleaned
    assert "\r" not in cleaned and "\n" not in cleaned and "\t" not in cleaned
    assert "bad?char?here" in cleaned
    assert cleaned.startswith("FAIL: line1 bad?char?here ")
    assert len(cleaned) == 300


def test_o2_command_grammar_validation(tmp_path: Path) -> None:
    """S1-R6.2: run_o2 strictly requires pytest or python3 -m pytest and raises ValueError on bad commands."""
    try:
        from actl.verify import run_o2
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R6: actl.verify missing: {exc}")

    _sdir, wt = _setup_golden_sandbox(tmp_path, "good.patch")

    # Positive control
    ok_steps = run_o2(wt, repo_test_cmd="python3 -m pytest test -q -rf")
    assert len(ok_steps) == 1 and ok_steps[0].exit_code == 0

    # Negative controls: must raise ValueError specifically (not ImportError or generic Exception)
    for disallowed in ["bash run.sh", "python3 test.py", "pytest; echo evil", "cat /etc/passwd", ""]:
        with pytest.raises(ValueError):
            run_o2(wt, repo_test_cmd=disallowed)
