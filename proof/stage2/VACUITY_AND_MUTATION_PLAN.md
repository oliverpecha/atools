
# Stage 2 Vacuity and Mutation Plan (Seed 79)

Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
Date: 2026-10-27. Reserved Seed: 79.

## 1. Experimental Three-Stand-In Vacuity Verification

Every proof `P-S2-01`..`P-S2-18` in `proof/run_suite_actl_s2.sh` is verified against four configurations:

1. **Base (`4e16cc3`, no Stage 2 implementation):** `0 Passed, 18 Failed, 0 Environment` (Exit `1`).
2. **Stand-in (a) — Empty modules (`PRIORITY = 10`, empty `prompts/*.md`):** `0 Passed, 18 Failed, 0 Environment` (Exit `1`).
3. **Stand-in (b) — Always-succeed stubs (all functions/handlers return `0`, `True`, or dummy `dict`/`tuple`):** `0 Passed, 18 Failed, 0 Environment` (Exit `1`).
4. **Stand-in (c) — Always-fail stubs (all functions/handlers raise `RuntimeError("always fail")` or return exit `1`):** `0 Passed, 18 Failed, 0 Environment` (Exit `1`).

Why stand-ins (a), (b), and (c) fail on every proof:

* Every pytest file (`test/actl/test_s2_*.py`) invokes the actual Stage 2 entrypoints (`allocate_turn`, `latest_turn`, `resolve_turn`, `promote_role`, `phase12.evaluate`, `actl.cli.main(["bundle", ...])`, `actl.cli.main(["unpack", ...])`, `actl.cli.main(["replay", ...])`, `actl.cli.main(["promote", ...])`) and asserts exact filesystem side effects, SHA-256 digests, permissions (`stat.S_IMODE`), and positive + negative return values.
* `P-S2-17` (`test_s2_prompts.py`) verifies exact authority and contract substrings inside `prompts/*.md` (rejecting empty files).
* `P-S2-18` (`P-S2-18.sh`) verifies `git rev-parse --git-dir`, `ACTL_FORK_POINT`, frozen-path immutability, and allowlisted additions (rejecting non-git directories and modified PB-2 files).

## 2. Mutation Testing Plan (Seed 79)

In Phase 2 (post-implementation), `tools/mutate.py --seed 79` is run against:

* `src/actl/turns.py`
* `src/actl/bundle.py` & `src/actl/cmd_bundle.py`
* `src/actl/envelope.py`
* `src/actl/unpack.py` & `src/actl/cmd_unpack.py`
* `src/actl/patchsynth.py`
* `src/actl/repair.py`
* `src/actl/replay.py` & `src/actl/cmd_replay.py`
* `src/actl/promote.py` & `src/actl/cmd_promote.py`
* `src/actl/next_rules/phase12.py`
