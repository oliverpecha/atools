# LT-A2 Report: Layout transition delta corrections

* Workstream: LT-A2 / branch `wip/layout-amend-a` / worktree `~/atools-lt-a`
* Fork reviewed: `738cd6b`
* Head: `117d7e3`
* Scratch: `/tmp/lt-a2-scratch/gLAIkJ`
* Date (UTC): 2026-10-25

## Commits (`738cd6b..HEAD`)

```
117d7e3 docs(plan): store delta challenge verdict and resolution (WI-DOCS-17)
e3d0498 test(proof): refresh P-S0-02 pins after delta fixes (WI-S0-PROOF)
da79a07 spec(actl): rename Design ev/qual file residues to L-5 names (WI-S0-SPEC)
3b5af34 docs(plan): courier one-liner and PB-2 tools in prompts (WI-DOCS-16)
defd33c spec(actl): include tools in PB-2 S0-R2.3 path list (WI-S0-SPEC)
4776395 test(actl): mailboxes_dir, F006 negative, layout mutants (WI-S0-PROOF)
8f2ceda spec(actl): apply delta fixes for profiles, closeout, keys (WI-S0-SPEC)
e3519e1 spec(actl): rewrite INTERFACES residue and drop O-17 (WI-IFACE)
b05757d test(proof): pin memo/runbooks and drop tools allowlist (WI-S0-PROOF)
```

## C1 — P-S0-02 path handling table

| Path | Method | Detail |
|---|---|---|
| `docs/plan/layout-transition-memo.md` | pinned blob | `a813524440dfdd2f9809f6730a3de85595d4808f` (never docs glob) |
| `docs/plan/runbooks/layout-transition-a-authoring.md` | pinned blob | `b0a9aa964f8ab8811a472fc92d36acea4465d341` (never docs glob) |
| `tools/mutate.py` | pinned blob | `a2e4042a9e0c1c05c9dafff2e21948626ab68c19` — **not** glob-allowlisted |
| `tools/unfiles.py` | pinned blob | `3faa8220b2afb6f359bd04e51b6235205b0375e6` — **not** glob-allowlisted |
| `tools/*` (other) | rejected | pin gate returns 1 unless exact `path:hash` match |
| `docs/design/*`, `docs/plan/*` (except memo/runbook above), `docs/guide/*` | allowlisted | docs amendment surface |
| `test/actl/*`, `proof/stage0/*`, `fixtures/*` | allowlisted + PB-2 pin table | amended pins refreshed in `e3d0498` |
| `src/actl/INTERFACES.md` | pin + allow-mod prefix | blob `4fabf5941beb…`; grep prefix `4fabf59` |
| INTERFACES / test / proof / fixtures / tools via docs globs | **no** | docs globs do not cover these |

Gate logic change: `b05757d`. Pin refresh (idempotent marker `# LT-A2 pin refresh applied`): `e3d0498`. P-S0-02: **PASS**.

## DC status

See `docs/plan/signoffs/layout-transition-delta-resolution.md` (committed as WI-DOCS-17).

| ID | Status |
|---|---|
| DC-1 | FIXED |
| DC-2 | FIXED |
| DC-3 | FIXED |
| DC-4 | FIXED |
| DC-5 | FIXED (residual hits justified below) |
| DC-6 | PROPOSED-DECISION (`mailboxes_dir`) |
| DC-7 | FIXED |
| DC-8 | FIXED |
| DC-9 | FIXED |
| DC-10 | FIXED |
| DC-11 | FIXED |
| DC-12 | FIXED (+ DEFERRED-PART-B for code-only mutants) |
| DC-13 | FIXED (this report) |
| DC-14 | PROPOSED-DECISION (README init-only; no sprint-proposal `repo` reject) |

## Proposed decisions (Owner ratification)

1. JSON key `handoff_dir` → `mailboxes_dir`.
2. Profile dir mode **0755** (Design aligned to spec/tests; memo silent).
3. `profiles/README.md` written by `actl init` only (L-8).
4. `sprint-proposal` does **not** reject `repo` (memo does not require it).
5. Layout property names: `records`, `profile`, `mailboxes`.
6. Mutants that need implementation code → Part B (`tools/mutate.py`, D-29).

## C12 — Crash evidence and new-rule coverage

### Crashing reds (exception line)

| Proof | Exception line | Memo cause |
|---|---|---|
| P-S0-05 | `FileNotFoundError: State file missing for 2026-10-16_public-profiles` / `ValueError: Invalid artifact kind/seq: 'verification', 1` | L-10 repo-scoped state path; L-5 kind rename (code still old) |
| P-S0-14 | `FileNotFoundError: Sprint not found: 2026-10-16_public-profiles` | L-10 repo-scoped sprint paths |
| P-S0-29 | `FileNotFoundError: Sprint not found: 2026-10-16_public-profiles` | L-10 repo-scoped sprint paths |

### New-rule tests → suite that turns red

| Rule | Test / check | Red suite |
|---|---|---|
| Repo-scoped paths (default name) | `test_p03_layout.py::test_repo_scoped_paths_with_default_name` | P-S0-03 |
| Two repos same tag | `test_p03_layout.py` (cat_app/dog_app) | P-S0-03 |
| Wrong-repo guard | `test_p03_layout.py::test_wrong_repo_guard_rejects_mismatch` | P-S0-03 |
| `profiles/README.md` init-only | `test_base_tree…` (ensure must not write) + init assertion | P-S0-03 / P-S0-04 |
| Renamed kinds | `test_p03_layout.py` artifact id asserts; golden dirs | P-S0-03, P-S0-08 (`schemas/verification.json missing`) |
| `mailboxes_dir` JSON key | `test_p04_sprint.py` `NEW_KEYS` / happy path | P-S0-04 |
| F006 `records/` anchor + negative | `golden_selfcheck.sh` F006 self-tests | green (self-check); pattern for Part B tripwire |
| Mutants M19–M23 | `selfcheck_mutations.sh` | green (23 detected) |

## Deferred to Part B

* Implementation in `src/actl/*.py`, `schemas/*.json`.
* PB-2 enforcement in hooks/rules/audit for `tools/`.
* Mutants that can only be planted once `Layout(repo=…)` / kinds exist in code (`tools/mutate.py`, D-29).
* Closeouts index `closeouts.tsv` (memo §5 / Stage 5).

## C4 sweep (final)

Command (exclusions per runbook): 90 hits. Justifications:

* **Rename maps / decided items:** Design R17, L-5, L-9; addendum D-34, D-38 — old names on the left of old→new.
* **Schema field `qual`** on contract objects (fixtures, INTERFACES contract shape, Design JSON examples): schemas frozen in Part A; key stays until Part B.
* **Historical rulings** `ev.exit_code` (C-3), SA-24 "Golden qual", Design_changes.md — retained ruling vocabulary.
* **Stage 1 addendum shorthand** `ev` / `StepResult`/`ev` — Stage 1 not yet authored; D-34 records L-5 rename for when those specs are written.
* **Tests/proofs planting old names:** `diff_equiv_seed11.py`, gap reconstruct fixtures writing `ev-*`, `reserve(..., "ev")` negatives, mutants M19–M22 — intentional reds / killers.
* **P-S0-02 / golden_selfcheck:** comments and negative checks mentioning `ev`/`qual` dirs.
* **INTERFACES** `handoff_dir` → `mailboxes_dir` in Owner Amendment proposed list — documents the rename.
* **`/srv/agent-graph`:** only as L-9 example value.
* **`actl-repo`:** only in mutant M22 sed pattern (planted defect).

Raw: `/tmp/lt-a2-scratch/gLAIkJ/c4-sweep-final.txt`

## Delivery gate outputs

### 1. Ancestry / commits
```
merge-base_is_ancestor_rc=0
117d7e3 docs(plan): store delta challenge verdict and resolution (WI-DOCS-17)
e3d0498 test(proof): refresh P-S0-02 pins after delta fixes (WI-S0-PROOF)
da79a07 spec(actl): rename Design ev/qual file residues to L-5 names (WI-S0-SPEC)
3b5af34 docs(plan): courier one-liner and PB-2 tools in prompts (WI-DOCS-16)
defd33c spec(actl): include tools in PB-2 S0-R2.3 path list (WI-S0-SPEC)
4776395 test(actl): mailboxes_dir, F006 negative, layout mutants (WI-S0-PROOF)
8f2ceda spec(actl): apply delta fixes for profiles, closeout, keys (WI-S0-SPEC)
e3519e1 spec(actl): rewrite INTERFACES residue and drop O-17 (WI-IFACE)
b05757d test(proof): pin memo/runbooks and drop tools allowlist (WI-S0-PROOF)
```

### 2. Forbidden paths
`git diff --name-only main..HEAD`: 62 paths, **0 forbidden**.

### 3. `bash proof/run_suite_actl_s0.sh` → exit 1, 0 Environment
```
    FAIL: pytest reported failures without a FAIL: line
Running P-S0-07_hashing... [PASS]
Running P-S0-08_schemas... [FAIL] (see proof/out/P-S0-08_schemas.log)
    FAIL: schemas/verification.json missing
    FAIL: installed golden state.json invalid: [{'path': '/repo', 'message': 'Additional property not allowed: repo'}]
Running P-S0-09_defaults... [FAIL] (see proof/out/P-S0-09_defaults.log)
    FAIL: pytest reported failures without a FAIL: line
Running P-S0-11_cli_exit_codes... [PASS]
Running P-S0-12_scope... [PASS]
Running P-S0-13_global_hook_immunity... [PASS]
Running P-S0-14_registries... [FAIL] (see proof/out/P-S0-14_registries.log)
    FAIL: decide_next crashed: Traceback (most recent call last):
    FAIL: decide_next crashed: Traceback (most recent call last):
Running P-S0-15_expected_fragments... [PASS]
Running P-S0-26_interfaces_conformance... [FAIL] (see proof/out/P-S0-26_interfaces_conformance.log)
    FAIL: 5 interface problem(s):
Running P-S0-28_doctor_uninitialised... [PASS]
Running P-S0-29_next_rules_table... [FAIL] (see proof/out/P-S0-29_next_rules_table.log)
    FAIL: decide_next crashed: Traceback (most recent call last):
    FAIL: decide_next crashed: Traceback (most recent call last):
Running P-S0-30_gap_proofs... [FAIL] (see proof/out/P-S0-30_gap_proofs.log)
    FAIL: pytest reported failures without a FAIL: line
==========================================
Suite Summary: 9 Passed, 10 Failed, 0 Environment
==========================================
```
Red set (= prior 10): P-S0-03, -04, -05, -06, -08, -09, -14, -26, -29, -30. P-S0-02 PASS.

### 4. Green suites
```
run_suite_exit_code: exit EXIT_RC=0
Running E9_read_exit_code_helper... [PASS]
Running E10_signalled_runner_never_zero... [PASS]
==========================================
Suite Summary: 10 Passed, 0 Failed
==========================================
P-S0-27: exit P27_RC=0
golden_selfcheck: exit GOLDEN_RC=0
ok: solution_key case matches expected.d
==========================================
golden_selfcheck: ALL CHECKS PASSED
selfcheck_mutations: exit MUT_RC=0
      FAIL: build_golden.sh state template missing repo field
==========================================
selfcheck_mutations: control green, all 23 planted defects detected
```

### 5. Compliance audit
```
Audit Verdict: 49 passed, 0 failed, 18 skipped, 2 warnings (profile=dev, adapter=cursor)
========================================================
```

### 6–7. P-S0-02 + C4
Covered above. C4 re-run stored at `/tmp/lt-a2-scratch/gLAIkJ/c4-sweep-final.txt`.

### 8. `git status --short`
empty.

## Stop
LT-A2 authoring complete. No push, no Part B.
