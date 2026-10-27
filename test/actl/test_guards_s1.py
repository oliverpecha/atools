"""Pytest suite for Stage 1 guards G1-G6 and run_selftests (S1-R3).

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from test_verify_s1 import REPO_ROOT, TAG, _setup_golden_sandbox


def test_run_selftests_positive_and_negative() -> None:
    """S1-R3.7: run_selftests returns 6 passing StepResults (G1..G6)."""
    try:
        from actl.verify import run_selftests
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R3.7: actl.verify missing: {exc}")

    results = run_selftests()
    assert isinstance(results, list) and len(results) >= 6
    for g in ("G1", "G2", "G3", "G4", "G5", "G6"):
        assert any(g in r.id and r.exit_code == 0 for r in results), f"Missing passing self-test for {g}"


def test_g2_rejects_extra_fields_and_invalid_schema(tmp_path: Path) -> None:
    """S1-R3.2, S1A-11: G2 fails red when closure.json has extra properties or missing required fields."""
    try:
        from actl.verify import check_guards
        from actl.layout import Layout
        import actl.schemas as schemas
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R3.2: actl.verify missing: {exc}")

    sdir, wt = _setup_golden_sandbox(tmp_path, "good.patch")
    layout = Layout(sdir)
    exp = schemas.load_expected()["cases"]["closure_invalid_schema"]["expect"]

    # 1. Missing required 'reason' field
    missing_reason = tmp_path / "missing_reason.json"
    missing_reason.write_text(json.dumps({
        "blocking_step": None,
        "notes": [],
        "backlog": [],
        "solution_key_divergence": None,
    }), encoding="utf-8")
    res1 = check_guards(layout, TAG, wt, closure_path=missing_reason)
    g2_1 = next((r for r in res1 if r.id == "G2"), None)
    assert g2_1 is not None and g2_1.exit_code == 1
    assert exp["failing_line_contains"] in (g2_1.failing_line or "")

    # 2. Extra field rejected by additionalProperties: false (S1A-11)
    extra_field = tmp_path / "extra_field.json"
    extra_field.write_text(json.dumps({
        "reason": "done",
        "blocking_step": None,
        "notes": ["ok"],
        "backlog": [],
        "solution_key_divergence": None,
        "unexpected_extra_key": 123,
    }), encoding="utf-8")
    res2 = check_guards(layout, TAG, wt, closure_path=extra_field)
    g2_2 = next((r for r in res2 if r.id == "G2"), None)
    assert g2_2 is not None and g2_2.exit_code == 1


def test_g4_hollow_test_and_valid_test_detection(tmp_path: Path) -> None:
    """S1-R3.4: G4 on real git repo with thawed test/test_users.py accepts real tests and rejects hollow tests."""
    try:
        from actl.verify import check_guards
        from actl.layout import Layout
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R3.4: actl.verify missing: {exc}")

    sdir, wt = _setup_golden_sandbox(tmp_path, "good.patch")
    layout = Layout(sdir)
    # Thaw test/test_users.py using golden scope override
    scope_override = REPO_ROOT / "fixtures" / "golden" / "sprint" / "scope_overrides" / "bad_testcount.txt"
    (layout.sprint_dir(TAG) / "oracle-003" / "scope.txt").write_text(
        scope_override.read_text(encoding="utf-8"), encoding="utf-8"
    )

    test_file = wt / "test" / "test_users.py"
    base_text = test_file.read_text(encoding="utf-8")
    env = {
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }

    # 1. Positive control: valid test passes G4
    res_ok = check_guards(layout, TAG, wt)
    g4_ok = next((r for r in res_ok if r.id == "G4"), None)
    assert g4_ok is not None and g4_ok.exit_code == 0

    # 2. Negative control: hollow test body fails G4
    test_file.write_text(base_text + "\ndef test_hollow():\n    assert True\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "commit", "-q", "-a", "-m", "add hollow"], env=env, check=True)
    res_bad = check_guards(layout, TAG, wt)
    g4_bad = next((r for r in res_bad if r.id == "G4"), None)
    assert g4_bad is not None and g4_bad.exit_code == 1


def test_g5_secret_scrubbing_and_allowlist(tmp_path: Path) -> None:
    """S1-R3.5: G5 detects secret in bad_secret.patch, scrubs raw value from failing_line, and passes clean diff."""
    try:
        from actl.verify import check_guards
        from actl.layout import Layout
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R3.5: actl.verify missing: {exc}")

    sdir_ok, wt_ok = _setup_golden_sandbox(tmp_path / "ok", "good.patch")
    sdir_bad, wt_bad = _setup_golden_sandbox(tmp_path / "bad", "bad_secret.patch")

    res_ok = check_guards(Layout(sdir_ok), TAG, wt_ok)
    g5_ok = next((r for r in res_ok if r.id == "G5"), None)
    assert g5_ok is not None and g5_ok.exit_code == 0

    res_bad = check_guards(Layout(sdir_bad), TAG, wt_bad)
    g5_bad = next((r for r in res_bad if r.id == "G5"), None)
    assert g5_bad is not None and g5_bad.exit_code == 1
    assert "AKIAIOSFODNN7EXAMPLE" not in (g5_bad.failing_line or "")
    assert "[REDACTED]" in (g5_bad.failing_line or "")


def test_g6_ast_alias_and_regex_fallback(tmp_path: Path) -> None:
    """S1-R3.6: G6 catches aliased os.system calls via AST and forbidden calls via regex."""
    try:
        from actl.verify import check_guards
        from actl.layout import Layout
    except ImportError as exc:
        pytest.fail(f"FAIL: S1-R3.6: actl.verify missing: {exc}")

    sdir, wt = _setup_golden_sandbox(tmp_path, "good.patch")
    layout = Layout(sdir)
    profile_py = wt / "api" / "profile.py"
    profile_py.write_text(
        profile_py.read_text(encoding="utf-8") + "\nimport os as _sneaky_os\n_sneaky_os.system('echo hi')\n",
        encoding="utf-8",
    )
    env = {
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "t@example.test",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "t@example.test",
    }
    subprocess.run(["git", "-C", str(wt), "-c", "core.hooksPath=/dev/null", "commit", "-q", "-a", "-m", "sneaky alias"], env=env, check=True)
    res = check_guards(layout, TAG, wt)
    g6 = next((r for r in res if r.id == "G6"), None)
    assert g6 is not None and g6.exit_code == 1
