# Migration

Moves the existing atools workflow (eval-repair guide and the router-to-runtime memo) to the gated graph protocol in `DESIGN.md`.

## 1. Router to gated runtime

The router-to-runtime memo is outdated. Its durable ideas are kept; its prototype controller is deprecated.

**Kept**
- Fresh contexts at leaf boundaries.
- Runtime-neutral worker nodes.
- Deterministic subprocess gates.
- Compact evidence packets instead of full transcripts.
- Bounded retries with human escalation.

**Deprecated, with the replacement in the new protocol**

| Deprecated | New protocol |
|---|---|
| `aorch` prototype controller | `amaster` state machine calling `agate` |
| Contract in `/tmp/Runbook_<id>.md` | Task contract and implementation brief generated in `runs/` |
| Proofs in the target repo under `proof/` | Private, versioned oracle outside the target repo (R-ORACLE-1) |
| Same model rewrites the runbook after a failure | Restart a session with a new implementation brief; changed contract means new version and superseding run (R-FREEZE-1, R-SESSION-1) |
| One baseline-red run as validation | Full qualification: null, defect reinjection, base/reference, E2E, repeats |
| Tier name as role (`asmart` is the architect) | Role identity and profile recorded separately (R-ROLE-1) |
| Exit 0 means complete | Exit 0 stops the worker; acceptance needs the gate, diff review and live gate (R-STOP-1) |
| Prompt lists allowed files | `BASE..HEAD` diff scope check (R-SCOPE-1) |
| `git add -u && git commit` after green | Workers commit on `wip/*` with `(WI-<id>)`; gate checks history and clean worktree (R-COMMIT-1) |
| Engine comparison table in the architecture memo | Measured cost per accepted item from `sessions.tsv` |

## 2. Legacy proof layout

| Legacy | Target |
|---|---|
| `proof/run_suite_<title>.sh` in the repo | `repos/<name>/oracle/` in private `agate` state |
| `proof/out/<test>.log` in the repo | Reports under `runs/` |
| `verify_fails_on_base.sh` | `agate qualify` |
| `/tmp/Runbook_<title>.md` | `runs/<run-id>/brief.md` |
| Worker skill with `chmod +x proof/*.sh` | Worker skill without any oracle mutation |
| `atools-compliance_audit.sh` (36 guardrails) | Split into the checks in `audits.md` |

## 3. Phases

### Phase 0: establish semantics
1. Create `DESIGN.md` as the successor to `graph-exploration.md` v6; mark it provisional and record the supersession.
2. Define proof exit 0 as the implementer's stop condition.
3. Prohibit implementers from authoring or modifying oracle files.
4. Separate the frozen task contract from regenerable implementation briefs.
5. Allow fresh sessions against the same contract with compact artifact packets.
6. Require any scope, oracle or definition-of-done change to create a new contract version and a superseding run.
7. Require workers to commit on `wip/*` with `(WI-<id>)` tags.
8. Remove automatic green-to-commit-to-accept behavior from the prototype.

### Phase 1: separate artifacts
- Create the private `agate` layout.
- Move one pilot task's proofs, scope and acceptance record out of the target repo.
- Replace `/tmp` runbooks with generated briefs under `runs/`.
- Add content hashes for scope, brief and oracle manifest.

### Phase 2: add enforcement
- Path scope checks over `BASE..HEAD`.
- History checks: tags, declared work items, clean worktree.
- Blank keys for offline proof execution.
- Leak scanning over tracked changes and reports.
- Role identity checks.
- Argument-vector subprocess calls that fail closed.

### Phase 3: qualify oracles
- Null implementation checks, defect reinjection fixtures, base and reference worktrees.
- Real-data E2E probe with an independent reference.
- Repeated runs for flakes.
- Independent oracle review before freeze.

### Phase 4: complete acceptance
- Independent diff review after the offline gate.
- Owner-only live gate.
- Evidence-derived reports and `ACCEPTANCE.md` entries.
- Normalize `asessions` output into per-run costs and accepted-item counts.

### Phase 5: generalize runtimes
- Stabilize the `arun` contract.
- Add a second runtime only after the gate protocol is runtime-neutral.
- Choose default profiles from observed cost per accepted item.

## 4. Existing installations

Existing `arouter`, `arun`, tier entry points, `asessions`, permissions and hooks keep working during migration. Remove the `/tmp` hook bypass and the proof-editing step in the worker skill early, since both conflict with the protocol.
