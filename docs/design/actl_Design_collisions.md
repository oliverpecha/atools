> **Historical record (layout transition).** This file captures collision analysis against the pre-transition Design paths (`actl-repo/`, `handoff/`, `ev-NNN`, `qual-NNN`). It is retained as-written for audit trail. Normative current names are in `actl_Design.md` and `docs/plan/layout-transition-memo.md` (L-1..L-11). Do not treat path strings below as current requirements.

### 1. POSIX Isolation, File Permissions & Multi-Account Collisions

* **1.1. Architect Lost Write/Edit Path to `scope.txt` After Splitting `UID plan` (§1.5, §5.2.3, §5.4.2)**
* **a) Issue:** In the 20:05 draft, Architect and Challenger shared `UID plan` and `plan-box/oracle-draft/` (`0770 actl:plan`), allowing the Architect to directly widen `ALLOW` in `scope.txt` during Phase 2 `lock_oracle` or Phase 3 `update_scope`. In the 23:30 revision, `challenger-outputs/oracle-draft/` is owned by `actl:challenger` (`0770` on Challenger's turn, `0750` otherwise) and `architect-inputs/` is `0750 actl:architect` (read-only to `architect`).


* **i.** In Phase 2 (`§5.2.3 Path 1`), when `diagnostic_case == "solution_key_conflict"`, the spec states the Architect fixes `solution_key.patch` and/or widens `ALLOW` in `scope.txt` and emits `lock_oracle`, but `architect` has no write access to `challenger-outputs/oracle-draft/scope.txt` and `scope.txt` is omitted from `architect-outputs/` in the §1.5 directory tree.




* **b) Proposed Fix:**
* **i.** Add `scope.txt` (optional override) to `handoff/{sprint_tag}/architect-outputs/` in §1.5.


* **ii.** Specify in §5.2.3 and §5.4.2 that `actl` stages the current `scope.txt` into `architect-inputs/scope.txt`; if the Architect writes an updated `architect-outputs/scope.txt`, `actl` validates the diff (literal `ALLOW` additions only) and promotes it into the new `oracle-{seq}/scope.txt`.






* **1.2. Missing `setgid` (`2750` / `2770`) on `repos/target-repo/.git` and `{role}-inputs/` Breaks Group Read Access (§1.5, §5.3, §5.5)**
* **a) Issue:** `actl`'s primary group is `actl`, and no persona account is a member of group `actl`.


* **i.** `repos/target-repo/` is specified as `0750 actl:cloners` (without the `2000` setgid bit or `core.sharedRepository = group`). When `actl` fetches the approved `{head_sha}` (which must also be explicitly stated before tagging) or writes `refs/tags/actl/{sprint_tag}/{contract_sha256}` into `repos/target-repo/.git`, new packfiles, loose objects (`0440`), and tag refs are created with `actl`'s primary group (`actl:actl`), making them unreadable (`EACCES`) to `sudo -u {account} git clone --local --no-hardlinks`.


* **ii.** Similarly, `{role}-inputs/` is `0750 actl:{role}` (no setgid bit). Files created or copied into `{role}-inputs/` by `actl` inherit GID `actl` unless `2750` or explicit `chgrp` is used.




* **b) Proposed Fix:**
* **i.** Change `repos/target-repo/` (and `.git/` recursively) to `chmod 2750 actl:cloners` with `git config core.sharedRepository group`, and explicitly state in §5.3/§5.5.3 that `actl` fetches `{head_sha}` from `workspaces/verify-implementer/` into `repos/target-repo/` before pinning `{contract-tag}`.


* **ii.** Change all `handoff/{sprint_tag}/{role}-inputs/` directories to `chmod 2750 actl:{role}` and `{role}-outputs/` to `chmod 2770 actl:{role}`.






* **1.3. `UID actl` Git Operations Inside `workspaces/verify-{role}/` Create Undeletable / Unreadable Files for `{role}` (§1.5, §5.1, §5.4, §5.6)**
* **a) Issue:** `workspaces/verify-{challenger,implementer,curator}/` are owned by `{account}:{account}` (`chmod 2770`), and §5.1.1 mandates that all workspaces are created and wiped via `sudo -u {account} rm -rf`. However, §5.4.1, §5.5.1, and §5.6.2 state that `actl` fetches `wip/{seq}`, checks out commits, stages the temporary oracle copy, and runs `git apply --index && git commit -F` (`E1.2`) inside `workspaces/verify-{role}/`.


* **i.** If `actl` runs these git/file operations as `UID actl` rather than `sudo -u {account}`, `.git/index`, `.git/HEAD`, and loose objects (`0444`) are owned by `UID actl`, causing subsequent `sudo -u {account}` git commands in `E1.3–E1.6` or `O1–O2` to fail on overwriting read-only `actl`-owned git objects/index files.


* **ii.** Conversely, during `O1` (`proofs/*.sh`) and `L` (Live Run), candidate code executes as `UID implementer` inside `workspaces/verify-implementer/`. If the staged oracle copy inside `verify-implementer/` is owned by `implementer:implementer` (`0770`), untrusted candidate code invoked by `proofs/01_*.sh` can **modify or overwrite** `proofs/02_*.sh`, `probe.sh`, or `test/**` on disk mid-run before `O2` executes (a much larger hole than the read-only residual risk noted in Invariant **P**).




* **b) Proposed Fix:**
* **i.** Specify that all git mutations inside `workspaces/verify-{role}/` (`git fetch`, `git checkout`, `git apply`, `git commit`) execute via `sudo -u {account}`.


* **ii.** Specify that `actl` mounts or stages the temporary oracle copy outside the writable worktree at `/run/actl/verify-{role}-oracle/` owned by `actl:{account}` with `chmod 0550` (files `0440`), so `UID implementer` can read/execute the staged oracle scripts during `O1`/`L` (per Invariant **P**'s residual risk) but can never modify them mid-run.







---

### 2. Sequence Numbering (`{seq}`), Artifact Promotion & State Reconstruction Collisions

* **2.1. Implementer `closure-{seq}.json` Draft vs. Promotion Collision & Mutability Across Retries (§1.5, §4, §4.3, §5.4)**
* **a) Issue:** §4 states two conflicting rules: *"Agents write only to fixed draft names; `actl` assigns the number when it promotes a file. An Implementer attempt reserves its `seq` at dispatch, and its workspace (`implementer-{seq}`), branch (`wip/{seq}`), and closure (`closure-{seq}`) share that number."*

* **i.** In §1.5, §4.3, and §5.4, `closure-006.json` is written directly by the Implementer into `handoff/{sprint_tag}/implementer-outputs/closure-006.json` and is **never promoted** into `actl-repo/specs/{sprint_tag}/runs/`.


* **ii.** Because `implementer-outputs/` is unlocked back to `chmod 0770` on the next Implementer attempt (§5.4.1), leaving prior `closure-{seq}.json` files inside `implementer-outputs/` allows a later Implementer session to overwrite or tamper with historical closure reports.




* **b) Proposed Fix:**
* **i.** Have the Implementer write to the fixed draft path `implementer-outputs/closure.json`.


* **ii.** Upon closure, `actl` locks `implementer-outputs/` to `0750`, promotes and unlinks `closure.json` into `actl-repo/specs/{sprint_tag}/runs/closure-{seq}.json` (using the `seq` reserved by that attempt at dispatch), and add `closure-006.json` under `runs/` in the §1.5 directory tree.






* **2.2. Phase 2 `oracle-{seq}` Promotion Timing Collides with `qual-{seq}` and `escalation-{seq}` References (§1.5, §4.2, §4.3, §5.2)**
* **a) Issue:** §1.5 and §5.2.3 state that `oracle-{seq}/` is frozen into `actl-repo/specs/{sprint_tag}/` only when the Architect emits `lock_oracle`. However:


* **i.** `qual-004.json` (§4.2) references `"oracle": "oracle-003"` *before* the Architect has decided whether to lock or revise the oracle.


* **ii.** `escalation-004.json` (§4.3, where the oracle was *never* locked because all 3 attempts failed qualification) references `"latest_oracle": "oracle-002"` and `"qual": "qual-003.json"`, and §1.3 requires `actl` to stage the `prior oracle` into `challenger-inputs/` on retry.




* **b) Proposed Fix:**
* **i.** Specify in §5.2.1 that at the end of every Challenger turn (and whenever the Architect updates `solution_key.patch` or `scope.txt` in Phase 2/3), `actl` promotes `challenger-outputs/oracle-draft/` (plus the current `solution_key.patch`) into an immutable `actl-repo/specs/{sprint_tag}/oracle-{seq}/` *before* running `qual-{seq+1}.json`.


* **ii.** When the Architect later emits `lock_oracle`, `actl` simply mints `contract-{seq}.json` referencing the qualified `oracle-{seq_o}` and `qual-{seq_q}`.






* **2.3. Mandatory `kind`, `seq`, and `parent` Metadata Missing from All Schema Examples & Inconsistent ID Formats (§4, §4.2, §4.3)**
* **a) Issue:** §4 normatively states: *"Every immutable artifact is named `{kind}-{seq}` ... Each file records `kind`, `seq`, and `parent`"*.


* **i.** None of the JSON schemas or examples in §4.2–§4.3 (`qual-004.json`, `closure-006.json`, `ev-007.json`, `escalation-*.json`, `live-decision-012.json`) include `kind`, `seq`, or `parent`.


* **ii.** Cross-references mix bare IDs and filenames inconsistently within the same object (e.g., `ev-007.json` uses `"oracle": "oracle-003"` without an extension alongside `"contract": "contract-005.json"` with `.json`; `escalation-010.json` uses `"last_closure": "closure-008.json"` with `.json` alongside `"evidence": ["ev-007", "ev-009"]` without `.json`).




* **b) Proposed Fix:**
* **i.** Add `"kind"`, `"seq"`, and `"parent"` to all JSON schemas/examples in §4.2–§4.3 (or replace `"id": "{kind}-{seq}"` with those fields consistently) and standardize all artifact references to bare `{kind}-{seq}` IDs (stripping `.md`/`.json` extensions everywhere).






* **2.4. `state.json` Reconstruction Broken by Removal of Counter Columns from `sessions.tsv` (§4, §4.1, §5.1)**
* **a) Issue:** The 23:30 revision removed `closures_submitted` and `hard_caps_tripped` from `runs/sessions.tsv` (§4.1), while claiming in §4 (*Reconstruction*) that `state.json` can be rebuilt by replaying `qual`, `ev`, `escalation` receipts, and `sessions.tsv`.


* **i.** Because every dispatch now consumes an attempt even if it produces no artifact (§6.1.2), and because both a missing/invalid closure (`closures_submitted` not incremented) and a rejected `blocked` closure (`closures_submitted` incremented) emit a red `G2` step in `ev-{seq}.json` (§5.4.1–§5.4.2), `actl` cannot reconstruct `attempts.{stage}`, `closures_submitted`, or `seq` reserved by crashed dispatches from `ev-*.json` and the reduced `sessions.tsv` alone.




* **b) Proposed Fix:**
* **i.** Add `seq`, `epoch`, `stage`, and `terminal_status` (`artifact_valid` | `artifact_invalid` | `session_cap`) to `runs/sessions.tsv` in §4.1, and include promoted `runs/closure-*.json` in the §4 reconstruction replay list.







---

### 3. Escalation Routing, Attempt Budgets & State-Machine Deadlocks

* **3.1. `session_cap` Escalation Table Has Invalid Actions for `architect`/`curator` and Prematurely Halts Budgeted Stages (§4.3, §5.4.2, §6.1, §6.3)**
* **a) Issue:** In §6.3, the `session_cap` routing rows introduce three collisions:
* **i.** For `stage: architect, curator`, `session_cap` routes to **Owner** with `legal_actions: ["grant_attempts", "escalate_owner"]`. First, the Owner cannot execute `escalate_owner` (escalating to itself), and `abort` is missing. Second, §6.1.2 explicitly declares that *"The Architect and the Owner are not attempt-budgeted"* (and `sprint.toml` `[max_attempts]` has no `architect` key), so `grant_attempts` is meaningless for `stage: architect`.


* **ii.** For `stage: oracle, implementer`, a `session_cap` already consumes 1 attempt (`attempts.used += 1`, §6.1.1). Yet in the §4.3 `escalation-011` example, `session_cap` fires when `attempts: {"used": 1, "max": 2}` (1 attempt still remains!), forcing the Architect to call `grant_attempts` (`n: 1`) just to continue. Conversely, if `session_cap` occurs on the final attempt (`used == max`) due to an infinite loop caused by a bad oracle proof or scope restriction, `reopen_oracle` and `update_scope` are forbidden by `session_cap`'s `legal_actions` (`["grant_attempts", "escalate_owner"]`).




* **b) Proposed Fix:**
* **i.** In §6.3, split `session_cap` for `stage: architect` (`Routes to: Owner`, `Legal actions: resume, abort`) from `stage: curator` (`Routes to: Owner`, `Legal actions: grant_attempts, abort`).


* **ii.** For `stage: oracle, implementer`, allow `reopen_oracle` (and `update_scope` for `implementer`, or `n: 0` in `grant_attempts` when `attempts.used < attempts.max`) in `session_cap` `legal_actions`.






* **3.2. `attempts_exhausted` (`stage: implementer`) Forbids `update_scope` and Interacts Badly with `min_attempts_before_block` (§4.1, §5.4.2, §6.3)**
* **a) Issue:**
* **i.** In §6.3, when `attempts_exhausted` fires for `implementer`, `legal_actions` are `["grant_attempts", "reopen_oracle", "escalate_owner"]`—omitting `update_scope`. If the Implementer fails attempt 1 without a valid closure (`closures_submitted = 0`, `attempts.used = 1/2`) and on attempt 2 (`attempts.used = 2/2`) hits a genuine `G3` scope block or `O2` obsolete legacy test, `closures_submitted` is `1 < min_attempts_before_block (2)`. `actl` rejects the `blocked` claim at `G2` and triggers `attempts_exhausted`, where the Architect is **prohibited from choosing `update_scope` (fast-path qualification)** and is forced to run a full `reopen_oracle` Challenger loop.


* **ii.** Conversely, because §5.4.1 increments `closures_submitted` whenever `closure-{seq}.json` is merely schema-valid (even if `reason: blocked` is rejected by `G2`), an Implementer can submit an invalid `reason: blocked` on attempt 1 (`closures_submitted = 1`) and immediately re-submit `reason: blocked` on attempt 2 (`closures_submitted = 2 >= 2`) without ever attempting `reason: done`.




* **b) Proposed Fix:**
* **i.** Add `update_scope` to `legal_actions` for `attempts_exhausted` (`stage: implementer`) in §6.3.


* **ii.** In §5.4.1–§5.4.2, specify that `closures_submitted` only increments on schema-valid `reason: done` closures (or accepted `reason: blocked` closures), and change precondition 1 of `blocked` to require `closures_submitted >= min_attempts_before_block - 1` prior `done` closures (or waive precondition 1 when `blocking_step` is `"G3"` or `"O2:{test}"`, since scope/frozen-test blocks cannot be overcome by retrying without scope changes).






* **3.3. `attempts.live` Resets on Every New Epoch and `retry_live` Double-Counts Live Runs (§4.1, §5.1, §5.5.3, §6.1.2, §6.3)**
* **a) Issue:**
* **i.** §4.1 (`[max_attempts] # per epoch`) and §5.1 state that all per-epoch attempt counters (`oracle`, `implementer`, `live`, `curator`) reset to the `sprint.toml` baseline whenever `epoch` increments on `update_scope` or `reopen_oracle`. Because one of the Architect's resolutions for `live_failed` is `reopen_oracle` (§5.5.3, §6.3), choosing `reopen_oracle` after a failed Live Run resets `attempts.live` back to `0`, allowing the Architect to run up to `max_epochs × max_attempts.live` (`3 × 2 = 6`) Live Runs against real credentials without halting to the Owner!


* **ii.** In §5.5.3, when Live Run 1 fails (`attempts.live = 1` of `max_attempts.live = 2`), `actl` immediately escalates `live_failed` to the Architect *before* attempt 2 is used. If the Architect resolves a transient network flake with `retry_live` ("+1 live attempt", §6.3), the total budget becomes `2 + 1 = 3` runs, AND §5.5.3 says *"the loop then repeats Architect action → Offline green again → Live Run again"*, unnecessarily re-running the Offline Run on an unchanged `{head_sha}`.


* **iii.** In §6.3 Row 7 (`live_failed`), `escalate_owner` is omitted from the Architect's `legal_actions`.




* **b) Proposed Fix:**
* **i.** Make `attempts.live` a **sprint-wide** counter (never reset on `epoch` increment) in §4.1 and §5.1.


* **ii.** Clarify in §5.5.3 and §6.3 that with `max_attempts.live = 2`, Live Run 1 failure (`attempts.live = 1 < 2`) routes `live_failed` to the Architect where `retry_live` re-invokes `actl-live-run` directly on the already-approved `{head_sha}` without incrementing `max_attempts.live` (consuming the 2nd attempt in `max_attempts.live = 2`) and without re-running the Offline Run, while `grant_attempts` / `reopen_oracle` require passing the Offline Run on the new `{head_sha}` before consuming the 2nd Live Run attempt. Add `escalate_owner` (for Architect) and `abort` (for Owner) to the `live_failed` row in §6.3.






* **3.4. Missing Owner `legal_actions` When `escalate_owner` or `max_epochs` Exhaustion Fires (§4.1, §5.1, §6.3)**
* **a) Issue:** §5.1 states that once `epoch` would exceed `max_epochs`, `update_scope` and `reopen_oracle` are no longer legal and the escalation routes to the Owner. Likewise, the Architect can resolve any escalation with `escalate_owner`. However, the §6.3 routing table defines no `legal_actions` for the Owner when receiving an `escalate_owner` handoff or a `max_epochs`-capped escalation.


* **b) Proposed Fix:**
* **i.** Add a rule beneath the §6.3 table specifying that when any escalation is routed to the Owner (via `escalate_owner`, `max_epochs` cap, or `live_failed` exhaustion), the Owner's `legal_actions` are `grant_attempts`, `update_scope`, `reopen_oracle`, `waive_mutant` (if `stage == "oracle"` and `failing_checks` is empty), `retry_live` (if `stage == "live"`), and `abort` (and that Owner-initiated `update_scope`/`reopen_oracle` automatically increments `max_epochs` by 1).







---

### 4. Verification Gate Regressions & Phase 4 Anti-Slop Bypass

* **4.1. Phase 4 `E1.4` + `E1.5` Re-Opens the `ImportError` Vacuous-Test Bypass (§4.2, §5.2.1, §5.6.2)**
* **a) Issue:** In the 23:30 revision, `E1.4` was rewritten to state: *"At least one new test must fail. A graduated test that passes at base is allowed only if `E1.5` shows it failing under at least one mutant that `coverage.md` maps to its originating proof."*

* **i.** If a graduated test in `NN-graduate-tests.patch` imports a new symbol introduced in feature commits `01..N-1` and contains a vacuous assertion (`from app.new_mod import foo; def test_x(): assert True`), running `test_x` at `base_sha` (`E1.4`) **fails with `ImportError` / `NameError` / compile error (`exit != 0`)**!
* **ii.** Because `test_x` **failed** at `base_sha` (rather than passing at base), `E1.4` treats `test_x` as already satisfied and does **not** require `test_x` to kill any mutant in `E1.5`! If another test in the suite kills the mutant in `E1.5`, `test_x` (`assert True`) passes both `E1.4` and `E1.5` completely unchallenged!


* **iii.** Furthermore, in Phase 2 (`Q5`, §5.2.1), `actl` requires every mutant to be mapped to proofs in `coverage.md`, but `Q5` only checks that *at least one* proof in `proofs/` exits `1`—it never verifies that the mutant is killed by the **specific proof(s) mapped to it in `coverage.md**`, nor that every proof in `coverage.md` has at least one mutant mapped to it!




* **b) Proposed Fix:**
* **i.** In `Q5` (§5.2.1), require every requirement/proof in `coverage.md` to map to $\ge 1$ mutant, and define a mutant as `killed: true` only if at least one of its **mapped** proofs in `coverage.md` exits `1`.


* **ii.** In `E1.4` and `E1.5` (§5.6.2), tighten the per-test rule: every graduated test identified by a `Graduated-Proof: {proof} → {test_file}::{test_name}` trailer must **either** (1) fail at `base_sha` (`E1.4`) via an **assertion failure after successful module import/collection** AND kill at least one mutant mapped to `{proof}` in `E1.5` if `{proof}` has mapped mutants, **or** (2) if it passes at `base_sha` or fails at `base_sha` during import/collection/compile (`ImportError`, `SyntaxError`, `NameError`), it **must** fail (`exit != 0` on assertion) under at least one mutant mapped to `{proof}` in `E1.5`.






* **4.2. Phase 2 `Q2` (`solution_key_guards`) Omits `G4` (Legacy Test Function Count Conservation) (§2.3, §5.2.1)**
* **a) Issue:** §2.3 and §5.2.1 define `Q2` as checking only `G3`, `G5`, and `G6`, omitting `G4`. If the Architect unfreezes a legacy test file (`ALLOW: test/{specific_file}`) in Phase 2 and `solution_key.patch` deletes a `test_*` function, `Q2` passes `solution_key.patch` in Phase 2, but when `solution_key.patch` is handed to the Implementer in Phase 3 (`solution_key_exposure: full`), the Implementer immediately fails `G4`.


* **b) Proposed Fix:**
* **i.** Include `G4` in `Q2` (`G3–G6`) in §2.3 and §5.2.1.






* **4.3. Phase 2 `lock_oracle` Re-Qualification Failure Bypasses Architect Review (§5.2.3)**
* **a) Issue:** In §5.2.3 Path 1 (`when diagnostic_case == "solution_key_conflict"`), if the Architect fixes `solution_key.patch` and emits `lock_oracle`, `actl` runs a new `qual-{seq}`. The text states: *"if `diagnostic_case` is now `"none"`, `actl` freezes the oracle and mints the contract, otherwise (a mutant now fails with `apply_error: true` or survives) it routes as `revise_oracle`."*

* **i.** If `actl` routes directly to the Challenger as `revise_oracle` without first returning the new `qual-{seq}` to the Architect, the Challenger is dispatched with `oracle-decision.json` still containing `{"decision": "lock_oracle", "feedback": null}`, and if the re-qualification failed because of a typo in the Architect's `solution_key.patch` (`solution_key_conflict`), the Challenger cannot fix `solution_key.patch`.




* **b) Proposed Fix:**
* **i.** Change §5.2.3 Path 1 so that if the re-qualification `qual-{seq}` has `diagnostic_case != "none"`, `actl` stages the new `qual-{seq}` in `architect-inputs/` and re-invokes the Architect (matching the universal rule in §5.2.3 sentence 1: *"after every `qual` ... `actl` stages the results in `architect-inputs/` and invokes the Architect"*).







---

### 5. Policy Signing, Live Wrapper Enforcement & `sprint.toml` Amendment Collisions

* **5.1. Missing Environment-Variable Allowlist Key in `sprint.toml` for `actl-live-run` (§4.1, §5.5.3 vs. `*2330_changes.md` #11)**
* **a) Issue:** `*2330_changes.md` #11 states: *"The live wrapper verifies it, reads the policy, and checks the allowlisted env-var names."* In `*2330.md` §5.5.3, step 2 of `/usr/local/bin/actl-live-run` says *"Loads the allowlisted secret environment variables from `/etc/actl/live.env` into process memory"*, but `sprint.toml` (§4.1) has no field declaring the allowlisted environment variable names, and step 1 of `actl-live-run` does not check them.


* **i.** Additionally, step 1 of `actl-live-run` (§5.5.3) says it checks that `architect-outputs/live-decision.json` *"is owned by account `architect` and matches `contract_sha256` and `{head_sha}`"*, forgetting to require `"decision": "approve_live"` (a `"reject_live"` file also matches those checks) and omitting `{contract_sha256}` from the wrapper CLI arguments (`sudo /usr/local/bin/actl-live-run {sprint_tag} {head_sha}`).




* **b) Proposed Fix:**
* **i.** Add `live_env_vars = ["..."]` to `sprint.toml` in §4.1 (required when `live_run = "required"`).


* **ii.** Update `/usr/local/bin/actl-live-run {sprint_tag} {contract_sha256} {head_sha}` in §5.5.3 so step 1 verifies `decision == "approve_live"`, `contract_sha256`, and `{head_sha}` (or `runs/live-decision-{seq}.hmac` in `owner` mode), and step 2 exports only the variable names listed in `sprint.toml`'s `live_env_vars` from `/etc/actl/live.env`.






* **5.2. `actl sprint amend` Invalidates Immutable `contract-{seq}.json` (`sprint_sha256`) Mid-Epoch (§4, §4.1, §4.3, §6.1.1)**
* **a) Issue:** §4.1 allows the Owner to modify `sprint.toml` after freeze via `actl sprint amend` (for example, to remove an unsupported `hard_cap` dimension after a `halt: unsupported_cap` in Phase 3 or Phase 4, §6.1.1). However, `contract-{seq}.json` locks `sprint_sha256` and is never mutated during an epoch (§4, §4.3, §5.1).


* **i.** Amending `sprint.toml` mid-epoch changes its SHA-256 hash and `sprint.hmac`, breaking `contract-{seq}.json`'s `sprint_sha256` pointer and erasing prior baseline values needed for deterministic `state.json` replay (§4).




* **b) Proposed Fix:**
* **i.** Specify in §4.1 that `actl sprint amend` writes a versioned `sprint-{seq}.toml` (and `sprint-{seq}.hmac` when required) and updates `active_sprint_policy` in `state.json` (or, if in Phase 3, re-mints `contract-{seq+1}.json` within the current epoch carrying the new `sprint_sha256` without resetting attempt counters).
