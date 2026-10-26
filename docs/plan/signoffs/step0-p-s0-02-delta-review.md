# Step 0: P-S0-02 rework, delta review record (D-28)

Date: 2026-10-26. Ruling: kickoff v3 ruling 2 (D-41). Work item: WI-S0-PROOF.

## Change
- 3148198 `proof/stage0/P-S0-02.sh`: the integration-mode loop that checked added files against `is_allowed_addition` is removed. Negative self-check 1 now modifies the tracked file `bin/arouter` and requires the exact diagnostic `S0-R2.1: unauthorized file change: bin/arouter`.
- d813ad0 `proof/stage0/P-S0-02.sh`: the restore of `bin/arouter` in self-check 1 is fail-closed (checkout status, status call status, clean state).
- All blob pins and the PB-2 frozen-path checks (modify, delete, rename, `expected.d/base.json`) are unchanged. The pin of `tools/mutate.py` was refreshed separately in 4fb7aed and ecf7266 (D-47).

## Independence (PB-9)
- First patch: Argon 4. Narrowed (two small edits, byte-safe writer) by the Step 0 assistant thread (model family not recorded).
- Reviewer: GPT 6.1 Sol thinking, three rounds, all on the supplied diff without execution.
- Implementer sessions: Cursor agent through `arouter` tier `auto` (asessions shows the model as `default`).

## Rounds
1. Argon patch: not approved as supplied. Findings: `bin/arouter` must be tracked (confirmed tracked); whole-file rewrite may change line endings (raw-byte writer, no CR in file); anchors need exact whitespace (assert count 1); the redundant edit to `is_allowed_modification` was dropped.
2. Slim diff of the narrowed patch: APPROVE WITH CONDITIONS. Major: integration mode accepts additions under frozen paths by design, until P-S1-02 exists no check gates additions; self-check 1 could pass for the wrong reason, so the exact diagnostic, the probe write and the restore must be verified. Minor: `expected.d/base.json` probe is not restored before the INTERFACES probe (pre-existing); the PB-2 scan uses `-M` not `-C`, so the `C*` branch never fires (pre-existing); the signal trap does not exit.
3. Recheck of the committed first revision (3148198): CONDITIONS. The restore check could fail open (unchecked checkout, a failed status call gives empty output). Fixed in d813ad0 with the replacement text GPT supplied, verbatim. d813ad0 was not sent for a fourth round.

## Accepted consequences and backlog
- Until P-S1-02 exists, nothing in P-S0-02 gates added files in integration mode (D-41).
- Backlog, not done: restore `expected.d/base.json` after its probe; enable copy detection or drop the `C*` branch; make the INT/TERM trap exit.

## Gates
Before each commit: `proof/run_suite_actl_s0.sh` 19 passed, 0 failed, 0 environment; audit `--cursor` 49 passed, 0 failed, 18 skipped, 2 warnings. After 3148198 and d813ad0: `P-S0-02.sh` exit 0.

## Approval
Owner approval of the merge is the push of the Step 0 branch; it is not separately recorded here.
