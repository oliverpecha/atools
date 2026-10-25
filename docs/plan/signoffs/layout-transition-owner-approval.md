# Layout transition owner approval

- **Date:** 2026-10-25
- **Approver:** Owner
- **Scope:** Decisions L-1 through L-11 as locked in `docs/plan/layout-transition-memo.md`; PB-4 and D-28 approval
- **Approval given:** Owner approved the layout-transition memo (PB-4, D-28) on 2026-10-25. Formal logging of this record accompanies the transition push to `main` after Part A authoring, cross-family delta review, and Part B implementation.
- **Conditions:**
  - Cross-family delta review of the Part A authoring diff before merge
  - PB-1 re-verified (amended suites red against current code for memo-scoped checks only; golden and mutation self-checks green)
- **Status:** delta review verdict: pending

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
