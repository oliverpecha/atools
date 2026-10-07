# atools Graph Protocol

Status: provisional normative design
Supersedes: `graph-exploration.md` v6 (frozen as historical input; do not edit)

This is the normative reference for running multi-agent code tasks with the atools suite. It states premises, identities, protocols and requirements. How the suite implements them is in `docs/architecture.md`. History lives in the commit log of the `agate` private repository, not here. This document changes only when a lesson changes a premise or a guard.

## 1. Premises

Each premise comes from repeated failures in earlier runs.

1. **Independence.** The party that writes the code never writes or edits the checks that judge it, and the checks have a reviewer who is neither of them. A check with no independent reviewer is a claim.
2. **Enforcement over prose.** A rule counts only if a guard checks it mechanically. A rule without a guard is a wish and is dropped. When a guard is added, the prose rule goes away.
3. **Evidence is generated.** Reports derive from command output. A claim with no command that produces it counts as nothing. A skipped check is SKIP, not PASS.
4. **Oracles are tested too.** Before freezing, an oracle must fail on a null implementation, fail when known defects are re-injected, and pass at a reference. A green result means something only if red was possible.
5. **A green oracle isn't truth.** Proofs can pass while the real output is wrong. Every oracle needs an end-to-end probe on real data and an independent reference for its signals.
6. **Measure before building.** Environmental problems are reproduced and quantified before any mitigation enters a brief.
7. **Fresh, short, small.** Each session gets its own context, scope, budget and oracle slice. Between sessions, only artifacts pass (a commit, a diff, a report), never a conversation.
8. **Disputes stop work.** When a check conflicts with code the implementer believes is correct, the implementer stops and reports. The oracle owner decides whether the check is wrong.

## 2. Components and trust domains

```
atools suite
├── arouter       model/runtime resolution
├── arun          one bounded agent invocation
├── asessions     runtime telemetry
├── amaster       graph/state orchestration
└── agate         oracle, scope, evidence, and acceptance
```

| Component | Owns | Does not own | Trust domain |
|---|---|---|---|
| `arouter` | Mapping a profile or role to a concrete model and runtime | Acceptance, state | Owner |
| `arun` | One fresh, bounded session: timeout, environment policy, usage metadata | Deciding whether work is accepted | Worker runtime |
| `asessions` | Execution telemetry, normalized into per-run cost records | Verdicts | Owner, read-only over runtime logs |
| `amaster` | Run state transitions | Oracle content, scope content, evidence evaluation | Owner |
| `agate` | Oracle execution, qualification, scope enforcement, evidence reports, acceptance ledger | Launching agents | Separate from the worker runtime |

`amaster` decides what happens next. `agate` decides whether a check holds. `amaster` calls `agate` and never evaluates evidence itself. `agate` is part of the suite but is a separate trust domain from agent runtime components.

## 3. Identities and profiles

| Identity | Owns | Can access |
|---|---|---|
| Owner | `agate` private state, API keys, the live gate run | Everything |
| Gate runner (optional low-privilege user) | Runs offline proofs with keys blanked | Worktrees, read-only oracle |
| Implementer | Its own worktree of the target repo | No keys, no oracle source, no global git config |

**Requirement R-ID-1.** In the production profile, the implementer's operating-system identity cannot read or edit the private oracle. Instructions are not a substitute.

**Profiles.**
- *Production:* separate implementer user, oracle inaccessible to it, keys absent from offline runs, root- or owner-owned hooks path the agent cannot edit. Required for unattended runs and sensitive repositories.
- *Development:* single user. Isolation relies on worktrees, tool permissions, hooks and post-run gate checks. Supported for local iteration only, and not the trust boundary for unattended work.

## 4. Roles

Author, implementer and oracle reviewer are three different parties. Models are placeholders; nothing in the oracle depends on a vendor.

| Role | Does | Model |
|---|---|---|
| Oracle author | Writes and tests proofs, E2E probe and scope file | `<MODEL_A>` |
| Implementer | Edits code only, inside scope, commits on `wip/*` | `<MODEL_B>` |
| Oracle reviewer | Tries to make each proof pass while its claim is false | `<MODEL_C>`, prefer a different family from A |
| Diff reviewer | Reads diffs for risk the gate can't see | `<MODEL_D>`, must differ from B |
| Owner | Commits oracle versions and the ledger, runs the live gate | Human |

**Requirement R-ROLE-1.** Role identity is recorded in the run manifest as data. A model tier name (`cheap`, `balanced`, `smart`) is never a role identity.

Whether reviewer-differs-from-author is a hard gate check or an overridable default is the owner's call. Parallel and cheaper implementers remain hypotheses until `sessions.tsv` shows cost per accepted item per model.

## 5. Artifacts

| Artifact | Meaning | Mutability |
|---|---|---|
| Task contract | Goal, scope, oracle version, definition of done | Frozen. Changes only via a new version and a superseding run |
| Oracle | Scope file, proofs, E2E probe, qualification manifest | Versioned; owner-tagged |
| Implementation brief | Compact packet for one fresh session | Regenerated for every session |
| Session | One bounded `arun` invocation | Immutable record |
| Run | One execution of a contract version | Ends in accepted, rejected or superseded |
| Evidence report | Output derived from commands | Generated |
| Acceptance ledger | Accepted, open, deferred, each with evidence | Gate-filled, owner-committed |

```
contract v1 ── run R1 ── implementation sessions S1, S2
                      \
                       \ superseded by
                        contract v2 ── run R2 ── implementation session S1
```

**Requirement R-FREEZE-1.** Oracle files, scope and definition of done must not change inside a run. Any change creates a new contract version, is requalified, and starts a new run.

**Requirement R-SESSION-1.** Session restarts are allowed and encouraged whenever context grows. A restart receives a new implementation brief containing only: the contract reference and hash, the current diff or commit, the relevant failing lines, and the remaining budget. It never receives the previous conversation. A restart does not alter the contract.

| Event | New session | New contract version | New run |
|---|---|---|---|
| Context too large | Yes | No | No |
| Session timeout | Yes | No | No |
| Implementation not converging | Yes | No | No |
| Brief regenerated from the same contract | Yes | No | No |
| Allowed paths change | Yes | Yes | Yes |
| Acceptance behavior changes | Yes | Yes | Yes |
| A proof is found defective | Yes | Yes | Yes, after requalification |
| Owner changes definition of done | Yes | Yes | Yes |

## 6. Oracle

One command, with its pass condition stated as its last line. Three layers:
1. Unit proofs for known defects.
2. An end-to-end probe on real data: properties of what is actually sent, and deterministic signals compared with an independent reference (for example `git show --numstat`).
3. Repeated runs (3 or more) to catch flakes.

**Oracle draft.** The oracle author produces scope, proofs and the E2E probe before any implementation. A draft is not authoritative until reviewed, qualified and frozen.

**Qualification before freezing.**
- Red with a null implementation, and red when each known defect is re-injected.
- Green at a reference commit.
- Reference worktrees for each named ref prove red at base and green at reference by running them.
- `NEG_SPEC` maps each proof to a reference commit and an allowed failure label (behavioral, import-only or CLI-only). The label is computed, never written by hand.
- Pre-existing tests in the target repo are byte-identical to base.
- The kit has been dry-run on the real repo, not only a toy one.
- The oracle reviewer has attacked it.

**Location (R-ORACLE-1).** Oracle files, scope definitions, manifests and acceptance records live outside the target repository in private storage. The implementer may run the oracle only through a restricted interface and cannot read or modify its source or frozen manifest. Content hashes are checked before execution. Nothing uses `/tmp`, because hooks that skip `/tmp` repos would not apply there.

**Standing guards.**
- A lint with a self-test forbids `echo | grep -q` under pipefail (use here-strings).
- A leak scan covers tracked files and output artifacts for API key patterns.
- Keys are blanked for offline proofs.
- Shell checks are written by the oracle author.

**Versioning.** The manifest hash is pinned to a version tag; the gate verifies it before running. A new oracle version is a new tag.

## 7. Scope and history

```
# scopes/TASK-<id>.txt
ALLOW  <paths this task may edit>
FROZEN <paths this task must not touch>
WI     <id>  <one-line description>     # optional
```

**Requirement R-SCOPE-1.** The gate runs `git diff --name-only BASE..HEAD` in the implementer's worktree. It fails on any path that is `FROZEN` or matches no `ALLOW` line, and prints the offenders as evidence. Which paths are frozen is a per-task decision. The oracle reviewer flags overbroad scopes such as `ALLOW **`.

**Commits (R-COMMIT-1).**
1. Implementers commit their own progress on `wip/*` branches as often as they judge useful. Commits increase traceability.
2. Commit messages carry a `(WI-<id>)` tag. Tags are informational: they show that a commit claims a work item and say nothing about content.
3. The gate checks final history, after any squash or rebase:
   - every commit in `BASE..HEAD` has a registered tag;
   - every declared work item has at least one commit;
   - every changed path matches `ALLOW` and avoids `FROZEN`;
   - the worktree is clean (no uncommitted or untracked files).
4. No pushes. Remote sync is reserved for humans.
5. A commit is not acceptance.

## 8. Process

1. **Preflight (once per task):** repo state, hooks, how checks run, env and quota facts; where the gate runs (local, pre-push hook or CI); the definition of done; a coverage map of which existing tests import the changed code; owner decisions, each with a default the owner can veto; the budget.
2. **Diagnose before design.** For any environmental problem, a repro script runs K calls at default settings and reports an error rate before a mitigation enters a brief.
3. **Draft the oracle,** have the oracle reviewer attack it, qualify it, then freeze and tag it before the implementer starts.
4. **Implement:** short sessions, fresh context, implementation brief below. Restart sessions per R-SESSION-1.
5. **Gate, then diff review.** The gate writes the report to `runs/`. Review diffs (`--stat` first), not summaries.
6. **Owner runs the live gate** and pastes the tail.
7. **Accept and record.**

Edges between steps carry artifacts only. Parallel implementers need disjoint paths.

**Worker stop versus acceptance (R-STOP-1).** Exit 0 from the offline oracle ends the implementer's session. It is not acceptance. Acceptance requires: final scope/history gate, independent diff review, live gate, evidence report, and a ledger entry.

## 9. Dispute protocol

1. The implementer pastes only the failing line and stops.
2. The oracle author runs the oracle at a known-good reference. Red there means the oracle is wrong.
3. A fresh session patches the oracle; it is requalified at base and reference on the real repo.
4. The owner commits it as a new version tag. The current run is superseded; a new run starts (R-FREEZE-1).

## 10. Implementation brief template

```
Goal: <one sentence>
Oracle: agate run <repo> <task-id>; done = <its last line>
Scope: scopes/TASK-<id>.txt (gate-enforced), oracle vN, contract hash <sha>
Context: <current diff/commit, relevant failing lines only>
Commits: on wip/*, tag (WI-<id>)
Dispute: if a proof looks wrong, paste only the failing line and stop. Do not work around it.
Budget: <n> tool calls; final message <= 12 lines
Never: bypass hooks, print secrets, push
```

Briefs are generated into `runs/` and archived there.

## 11. Records

`ACCEPTANCE.md` holds accepted, open and deferred items per repo, each with evidence (accepted lines cite the report commit). The gate fills it from its own output, and the owner commits it. `sessions.tsv` logs model, turns, tokens, cost and accepted items; call caps come from observed cost per accepted item. There is no separate postmortem log: every commit that adds or changes a guard states which failure it prevents and where it was seen, so `git log` over `core/` and `oracle/` is the record. The owner writes a postmortem by hand when a run surprises them.

## 12. Orchestrator conduct

- Batch diagnostics into one block, and ask for sizes before diffs.
- Treat any "resolved" claim as unverified until independent command output shows it.
- When a check forces a production change, first ask whether the check is wrong.
- Checkpoint with a short note when a session gets long.

## 13. Requirement index

| ID | Requirement |
|---|---|
| R-ID-1 | Implementer OS identity cannot read or edit the private oracle |
| R-ROLE-1 | Role identity is manifest data, separate from model tier |
| R-FREEZE-1 | No oracle, scope or definition-of-done change inside a run |
| R-SESSION-1 | Sessions restart from artifacts only; contract unchanged |
| R-ORACLE-1 | Oracle private, external, hash-checked, restricted interface |
| R-SCOPE-1 | Scope enforced by diff over `BASE..HEAD` |
| R-COMMIT-1 | Workers commit on `wip/*` with `(WI-<id>)`; gate checks history and clean worktree |
| R-STOP-1 | Exit 0 stops the worker; it does not accept the task |
