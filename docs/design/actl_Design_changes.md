## Isolation and identity

1. **Five accounts, one per persona.** The accounts are `actl`, `architect`, `challenger`, `implementer` and `curator`. The UID, group, directory prefix and `sudo -u` target are all the persona name. `ship` and Archivist become Curator, so `archivation-plan` becomes `curation-plan` and `ship-inputs` becomes `curator-inputs`.
2. **One group per role.** Actl is a member of each role group, and no agent ever holds gid `actl`. The live wrapper uses `--regid=implementer`, and each role gets its own verify directory (`actl-verify-{role}`).
3. **Symmetric mailbox.** Every role has `{role}-inputs/` (staged read-only by actl) and `{role}-outputs/` (role-writable). `plan-box` splits into `architect-outputs/` and `challenger-outputs/`.
4. **Removed mechanisms.** Delete the unlink/re-create trick, the `0440` and `0750`/`0770` toggling, and the thread restore. Keep one vault copy of the Architect thread for recovery only.
5. **Cleanup.** The Challenger gets the same `pkill` and private `/tmp` cleanup as `implementer` and `curator`. Phase 2 qualification runs as `challenger`.
6. **`target-repo` access.** `repos/target-repo` becomes a group-readable export (`0750 actl:cloners`) that only actl can write to. Oracle material stays only in `records`, which is `chmod 700`.
7. **P restated minimally.** P covers the Implementer's LLM session. Add one residual-risk line: candidate code can read the oracle during Offline and Live runs. The defences are mutants, the Live Run and graduation. No extra lint or output caps.

## Sprint, policy and approvals

8. **`actl sprint new <sprint_tag>` is the single entry point.** There are two modes, interactive Q&A or `--spec spec.md` import. Both create the directory, `state.json` and a draft `sprint.toml` immediately, and pin `base_sha`. `sprint.toml` records `spec_source`. In import mode a short Architect turn authors `solution_key.patch`, and its questions use the existing `hold`.
9. **`sprint.toml` is the per-sprint immutable record.** It holds `sprint_tag`, `base_sha` and every resolved policy value, fully copied from `graph.toml` at creation. `graph.toml` keeps the topology and installation-wide defaults.
10. **Completeness gate.** Actl refuses to dispatch the Challenger while a required field is unset. `live_run` is required, has no default, and the Architect chooses it. Defaults remain for `solution_key_exposure = full` and `approval_live_run = architect`.
11. **Owner signature only when needed.** It is required when `live_run = required` and `approval_live_run = architect`, and covers `sprint_tag || sprint_sha256`. The live wrapper verifies it, reads the policy, and checks the allowlisted env-var names. The Architect's `live-decision` binds `contract_sha256 || head_sha`, and the wrapper checks that its owner is `architect`. `live-delegation.hmac` is removed.
12. **`owner_review_triggers`.** This is a list of actions the Owner must confirm. If the Architect's `resolution.action` is on the list, actl sets `hold` until the Owner countersigns. `mutant_waiver_authority` folds into it as `waive_mutant`. The six hardwired Owner routes in §6.3 stay. Risk tier, time of day and availability are removed as routing inputs and only affect notification delivery.
13. **Dead knob removed.** Delete `approval_archivation_plan`, because Owner approval is unconditional.
14. **Backlog.** The Architect no longer curates the backlog. The Owner selects items, and `architect-notes.md` stays only as the compaction fallback.
15. **Work items.** One graph node per spec. Larger work is several sprints linked by an `after:` field. You never commented on this point specifically, so tell me if you want it changed.

## Counters, naming and escalation

16. **`seq` in `state.json`.** A single per-sprint counter, written only by actl, reserved before the artifact is written. If lost, it is rebuilt as the highest number in the filenames.
17. **Names.** Every immutable artifact is named `{kind}-{seq}` and records `kind`, `seq` and `parent`. No file refers to "latest". Actl resolves "current" from `state.json`. This replaces `spec-vN`, `oracles/vN`, `oracle-qual-vN` and `contract-vN`, and removes the numbering-reset collisions.
18. **Attempts.** `retries_*` become `max_attempts_{oracle,implementer,live,curator}`. Every dispatched session consumes one attempt, even when it produces no valid artifact. `hard_caps_tripped` stays as an annotation. `max_attempts_live` counts Live Run executions per epoch, so the old `retries_live=1` is `max_attempts_live=2`. "Recovery cycle" is no longer a counter.
19. **Budgets.** Baselines live in `sprint.toml`:
    - `max_attempts_*`
    - `min_attempts_before_block`
    - per-persona `hard_cap`
    - new `max_epochs` (escalate to the Owner when exceeded)

    `state.json` holds only consumed counters and granted increments. The contract stores a `sprint_sha256` reference instead of copying budgets.
20. **Unified escalation table.** Every record carries `stage`, `trigger`, `to` and `legal_actions`:

    | Trigger | Stage | Routes to | Legal actions |
    |---|---|---|---|
    | `attempts_exhausted` | oracle | Architect | `grant_attempts`, `waive_mutant` (only if `failing_checks` is empty), `escalate_owner` |
    | `attempts_exhausted` | implementer | Architect | `grant_attempts`, `reopen_oracle`, `escalate_owner` |
    | `attempts_exhausted` | curator | Owner | `grant_attempts`, `abort` |
    | `blocked` | implementer | Architect | `update_scope`, `reopen_oracle`, `grant_attempts`, `escalate_owner` |
    | `session_cap` | any | Architect for oracle/implementer; Owner for architect/curator | `grant_attempts`, `escalate_owner` |
    | `live_failed` | live | Architect, plus an Owner alert | `grant_attempts`, `reopen_oracle`, `retry_live` |
    | `halt` | actl | Owner | `resume`, `abort` |

    The `halt` row covers integrity halt, wrapper mismatch, unsupported cap and Architect unavailable.
21. **Examples.** In the oracle-exhaustion example, remove `closures_submitted` and `hard_caps_tripped`, because those are Phase 3 counters.
22. **`scope.txt` precedence.** Default deny. `FROZEN` beats any `ALLOW` glob. Only a literal-path `ALLOW` thaws a frozen path.
23. **Cross-family stays preferred.** Log `model_family` in `sessions.tsv` and add `same_family: true` to the `diff-risk-review.md` disclosure. The matrix cell for Challenger vs Architect becomes plain **F**.

## Verification and Phase 4

24. **Blocked rule.** `solution_key_divergence` is required only when `blocking_step` cites a proof step. It is `null`-able for `guard:scope`, `test:{name}` and architectural blocks.
25. **Check IDs.** The IDs, used everywhere:
    - Q1–Q5 for Phase 2 qualification
    - G1–G6 for Phase 3 closure guards
    - O1 (proofs and `probe.sh`) and O2 (repo Test)
    - L for the Live Run
    - E1.1–E1.6 for Phase 4

    Add the ID as an extra field in `ev-NN.json` and keep `steps[].cmd`. "Stage 2a/2b" and "Step 1/2/3" are retired.
26. **Phase 4 Edge 1.** Delete the conditional in E1.4, since E1.5 always runs. Add a mutant → requirement mapping to `coverage.md`. Each graduated test must either fail on `base_sha` or kill a mutant mapped to its proof. §5.6 becomes the only normative text, and §1.6, §3.2 and §4.4 reference `E1.x`.
27. **Edge styling.** Control edges are solid, except human-acceptance edges, which are dashed (`actl` → Owner).

## Terminology cleanup

28. **Invariants table in §2.** It defines S, P, F and C. C is what "Premise 7" says. "Premise 5" is dropped in favour of a pointer to the §5.2 four-layer defence.
29. **Forward references.** After the check IDs are introduced, every use in Phase 2 and elsewhere points to them.

I can draft these as a patch against the spec, ordered so the renames (1, 16–17, 25) land first.


# I made these judgment calls beyond what we agreed, so check them:

Closure seq: an Implementer attempt reserves its seq at dispatch, and its workspace, branch and closure share that number, so those names never collide.

E1.1 count check: the legacy test-count re-check moved out of E1.1, because G4 and E1.2 already cover it.

Attempt budgets: the Architect and Owner are not attempt-budgeted. Their failures go through halt or session_cap.

E1.4 rule: at least one new test must fail at base, and any test that passes at base must kill a mapped mutant at E1.5.

Live decision file: the live wrapper reads it directly from architect-outputs/. Its owner must be the architect account, and actl keeps an audit copy.

Sprint dependencies: I added an optional after = [] field to sprint.toml for linking dependent sprints, which §7 now relies on.

Revision notes: I added a short block at the end. Delete it if you don't want it in the spec.
