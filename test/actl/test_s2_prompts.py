from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"


def test_prompts_authority_and_forbidden_prohibitions():
    """Proves F-09 & S2-R11.2: asserts role-specific authority and exact forbidden prohibitions."""
    intake = (PROMPTS_DIR / "architect-intake.md").read_text(encoding="utf-8")
    assert "proof" in intake.lower() and ("never" in intake.lower() or "must not" in intake.lower())
    assert "mutant" in intake.lower() and ("never" in intake.lower() or "must not" in intake.lower())

    review = (PROMPTS_DIR / "architect-review.md").read_text(encoding="utf-8")
    assert "lock_oracle" in review and "revise_oracle" in review
    assert "oracle-decision.json" in review

    challenger = (PROMPTS_DIR / "challenger.md").read_text(encoding="utf-8")
    assert "spec" in challenger.lower() and ("never" in challenger.lower() or "must not" in challenger.lower())
    assert "solution_key" in challenger.lower() and ("never" in challenger.lower() or "must not" in challenger.lower())
    assert "ACTL_TARGET_CMD" in challenger and "FAIL:" in challenger
