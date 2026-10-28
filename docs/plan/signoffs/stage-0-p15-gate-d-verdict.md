# Stage 0 P-S0-15 Gate D verdict (D-28)

Date: 2026-10-28. Branch: wip/fix-p15. Accept SHA: fa3387d052dac9c69de04b5b194f31fd4d5acda6.
Author (this session): Cursor-S1 (Grok 4.6), model family Grok / xAI.
Challenger: GPT-6 (OpenAI), Gate D D-28 round 3. Verdict: ACCEPT, zero BLOCKERS.
Scope: test/actl/test_p15_expected.py and proof/stage0/P-S0-02.sh vs main 8efed76.
No S1/S2 file changes. No production tag from Auto.

## Worktree snapshot (close-out)

- git status --short: empty
- git rev-parse HEAD: fa3387d052dac9c69de04b5b194f31fd4d5acda6
- Owner-run VELA 18 at 20261028T1820Z: RESULT OK fa3387d
- S0: 19 Passed, 0 Failed, 0 Environment
- audit --cursor: 49 passed, 0 failed, 18 skipped, 2 warnings
- P-S0-15 on 1a891fb: PASS
- P-S0-15 on 49861fc: PASS
- P-S0-02 pin: test/actl/test_p15_expected.py:8399c63e79b2a8dd89b0ee2da76df2383c6cc46e
- bundle: 20261028T1820Z_s0_p15_d28_r3_delta.txt
  sha256=38a13b16709c95a9b944609b584a2db1c6ec5e1c989630da750fad9d65b155b9
- GPT file: 20261028T1820Z_s0_p15_gate_d_r3.txt
  sha256=54ed66bd3170847eeaad2e656108e3f2b54c8c7cf9964b620f2f0faeff1bfc70

## Challenger round-3 table (GPT-6, OpenAI)

| ID | Status | One-line assessment |
|---|---|---|
| D28-01 | CLOSED | Adjacent s1.json/s2.json share s1_only; ValueError required. |
| D28-02 | CLOSED | s1.json/s3.json share duplicate_across_files; s2.json is middle_only. |
| Q1 loaders | CLOSED | ignore base.json; drop/alter base case; ignore fragment responses; ignore fragment cases; adj+nonadj duplicates. BAD_LOADERS_REJECTED. |
| Q2 pin | CLOSED | Allowlist retargets that one test blob only; frozen-path checks unchanged. |
| Q3 S0-R14 / INTERFACES 3.7 | CLOSED | Duplicate case keys across non-base fragments raise ValueError. |

## Rounds (blockers raised, closing commit)

| Round | Kind | Blockers raised | Closing commit |
|---|---|---|---|
| R1 | GPT | D28-01 adjacent-only coverage | a903b65 |
| R2 | GPT | D28-02 adjacency-only duplicate check | fa3387d |
| R3 | GPT | none; D28-01 and D28-02 CLOSED; ACCEPT | fa3387d052dac9c69de04b5b194f31fd4d5acda6 |

R1 reviewed 581d57b (keep-base merge oracle). R2 closed D28-01 on a903b65.

## Accepted ADVISORY dispositions

- Finite-test oracle mimicry: ACCEPT for this closure round. Filename-specific and N-window variants stay ADVISORY.
- Broader duplicate permutations: DEFER. The non-adjacent example addresses D28-02 without every fragment count and position.

## STOP

No merge, no push, no tags from Auto. Owner may ff-merge wip/fix-p15 when ready.
