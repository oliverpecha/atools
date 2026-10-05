# Architecture

How the atools suite implements `DESIGN.md`. This file describes structure; it does not restate protocol requirements.

## 1. Suite topology

```
                 Owner (human)
                      │
                 ┌────▼────┐
                 │ amaster │  state transitions only
                 └─┬─┬───┬─┘
        resolve    │ │   │   check / record
      ┌────────────┘ │   └──────────────┐
 ┌────▼────┐   ┌─────▼────┐        ┌────▼────┐
 │ arouter │   │   arun   │        │  agate  │  private trust domain
 └────┬────┘   └─────┬────┘        └────┬────┘
      │              │ one session      │ oracle, scope, evidence, ledger
      │         ┌────▼─────┐            │
      └────────►│ adapter  │◄───────────┘ (restricted interface only)
                │ → runtime│
                └────┬─────┘
                     │ telemetry
                ┌────▼──────┐
                │ asessions │
                └───────────┘
```

| Component | Responsibility | Trust domain |
|---|---|---|
| `arouter` | Resolve role/profile to model and runtime | Owner |
| `arun` | Launch one bounded session through an adapter and return structured metadata | Worker runtime |
| `asessions` | Read runtime logs through the adapter, normalize to per-run cost records | Owner, read-only |
| `amaster` | Drive the run state machine, call `agate` for every verdict | Owner |
| `agate` | Run and qualify oracles, enforce scope and history, write evidence, keep the ledger | Separate from worker runtime |

## 2. Vendor boundary

The suite core is vendor-neutral. A **runtime adapter** is the only place a specific agent runtime is named.

| Concern | Core (vendor-neutral) | Adapter (per runtime) |
|---|---|---|
| Role and profile resolution | `arouter` | Model identifiers the runtime accepts |
| Invocation | `arun` contract: fresh, bounded, structured result | Binary, flags, non-interactive mode |
| Instructions | Content of rules, operator and worker files | File locations and format |
| Permissions | Required deny rules (push, destructive, hook bypass) | Syntax and config file |
| Telemetry | Normalized per-run record | How session logs are read |
| Environment policy | `offline` and `live` | How keys are blanked and passed |
| Oracle, scope, history, ledger | `agate` | Nothing; the gate never depends on a runtime |
| State transitions | `amaster` | Nothing |

Rules for the boundary:
- `agate` and `amaster` must not import, call or configure a specific runtime.
- Model names appear only in `arouter` configuration and run manifests as data.
- An adapter can be replaced without changing the oracle protocol or any past evidence.
- Cursor is the first adapter; it is documented in `install.md` section 7.1 and checked by the `ADP` section of the audit. Its CLI flags, config paths and permission syntax do not appear in `DESIGN.md`.

## 3. Run state machine

```
PREFLIGHT → ORACLE_DRAFT → ORACLE_REVIEW → QUALIFIED → FROZEN
   → IMPLEMENTING ⇄ (new session, same contract)
   → OFFLINE_GATE → DIFF_REVIEW → LIVE_GATE → ACCEPTED
        │                │             │
        └── fail ────────┴─────────────┴──► IMPLEMENTING (same contract) or REJECTED
ORACLE_DISPUTE → (requalify, new version) → SUPERSEDED → new run at FROZEN
```

Rules:
- Every transition consumes artifact identifiers and emits a report. No transition passes conversation.
- `IMPLEMENTATION_RED` keeps the frozen oracle authoritative and permits a new session. `ORACLE_DISPUTE` stops implementation and supersedes the run.
- A failed transition leaves the run inspectable and resumable. It never silently reprompts another model or edits the contract.

## 4. Data layout

```
~/gate/                          # private git repo, owner-committed (agate state)
  DESIGN.md                      # copy or link of the normative design
  core/                          # repo-agnostic: run-all, verify-ref, final-gate, write-manifest, lints, leak scan
  repos/<name>/
    repo.toml                    # repo path, base ref, how checks run, env/key rules
    oracle/                      # proofs, E2E probe, NEG_SPEC.tsv, NEG_EXEMPT.txt, MANIFEST.sha256
    scopes/                      # TASK-<id>.txt
    ACCEPTANCE.md                # accepted / open / deferred, with evidence
    sessions.tsv                 # model, turns, tokens, cost, accepted items
  runs/                          # generated briefs and reports (untracked)
  work/                          # ephemeral reference worktrees (untracked)
```

The location may be relocated (for example under `~/.local/share/atools/`) provided the access rules in section 5 hold. Nothing uses `/tmp`.

## 5. Trust boundaries and profiles

| Layer | Production | Development |
|---|---|---|
| Implementer identity | Separate OS user | Same user as owner |
| Oracle access | Not readable or writable by implementer; run through `agate` interface | Same-user filesystem; protected by hash checks and post-run gate |
| Credentials | Absent from offline runs | Blanked environment variables |
| Hooks path | Root- or owner-owned | User-owned global hooks |
| Live gate | Owner only | Owner only |

Defense in depth, in both profiles: machine-wide agent rules, adapter permission rules, branch hook, `timeout -k` watchdog. These reduce the blast radius. None of them counts as acceptance evidence; only gate output does. Proofs execute the implementer's code, so offline proofs always run with keys blanked.

## 6. Runtime layer

`arun` accepts a role, profile, worktree, brief, budget, timeout and environment policy, and returns a structured result. It reaches a runtime only through the configured adapter.

Dispatchers and tier entry points (`acheap`, `abalanced`, `asmart`) are persistent executables rather than shell functions, because exported shell functions do not survive the non-interactive subshells that `timeout` starts. They are convenience profiles, not roles.

**Anti-recursion boundary.** Worker instructions exclude outer dispatchers (`arouter`, tier entry points, `asessions`, `arun`, `amaster`) so a worker cannot launch further workers. Operator tooling lives in a separate instruction file.

## 7. Artifact flow

```
oracle author ─► scope + proofs + E2E probe ─► review ─► qualify ─► freeze (tag)
                                                                      │
                  implementation brief ◄── contract ref + hash ◄──────┘
                          │
                     arun session ─► commits on wip/* with (WI-<id>)
                          │
                     agate offline gate ─► evidence report
                          │
                     diff review ─► live gate ─► ACCEPTANCE.md + sessions.tsv
```

Only artifacts cross arrows: a commit, a diff, a report, a hash.

## 8. Compliance

`docs/audits/atools-compliance_audit.sh` mirrors this structure: vendor-neutral sections (`INST`, `HARD`, `HOOK`, `SKILL`, `PROF`, and the planned `ORC`, `SCP`, `EVD`) and one adapter section (`ADP`). The adapter is chosen explicitly with `--cursor` or `--adapter none`; there is no default.
