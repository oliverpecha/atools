# Context Extraction Memo: Agent Graph Architecture & Governance Specification

**Purpose:** This memo consolidates all architectural conclusions, role definitions, artifact schemas, control-flow mechanics, and governance policies agreed upon during the design review. It supersedes earlier terminology and resolves the structural gaps identified in the initial diagram set.

**Revision note:** This revision streamlines the architecture into a direct `Architect ↔ Gate ↔ Challenger` oracle loop (retiring the separate `Prover` role by default while preserving `oracle_author: challenger | prover` as a config option), separates Phase 1–3 runtime state (`state.json`) from the immutable Phase 3 implementation lockfile (`contract.json`), moves all self-tested mechanical guards and git tree-equality checks to execute *before* Offline Runs and Approver reviews, unifies `dispute` and `blocked` into a single `blocked` closure gated by `min_attempts_before_block` and `solution_key_divergence` (eliminating redundant `dispute_verification` runs), splits `checklist/<spec>.md` tracking into explicit `Offline Run` and `Live Run` columns with a `waived` token for accepted traps, clarifies `amaster` prefix-cached stateless leaf execution, and settles `solution_key_exposure` as `full | hidden` (default `full`).

---

## 0. What Changed from `graph-exploration.md` (v.6 Migration Map)

| `graph-exploration.md` v.6 Term | New Specification Equivalent | Summary of Structural Change |
| --- | --- | --- |
| **Oracle author / Oracle reviewer** | **Challenger** | Single cross-family adversarial leaf node (replaces the separate Prover + Challenger pair by default; configurable via `oracle_author: challenger | prover`). Audits `Spec vN` and `solution_key.patch`, asks proof-blocked clarifications (`clar-NN.md`), and authors `Oracle v1` (`proofs/`, `probe.sh`, `traps/`, `scope.txt`, `coverage.md`). Disagreements during `review_rounds` produce the next `Oracle vN` directory directly—no separate "review note" artifact exists.

 |
| **Diff reviewer** | **Archivist** | Reviews the approved diff for semantic risk *after* all offline and live runs pass, curates `backlog-proposal.md`, and writes the commit plan.

 |
| **`ACCEPTANCE.md` / Ledger** | **Checklist (`checklist/<spec>.md`)** | Tracked per-spec checklist initialized at oracle freeze (`open`), recording separate `Offline Run` and `Live Run` evidence columns, and stamped `done` mechanically by the Gate when all mapped proofs in `coverage.md` plus `probe.sh` pass on the identical `head` SHA (or `waived` for accepted surviving traps).

 |
| **Implementation brief / Runbook** | **Work order** | Not a newly authored prose file; a mechanical bundle of `spec-vN.md` + `contract.json` (+ `solution_key.patch` when `solution_key_exposure: full`, and optional `prior_attempt` on retry).

 |
| **Known-good reference** | **Solution key (`solution_key.patch`)** | Authored once by the Architect in the Spec phase, audited by the Challenger, and copied into the Oracle directory at freeze (one owner, one hash). Passed to the Implementer as a starting draft when `solution_key_exposure: full`, but never merged directly into the target repository without passing the Implementer/Gate/Archivist pipeline.

 |
| **Mutants / Wrong implementations** | **Traps (`traps/*.patch`)** | Deliberately flawed patches supplied by the Challenger that violate a spec clause and must be killed (exit `1`) by the oracle.

 |
| **Stop report / Session result** | **Implementation closure report (`closure-NN.json`)** | Written by the Implementer when halting itself (`reason: done | blocked`), carrying `proof_id`, `solution_key_divergence`, `detail`, `notes[]` (for Archivist), and `backlog[]`.

 |
| **Dispute report / Pruned packet** | **Escalation record (`escalation-NN.json`)** | Assembled mechanically by `amaster` and routed strictly via `amaster → Architect` on `retries_exhausted`, `review_rounds_exhausted`, `budget_kill`, or `blocked` (with `oracle_review` populated only when `trigger: review_rounds_exhausted`, else `null`).

 |
| **Evidence report** | **Gate evidence record (`runs/ev-NN.json`)** | Untracked per-run execution receipts written by the Gate to `runs/`, cited by SHA-256 hash in the Checklist.

 |
| **Offline gate / Live gate** | **Offline run / Live run** | "Gate" (`agate`) is strictly the runner component; `Offline run` (keys blanked) and `Live run` (real Owner credentials) are execution stages.

 |
| **Approved snapshot** | *(Internal git tag)* | Retired as a named package; the Gate pins the approved tree via an internal git tag keyed by contract hash before `amaster` invokes the Archivist.

 |
| **Final history** | **Archivation plan** | A directory (`diff-risk-review.md`, `backlog-proposal.md`, `commit-plan.sh`, plus `plan/` patch/message pairs) routed via two distinct edges: `Archivist → Gate` (solid, including regex and git tree-equality verification) and `Gate → Approver` (dashed).

 |
| **`sessions.tsv` schema** | **Extended `sessions.tsv` schema** | Logs every CLI invocation (`model`, `turns`, `tokens`, `cost`, `accepted_items`) plus `clarification_rounds` and `escalation_alerts_sent` events so `state.json` can be reconstructed alongside `runs/ev-*.json` and `escalation-NN.json`.

 |

---

## 1. Graph Topology & Visual Semantics

### 1.1 Single Source of Truth & Generated Views

* **Canonical Source (`graph.toml`):** One primary persona graph serves as the central representation, while Views `02` (Swimlane Sequence), `03` (Context and Session Views), and `04` (Guard Map) are retained as generated views derived from the same `graph.toml` definition. The Guard Map functions as an annotation layer over the persona graph rather than an independent topology.


* **Primary Deliverable:** Raw `.mmd` Mermaid definitions are the canonical visual artifacts (rendered at full resolution via `mermaid-cli` or native Markdown viewers rather than auto-layout PNG thumbnails).


* **Current Morphology:** The workflow operates as a deterministic spine (`amaster`) orchestrating bounded loops (spec clarification, adversarial oracle qualification, implementation retries, escalation resolution, and closeout archivation).


* **Escalation edges in the graph:** A single `amaster → Architect` edge (never drawn through the Implementer) carries the `Escalation record` for `retries_exhausted`, `review_rounds_exhausted`, `budget_kill`, and `blocked`. `high_risk_diff` is intentionally **not** drawn (parked in §7 and `NOTES.md`).



### 1.2 Orthogonal Edge Semantics & Stateless Prefix Caching

Every edge in the graph is classified along two independent axes: **acceptance verification** (line style) and **routing role** (color or arrowhead).

| Axis | Visual Encoding | Classification & Mechanics |
| --- | --- | --- |
| **Axis 1: Who Accepts the Hand-off** *(Verification)* | **Solid Line** | **Deterministic / Objective:** Accepted or enforced by a script or mechanical check that inspects the transfer and rejects violations (e.g., JSON schema validation on an LLM-written closure report, `git diff` scope checks, regex and git tree-equality checks on commit plans, deterministic session invocation).

 |
| **Axis 1: Who Accepts the Hand-off** *(Verification)* | **Dashed Line** | **Probabilistic / Subjective:** Accepted by an LLM or human exercising judgment (e.g., `Architect ↔ Challenger` spec/oracle hand-off, `Gate → Approver` archivation judgment). Left dashed intentionally because no regex can verify semantic quality.

 |
| **Axis 2: What Travels** *(Routing Role)* | **Standard Arrowhead / Primary Color** | **Unmodified Artifact Flow (`Persona → Persona`):** Visually represents an artifact authored by one persona (`spec-vN.md`, `Oracle vN`) whose file pointer is handed unmodified to the next persona when scheduled by `amaster`.

 |
| **Axis 2: What Travels** *(Routing Role)* | **Open Arrowhead / Distinct Control Color** | **Control & Synthesized Envelope Flow (`amaster → Persona`):** Scheduling signals and pointers to `amaster`-synthesized JSON envelopes (`contract.json`, `Work order`, `escalation-NN.json`). **Because `amaster` invokes sessions deterministically via script, control edges are drawn as solid lines** (distinguished by their open arrowhead and control color, never dashed).

 |

* **Runtime Routing & Prompt-Cache Discipline:** At runtime, all artifacts reside on disk and `amaster` routes file pointers (which contain LLM-authored prose, code comments, diffs, and string fields like `notes[]`, `detail`, or `log_tail`) to each session. Saying "`amaster` never interprets prose" means `amaster`'s routing logic branches strictly on deterministic schema fields (enums, hashes, exit codes, counters), never on free-text strings. While the **Architect** maintains a persistent session across a spec's lifecycle (to preserve end-to-end Q&A context with the Owner), all leaf personas (**Challenger**, **Implementer**, **Archivist**) execute as fresh, stateless CLI invocations where `amaster` frontloads static, non-updated files (`Spec vN`, `contract.json`, `solution_key.patch`) ahead of dynamic turn feedback (`clar-NN.md`, `prior_attempt`) to maximize provider prompt-cache hits without dragging dead-end turn history.



### 1.3 Resolution of Formerly Unguarded Edges

1. **Implementer → `amaster` (Session Closure & Pre-Check Guards):** Guarded mechanically (**solid line**) *before* any Offline Run executes. `amaster` validates that `closure-NN.json` conforms to schema (`reason: done | blocked`, `notes`, `backlog`, plus `min_attempts_before_block` and `solution_key_divergence` when `reason: blocked`), while the Gate runs the self-tested mechanical guards: `git diff BASE..HEAD` against `ALLOW`/`FROZEN` scope (`scope.txt`), untouched oracle hash verification, credential/secret leak scan, and forbidden-call lint. If any guard fails, the Gate emits a red `runs/ev-NN.json` citing the violated guard and `amaster` routes it identically to a failed Offline Run (consuming 1 retry and passing the guard failure in `prior_attempt`).


2. **Archivation Plan Hand-off (Split into Two Explicit Edges):** Because the `Archivation plan` undergoes both mechanical policy verification and semantic review, it is modeled as two separate edges rather than a single mixed edge:


* **Edge 1 — `Archivist → Gate` (Solid Line / Script-Accepted):** `amaster` enforces the precondition that `diff-risk-review.md`, `backlog-proposal.md`, `commit-plan.sh`, and the `plan/` directory exist and parse. The Gate runs the deterministic regex policy check on `commit-plan.sh` and `plan/*.msg` (subject format, required git trailers, no forbidden paths, every `plan/NN-<slug>.patch` has a matching `plan/NN-<slug>.msg`) **and ephemerally executes `commit-plan.sh` in a detached worktree to verify git tree-equality against the pinned contract-hash git tag**.


* **Edge 2 — `Gate → Approver` (Dashed Line / LLM- or Human-Accepted):** Once Edge 1 passes (guaranteeing the commit plan applies cleanly and produces the exact approved tree), the validated `Archivation plan` is handed off to the Approver (`architect` or `owner`) for semantic judgment of `diff-risk-review.md`, `commit-plan.sh`, and `backlog-proposal.md` dispositions. If either Edge 1 (Gate) or Edge 2 (Approver) rejects the plan, `amaster` re-invokes the Archivist with the rejection reason, bounded by `review_rounds` (escalating on exhaustion).





---

## 2. Core Vocabulary & Verification Concepts

| Term | Definition |
| --- | --- |
| **Proof** | A single executable script (`proofs/*.sh`) verifying a specific spec requirement. Exits `0` (pass) or `1` (fail).

 |
| **Oracle** | **An artifact, not an actor.** A frozen, hashed directory containing `proofs/`, `probe.sh`, `scope.txt`, `solution_key.patch`, `traps/`, and `coverage.md`. It does not execute itself or message agents; the Gate executes it against the target codebase.

 |
| **Test** | The target repository's own pre-existing test suite.

 |
| **Guard** | A mechanical process check (e.g., file scope enforcement, credential leak scan, forbidden-call lint, untouched oracle hash check, commit message regex, git tree-equality). **Proofs judge code; guards judge process.**

 |
| **Gate (`agate`)** | The deterministic runner ("club door bouncer") that executes guards and proofs, writes `Gate evidence records`, and mechanically stamps the `Checklist`. Exercises zero judgment and writes no prose.

 |
| **Offline Run** | *(Replaces "offline gate" / "dry run")* Full execution of the oracle by the Gate (after closure guards pass) with real credentials blanked, protecting against untrusted Implementer code.

 |
| **Live Run** | *(Replaces "live gate")* Execution of the oracle against live external services using real credentials stored strictly in the Owner's environment/secret store.

 |
| **Solution Key (`solution_key.patch`)** | *(Replaces "known-good reference" / "answer key")* A reference implementation patch authored once by the Architect in the Spec phase, audited by the Challenger, and copied into the Oracle directory at freeze so it has **one owner and one canonical hash**. Proves satisfiability (Base = red, `solution_key.patch` = green) and serves as the Implementer's initial draft when `solution_key_exposure: full`. **A solution key is never merged directly into the target repository without passing the Implementer, Gate, and Archivist closeout pipeline.**

 |
| **Traps** | *(Replaces "mutants" / "wrong implementations")* Deliberately flawed patches (`traps/*.patch`) written by the Challenger that violate a specific spec requirement to test whether the oracle catches them. A trap is **killed** if at least one proof goes red, and **survives** if all proofs stay green.

 |
| **Recomputation** | The oracle's end-to-end probe (`probe.sh`, Premise 5), which independently calculates claimed metrics from raw data (e.g., SQL counts, `git show --numstat`) and compares them against the implementation's output.

 |

---

## 3. Personas, Authority & Independence Rules

### 3.1 Premise 7 Clarification

* **Premise 7 Formulation:** *"A persona may keep its own context across its own turns; what passes between personas is artifacts only."*

* Because Premise 7 restricts the communication channel *between* distinct personas rather than prohibiting a single persona from maintaining state across its own turns, the Architect's persistent context across a spec's lifecycle is natively compliant and requires no exception. Leaf personas (`Challenger`, `Implementer`, `Archivist`) run fresh per session with static artifacts frontloaded by `amaster` for prompt-cache efficiency.



### 3.2 Persona Roster & Responsibilities

| Persona | Type | Context Lifecycle | Core Responsibilities |
| --- | --- | --- | --- |
| **Owner** | Human | Continuous | Supplies initial intent, holds live credentials, resolves human-level escalations, approves live runs or archivation plans when configured as `owner`, decides which `backlog-proposal.md` items enter the repo backlog, and executes the final `git push` / merge.

 |
| **Architect** | LLM (Frontier Model A) | **Persistent per Spec** | Acts as CTO/authority directly below Owner. Conducts initial Q&A with Owner, writes `Spec vN` and `solution_key.patch`, answers Challenger clarifications (`clar-NN.md`), resolves refinements during the Oracle qualification loop or escalations (`retries_exhausted`, `review_rounds_exhausted` including surviving traps, `budget_kill`, or `blocked`), approves the `Archivation plan` when configured as `architect`, and curates the repo backlog. (Durable notes file serves as context-overflow fallback).

 |
| **`amaster`** | Python Script | Stateless / Event-driven (persists `runs/<run-id>/state.json`) | Deterministic state-machine controller and router ("flight controller"). Launches headless sessions via idempotent write-ahead transitions, frontloads static file prefixes for cache hits, enforces file-existence preconditions, tracks budget counters in `state.json`, mechanically mints the immutable `contract.json` at Oracle freeze and assembles the `Work order`, assembles `Escalation records`, and emits solid control signals.

 |
| **Challenger** | LLM Leaf (Frontier Model B, Adversarial) | Fresh per session | *(Consolidates "Oracle author" + "Oracle reviewer"; configurable via `oracle_author: challenger | prover`)* Cross-family adversarial verifier. Audits `Spec vN` and `solution_key.patch`, requests proof-driven clarifications (`clar-NN.md`) if spec definitions are ambiguous, and authors `Oracle v1` (`proofs/`, `probe.sh`, `traps/`, `scope.txt`, `coverage.md`) to expose semantic gaps and weak assertions. Strictly focused on proving stated requirements, never extending features.

 |
| **Implementer** | LLM Leaf (Fast Workforce Model) | Fresh per attempt | Isolated worker on `wip/*`. Receives `Work order` (plus `solution_key.patch` when `solution_key_exposure: full`) and edits code, resolves dependencies, and adapts implementation within `ALLOW` scope until the Gate exits `0`. Never communicates with Challenger, cannot read Oracle proofs/traps (`proofs/`, `probe.sh`, `traps/`), and only sees failing lines from Gate runs. Emits an `Implementation closure report` (`done` or `blocked`).

 |
| **Gate (`agate`)** | Script | Stateless (persisted outputs: `qual.json`, `runs/ev-*.json`, checklist stamps, and git tag keyed by contract hash) | Runs Oracle qualification checks (`qual.json`), self-tested closure guards (scope, untouched oracle hash, secret scan, forbidden-call lint), offline runs, live runs, and closeout regex/tree-equality checks. Writes `qual.json` and `Gate evidence records`, stamps `Checklist` columns (`done` or `waived`), and pins the approved git tag keyed by contract hash.

 |
| **Archivist** | LLM Leaf | Fresh per session | *(Replaces the old "Diff reviewer")* Invoked once all required gates (including Live run, if required) are green. Reads `Spec vN`, the approved diff, and the Implementer's `notes`. Produces the `Archivation plan` (`diff-risk-review.md`, `backlog-proposal.md`, `commit-plan.sh`, `plan/`). Cannot alter code (enforced by Gate tree-equality check on Edge 1 before Approver review).

 |

### 3.3 Independence Matrix (Settled)

Every persona invocation runs in its own isolated session (`S`), so session separation is a universal baseline and omitted from the cells below. Rows are the persona being constrained; columns are the persona it is compared against. Blank cells indicate no constraint.

| Persona (row) | Architect | Challenger | Implementer |
| --- | --- | --- | --- |
| **Challenger** | **F** |  |  |
| **Implementer** | **P*** *(only when `solution_key_exposure: hidden`)* | **P** |  |
| **Archivist** |  |  | **F** |

* **F (Cross-Family Preferred):** Prefer a different frontier model family (Challenger auditing the Architect's `Spec vN` and `solution_key.patch` to author the `Oracle`; Archivist reviewing the Implementer's diff).


* **P (Private Artifacts Unreadable):** The Implementer is **always** mechanically blocked from reading the Challenger's test logic (`proofs/*.sh`, `probe.sh`, `traps/*.patch`). Access to the Architect's `solution_key.patch` is governed by `solution_key_exposure: full | hidden` (default `full`, where the Implementer reads `solution_key.patch` as an initial draft to adapt and self-repair on `wip/*`; `hidden` blocks `solution_key.patch` via `P`).



---

## 4. Standardized Artifact & Package Schemas

**Naming & Lifecycle Rules:**

* **Records** are structured data files emitted by an agent or the Gate.


* **Plans / Scripts** are actionable bundles reviewed and executed during closeout.


* **Single Ownership of `solution_key.patch`:** Authored by the Architect in the Spec phase, audited by the Challenger, and copied into the Oracle directory when frozen so it maintains a single owner and a single hash.


* **State vs. Contract Separation:** `runs/<run-id>/state.json` is initialized at Phase 1 start to track dynamic counters across all phases, whereas `contract.json` is minted **strictly once** at Oracle freeze (entering Phase 3) and remains immutable throughout the implementation run.


* **Internal Mechanisms:** Git tags used by the Gate to pin an approved tree state (keyed by contract hash) are internal mechanisms, not named packages.


* **Evidence numbering:** `ev-NN` is a monotonic counter per spec, kept in `runs/`, never reset between runs or contract versions. Examples below are independent scenarios that reuse low numbers for readability.



### 4.1 Phase 1: Spec Phase

| Package | From → To | Concrete Form | Example (`Add public profiles to users`) |
| --- | --- | --- | --- |
| **Intent** | Owner ↔ Architect | Conversational Q&A | `"Add public profiles to users"`<br> |
| **Spec vN** | Architect → Challenger | `spec-v2.md` (fixed headings: *Requirements*, *Locked*, *Deferred*), SHA-256 hashed | **R1:** Guests see name, bio, avatar, photo count of public profiles. **R2:** Never expose email. **R3:** Private profiles return 404. **Locked:** `users` schema unchanged. **Deferred:** Search engine indexing.

 |
| **Solution key** | Architect → Challenger (audit), Implementer (when `full`) | `solution_key.patch` (authored in Spec phase; copied into Oracle at freeze) | Working reference patch adding `is_public`, route, and serializer to prove the spec is satisfiable.

 |
| **Clarification** | Challenger ↔ Architect | `clar-01.md` (question + specific proof it blocks; bumps Spec to `vN+1`) | `"To write proof_01, what field defines a public vs. private profile?"` → `"is_public = true"`<br> |

### 4.2 Phase 2: Oracle Phase

| Package | From → To | Concrete Form | Example (`Add public profiles to users`) |
| --- | --- | --- | --- |
| **Oracle vN** | Challenger ↔ Architect (via Gate `qual.json`) | Directory: `proofs/`, `probe.sh`, `scope.txt`, `traps/`, `solution_key.patch`, `coverage.md` | `proofs/02_no_email.sh`, `traps/contact_leak.patch`<br> |
| **Coverage map** | Challenger → Oracle | `coverage.md` (frozen and hashed inside Oracle; lists every proof + `probe.sh` a `done` stamp depends on) | `R1 → proofs 01, 04, probe.sh`; `R2 → proofs 02, 05, probe.sh`; `R3 → proof 03`<br> |
| **Oracle qualification record** | Gate → `amaster`, Challenger, Architect | `qual.json` (command, exit code, and hashes for every qualification check) | `null_base: red (5/5)`, `traps_killed: 4/4`, `solution_key_green: 3/3 repeats`, `manifest_sha256: 8a1b...`<br> |
| **Checklist** | Initialized at freeze (`open`); stamped `done` or `waived` by Gate | `checklist/public-profiles.md` (tracked in gate repo; separate `Offline Run` and `Live Run` columns; cites green `ev-*` runs on identical `head` SHA) | `R2 | proofs 02, 05, probe.sh | Offline: ev-09, ev-10 (sha256: 4b1a...) | Live: ev-12 (sha256: 9c4d...) | done` *(or `Live: n/a` when `live_run: none`; accepted surviving traps stamped `waived | escalation-01 (sha256: ...)`)*<br> |

### 4.3 Phase 3: Implementation Phase

| Package | From → To | Concrete Form | Example (`Add public profiles to users`) |
| --- | --- | --- | --- |
| **Implementation contract** | `amaster` (minted once at Oracle freeze, immutable) → Gate, Implementer, Archivist | `contract.json` | Hashes of `spec-v2.md`, `Oracle v1`, and `qual.json`; `scope.txt` ref; initial resolved budgets (`min_attempts_before_block`, `retries`, etc.); `solution_key_exposure: full`; `live_run: required`; `approval_live_run: auto`; `approval_archivation_plan: architect`<br> |
| **Work order** | `amaster` → Implementer | Mechanical bundle of `spec-v2.md` + `contract.json` (+ `solution_key.patch` when `full`, + optional `prior_attempt` on retry) | Contains zero prose written by `amaster`. Defines `"done = all Gate guards and oracle proofs exit 0"`.

 |
| **Implementation closure report** | Implementer → `amaster` | `closure-NN.json` (`reason: done | blocked`, `proof_id`, `solution_key_divergence`, `detail`, `notes[]`, `backlog[]`) | `closure-02.json`: `{"reason": "blocked", "proof_id": "01", "solution_key_divergence": "solution_key.patch assumes is_public column exists, but DB migration is outside ALLOW scope", "detail": "is_public requires DB migration outside ALLOW", "notes": ["Reused serialize_user with exclude list"], "backlog": ["Avatar size limit unspecified"]}`<br> |
| **Gate evidence record** | Gate → `runs/` (untracked) | `runs/ev-07.json` (emitted on every guard rejection, partial run, or full Gate run) | `{"id": "ev-07", "stage": "offline", "command": "bash proofs/02_no_email.sh", "exit_code": 1, "output_sha256": "9f2c...", "oracle": "v1", "head": "a41c9e0", "failing_line": "FAIL: body contains seeded email"}`<br> |
| **Escalation record** | `amaster → Architect` | `escalation-NN.json`, assembled mechanically by `amaster`. `trigger` is one of `retries_exhausted`, `review_rounds_exhausted`, `budget_kill`, `blocked`. `oracle_review` is `null` unless `trigger: review_rounds_exhausted`. | See examples below.

 |

**Retry-exhaustion example** (attempts ended with `reason: done` closures and stayed red, so `last_closure` points to the latest one):

```json
{"spec": "spec-v2", "trigger": "retries_exhausted", "attempts": 2, "last_closure": "closure-02.json", "evidence": ["ev-07", "ev-08"], "diff_stat": "api/profile.py | 31 +++", "log_tail": "<last 40 lines>", "oracle_review": null}

```

**Budget-kill example** (session killed before it could write a closure; `last_closure` is `null` only because no closure was written. If earlier attempts wrote closures, point to the latest of those):

```json
{"spec": "spec-v2", "trigger": "budget_kill", "attempts": 1, "last_closure": null, "evidence": [], "diff_stat": "api/profile.py | 9 +", "log_tail": "<last 40 lines>", "oracle_review": null}

```

**Blocked example** (`reason: blocked`, accepted by `amaster` only after `attempts >= min_attempts_before_block`, green repo build/tests, and populated `solution_key_divergence`):

```json
{"spec": "spec-v2", "trigger": "blocked", "attempts": 2, "last_closure": "closure-02.json", "evidence": ["ev-07", "ev-08"], "diff_stat": "api/profile.py | 18 ++", "log_tail": "<last 40 lines>", "oracle_review": null}

```

**Review-rounds-exhausted example** (oracle loop; `amaster → Architect`, same record shape. Implementation-only fields are empty; the nullable `oracle_review` object is populated only for this trigger. All its values are filled mechanically; `surviving_traps` comes from the latest `qual.json`, never from agent prose):

```json
{"spec": "spec-v2", "trigger": "review_rounds_exhausted", "attempts": null, "last_closure": null, "evidence": [], "diff_stat": null, "log_tail": null, "oracle_review": {"rounds_used": 3, "latest": "v3", "latest_sha256": "5d2f...", "qual": "qual.json", "surviving_traps": ["traps/contact_leak.patch"]}}

```

### 4.4 Phase 4: Closeout Phase

| Package | From → To | Concrete Form | Example (`Add public profiles to users`) |
| --- | --- | --- | --- |
| **Archivation plan** | Edge 1: Archivist → Gate (solid: regex + tree-equality)<br>

<br>Edge 2: Gate → Approver (`architect` or `owner`, dashed) | Directory containing:<br>

<br>1. `diff-risk-review.md`<br>

<br>2. `backlog-proposal.md`<br>

<br>3. `commit-plan.sh`<br>

<br>4. `plan/` with `NN-<slug>.patch` / `NN-<slug>.msg` pairs | **1.** `verdict: approve`, risk notes on serializer reuse.<br>

<br>**2.** Merged follow-ups tagged `source: implementer` or `source: archivist` (or `none`).<br>

<br>**3.** `git apply --cached plan/01-public-profile-serializer.patch && git commit -F plan/01-public-profile-serializer.msg`, with `Spec:` and `Oracle:` trailers in the `.msg`.

 |

---

## 5. Lifecycle Mechanics & Loop Governance

### 5.1 State Persistence, Immutable Contract & Idempotent Transitions (`amaster`)

* **External State File (`runs/<run-id>/state.json`) vs. Immutable `contract.json`:** `amaster` initializes `runs/<run-id>/state.json` at the start of Phase 1 (completely outside the frozen oracle directory) to track runtime counters (`clarification_rounds`, `review_rounds`, `retries`, active stage, and any dynamic budget increments granted by the Architect during escalations). `contract.json` is minted **once** at Oracle freeze (entering Phase 3) and is never mutated during the implementation run; if the Architect grants additional retries on escalation, `state.json` is updated while `contract.json` remains static. If `state.json` is lost or corrupted, all counters and budget grants can be deterministically reconstructed from `runs/ev-*.json`, `escalation-NN.json`, and the extended `sessions.tsv` ledger (`model`, `turns`, `tokens`, `cost`, `accepted_items`, `clarification_rounds`, `escalation_alerts_sent`).


* **Idempotent Write-Ahead Transitions:** Every state transition is idempotent, keyed by `(run_id, spec_sha256, transition_id, attempt)` (and including `contract_hash` from Phase 3 onward), and writes a `"started"` marker to `state.json` *before* launching a process or sending an alert.


* If `amaster` crashes after launching an agent session but before recording completion, a restarted `amaster` detects the `"started"` marker and does not launch a duplicate session or double-spend the budget.


* Similarly, if an owner-unavailable timeout triggers during an Owner escalation wait, idempotency prevents sending duplicate escalation alerts.



### 5.2 Adversarial Oracle Qualification Loop (`Architect ↔ Gate ↔ Challenger`)

1. **Adversarial Authoring & Mechanical Qualification:**
* **Architect Spec & Reference Key:** In Phase 1, the Architect authors `Spec vN` and `solution_key.patch`.


* **Challenger Audit & Oracle Authoring:** In Phase 2, the cross-family Challenger audits `Spec vN` and `solution_key.patch` for semantic flaws (missing requirement coverage, shared misreadings, weak assertions such as checking `has("email")|not` when an email leaks under a renamed key `contact`). The Challenger requests clarifications (`clar-NN.md`) if `Spec vN` is ambiguous, and authors `Oracle v1` (`proofs/`, `probe.sh`, `traps/`, `scope.txt`, `coverage.md`). *(Note: If configured with `oracle_author: prover`, a dedicated Prover writes `Oracle v1` before the Challenger writes `Oracle v2`; under the default `oracle_author: challenger`, the Challenger authors `Oracle v1` directly).*


* **Mechanical Qualification (`qual.json`):** The Gate runs `Oracle v1`, verifying that the null base implementation fails (`red`), `solution_key.patch` passes repeatedly (`green`), and all `traps/*.patch` are killed (`red`).




2. **Four-Layer Defense Against Weak Proofs:**
* *Value-level sentinel proofs:* Seed known sentinel strings (e.g., a test email) and fail if the literal string appears anywhere in the raw response payload.


* *End-to-end probe (`probe.sh`):* Inspects actual runtime outputs and performs independent recomputation.


* *Adversarial traps:* Challenger supplies executable patches (`traps/contact_leak.patch`) that expose weak assertions.


* *Visible residual risk:* Any surviving trap accepted at escalation is explicitly stamped `waived | escalation-NN (sha256: ...)` in `checklist/<spec>.md`.




3. **Deterministic Convergence & Budget Exhaustion Resolution:**
* **Immediate Freeze on Green `qual.json`:** If `qual.json` passes completely (`null_base: red`, `solution_key: green`, `traps_killed: all`), `amaster` freezes the Oracle immediately and mints `contract.json`.


* **Refinement Iterations (`v2`, `v3`):** If `qual.json` is `red` (e.g., a Challenger proof exposed a flaw in `solution_key.patch`, an over-strict proof rejected a valid `solution_key.patch`, or a trap survived), `amaster` wakes the Architect/Challenger to resolve the discrepancy (producing `Oracle vN` directly—no separate "review note" artifact is created), bounded by the budget function's `review_rounds` limit.


* **When `review_rounds` Budget Runs Out (`trigger: review_rounds_exhausted`):** `amaster` assembles `escalation-NN.json` (with `oracle_review` populated from `qual.json`) and routes it via `amaster → Architect`. Surviving traps are covered by this trigger. The Architect chooses one of three actions:


1. Grant additional `review_rounds` budget in `state.json` for the Oracle loop.


2. Write the next oracle version (`Oracle vN`) directly (re-verified by `qual.json`).


3. Accept the residual risk and grant no further rounds: the latest oracle version freezes and proceeds directly to implementation, with any surviving traps recorded as `waived | escalation-NN (sha256: ...)` rows in `checklist/<spec>.md`.







### 5.3 Coverage Map & Checklist Stamping Rule

* `coverage.md` explicitly lists every proof ID (plus `probe.sh`) required to satisfy each requirement (`R_i → [proof_a, proof_b, ..., probe.sh]`).


* `checklist/<spec>.md` tracks `Offline Run` and `Live Run` receipts in separate columns:
* When `live_run: none`, the `Live Run` column is initialized to `n/a`, and the Gate stamps the row `Status: done` once all mapped proofs and `probe.sh` exit `0` (`green`) in the `Offline Run` against the **exact same `head` commit SHA** (pinned by the contract-hash git tag).


* When `live_run: required`, `Status` remains `open` after the `Offline Run` column is populated and only flips to `done` when the `Live Run` column also records `0` (`green`) receipts for all mapped proofs and `probe.sh` on the **identical `head` commit SHA**.


* Partial runs during implementation retries emit `runs/ev-NN.json` for feedback only and never stamp `checklist/<spec>.md`.


* Closeout requires **zero `open` rows** in `checklist/<spec>.md` (every row must be `done` or `waived | escalation-NN`).



### 5.4 Implementation Routing, Retries & Blocked Escalations (Settled)

1. **Retry / Restart Mechanics:** When a Gate guard or Offline run is red and retry budget remains, `amaster` launches a fresh Implementer session in a clean worktree at base with a cleared context (frontloading static prefixes + `solution_key.patch` when `full`). It attaches `prior_attempt` (the previous diff patch, failing lines from the last `Gate evidence record`, and attempt count) strictly as an optional hint. `log_tail` from Escalation records goes to the Architect only and is never forwarded to a later Implementer.


2. **Deterministic Routing on Closure `reason`:**
* `reason: done` → Triggers Gate **Closure Guards** followed immediately by the **Offline run**.


* `reason: blocked` *(Consolidates former `blocked` and `dispute`)* → Implementer halts when it cannot satisfy the Gate due to an `ALLOW` scope restriction, missing architectural decision, or suspected over-constrained proof.


* **Anti-Early-Give-Up Guards:** `amaster` and the Gate mechanically reject `reason: blocked` (treating an invalid `blocked` claim as a failed attempt that consumes 1 retry) unless:
1. `attempts >= min_attempts_before_block` (configured via the budget function),
2. the target repository's own compilation and pre-existing test suite (`Test`) pass and all mechanical `ALLOW`/secret/lint guards are green, and
3. `closure-NN.json` includes a non-empty `solution_key_divergence` explaining why `solution_key.patch` could not be applied or adapted to pass the failing proof.


* **Escalation Routing:** Once those preconditions are met, `amaster` assembles `escalation-NN.json` (`trigger: blocked`, citing `last_closure` and `evidence`) and routes it via `amaster → Architect`. *(Because `qual.json` already proved `solution_key.patch` is green in Phase 2, the Gate does not re-run the proof against `solution_key.patch`)*. The Architect inspects `escalation-NN.json` and either (a) updates `scope.txt` / `Spec vN` / `Oracle vN` (starting a new contract run), or (b) rejects the block and grants retry budget in `state.json`.




* *External Budget Termination (`trigger: budget_kill`):* If a session is killed by wall-clock timeout or turn/cost caps, `amaster` synthesizes `escalation-NN.json` from `state.json` counters and routes it via `amaster → Architect`. `last_closure` is `null` only if the killed session never wrote a closure and no earlier attempt did.





### 5.5 Closure Guards, Offline Run, Live Run & Archivation Sequence (Settled)

1. **Step 1 — Self-Tested Mechanical Closure Guards (Before Offline Run):** Upon `Implementer → amaster` closure, and *before* executing untrusted Implementer code in an Offline or Live run, `amaster` validates `closure-NN.json` and the Gate runs the mandatory mechanical guards:


* File `ALLOW` / `FROZEN` scope check (`scope.txt`) and untouched oracle hash check.


* Credential and secret leak scan.


* Forbidden-call lint.


* **Mandatory Self-Tests:** `approval_live_run: auto` is only safe because these pre-checks are strict. Per design rules requiring lints to have self-tests, **every guard/scanner must pass its own built-in self-test** (verifying it catches known synthetic leaks and forbidden calls) so a broken lint cannot silently pass.




2. **Step 2 — Offline Run:** Once Step 1 guards are green, the Gate executes the oracle with credentials blanked and stamps the `Offline Run` column in `checklist/<spec>.md` when green.


3. **Step 3 — Live Run (Before Archivist):** Governed by `live_run: none | required` and `approval_live_run: auto | architect | owner`. **`approval_live_run: auto` means the Owner pre-authorized the live run in `contract.json`, and the live run still executes strictly within the Owner's environment/account (where the real credentials reside), never under the low-privilege runner user**; the Gate script itself never holds or stores the real keys. When green, the Gate stamps the `Live Run` column and marks `Status: done` in `checklist/<spec>.md`.


4. **Step 4 — Archivist Curation:**
* Only after Closure Guards, Offline run, and Live run (when required) are all green and zero `open` rows remain in `checklist/<spec>.md`, the Gate pins the approved state via an internal git tag **keyed by contract hash**, and `amaster` invokes the Archivist.


* The Archivist consumes the Implementer's `notes` to inform `diff-risk-review.md` and craft commit messages in `plan/*.msg`, without forwarding `notes` as a file.


* The Archivist merges the Implementer's `backlog` items with its own candidates into `backlog-proposal.md` (always written; contains `none` if empty so `amaster`'s precondition check stays unconditional).




5. **Step 5 — Closeout Policy & Tree-Equality Check, Approval, Backlog Curation & Owner Push:**
* **Solid Edge (`Archivist → Gate`):** `amaster` verifies all required files exist and parse, and the Gate runs the regex policy check on `commit-plan.sh` and `plan/*.msg` **plus ephemeral execution of `commit-plan.sh` to verify git tree-equality between the resulting final commit and the contract-hash-keyed git tag** (automatically failing the edge if the resulting tree differs from the tag).


* **Dashed Edge (`Gate → Approver`):** Governed by `approval_archivation_plan: architect | owner` (`auto` is prohibited). In a single turn, the approver reviews `diff-risk-review.md` and approves `commit-plan.sh`. If either the Gate (Edge 1) or Approver (Edge 2) rejects the plan, `amaster` loops back to the Archivist with the rejection reason (bounded by `review_rounds`, escalating on exhaustion).


* **Final Commit, Backlog Storage & Push:** Once approved, the verified commit chain is applied, the final stamped `checklist/<spec>.md` is committed to the gate repo (`runs/ev-*.json` remain untracked and disposable), `backlog-proposal.md` items are stored for the **Owner** to decide which items enter the repository backlog (without blocking the current green closeout), and the human **Owner pushes** to remote trunk.





---

## 6. Dynamic Budget & Escalation Functions

### 6.1 Budget Resolution Function & Fail-Closed Guard

All resource and iteration ceilings (`wall_clock`, `turns`, `tool_calls`, `tokens`, `cost_usd`, `retries`, `min_attempts_before_block`, `review_rounds`, `clarification_rounds`, `sessions_per_run`) are resolved dynamically at Phase 1 start into `state.json` and locked into `contract.json` at Phase 3 Oracle freeze:

```text
effective_limit(dimension, contract_or_state, context) -> (limit, mechanism, on_exceed)

```

* **Fail-Closed Adapter Guard:** Budget enforcement is fail-closed. If a contract specifies a hard budget dimension and the CLI adapter cannot confirm that the enforcement mechanism or CLI flag took effect, **the run refuses to start**.


* **Universal Wall-Clock Supervisor:** Every CLI engine retains the external `coreutils timeout -k 15s <limit>` wrapper as the hard wall-clock kill switch.



### 6.2 CLI Engine Budget Capabilities (Status as of October 2026)

| CLI Engine | Headless / Budget Flag Support | Operational & Adapter Rules |
| --- | --- | --- |
| **Anthropic Claude Code (`claude`)** | Supports `--max-turns <N>` and `--max-budget-usd <amount>`.

 | **Force print mode (`-p`) in the adapter**, because outside print mode these flags may be silently ignored. Retains external `timeout -k` supervisor.

 |
| **OpenAI Codex CLI (`codex`)** | Turn and step caps for `codex exec` were requested in Feb and Jul 2026 (defaulting to unlimited); unconfirmed whether closed. A token budget landed in an alpha build in Aug 2026.

 | Do not rely on unverified turn caps; enforce via external `timeout -k` supervisor, API spend gateway, and post-run telemetry gating (`asessions`).

 |
| **Google Antigravity CLI (`agy`)** | Headless flags include `--print-timeout`; no turn or spend cap found in reviewed cheat sheets.

 | `--print-timeout` returns partial output rather than killing the run, so **it cannot serve as a hard cap**. Rely on external `timeout -k` supervisor.

 |
| **Cursor Agent CLI (`agent`)** | Reviewed headless docs list no turn or spend flag *(absence from docs is not proof of non-existence)*.

 | Treat native turn/spend caps as unconfirmed (fail-closed if requested as native hard caps); rely on external `timeout -k` supervisor and post-run telemetry.

 |

### 6.3 Dynamic Escalation Policy Function

Escalation routing resolves dynamically at the moment an escalation event occurs:

```text
escalation_policy(event, contract, context) -> decision (logged with inputs)

```

* **Inputs:** Event type (`retries_exhausted`, `review_rounds_exhausted`, `budget_kill`, `blocked`), contract risk tier, time of day, and Owner availability. *(`high_risk_diff` was removed: nothing in the memo produces it. Parked in §7; see `NOTES.md`.)*


* **Safe Default on No Response (`hold`):** Availability windows, time-of-day routing, and `escalation_alerts_sent` apply strictly when `escalation_policy()` targets the human **Owner**. Architect escalations are synchronous LLM invocations; if an Owner escalation receives no response within the configured availability window (or if a synchronous Architect session fails/times out), the mandatory safe default is **`hold` (pause the run in `state.json` and await human Owner intervention)—never auto-approve**.


* **Hold scope:** `hold` applies strictly to the actionable party's decision; an unanswered informational Owner notification never blocks a run that the Architect can resolve.



---

## 7. Parked Items for Next Iteration

Three architectural items remain tracked before generating `graph.toml` and the `.mmd` views:

1. **Solution Key Exposure (`solution_key_exposure: full | hidden`):**
* Settled binary policy knob (`outline` retired as lossy/redundant). Defaults to `full` (passing `solution_key.patch` in the `Work order` so the workforce Implementer can apply, adapt, and self-repair it against repo dependencies, tests, and Challenger proofs), while retaining `hidden` in code for clean-room implementation runs.




2. **Work Items as True Graph Nodes:**
* Deciding whether a spec decomposes into parallel work-item nodes connected by `AFTER` dependency edges (concurrent Implementer loops on disjoint `ALLOW` scopes) or executes as a single node per spec.




3. **Risk-Tiered Approval / `high_risk_diff`:**
* Deciding whether `approval_archivation_plan` is resolved from the contract risk tier (e.g. `high → owner`). If adopted, `high_risk_diff` is unnecessary as an event. If a true event is wanted instead, it needs a producer (e.g. `verdict: approve | escalate` in `diff-risk-review.md`), a route, and a record shape.
