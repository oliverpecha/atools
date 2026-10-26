# Runbook: Layout transition, part A3 (test and proof rename residue) - workstream `LT-A3`

- **Branch / worktree:** `wip/layout-amend-a` in `~/atools-lt-a`, on top of `117d7e3`. New commits only; no amend, no rebase, no push, no merge, no `--no-verify`.
- **Why:** the A2 sweep (`/tmp/lt-a2-scratch/gLAIkJ/c4-sweep-final.txt`) shows gating tests still use the OLD artifact kinds and file names as valid values: `"ev"`, `"qual"`, `ev-NNN.json`, `schemas.validate("qual", ...)`, `seq.reserve(..., "ev")`. After Part B renames the kinds (L-5) these tests would fail, and the Part B implementer may not edit `test/actl` (PB-2). The A2 report justified them as "intentional reds / killers"; that is wrong for positive uses. Fix them now.
- **Boundary and tags:** as in `docs/plan/runbooks/layout-transition-a-authoring.md` sections 1 and 2. Allowed: `test/actl/`, `proof/`, `fixtures/`, `docs/plan/`. Forbidden: `src/actl/*.py`, `schemas/*.json`, `tools/`, `audit/`, `hooks/`, `rules/`, `bin/`, `src/router`, `src/sessions`, `src/core`, `engines`. Test and proof edits use `(WI-S0-PROOF)`. Commit format: `type(scope): summary (WI-S0-PROOF)` then `Why:` (bare SHAs), `What changed:` with one `- <file>: <change>` bullet per file, `Result:` with metrics. Run every command with `</dev/null`.
- **Ratified decisions (Owner, 2026-10-25), do not reopen:** the contract object's `qual` FIELD stays (`qual: {seq, id, sha256}`); only file names, kinds and schema names are renamed. `handoff_dir` becomes `mailboxes_dir`. Stage 1 prose shorthand `ev` in the addendum stays for the Stage 1 authoring thread.

## Tasks

**R1 Inventory.** Run, over `test/actl proof fixtures`:
`git grep -nE '"(ev|qual)"|\b(ev|qual)-[0-9{]|validate\("(ev|qual)"|\b(ev|qual)\.json|reserve\([^)]*"(ev|qual)"' -- test/actl proof fixtures`
Save the raw output in the report. Known files: `test_p05_seq.py`, `test_s0_gap2_reconstruct.py`, `test_s0_gap2_schemas.py`, `test_s0_gap2_seed23.py`, `test_s0_gap_conformance.py`, `test_s0_gap_ids.py`, `test_s0_gap_schemas_oneof.py`. Look for more (also `proof/stage0/*.sh`, `fixtures/golden/build_golden.sh`, helpers, conftest).

**R2 Rename.** Positive uses become `verification` / `qualification` (kind strings, schema names, `verification-NNN.json`, `qualification-NNN.json`). Do NOT rename: the contract field `qual`, Python variables named `ev`, fixtures that are contract objects.

**R3 Old names become negatives.** In `test_s0_gap_ids.py` BAD_KINDS and in the schema-kind tests, add `"ev"` and `"qual"` as REJECTED kinds/schemas (the old names must be refused). Keep every existing assertion at least as strong; no skips, no xfail, no loosened bounds, no deleted parametrizations. Parametrized bounds on `exit_code` (0..255, null) and `seq` minimum 1 must carry over unchanged to `verification` / `qualification`.

**R4 Legacy script.** Do not edit `proof/stage0/diff_equiv_seed11.py` (historical differential, no gate runs it). Add a one-line note in the report that it is non-gating and must not be run after Part B.

**R5 Re-pin.** Re-pin the changed files in `proof/stage0/P-S0-02.sh` with an idempotent python script printing `ok`/`SKIPPED` per edit (the replacement contains the marker `# LT-A3 pin refresh applied`). Separate `WI-S0-PROOF` commit, last. If `INTERFACES.md` is untouched, its pin stays.

**R6 Report** `/tmp/lt-a3-report.md` (not committed): R1 raw output before and after, per-file change list, and for every pytest failure in the touched test files the exception line, each tied to a memo item (for example `Unknown schema kind: verification`). Then stop.

## Delivery gate (paste raw output)

1. `git merge-base --is-ancestor 117d7e3 HEAD` exits 0; new commits only; each has exactly one valid tag; hook accepted them.
2. `git diff --name-only 117d7e3..HEAD` shows only `test/actl/`, `proof/`, `fixtures/`; forbidden-path count 0.
3. The R1 grep run again: every remaining hit is one of: contract `qual` field, a Python variable, or an explicit negative (old name expected to be rejected), each listed with its justification. Zero positive uses.
4. `bash proof/run_suite_actl_s0.sh` exits 1 with 0 Environment; every red is listed with its memo reason; the red set may grow only with a stated memo reason.
5. `bash proof/run_suite_exit_code.sh`, `bash proof/stage0/P-S0-27.sh`, `proof/stage0/golden_selfcheck.sh`, `proof/stage0/selfcheck_mutations.sh` exit 0 (mutants still 23 or more).
6. `bash audit/atools-compliance_audit.sh --cursor | tail -2` shows 0 failed.
7. P-S0-02 passes with the new pins; `git status --short` empty.
