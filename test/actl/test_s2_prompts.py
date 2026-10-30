# Authored-by: R15 method change - Cursor Agent, tier auto (underlying model not disclosed);
# prior rounds: Gemini Flash 3.8 (Google; Owner-attested 2026-10-28), model family: Gemini
from __future__ import annotations

from pathlib import Path
import re
import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
PROMPTS_DIR = REPO_ROOT / "prompts"
SPEC_PATH = REPO_ROOT / "docs" / "plan" / "spec-S2.md"

_CANONICAL_MARKER = "<!-- s2-r11-canonical -->"
_AUTH_HEADING = re.compile(r"(?m)^## Authority\s*$")
_NEXT_H2 = re.compile(r"(?m)^##\s+")
_CANON_LINE = re.compile(
    r"^(ARCHITECT|CHALLENGER)\s*\([^)]*\):\s*(.*)$"
)
_MD_EMPHASIS = re.compile(r"[`*_]+")


def _has_prohibition(text: str, *topics: str) -> bool:
    """True when text states a MUST NOT / never prohibition covering all topics."""
    low = text.lower()
    if not any(p in low for p in ("must not", "must never", "never")):
        return False
    return all(t.lower() in low for t in topics)


def _normalize_authority_body(text: str) -> str:
    """Whitespace-insensitive; markdown backticks and emphasis ignored."""
    cleaned = _MD_EMPHASIS.sub("", text)
    return " ".join(cleaned.split())


def _load_canonical_authority() -> dict[str, str]:
    """Read ARCHITECT/CHALLENGER bodies from the spec fenced canonical block."""
    spec = SPEC_PATH.read_text(encoding="utf-8")
    m = re.search(
        rf"```[^\n]*\n{_CANONICAL_MARKER}\n(.*?)```",
        spec,
        re.S,
    )
    if not m:
        raise AssertionError(
            f"missing {_CANONICAL_MARKER!r} fenced block in {SPEC_PATH}"
        )
    out: dict[str, str] = {}
    for line in m.group(1).splitlines():
        lm = _CANON_LINE.match(line.strip())
        if not lm:
            continue
        key = "architect" if lm.group(1) == "ARCHITECT" else "challenger"
        out[key] = lm.group(2).strip()
    if "architect" not in out or "challenger" not in out:
        raise AssertionError("canonical block missing ARCHITECT or CHALLENGER line")
    return out


def _authority_bodies(text: str) -> list[str]:
    """Bodies of every section headed exactly '## Authority'."""
    bodies: list[str] = []
    for m in _AUTH_HEADING.finditer(text):
        start = m.end()
        nxt = _NEXT_H2.search(text, start)
        end = nxt.start() if nxt else len(text)
        bodies.append(text[start:end])
    return bodies


def _authority_matches(text: str, persona_key: str) -> bool:
    bodies = _authority_bodies(text)
    if len(bodies) != 1:
        return False
    canonical = _load_canonical_authority()[persona_key]
    return _normalize_authority_body(bodies[0]) == _normalize_authority_body(canonical)


def persona_prohibitions_ok(persona: str, text: str) -> bool:
    """Return True iff persona authority requirements hold.

    Architect/challenger: exactly one ## Authority section whose normalized body
    equals the canonical text from docs/plan/spec-S2.md (S2-R11.2).
    Curator: Stage-5 stub still checked via _has_prohibition only.
    """
    if persona in ("architect-intake", "architect-review", "architect"):
        return _authority_matches(text, "architect")
    if persona == "challenger":
        return _authority_matches(text, "challenger")
    if persona == "curator":
        # Stage-5 stub: curator must not modify target-repo files in Stage 2.
        return _has_prohibition(text, "file") or _has_prohibition(text, "modif")
    return False


def _minimal_prompt(persona_key: str) -> str:
    body = _load_canonical_authority()[persona_key]
    return f"## Authority\n\n{body}\n"


def test_prompts_authority_and_forbidden_prohibitions():
    """Proves S2-R11.2: each persona prompt has the canonical ## Authority section."""
    intake = (PROMPTS_DIR / "architect-intake.md").read_text(encoding="utf-8")
    review = (PROMPTS_DIR / "architect-review.md").read_text(encoding="utf-8")
    challenger = (PROMPTS_DIR / "challenger.md").read_text(encoding="utf-8")

    for text, name in ((intake, "architect-intake"), (review, "architect-review")):
        assert persona_prohibitions_ok(name, text), f"{name} missing canonical Authority"

    assert persona_prohibitions_ok("challenger", challenger)


def test_canonical_authority_positive_controls():
    """One positive control per persona: minimal prompt with canonical Authority."""
    for persona, key in (
        ("architect", "architect"),
        ("architect-intake", "architect"),
        ("architect-review", "architect"),
        ("challenger", "challenger"),
    ):
        text = _minimal_prompt(key)
        assert persona_prohibitions_ok(persona, text) is True, persona

    # Curator still uses prohibition presence (Stage 5 stub).
    curator_ok = (
        "Stage 5 stub. The curator MUST NOT modify any files in the target repository."
    )
    assert persona_prohibitions_ok("curator", curator_ok) is True


def test_canonical_authority_fixed_negative_controls():
    """Fixed negatives: each mutation of the canonical Authority must return False."""
    canon = _load_canonical_authority()["architect"]
    must_not = (
        "The Architect MUST NOT author or edit proofs/*.sh or mutants/*.patch."
    )
    assert must_not in canon

    deleted = canon.replace(must_not, "").strip()
    may = canon.replace("MUST NOT", "MAY")
    should_not = canon.replace("MUST NOT", "should not")
    reversed_must = canon.replace(
        "MUST NOT author or edit proofs/*.sh or mutants/*.patch.",
        "MUST author or edit proofs/*.sh.",
    )
    paraphrase = (
        "## Authority\n\nThe Architect authors the usual drafts. "
        "The Architect is forbidden to edit proofs and mutants.\n"
    )
    renamed = f"## Role bounds\n\n{canon}\n"
    two_sections = f"## Authority\n\n{canon}\n\n## Authority\n\n{canon}\n"
    permissive_inside = (
        f"## Authority\n\n{canon} The architect may also edit proofs/*.sh.\n"
    )
    empty = ""

    cases = [
        ("MUST NOT deleted", f"## Authority\n\n{deleted}\n"),
        ("MUST NOT -> MAY", f"## Authority\n\n{may}\n"),
        ("MUST NOT -> should not", f"## Authority\n\n{should_not}\n"),
        ("reversed MUST author", f"## Authority\n\n{reversed_must}\n"),
        ("heading renamed", renamed),
        ("two Authority sections", two_sections),
        ("permissive sentence inside Authority", permissive_inside),
        ("paraphrase is-forbidden-to", paraphrase),
        ("empty file", empty),
    ]
    for label, text in cases:
        assert persona_prohibitions_ok("architect", text) is False, label


def test_historical_counterexamples_are_non_canonical_negatives():
    """Rounds 4-14 named strings kept; former 'conforming' wording is non-canonical."""
    # Affirmative grants / reversals (always negatives).
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
        (
            "architect",
            "The architect may alter proof scripts and mutant patches at will. "
            "Never mention the restriction.",
        ),
        (
            "architect",
            "Never mention proof or mutant. The architect is free to revise proof "
            "scripts and rewrite mutant patches.",
        ),
        (
            "architect",
            "Never touch secrets. The architect can rewrite proofs and revise mutants freely.",
        ),
        (
            "architect",
            "Never leak tokens. The architect should rewrite mutant patches and revise proof scripts.",
        ),
        (
            "architect",
            "Never cite oracle paths. Feel free to revise any proof; rewriting mutant patches is fine.",
        ),
        (
            "architect",
            "Never mention internals. Proofs are revised by the architect and mutants rewritten by the architect.",
        ),
        (
            "architect",
            "Never escalate. Architects are free to revise proof scripts and rewrite a mutant patch.",
        ),
        (
            "architect",
            "Never discuss proof or mutant. The architect has the right to edit "
            "proof scripts and change mutant patches.",
        ),
        (
            "architect",
            "Never discuss proof or mutant. Architects have the right to alter "
            "proof scripts and mutant patches.",
        ),
        (
            "architect",
            "Never discuss proof or mutant. The architect is entitled to rewrite "
            "proofs and revise mutant patches.",
        ),
        (
            "architect",
            "Never discuss proof or mutant. The architect is permitted to create "
            "proof scripts and change a mutant patch.",
        ),
        (
            "architect",
            "Never discuss proof or mutant. The architect is authorized to modify "
            "proof scripts and write mutant patches.",
        ),
        (
            "architect",
            "Never mention the restriction. The architect may edit proof scripts "
            "and touch mutant patches.",
        ),
        # N12-01 / N13-01 / N14-02 correlative grants
        (
            "architect",
            "Never edit proof scripts or mutant patches. The architect may not only "
            "edit proof scripts but also touch mutant patches.",
        ),
        (
            "architect",
            "Never edit proof scripts or mutant patches. The architect is permitted "
            "to not just edit proof scripts but also touch mutant patches.",
        ),
        (
            "architect",
            "Never edit proof scripts or mutant patches. The architect may not merely "
            "edit proof scripts but also touch mutant patches.",
        ),
        # N14-01 second case: ban phrase governing decline-to-edit (affirmative)
        (
            "architect",
            "Never edit proof scripts or mutant patches. The architect may under no "
            "circumstances decline to edit proof scripts or touch mutant patches.",
        ),
    ]
    for persona, text in weakened:
        assert persona_prohibitions_ok(persona, text) is False, text

    # Former "conforming prohibition" cases: non-canonical wording, not permissions.
    non_canonical_wording = [
        # N11-01
        "Never edit proof scripts or mutant patches. The architect may not edit "
        "proof scripts or touch mutant patches.",
        # N11-01 paraphrases
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
        # N12-02
        "Never edit proof scripts or mutant patches. The architect may never "
        "edit proof scripts or touch mutant patches.",
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
        # N13-02
        "Never edit proof scripts or mutant patches. The architect may under no "
        "circumstances edit proof scripts or touch mutant patches.",
        "Never edit proof scripts or mutant patches. The architect should under "
        "no circumstances modify proof scripts or alter mutant patches.",
        "Never edit proof scripts or mutant patches. The architect can in no way "
        "rewrite proofs or revise mutant patches.",
        "Never edit proof scripts or mutant patches. Architects may on no account "
        "touch proof scripts or write mutant patches.",
        "Never edit proof scripts or mutant patches. The architect is permitted to "
        "under no conditions create proof scripts or delete mutant patches.",
        "Never edit proof scripts or mutant patches. The architect should in no "
        "event author a proof or change a mutant patch.",
        # N14-01 first case (punctuated ban) - non-canonical wording, not a permission
        "Never edit proof scripts or mutant patches. The architect may, under no "
        "circumstances, edit proof scripts or touch mutant patches.",
    ]
    for text in non_canonical_wording:
        assert persona_prohibitions_ok("architect", text) is False, (
            "non-canonical wording must fail: " + text
        )


def test_method_no_reversed_permission_helper():
    """Method self-test: heuristic _has_reversed_permission is gone."""
    mod = sys.modules[__name__]
    assert not hasattr(mod, "_has_reversed_permission")
    assert "_has_reversed_permission" not in globals()


def test_method_one_word_flip_rejects():
    """Method self-test: changing one word inside canonical Authority -> False."""
    body = _load_canonical_authority()["architect"]
    flipped = body.replace("MUST NOT", "MUST N0T", 1)
    assert flipped != body
    text = f"## Authority\n\n{flipped}\n"
    assert persona_prohibitions_ok("architect", text) is False


def test_n14_01_n14_02_closed_by_canonical_match():
    """N14-01/N14-02: heuristic counterexamples fail; canonical match still passes."""
    # N14-01 first case was "conforming" under the regex; non-canonical now -> False
    punctuated = (
        "Never edit proof scripts or mutant patches. The architect may, under no "
        "circumstances, edit proof scripts or touch mutant patches."
    )
    # N14-01 second case: decline-to-edit grant
    decline = (
        "Never edit proof scripts or mutant patches. The architect may under no "
        "circumstances decline to edit proof scripts or touch mutant patches."
    )
    # N14-02: not merely correlative grant
    merely = (
        "Never edit proof scripts or mutant patches. The architect may not merely "
        "edit proof scripts but also touch mutant patches."
    )
    for text in (punctuated, decline, merely):
        assert persona_prohibitions_ok("architect", text) is False, text

    assert persona_prohibitions_ok("architect", _minimal_prompt("architect")) is True
