# Runbook: Layout transition, part B (implementation) - workstream `LT-B`

- **Branch / worktree:** create `wip/layout-b` in `~/atools-lt-b` from `wip/layout-int` at `68e2e96` (the integration merge of part A, WI-DOCS-18). Work only there. Never touch `~/atools-lt-a`, `~/atools-lt-int`, `main`. No push, no merge, no `--no-verify`, no `rm` of tracked files (`git mv`).
- **Specification (authority, in this order):** `docs/plan/layout-transition-memo.md` (L-1 to L-11 locked), `src/actl/INTERFACES.md`, `docs/plan/spec-S0.md`, the addendum requirements S0-R3, S0-R4, S0-R5, S0-R7, and the tests. The tests and proofs are the oracle: you make them green by changing the implementation. You never change an oracle.
- **Ratified by the Owner (2026-10-25), do not reopen:** JSON key `handoff_dir` becomes `mailboxes_dir`; profile directories are mode 0755; `profiles/README.md` is written by `actl init` only (not by `ensure_base_tree`); `sprint-proposal` does not reject a `repo` field; Layout property names `records`, `profile`, `mailboxes`; the contract object's `qual` field keeps its name; only file names, kinds and schema names are renamed.
- **Model:** record the model you are actually running in the report. Preferred family: Grok through Cursor auto.

## 1. Boundary

Allowed to edit: `src/actl/*.py` (the modules named below and any other module that still names old kinds or paths), `schemas/*.json`.
Forbidden (PB-2 plus scope): `proof/`, `fixtures/`, `test/actl/`, `src/actl/INTERFACES.md`, `tools/`, `docs/`, `hooks/`, `rules/`, `audit/`, `engines/`, `bin/`, `install.sh`, `src/router`, `src/sessions`, `src/core`, `config/`. If a change outside the allowed paths looks necessary, stop and report it; do not make it.
If a test contradicts the memo, stop and report a "test defect" with the test id and the memo line. Do not edit the test, skip it, or work around it in code.

## 2. Tasks, in order

**B0 Baseline.** Before editing, run `python3 -m pytest test/actl -q --tb=line` and `bash proof/run_suite_actl_s0.sh`; save the outputs to `/tmp/lt-b-baseline/`. Expect 157 failed / 660 passed and 9 pass / 10 fail.

**B1 Inventory (no edits).** Run `git grep -nE 'actl-repo|handoff|homes|target_repo|"ev"|"qual"|ev-|qual-|ev\.json|qual\.json' -- src/actl schemas config bin install.sh` and save it. Also run `git grep -nE 'test/actl|proof|fixtures|INTERFACES' -- hooks rules audit engines` and list every place that spells out the PB-2 immutable list. Report these hits; do NOT edit `hooks`, `rules`, `audit` or `engines` (the Owner and Vela decide that separately).

**B2 Schemas** (`WI-S0-R7`). `git mv schemas/ev.json schemas/verification.json` and `git mv schemas/qual.json schemas/qualification.json`; update `$id`, the `kind` const or enum, and any cross-references. Add the `repo` property to the `state` and `sprint` schemas. Keep every bound, pattern and `additionalProperties` as pinned by the tests.

**B3 Kinds and ids** (`WI-S0-R7`): `ids.py`, `schemas.py`, `seq.py` kind lists and filename patterns: `verification` and `qualification` replace `ev` and `qual`; the old names must be rejected (ValueError). Reconstruct (`WI-S0-R5`) reads `verification-NNN.json` and `qualification-NNN.json` from the new run and record locations.

**B4 Layout** (`WI-S0-R3`): `layout.py`. `Layout(root, repo="target-repo")`; the new tree from memo sections 1 to 3 (`repos/<repo>`, `records/<repo>/<tag>`, `sprints/<repo>/<tag>/{runs,mailboxes/<role>/{inbox,outbox},workspaces}`, `profiles/<role>`); accessors `records`, `profile(role)`, `mailboxes(tag)` as in INTERFACES.md; validation of repo names like workspace names; modes as the tests pin them. Two repos with the same tag must not collide.

**B5 Sprint and state** (`WI-S0-R4`): `sprint.py`, `cmd_sprint.py`: record `repo` in `sprint.toml` and `state.json`; every function that loads state checks `state.repo == layout.repo` and raises the existing integrity error (exit 3); `sprint new --json` uses `mailboxes_dir`; paths follow B4.

**B6 Init and doctor** (`WI-S0-R4`): `cmd_init.py`: repo selection (`--name`), writes `profiles/README.md` with the text in memo section 6; `doctor.py`: checks and `--refresh` match the new tree.

**B7 Sweep.** Re-run the B1 grep over `src/actl schemas`. Every remaining hit must be a rejection of an old name or a documented historical string.

## 3. Commits

One tag per commit: `(WI-S0-R3)`, `(WI-S0-R4)`, `(WI-S0-R5)` or `(WI-S0-R7)`; one requirement per commit. Format `type(scope): summary (WI-S0-Rk)`, then `Why:` (bare SHAs), `What changed:` with `- <file>: <change>` bullets, `Result:` with metrics. No vague leading verb. Run every command with `</dev/null`.

## 4. Delivery gate (paste raw output into `/tmp/lt-b-report.md`, not committed)

1. `git merge-base --is-ancestor 68e2e96 HEAD` exits 0; only new commits; each has exactly one valid tag.
2. `git diff --name-only 68e2e96..HEAD -- proof fixtures test/actl src/actl/INTERFACES.md tools` is EMPTY (PB-2). `git diff --name-only 68e2e96..HEAD` shows only `src/actl/*.py` and `schemas/*.json`.
3. `python3 -m pytest test/actl -q` is fully green (0 failed).
4. `bash proof/run_suite_actl_s0.sh` exits 0 (19 passed). Run P-S0-02 only as part of that suite, without `ACTL_FORK_POINT`.
5. Exit 0 for every other gate suite: `ls proof/run_suite_*.sh`, then run `run_suite_exit_code`, `run_suite_commit_msg`, `run_suite_engines`, `run_suite_session_persistence` (use the real names), plus `bash proof/stage0/P-S0-27.sh`, `proof/stage0/golden_selfcheck.sh`, `proof/stage0/selfcheck_mutations.sh` (still 23 detected).
6. `bash audit/atools-compliance_audit.sh --cursor | tail -2` shows 0 failed.
7. `git status --short` empty. The report lists the B1 inventory (including the PB-2 spelling hits in hooks, rules, audit, engines), the commits, any "test defect" or ambiguity, and the model used. Then stop. Do not run the mutation harness, the end-to-end demo or the doctor refresh: the Owner runs those.
