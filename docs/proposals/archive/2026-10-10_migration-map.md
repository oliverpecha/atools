
## Appendix A: Legacy (`graph-exploration.md` v.6) Terminology Migration Map

| `graph-exploration.md` v.6 Term | Specification Equivalent | Summary of Structural Change |
| --- | --- | --- |
| **Orchestrator (`amaster`) + Runner (`agate`)** | **Actl (`actl`)** | Merged into a single deterministic binary (`actl-repo/bin/actl`) running under OS `UID actl` with three internal modules: `orchestrator` (`state.py`), `dispatcher` (`dispatch.py`), and `verifier` (`verify.py`). Spawns agent CLI sessions inside detached headless `tmux` sessions under `systemd` linger.

 |
| **Oracle author / Oracle reviewer** | **Challenger** | Single cross-family adversarial leaf node running as OS `UID plan` (replaces the separate Prover + Challenger pair). Audits read-only `spec-vN.md` and `solution_key.patch` (re-created as `actl:plan`, `chmod 0440` inside `chmod 0750 plan-box/`) and authors Oracle vN (`proofs/`, `probe.sh`, `mutants/`, `scope.txt`, `coverage.md`) plus `oracle-critique.md` for Architect review and lock decision.

 |
| **Diff reviewer** | **Archivist** | Runs as isolated OS `UID ship` strictly in Phase 4 after the Implementer passes all offline and live runs. Reviews the approved diff for semantic risk (including any modified legacy tests and waived mutants), curates `backlog-proposal.md`, graduates black-box `proofs/*.sh` into new native repo test files (`test/`), rebases any non-applying Phase 2 mutants onto Commit N, and writes the `plan/` patch/message pairs.

 |
| **`ACCEPTANCE.md` / Ledger** | **Checklist (`specs/{sprint}/checklist.md`)** | Tracked per-spec checklist initialized at oracle freeze (`open`), recording separate Offline Run and Live Run evidence columns with literal head commit SHAs, and stamped `done` mechanically by `actl` when all mapped proofs in `coverage.md`, `probe.sh`, and the repo Test suite pass on the identical head SHA (with dedicated `mutant/{name}.patch` | `waived` | `escalation-NN` rows when surviving mutants are waived at escalation).

 |
| **Implementation brief / Runbook** | **Work order** | Not a newly authored prose file; a mechanical bundle of `spec-vN.md` + `contract-vN.json` (+ `solution_key.patch` when `solution_key_exposure: full`, and optional `prior_attempt.json` on retry) materialized in `handoff/{sprint}/work-order/`.

 |
| **Known-good reference** | **Solution key (`solution_key.patch`)** | Authored solely by the Architect in the Spec phase (updated only by the Architect if Phase 2 qualification exposes a flaw), re-created by `actl` as `actl:plan` (`chmod 0440`) in `plan-box/` for Challenger audit, verified against Step 1 closure guards and Stage 2b repo Test in `oracle-qual-vN.json`, and copied into the Oracle directory at freeze where its canonical hash is locked. Passed to the Implementer as a starting draft when `solution_key_exposure: full`, but never merged directly into the target repository without passing the Implementer/`actl`/Archivist pipeline.

 |
| **Wrong implementations / Traps** | **Mutants (`mutants/*.patch`)** | Deliberately sabotaged patches supplied by the Challenger that violate a spec clause and must apply cleanly and be killed (`killed: true`, exit 1) by the oracle's proofs in Phase 2 (gated on `solution_key_green`) and by the Archivist's graduated native tests in Phase 4 (directly or via `mutants-rebased/`).

 |
| **Stop report / Session result** | **Implementation closure report (`closure-NN.json`)** | Written by the Implementer to `handoff/{sprint}/closures/` when halting itself (`reason`: `"done"` | `"blocked"`, `blocking_step`, `notes`, `backlog`, and optional `solution_key_divergence`).

 |
| **Dispute report / Pruned packet** | **Escalation record (`escalation-NN.json`)** | Assembled mechanically by `actl` on `retries_oracle_exhausted`, `retries_implementer_exhausted`, `retries_archivist_exhausted`, `live_run_failed`, `hard_cap_exhausted`, or `blocked` (with `oracle_review` populated only when `trigger: retries_oracle_exhausted`, else `null`), tracking orthogonal `closures_submitted` and `hard_caps_tripped` counters, and updated with a structured `resolution` object when resolved. Routed via `actl` → Architect first, and `actl` → Owner when the Architect escalates or fails.

 |
| **Evidence report** | **`actl` evidence record (`runs/ev-NN.json`)** | Untracked per-run composite execution receipts (`steps[]` array) written by `actl` to `specs/{sprint}/runs/`, cited by SHA-256 hash and head commit SHA in `checklist.md`.

 |
| **Offline gate / Live gate** | **Offline run / Live run** | `actl` is strictly the unified control-plane and runner binary; Offline run (credentials blanked, executed under `UID impl`) and Live run (gated by `approval_live_run`: `"architect"` | `"owner"` and executed via `/usr/local/bin/actl-live-run`) are verification stages executed by `actl`.

 |
| **Approved snapshot** | **Contract-hash git tag (`{contract-tag}`)** | Retired as a named package; once Phase 3 Offline and Live runs pass on the identical head SHA, `actl` pins that commit via `refs/tags/actl/{sprint}/{contract-vN-sha256}` in `repos/target-repo/.git` before invoking the Archivist.

 |
| **Final history** | **Archivation plan** | A directory (`diff-risk-review.md`, `backlog-proposal.md`, optional `mutants-rebased/*.patch`, plus `plan/NN-{slug}.patch` and `.msg` pairs always ending with `NN-graduate-tests.patch/.msg`) routed via two distinct edges: Archivist → `actl` (solid: regex + `Graduated-Proof:` trailers, 100% git tree-equality on feature commits `01..N-1`, legacy test function count guard, strictly newly added `test/**` files via `--no-renames --diff-filter=a` on commit N, Null-Base Red Check, Mutant-Kill Transfer Check across all non-waived mutants, and full Test execution under `UID ship`) and `actl` → Owner (dashed; mandatory human trunk supervision).

 |
| **`sessions.tsv` schema** | **Extended `sessions.tsv` schema** | Logs every CLI invocation (`model`, `turns`, `tool_calls`, `tokens`, `cost_usd`, `accepted_items`) plus soft retry counters (`closures_submitted`), hard watchdog counts (`hard_caps_tripped`), and `escalation_alerts_sent` events so `state.json` can be deterministically reconstructed alongside `runs/ev-*.json` and `escalation-NN.json`.

 |
