# Reference

`arouter`, `asessions` and the dispatcher describe existing behavior from the current guide. Everything under `arun` (target), `amaster` and `agate` is a **proposed interface**, not implemented behavior. Flags and schemas may change.

## arouter

```bash
arouter --set <profile> <model>   # map a profile to a model
arouter --get <profile>           # print resolved model
arouter --show                    # print all mappings
```

Profiles: `cheap` (routine edits), `balanced` (multi-file work and debugging), `smart` (ambiguous or architectural work). The target version also resolves a role to a runtime and records both.

## arun

Current: `arun [tier] "<prompt>"` runs the Cursor agent with `--auto-review --trust`, resolving the model through `arouter`, and appends piped stdin as context.

Target (proposed):

```text
arun --role implementer --runtime cursor --profile balanced \
     --worktree <path> --brief <path> --budget-calls <n> --timeout <dur> \
     --env-policy offline --report <path.json>
```

Responsibilities: launch one fresh session, apply timeout and environment policy, capture identity and usage, return structured JSON. It never decides acceptance.

## asessions

```bash
asessions               # list recent sessions, durations, token usage
asessions <session-id>  # trace of tool calls and model decisions
```

Target: export normalized records appended to `sessions.tsv` (model, turns, tokens, cost, accepted items).

## amaster (proposed)

```text
amaster preflight    <repo> <task>
amaster draft-oracle <repo> <task> --author <profile>
amaster review-oracle <repo> <task> --reviewer <profile>
amaster qualify      <repo> <task>
amaster freeze       <repo> <task>
amaster implement    <repo> <task> --runtime <name> --profile <profile>
amaster verify       <repo> <task>
amaster review-diff  <repo> <task> --reviewer <profile>
amaster live-gate    <repo> <task>
amaster accept       <repo> <task>
amaster status       <repo> <task>
```

Each command consumes artifact identifiers, emits a report, and leaves the run resumable. Subprocesses use argument vectors, not shell strings, and fail closed on non-zero results. `amaster` never evaluates evidence; it calls `agate`.

## agate (proposed)

```text
agate run       <repo> <task-id>      # run the oracle; last line states the pass condition
agate qualify   <repo> <task-id>      # null, defect reinjection, base/reference, E2E, repeats
agate scope     <repo> <task-id>      # BASE..HEAD path check
agate history   <repo> <task-id>      # WI tags, clean worktree
agate final     <repo> <task-id>      # all offline checks, writes report to runs/
agate manifest  <repo>                # write/verify MANIFEST.sha256 and version tag
agate ledger    <repo> <task-id>      # update ACCEPTANCE.md and sessions.tsv from evidence
```

The worker-facing surface is limited to `agate run`. All other commands are owner-side.

## Run manifest (proposed schema)

```yaml
run_id: RUN-42
repo: <name>
task_id: TASK-17
base_ref: <sha>
contract_version: v1
scope_hash: <sha256>
oracle_version: v7
oracle_manifest_hash: <sha256>
roles:
  oracle_author:   {profile: smart,    resolved: <model/runtime>}
  oracle_reviewer: {profile: smart,    resolved: <model/runtime>}
  implementer:     {profile: balanced, resolved: <model/runtime>}
  diff_reviewer:   {profile: smart,    resolved: <model/runtime>}
runtime: {engine: cursor}
budgets: {calls: 24, wall_clock_seconds: 720}
state: FROZEN
supersedes: null
sessions: []
```

## Scope file

```text
ALLOW  <glob>
FROZEN <glob>
WI     <id>  <one-line description>
```

A path fails if it matches `FROZEN` or matches no `ALLOW` line. `ALLOW **` is flagged by the oracle reviewer.

## Exit codes (proposed)

| Code | Meaning |
|---|---|
| 0 | Check passed |
| 1 | Check failed (`IMPLEMENTATION_RED`) |
| 2 | Oracle suspected defective (`ORACLE_DISPUTE`) |
| 3 | Scope or history violation |
| 4 | Environment or infrastructure error |
| 5 | Skipped check (never reported as pass) |

## Environment policy

| Policy | Meaning |
|---|---|
| `offline` | Keys blanked, no oracle source visible; used for implementer sessions and offline proofs |
| `live` | Credentials available; owner only |
