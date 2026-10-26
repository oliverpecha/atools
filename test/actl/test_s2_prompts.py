# test/actl/test_s2_prompts.py - P-S2-16: prompts checklist test
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
from pathlib import Path
import pytest

def test_prompts_presence_and_checklist():
    prompts_dir = Path("prompts")
    for req in ("architect.md", "challenger.md", "architect_review.md", "_output_contract.md"):
        f = prompts_dir / req
        if not f.is_file():
            pytest.fail(f"FAIL: S2-R11.1: required prompt file missing: {req}")
