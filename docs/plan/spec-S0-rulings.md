# spec-S0-rulings.md - errata to spec-S0.md after the Owner rulings of 2026-10-20
Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity

Apply these over spec-S0.md; nothing else in the spec changes.

## Design conflicts (spec-S0.md section 5) - resolved
| ID | Ruling | Effect |
|---|---|---|
| C-1 | 40-hex SHAs everywhere in schemas, state and JSON artifacts; short prefixes are display only | SA-25 closed. Fixtures already use 40-hex; new invalid cases `sprint/short_base_sha` and `contract/short_base_sha` |
| C-2 | `owner_review_triggers` items are `plan_deviation`, `budget_exceeded`, `critical_tripwire`, `manual_flag` | Replaces the five action names of INTERFACES 3.2. Fixtures changed: `sprint-proposal_base` now uses `manual_flag, budget_exceeded`; new valid `sprint_all_owner_triggers`; new invalid `trigger_old_vocabulary` (sprint and sprint-proposal) |
| C-3 | `ev.exit_code` is an integer 0..255 or null | Replaces `0|1|3`. New valid `ev_exit_255`, `ev_exit_null`; invalid cases `exit_code_above_255`, `exit_code_negative`, `exit_code_type` (the old `exit_code_enum` case with value 2 would now be valid and was removed) |

Both C-2 and C-3 change text that INTERFACES.md froze. Under PB-4 `src/actl/INTERFACES.md` (section 3.2, section 3.4 and the manifest where affected) must be edited with the Owner's note before Stage 0A implementation; until then P-S0-08 fixtures and INTERFACES disagree on purpose. Also check: the Design (4.1, 6.3) uses `waive_mutant` and the other escalation actions as the values of `owner_review_triggers`; the new vocabulary is different, so the Design text needs the same amendment or the two documents will contradict each other. The escalation `resolution.action` vocabulary (`grant_attempts`, `waive_mutant`, ...) is unaffected.

## Review items
| Item | Ruling | Where it lands in Stage 0 |
|---|---|---|
| F-11 | INTERFACES section 3 is normative; `schemas/*.json` mirror it with `additionalProperties: false` | P-S0-08 (`test_schema_files_shape` already checks this) |
| F-15 | `wait_session` default timeout 600 s | Stage 1 (S1-R14); no Stage 0 proof |
| F-16 | Missing entities raise `FileNotFoundError`/`KeyError` internally and map to exit 2 (`UsageError`) or 3 (`StateIntegrityError`) | Covered partly by P-S0-04/P-S0-11. Not yet pinned: which missing-entity cases map to 3. SA-5 stays as the working reading (2) |
| F-17 | implementer artifact id is `implementer-{attempt_seq:03d}` | `format_artifact_id` currently lists no `implementer` kind (INTERFACES 1.2); the manifest/INTERFACES text needs that kind added; `parse_seq_from_name` already accepts `implementer-NNN` |
| F-18, F-19 | Logged as proposed decisions, deferred to Stage 2 | None |
| F-24, F-25, F-27 | `state_lock` is thread-local re-entrant on `runs/state.lock` via `fcntl.flock`; exit 3 on acquisition failure | Re-entrancy and cross-process exclusion are exercised by P-S0-05 (threads, 10 processes, SIGKILL). The exit-3-on-lock-failure case has no proof yet; proposed addition: make the lock file unopenable (directory at that path) and expect `OSError` from `state_lock` and exit 3 from `actl sprint new` |

## Counts updated in S0-R7.6
24 valid and 59 invalid documents (11 kinds, at least 4 invalid per kind).
