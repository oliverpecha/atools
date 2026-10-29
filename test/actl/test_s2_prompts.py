# Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

from pathlib import Path
import re
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"


def _has_prohibition(text: str, *topics: str) -> bool:
    """True when text states a MUST NOT / never prohibition covering all topics."""
    low = text.lower()
    if not any(p in low for p in ("must not", "must never", "never")):
        return False
    return all(t.lower() in low for t in topics)


def _has_reversed_permission(text: str, *topics: str) -> bool:
    """True when text weakens/reverses a prohibition into an allowance for topics."""
    low = text.lower()
    if not all(t.lower() in low for t in topics):
        return False
    return bool(
        re.search(
            r"\b(may|can|should|are allowed to|is allowed to|feel free to)\b.{0,80}"
            r"\b(edit|modify|author|patch|accept|write)\b",
            low,
        )
        or re.search(
            r"\b(edit|modify|author|patch|accept|write)\b.{0,40}"
            r"\b(freely|without approval|without logs|any files)\b",
            low,
        )
    )


def persona_prohibitions_ok(persona: str, text: str) -> bool:
    """Return True iff persona authority prohibitions hold and are not reversed."""
    if _has_reversed_permission(text):
        return False
    if persona in ("architect-intake", "architect-review", "architect"):
        return _has_prohibition(text, "proof") and _has_prohibition(text, "mutant")
    if persona == "challenger":
        return (
            _has_prohibition(text, "spec")
            and _has_prohibition(text, "solution_key")
            and "ACTL_TARGET_CMD" in text
            and "FAIL:" in text
        )
    if persona == "curator":
        # Stage-5 stub: curator must not modify target-repo files in Stage 2.
        return _has_prohibition(text, "file") or _has_prohibition(text, "modif")
    return False


def test_prompts_authority_and_forbidden_prohibitions():
    """Proves R4-06 & S2-R11.2: checks exact authority boundaries and negative mutation controls."""
    intake = (PROMPTS_DIR / "architect-intake.md").read_text(encoding="utf-8")
    review = (PROMPTS_DIR / "architect-review.md").read_text(encoding="utf-8")
    challenger = (PROMPTS_DIR / "challenger.md").read_text(encoding="utf-8")

    # Architect intake & review must forbid authoring/editing proofs and mutants
    for text, name in ((intake, "architect-intake"), (review, "architect-review")):
        assert persona_prohibitions_ok(name, text), f"{name} missing or reversed prohibition"

    # Challenger must forbid authoring/editing spec or solution_key
    assert persona_prohibitions_ok("challenger", challenger)


def test_prompt_prohibition_negative_controls():
    """R4-06: Weakened/reversed persona prohibitions must fail validation."""
    weakened = [
        (
            "curator",
            "As curator you may modify any files in the target repository freely.",
        ),
        (
            "architect",
            "The architect may patch proofs/*.sh and mutants/*.patch without approval.",
        ),
        (
            "challenger",
            "The challenger may accept bundles without logs and may edit the spec freely.",
        ),
    ]
    for persona, text in weakened:
        assert persona_prohibitions_ok(persona, text) is False, (
            f"weakened {persona} prompt must fail validation"
        )
