
# test/actl/test_s2_prompts.py - P-S2-17: prompts/*.md content checklist & single-source contract (S2-R11, D-S2-12)

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

from **future** import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(**file**).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"

def test_prompts_presence_authority_and_single_source_contract():
"""Proves S2-R11 & D-S2-12: rejects empty prompt files; verifies persona authority statements, prohibitions, ACTL_TARGET_CMD, and single-source _output_contract.md."""
required_files = (
"architect-intake.md",
"architect-review.md",
"challenger.md",
"curator.md",
"_output_contract.md",
)
for req in required_files:
f = PROMPTS_DIR / req
if not f.is_file():
pytest.fail(f"FAIL: S2-R11.1: required prompt file missing: prompts/{req}")
text = f.read_text(encoding="utf-8").strip()
if len(text) < 50:
pytest.fail(f"FAIL: S2-R11.1: prompt file prompts/{req} is empty or stubbed ({len(text)} chars)")

```
contract_text = (PROMPTS_DIR / "_output_contract.md").read_text(encoding="utf-8")
for token in ("<<<FILE", "<<<END_FILE>>>", "<<<PATCH", "<<<END_PATCH>>>", "<<<<<<< SEARCH", ">>>>>>> REPLACE", "<<<END_RESPONSE bundle=", "fence="):
    assert token in contract_text, f"prompts/_output_contract.md missing grammar token {token!r}"

intake_text = (PROMPTS_DIR / "architect-intake.md").read_text(encoding="utf-8")
assert "Architect" in intake_text or "architect" in intake_text
assert "solution_key" in intake_text
assert "never" in intake_text.lower() or "must not" in intake_text.lower(), (
    "architect-intake.md must forbid editing proofs/mutants"
)
assert "<<<END_RESPONSE" not in intake_text, (
    "prompts/_output_contract.md must be the single source of <<<END_RESPONSE (not duplicated in architect-intake.md)"
)

review_text = (PROMPTS_DIR / "architect-review.md").read_text(encoding="utf-8")
assert "lock_oracle" in review_text and "revise_oracle" in review_text
assert "oracle-decision.json" in review_text
assert "<<<END_RESPONSE" not in review_text

challenger_text = (PROMPTS_DIR / "challenger.md").read_text(encoding="utf-8")
for req_tok in ("ACTL_TARGET_CMD", "FAIL:", "probe.sh", "coverage.md", "scope.txt", "oracle-critique.md"):
    assert req_tok in challenger_text, f"challenger.md missing required token {req_tok!r}"
assert "<<<END_RESPONSE" not in challenger_text

curator_text = (PROMPTS_DIR / "curator.md").read_text(encoding="utf-8")
assert "Stage 5" in curator_text or "curator" in curator_text.lower()

```

