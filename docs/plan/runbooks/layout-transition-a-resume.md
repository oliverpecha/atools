# Runbook: Layout transition, part A (resume & complete) - workstream `LT-A`

* **Workstream:** `LT-A` (branch `wip/layout-amend-a`, worktree `~/atools-lt-a`)
* **Specification:** `docs/plan/layout-transition-memo.md`
* **Prior Commits:**
* `e053374` `spec(actl): realign specifications with layout transition memo (WI-S0-SPEC)`
* `e72e521` `spec(actl): realign public signatures with layout transition memo (WI-IFACE)`


* **Current State:** 43 dirty files in `fixtures/golden/` and `test/actl/`. Tasks T0–T5 are complete. T0 baseline is stored in `/tmp/lt-a-baseline/` (do not rerun or overwrite).
* **Commit Tag Rules:** Every commit subject ends with exactly one tag: `(WI-S0-PROOF)` for T6, `(WI-DOCS-n)` for T7 and T8 where `n` increments sequentially (`WI-DOCS-13`, `WI-DOCS-14`). Follow `hooks/commit-msg`: `type(scope): summary (WI-tag)`, then `Why:`, `What changed:`, `Result:`.
* **Absolute Boundary:** Do NOT edit `src/actl/*.py`, `schemas/*.json`, `bin/`, `audit/`, or any implementation code.

---

## Task Execution Steps

### 1. Complete Task T6 (Tests, Proofs, Fixtures)

1. Finish updating remaining test files in `test/actl/` containing legacy paths or artifact names:
* `test/actl/test_s0_gap3_layout.py`: replace `actl-repo/specs` with `records/target-repo` / `records/<repo>/<tag>`.
* `test/actl/test_s0_gap4_seed41.py`: change `ev-001.json` to `verification-001.json` (and `kind="verification"`).
* `test/actl/test_s0_gap_seq_reconstruct_order.py`: change `ev-002` / `ev-002.json` to `verification-002` / `verification-002.json` (and `kind="verification"`).
* `test/actl/test_s0_gap_sprint_initial_state.py`: replace `actl-repo/specs` with `records/target-repo`.


2. Update proof scripts under `proof/stage0/`:
* `proof/stage0/P-S0-02.sh`: update `is_allowed_addition` and `is_allowed_modification` for new documentation and proof changes; refresh pinned blob hashes in `is_authorized_pb2_modification`.
* `proof/stage0/P-S0-03.sh`: align assertions with repo-scoped layout (`records/`, `sprints/`, `profiles/`, `repos/`).
* `proof/stage0/golden_selfcheck.sh` and `proof/stage0/selfcheck_mutations.sh`: ensure new rules have at least one mutant and both scripts exit 0.


3. Rebuild golden fixtures:
```bash
bash fixtures/golden/build_golden.sh --install-sprint

```


4. Verify tests and self-checks:
```bash
bash proof/stage0/golden_selfcheck.sh
bash proof/stage0/selfcheck_mutations.sh
bash proof/stage0/P-S0-27.sh

```


5. Commit T6 changes:
```bash
git add fixtures/ test/ proof/
git commit -m "test(actl): realign tests, proofs, and fixtures with layout transition (WI-S0-PROOF)


```



Why:
Layout transition memo locks decisions L-1 through L-11 requiring updated repo-scoped layout, renamed verification and qualification artifact paths, and schema proofs.

What changed:

* fixtures/golden: renamed artifacts and updated build_golden.sh
* test/actl: updated layout, sprint, reconstruct, seq, and schema tests
* proof/stage0: updated P-S0-02 hash pins, P-S0-03 layout assertions, and mutation checks

Result:
Test suite, proofs, and golden fixtures specify the new layout and fail cleanly against unimplemeted Stage 0 code."

```

---

### 2. Task T7: Prompts & Guide Updates

1. `docs/plan/actl_Handoff_Prompts.md`:
- Add the courier paragraph (memo section 4) to the `COMMON BLOCK`.
- Update paths (`profiles/<role>`, `sprints/<repo>/<tag>/mailboxes/`, `verification-NNN.json`, `qualification-NNN.json`).
2. `docs/guide/actl_Guide.md`:
- Update directory tree diagrams and CLI path invocations that become false.
3. Determine next `WI-DOCS-n` tag (`WI-DOCS-13`):
```bash
git add docs/plan/actl_Handoff_Prompts.md docs/guide/actl_Guide.md
git commit -m "docs(plan): update handoff prompts and guide for layout transition (WI-DOCS-13)

Why:
Layout transition requires persona prompts and operator guides to reflect profiles, mailboxes, and courier transport.

What changed:
- docs/plan/actl_Handoff_Prompts.md: add courier paragraph to common block and update role paths
- docs/guide/actl_Guide.md: update layout references and directory hierarchy

Result:
Prompts and user guide reflect layout transition memo requirements."

```

---

### 3. Task T8: Sign-off Record

1. Author `docs/plan/signoffs/layout-transition-owner-approval.md`:
* Date: 2026-10-25
* Approver: Owner
* Scope: Decisions L-1 to L-11, PB-4, D-28 approval
* Conditions: Cross-family delta review before merge, PB-1 re-verified
* Status: "delta review verdict: pending"


2. Commit with next `WI-DOCS-n` tag (`WI-DOCS-14`):
```bash
git add docs/plan/signoffs/layout-transition-owner-approval.md
git commit -m "docs(plan): record layout transition owner approval signoff (WI-DOCS-14)


```



Why:
Record formal owner approval for layout transition decisions L-1 through L-11.

What changed:

* docs/plan/signoffs/layout-transition-owner-approval.md: drafted owner signoff record

Result:
Owner approval documented in accordance with runbook T8."

```

---

### 4. Task T9: Sweep & Collision Cleanup

1. Address or justify remaining hits from:
```bash
git grep -nE 'actl-repo|handoff/|homes|ev-[0-9]|qual-[0-9]|ev\.json|qual\.json|target_repo\(' -- . ':!docs/proposals' ':!docs/plan/signoffs' ':!docs/plan/runbooks'

```

* `docs/design/actl_Design_collisions.md`: update stale references where applicable or document as historical collision analysis.
* `docs/plan/actl_Build_Plan-Stages0to2.md`: update or justify table rows referencing legacy paths.
* `schemas/ev.json` and `schemas/qual.json`: rule 3 forbids editing schemas; document these hits in `/tmp/lt-a-report.md`.
* `src/actl/layout.py`: rule 3 forbids editing implementation; document these hits in `/tmp/lt-a-report.md`.
* `src/actl/INTERFACES.md`: hits in section 3.5, 4.2, and rename notes must be checked against T5 requirements and justified.

2. If file edits are made to `docs/design/` or `docs/plan/`, commit them under appropriate scope and tag before final gate verification.

---

### 5. Gates Verification

Execute all gate checks and capture verbatim outputs for the report:

1. `bash proof/run_suite_actl_s0.sh` must exit 1. Confirm every FAIL corresponds strictly to unimplemented Part B features (no syntax/import errors).
2. Compare test failures against `/tmp/lt-a-baseline/`: confirm only memo-related checks turned red.
3. `bash proof/run_suite_exit_code.sh` must exit 0.
4. `bash proof/stage0/P-S0-27.sh` must exit 0.
5. `bash proof/stage0/golden_selfcheck.sh` must exit 0.
6. `bash proof/stage0/selfcheck_mutations.sh` must exit 0.
7. `bash audit/atools-compliance_audit.sh --cursor` must show 0 failed.
8. `git diff --name-only main..HEAD` must only list permitted paths from section 2.
9. Verify commit subjects:
```bash
git log --format='%h %s' main..HEAD

```


Confirm every commit has exactly one valid WI tag (`WI-S0-SPEC`, `WI-IFACE`, `WI-S0-PROOF`, `WI-DOCS-*`).

---

### 6. Closeout Report

Write `/tmp/lt-a-report.md` with the following structure:

1. **Changed Files Grouped by Tag:** List every commit on `main..HEAD` and its touched files.
2. **Rename Map & Completeness Check:** Full mapping of old to new paths, artifact names, methods, and properties.
3. **Baseline vs. After Comparison Table:** Detailed matrix comparing results against `/tmp/lt-a-baseline/`.
4. **Proposed Decisions & Ambiguities:** Detail any discrepancies, schema renames deferred to Part B, and interface resolutions.
5. **Gate Outputs:** Verbatim exit codes and stdout/stderr of Gates 1 through 6.
6. **T9 Sweep Results:** List of every remaining `git grep` hit along with its one-line justification.
7. Stop. Do not implement code changes in `src/actl/`.
