# Step 0 Doctor Hardening Signoff (OPB-2)
Authored-by: Vela-S2 (Argon 4 Medium for c98e94d, Flash 3.8 High for 842906b, as reported by the Owner), model family: Gemini
Date: 2026-10-26. Branch: wip/s0-doctor-hardening, created from c0080ba; integrated on main 4e16cc3 as c98e94d (tests: 849635a).

## 1. Scope and Objective
Close the four doctor.py survivors found at seed 61 (lines 117, 154, 164, 170) under OPB-2 (D-29 follow-up) before Stage 1 integration. Seeds 67 and 71 were verification runs and found nothing new.

## 2. Test Files Added
- test/actl/test_s0_gap5_doctor_helpers.py
- test/actl/test_s0_gap5_doctor_report.py
- test/actl/test_s0_gap5_doctor_suites_fs.py
- test/actl/test_s0_gap5_doctor_contract.py

## 3. Accepted Survivors and Equivalence Justifications
Decision of Vela-1 (GPT 6.1 Sol concurred); the Owner ruled yes on 2026-10-27:
1. timeout=600 constants (src/actl/doctor.py lines ~150, 170, 171): accepted survivors. No contract specifies the internal suite execution timeout of 600 seconds.
2. Proven equivalent survivors (49:16, 85:75): accepted; arguments in section 5.

In the scratch hand-check, 63 of 68 token sites were killed (section 5). mutate.py sampled 21 distinct sites over seeds 61, 67 and 71.

## 4. Gate Verification
- proof/run_suite_actl_s0.sh: PASS (19/19)
- pytest test/actl: PASS
- audit/atools-compliance_audit.sh --cursor: PASS
- audit/atools-compliance_audit.sh --self-test: PASS

## 5. Evidence
Tests commit 849635a; merge and signoff c98e94d.
Mutation (tools/mutate.py --only src/actl/doctor.py --n 8 --timeout 240, clean committed tree, under flock):
- seed 61: 8 sampled, 7 killed, 1 survived (170:91 600 to 601, accepted). The four seed-61 originals:
  117, 154 and 164 killed, 170 accepted.
- seed 67: 8 sampled, 7 killed, 1 survived (150:76 600 to 601, accepted).
- seed 71: 8 sampled, 8 killed.
- Total 24 draws on 21 distinct sites: 22 killed, 2 accepted constants, 0 unexplained. Stop rule not triggered.
Hand-check in a scratch export (not mutate.py): 68 token mutants, 63 killed; survivors 49:16 and 85:75 (equivalent),
150:76, 170:91 and 171:94 (accepted constants). Plus 13 distinct structural mutants (15 entries; S9 and S13 repeat S5), all killed (S8 by a suites_fs test, not by the contract file); S8, S10, S11 and S12 were not run without the contract file.
Equivalence arguments:
- 49:16 (> to >= in _tail): differs only when len(out) == max_chars, and out[-max_chars:] is then the same string as out.
- 85:75 ([:3] to [:4] on the version digits): a longer tuple with an equal 3-prefix compares greater, never less, so the
  comparison against (0,1,4) is unchanged.
Accepted constants (150, 170, 171): no contract names 600 for doctor (spec-S0 F-15 concerns wait_session). Asserted instead:
a positive finite timeout on all five suite and audit calls, the exact command vectors and cwd. GPT 6.1 Sol concurred:
record them as accepted constant-pinning survivors, not equivalent mutants.
Evidence caveat: 49, 85 and 171 were not sampled by mutate.py at seeds 61, 67 and 71; their status rests on the
arguments and the hand-check.
Review: GPT 6.1 Sol (top variant; High and Thinking cannot be told apart in the Perplexity wrapper), two rounds before the commit, both approve with conditions. Round 1 reviewed doctor_helpers, doctor_report and doctor_suites_fs; round 2 reviewed only doctor_contract, before its two conditions. The committed contract file is the round-2 version plus the hunks GPT specified (exact heavy-command vectors, str(p) assertions in the Path stubs); GPT did not see the final text. The 600-constant follow-up covered no file.
Independence (PB-9): tests by Vela-OPB (Sonnet 5.5, Owner-reported and not instance-verified; the instance says it cannot see its model),
reviewer GPT 6.1 Sol, signoff by Vela-S2 (Argon 4 Medium for c98e94d, Flash 3.8 High for 842906b, as reported by the Owner).
