# Orchestrating agent graphs
v.6

This is a general reference for running multi-agent code tasks across repos. It states premises and protocols. History lives in the gate repo's commit log, not here.

## 1. Premises

Each premise comes from repeated failures in earlier runs.

1. **Independence.** The party that writes the code never writes or edits the checks that judge it, and the checks have a reviewer who is neither of them. A check with no independent reviewer is a claim.
2. **Enforcement over prose.** A rule counts only if a guard checks it mechanically. A rule without a guard is a wish and is dropped. When a guard is added, the prose rule goes away.
3. **Evidence is generated.** Reports derive from command output. A claim with no command that produces it counts as nothing. A skipped check is SKIP, not PASS.
4. **Oracles are tested too.** Before freezing, an oracle must fail on a null implementation, fail when known defects are re-injected, and pass at a reference. A green result means something only if red was possible.
5. **A green oracle isn't truth.** Proofs can pass while the real output is wrong. Every oracle needs an end-to-end probe on real data and an independent reference for its signals.
6. **Measure before building.** Environmental problems are reproduced and quantified before any mitigation enters a brief.
7. **Fresh, short, small.** Each task gets its own context, scope, budget and oracle slice. Between tasks, only artifacts pass (a commit, a diff, a report), never a conversation.
8. **Disputes stop work.** When a check conflicts with code the implementer believes is correct, the implementer stops and reports. The oracle owner decides whether the check is wrong.

## 2. Layout and identities

The oracle lives outside every target repo, so public repos contain none of it.

```
~/gate/                          # private git repo, owner-committed
  DESIGN.md                      # this document
  core/                          # repo-agnostic: run-all, verify-ref, final-gate, write-manifest, lints, leak scan
  repos/<name>/
    repo.toml                    # repo path, base ref, how checks run, env/key rules
    oracle/                      # proofs, NEG_SPEC.tsv, NEG_EXEMPT.txt, MANIFEST.sha256
    scopes/                      # TASK-<id>.txt
    ACCEPTANCE.md                # accepted / open / deferred, with evidence
    sessions.tsv                 # model, turns, tokens, cost, accepted items
  runs/                          # generated briefs and reports (untracked)
  work/                          # ephemeral reference worktrees (untracked)
```

Invocation: `gate run <repo> <task-id>`. Nothing uses `/tmp`, because hooks that skip `/tmp` repos would not apply there.

| Identity | Owns | Can access |
|---|---|---|
| Owner | `~/gate`, API keys, the live gate run | Everything |
| Gate runner (optional low-privilege user) | Runs offline proofs with keys blanked | Worktrees, read-only oracle |
| Implementer | Its own worktree of the target repo | No keys, no `~/gate`, no global git config |

A separate implementer user gives OS-level protection for the oracle, isolation from secrets, a smaller blast radius, attributable commits, per-user resource and network limits, and a root-owned system hooks path the agent can't edit. Proofs execute the implementer's code, so offline proofs run with keys blanked, and only the owner runs the live gate.

## 3. Roles

Author, implementer and oracle reviewer are three different parties. Models are placeholders, and nothing in the oracle depends on a vendor.

| Role | Does | Model |
|---|---|---|
| Oracle author | Writes and tests proofs, gate, scope file | `<MODEL_A>` |
| Implementer | Edits code only, inside scope | `<MODEL_B>` |
| Oracle reviewer | Tries to make each proof pass while its claim is false | `<MODEL_C>`, prefer a different family from A |
| Diff reviewer | Reads diffs for risk the gate can't see | `<MODEL_D>`, must differ from B |
| Owner | Commits oracle versions and the ledger, runs the live gate | Human |

Parallel implementers and a cheaper implementer are hypotheses until `sessions.tsv` shows cost per accepted item per model. Whether reviewer-differs-from-author is a hard gate check or an overridable default is the owner's call.

## 4. The oracle

One command, with its pass condition stated as its last line. It has three layers:
1. Unit proofs for known defects.
2. An end-to-end probe on real data: properties of what is actually sent, and deterministic signals compared with an independent reference (for example `git show --numstat`).
3. Repeated runs (3 or more) to catch flakes.

**Qualification before freezing:**
- Red with a null implementation, and red when each known defect is re-injected.
- Green at a reference commit.
- Reference worktrees for each named ref prove red at base and green at reference by running them.
- `NEG_SPEC` maps each proof to a reference commit and an allowed failure label (behavioral, import-only or CLI-only). The label is computed, never written by hand.
- Pre-existing tests in the target repo are byte-identical to base.
- The kit has been dry-run on the real repo, not only a toy one.

**Standing guards:**
- A lint with a self-test forbids `echo | grep -q` under pipefail (use here-strings).
- A leak scan covers tracked files and output artifacts for API key patterns.
- Keys are blanked for offline proofs.
- Shell checks are written by the oracle author.

**Versioning.** The manifest hash is pinned to a version tag in `~/gate`, and the gate verifies it before running. A new oracle version is a new tag.

## 5. Scope and enforcement

```
# repos/<name>/scopes/TASK-<id>.txt
ALLOW  <paths this task may edit>
FROZEN <paths this task must not touch>
WI     <id>  <one-line description>     # optional
```

The gate runs `git diff --name-only BASE..HEAD` in the implementer's worktree. It fails on any path that is `FROZEN` or matches no `ALLOW` line, and prints the offenders as evidence. Which paths are frozen is a per-task decision, not a standing property of the repo.

**Work-item traceability.** If the scope file lists work items, the gate fails when any commit in the range lacks a registered `(WI-<id>)` tag, or when a listed item has no commit. It runs on final history, after any squash or rebase. It proves a commit claims an item and says nothing about content.

The oracle reviewer flags overbroad scopes, such as `ALLOW **`.

## 6. Dispute protocol

1. The implementer pastes only the failing line and stops.
2. The oracle author runs the oracle at a known-good reference. Red there means the oracle is wrong.
3. A fresh session patches the oracle, and it is tested at base and reference on the real repo.
4. The owner commits it as a new version tag.

## 7. Process

1. **Preflight (once per task):**
   - Repo state, hooks, how checks run, env and quota facts.
   - Where the gate runs (local, pre-push hook or CI).
   - The definition of done.
   - A coverage map of which existing tests import the changed code.
   - Owner decisions, each with a default the owner can veto.
   - The budget.
2. **Diagnose before design.** For any environmental problem, a repro script runs K calls at default settings and reports an error rate before a mitigation enters a brief.
3. **Qualify the oracle,** have the oracle reviewer attack it, then freeze and tag it before the agent starts.
4. **Implement:** short session, fresh context, brief below.
5. **Gate, then diff review:** the gate writes the report to `runs/`. Review diffs (`--stat` first), not summaries.
6. **Owner** runs the live gate and pastes the tail.

Edges between steps carry artifacts only. Parallel implementers need disjoint paths.

## 8. Brief template

```
Goal: <one sentence>
Oracle: gate run <repo> <task-id>; done = <its last line>
Scope: scopes/TASK-<id>.txt (gate-enforced), oracle vN
Dispute: if a proof looks wrong, paste only the failing line and stop. Do not work around it.
Budget: <n> tool calls; final message <= 12 lines
Never: bypass hooks, print secrets
```

Briefs are generated from this template into `runs/` and archived there.

## 9. Records

`ACCEPTANCE.md` holds accepted, open and deferred items per repo, each with evidence (accepted lines cite the report commit). The gate fills it from its own output, and the owner commits it. `sessions.tsv` logs model, turns, tokens, cost and accepted items, and call caps come from observed cost per accepted item.

There is no separate postmortem log. Every commit that adds or changes a guard states in its message which failure it prevents and where it was seen, so `git log` over `core/` and `oracle/` is the record. The owner writes a postmortem by hand when a run surprises them. The design document changes only when a lesson changes a premise or a guard.

## 10. Orchestrator conduct

- Batch diagnostics into one block, and ask for sizes before diffs.
- Treat any "resolved" claim as unverified until independent command output shows it.
- When a check forces a production change, first ask whether the check is wrong.
- Checkpoint with a short note when a session gets long.
