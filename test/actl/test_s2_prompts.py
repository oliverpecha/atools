from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"


def test_prompts_presence_authority_and_single_source_contract():
    required_files = (
        "architect-intake.md",
        "architect-review.md",
        "challenger.md",
        "curator.md",
        "_output_contract.md",
    )
    for req in required_files:
        f = PROMPTS_DIR / req
        assert f.is_file(), f"Missing required prompt: prompts/{req}"
        text = f.read_text(encoding="utf-8").strip()
        assert len(text) >= 50, f"Prompt file prompts/{req} is empty or stubbed"

    contract_text = (PROMPTS_DIR / "_output_contract.md").read_text(encoding="utf-8")
    for token in ("<<<FILE", "<<<END_FILE>>>", "<<<PATCH", "<<<END_PATCH>>>", "<<<<<<< SEARCH", ">>>>>>> REPLACE", "<<<END_RESPONSE bundle=", "fence="):
        assert token in contract_text, f"Missing token {token!r} in _output_contract.md"

    intake_text = (PROMPTS_DIR / "architect-intake.md").read_text(encoding="utf-8")
    assert "Architect" in intake_text or "architect" in intake_text
    assert "solution_key" in intake_text
    assert "never" in intake_text.lower() or "must not" in intake_text.lower()
    assert "<<<END_RESPONSE" not in intake_text

    review_text = (PROMPTS_DIR / "architect-review.md").read_text(encoding="utf-8")
    assert "lock_oracle" in review_text and "revise_oracle" in review_text
    assert "oracle-decision.json" in review_text
    assert "<<<END_RESPONSE" not in review_text

    challenger_text = (PROMPTS_DIR / "challenger.md").read_text(encoding="utf-8")
    for req_tok in ("ACTL_TARGET_CMD", "FAIL:", "probe.sh", "coverage.md", "scope.txt", "oracle-critique.md"):
        assert req_tok in challenger_text, f"challenger.md missing token {req_tok!r}"
    assert "<<<END_RESPONSE" not in challenger_text

    curator_text = (PROMPTS_DIR / "curator.md").read_text(encoding="utf-8")
    assert "Stage 5" in curator_text or "curator" in curator_text.lower()
