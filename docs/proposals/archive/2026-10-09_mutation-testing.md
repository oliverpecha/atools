# Context Extraction Memo: Agent Graph Architecture & Governance Specification (`2026-10-09_mutation-testing.md`)

**Date:** October 9, 2026
**Purpose:** This memo consolidates all architectural conclusions, role definitions, artifact schemas, control-flow mechanics, and governance policies agreed upon during the design review[cite: 1]. It supersedes earlier terminology and resolves the structural gaps identified in the initial diagram set and the October 8 review[cite: 1].

**Revision note (Oct 9):** This revision streamlines the architecture into a direct `Architect ↔ Gate ↔ Challenger` oracle loop (retiring `Prover` by default while preserving `oracle_author: challenger | prover`, and retiring separate Challenger clarification rounds `clar-NN.md`), standardizes on industry-convention **Mutation Testing** (`mutants/*.patch` with boolean `killed: true | false` and `mutant_waiver_authority: architect | owner`, default `architect`), separates Phase 1–4 runtime state (`state.json`) from the immutable Phase 3 implementation lockfile (`contract.json`)[cite: 1], enforces OS-level directory isolation (`chmod 700` on `gate-repo/`, shared `handoff/` IPC mailbox, and external `workspaces/` git worktrees), standardizes intra-session hard limits (`hard_cap` → `hard_cap_exhausted`) vs. stage-specific loop counters (`retries_oracle`, `retries_implementer`, `retries_archivist`), defines the fail-fast Offline Run order (`proofs/` + `probe.sh` first, existing repo `Test` suite second) and Phase 4 proof-to-test graduation into `test/`, sets `approval_archivation_plan: owner | architect` (default `owner`), and documents the complete Owner communication & context-piping blueprint.

---

## 0. What Changed from `graph-exploration.md` (v.6 Migration Map)

| `graph-exploration.md` v.6 Term | New Specification Equivalent | Summary of Structural Change |
| --- | --- | --- |
| **Oracle author / Oracle reviewer** | **Challenger** | Single cross-family adversarial leaf node (replaces the separate Prover + Challenger pair by default; configurable via `oracle_author: challenger | prover`)[cite: 1]. Audits `Spec vN` and `solution_key.patch` and authors `Oracle v1` (`proofs/`, `probe.sh`, `mutants/`, `scope.txt`, `coverage.md`) directly—no separate `clar-NN.md` or "review note" artifact exists[cite: 1]. |
| **Diff reviewer** | **Archivist** | Reviews the approved diff for semantic risk *after* all offline and live runs pass, curates `backlog-proposal.md`, graduates black-box `proofs/*.sh` into native repo tests (`test/`), and writes the commit plan[cite: 1]. |
| **`ACCEPTANCE.md` / Ledger** | **Checklist (`specs/<sprint>/checklist.md`)** | Tracked per-spec checklist initialized at oracle freeze (`open`), recording separate `Offline Run` and `Live Run` evidence columns, and stamped `done` mechanically by the Gate when all mapped proofs in `coverage.md`, `probe.sh`, and the repo `Test` suite pass on the identical `head` SHA (with dedicated `mutant/<name>.patch | waived` rows for accepted surviving mutants)[cite: 1]. |
| **Implementation brief / Runbook** | **Work order** | Not a newly authored prose file; a mechanical bundle of `spec-vN.md` + `contract.json` (+ `solution_key.patch` when `solution_key_exposure: full`, and optional `prior_attempt.json` on retry)[cite: 1] materialized in `handoff/<sprint>/work-order/`. |
| **Known-good reference** | **Solution key (`solution_key.patch`)** | Authored solely by the Architect in the Spec phase (updated only by the Architect if Phase 2 qualification exposes a flaw), audited by the Challenger, and copied into the Oracle directory at freeze where its canonical hash is locked[cite: 1]. Passed to the Implementer as a starting draft when `solution_key_exposure: full`, but never merged directly into the target repository without passing the Implementer/Gate/Archivist pipeline[cite: 1]. |
| **Wrong implementations / Traps** | **Mutants (`mutants/*.patch`)** | Deliberately sabotaged patches supplied by the Challenger that violate a spec clause and must be killed (`killed: true`, exit `1`) by the oracle's proofs[cite: 1]. |
| **Stop report / Session result** | **Implementation closure report (`closure-NN.json`)** | Written by the Implementer to `handoff/<sprint>/closures/` when halting itself (`reason: done | blocked`), carrying `proof_id`, `solution_key_divergence` (required when `blocked` and `solution_key_exposure: full`), `detail`, `notes[]` (for Archivist), and `backlog[]`[cite: 1]. |
| **Dispute report / Pruned packet** | **Escalation record (`escalation-NN.json`)** | Assembled mechanically by `amaster` on `retries_oracle_exhausted`, `retries_implementer_exhausted`, `retries_archivist_exhausted`, `hard_cap_exhausted`, or `blocked` (with `oracle_review` populated only when `trigger: retries_oracle_exhausted`, else `null`)[cite: 1]. Routed via `amaster → Architect` first, and `amaster → Owner` when the Architect escalates, fails, or is the rejecting Approver. |
| **Evidence report** | **Gate evidence record (`runs/ev-NN.json`)** | Untracked per-run execution receipts written by the Gate to `specs/<sprint>/runs/`, cited by SHA-256 hash in `checklist.md`[cite: 1]. |
| **Offline gate / Live gate** | **Offline run / Live run** | "Gate" (`agate`) is strictly the runner component; `Offline run` (credentials blanked) and `Live run` (real Owner credentials) are execution stages[cite: 1]. |
| **Approved snapshot** | *(Internal git tag)* | Retired as a named package; the Gate pins the approved tree via an internal git tag in `repos/target-repo/.git` keyed by contract hash before `amaster` invokes the Archivist[cite: 1]. |
| **Final history** | **Archivation plan** | A directory (`diff-risk-review.md`, `backlog-proposal.md`, `commit-plan.sh`, plus `plan/` patch/message pairs including graduated `test/` commits) routed via two distinct edges: `Archivist → Gate` (solid: regex, non-`test/` git tree-equality, and `Test` execution) and `Gate → Approver` (`owner` by default, or `architect`; dashed)[cite: 1]. |
| **`sessions.tsv` schema** | **Extended `sessions.tsv` schema** | Logs every CLI invocation (`model`, `turns`, `tokens`, `cost`, `accepted_items`) plus retry counters and `escalation_alerts_sent` events so `state.json` can be reconstructed alongside `runs/ev-*.json` and `escalation-NN.json`[cite: 1]. |

---

## 1. Graph Topology, Visual Semantics & Workspace Isolation

### 1.1 Single Source of Truth & Generated Views

* **Canonical Source (`graph.toml`):** One primary persona graph serves as the central representation, while Views `02` (Swimlane Sequence), `03` (Context and Session Views), and `04` (Guard Map) are retained as generated views derived from the same `graph.toml` definition[cite: 1]. The Guard Map functions as an annotation layer over the persona graph rather than an independent topology[cite: 1].
* **Primary Deliverable:** Raw `.mmd` Mermaid definitions are the canonical visual artifacts (rendered at full resolution via `mermaid-cli` or native Markdown viewers rather than auto-layout PNG thumbnails)[cite: 1].
* **Current Morphology:** The workflow operates as a deterministic spine (`amaster`) orchestrating bounded loops (adversarial oracle qualification, implementation retries, escalation resolution, and closeout archivation)[cite: 1].
* **Escalation edges in the graph:** `amaster → Architect` (never drawn through the Implementer) carries the `Escalation record` for `retries_oracle_exhausted`, `retries_implementer_exhausted`, `hard_cap_exhausted`, and `blocked`[cite: 1]. A secondary `amaster → Owner` control edge activates when the Architect escalates to the human Owner, fails/times out, on `retries_archivist_exhausted`, or when `escalation_policy()` targets the Owner directly.

### 1.2 Orthogonal Edge Semantics

Every edge in the graph is classified along two independent axes: **acceptance verification** (line style) and **routing role** (color or arrowhead)[cite: 1].

| Axis | Visual Encoding | Classification & Mechanics |
| --- | --- | --- |
| **Axis 1: Who Accepts the Hand-off** *(Verification)* | **Solid Line** | **Deterministic / Objective:** Accepted or enforced by a script or mechanical check that inspects the transfer and rejects violations (e.g., JSON schema validation on an LLM-written closure report, `git diff` scope checks, regex and git tree-equality checks on commit plans, deterministic session invocation)[cite: 1]. |
| **Axis 1: Who Accepts the Hand-off** *(Verification)* | **Dashed Line** | **Probabilistic / Subjective:** Accepted by an LLM or human exercising judgment (e.g., `Architect ↔ Challenger` spec/oracle hand-off, `Gate → Approver` archivation judgment)[cite: 1]. Left dashed intentionally because no regex can verify semantic quality[cite: 1]. |
| **Axis 2: What Travels** *(Routing Role)* | **Standard Arrowhead / Primary Color** | **Unmodified Artifact Flow (`Persona → Persona`):** Visually represents an artifact authored by one persona (`spec-vN.md`, `Oracle vN`) whose file pointer is handed unmodified to the next persona when scheduled by `amaster`[cite: 1]. |
| **Axis 2: What Travels** *(Routing Role)* | **Open Arrowhead / Distinct Control Color** | **Control & Synthesized Envelope Flow (`amaster → Persona`):** Scheduling signals and pointers to `amaster`-synthesized JSON envelopes (`contract.json`, `Work order`, `escalation-NN.json`)[cite: 1]. **Because `amaster` invokes sessions deterministically via script, control edges are drawn as solid lines** (distinguished by their open arrowhead and control color, never dashed)[cite: 1]. |

### 1.3 Module-by-Module Context & Piping Blueprint

At runtime, all artifacts reside on disk and `amaster` routes file pointers to each session[cite: 1]. Saying "`amaster` never interprets prose" means `amaster`'s routing logic branches strictly on deterministic schema fields (enums, booleans, hashes, exit codes, counters), never on free-text strings[cite: 1]. To prevent context rot from dead-end debugging turns while preserving end-to-end architectural intent, context lifecycles are strictly partitioned:

| Module | Context Strategy | Technical Piping & Execution Blueprint |
| --- | --- | --- |
| **`amaster` (Orchestrator)** | **Deterministic State File (`state.json`)** | Runs as an event-driven CLI/daemon[cite: 1]. Communicates with the human Owner via a **Notification Adapter** (interactive terminal prompt when attached; Telegram/webhook message when detached). Whenever a human decision is required, `amaster` writes `status: "hold"` to `state.json`, emits the notification (`escalation_alerts_sent++`), and exits cleanly[cite: 1]. The Owner resumes execution via CLI (`amaster resolve <sprint> ...`) or an authenticated webhook/bot reply that writes the decision artifact and re-invokes `amaster`. |
| **`Architect`** | **Persistent Thread (`architect_thread.jsonl` / `--resume`) + Compaction Fallback** | **Phase 1 (Interactive Q&A):** Owner converses directly with the Architect session to settle product intent and ambiguities before the Architect writes `spec-v1.md` and `solution_key.patch`[cite: 1].<br>**Phases 2–4 (Autonomous Arbitrator):** When `amaster` routes `qual.json` failures, `escalation-NN.json`, or `Archivation plan` reviews to the Architect, it resumes the **same persisted thread** so the Architect retains full conversational context of *why* specific trade-offs were agreed with the Owner[cite: 1]. If token volume approaches context limits, older turns compact into `architect-notes.md`[cite: 1]. |
| **`Challenger`** | **Stateless Just-in-Time (JIT) Payload** | Fresh CLI invocation per round[cite: 1]. Retaining failed turns causes the model to anchor on prior blind spots. `amaster` frontloads static cache-friendly prefixes (`[Challenger System Prompt] + [spec-vN.md] + [solution_key.patch]`) ahead of dynamic feedback (`[qual.json + prior Oracle vN]`)[cite: 1]. |
| **`Implementer`** | **Stateless Just-in-Time (JIT) Payload** | Fresh CLI invocation per attempt inside a clean `workspaces/wip-attempt-N/` git worktree checked out at `BASE`[cite: 1]. `amaster` frontloads static files (`[Implementer System Prompt] + [spec-vN.md] + [contract.json] + [solution_key.patch when full]`) ahead of dynamic retry feedback (`[prior_attempt.json]`) to maximize prompt-cache hits without dragging failed tool call noise[cite: 1]. |
| **`Archivist`** | **Stateless Just-in-Time (JIT) Payload** | Fresh CLI invocation at closeout[cite: 1]. Receives `[Archivist System Prompt] + [spec-vN.md] + [approved git diff] + [Oracle proofs/*.sh] + [closure notes[] & backlog[]]` (plus Gate/Approver rejection details if re-invoked)[cite: 1]. |

### 1.4 Every Place the Workflow Reaches the Owner

1. **Phase 1 Intent Q&A (§3.2, §4.1):** Interactive `Owner ↔ Architect` conversation to establish requirements and name the sprint (`YYYY-MM-DD_<slug>`) before `spec-v1.md` is authored[cite: 1].
2. **Escalation Resolution (§5.2, §5.4, §6.3):** When the Architect cannot resolve an escalation without changing product intent, when `mutant_waiver_authority: owner`, when `retries_archivist_exhausted` fires, or when `escalation_policy()` routes directly to the Owner[cite: 1].
3. **Live Run Execution & Gated Approvals (§4.3, §5.5):** When `approval_live_run: owner` or `approval_archivation_plan: owner` (the default) is active, and for executing the Live Run inside the Owner's credentialed environment[cite: 1].
4. **Closeout & Merge (§3.2, §5.5):** Reviewing `diff-risk-review.md` (including any waived mutant disclosures), selecting items from `backlog-proposal.md` for the repo backlog, and executing the final `git push`[cite: 1].

### 1.5 Multi-Sprint Directory Architecture & OS-Level Isolation

To enforce **`P` (Private Artifacts Unreadable)** mechanically[cite: 1] and scale cleanly across hundreds of sprints, the workspace is partitioned across two OS accounts (`agate` for the orchestrator/gate and `impl` for the untrusted Implementer) with external scratch git worktrees (`workspaces/`) and an explicit POSIX IPC mailbox (`handoff/`):

```text
/srv/agent-graph/
├── gate-repo/                                     # [owner: agate:agate, chmod 700] — UNREADABLE BY IMPLEMENTER
│   ├── .git/
│   ├── bin/
│   │   ├── amaster                                # Deterministic state-machine controller & router
│   │   └── agate                                  # Deterministic runner & guard verifier
│   ├── graph.toml                                 # Canonical topology & default budget policies
│   └── specs/                                     # Scalable archive of all historical and active sprints
│       └── 2026-10-09_public-profiles/            # Per-sprint self-contained directory
│           ├── spec-v1.md                         # Hashed specification
│           ├── architect_thread.jsonl             # Persistent Architect session transcript
│           ├── architect-notes.md                 # Architect context-compaction fallback
│           ├── contract.json                      # Minted once at Phase 3 freeze (immutable)
│           ├── checklist.md                       # Git-tracked acceptance checklist
│           ├── oracles/
│           │   └── v1/                            # Frozen Oracle directory (hashed into contract.json)
│           │       ├── proofs/                    # Black-box executable checks (01_public.sh, ...)
│           │       ├── probe.sh                   # End-to-end recomputation script
│           │       ├── mutants/                   # Sabotaged patches (contact_leak.patch, ...)
│           │       ├── scope.txt                  # ALLOW / FROZEN path glob rules
│           │       ├── coverage.md                # Requirement -> proof mapping
│           │       └── solution_key.patch         # Canonical reference patch copied at freeze
│           └── runs/                              # [untracked, .gitignored] Disposable runtime receipts
│               ├── state.json                     # Dynamic state counters, active stage, idempotent markers
│               ├── sessions.tsv                   # CLI invocation telemetry & alert ledger
│               ├── qual.json                      # Phase 2 Oracle qualification receipt
│               ├── ev-01.json, ev-02.json         # Gate evidence records (ev-NN)
│               └── escalation-01.json             # Synthesized escalation packets
│
├── handoff/                                       # [owner: agate:impl, chmod 750] — SHARED IPC MAILBOX
│   └── 2026-10-09_public-profiles/
│       ├── work-order/                            # Materialized by amaster (read-only to impl)
│       │   ├── spec-v1.md
│       │   ├── contract.json
│       │   ├── solution_key.patch                 # Omitted when solution_key_exposure: hidden
│       │   └── prior_attempt.json                 # Last diff + failing_line from ev-NN (on retry)
│       ├── closures/                              # Written by Implementer (closure-01.json)
│       └── archivation-plan/                      # Written by Archivist in Phase 4
│           ├── diff-risk-review.md                # Includes mandatory Waived Mutants section if any waived
│           ├── backlog-proposal.md
│           ├── commit-plan.sh
│           └── plan/                              # 01-feature.patch/.msg, 02-graduate-tests.patch/.msg
│
├── workspaces/                                    # Ephemeral scratchpad git worktrees (linked to target-repo)
│   ├── wip-attempt-1/                             # [owner: impl] Isolated Implementer worktree (deleted on retry)
│   └── gate-verify/                               # [owner: agate, chmod 700] Detached worktree for Gate runs
│
└── repos/
    └── target-repo/                               # Central local git repository
        └── .git/                                  # Stores contract-hash git tags pinned by agate

```

### 1.6 Resolution of Formerly Unguarded Edges

1. **Implementer → `amaster` (Session Closure & Pre-Check Guards):** Guarded mechanically (**solid line**) *before* any Offline Run executes.


* **Gate Pre-Flight Integrity Check:** `agate` first verifies that the frozen `oracles/vN/` directory inside `gate-repo/` matches the immutable hash in `contract.json`. A mismatch halts the runner immediately as a system integrity error (never consuming an Implementer retry).
* **Closure & Code Guards:** `amaster` validates that `closure-NN.json` conforms to schema (`reason: done | blocked`, `notes`, `backlog`, plus `min_attempts_before_block` and—when `solution_key_exposure: full`—`solution_key_divergence` for `reason: blocked`), while the Gate checks `git diff BASE..HEAD` against `ALLOW`/`FROZEN` scope (`scope.txt`), credential/secret leak scan, and forbidden-call lint. If any closure guard fails, the Gate emits a red `runs/ev-NN.json` citing the violated guard and `amaster` routes it identically to a failed Offline Run (consuming 1 `retries_implementer` attempt and passing the guard failure in `prior_attempt.json`).




2. **Archivation Plan Hand-off (Split into Two Explicit Edges):** Because the `Archivation plan` undergoes both mechanical policy verification and semantic review, it is modeled as two separate edges:


* **Edge 1 — `Archivist → Gate` (Solid Line / Script-Accepted):** `amaster` enforces the precondition that `diff-risk-review.md`, `backlog-proposal.md`, `commit-plan.sh`, and `plan/` exist and parse. The Gate runs the deterministic regex policy check on `commit-plan.sh` and `plan/*.msg` (subject format, required git trailers, no forbidden paths, matching `.patch`/`.msg` pairs, and a mandatory `Waived Mutants & Residual Risk` section in `diff-risk-review.md` if any mutant was waived), **ephemerally executes `commit-plan.sh` in `workspaces/gate-verify/` to verify bit-for-bit git tree-equality against the pinned contract-hash git tag on all non-`test/` paths (`git diff <contract-tag> HEAD -- . ':!test/'`), verifies the final test-graduation commit touches only `test/**`, and runs the repo's `Test` suite to confirm all existing and newly graduated tests pass**.


* **Edge 2 — `Gate → Approver` (Dashed Line / Human- or LLM-Accepted):** Once Edge 1 passes, the validated `Archivation plan` is handed off to the Approver (`approval_archivation_plan: owner | architect`, default **`owner`**) for semantic review of `diff-risk-review.md`, `commit-plan.sh`, and `backlog-proposal.md`. Automated rejections by the Gate (Edge 1) or by the `Architect` (when `approval_archivation_plan: architect` on Edge 2) re-invoke the Archivist bounded by `retries_archivist` (escalating to the `Owner` on `retries_archivist_exhausted`). Human `Owner` revision requests bypass budget limits entirely.





---

## 2. Core Vocabulary & Verification Concepts

| Term | Definition |
| --- | --- |
| **Proof** | A single executable script (`proofs/*.sh`) verifying a specific spec requirement. Exits `0` (pass) or `1` (fail). Graduated into the target repository's `test/` directory by the Archivist during Phase 4 closeout.

 |
| **Oracle** | **An artifact, not an actor.** A frozen, hashed directory (`oracles/vN/`) inside `gate-repo/` containing `proofs/`, `probe.sh`, `scope.txt`, `solution_key.patch`, `mutants/`, and `coverage.md`. The Gate executes it against the target codebase.

 |
| **Test** | The target repository's own tracked regression test suite (`test/`), including graduated proofs from prior specs. Executed automatically by the Gate during every Offline Run (after `proofs/` and `probe.sh` pass) and during Phase 4 tree verification.

 |
| **Guard** | A mechanical process check (file scope enforcement, credential leak scan, forbidden-call lint, commit message regex, git tree-equality). Proofs judge code; guards judge process.

 |
| **Gate (`agate`)** | The deterministic runner ("club door bouncer") that verifies oracle integrity, executes guards, proofs, and repo tests, writes `Gate evidence records`, and mechanically stamps `checklist.md`. Exercises zero judgment and writes no prose.

 |
| **Offline Run** | Full execution of the oracle (`proofs/` + `probe.sh` first, followed by the target repo's `Test` suite) by the Gate in `workspaces/gate-verify/` after closure guards pass, with real credentials blanked.

 |
| **Live Run** | Execution of the oracle against live external services using real credentials stored strictly in the Owner's environment/secret store.

 |
| **Solution Key (`solution_key.patch`)** | A reference implementation patch authored solely by the Architect in Phase 1 (updated only by the Architect if Phase 2 qualification exposes a flaw), audited by the Challenger, and copied into the Oracle directory at freeze where its canonical hash is locked. Proves satisfiability (Base = red, `solution_key.patch` = green) and serves as the Implementer's initial draft when `solution_key_exposure: full`. Never merged directly into the target repository without passing the Implementer, Gate, and Archivist pipeline.

 |
| **Mutants** | *(Standard Mutation Testing convention; replaces "traps")* Deliberately sabotaged patches (`mutants/*.patch`) written by the Challenger that violate a specific spec requirement to test whether the oracle catches them. Recorded in `qual.json` via boolean `killed: true` (at least one proof exited `1`) or `killed: false` (surviving mutant: all proofs stayed green, exposing a blind spot).

 |
| **Recomputation** | The oracle's end-to-end probe (`probe.sh`, Premise 5), which independently calculates claimed metrics from raw data (e.g., SQL counts, `git show --numstat`) and compares them against the implementation's output.

 |

---

## 3. Personas, Authority & Independence Rules

### 3.1 Premise 7 Clarification

* **Premise 7 Formulation:** *"A persona may keep its own context across its own turns; what passes between personas is artifacts only."*

* Because Premise 7 restricts the communication channel *between* distinct personas rather than prohibiting a single persona from maintaining state across its own turns, the Architect's persistent thread (`architect_thread.jsonl`) across a spec's lifecycle is natively compliant. Leaf personas (`Challenger`, `Implementer`, `Archivist`) run fresh per session with static artifacts frontloaded by `amaster` for prompt-cache efficiency.



### 3.2 Persona Roster & Responsibilities

| Persona | Type | Context Lifecycle | Core Responsibilities |
| --- | --- | --- | --- |
| **Owner** | Human | Continuous | Supplies initial intent, holds live credentials, resolves human-level escalations, approves archivation plans (default `approval_archivation_plan: owner`) and live runs (when configured as `owner`), waives surviving mutants when `mutant_waiver_authority: owner`, decides which `backlog-proposal.md` items enter the repo backlog, and executes the final `git push` / merge.

 |
| **Architect** | LLM (Frontier Model A) | **Persistent per Spec (`architect_thread.jsonl`)** | Acts as CTO/authority directly below Owner. Conducts initial Q&A with Owner, authors `Spec vN` and `solution_key.patch`, resolves discrepancies during the Phase 2 Oracle qualification loop or escalations (`retries_oracle_exhausted`, `retries_implementer_exhausted`, `hard_cap_exhausted`, `blocked`), waives benign surviving mutants when `mutant_waiver_authority: architect` (default), approves the `Archivation plan` when `approval_archivation_plan: architect`, and curates the repo backlog (`architect-notes.md` serves as context-compaction fallback).

 |
| **`amaster`** | Python Script | Stateless / Event-driven (persists `specs/<sprint>/runs/state.json`) | Deterministic state-machine controller and router ("flight controller"). Launches headless sessions in external `workspaces/` via idempotent write-ahead transitions, frontloads static file prefixes for cache hits, materializes `handoff/` bundles, tracks counters in `state.json`, mechanically mints the immutable `contract.json` at Oracle freeze, assembles `Escalation records`, and dispatches Owner notifications via the Notification Adapter.

 |
| **Challenger** | LLM Leaf (Frontier Model B, Adversarial) | Fresh per session (JIT payload) | *(Configurable via `oracle_author: challenger |
| **Implementer** | LLM Leaf (Fast Workforce Model) | Fresh per attempt (JIT payload) | Isolated worker running as OS user `impl` inside `workspaces/wip-attempt-N/`. Reads `handoff/<sprint>/work-order/` (including `solution_key.patch` when `solution_key_exposure: full`) and edits code within `ALLOW` scope until the Gate exits `0`. Mechanically blocked by OS permissions (`chmod 700` on `gate-repo/`) from reading Oracle `proofs/`, `probe.sh`, or `mutants/`, and only sees failing lines from Gate runs. Emits `closure-NN.json` (`done` or `blocked`).

 |
| **Gate (`agate`)** | Script | Stateless (persisted outputs: `qual.json`, `runs/ev-*.json`, `checklist.md` stamps, and contract-hash git tag) | Verifies untouched oracle hash against `contract.json`, runs Oracle qualification (`qual.json`), self-tested closure guards (scope, secret scan, forbidden-call lint), offline runs (`proofs/` + `probe.sh` then repo `Test`), live runs, and closeout regex, non-`test/` tree-equality, and graduated `Test` checks. Stamps `checklist.md` and pins the approved git tag.

 |
| **Archivist** | LLM Leaf | Fresh per session (JIT payload) | Invoked once all required gates (including Live run, if required) are green. Reads `Spec vN`, the approved diff, `oracles/vN/proofs/*.sh`, any waived mutant records, and the Implementer's `notes`. Produces the `Archivation plan` (`diff-risk-review.md`, `backlog-proposal.md`, `commit-plan.sh`, `plan/` including graduated native tests in `test/`). Cannot alter production code (enforced by Gate non-`test/` tree-equality check on Edge 1).

 |

### 3.3 Independence Matrix (Settled)

Every persona invocation runs in its own isolated session (`S`), so session separation is a universal baseline and omitted from the cells below. Rows are the persona being constrained; columns are the persona it is compared against.

| Persona (row) | Architect | Challenger | Implementer |
| --- | --- | --- | --- |
| **Challenger** | **F**<br> |  |  |
| **Implementer** | **P*** *(only when `solution_key_exposure: hidden`)*<br> | **P**<br> |  |
| **Archivist** |  |  | **F**<br> |

* **F (Cross-Family Preferred):** Prefer a different frontier model family (Challenger auditing the Architect's `Spec vN` and `solution_key.patch` to author the `Oracle`; Archivist reviewing the Implementer's diff and graduating tests).


* **P (Private Artifacts Unreadable):** Enforced mechanically at the OS filesystem level (`gate-repo/` owned by `agate:agate` with `chmod 700`). The Implementer (`impl` user) is **always** blocked from reading the Challenger's test logic (`proofs/*.sh`, `probe.sh`, `mutants/*.patch`). When `solution_key_exposure: full` (default), `amaster` copies `solution_key.patch` into `handoff/<sprint>/work-order/`; when `hidden`, `amaster` omits it so `solution_key.patch` remains unreadable inside `gate-repo/`.



---

## 4. Standardized Artifact & Package Schemas

**Naming & Lifecycle Rules:**

* **Records** are structured data files emitted by an agent or the Gate.


* **Plans / Scripts** are actionable bundles reviewed and executed during closeout.


* **Single Ownership of `solution_key.patch`:** Authored solely by the Architect in Phase 1 (and updated only by the Architect if Phase 2 qualification exposes a bug or spec refinement), audited by the Challenger, and copied into `oracles/vN/` when frozen so its canonical hash is locked at Oracle freeze.


* **State vs. Contract Separation:** `specs/<sprint>/runs/state.json` is initialized at Phase 1 start to track dynamic counters across all phases (scoped to `run_id`), whereas `specs/<sprint>/contract.json` is minted **strictly once** at Oracle freeze (entering Phase 3) and remains immutable throughout the implementation run.


* **Evidence numbering:** `ev-NN` is a monotonic counter per spec in `specs/<sprint>/runs/`, never reset between runs or contract versions.



### 4.1 Phase 1: Spec Phase

| Package | From → To | Concrete Form | Example (`2026-10-09_public-profiles`) |
| --- | --- | --- | --- |
| **Intent & Q&A** | Owner ↔ Architect | Interactive conversation persisted in `architect_thread.jsonl` | `"Add public profiles to users"` → Q&A settles `is_public` boolean and sprint slug `2026-10-09_public-profiles`.

 |
| **Spec vN** | Architect → Challenger | `spec-v1.md` (fixed headings: *Requirements*, *Locked*, *Deferred*), SHA-256 hashed

 | **R1:** Guests see name, bio, avatar, photo count of public profiles. **R2:** Never expose email. **R3:** Private profiles return 404. **Locked:** `users` schema unchanged. **Deferred:** Search engine indexing.

 |
| **Solution key** | Architect → Challenger (audit), Implementer (when `full`) | `solution_key.patch` (authored in Spec phase; locked into `oracles/vN/` at freeze)

 | Working reference patch adding `is_public`, route, and serializer to prove the spec is satisfiable.

 |

### 4.2 Phase 2: Oracle Phase

| Package | From → To | Concrete Form | Example (`2026-10-09_public-profiles`) |
| --- | --- | --- | --- |
| **Oracle vN** | Challenger ↔ Architect (via Gate `qual.json`) | Directory `oracles/v1/`: `proofs/`, `probe.sh`, `scope.txt`, `mutants/`, `solution_key.patch`, `coverage.md`<br> | `proofs/02_no_email.sh`, `mutants/contact_leak.patch`<br> |
| **Coverage map** | Challenger → Oracle | `coverage.md` (frozen and hashed inside Oracle; lists every proof + `probe.sh` a `done` stamp depends on)

 | `R1 → proofs 01, 04, probe.sh`; `R2 → proofs 02, 05, probe.sh`; `R3 → proof 03`<br> |
| **Oracle qualification record** | Gate → `amaster`, Challenger, Architect | `runs/qual.json` (command, exit code, boolean `killed` per mutant, and hashes for every qualification check)

 | `{"null_base": "red (5/5)", "solution_key_green": "3/3", "mutants": [{"name": "contact_leak.patch", "killed": true}], "killed_count": "4/4", "manifest_sha256": "8a1b..."}`<br> |
| **Checklist** | Initialized at freeze (`open`); stamped `done` or `waived` by Gate | `specs/<sprint>/checklist.md` (tracked in `gate-repo`; separate `Offline Run` and `Live Run` columns; cites green `ev-*` runs on identical `head` SHA)

 | `R2 | proofs 02, 05, probe.sh + Test | Offline: ev-09 (sha256: 4b1a...) | Live: ev-12 (sha256: 9c4d...) | done` *(accepted surviving mutants append dedicated `mutant/contact_leak.patch | waived | escalation-01 (sha256: ...)` rows)*<br> |

### 4.3 Phase 3: Implementation Phase

| Package | From → To | Concrete Form | Example (`2026-10-09_public-profiles`) |
| --- | --- | --- | --- |
| **Implementation contract** | `amaster` (minted once at Oracle freeze, immutable) → Gate, Implementer, Archivist | `specs/<sprint>/contract.json`<br> | Hashes of `spec-v1.md`, `oracles/v1`, and `qual.json`; `scope.txt` ref; initial resolved budgets (`min_attempts_before_block`, `retries_implementer`, `retries_archivist`, `hard_cap`, etc.); `solution_key_exposure: full`; `mutant_waiver_authority: architect`; `live_run: required`; `approval_live_run: auto`; `approval_archivation_plan: owner`<br> |
| **Work order** | `amaster` → Implementer | Materialized in `handoff/<sprint>/work-order/`: `spec-v1.md` + `contract.json` (+ `solution_key.patch` when `full`, + optional `prior_attempt.json` on retry)

 | Contains zero prose written by `amaster`. Defines `"done = all Gate guards, oracle proofs, probe.sh, and repo Test suite exit 0"`.

 |
| **Implementation closure report** | Implementer → `amaster` | `handoff/<sprint>/closures/closure-NN.json` (`reason: done | blocked`, `proof_id`, `solution_key_divergence`, `detail`, `notes[]`, `backlog[]`)

 |
| **Gate evidence record** | Gate → `specs/<sprint>/runs/` (untracked) | `runs/ev-07.json` (emitted on every guard rejection, partial run, or full Gate run)

 | `{"id": "ev-07", "stage": "offline", "command": "bash proofs/02_no_email.sh", "exit_code": 1, "output_sha256": "9f2c...", "oracle": "v1", "head": "a41c9e0", "failing_line": "FAIL: body contains seeded email"}`<br> |
| **Escalation record** | `amaster → Architect` (and `amaster → Owner` on hand-off) | `runs/escalation-NN.json`, assembled mechanically by `amaster`. `trigger` is one of `retries_oracle_exhausted`, `retries_implementer_exhausted`, `retries_archivist_exhausted`, `hard_cap_exhausted`, `blocked`. `oracle_review` is `null` unless `trigger: retries_oracle_exhausted`.

 | See examples below.

 |

**Implementer retry-exhaustion example** (`trigger: retries_implementer_exhausted`; attempts ended with `reason: done` closures and stayed red):

```json
{"spec": "spec-v1", "trigger": "retries_implementer_exhausted", "attempts": 2, "last_closure": "closure-02.json", "evidence": ["ev-07", "ev-08"], "diff_stat": "api/profile.py | 31 +++", "log_tail": "<last 40 lines>", "oracle_review": null}

```

**Hard-cap exhaustion example** (`trigger: hard_cap_exhausted`; session killed by wall-clock/turn/token/cost supervisor before writing a closure):

```json
{"spec": "spec-v1", "trigger": "hard_cap_exhausted", "attempts": 1, "last_closure": null, "evidence": [], "diff_stat": "api/profile.py | 9 +", "log_tail": "<last 40 lines>", "oracle_review": null}

```

**Blocked example** (`trigger: blocked`; accepted by `amaster` only after `attempts >= min_attempts_before_block`, green Closure Guards, green repo `Test` unless cited in `detail`, and populated `solution_key_divergence` when `solution_key_exposure: full`):

```json
{"spec": "spec-v1", "trigger": "blocked", "attempts": 2, "last_closure": "closure-02.json", "evidence": ["ev-07", "ev-08"], "diff_stat": "api/profile.py | 18 ++", "log_tail": "<last 40 lines>", "oracle_review": null}

```

**Oracle-retries-exhausted example** (`trigger: retries_oracle_exhausted`; `oracle_review` populated mechanically from `qual.json` where `killed: false`):

```json
{"spec": "spec-v1", "trigger": "retries_oracle_exhausted", "attempts": null, "last_closure": null, "evidence": [], "diff_stat": null, "log_tail": null, "oracle_review": {"rounds_used": 3, "latest": "v3", "latest_sha256": "5d2f...", "qual": "qual.json", "surviving_mutants": ["mutants/contact_leak.patch"]}}

```

### 4.4 Phase 4: Closeout Phase

| Package | From → To | Concrete Form | Example (`2026-10-09_public-profiles`) |
| --- | --- | --- | --- |
| **Archivation plan** | Edge 1: Archivist → Gate (solid: regex + non-`test/` tree-equality + `Test` run)<br>

<br>

<br>Edge 2: Gate → Approver (`owner` by default, or `architect`, dashed)

 | Written to `handoff/<sprint>/archivation-plan/`:<br>

<br>

<br>1. `diff-risk-review.md`<br>

<br>2. `backlog-proposal.md`<br>

<br>3. `commit-plan.sh`<br>

<br>4. `plan/` with `NN-<slug>.patch` / `NN-<slug>.msg` pairs (ending with `NN-graduate-tests.patch`/`.msg`)

 | **1.** Semantic risk notes on serializer reuse + mandatory `Waived Mutants & Residual Risk` section if any mutant was waived.<br>

<br>**2.** Merged follow-ups tagged `source: implementer` or `source: archivist` (or `none`).

<br>

<br>**3.** Applies feature patches (`01-public-profile-serializer.patch`) and graduated test patch (`02-graduate-tests.patch` in `test/`), with `Spec:` and `Oracle:` trailers in each `.msg`.

 |

---

## 5. Lifecycle Mechanics & Loop Governance

### 5.1 State Persistence, Immutable Contract & Idempotent Transitions (`amaster`)

* **External State File (`specs/<sprint>/runs/state.json`) vs. Immutable `contract.json`:** `amaster` initializes `state.json` at the start of Phase 1 (scoped to `run_id` across any `Spec vN` revisions) to track runtime counters (`retries_oracle`, `retries_implementer`, `retries_archivist`, active stage, `status`, and any dynamic retry increments granted during escalations). `contract.json` is minted **once** at Oracle freeze (entering Phase 3) and is never mutated during the implementation run; if additional retries are granted on escalation, `state.json` is updated while `contract.json` remains static. If `state.json` is lost or corrupted, all counters and grants can be deterministically reconstructed from `runs/ev-*.json`, `escalation-NN.json`, and the extended `sessions.tsv` ledger (`model`, `turns`, `tokens`, `cost`, `accepted_items`, retry counters, `escalation_alerts_sent`).


* **Idempotent Write-Ahead Transitions:** Every state transition is idempotent, keyed by `(run_id, transition_id, attempt)` (and including `contract_hash` from Phase 3 onward), and writes a `"started"` marker to `state.json` *before* launching a process or sending an alert.


* If `amaster` crashes after launching an agent session, a restarted `amaster` detects the `"started"` marker and does not launch a duplicate session or double-spend the budget.


* Similarly, during an Owner `hold` wait, idempotency prevents sending duplicate escalation alerts.





### 5.2 Adversarial Oracle Qualification Loop (`Architect ↔ Gate ↔ Challenger`)

1. **Adversarial Authoring & Mechanical Qualification:**
* **Architect Spec & Reference Key:** In Phase 1, following interactive Q&A with the Owner, the Architect authors `spec-v1.md` and `solution_key.patch`.


* **Challenger Audit & Oracle Authoring:** In Phase 2, the cross-family Challenger audits `spec-v1.md` and `solution_key.patch` for semantic flaws (missing requirement coverage, shared misreadings, weak assertions such as checking `has("email")|not` when an email leaks under a renamed key `contact`) and authors `oracles/v1/` (`proofs/`, `probe.sh`, `mutants/`, `scope.txt`, `coverage.md`). (If configured with `oracle_author: prover`, a dedicated Prover writes `oracles/v1/` before the Challenger writes `oracles/v2/`).


* **Mechanical Qualification (`qual.json`):** The Gate runs `oracles/v1/` in `workspaces/gate-verify/`, verifying that the null base implementation fails (`red`), `solution_key.patch` passes repeatedly (`green`), and all `mutants/*.patch` are killed (`killed: true`, exit `1`).




2. **Four-Layer Defense Against Weak Proofs:**
* *Value-level sentinel proofs:* Seed known sentinel strings (e.g., a test email) and fail if the literal string appears anywhere in the raw response payload.


* *End-to-end probe (`probe.sh`):* Inspects actual runtime outputs and performs independent recomputation.


* *Adversarial mutants:* Challenger supplies sabotaged patches (`mutants/contact_leak.patch`) that expose weak assertions and remain archived in `oracles/vN/mutants/` for future verification.


* *Visible residual risk & Owner disclosure:* Any surviving mutant (`killed: false`) waived at escalation is stamped as a dedicated `mutant/<name>.patch | waived | escalation-NN` row in `checklist.md` and must be explained in `diff-risk-review.md` for Owner review at closeout.




3. **Deterministic Convergence & `retries_oracle_exhausted` Resolution:**
* **Immediate Freeze on Green `qual.json`:** If `qual.json` passes completely (`null_base: red`, `solution_key_green: 3/3`, all mutants `killed: true`), `amaster` freezes the Oracle immediately (locking the canonical hash of `solution_key.patch`) and mints `contract.json`.


* **Refinement Iterations (`v2`, `v3`):** If `qual.json` is red (e.g., a Challenger proof exposed a flaw in `solution_key.patch`, an over-strict proof rejected a valid `solution_key.patch`, or a mutant survived with `killed: false`), `amaster` wakes the Architect/Challenger to resolve the discrepancy (updating `spec-vN.md`/`solution_key.patch` or producing `oracles/vN/` directly), bounded by `retries_oracle`.


* **When `retries_oracle` Runs Out (`trigger: retries_oracle_exhausted`):** `amaster` assembles `escalation-NN.json` (with `oracle_review` populated from `qual.json`) and routes it via `amaster → Architect` (or `amaster → Owner` if `mutant_waiver_authority: owner`). The authority chooses one of three actions:


1. Grant additional `retries_oracle` budget in `state.json`.


2. Write the next oracle version (`oracles/vN/`) directly (re-verified by `qual.json`).


3. Waive the surviving mutant(s) (governed by `mutant_waiver_authority: architect | owner`, default `architect`): the latest oracle freezes and proceeds to Phase 3, appending `mutant/<name>.patch | waived | escalation-NN (sha256: ...)` rows in `checklist.md`.







### 5.3 Coverage Map & Checklist Stamping Rule

* `coverage.md` explicitly lists every proof ID (plus `probe.sh`) required to satisfy each requirement (`R_i → [proof_a, proof_b, ..., probe.sh]`).


* `specs/<sprint>/checklist.md` tracks `Offline Run` and `Live Run` receipts in separate columns:


* When `live_run: none`, the `Live Run` column is initialized to `n/a`, and the Gate stamps each `R_i` row `Status: done` once all mapped `proofs/`, `probe.sh`, and the target repo's `Test` suite exit `0` (`green`) in the `Offline Run` against the **exact same `head` commit SHA** (pinned by the contract-hash git tag).


* When `live_run: required`, `Status` remains `open` after the `Offline Run` column is populated and only flips to `done` when the `Live Run` column also records `0` (`green`) receipts for all mapped `proofs/` and `probe.sh` on the **identical `head` commit SHA**.


* Surviving mutants waived in Phase 2 occupy their own `mutant/<name>.patch | waived | escalation-NN` rows and **never** mark a requirement row (`R_i`) as `done` or `waived`.
* Closeout requires **zero `open` requirement rows** in `checklist.md` (every `R_i` row must be `done`, and any waived mutant rows must be disclosed in `diff-risk-review.md`).





### 5.4 Implementation Routing, Retries & Blocked Escalations (Settled)

1. **Retry / Restart Mechanics:** When a Gate closure guard or Offline run is red and `retries_implementer` budget remains, `amaster` deletes the dirty `workspaces/wip-attempt-N/` directory, creates a fresh `git worktree` at `BASE`, and launches a fresh Implementer session (frontloading static prefixes + `solution_key.patch` when `full`). It writes `prior_attempt.json` (previous diff patch, failing line from the last `ev-NN.json`, and attempt count) to `handoff/<sprint>/work-order/` strictly as an optional hint. `log_tail` from Escalation records goes to the Architect only and is never forwarded to a later Implementer.


2. **Deterministic Routing on Closure `reason`:**
* `reason: done` → Triggers Gate **Step 1 Pre-Flight & Closure Guards** followed immediately by the **Step 2 Fail-Fast Offline Run**.


* `reason: blocked` *(Consolidates former `blocked` and `dispute`)* → Implementer halts when it cannot satisfy the Gate due to an `ALLOW` scope restriction, missing architectural decision, or suspected over-constrained proof.


* **Anti-Early-Give-Up Guards:** `amaster` and the Gate mechanically reject `reason: blocked` (treating an invalid `blocked` claim as a failed attempt that consumes 1 `retries_implementer` credit) unless:


1. `attempts >= min_attempts_before_block`,


2. all Step 1 mechanical `ALLOW`/secret/lint closure guards pass and the target repository's own compilation and `Test` suite pass in the offline sandbox (unless a failing test in `Test` is the exact blocker cited in `detail`), and


3. **when `solution_key_exposure: full**`, `closure-NN.json` includes a non-empty `solution_key_divergence` explaining why `solution_key.patch` could not be applied or adapted to pass the failing proof.




* **Escalation Routing:** Once those preconditions are met, `amaster` assembles `escalation-NN.json` (`trigger: blocked`, citing `last_closure` and `evidence`) and routes it via `amaster → Architect`. The Architect inspects `escalation-NN.json` in its persistent thread and either (a) updates `scope.txt` / `Spec vN` / `Oracle vN` (starting a new contract run), (b) rejects the block and grants additional `retries_implementer` budget in `state.json`, or (c) escalates to the human `Owner` via `amaster → Owner` (`status: "hold"`) if product intent must change.


* *Intra-Session Hard-Cap Termination (`trigger: hard_cap_exhausted`):* If a session is killed by the wall-clock supervisor (`timeout -k 15s`) or turn/token/cost hard caps, `amaster` synthesizes `escalation-NN.json` (`trigger: hard_cap_exhausted`) from `state.json` and routes it via `amaster → Architect`.





### 5.5 Closure Guards, Fail-Fast Offline Run, Live Run & Archivation Sequence (Settled)

1. **Step 1 — Gate Pre-Flight & Self-Tested Mechanical Closure Guards (Before Offline Run):**
* **Oracle Pre-Flight Hash Check:** Gate verifies `gate-repo/specs/<sprint>/oracles/vN/` against `contract.json` (halting on corruption without consuming an Implementer retry).
* **Closure Guards:** Upon `Implementer → amaster` closure, and *before* executing untrusted Implementer code, `amaster` validates `closure-NN.json` and the Gate checks `git diff BASE..HEAD` against `ALLOW`/`FROZEN` scope (`scope.txt`), runs the credential/secret leak scan, and runs the forbidden-call lint.


* **Mandatory Self-Tests:** Every guard/scanner must pass its own built-in self-test (verifying it catches known synthetic leaks and forbidden calls) before evaluating the worktree so a broken lint cannot silently pass under `approval_live_run: auto`.




2. **Step 2 — Fail-Fast Offline Run (`proofs/` First, Repo `Test` Second):**
Once Step 1 guards are green, the Gate checks out the candidate commit in `workspaces/gate-verify/` with credentials blanked:


* **Stage 2a (Fast Feature Check):** Executes the Oracle's `proofs/*.sh` and `probe.sh` first so feature errors fail fast within seconds.


* **Stage 2b (Regression Armor):** Immediately executes the target repository's existing `Test` suite (`test/`) to guarantee zero regressions against prior specs.
* When both Stage 2a and Stage 2b exit `0`, the Gate stamps the `Offline Run` column in `checklist.md`.




3. **Step 3 — Live Run (Before Archivist):** Governed by `live_run: none | required` and `approval_live_run: auto | architect | owner`. **`approval_live_run: auto` means the Owner pre-authorized the live run in `contract.json`, and the live run still executes strictly within the Owner's environment/account (where real credentials reside), never under the `impl` user**; the Gate script itself never holds or stores real keys. When green, the Gate stamps the `Live Run` column and marks requirement rows `Status: done` in `checklist.md`.


4. **Step 4 — Archivist Curation & Proof-to-Test Graduation:**
* Once Step 1–3 are green and zero `open` rows remain in `checklist.md`, the Gate pins the approved state via an internal git tag in `repos/target-repo/.git` **keyed by contract hash**, and `amaster` invokes the Archivist.


* The Archivist consumes `spec-vN.md`, the approved diff, the Implementer's `notes`, and any waived mutant records to author `diff-risk-review.md` (including a mandatory `Waived Mutants & Residual Risk` section if any mutant was waived) and craft commit messages in `plan/*.msg`.


* The Archivist merges the Implementer's `backlog` items with its own candidates into `backlog-proposal.md` (containing `none` if empty).


* **Proof-to-Test Graduation:** The Archivist translates the black-box `oracles/vN/proofs/*.sh` into native repository tests inside `test/` as a dedicated final commit (`plan/NN-graduate-tests.patch` + `.msg`, restricted to `ALLOW: test/**`) in `commit-plan.sh`.


5. **Step 5 — Closeout Policy, Non-`test/` Tree-Equality & Graduated `Test` Check, Approval & Owner Push:**
* **Solid Edge (`Archivist → Gate`):** `amaster` verifies all required files exist in `handoff/<sprint>/archivation-plan/`, and the Gate runs the regex policy check on `commit-plan.sh`, `plan/*.msg`, and `diff-risk-review.md`, **ephemerally executes `commit-plan.sh` in `workspaces/gate-verify/`, verifies bit-for-bit git tree-equality between the resulting commit and the contract-hash git tag on all non-`test/` paths (`git diff <contract-tag> HEAD -- . ':!test/'` is empty), verifies the test-graduation patch only modifies `test/**`, and runs the repo's `Test` suite to prove the graduated tests pass**.


* **Dashed Edge (`Gate → Approver`):** Governed by `approval_archivation_plan: owner | architect` (default **`owner`**; `auto` is prohibited). If the Gate (Edge 1) or an LLM `Architect` Approver (Edge 2) rejects the plan, `amaster` loops back to the Archivist with the rejection reason bounded by `retries_archivist` (escalating to the `Owner` on `retries_archivist_exhausted`). Human `Owner` revision requests are uncapped.


* **Final Commit, Backlog Storage & Push:** Once approved, the verified commit chain (feature commits + graduated `test/` commit) is applied to the target repo, the final stamped `specs/<sprint>/checklist.md` is committed to `gate-repo` (`runs/ev-*.json` remain untracked), `backlog-proposal.md` items are presented for the **Owner** to curate into the repo backlog, and the human **Owner pushes** to remote trunk.





---

## 6. Dynamic Budget & Escalation Functions

### 6.1 Intra-Session Hard Caps (`hard_cap`) vs. Inter-Session Loop Counters (`retries_*`)

Resource and iteration ceilings are partitioned into two distinct classes resolved at Phase 1 start into `state.json` and locked into `contract.json` at Phase 3 Oracle freeze:

```text
effective_limit(dimension, contract_or_state, context) -> (limit, mechanism, on_exceed)

```

1. **Intra-Session Hard Caps (`hard_cap` → triggers `hard_cap_exhausted`):**
* Govern a **single CLI invocation**: `wall_clock` (`timeout -k 15s <limit>`), `turns`, `tool_calls`, `tokens`, and `cost_usd`.


* **Fail-Closed Adapter Guard:** If a contract specifies a hard cap dimension and the CLI adapter cannot confirm that the enforcement mechanism or CLI flag took effect, **the run refuses to start**.


* **Universal Wall-Clock Supervisor:** Every CLI engine retains the external `coreutils timeout -k 15s <limit>` wrapper as the hard wall-clock kill switch.




2. **Inter-Session Loop Counters (`retries_<stage>` → triggers `retries_<stage>_exhausted`):**
* Govern multi-session state machine loops tracked in `state.json`:
* `retries_oracle` → `retries_oracle_exhausted` (Phase 2 `Architect ↔ Gate ↔ Challenger` qualification loop).


* `retries_implementer` → `retries_implementer_exhausted` (Phase 3 `Implementer ↔ Gate` implementation loop, paired with `min_attempts_before_block`).


* `retries_archivist` → `retries_archivist_exhausted` (Phase 4 automated Gate/Architect rejections of the Archivation plan; human Owner revisions are uncapped).





### 6.2 CLI Engine Hard-Cap Capabilities (Status as of October 2026)

| CLI Engine | Headless / Hard-Cap Flag Support | Operational & Adapter Rules |
| --- | --- | --- |
| **Anthropic Claude Code (`claude`)** | Supports `--max-turns <N>` and `--max-budget-usd <amount>`.

 | **Force print mode (`-p`) in the adapter**, because outside print mode these flags may be silently ignored. Use `--resume <session_id>` for the persistent `Architect` thread; retain external `timeout -k` supervisor.

 |
| **OpenAI Codex CLI (`codex`)** | Turn and step caps for `codex exec` were requested in Feb and Jul 2026 (defaulting to unlimited); token budget landed in alpha in Aug 2026.

 | Do not rely on unverified turn caps; enforce via external `timeout -k` supervisor, API spend gateway, and post-run telemetry gating (`sessions.tsv`).

 |
| **Google Antigravity CLI (`agy`)** | Headless flags include `--print-timeout`; no turn or spend cap found in reviewed cheat sheets.

 | `--print-timeout` returns partial output rather than killing the run, so **it cannot serve as a hard cap**. Rely on external `timeout -k` supervisor.

 |
| **Cursor Agent CLI (`agent`)** | Reviewed headless docs list no turn or spend flag.

 | Treat native turn/spend caps as unconfirmed (fail-closed if requested as native hard caps); rely on external `timeout -k` supervisor and post-run telemetry.

 |

### 6.3 Dynamic Escalation Policy Function

Escalation routing resolves dynamically across all four phases (reading `state.json` in Phases 1–2 and `contract.json` in Phases 3–4):

```text
escalation_policy(event, contract_or_state, context) -> decision (logged with inputs)

```

* **Inputs:** Event type (`retries_oracle_exhausted`, `retries_implementer_exhausted`, `retries_archivist_exhausted`, `hard_cap_exhausted`, `blocked`), risk tier, `mutant_waiver_authority`, time of day, and Owner availability.


* **Two-Tier Routing (`amaster → Architect` then `amaster → Owner`):** By default, `amaster` routes `retries_oracle_exhausted`, `retries_implementer_exhausted`, `hard_cap_exhausted`, and `blocked` to the **Architect** first. `amaster` routes directly to the human **Owner** (via the Notification Adapter) when:


1. The Architect explicitly escalates an unresolved spec/scope/mutant decision to the Owner,
2. The synchronous Architect session itself fails or hits `hard_cap_exhausted`,


3. `retries_archivist_exhausted` triggers in Phase 4, or
4. `escalation_policy()` requires direct Owner authority (e.g., `mutant_waiver_authority: owner` or high risk tier).




* **Safe Default on No Response (`hold`):** Availability windows, time-of-day routing, and `escalation_alerts_sent` apply strictly when targeting the human **Owner**. If an Owner escalation receives no response within the availability window (or if a synchronous Architect invocation fails), the mandatory safe default is **`hold` (write `status: "hold"` in `state.json` and await human Owner intervention)—never auto-approve**.


* **Hold scope:** `hold` applies strictly to the actionable party's decision; an unanswered informational Owner notification never blocks a run that the Architect is authorized to resolve.



---

## 7. Parked Items for Next Iteration

Two architectural items remain tracked before generating `graph.toml` and the `.mmd` views:

1. **Work Items as True Graph Nodes:**
* Deciding whether a spec decomposes into parallel work-item nodes connected by `AFTER` dependency edges (concurrent Implementer loops in separate `workspaces/wip-*` worktrees on disjoint `ALLOW` scopes) or executes as a single node per spec.




2. **Risk-Tiered Approval / `high_risk_diff`:**
* Deciding whether `approval_archivation_plan` is resolved from the contract risk tier (note: since `owner` is now the default for `approval_archivation_plan`, low-risk specs could optionally resolve to `architect`). If adopted, `high_risk_diff` is unnecessary as an event; if a true event is wanted instead when `approval_archivation_plan: architect`, the Archivist or Architect would need an explicit `escalate` trigger to hand off to the Owner.





```

```
