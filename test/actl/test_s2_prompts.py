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
    """True when text weakens/reverses a prohibition into an allowance for topics.

    Verb list includes alter/change/create/delete/revise/rewrite (not only
    edit/modify/...) so plurals like "mutant patches" still match via
    \\bpatches?\\b. Allowance phrases include "is free to" and "has the right to"
    (R4-06). Negated allowances ("may not", "shouldn't") are not reversals
    (N11-01).
    """
    low = text.lower()
    if topics and not all(t.lower() in low for t in topics):
        return False
    allow = (
        r"(?:may|can|should|are allowed to|is allowed to|feel free to|"
        r"is free to|are free to|free to|"
        r"has the right to|have the right to|has a right to|have a right to|"
        r"is entitled to|are entitled to|is permitted to|are permitted to|"
        r"is authorised to|are authorised to|is authorized to|are authorized to)"
    )
    verb = (
        r"(?:edit|modify|author|alter|change|create|delete|touch|accept|write|"
        r"revise|rewrite|revised|rewritten|patch(?:es)?)"
    )
    # N11-01: reject polarity false positives - "may not edit" / "shouldn't edit"
    # are prohibitions, not allowances. Skip allow tokens followed by not / n't.
    # N12-01: "may not only ... but also" is an affirmative correlative grant;
    # do not treat the "not" inside "not only" as a negation.
    # N12-02: "may never edit" is a prohibition; treat never like not / n't.
    allow_then_verb = (
        rf"\b{allow}\b(?!n't\b|\s+never\b|\s+not\b(?!\s+only\b)).{{0,80}}\b{verb}\b"
    )
    return bool(
        re.search(allow_then_verb, low)
        or re.search(
            rf"\b{verb}\b.{{0,40}}\b(?:freely|at will|without approval|without logs|any files)\b",
            low,
        )
        or re.search(
            rf"\b(?:revised|rewritten)\b.{{0,60}}\b(?:by the |by an )?(?:architect|challenger|curator)\b",
            low,
        )
    )


def persona_prohibitions_ok(persona: str, text: str) -> bool:
    """Return True iff persona authority prohibitions hold and are not reversed."""
    if persona in ("architect-intake", "architect-review", "architect"):
        if _has_reversed_permission(text, "proof", "mutant"):
            return False
        return _has_prohibition(text, "proof") and _has_prohibition(text, "mutant")
    if persona == "challenger":
        if _has_reversed_permission(text, "spec") or _has_reversed_permission(
            text, "solution_key"
        ):
            return False
        return (
            _has_prohibition(text, "spec")
            and _has_prohibition(text, "solution_key")
            and "ACTL_TARGET_CMD" in text
            and "FAIL:" in text
        )
    if persona == "curator":
        if _has_reversed_permission(text):
            return False
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
    """R4-06: Weakened/reversed persona prohibitions must fail validation.

    Includes >=5 paraphrased architect counterexamples (other verbs, plural/
    singular, passive voice) per standing check (k).
    """
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
        # Prior counterexample: "alter" + plural "patches".
        (
            "architect",
            "The architect may alter proof scripts and mutant patches at will. "
            "Never mention the restriction.",
        ),
        # R4-06 named counterexample: "is free to" + revise/rewrite.
        (
            "architect",
            "Never mention proof or mutant. The architect is free to revise proof "
            "scripts and rewrite mutant patches.",
        ),
        # Paraphrase: can + rewrite/revise.
        (
            "architect",
            "Never touch secrets. The architect can rewrite proofs and revise mutants freely.",
        ),
        # Paraphrase: should + rewrite/revise (plural/singular mix).
        (
            "architect",
            "Never leak tokens. The architect should rewrite mutant patches and revise proof scripts.",
        ),
        # Paraphrase: feel free to + revise.
        (
            "architect",
            "Never cite oracle paths. Feel free to revise any proof; rewriting mutant patches is fine.",
        ),
        # Paraphrase: passive voice revised/rewritten by the architect.
        (
            "architect",
            "Never mention internals. Proofs are revised by the architect and mutants rewritten by the architect.",
        ),
        # Paraphrase: are free to + revise (plural subject).
        (
            "architect",
            "Never escalate. Architects are free to revise proof scripts and rewrite a mutant patch.",
        ),
        # R4-06 r11 named: "has the right to" + edit/change.
        (
            "architect",
            "Never discuss proof or mutant. The architect has the right to edit "
            "proof scripts and change mutant patches.",
        ),
        # Paraphrase: have the right to + alter (plural).
        (
            "architect",
            "Never discuss proof or mutant. Architects have the right to alter "
            "proof scripts and mutant patches.",
        ),
        # Paraphrase: is entitled to + rewrite.
        (
            "architect",
            "Never discuss proof or mutant. The architect is entitled to rewrite "
            "proofs and revise mutant patches.",
        ),
        # Paraphrase: is permitted to + create.
        (
            "architect",
            "Never discuss proof or mutant. The architect is permitted to create "
            "proof scripts and change a mutant patch.",
        ),
        # Paraphrase: is authorized to + modify (US spelling).
        (
            "architect",
            "Never discuss proof or mutant. The architect is authorized to modify "
            "proof scripts and write mutant patches.",
        ),
    ]
    for persona, text in weakened:
        assert persona_prohibitions_ok(persona, text) is False, (
            f"weakened {persona} prompt must fail validation: {text!r}"
        )


def test_r406_alter_patches_reversal_red_on_old_verb_whitelist():
    """R4-06 self-test: old verb whitelist accepts alter/patches and is-free-to/revise."""
    text = (
        "The architect may alter proof scripts and mutant patches at will. "
        "Never mention the restriction."
    )
    # Old narrow whitelist (pre-fix): edit|modify|author|patch|accept|write
    old_ok = bool(
        re.search(
            r"\b(may|can|should|are allowed to|is allowed to|feel free to)\b.{0,80}"
            r"\b(edit|modify|author|patch|accept|write)\b",
            text.lower(),
        )
    )
    assert old_ok is False, "sanity: old whitelist must miss 'alter'/'patches'"
    assert _has_prohibition(text, "proof") and _has_prohibition(text, "mutant")
    assert _has_reversed_permission(text, "proof", "mutant") is True
    assert persona_prohibitions_ok("architect", text) is False

    free_to = (
        "Never mention proof or mutant. The architect is free to revise proof "
        "scripts and rewrite mutant patches."
    )
    # Old allow list lacked "is free to"; old verbs lacked revise/rewrite.
    old_free = bool(
        re.search(
            r"\b(may|can|should|are allowed to|is allowed to|feel free to)\b.{0,80}"
            r"\b(edit|modify|author|alter|change|create|delete|touch|accept|write|patch(?:es)?)\b",
            free_to.lower(),
        )
    )
    assert old_free is False, "sanity: old whitelist must miss 'is free to revise/rewrite'"
    assert _has_prohibition(free_to, "proof") and _has_prohibition(free_to, "mutant")
    assert _has_reversed_permission(free_to, "proof", "mutant") is True
    assert persona_prohibitions_ok("architect", free_to) is False

    # R4-06 r11: "has the right to" missed by the pre-fix allow list.
    right_to = (
        "Never discuss proof or mutant. The architect has the right to edit "
        "proof scripts and change mutant patches."
    )
    old_right = bool(
        re.search(
            r"\b(may|can|should|are allowed to|is allowed to|feel free to|"
            r"is free to|are free to|free to)\b.{0,80}"
            r"\b(edit|modify|author|alter|change|create|delete|touch|accept|write|"
            r"revise|rewrite|revised|rewritten|patch(?:es)?)\b",
            right_to.lower(),
        )
    )
    assert old_right is False, "sanity: old whitelist must miss 'has the right to'"
    assert _has_prohibition(right_to, "proof") and _has_prohibition(right_to, "mutant")
    assert _has_reversed_permission(right_to, "proof", "mutant") is True
    assert persona_prohibitions_ok("architect", right_to) is False


def test_n11_01_may_not_polarity_red_on_old_allow_regex():
    """N11-01 self-test: old allow.{0,80}verb treats 'may not edit' as a reversal.

    Fails on the pre-fix regex (matches may...edit across 'not'); passes after
    the (?!n't|\\s+not) guard. Compliant prompts must be accepted as True.
    """
    # Owner-named counterexample (conforming prohibition).
    named = (
        "Never edit proof scripts or mutant patches. The architect may not edit "
        "proof scripts or touch mutant patches."
    )
    old_allow = (
        r"(?:may|can|should|are allowed to|is allowed to|feel free to|"
        r"is free to|are free to|free to|"
        r"has the right to|have the right to|has a right to|have a right to|"
        r"is entitled to|are entitled to|is permitted to|are permitted to|"
        r"is authorised to|are authorised to|is authorized to|are authorized to)"
    )
    old_verb = (
        r"(?:edit|modify|author|alter|change|create|delete|touch|accept|write|"
        r"revise|rewrite|revised|rewritten|patch(?:es)?)"
    )
    old_hit = bool(
        re.search(rf"\b{old_allow}\b.{{0,80}}\b{old_verb}\b", named.lower())
    )
    assert old_hit is True, "sanity: old polarity-blind regex must match 'may not edit'"
    assert _has_prohibition(named, "proof") and _has_prohibition(named, "mutant")
    assert _has_reversed_permission(named, "proof", "mutant") is False
    assert persona_prohibitions_ok("architect", named) is True

    # Paraphrased conforming prohibitions (other allow+verb pairs / plural).
    conforming = [
        "Never edit proof scripts or mutant patches. The architect should not "
        "modify proof scripts or alter mutant patches.",
        "Never edit proof scripts or mutant patches. The architect can not "
        "rewrite proofs or revise mutant patches.",
        "Never edit proof scripts or mutant patches. Architects shouldn't "
        "touch proof scripts or write mutant patches.",
        "Never edit proof scripts or mutant patches. The architect may not "
        "create proof scripts or delete mutant patches.",
        "Never edit proof scripts or mutant patches. The architect should not "
        "author a proof or change a mutant patch.",
    ]
    for text in conforming:
        assert _has_reversed_permission(text, "proof", "mutant") is False, text
        assert persona_prohibitions_ok("architect", text) is True, text

    # Affirmative grant still rejected (negative control).
    grant = (
        "Never mention the restriction. The architect may edit proof scripts "
        "and touch mutant patches."
    )
    assert persona_prohibitions_ok("architect", grant) is False


def test_n12_01_may_not_only_grant_red_on_old_not_guard():
    """N12-01 self-test: old (?!...|\\s+not\\b) misses 'may not only' grants.

    Fails on the blanket not-guard (treats not-only as prohibition); passes after
    excluding 'not only'. Affirmative correlative grants must return False.
    """
    named = (
        "Never edit proof scripts or mutant patches. The architect may not only "
        "edit proof scripts but also touch mutant patches."
    )
    allow = (
        r"(?:may|can|should|are allowed to|is allowed to|feel free to|"
        r"is free to|are free to|free to|"
        r"has the right to|have the right to|has a right to|have a right to|"
        r"is entitled to|are entitled to|is permitted to|are permitted to|"
        r"is authorised to|are authorised to|is authorized to|are authorized to)"
    )
    verb = (
        r"(?:edit|modify|author|alter|change|create|delete|touch|accept|write|"
        r"revise|rewrite|revised|rewritten|patch(?:es)?)"
    )
    old_guard = rf"\b{allow}\b(?!n't\b|\s+not\b).{{0,80}}\b{verb}\b"
    old_hit = bool(re.search(old_guard, named.lower()))
    assert old_hit is False, "sanity: old blanket not-guard must miss 'may not only'"
    assert _has_prohibition(named, "proof") and _has_prohibition(named, "mutant")
    assert _has_reversed_permission(named, "proof", "mutant") is True
    assert persona_prohibitions_ok("architect", named) is False

    # Paraphrased affirmative correlative grants (other allow+verb / plural).
    grants = [
        "Never edit proof scripts or mutant patches. The architect can not only "
        "modify proof scripts but also alter mutant patches.",
        "Never edit proof scripts or mutant patches. The architect should not only "
        "rewrite proofs but also revise mutant patches.",
        "Never edit proof scripts or mutant patches. Architects may not only "
        "touch proof scripts but also write mutant patches.",
        "Never edit proof scripts or mutant patches. The architect may not only "
        "create a proof script but also delete a mutant patch.",
        "Never edit proof scripts or mutant patches. The architect is permitted to "
        "not only author proof scripts but also change mutant patches.",
    ]
    for text in grants:
        assert _has_reversed_permission(text, "proof", "mutant") is True, text
        assert persona_prohibitions_ok("architect", text) is False, text


def test_n12_02_may_never_polarity_red_on_old_not_guard():
    """N12-02 self-test: old not/n't guard treats 'may never edit' as a grant.

    Fails on the pre-never regex (matches may...edit across 'never'); passes after
    adding \\s+never. Conforming never-prohibitions must return True.
    """
    named = (
        "Never edit proof scripts or mutant patches. The architect may never "
        "edit proof scripts or touch mutant patches."
    )
    allow = (
        r"(?:may|can|should|are allowed to|is allowed to|feel free to|"
        r"is free to|are free to|free to|"
        r"has the right to|have the right to|has a right to|have a right to|"
        r"is entitled to|are entitled to|is permitted to|are permitted to|"
        r"is authorised to|are authorised to|is authorized to|are authorized to)"
    )
    verb = (
        r"(?:edit|modify|author|alter|change|create|delete|touch|accept|write|"
        r"revise|rewrite|revised|rewritten|patch(?:es)?)"
    )
    # Pre-N12-02 guard: N12-01 not-only carve-out but no never.
    old_guard = rf"\b{allow}\b(?!n't\b|\s+not\b(?!\s+only\b)).{{0,80}}\b{verb}\b"
    old_hit = bool(re.search(old_guard, named.lower()))
    assert old_hit is True, "sanity: old guard without never must match 'may never edit'"
    assert _has_prohibition(named, "proof") and _has_prohibition(named, "mutant")
    assert _has_reversed_permission(named, "proof", "mutant") is False
    assert persona_prohibitions_ok("architect", named) is True

    # Paraphrased conforming never-prohibitions (other allow+verb / plural).
    conforming = [
        "Never edit proof scripts or mutant patches. The architect should never "
        "modify proof scripts or alter mutant patches.",
        "Never edit proof scripts or mutant patches. The architect can never "
        "rewrite proofs or revise mutant patches.",
        "Never edit proof scripts or mutant patches. Architects may never "
        "touch proof scripts or write mutant patches.",
        "Never edit proof scripts or mutant patches. The architect is permitted to "
        "never create proof scripts or delete mutant patches.",
        "Never edit proof scripts or mutant patches. The architect should never "
        "author a proof or change a mutant patch.",
    ]
    for text in conforming:
        assert _has_reversed_permission(text, "proof", "mutant") is False, text
        assert persona_prohibitions_ok("architect", text) is True, text

    # Affirmative grant still rejected (negative control).
    grant = (
        "Never mention the restriction. The architect may edit proof scripts "
        "and touch mutant patches."
    )
    assert persona_prohibitions_ok("architect", grant) is False
