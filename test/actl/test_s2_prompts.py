from __future__ import annotations

from pathlib import Path
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"


def test_prompts_authority_and_forbidden_prohibitions():
    """Proves R4-06 & S2-R11.2: checks exact authority boundaries and negative mutation controls."""
    intake = (PROMPTS_DIR / "architect-intake.md").read_text(encoding="utf-8")
    review = (PROMPTS_DIR / "architect-review.md").read_text(encoding="utf-8")
    challenger = (PROMPTS_DIR / "challenger.md").read_text(encoding="utf-8")

    # Architect intake & review must forbid authoring/editing proofs and mutants
    for text, name in ((intake, "architect-intake"), (review, "architect-review")):
        assert "proof" in text.lower() and ("never" in text.lower() or "must not" in text.lower()), f"{name} missing proof prohibition"
        assert "mutant" in text.lower() and ("never" in text.lower() or "must not" in text.lower()), f"{name} missing mutant prohibition"

    # Challenger must forbid authoring/editing spec or solution_key
    assert "spec" in challenger.lower() and ("never" in challenger.lower() or "must not" in challenger.lower())
    assert "solution_key" in challenger.lower() and ("never" in challenger.lower() or "must not" in challenger.lower())
    assert "ACTL_TARGET_CMD" in challenger and "FAIL:" in challenger
