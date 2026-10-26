# Step 0 Doctor Hardening Signoff (OPB-2)
Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
Date: 2026-10-26. Base: 4e16cc3. Branch: wip/s0-doctor-hardening.

## 1. Scope and Objective
Close doctor.py survivors identified in seed 61, 67, and 71 mutation runs under OPB-2 (D-29 follow-up) prior to Stage 1 integration.

## 2. Test Files Added
- test/actl/test_s0_gap5_doctor_helpers.py
- test/actl/test_s0_gap5_doctor_report.py
- test/actl/test_s0_gap5_doctor_suites_fs.py
- test/actl/test_s0_gap5_doctor_contract.py

## 3. Accepted Survivors and Equivalence Justifications
Per decision Vela-1 and Owner ruling:
1. timeout=600 constants (src/actl/doctor.py lines ~150, 170, 171): accepted survivors. No contract specifies the internal suite execution timeout of 600 seconds.
2. Proven equivalent survivors (49:16, 85:75): accepted with recorded review arguments.

All other token sites were killed by the expanded hermetic test suite.

## 4. Gate Verification
- proof/run_suite_actl_s0.sh: PASS (19/19)
- pytest test/actl: PASS
- audit/atools-compliance_audit.sh --cursor: PASS
- audit/atools-compliance_audit.sh --self-test: PASS
