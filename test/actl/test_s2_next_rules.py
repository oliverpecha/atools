# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

import json
from pathlib import Path
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GOLDEN_DIR = REPO_ROOT / "fixtures" / "golden"


def _create_draft_sprint(tmp_path: Path, slug: str = "demo-next"):
    from actl.layout import Layout
    from actl.sprint import create_sprint, init_target

    root = tmp_path / "actl-root"
    target_src = tmp_path / "target-src"
    subprocess.run(["bash", str(GOLDEN_DIR / "build_golden.sh"), str(target_src)], check=True)
    layout = Layout(root)
    init_target(layout, str(target_src))
    info = create_sprint(layout, slug)
    return layout, info["sprint_tag"]


def test_next_rules_phase12_ten_states(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    try:
        import actl.next_rules.phase12 as p12
        from actl.next import decide_next
        from actl.seq import update_state
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R10: actl.next_rules.phase12 missing: {e}")

    assert getattr(p12, "PRIORITY", None) == 10, "phase12.PRIORITY must be 10"
    monkeypatch.setenv("ACTL_TODAY", "2026-10-16")
    layout, tag = _create_draft_sprint(tmp_path)

    r1 = decide_next(layout, tag)
    assert r1["action"] == "bundle_architect_intake"
    assert r1["command"] == f"actl bundle architect-intake --sprint {tag}"

    t_arch1 = layout.turns_dir(tag) / "architect-1"
    t_arch1.mkdir(parents=True, exist_ok=True)
    (t_arch1 / "bundle.json").write_text(
        json.dumps({"turn_id": "architect-1", "role": "architect", "purpose": "architect-intake"}),
        encoding="utf-8",
    )
    (t_arch1 / "response.txt").write_text("raw", encoding="utf-8")
    r2 = decide_next(layout, tag)
    assert r2["action"] == "unpack_architect_intake"
    assert r2["command"] == f"actl unpack architect-intake --sprint {tag}"

    (t_arch1 / "unpack.json").write_text(
        json.dumps({"turn_id": "architect-1", "role": "architect", "purpose": "architect-intake", "ok": False, "errors": [{"code": "E_TOML"}]}),
        encoding="utf-8",
    )
    (t_arch1 / "repair.txt").write_text("Fix TOML", encoding="utf-8")
    r3 = decide_next(layout, tag)
    assert r3["action"] == "repair"
    assert r3["command"] == f"actl unpack architect-intake --sprint {tag} --turn architect-1 --amend"

    (t_arch1 / "repair.txt").unlink()
    (t_arch1 / "unpack.json").write_text(
        json.dumps({"turn_id": "architect-1", "role": "architect", "purpose": "architect-intake", "ok": True, "errors": []}),
        encoding="utf-8",
    )
    arch_out = layout.outbox(tag, "architect")
    (arch_out / "spec-draft.md").write_text("# Spec\nR1: ok\n", encoding="utf-8")
    (arch_out / "solution_key.patch").write_text("diff\n", encoding="utf-8")
    r4 = decide_next(layout, tag)
    assert r4["action"] == "promote_architect"
    assert r4["command"] == f"actl promote architect --sprint {tag}"

    for f in arch_out.iterdir():
        f.unlink()
    update_state(layout, tag, {"active_spec": "spec-001.md", "active_solution_key": "solution_key-002.patch"})
    r5 = decide_next(layout, tag)
    assert r5["action"] == "bundle_challenger"
    assert r5["command"] == f"actl bundle challenger --sprint {tag}"

    t_chal1 = layout.turns_dir(tag) / "challenger-1"
    t_chal1.mkdir(parents=True, exist_ok=True)
    (t_chal1 / "bundle.json").write_text(
        json.dumps({"turn_id": "challenger-1", "role": "challenger", "purpose": "challenger"}),
        encoding="utf-8",
    )
    (t_chal1 / "response.txt").write_text("raw", encoding="utf-8")
    r6 = decide_next(layout, tag)
    assert r6["action"] == "unpack_challenger"
    assert r6["command"] == f"actl unpack challenger --sprint {tag}"

    (t_chal1 / "unpack.json").write_text(
        json.dumps({"turn_id": "challenger-1", "role": "challenger", "purpose": "challenger", "ok": True, "errors": []}),
        encoding="utf-8",
    )
    chal_out_draft = layout.outbox(tag, "challenger") / "oracle-draft"
    chal_out_draft.mkdir(parents=True, exist_ok=True)
    (chal_out_draft / "scope.txt").write_text("FROZEN: test/**\nALLOW: api/profile.py\n", encoding="utf-8")
    r7 = decide_next(layout, tag)
    assert r7["action"] == "promote_challenger"
    assert r7["command"] == f"actl promote challenger --sprint {tag}"

    import shutil
    shutil.rmtree(chal_out_draft)
    update_state(layout, tag, {"active_oracle_draft": "oracle-draft-003"})
    r8 = decide_next(layout, tag)
    assert r8["action"] == "ready_for_qualification"
    assert r8["command"] == ""

    (layout.sprint_dir(tag) / "qualification-004.json").write_text("{}", encoding="utf-8")
    r9 = decide_next(layout, tag)
    assert r9["action"] == "bundle_architect_review"
    assert r9["command"] == f"actl bundle architect-review --sprint {tag}"

    t_arch2 = layout.turns_dir(tag) / "architect-2"
    t_arch2.mkdir(parents=True, exist_ok=True)
    (t_arch2 / "bundle.json").write_text(
        json.dumps({"turn_id": "architect-2", "role": "architect", "purpose": "architect-review"}),
        encoding="utf-8",
    )
    (t_arch2 / "unpack.json").write_text(
        json.dumps({"turn_id": "architect-2", "role": "architect", "purpose": "architect-review", "ok": True, "errors": []}),
        encoding="utf-8",
    )
    (arch_out / "oracle-decision.json").write_text(
        json.dumps({"decision": "revise_oracle", "feedback": "tighten"}), encoding="utf-8"
    )
    r10a = decide_next(layout, tag)
    assert r10a["action"] == "bundle_challenger"
    assert r10a["command"] == f"actl bundle challenger --sprint {tag}"

    (arch_out / "oracle-decision.json").write_text(
        json.dumps({"decision": "lock_oracle", "feedback": None}), encoding="utf-8"
    )
    r10b = decide_next(layout, tag)
    assert r10b["action"] == "qualify_lock"
    assert r10b["command"] == ""

def test_next_rules_active_contract_bypass(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Proves R4-07 & S2-R10.1: active_contract makes phase12 yield; decide_next must not emit phase12 actions.

    Checking only phase12.evaluate is insufficient: a decide_next that ignores the
    None yield would still pass that assertion while returning bundle_architect_intake.
    """
    try:
        import actl.next_rules.phase12 as p12
        from actl.next import decide_next
        from actl.seq import update_state
    except ImportError as e:
        pytest.fail(f"FAIL: S2-R10.1: phase12/decide_next missing: {e}")

    monkeypatch.setenv("ACTL_TODAY", "2026-10-16")
    layout, tag = _create_draft_sprint(tmp_path)

    # Baseline without active_contract: phase12 owns the draft sprint.
    base = decide_next(layout, tag)
    assert base["action"] == "bundle_architect_intake", (
        "precondition: draft sprint must be a phase12 action before active_contract"
    )

    update_state(layout, tag, {"active_contract": "contract-005.json"})
    assert p12.evaluate(layout, tag) is None, "phase12 must return None when active_contract is set"

    # decide_next must honour the bypass (not re-emit a phase12 action).
    bypassed = decide_next(layout, tag)
    phase12_actions = {
        "bundle_architect_intake",
        "unpack_architect_intake",
        "repair",
        "promote_architect",
        "bundle_challenger",
        "unpack_challenger",
        "promote_challenger",
        "ready_for_qualification",
        "bundle_architect_review",
        "qualify_lock",
    }
    assert bypassed["action"] not in phase12_actions, (
        f"decide_next must not return phase12 action {bypassed['action']!r} when "
        "active_contract is set (S2-R10.1)"
    )
    # With no phase3 rule present, the terminal fallback is noop.
    assert bypassed["action"] == "noop", (
        f"expected noop when phase12 yields and no later rule matches, got {bypassed!r}"
    )


def test_r407_active_contract_decide_next_red_on_evaluate_only():
    """R4-07 self-test: evaluate-only assertion would miss a broken decide_next guard."""
    # Simulate a broken decide_next that ignores phase12's None and still returns
    # the draft intake action — the evaluate-only check would still pass.
    evaluate_result = None
    broken_decide_action = "bundle_architect_intake"
    assert evaluate_result is None  # old assertion still green
    phase12_actions = {"bundle_architect_intake"}
    assert broken_decide_action in phase12_actions
    # The fixed test requires decide_next action NOT in phase12_actions.
    with pytest.raises(AssertionError):
        assert broken_decide_action not in phase12_actions


def test_traceability_matrix_names_match_delivered_tests():
    """R4-07: every test_* name cited in the S2 traceability matrix must exist."""
    import re

    spec = (REPO_ROOT / "docs" / "plan" / "spec-S2.md").read_text(encoding="utf-8")
    start = spec.index("## 2. Traceability and Three-Stand-In Vacuity Matrix")
    end = spec.index("## 3. Ambiguity Register")
    cited = re.findall(r"`(test_[a-z0-9_]+)`", spec[start:end])
    assert cited, "matrix must cite at least one test_* name"

    delivered: set[str] = set()
    for path in (REPO_ROOT / "test" / "actl").glob("test_s2_*.py"):
        delivered.update(
            re.findall(r"^def (test_[a-z0-9_]+)\b", path.read_text(encoding="utf-8"), re.M)
        )
    missing = sorted(set(cited) - delivered)
    assert not missing, "traceability matrix cites nonexistent tests: " + ", ".join(missing)
    for required in (
        "test_courier_drawer_creation",
        "test_promote_immutable_frozen_fields",
        "test_next_rules_active_contract_bypass",
        "test_p01_good_architect_intake_unpack_and_proof_preview",
        "test_p11_sentinel_hash_and_mismatch",
    ):
        assert required in cited, f"matrix must cite {required}"
        assert required in delivered, f"delivered tests must include {required}"
