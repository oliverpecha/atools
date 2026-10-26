# Step 0: mutation evidence and the D-29 outcome

Date: 2026-10-26. Harness: `tools/mutate.py` (mutates HEAD in a detached worktree). Seeds used so far: 7, 11, 23, 37, 41, 53, 59, 61.

## Seed 59 on 4fb7aed (new map entries)
| Target | Mutants | Killed | Survived | Note |
|---|---|---|---|---|
| src/actl/cmd_* | 12 | 6 | 6 | untested branches, never mutated before |
| src/actl/doctor.py | 4 | 0 | 4 | |
| src/actl/errors.py | 0 | n/a | n/a | no mutation sites |
| src/sessions/* | 16 | 0 | 16 | wrong mapping (router tests); entries removed in ecf7266 (WI-TOOLS-5) |

The 10 survivors: cmd_init.py:15 and :29, cmd_sprint.py:14, cmd_next.py:14, cmd_doctor.py:23 and :25, doctor.py:67, :131, :172, :247. All were untested branches (required CLI arguments, the `created` flag, text output, `refresh` default, linger state, audit output joining, `proof/out` rewrite), not regressions: these modules had never been in the map.

## Tests and re-run
- 56a5326 adds test/actl/test_s0_gap5_{cmd_args,cmd_doctor_init,doctor}.py (12 tests), merged in c0080ba. pytest 829 passed (817 plus 12).
- Seed 59 re-run on the committed tests: cmd_init 4/4, cmd_sprint 2/2, cmd_next 2/2, cmd_doctor 4/4, doctor.py 4/4 killed; 16 of 16, the same mutants as before; all 10 original survivors killed.
- Seed 61 (fresh): cmd_init 4/4, cmd_sprint 2/2, cmd_next 2/2, cmd_doctor 4/4 killed; doctor.py 0 of 4 killed. Open survivors: doctor.py:117 (`or` to `and`, timeout lookup), :154 (`or` to `and`, suite tail), :164 (`0` to `1`, default audit dict), :170 (`600` to `601`, audit timeout; pins a constant). doctor.py has 68 mutable sites and each seed samples 4, so further gaps are likely.

## Independence (PB-9)
Tests: Gemini Flash 3.8 High. Revised before commit by Vela-OPB (Claude Sonnet 5.5 as reported by the Owner): Layout guard, direct `cli.main(...) == 2` asserts, hermetic doctor fixture, narrow stdlib proxies, `sys.path` restore. Reviewer: GPT 6.1 Sol thinking, APPROVE WITH CONDITIONS, conditions applied by the reviser. A recheck of the final revised files by GPT was requested; its verdict is not recorded here.

## D-29 outcome
Owner decision, option A (2026-10-26): Step 0 merges and is pushed with the four seed-61 doctor.py survivors open. A doctor.py hardening work item (tests only, WI-S0-PROOF, branch wip/s0-doctor-hardening) must close them before the Stage 1 merge, which is the next D-29 trigger, and the Stage 1 merge reruns the harness with a seed not used before.

## Not verified
Equivalence of any survivor was not proven; none of the four open ones is equivalent by inspection.
