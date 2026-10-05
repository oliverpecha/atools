# Operations

Procedures assume the target components. Where `amaster` or `agate` do not yet exist, perform the step by hand against the same artifacts.

## 1. Create a task

1. Record repo, base ref, definition of done and budget (preflight).
2. For any environmental problem, run a repro script for K calls at default settings and record the error rate before proposing a mitigation.
3. Build a coverage map: which existing tests import the changed code.
4. List owner decisions, each with a default the owner can veto.

## 2. Draft the oracle

The oracle author writes `scopes/TASK-<id>.txt`, the proofs and the E2E probe. The probe should run the real path on real data and compare deterministic signals with an independent reference such as `git show --numstat`. The author must not be the implementer.

## 3. Review and qualify

1. The oracle reviewer tries to make each proof pass while its claim is false, and flags overbroad scopes.
2. Qualify: null implementation red; each known defect re-injected red; reference green; base and reference worktrees executed; pre-existing tests byte-identical to base; 3 or more repeated runs stable; dry-run on the real repo.
3. Freeze: write the manifest hash, tag the version in `agate`.

## 4. Start implementation

1. Generate the implementation brief from the template into `runs/`.
2. Launch one session with `arun` in a fresh worktree on a `wip/*` branch, under `timeout -k`.
3. The worker commits progress with `(WI-<id>)` tags and stops when the oracle exits 0 or a dispute arises.

## 5. Restart a session

Use this when context grows large, a session times out, or progress stalls. The contract stays the same.

1. Generate a new implementation brief containing the contract reference and hash, the current diff or commit, only the relevant failing lines, and the remaining budget.
2. Launch a fresh session. Do not pass the earlier transcript.
3. Record the session in `sessions.tsv`.

If the scope, oracle behavior or definition of done must change, do not restart. Follow section 7.

## 6. Verify and review

1. Run the offline gate: oracle, scope over `BASE..HEAD`, history (tags, clean worktree), leak scan.
2. If the gate fails with `IMPLEMENTATION_RED`, restart per section 5. If the gate fails scope or history, correct the cause in a new session.
3. Review the diff with `--stat` first, then focused hunks, with a diff reviewer that differs from the implementer. Do not review from summaries.
4. The owner runs the live gate and pastes the tail.
5. On success, `agate` writes the evidence report and updates `ACCEPTANCE.md` and `sessions.tsv`; the owner commits the ledger.

## 7. Handle an oracle dispute

1. The implementer pastes only the failing line and stops.
2. The oracle author runs the oracle at a known-good reference. If red, the oracle is wrong.
3. A fresh session patches the oracle; qualify it again at base and reference on the real repo.
4. The owner commits it as a new version tag. The old run is marked superseded and a new run starts.

## 8. Inspect sessions

```bash
asessions               # recent runs, durations, tokens
asessions <session-id>  # tool calls and decisions, without spending tokens
```

Compare cost per accepted item per model before changing defaults or enabling parallel implementers.

## 9. Conduct checklist

- Batch diagnostics into one block; ask for sizes before diffs.
- Treat any "resolved" claim as unverified until independent output shows it.
- When a check forces a production change, ask whether the check is wrong first.
- Checkpoint with a short note when a session gets long.
