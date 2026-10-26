# LT-A Part A Authoring Report

Workstream: `LT-A` · Branch: `wip/layout-amend-a` · Worktree: `~/atools-lt-a`  
Memo: `docs/plan/layout-transition-memo.md`  
Date: 2026-10-25  
Stopped after this report per runbook. No Part B implementation in `src/actl/*.py` or `schemas/*.json`.

---

## 1. Changed Files Grouped by Tag

Commits on `main..HEAD`:

```
738cd6b docs(plan): realign build-plan tables and mark collisions historical (WI-DOCS-15)
d6824c8 docs(plan): record layout transition owner approval signoff (WI-DOCS-14)
30833e1 docs(plan): realign handoff prompts and guide for layout transition (WI-DOCS-13)
2d8be0d test(actl): realign tests, proofs, and fixtures with layout transition (WI-S0-PROOF)
e72e521 spec(actl): realign public signatures with layout transition memo (WI-IFACE)
e053374 spec(actl): realign specifications with layout transition memo (WI-S0-SPEC)
```

Files per commit:

```
### e053374 spec(actl): realign specifications with layout transition memo (WI-S0-SPEC)
  - docs/design/actl_Design.md
  - docs/design/actl_Design_changes.md
  - docs/plan/actl_Build_Plan-Stages0to2_addendum.md
  - docs/plan/spec-S0.md

### e72e521 spec(actl): realign public signatures with layout transition memo (WI-IFACE)
  - src/actl/INTERFACES.md

### 2d8be0d test(actl): realign tests, proofs, and fixtures with layout transition (WI-S0-PROOF)
  - fixtures/golden/artifacts/invalid/contract/budgets_forbidden.json
  - fixtures/golden/artifacts/invalid/contract/epoch_zero.json
  - fixtures/golden/artifacts/invalid/contract/id_pattern.json
  - fixtures/golden/artifacts/invalid/contract/kind_const.json
  - fixtures/golden/artifacts/invalid/contract/short_base_sha.json
  - fixtures/golden/artifacts/invalid/contract/spec_missing_sha256.json
  - fixtures/golden/artifacts/invalid/ev/exit_code_above_255.json
  - fixtures/golden/artifacts/invalid/ev/exit_code_negative.json
  - fixtures/golden/artifacts/invalid/ev/exit_code_type.json
  - fixtures/golden/artifacts/invalid/ev/failing_line_too_long.json
  - fixtures/golden/artifacts/invalid/ev/halt_reason_enum.json
  - fixtures/golden/artifacts/invalid/ev/head_pattern.json
  - fixtures/golden/artifacts/invalid/ev/missing_kind.json
  - fixtures/golden/artifacts/invalid/ev/stage_enum.json
  - fixtures/golden/artifacts/invalid/ev/step_exit_code_type.json
  - fixtures/golden/artifacts/invalid/index.json
  - fixtures/golden/artifacts/invalid/meta/kind_enum.json
  - fixtures/golden/artifacts/invalid/qual/diagnostic_enum.json
  - fixtures/golden/artifacts/invalid/qual/green_pattern.json
  - fixtures/golden/artifacts/invalid/qual/killed_type.json
  - fixtures/golden/artifacts/invalid/qual/manifest_pattern.json
  - fixtures/golden/artifacts/invalid/qual/null_base_enum.json
  - fixtures/golden/artifacts/invalid/qualification/diagnostic_enum.json
  - fixtures/golden/artifacts/invalid/qualification/green_pattern.json
  - fixtures/golden/artifacts/invalid/qualification/killed_type.json
  - fixtures/golden/artifacts/invalid/qualification/manifest_pattern.json
  - fixtures/golden/artifacts/invalid/qualification/null_base_enum.json
  - fixtures/golden/artifacts/invalid/verification/exit_code_above_255.json
  - fixtures/golden/artifacts/invalid/verification/exit_code_negative.json
  - fixtures/golden/artifacts/invalid/verification/exit_code_type.json
  - fixtures/golden/artifacts/invalid/verification/failing_line_too_long.json
  - fixtures/golden/artifacts/invalid/verification/halt_reason_enum.json
  - fixtures/golden/artifacts/invalid/verification/head_pattern.json
  - fixtures/golden/artifacts/invalid/verification/missing_kind.json
  - fixtures/golden/artifacts/invalid/verification/stage_enum.json
  - fixtures/golden/artifacts/invalid/verification/step_exit_code_type.json
  - fixtures/golden/artifacts/valid/contract/contract_base.json
  - fixtures/golden/artifacts/valid/ev/ev_base.json
  - fixtures/golden/artifacts/valid/ev/ev_exit_255.json
  - fixtures/golden/artifacts/valid/ev/ev_exit_null.json
  - fixtures/golden/artifacts/valid/ev/ev_green_with_session.json
  - fixtures/golden/artifacts/valid/ev/ev_halt.json
  - fixtures/golden/artifacts/valid/qual/qual_base.json
  - fixtures/golden/artifacts/valid/qual/qual_conflict.json
  - fixtures/golden/artifacts/valid/qualification/qualification_base.json
  - fixtures/golden/artifacts/valid/qualification/qualification_conflict.json
  - fixtures/golden/artifacts/valid/verification/verification_base.json
  - fixtures/golden/artifacts/valid/verification/verification_exit_255.json
  - fixtures/golden/artifacts/valid/verification/verification_exit_null.json
  - fixtures/golden/artifacts/valid/verification/verification_green_with_session.json
  - fixtures/golden/artifacts/valid/verification/verification_halt.json
  - fixtures/golden/build_golden.sh
  - fixtures/golden/expected_text/sprint.toml.tmpl
  - proof/stage0/P-S0-02.sh
  - test/actl/test_p03_layout.py
  - test/actl/test_p04_sprint.py
  - test/actl/test_p05_seq.py
  - test/actl/test_p06_reconstruct.py
  - test/actl/test_p08_schemas.py
  - test/actl/test_p09_defaults.py
  - test/actl/test_p13_next_rules.py
  - test/actl/test_p14_registries.py
  - test/actl/test_s0_gap2_layout_modes.py
  - test/actl/test_s0_gap2_reconstruct.py
  - test/actl/test_s0_gap2_seed23.py
  - test/actl/test_s0_gap3_layout.py
  - test/actl/test_s0_gap4_seed41.py
  - test/actl/test_s0_gap_seq_reconstruct_order.py
  - test/actl/test_s0_gap_sprint_initial_state.py

### 30833e1 docs(plan): realign handoff prompts and guide for layout transition (WI-DOCS-13)
  - docs/guide/actl_Guide.md
  - docs/plan/actl_Handoff_Prompts.md

### d6824c8 docs(plan): record layout transition owner approval signoff (WI-DOCS-14)
  - docs/plan/signoffs/layout-transition-owner-approval.md

### 738cd6b docs(plan): realign build-plan tables and mark collisions historical (WI-DOCS-15)
  - docs/design/actl_Design_collisions.md
  - docs/plan/actl_Build_Plan-Stages0to2.md
```

`git diff --name-only main..HEAD` (union):

```
docs/design/actl_Design.md
docs/design/actl_Design_changes.md
docs/design/actl_Design_collisions.md
docs/guide/actl_Guide.md
docs/plan/actl_Build_Plan-Stages0to2.md
docs/plan/actl_Build_Plan-Stages0to2_addendum.md
docs/plan/actl_Handoff_Prompts.md
docs/plan/signoffs/layout-transition-owner-approval.md
docs/plan/spec-S0.md
fixtures/golden/artifacts/invalid/contract/budgets_forbidden.json
fixtures/golden/artifacts/invalid/contract/epoch_zero.json
fixtures/golden/artifacts/invalid/contract/id_pattern.json
fixtures/golden/artifacts/invalid/contract/kind_const.json
fixtures/golden/artifacts/invalid/contract/short_base_sha.json
fixtures/golden/artifacts/invalid/contract/spec_missing_sha256.json
fixtures/golden/artifacts/invalid/index.json
fixtures/golden/artifacts/invalid/meta/kind_enum.json
fixtures/golden/artifacts/invalid/qualification/diagnostic_enum.json
fixtures/golden/artifacts/invalid/qualification/green_pattern.json
fixtures/golden/artifacts/invalid/qualification/killed_type.json
fixtures/golden/artifacts/invalid/qualification/manifest_pattern.json
fixtures/golden/artifacts/invalid/qualification/null_base_enum.json
fixtures/golden/artifacts/invalid/verification/exit_code_above_255.json
fixtures/golden/artifacts/invalid/verification/exit_code_negative.json
fixtures/golden/artifacts/invalid/verification/exit_code_type.json
fixtures/golden/artifacts/invalid/verification/failing_line_too_long.json
fixtures/golden/artifacts/invalid/verification/halt_reason_enum.json
fixtures/golden/artifacts/invalid/verification/head_pattern.json
fixtures/golden/artifacts/invalid/verification/missing_kind.json
fixtures/golden/artifacts/invalid/verification/stage_enum.json
fixtures/golden/artifacts/invalid/verification/step_exit_code_type.json
fixtures/golden/artifacts/valid/contract/contract_base.json
fixtures/golden/artifacts/valid/qualification/qualification_base.json
fixtures/golden/artifacts/valid/qualification/qualification_conflict.json
fixtures/golden/artifacts/valid/verification/verification_base.json
fixtures/golden/artifacts/valid/verification/verification_exit_255.json
fixtures/golden/artifacts/valid/verification/verification_exit_null.json
fixtures/golden/artifacts/valid/verification/verification_green_with_session.json
fixtures/golden/artifacts/valid/verification/verification_halt.json
fixtures/golden/build_golden.sh
fixtures/golden/expected_text/sprint.toml.tmpl
proof/stage0/P-S0-02.sh
src/actl/INTERFACES.md
test/actl/test_p03_layout.py
test/actl/test_p04_sprint.py
test/actl/test_p05_seq.py
test/actl/test_p06_reconstruct.py
test/actl/test_p08_schemas.py
test/actl/test_p09_defaults.py
test/actl/test_p13_next_rules.py
test/actl/test_p14_registries.py
test/actl/test_s0_gap2_layout_modes.py
test/actl/test_s0_gap2_reconstruct.py
test/actl/test_s0_gap2_seed23.py
test/actl/test_s0_gap3_layout.py
test/actl/test_s0_gap4_seed41.py
test/actl/test_s0_gap_seq_reconstruct_order.py
test/actl/test_s0_gap_sprint_initial_state.py
```

All paths are within the authoring allowlist (`docs/design/`, `docs/plan/`, `docs/guide/`, `src/actl/INTERFACES.md`, `test/actl/`, `proof/`, `fixtures/`).

---

## 2. Rename Map & Completeness Check

| Old | New | Status in Part A |
|---|---|---|
| `actl-repo/` | `records/` | Specs, tests, fixtures, proofs updated |
| `actl-repo/specs/<tag>/` | `records/<repo>/<tag>/` | Updated |
| `actl-repo/specs/<tag>/runs/` | `sprints/<repo>/<tag>/runs/` | Updated |
| `handoff/<tag>/` | `sprints/<repo>/<tag>/mailboxes/` | Updated in Design/Guide/tests; some INTERFACES Stage-1 prose still names `handoff/` (justified in §4/§6) |
| `workspaces/` (top-level) | `sprints/<repo>/<tag>/workspaces/` | Updated |
| `repos/target-repo` | `repos/<repo>` (default `target-repo`) | Updated |
| `homes/<role>`, `Layout.homes` | `profiles/<role>`, `Layout.profile` | Specs/tests updated; impl deferred Part B |
| `Layout.actl_repo` | `Layout.records` | INTERFACES + tests |
| `Layout.handoff` | `Layout.mailboxes` | INTERFACES + tests |
| `ev-NNN.json` / kind `ev` | `verification-NNN.json` / kind `verification` | Fixtures, tests, proofs updated |
| `qual-NNN.json` / kind `qual` | `qualification-NNN.json` / kind `qualification` | Fixtures, tests, proofs updated |
| `schemas/ev.json` | `schemas/verification.json` | **Deferred Part B** (schemas forbidden in Part A) |
| `schemas/qual.json` | `schemas/qualification.json` | **Deferred Part B** |
| `StepResult.to_ev_step` | `StepResult.to_verification_step` | INTERFACES only; impl deferred |
| `Layout(root)` | `Layout(root, repo="target-repo")` + repo guard | INTERFACES + tests; impl deferred |
| `sprint.toml` / `state.json` | add `repo` field | Fixtures/tests expect it; schemas/impl deferred |
| courier / `ACTL_COURIER_DIR` | COMMON BLOCK + Design/addendum | Docs only (Stage 2 impl later) |
| `tools/` | top-level PB-2 list | Specs; allowlisted in P-S0-02; not edited |

Completeness: T9 `git grep` remaining hits are listed in §6 with one-line justifications. No remaining hits under `test/actl/` for the sweep pattern.

---

## 3. Baseline vs. After Comparison Table

| Check | Baseline (`/tmp/lt-a-baseline/`) | After Part A | Maps to memo? |
|---|---|---|---|
| `proof/run_suite_actl_s0.sh` | exit 1 (1 FAIL: P-S0-02 unauthorized docs) | exit 1 (10 FAIL: layout/schemas/iface/next/gaps) | Yes — P-S0-02 now PASS; new reds are L-1..L-10 / L-5 unimplemented |
| `python3 -m pytest test/actl -q` | exit 0 · 804 passed | exit 1 · 118 failed, 691 passed | Yes — failures assert new paths/kinds/repo guard against old code |
| `proof/stage0/P-S0-27.sh` | exit 0 | exit 0 | Unchanged green |
| `proof/stage0/golden_selfcheck.sh` | exit 0 | exit 0 | Unchanged green |
| `proof/stage0/selfcheck_mutations.sh` | exit 0 | exit 0 | Unchanged green (18 mutants) |
| `proof/run_suite_exit_code.sh` | exit 0 | exit 0 | Unchanged green |
| `audit/atools-compliance_audit.sh --cursor` | 0 failed | 49 passed, 0 failed, 18 skipped, 2 warnings | Unchanged green |

Suite FAIL detail (after → memo item):

| Proof | Failure signature | Memo |
|---|---|---|
| P-S0-03_layout | missing `profiles/README.md`; `Layout(..., repo=)` / `.records` / kinds `verification` | L-1, L-8, L-10, L-5 |
| P-S0-04_sprint_new | expects files under `records/<repo>/<tag>/` (impl still writes old tree) | L-1, L-10 |
| P-S0-05_seq_concurrency | `reserve(..., "verification")` rejected by ids; state path under old tree | L-5, L-1 |
| P-S0-06_seq_reconstruct | writes via new `runs_dir` expectation vs old `actl-repo/specs/.../runs` | L-1, L-5 |
| P-S0-08_schemas | `schemas/verification.json` missing; kind `qualification` unknown; `repo` extra on state | L-5, L-10 |
| P-S0-09_defaults | expects `records/.../sprint.toml` | L-1 |
| P-S0-14_registries / P-S0-29_next_rules | `Sprint not found` — decide_next looks up old sprint_dir | L-1 |
| P-S0-26_interfaces | Layout params/properties and `to_verification_step` missing in code | L-10, L-2, L-5 |
| P-S0-30_gap_proofs | gap tests expect `records/` / verification artifacts | L-1, L-5 |

P-S0-02 flipped baseline FAIL → PASS after docs/tools allowlists and pin refresh (authoring hygiene, not a new product feature).

Nothing outside the amendment scope turned red (hashing, scope, doctor, CLI exit codes, expected fragments, golden self-check stay green).

---

## 4. Proposed Decisions & Ambiguities

From `src/actl/INTERFACES.md` §6 / Owner Amendment Note (already on branch via WI-IFACE):

- **O-17:** property/method renames (`records`, `profile`, `mailboxes`, `to_verification_step`) locked to memo §3 / L-5.
- **Owner Amendment Note:** L-1..L-11 approved 2026-10-25 (PB-4, D-28); conditions: cross-family delta review + PB-1 re-verify; **delta review verdict: pending**.
- **Schema file renames** (`schemas/ev.json` → `verification.json`, `qual.json` → `qualification.json`): specified in Part A; **implementation deferred to Part B** (hard rule forbids editing `schemas/*.json` here).
- **INTERFACES leftover `handoff/` / `ev-` prose** in §1.10 `verify_impl` side effects and §3.5 `attempt.json` / `prior_attempt.json` paths: intentional residual Stage-1 wording; mailbox rename is recorded in O-17 and Design; Part B should rewrite those strings when implementing verify/dispatch. Not silently resolved against Design.
- **A-3 / A-4** still mention `ev`/`qual`/`specs/` in historical ambiguity rows; left as frozen register text (pre-transition readings). Normative schema kinds elsewhere in INTERFACES already say `verification` / `qualification`.
- **L-11 / O-16:** Stage 4 revisit of `Layout(root, repo)` vs explicit repo arg — recorded in addendum; out of Part A impl scope.

Sign-off draft: `docs/plan/signoffs/layout-transition-owner-approval.md` (WI-DOCS-14).

---

## 5. Gate Outputs

### Gate 1 — `bash proof/run_suite_actl_s0.sh` (expect exit 1)

```
exit: 1
```

```
Running P-S0-10_golden_selfcheck... [PASS]
Running P-S0-01_doctor... [PASS]
Running P-S0-02_additive_change... [PASS]
Running P-S0-03_layout... [FAIL] (see proof/out/P-S0-03_layout.log)
    FAIL: pytest reported failures without a FAIL: line
Running P-S0-04_sprint_new... [FAIL] (see proof/out/P-S0-04_sprint_new.log)
Running P-S0-05_seq_concurrency... [FAIL] (see proof/out/P-S0-05_seq_concurrency.log)
    FAIL: worker produced too few numbers (0) to test a kill
Running P-S0-06_seq_reconstruct... [FAIL] (see proof/out/P-S0-06_seq_reconstruct.log)
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

### Gate 2 — Baseline comparison

See §3 table. Baseline suite: 18 Passed, 1 Failed (P-S0-02 docs). After: 9 Passed, 10 Failed, 0 Environment. All new FAILs map to unimplemented Part B layout/kind/repo features; zero harness/import/syntax environment errors (exit 4 count = 0).

### Gate 3 — `bash proof/run_suite_exit_code.sh` (expect exit 0)

```
exit: 0
Running E1_exit_zero... [PASS]
Running E2_exit_nonzero... [PASS]
Running E3_exit_timeout_124... [PASS]
Running E4_exit_file_format... [PASS]
Running E5_runner_removed_exit_kept... [PASS]
Running E6_stale_exit_replaced... [PASS]
Running E7_no_exit_while_running... [PASS]
Running E8_kill_records_signal_exit... [PASS]
Running E9_read_exit_code_helper... [PASS]
Running E10_signalled_runner_never_zero... [PASS]
==========================================
Suite Summary: 10 Passed, 0 Failed
==========================================
```

### Gate 4 — `bash proof/stage0/P-S0-27.sh` (expect exit 0)

```
exit: 0
OK: P-S0-27 suite conforms
```

### Gate 5 — `bash proof/stage0/golden_selfcheck.sh` (expect exit 0)

```
exit: 0
ok: build is deterministic (01d880bc3176cdd8f31d72e67bb3eba54d634378)
ok: base_sha matches expected.d
ok: G5 self-test catches synthetic secret
ok: G6 self-test catches synthetic eval
ok: G6 self-test no false positive
ok: base: every proof and probe is red
ok: base: first failing step O1:01_public.sh
ok: base: failing line has FAIL:
ok: base: repo tests green
ok: key run 1/3 green (O1+O2)
ok: key run 2/3 green (O1+O2)
ok: key run 3/3 green (O1+O2)
ok: key passes G3/G5/G6
ok: mutant avatar_drop survives (deliberate)
ok: mutant avatar_drop first failing step 'none' as declared
ok: mutant contact_leak killed exactly by [02_no_email.sh]
ok: mutant contact_leak first failing step 'O1:02_no_email.sh' as declared
ok: mutant photo_count_off killed exactly by [probe.sh]
ok: mutant photo_count_off first failing step 'O1:probe.sh' as declared
ok: mutant private_200 killed exactly by [03_private_404.sh]
ok: mutant private_200 first failing step 'O1:03_private_404.sh' as declared
ok: exactly one deliberate survivor
ok: good -> step=O2 exit=0 failing=none
ok: bad_scope -> step=G3 exit=1 failing=G3
ok: bad_testcount -> step=G4 exit=1 failing=G4
ok: bad_secret -> step=G5 exit=1 failing=G5
ok: bad_forbidden -> step=G6 exit=1 failing=G6
ok: bad_proof_o1 -> step=O1 exit=1 failing=O1:02_no_email.sh
ok: bad_regression_o2 -> step=O2 exit=1 failing=O2:test_users::test_get_user_unknown_returns_none
ok: bad_testcount under default scope fails G3 (frozen)
ok: solution_key case matches expected.d
==========================================
golden_selfcheck: ALL CHECKS PASSED
```

### Gate 6 — `bash proof/stage0/selfcheck_mutations.sh` (expect exit 0)

```
exit: 0
ok: control green
ok: M01 detected (wrong base_sha in expected.d)
      FAIL: base_sha 01d880bc3176cdd8f31d72e67bb3eba54d634378 != expected.d 0000000000000000000000000000000000000000
ok: M02 detected (target-repo content changed (SHA drifts))
      FAIL: base_sha 7999afe6e90145478ca887c911ca92a3f0007a16 != expected.d 01d880bc3176cdd8f31d72e67bb3eba54d634378
ok: M03 detected (mutant remapped to a proof that cannot kill it)
      FAIL: mutant contact_leak killed by [02_no_email.sh], coverage.md says [01_public.sh]
ok: M04 detected (avatar assertion added: survivor becomes killable)
      FAIL: mutant avatar_drop must survive but failed [01_public.sh]
ok: M05 detected (02_no_email.sh weakened to always pass)
      FAIL: base: expected all 4 proofs red, red set = [01_public.sh 03_private_404.sh probe.sh]
ok: M06 detected (probe.sh weakened to always pass)
      FAIL: base: expected all 4 proofs red, red set = [01_public.sh 02_no_email.sh 03_private_404.sh]
ok: M07 detected (03_private_404.sh weakened to always pass)
      FAIL: base: expected all 4 proofs red, red set = [01_public.sh 02_no_email.sh probe.sh]
ok: M08 detected (good.patch replaced by a leaking patch)
      FAIL: good: got step=O1 exit=1 failing='O1:02_no_email.sh' line='FAIL: body contains seeded email material (ada@example.test) for id 1' ; want step=O2 exit=0 failing='' contains=''
ok: M09 detected (bad_regression_o2 replaced by good.patch)
      FAIL: bad_regression_o2: got step=O2 exit=0 failing='' line='' ; want step=O2 exit=1 failing='O2:test_users::test_get_user_unknown_returns_none' contains='test_get_user_unknown_returns_none'
ok: M10 detected (bad_secret replaced by good.patch)
      FAIL: bad_secret: got step=O2 exit=0 failing='' line='' ; want step=G5 exit=1 failing='G5' contains='secret pattern'
ok: M11 detected (bad_forbidden replaced by good.patch)
      FAIL: bad_forbidden: got step=O2 exit=0 failing='' line='' ; want step=G6 exit=1 failing='G6' contains='forbidden call'
ok: M12 detected (scope.txt widened: bad_scope no longer denied)
      FAIL: bad_scope: got step=O2 exit=0 failing='' line='' ; want step=G3 exit=1 failing='G3' contains='api/cli.py'
ok: M13 detected (scope override removed: bad_testcount stops at G3, not G4)
      FAIL: bad_testcount: got step=G3 exit=1 failing='G3' line='FAIL: G3 path test/test_users.py is frozen by scope' ; want step=G4 exit=1 failing='G4' contains='test function count decreased'
ok: M14 detected (declared failing step of bad_scope changed)
      FAIL: bad_scope: got step=G3 exit=1 failing='G3' line='FAIL: G3 path api/cli.py is denied by scope (not in ALLOW)' ; want step=G3 exit=1 failing='G4' contains='api/cli.py'
ok: M15 detected (solution key sabotaged: avatar field returns the email)
      FAIL: key run 1/3 red at O1:02_no_email.sh: FAIL: body contains seeded email material (ada@example.test) for id 1
ok: M16 detected (a mutant patch no longer applies)
      FAIL: mutant private_200 does not apply on base+key
ok: M17 detected (second survivor planted (photo_count_off neutralised))
      FAIL: mutant photo_count_off killed by [], coverage.md says [probe.sh]
ok: M18 detected (proof 01 deleted)
      FAIL: base: first failing step 'O1:02_no_email.sh' != 'O1:01_public.sh'
==========================================
selfcheck_mutations: control green, all 18 planted defects detected
```

### Gate 7 — `bash audit/atools-compliance_audit.sh --cursor` (expect 0 failed)

```
exit: 0
Audit Verdict: 49 passed, 0 failed, 18 skipped, 2 warnings (profile=dev, adapter=cursor)
```

### Gate 8 — `git diff --name-only main..HEAD` permitted paths only

Confirmed: only `docs/`, `fixtures/`, `proof/stage0/P-S0-02.sh`, `src/actl/INTERFACES.md`, `test/actl/` (see §1). No `src/actl/*.py`, `schemas/*.json`, `bin/`, `audit/`, `tools/` edits.

### Gate 9 — Commit subjects each have exactly one WI tag

```
738cd6b docs(plan): realign build-plan tables and mark collisions historical (WI-DOCS-15)
d6824c8 docs(plan): record layout transition owner approval signoff (WI-DOCS-14)
30833e1 docs(plan): realign handoff prompts and guide for layout transition (WI-DOCS-13)
2d8be0d test(actl): realign tests, proofs, and fixtures with layout transition (WI-S0-PROOF)
e72e521 spec(actl): realign public signatures with layout transition memo (WI-IFACE)
e053374 spec(actl): realign specifications with layout transition memo (WI-S0-SPEC)
```

Tags present: `WI-S0-SPEC`, `WI-IFACE`, `WI-S0-PROOF`, `WI-DOCS-13`, `WI-DOCS-14`, `WI-DOCS-15`. No untagged commits on `main..HEAD`.

---

## 6. T9 Sweep Results

Command:

```bash
git grep -nE 'actl-repo|handoff/|homes|ev-[0-9]|qual-[0-9]|ev\.json|qual\.json|target_repo\(' -- . ':!docs/proposals' ':!docs/plan/signoffs' ':!docs/plan/runbooks'
```

Remaining hits (38) with one-line justification:

- `docs/design/actl_Design_collisions.md:1:> **Historical record (layout transition).** This file captures collision analysis against the pre-transition Design paths (`actl-repo/`, `handoff/`, `ev-NNN`, `qual-NNN`). It is retained as-written for audit trail. Normative current names are in `actl_Design.md` and `docs/plan/layout-transition-memo.md` (L-1..L-11). Do not treat path strings below as current requirements.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:15:* **i.** Add `scope.txt` (optional override) to `handoff/{sprint_tag}/architect-outputs/` in §1.5.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:41:* **ii.** Change all `handoff/{sprint_tag}/{role}-inputs/` directories to `chmod 2750 actl:{role}` and `{role}-outputs/` to `chmod 2770 actl:{role}`.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:79:* **i.** In §1.5, §4.3, and §5.4, `closure-006.json` is written directly by the Implementer into `handoff/{sprint_tag}/implementer-outputs/closure-006.json` and is **never promoted** into `actl-repo/specs/{sprint_tag}/runs/`.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:91:* **ii.** Upon closure, `actl` locks `implementer-outputs/` to `0750`, promotes and unlinks `closure.json` into `actl-repo/specs/{sprint_tag}/runs/closure-{seq}.json` (using the `seq` reserved by that attempt at dispatch), and add `closure-006.json` under `runs/` in the §1.5 directory tree.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:99:* **a) Issue:** §1.5 and §5.2.3 state that `oracle-{seq}/` is frozen into `actl-repo/specs/{sprint_tag}/` only when the Architect emits `lock_oracle`. However:` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:102:* **i.** `qual-004.json` (§4.2) references `"oracle": "oracle-003"` *before* the Architect has decided whether to lock or revise the oracle.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:105:* **ii.** `escalation-004.json` (§4.3, where the oracle was *never* locked because all 3 attempts failed qualification) references `"latest_oracle": "oracle-002"` and `"qual": "qual-003.json"`, and §1.3 requires `actl` to stage the `prior oracle` into `challenger-inputs/` on retry.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:111:* **i.** Specify in §5.2.1 that at the end of every Challenger turn (and whenever the Architect updates `solution_key.patch` or `scope.txt` in Phase 2/3), `actl` promotes `challenger-outputs/oracle-draft/` (plus the current `solution_key.patch`) into an immutable `actl-repo/specs/{sprint_tag}/oracle-{seq}/` *before* running `qual-{seq+1}.json`.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:125:* **i.** None of the JSON schemas or examples in §4.2–§4.3 (`qual-004.json`, `closure-006.json`, `ev-007.json`, `escalation-*.json`, `live-decision-012.json`) include `kind`, `seq`, or `parent`.` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/design/actl_Design_collisions.md:128:* **ii.** Cross-references mix bare IDs and filenames inconsistently within the same object (e.g., `ev-007.json` uses `"oracle": "oracle-003"` without an extension alongside `"contract": "contract-005.json"` with `.json`; `escalation-010.json` uses `"last_closure": "closure-008.json"` with `.json` alongside `"evidence": ["ev-007", "ev-009"]` without `.json`).` — Historical collision analysis; banner added (WI-DOCS-15); paths intentionally pre-transition.
- `docs/plan/actl_Build_Plan-Stages0to2_addendum.md:719:- D-39 (L-10) `Layout(root, repo="target-repo")`: one Layout per repository, so existing method signatures stay unchanged and the golden fixture works through the default. A `repo` field is recorded in `sprint.toml` and `state.json`. Every function that loads state checks it equals `layout.repo` and raises the existing integrity error (exit 3). One proof: "wrong-repo Layout rejected". The earlier narrower `Layout.target_repo(name)` amendment is superseded.` — D-39 cites superseded Layout.target_repo(name) by name while recording L-10; intentional.
- `docs/plan/layout-transition-memo.md:20:| L-10 | `Layout(root, repo="target-repo")`: one Layout per repository, so existing method signatures stay unchanged and the golden fixture works through the default. A `repo` field is recorded in `sprint.toml` and `state.json`. Every function that loads state checks it equals `layout.repo` and raises the existing integrity error (exit 3). One proof: "wrong-repo Layout rejected". The earlier narrower `Layout.target_repo(name)` amendment is superseded. |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `docs/plan/layout-transition-memo.md:52:| `actl-repo/` | `records/` |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `docs/plan/layout-transition-memo.md:53:| `actl-repo/specs/<tag>/` (hashed artifacts) | `records/<repo>/<tag>/` |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `docs/plan/layout-transition-memo.md:54:| `actl-repo/specs/<tag>/runs/` | `sprints/<repo>/<tag>/runs/` |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `docs/plan/layout-transition-memo.md:55:| `handoff/<tag>/` | `sprints/<repo>/<tag>/mailboxes/` |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `docs/plan/layout-transition-memo.md:58:| `homes/<role>`, `Layout.homes` | `profiles/<role>`, `Layout.profile` |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `docs/plan/layout-transition-memo.md:59:| `ev-NNN.json`, `schemas/ev.json` | `verification-NNN.json`, `schemas/verification.json` |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `docs/plan/layout-transition-memo.md:60:| `qual-NNN.json`, `schemas/qual.json` | `qualification-NNN.json`, `schemas/qualification.json` |` — Normative old→new map and L-10 text; must retain legacy spellings.
- `proof/stage0/SURVIVOR_ANALYSIS.md:36:S11-09 `layout.py:123` `0o755` to `0o756` (`actl-repo/specs`): killed-by `test_base_tree_exact_modes_and_exact_dir_set[...]`.` — Historical mutation survivor notes against pre-transition paths/schemas; not a live gate.
- `proof/stage0/SURVIVOR_ANALYSIS.md:90:S11-51 schemas/ev.json:28 seq minimum 1 to 0: killed-by test_pinned_bounds[ev:seq:minimum] and the lint.` — Historical mutation survivor notes against pre-transition paths/schemas; not a live gate.
- `proof/stage0/SURVIVOR_ANALYSIS.md:91:S11-52 schemas/ev.json:75 additionalProperties false to true: same as S11-47.` — Historical mutation survivor notes against pre-transition paths/schemas; not a live gate.
- `proof/stage0/SURVIVOR_ANALYSIS.md:92:S11-53 schemas/qual.json:63 additionalProperties false to true: same as S11-47.` — Historical mutation survivor notes against pre-transition paths/schemas; not a live gate.
- `schemas/ev.json:3:  "$id": "ev.json",` — Part B only — rule 3 forbids schema edits in Part A.
- `schemas/qual.json:3:  "$id": "qual.json",` — Part B only — rule 3 forbids schema edits in Part A.
- `src/actl/INTERFACES.md:407:* **Side effects:** Accepts `closure_path` at either `implementer-outputs/closure.json` or `closure-{seq:03d}.json`, stamps `kind="closure"`, `seq`, `parent=contract_id` into `runs/closure-{seq:03d}.json`, sets `ev.parent = f"closure-{attempt_seq:03d}.json"`, forces `G2` red if `session_info` has `lost=True` or `hard_cap=True`, evaluates post-`O2` blocked preconditions when `reason == "blocked"`, writes `runs/ev-{seq:03d}.json` (plus `handoff/{tag}/implementer-inputs/prior_attempt.json` when `exit_code == 1`, S1-R7), increments `closures_submitted` once per stamped closure via `update_state`, merges `scan_tripwires` output into `ev.tripwires` (a non-empty result makes the run red when `strict_tripwire=True`), and only then unlinks original `<LOG_DIR>/<session>.log` and `<METADATA_DIR>/<session>.exit`.` — Stage-1 verify_impl side-effect prose still says runs/ev- and handoff/; O-17 records rename; Part B rewrite.
- `src/actl/INTERFACES.md:597:* **`attempt.json` (`handoff/{tag}/implementer-inputs/attempt.json` — `schemas/attempt.json`, `S1-R8`, `S1-R9`):**` — attempt.json path still uses handoff/.../implementer-inputs vocabulary; mailbox rename in O-17; Part B.
- `src/actl/INTERFACES.md:602:### 3.5 `prior_attempt.json` (`handoff/{tag}/implementer-inputs/prior_attempt.json` — `schemas/prior_attempt.json`)` — §3.5 prior_attempt.json header still uses handoff/ path form; same justification as line 597.
- `src/actl/INTERFACES.md:759:  - `Layout.records` replaces `Layout.actl_repo` (matching memo section 3 rename of `actl-repo/` to `records/`).` — O-17 rename note intentionally mentions the legacy name being replaced.
- `src/actl/INTERFACES.md:760:  - `Layout.profile(role)` replaces `Layout.homes(role)` (matching memo section 3 rename of `homes/<role>` to `profiles/<role>`).` — O-17 rename note intentionally mentions the legacy name being replaced.
- `src/actl/INTERFACES.md:761:  - `Layout.mailboxes(tag)` replaces `Layout.handoff(tag)` (matching memo section 3 rename of `handoff/<tag>/` to `sprints/<repo>/<tag>/mailboxes/`).` — O-17 rename note intentionally mentions the legacy name being replaced.
- `src/actl/layout.py:66:        return self._resolve_contained(self.root / "actl-repo")` — Part B only — rule 3 forbids editing src/actl/*.py in Part A.
- `src/actl/layout.py:69:    def target_repo(self) -> Path:` — Part B only — rule 3 forbids editing src/actl/*.py in Part A.
- `src/actl/layout.py:116:    def homes(self, role: str) -> Path:` — Part B only — rule 3 forbids editing src/actl/*.py in Part A.
- `src/actl/layout.py:117:        return self._resolve_contained(self.root / "homes" / _check_role(role))` — Part B only — rule 3 forbids editing src/actl/*.py in Part A.
- `src/actl/layout.py:124:        for d in ("handoff", "workspaces", "repos", "homes"):` — Part B only — rule 3 forbids editing src/actl/*.py in Part A.
- `src/actl/layout.py:127:            _mkdir(self.homes(role), 0o755)` — Part B only — rule 3 forbids editing src/actl/*.py in Part A.

---

## 7. Stop

Part A authoring complete. Do not implement code changes in `src/actl/`. Part B follows cross-family delta review.
