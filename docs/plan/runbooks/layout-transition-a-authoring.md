# Runbook: Layout transition, part A (authoring) - workstream `LT-A`

- **Workstream:** `LT-A` (branch `wip/layout-amend-a`, worktree `~/atools-lt-a`)
- **Specification:** `docs/plan/layout-transition-memo.md`. Read it completely first. For the items it locks (L-1 to L-11), the memo wins over the Design and the addendum.
- **Designated gates:** section 5. Unlike a normal implementation run, this run ends with RED suites on purpose.
- **Commit tag format:** every commit subject ends with exactly one tag. `(WI-IFACE)` for `src/actl/INTERFACES.md`. `(WI-S0-SPEC)` for the Design, the addendum and `docs/plan/spec-S0.md`. `(WI-S0-PROOF)` for tests, proofs and fixtures. `(WI-DOCS-n)` for the Handoff Prompts, the Guide and `docs/plan/signoffs/`, where `n` is the next free number from `git log --format=%s | grep -o 'WI-DOCS-[0-9]*' | sort -V | tail -1`. Never mix areas in one commit. Follow the commit-message hook (`hooks/commit-msg`): `type(scope): summary (WI-tag)`, then `Why:`, `What changed:`, `Result:`.

## 1. Role and boundary

You are an authoring agent. You change specification text, interface text, tests, proofs and fixtures so that they describe the new layout. You do NOT implement it. When you finish, the amended suites fail against the current code, and that is the goal (PB-1 for this amendment). Part B, a separate runbook after an independent review, makes them green.

Skill override: if a skill or rule tells you not to edit proofs or fixtures, or to iterate until a suite passes, it does not apply to this runbook. This runbook's scope overrides it. The git-safety rules still apply in full: wip branches only, no push, no `--no-verify`.

## 2. Hard rules

1. Work only in `~/atools-lt-a` on `wip/layout-amend-a`. Never commit on `main`. Never push.
2. Allowed to edit: `docs/design/`, `docs/plan/` (except the historical records below), `docs/guide/`, `src/actl/INTERFACES.md`, `test/actl/`, `proof/`, `fixtures/`.
3. Forbidden: `src/actl/*.py`, `schemas/*.json`, `bin/`, `install.sh`, `src/router`, `src/sessions`, `src/core`, `engines`, `hooks`, `rules`, `audit/`, `tools/`. Part B changes the implementation.
4. Historical records are never rewritten: `docs/plan/signoffs/stage0-*`, `docs/plan/runbooks/*` (except this workstream's own runbooks), `docs/proposals/archive/*`.
5. Zero-destructive: never `rm` a tracked file. Rename with `git mv`.
6. Report ambiguities. Never resolve a conflict with the Design silently: record it under "Proposed decisions" in your report.
7. No LLM-dependent check in a gating suite. Every git call in helpers and proofs stays hermetic, like the existing ones.
8. Scratch space is `mktemp -d`. Unique names for sessions and temp directories (PB-6).

## 3. Tasks, in order

**T0 Baseline.** Before any edit, run and save the pass/fail lists to `/tmp/lt-a-baseline/`: `bash proof/run_suite_actl_s0.sh`, `python3 -m pytest test/actl -q`, `bash proof/stage0/P-S0-27.sh`, the golden self-check and the mutation self-check in `proof/stage0/` (run `ls proof proof/stage0` first and use the real script names), `bash proof/run_suite_exit_code.sh`, and `bash audit/atools-compliance_audit.sh --cursor`.

**T1 Rename map.** From memo section 3 and L-1 to L-11, write the complete old-to-new map, including every file, function, field and schema name you find with `git grep`. It goes into your report.

**T2 Design (`docs/design/`).** Section 1.5 directory tree and accounts text, and Invariant C text that says `~architect`: new tree and names. Replace `/srv/agent-graph` with `ACTL_ROOT` as an example value. Section 4 naming: `verification-NNN.json`, `qualification-NNN.json`. Add the closeout archive policy and the `closeout.md` contents (memo section 5). Describe `profiles`. Add an Appendix A revision-log entry. Tag `WI-S0-SPEC`.

**T3 Addendum.** Update S0-R3 (Layout), S0-R4 (`actl init --name`, repo selection), S0-R5 (reconstruct paths), S0-R7 (schema names, kinds, a `repo` field in `sprint` and `state`), S2-R1, S2-R2, S2-R4 and S2-R9 (courier copy, `unpack --drawer`, promote targets), and the Stage 1 and Stage 2 text where it names old paths. Add `tools` to the PB-2 immutable list everywhere it is spelled out. Record memo L-1 to L-11 as decided items, using the next free D numbers. Add open item O-16 (section 9.2) and the Stage 4 summary line (section 8.1) as the memo specifies. Also record the deferred `closeouts.tsv` index (memo section 5) as a Stage 5 item in the section 8.1 summary. Tag `WI-S0-SPEC`.

**T4 `docs/plan/spec-S0.md`.** It carries the rulings since commit 2bb1307. Update paths. Add requirement text for `Layout(root, repo="target-repo")`, the `repo` guard, `Layout.profile`, and the `profiles/README.md` that `actl init` writes. Tag `WI-S0-SPEC`.

**T5 `src/actl/INTERFACES.md`.** Update the human-readable signatures and the fenced `interfaces.json` block together. Keep existing names unless the memo renames the concept. Propose names for the renamed properties and list them in "Proposed decisions". Add `Layout.__init__(root, repo="target-repo")` and `Layout.profile`. Add the kinds `verification` and `qualification` and the schema list. Append an Owner Amendment Note at the bottom (see T8). Tag `WI-IFACE`.

**T6 Tests, proofs, fixtures.** Update every path and name assertion. Add tests for: repo-scoped paths with the default name working, two repos with the same tag not colliding, the wrong-repo guard rejecting a mismatched Layout (exit 3), `actl init` writing `profiles/README.md`, and the renamed artifact kinds. Update the proof for the tree (P-S0-03) and the schema proofs (P-S0-08, P-S0-26, P-S0-27 as needed). Rename the golden artifacts and update `build_golden.sh --install-sprint` and the `expected.d` fragments. Every new rule gets at least one mutant in the mutation self-check. Refresh the pinned blob hashes in P-S0-02 with an idempotent script that prints `ok` or `SKIPPED` per edit. Tag `WI-S0-PROOF`.

**T7 Prompts and Guide.** In `docs/plan/actl_Handoff_Prompts.md`, add the courier paragraph (memo section 4) to the COMMON BLOCK and update the names. In `docs/guide/actl_Guide.md`, update only statements that become false. Tag `WI-DOCS-n`.

**T8 Sign-off drafts.** Draft `docs/plan/signoffs/layout-transition-owner-approval.md`: date, approver, scope (L-1 to L-11), the PB-4 and D-28 approval as given by the Owner on 2026-10-25, the conditions (cross-family delta review before merge, PB-1 re-verified), and "delta review verdict: pending". Draft the Owner Amendment Note for `INTERFACES.md` with the same content. Tag `WI-DOCS-n` and `WI-IFACE`.

**T9 Sweep.** Run `git grep -nE 'actl-repo|handoff/|homes|ev-[0-9]|qual-[0-9]|ev\.json|qual\.json|target_repo\(' -- . ':!docs/proposals' ':!docs/plan/signoffs' ':!docs/plan/runbooks'`. Every remaining hit needs a one-line justification in your report, or a fix.

## 4. Do not

Implement anything in `src/actl`. Edit `schemas/*.json`. Merge. Push. Start part B.

## 5. Gates (run last, paste exact output into the report)

1. `bash proof/run_suite_actl_s0.sh` must exit 1. Every FAIL line names a missing feature from the memo, with zero harness or environment errors.
2. Compare against the T0 baseline: every check that turned red maps to a memo item. Nothing outside the amendment's scope turned red.
3. `bash proof/run_suite_exit_code.sh`, `bash proof/stage0/P-S0-27.sh`, the golden self-check and the mutation self-check must exit 0.
4. `bash audit/atools-compliance_audit.sh --cursor` must still show 0 failed.
5. `git diff --name-only main..HEAD` lists only allowed paths from section 2.
6. Every commit subject on the branch ends with exactly one valid WI tag.

## 6. Report

Write `/tmp/lt-a-report.md` (not committed): changed files grouped by tag, the rename map and its completeness check, the baseline versus after table, "Proposed decisions" and ambiguities, the gate outputs, and the T9 sweep results. Then stop.
