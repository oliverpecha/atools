# Concepts

Definitions used across the suite. Requirements are in `DESIGN.md`.

## Roles and identities

A **role** (oracle author, implementer, oracle reviewer, diff reviewer, owner) describes what a party is allowed to do. A **profile** (`cheap`, `balanced`, `smart`) describes a capability and cost tier that `arouter` resolves to a concrete model and runtime. They are independent: the manifest records both, and independence checks use the resolved identity, not the tier name.

## Assertion, proof, oracle, probe

| Term | Meaning |
|---|---|
| Assertion | A discrete check returning true or exit 0 |
| Proof | A focused check for one claim or known defect |
| E2E probe | A check of real output on real data, compared with an independent reference |
| Oracle | The versioned set of scope, proofs and probe, run as one command whose pass condition is its last line |
| Reference | A known-good commit at which the oracle must pass |
| Null implementation | A baseline with no change, at which every proof must fail |

The older layered taxonomy (assertion-gated, red-green, harness, eval-driven repair) still describes the worker's inner loop. That loop is one leaf inside the gated graph, not the whole system.

## Oracle draft, qualification, freeze

The oracle author drafts scope, proofs and an E2E probe. The oracle reviewer tries to make each proof pass while its claim is false. Qualification then proves red could happen: null implementation red, re-injected defects red, reference green, base and reference worktrees executed, repeated runs stable. Freezing pins the manifest hash to a version tag. A green result only has meaning because red was possible.

## Contract, brief, session, run

- **Task contract:** frozen goal, scope, oracle version and definition of done.
- **Implementation brief:** the small packet handed to one fresh session. It changes every session.
- **Session:** one bounded `arun` invocation.
- **Run:** one execution of one contract version. A changed contract supersedes the run.

Restarting a session refreshes context and drops accumulated token load. Changing the contract creates a new version and run.

```
contract v1 ── run R1 ── implementation sessions S1, S2
                      \
                       \ superseded by
                        contract v2 ── run R2 ── implementation session S1
```

## Worker stop versus acceptance

Exit 0 from the offline oracle is the implementer's stop condition. Acceptance additionally requires the final scope and history gate, independent diff review, the owner-run live gate, an evidence report and a ledger entry. A commit is not acceptance.

## Scope and history

Scope is a per-task list of `ALLOW` and `FROZEN` paths, enforced by diffing `BASE..HEAD`. Work-item tags `(WI-<id>)` in commit messages are cheap traceability: they show that a commit claims an item and prove nothing about its content. Workers commit freely on `wip/*`.

## Disputes

When a check conflicts with code the implementer believes is correct, the implementer pastes the failing line and stops. The oracle author runs the oracle at a known-good reference; red there means the oracle is wrong. A fresh session patches it, the owner tags a new version, and the run is superseded.

## Fresh-session semantics

Between sessions only artifacts pass. A new session gets the contract reference, the current diff or commit, the relevant failing lines and the remaining budget. It never gets the earlier transcript. This is how the suite controls token cost.
