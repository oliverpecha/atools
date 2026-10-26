# Layout transition owner approval

- **Date:** 2026-10-25
- **Approver:** Owner
- **Scope:** Decisions L-1 through L-11 as locked in `docs/plan/layout-transition-memo.md`; PB-4 and D-28 approval
- **Approval given:** Owner approved the layout-transition memo (PB-4, D-28) on 2026-10-25. Formal logging of this record accompanies the transition push to `main` after Part A authoring, cross-family delta review, and Part B implementation.
- **Conditions:**
  - Cross-family delta review of the Part A authoring diff before merge
  - PB-1 re-verified (amended suites red against current code for memo-scoped checks only; golden and mutation self-checks green)
- **Status:** delta review verdict: ACCEPT WITH FINDINGS (provisional, 2026-10-25); DC-1 to DC-14 resolved (LT-A2), oracle residue fixed (LT-A3, LT-A4); no second reviewer pass on the fixes, they were verified by Owner-run gates

## Decisions covered (L-1 to L-11)

| ID | Summary |
|---|---|
| L-1 | One `ACTL_ROOT` with three lifetimes: `records/` STORAGE, `sprints/` TRANSIENT, `profiles/` PERSISTENT; `repos/` holds targets |
| L-2 | Names: `repos`, `records`, `sprints`, `mailboxes`, `workspaces`, `profiles`, `tools`, `signoffs` |
| L-3 | Sprint closeout is archive-then-delete into `records/<repo>/<tag>/closeout/` |
| L-4 | Courier is transport, not storage |
| L-5 | `ev-NNN.json` → `verification-NNN.json`; `qual-NNN.json` → `qualification-NNN.json` |
| L-6 | Top-level `tools/` (PB-2 immutable) |
| L-7 | `docs/plan/signoffs/` for judgment-based acceptances |
| L-8 | `profiles/<persona>` is persistent HOME; `actl init` writes `profiles/README.md` |
| L-9 | `ACTL_ROOT` is the only root name; sprint tags keep `YYYY-MM-DD-slug` |
| L-10 | `Layout(root, repo="target-repo")` with repo guard (exit 3) |
| L-11 | Revisit `Layout(root, repo)` vs explicit repo arg at Stage 4 (O-16) |

## Owner ratification (2026-10-25) [R]

The Owner replied "ratify all" to the seven proposed decisions:
1. JSON key `handoff_dir` renamed to `mailboxes_dir`.
2. Profile directory mode 0755.
3. `profiles/README.md` written by `actl init` only (L-8).
4. `sprint-proposal` does not reject `repo`.
5. Layout property names `records`, `profile`, `mailboxes`.
6. Mutants that need implementation code are a part B gate (D-29, `tools/mutate.py`).
7. The contract object's `qual` field keeps its name; only file names, kinds and schema names are renamed.

## Verification pointers

- Delta verdict: `layout-transition-delta-challenge-verdict.md`; resolution of DC-1 to DC-14: `layout-transition-delta-resolution.md`.
- Part B gates, mutation seed 53, demo and known limitations: `layout-transition-part-b-verification.md`.
- Ratification and verification are logged with the single transition push to `main`.
