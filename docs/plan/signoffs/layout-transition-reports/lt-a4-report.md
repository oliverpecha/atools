# LT-A4 Report — Layout transition part A4 (oracle defects)

Branch: `wip/layout-a4` in `~/atools-lt-a4`
Base: `68e2e96` (part A integration)
Memo: `docs/plan/layout-transition-memo.md`
Runbook: `/tmp/Runbook_layout_a4.md`

Commits (68e2e96..HEAD):
- `ce828ad` test(actl): correct oracle defects TD-1 to TD-4 (WI-S0-PROOF)
- `b1bd811` docs(plan): state both workspace path forms in S0-R3.2 (WI-S0-SPEC)
- `f5180b2` docs(actl): align ensure_base_tree and sprint-proposal with L-8/L-10 (WI-IFACE)
- `06602d9` test(proof): refresh P-S0-02 pins after LT-A4 oracle fixes (WI-S0-PROOF)

## Defect evidence (pre-fix, raw)

### D1 — main vs amended no-tag workspace line

```
$ git show main:test/actl/test_p03_layout.py | sed -n '/workspace("verify-implementer")/p'
    if lay.workspace("verify-implementer") != r / "workspaces" / "verify-implementer": fail("workspace(name) wrong")

$ sed -n '36,37p' test/actl/test_p03_layout.py   # after fix
    if lay.workspace("implementer-006", TAG) != r / "sprints" / "target-repo" / TAG / "workspaces" / "implementer-006": fail("workspace(name, tag) wrong")
    if lay.workspace("verify-implementer") != r / "sprints" / "target-repo" / "workspaces" / "verify-implementer": fail("workspace(name) wrong")

$ sed -n '56p' src/actl/INTERFACES.md
* **Return value:** `Path` to `$ACTL_ROOT/sprints/{self.repo}/{tag}/workspaces/{name}` when `tag` is provided, else `$ACTL_ROOT/sprints/{self.repo}/workspaces/{name}`.
```

### D2 — wrong-repo guard shape (TD-2)

Part A wrote state under `lay_cat` then read with `lay_dog` (disjoint trees). Fix: `lay_dog.ensure_sprint_tree(TAG)`, write `"repo": "cat_app"` into `lay_dog.state_file(TAG)`, `seq.read_state(lay_dog, TAG)` raises; positive control with `"repo": "dog_app"` reads without error.

### D3 — symlink plant path

Before: `ws_dir = lay.root / 'workspaces'`. After: `ws_dir = lay.root / "sprints" / lay.repo / "workspaces"` (create parents). `lay.workspace("escape")` and `pytest.raises(ValueError, match=...)` unchanged.

### D4 — expected includes repo

`expected` dict gains `"repo": lay.repo`; `st == expected` and key-set assertion kept.

### D5 — INTERFACES

(a) `ensure_base_tree` side-effects: does not write `profiles/README.md`; `actl init` writes it (L-8).
(b) `sprint-proposal.json` forbids list no longer includes `repo`; prose states `repo` is optional and not rejected. Fenced `interfaces.json` had no forbid-repo claim.

### D6 — pin refresh script output

```
ok src/actl/INTERFACES.md: 4fabf5941beb -> 9a446778715f
ok test/actl/test_p03_layout.py: a626f19309f2 -> 2e5d62218c78
ok test/actl/test_s0_gap_layout.py: 2f306f2de868 -> d1024fe8824b
ok test/actl/test_s0_gap_sprint_initial_state.py: 76ffa9963687 -> 7260c0b97b58
ok INTERFACES allow-mod prefix -> 9a44677
wrote proof/stage0/P-S0-02.sh
==== re-run ====
SKIPPED: already-applied marker present
```

Marker: `# LT-A4 pin refresh applied`

---

## Delivery gate (raw)

### 1. Ancestor + commits

===== GATE 1: ancestor + commits =====
merge-base exit:0
--- log ---
06602d9 test(proof): refresh P-S0-02 pins after LT-A4 oracle fixes (WI-S0-PROOF)
f5180b2 docs(actl): align ensure_base_tree and sprint-proposal with L-8/L-10 (WI-IFACE)
b1bd811 docs(plan): state both workspace path forms in S0-R3.2 (WI-S0-SPEC)
ce828ad test(actl): correct oracle defects TD-1 to TD-4 (WI-S0-PROOF)
--- full messages ---
06602d9f6603f3b7021743838dacec7a808d3589
test(proof): refresh P-S0-02 pins after LT-A4 oracle fixes (WI-S0-PROOF)

Why:
ce828ad, b1bd811 and f5180b2 changed four gated blobs (three tests plus
INTERFACES.md); P-S0-02 must authorize the new hashes in both pin sites.

What changed:
- proof/stage0/P-S0-02.sh: re-pin INTERFACES.md, test_p03_layout.py, test_s0_gap_layout.py, test_s0_gap_sprint_initial_state.py; update is_allowed_modification grep prefix; LT-A4 marker

Result:
Idempotent re-run prints SKIPPED via marker; four ok edits on first pass.
----
f5180b201739a83404457b43df1865a74aa499d2
docs(actl): align ensure_base_tree and sprint-proposal with L-8/L-10 (WI-IFACE)

Why:
ce828ad/spec fix leave two stale INTERFACES statements that contradict
ratified decisions 3 and 4 and /tmp/lt-b-report.md: ensure_base_tree
claimed to write profiles/README.md; sprint-proposal description forbade
repo.

What changed:
- src/actl/INTERFACES.md: ensure_base_tree side-effects defer profiles/README.md to actl init (L-8); sprint-proposal forbids list drops repo and states repo is optional and not rejected

Result:
INTERFACES prose matches Owner ratification; interfaces.json block unchanged (no forbid-repo claim).
----
b1bd8114cbdf45afc6084720938441dd41c88f87
docs(plan): state both workspace path forms in S0-R3.2 (WI-S0-SPEC)

Why:
ce828ad fixed the no-tag workspace oracle; S0-R3.2 still wrote a single
formula that always inserts {tag}, conflicting with INTERFACES 1.1 and
TD-1.

What changed:
- docs/plan/spec-S0.md: S0-R3.2 lists tagged sprints/{repo}/{tag}/workspaces/{name} and untagged sprints/{repo}/workspaces/{name}

Result:
S0-R3.2 matches INTERFACES 1.1 both forms; no other spec lines touched.
----
ce828ad4954da1a601d9a04752f989b5285691eb
test(actl): correct oracle defects TD-1 to TD-4 (WI-S0-PROOF)

Why:
68e2e96 part A left four oracle defects that make part B unfixable
without rewriting tests: no-tag workspace invented TAG (TD-1), wrong-repo
guard never saw a mismatched state file (TD-2), symlink planted under
legacy workspaces/ (TD-3), and initial state expected dict omitted repo
(TD-4 / L-10). Assertions stay at least as strong; positive control added
for the repo guard.

What changed:
- test/actl/test_p03_layout.py: no-tag workspace expects sprints/{repo}/workspaces/{name}; wrong-repo writes mismatched repo into lay_dog.state_file then raises, plus matching-repo positive control
- test/actl/test_s0_gap_layout.py: plant escape symlink under sprints/{repo}/workspaces
- test/actl/test_s0_gap_sprint_initial_state.py: expected includes repo=lay.repo

Result:
Four oracle defects fixed in test/actl; no skip/xfail; raises/assert retained or strengthened.
----
===== GATE 2: diff names =====
docs/plan/spec-S0.md
proof/stage0/P-S0-02.sh
src/actl/INTERFACES.md
test/actl/test_p03_layout.py
test/actl/test_s0_gap_layout.py
test/actl/test_s0_gap_sprint_initial_state.py
--- forbidden check ---
forbidden-count: 0

### 3. Weakening check
===== GATE 3: weakening check =====
--- test/actl/test_p03_layout.py ---
REMOVED assert/raises/parametrize/skip/xfail:
(none)
ADDED assert/raises/parametrize/skip/xfail:
(none)
counts removed=0 added=0
skip/xfail added:
(none)
--- test/actl/test_s0_gap_layout.py ---
REMOVED assert/raises/parametrize/skip/xfail:
(none)
ADDED assert/raises/parametrize/skip/xfail:
(none)
counts removed=0 added=0
skip/xfail added:
(none)
--- test/actl/test_s0_gap_sprint_initial_state.py ---
REMOVED assert/raises/parametrize/skip/xfail:
(none)
ADDED assert/raises/parametrize/skip/xfail:
(none)
counts removed=0 added=0
skip/xfail added:
(none)

### 4. bash proof/run_suite_actl_s0.sh
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
EXIT:1

### 5a/5b. exit_code + P-S0-27
===== GATE 5a: exit_code suite =====
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
EXIT:0
===== GATE 5b: P-S0-27 =====
OK: P-S0-27 suite conforms
EXIT:0

### 5c/5d. golden_selfcheck + selfcheck_mutations
===== GATE 5c: golden_selfcheck =====
ok: build is deterministic (01d880bc3176cdd8f31d72e67bb3eba54d634378)
ok: base_sha matches expected.d
ok: G5 self-test catches synthetic secret
ok: G6 self-test catches synthetic eval
ok: G6 self-test no false positive
ok: F006 self-test catches records/ path
ok: F006 self-test no false positive on bare word records
ok: golden artifact dirs use verification/qualification (not ev/qual)
ok: verification_base kind is verification
ok: qualification_base kind is qualification
ok: build_golden install path is repo-scoped under records/
ok: build_golden state template records repo field
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
EXIT:0
===== GATE 5d: selfcheck_mutations =====
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
ok: M19 detected (verification kind renamed back to ev)
      FAIL: verification_base kind is not verification
ok: M20 detected (qualification kind renamed back to qual)
      FAIL: qualification_base kind is not qualification
ok: M21 detected (verification dir renamed to ev)
      FAIL: golden artifact dirs missing verification/qualification or still have ev/qual
ok: M22 detected (build_golden records path reverted)
      FAIL: build_golden.sh missing records/target-repo install path
ok: M23 detected (repo field removed from state template)
      FAIL: build_golden.sh state template missing repo field
==========================================
selfcheck_mutations: control green, all 23 planted defects detected
EXIT:0

### 5e. audit --cursor (tail + verdict)

========================================================
Audit Verdict: 49 passed, 0 failed, 18 skipped, 2 warnings (profile=dev, adapter=cursor)
========================================================
EXIT:0

### 6. D3 grep + justifications + status
===== D3 grep (raw) =====
proof/stage0/p02_doctor_empty.sh:4:# Must exit 0, print one JSON object, write only $ACTL_ROOT/baseline.json, create no sprint/handoff tree, and not touch the repo.
test/actl/test_s0_gap2_layout_modes.py:55:        m[r / "sprints" / repo / TAG / "workspaces"] = 0o755
test/actl/test_p03_layout.py:36:    if lay.workspace("implementer-006", TAG) != r / "sprints" / "target-repo" / TAG / "workspaces" / "implementer-006": fail("workspace(name, tag) wrong")
test/actl/test_p03_layout.py:37:    if lay.workspace("verify-implementer") != r / "sprints" / "target-repo" / "workspaces" / "verify-implementer": fail("workspace(name) wrong")
test/actl/test_s0_gap_layout.py:11:    # Create symlink escaping root under sprints/<repo>/workspaces (no-tag form)
test/actl/test_s0_gap_layout.py:12:    ws_dir = lay.root / "sprints" / lay.repo / "workspaces"

===== git status --short =====
(end status)

#### D3 hit justifications

| Hit | Verdict |
|---|---|
| `proof/stage0/p02_doctor_empty.sh:4` | Comment only ("sprint/handoff tree"); does not create a bare `handoff`/`workspaces` dir under a Layout root. No fix. |
| `test/actl/test_s0_gap2_layout_modes.py:55` | Mode map key is already new-layout `sprints/{repo}/{TAG}/workspaces`. Not a bare root mkdir. No fix. |
| `test/actl/test_p03_layout.py:36-37` | Path expectations under `sprints/.../workspaces` (tagged + no-tag). Asserts paths; does not plant bare dirs. No further fix (D1 already corrected no-tag). |
| `test/actl/test_s0_gap_layout.py:11-12` | **Fixed (D3):** plants symlink at `sprints/<lay.repo>/workspaces/escape`. |

Only the D3 symlink plant created a bare legacy directory; that was fixed. Remaining pattern hits are comments or new-layout path assertions.

#### Final status

`git status --short` empty (see raw block above).

## Stop

Per runbook: stop after writing `/tmp/lt-a4-report.md`. No push, no merge.
