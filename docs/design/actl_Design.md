# Agent Graph Architecture & Governance Specification

**Date:** October 14, 2026 (revision 2; supersedes earlier drafts)

**Overview:** This specification defines the graph topology, the five-account POSIX isolation model (`actl` plus one account per agent persona), persona responsibilities, artifact schemas, verification gates, and lifecycle governance for the `actl` multi-agent software delivery system.

**Conventions:**

* `{sprint_tag}` is `YYYY-MM-DD_{slug}`, declared once by `actl sprint new` and used for the sprint directory, git tags, and receipts.
* `{seq}` is the per-sprint monotonic sequence number assigned by `actl` (§5.1). Every immutable artifact is named `{kind}-{seq}`. Sequence numbers in examples are illustrative, and each example is an independent scenario.
* Check IDs (`Q1–Q5`, `G1–G6`, `O1`, `O2`, `L`, `E1.1–E1.6`) and invariants (`S`, `C`, `P`, `F`) are defined once in §2 and referenced by ID everywhere else.
* Appendix A (non-normative) records every removal and consolidation made in this revision, with its justification.

---

## 1. Graph Topology, Visual Semantics & Workspace Isolation

### 1.1 Single Source of Truth & Generated Views

* **Canonical sources:** `graph.toml` holds the installation-wide topology and default policy values. `sprint.toml` (§4.1) holds the fully resolved, frozen policy of one sprint. Views 02 (Swimlane Sequence), 03 (Context and Session Views), and 04 (`actl` Verification & Guard Map) are generated deterministically from `graph.toml`. View 04 functions as an annotation layer over the persona graph rather than an independent topology.
* **Primary deliverable:** Raw `.mmd` Mermaid definitions are the canonical visual artifacts (rendered at full resolution via `mermaid-cli` or native Markdown viewers).
* **Workflow topology:** The workflow operates as a deterministic spine (`actl`) orchestrating bounded loops: adversarial oracle qualification with Architect lock authority, implementation attempts, live run gating and recovery, escalation resolution, and closeout curation. One graph node exists per spec (§7).
* **Escalation edges in the graph:** `actl` → Architect (never drawn through the Implementer) carries the escalation record for `attempts_exhausted` (oracle and implementer stages), `session_cap`, `live_failed`, and `blocked`. A secondary `actl` → Owner control edge activates when the Architect escalates to the Owner (`escalate_owner`), when an Architect-listed action needs countersignature (`owner_review_triggers`), on Owner-routed triggers (curator `attempts_exhausted`, `session_cap` at the Architect or Curator, `live_failed` after the live budget), and on every `halt`. The full routing table is §6.3.

### 1.2 Orthogonal Edge Semantics

Every edge in the graph is classified along two independent axes: acceptance verification (line style) and routing role (color or arrowhead).

| Axis | Visual Encoding | Classification & Mechanics |
| --- | --- | --- |
| **Axis 1: Who Accepts the Hand-off (Verification)** | **Solid Line** | **Deterministic / Objective:** Accepted or enforced by `actl` via mechanical checks that inspect the transfer and reject violations (e.g., JSON schema validation on an LLM-written closure report, `git diff` scope checks, regex, git tree-equality, legacy test function count checks, mutant-kill checks on commit plans, deterministic session invocation). |
| **Axis 1: Who Accepts the Hand-off (Verification)** | **Dashed Line** | **Probabilistic / Subjective:** Accepted by an LLM or human exercising judgment (e.g., Architect ↔ Challenger spec/oracle review and lock decision, Architect or Owner Live Run approval, `actl` → Owner curation judgment and countersignatures). Represented as dashed lines because human review and semantic quality rely on judgment rather than mechanical verification. |
| **Axis 2: What Travels (Routing Role)** | **Standard Arrowhead / Primary Color** | **Unmodified Artifact Flow (Persona → Persona):** An artifact authored by one persona (spec, oracle) whose file pointer is staged and handed unmodified to the next persona when scheduled by `actl`. |
| **Axis 2: What Travels (Routing Role)** | **Open Arrowhead / Distinct Control Color** | **Control & Synthesized Envelope Flow (`actl` → Persona):** Scheduling signals and pointers to `actl`-synthesized JSON envelopes (contract, work order, escalation record). Because `actl` invokes sessions deterministically via script, control edges are drawn as solid lines (distinguished by their open arrowhead and control color). The single exception is a human-acceptance edge (`actl` → Owner), which is dashed because Axis 1 takes precedence over Axis 2. |

### 1.3 Module-by-Module Context & Piping Blueprint

At runtime, all artifacts reside on disk and `actl` routes file pointers to each session. `actl` never interprets free-text prose; its routing logic branches strictly on deterministic schema fields (enums, booleans, hashes, exit codes, counters). Process lifecycle supervision, state tracking, and console I/O are decoupled via daemonized headless `tmux` sessions backed by `systemd` user lingering (`loginctl enable-linger` for the four persona accounts):

| Module | Account & Context Strategy | Technical Piping & Execution Blueprint |
| --- | --- | --- |
| **`actl` (Unified Control Spine & Verifier)** | `actl` (member of groups `architect`, `challenger`, `implementer`, `curator`, `cloners`) / deterministic state file (`state.json`) + `tmux` supervisor registry | Single deterministic binary (`bin/actl`) composed of three internal modules: `orchestrator` (`state.py`), `dispatcher` (`dispatch.py`), and `verifier` (`verify.py`), running as an event-driven CLI/daemon. Spawns agent sessions inside detached headless `tmux` sessions (`spawn_detached_session`) with ephemeral `{session}.run.sh` scripts (`umask 0007`, `trap cleanup EXIT`, `remain-on-exit off`) and tracks liveness dynamically via `list_active_tmux_sessions()`. Interactive attachment (`actl attach {session}`) uses a non-destructive `pipe-pane` streaming tail proxy (`stream_session`). Communicates with the human Owner via a Notification Adapter (terminal prompt when attached; Telegram/webhook when detached), writing `status: "hold"` to `state.json` whenever a human decision is required. |
| **Architect** | `architect` / persistent thread (`--resume` from `profiles/architect`), vault copy `architect_thread.jsonl` + `architect-notes.md` in `records/` as compaction fallback | **Phase 1 (Sprint intake):** either interactive Owner Q&A (`sudo -u architect`) or an imported spec (§4.1). The Architect authors the spec and `solution_key.patch` and proposes the `sprint.toml` values in `architect-outputs/`. After every Architect turn `actl` copies `architect_thread.jsonl` and `architect-notes.md` into the vault in `records/` and promotes the authored artifacts. **Phase 2 (Oracle Review & Lock Authority):** when `actl` finishes running a qualification on the Challenger's draft oracle, it stages the results in `architect-inputs/`. The Architect reviews `oracle-critique.md` and the `qualification` receipt (which flags `pure_oracle_failure` or `solution_key_conflict`) and writes `oracle-decision.json` (`decision: "lock_oracle"` \| `"revise_oracle"`), optionally updating the spec, fixing `solution_key.patch` directly without wasting a Challenger attempt, or surgically widening `ALLOW` in `scope.txt`. **Phase 3 (Live Run Gate & Escalation Resolution):** reviews candidate diffs (`git diff {base_sha}..{head_sha}`) for Live Run approval (`live-decision.json`: `"approve_live"` \| `"reject_live"` when `approval_live_run: architect`) and resolves escalation records (`grant_attempts`, `waive_mutant`, `update_scope`, `reopen_oracle`, `retry_live`, `escalate_owner`), including `live_failed` recovery. |
| **Challenger** | `challenger` / stateless Just-in-Time (JIT) payload | Fresh CLI invocation (`sudo -u challenger`) per round inside a freshly reset `challenger-worktree/` workspace under `sprints/<repo>/<tag>/workspaces/`. Retaining failed turns causes the model to anchor on prior blind spots. `actl` stages `challenger-inputs/` read-only and frontloads static cache-friendly prefixes (`[Challenger System Prompt] + [spec] + [solution_key.patch]`) ahead of dynamic feedback (`[qualification receipt + oracle-decision.json + prior oracle]`). The Challenger writes only `challenger-outputs/oracle-draft/`. |
| **Implementer** | `implementer` / stateless JIT payload | Fresh CLI invocation (`sudo -u implementer`) per attempt inside a clean `implementer-{seq}/` standalone local git clone under `sprints/<repo>/<tag>/workspaces/` (`git clone --local --no-hardlinks` from the `cloners` export of `repos/<repo>`, owner `implementer:implementer`, `chmod 2770`, `umask 0007`) checked out at `base_sha` on branch `wip/{seq}`. `profiles/implementer` is provisioned as `HOME` (`chmod 0755`). `actl` frontloads static files (`[Implementer System Prompt] + [spec] + [contract] + [solution_key.patch when full]`) ahead of dynamic retry feedback (`[prior_attempt.json]`) to maximize prompt-cache hits without dragging failed tool-call noise. |
| **Curator** | `curator` / stateless JIT payload | Invoked strictly in Phase 4 (`sudo -u curator`) inside `curator-worktree/` under `sprints/<repo>/<tag>/workspaces/` (`owner: curator:curator`, `chmod 2770`, `umask 0007`) after the Implementer has passed all Phase 3 Offline and Live runs. Receives staged inputs from `curator-inputs/`: `[Curator System Prompt] + [spec] + [approved.diff] + [proofs/*.sh] + [non-applying mutants/*.patch requiring rebase] + [context.json (closure notes[], backlog[], waived_mutants[], modified_legacy_tests_diff)]` (plus `actl`/Owner rejection details if re-invoked). |

### 1.4 Every Place the Workflow Reaches the Owner

1. **Sprint intake (§4.1):** creates the sprint (`actl sprint new`), supplies requirements through interactive Q&A or an imported spec, and signs `sprint.toml` when `live_run = required` with `approval_live_run = architect`.
2. **Escalations, countersignatures and halts (§6.3):** resolves `escalate_owner`, countersigns any Architect action listed in `owner_review_triggers`, and clears `halt` records. Owner-routed cases: curator `attempts_exhausted`, `session_cap` at the Architect or Curator, `live_failed` after the live budget, and unsupported `hard_cap` dimensions for the target CLI engine.
3. **Live Run execution & gated approvals (§5.5):** signs `live-decision.hmac` per run on `head_sha` when `approval_live_run: owner`, and receives a parallel non-blocking alert on the first Live Run failure (blocking `hold` once the live budget is exhausted). Phase 4 curation-plan review and sign-off is unconditional.
4. **Closeout & merge (§3.2, §5.6):** reviews `diff-risk-review.md` (including any `Waived Mutants & Residual Risk`, `Modified Legacy Tests`, and `Same-Family Pairs` disclosures), selects items from `backlog-proposal.md` for the repo backlog, and executes the final `git push`.

### 1.5 Accounts, Groups & Directory Architecture

To enforce **P** mechanically, neutralize context-poisoning blast radii across phases, and scale cleanly across hundreds of sprints and repositories, the workspace under `ACTL_ROOT` is organized into three distinct lifetimes:
- **`records/`** is **STORAGE** (one git repository, owned by `actl:actl`, `chmod 700`).
- **`sprints/`** is **TRANSIENT** working memory, deleted after closeout.
- **`profiles/`** is **PERSISTENT** per-persona CLI state.
- **`repos/`** holds the target repositories written only by `actl`.

The system is partitioned across five Linux accounts: `actl` and one account per agent persona (`architect`, `challenger`, `implementer`, `curator`), paired with account-partitioned IPC mailboxes (`mailboxes/` under `sprints/<repo>/<tag>/`). Each persona account has a same-named primary group, `actl` is a member of every persona group, and no persona account is ever a member of group `actl`. All standalone local git clones (`workspaces/` under `sprints/<repo>/<tag>/`) are created and wiped via `sudo -u {account}` with `umask 0007` and `chmod 2770 {account}:{account}`, so `actl` has group read/write access for teardown without `EPERM`.

* **`actl`:** Runs the deterministic `actl` control-plane binary only. Owns `records/` (`chmod 700`, zero LLM access). Zero LLM sessions or untrusted verification scripts ever execute under `actl`.
* **`architect`:** Runs Phase 1–3 Architect sessions. Owns `sprints/<repo>/<tag>/workspaces/architect-worktree/`. Persistent state lives in `profiles/architect`.
* **`challenger`:** Runs Phase 2 Challenger sessions in `sprints/<repo>/<tag>/workspaces/challenger-worktree/` (which `actl` resets via `sudo -u challenger` before each round) and Phase 2 qualification (`Q1–Q5`) inside `sprints/<repo>/<tag>/workspaces/verify-challenger/`. Persistent state lives in `profiles/challenger`.
* **`implementer`:** Runs Phase 3 untrusted code authoring in `sprints/<repo>/<tag>/workspaces/implementer-{seq}/` and Phase 3 verification (`G`, `O1`, `O2`, `L`) inside `sprints/<repo>/<tag>/workspaces/verify-implementer/`. `profiles/implementer` is its persistent `HOME` (login, transcripts, installed skills; empty until Stage 4; `chmod 0755`; non-authoritative). No persistent path is trusted for verification; during verification, the outbox lock (`chmod 0750` on `outbox/`) is what is read-only. `actl` temporarily stages a copy of the oracle for verification and deletes it immediately after the run, so `records/` remains `chmod 700`.
* **`curator`:** Exclusively runs Phase 4 curation in `sprints/<repo>/<tag>/workspaces/curator-worktree/` and the Phase 4 checks `E1.4–E1.6` inside `sprints/<repo>/<tag>/workspaces/verify-curator/`, after the Implementer has passed all Phase 3 proofs. Persistent state lives in `profiles/curator`.

**Profiles (`profiles/`):**
`profiles/<persona>` is each persona account's persistent state directory, and the account's `HOME` points to it. It holds login, CLI configuration, session stores, transcripts, installed copies of skills and rules, and the Architect's persistent thread (`architect_thread.jsonl`). It does NOT hold persona instructions: prompts, skills, and rules are versioned in the atools repository and delivered by `actl` on each turn or installed at account creation. Nothing in a profile is authoritative: deleting one loses working memory, never policy. Durable results are copied into `records/` by `actl`. `actl init` writes `profiles/README.md`.

**Sprint closeout & archive policy (`records/<repo>/<tag>/closeout/`):**
Sprint closeout operates on an "archive, then delete" policy. Upon closeout, `actl` preserves essential verification and accounting records in `records/<repo>/<tag>/closeout/`:
- `sessions.tsv` (full session telemetry and cost ledger)
- The qualifying receipt (`qualification-NNN.json`)
- The final green verification receipt (`verification-NNN.json`)
- `closeout.md` (a deterministic summary report)
All transient working memory under `sprints/<repo>/<tag>/` (logs, workspaces, mailboxes, and raw turns) is discarded. `closeout.md` lives in `records/`, not in the target repository: the target repository is exported read-only to persona accounts, and `closeout.md` names oracle-derived items (waived mutants, proof IDs, tripwire hits), which Invariant **P** keeps inside the 700 `records/` repository. (A generated index `records/<repo>/closeouts.tsv` is deferred to Stage 5).

**`closeout.md` contents:**
Generated deterministically by `actl` from state and receipts (never written by an LLM, at most one page):
1. Identity: repo, sprint tag, `base_sha`, contract hash and tag, final head SHA, merge ref, opened and closed dates, spec source.
2. Outcome: done, aborted or escalated; the final verification receipt id and result; whether a Live Run happened.
3. Effort: attempts used against budget per stage, epochs, `closures_submitted`, `hardcap_stripped`, token and cost totals from `sessions.tsv`, wall-clock.
4. Models: model and family per persona, and the same-family pairs disclosed under Invariant F.
5. Decisions and exceptions: escalations (id, trigger, action), waived mutants with the Owner countersignature, modified legacy tests, tripwire hits, halts.
6. Backlog items the Owner accepted from `backlog-proposal.md`.
7. Artifact index: hashes of the kept files, the contract and oracle manifest hashes, and counts of what was discarded.
8. Pointers to the related sign-off records.

**Cleanup rule (all four persona accounts):** after every verification run and every persona session, `actl` runs `sudo -u {account} pkill -9 -u {account}` (SIGKILL to every process the account owns, so no background process spawned during a run survives into later runs), deletes any staged oracle copy, and wipes the private `/tmp`.

**Target repository access:** `repos/<repo>/` (e.g., `repos/target-repo/`) is written only by `actl` and exported read-only to group `cloners` (`0750 actl:cloners`; members: the four persona accounts and `actl`). Oracle material lives only in `records/`, so exposing target repositories does not weaken **P**.

```text
ACTL_ROOT (e.g. ~/actl-graph/)
├── README.md
├── baseline.json
├── repos/                                      # target repositories, written only by actl
│   └── target-repo/                            # [owner: actl:cloners, chmod 0750; write: actl only]
├── records/                                    # STORAGE: one git repo, actl only, chmod 700
│   └── target-repo/2026-10-16_public-profiles/
│       ├── sprint.toml                         # Frozen, fully resolved policy (§4.1)
│       ├── sprint.hmac                         # Owner signature (only when required)
│       ├── spec-001.md                         # Hashed specification (promoted from architect-outputs/)
│       ├── architect_thread.jsonl              # Vault copy of the Architect transcript (recovery only)
│       ├── architect-notes.md                  # Architect context-compaction fallback
│       ├── oracle-003/                         # Frozen oracle directory (hashed into the contract)
│       │   ├── proofs/                         # Black-box executable checks (01_public.sh, ...)
│       │   ├── probe.sh                        # End-to-end recomputation script
│       │   ├── mutants/                        # Sabotaged patches (contact_leak.patch, ...)
│       │   ├── scope.txt                       # ALLOW / FROZEN path glob rules
│       │   ├── coverage.md                     # Requirement -> proof and mutant -> proof mapping
│       │   ├── oracle-critique.md              # Challenger's adversarial critique of Spec & Key
│       │   └── solution_key.patch              # Canonical reference patch copied at freeze
│       ├── contract-005.json                   # Minted once per contract epoch at oracle freeze
│       ├── checklist.md                        # Git-tracked acceptance checklist
│       └── closeout/                           # Preserved closeout archive
│           ├── sessions.tsv                    # Final session accounting
│           ├── qualification-004.json          # Qualifying oracle receipt
│           ├── verification-007.json           # Final green verification receipt
│           └── closeout.md                     # Deterministic closeout report
├── sprints/                                    # TRANSIENT, deleted after closeout
│   └── target-repo/2026-10-16_public-profiles/
│       ├── runs/                               # Runtime receipts & working state
│       │   ├── state.json                      # seq, epoch, counters, active stage, tmux session refs
│       │   ├── sessions.tsv                    # CLI invocation telemetry & alert ledger
│       │   ├── qualification-004.json          # Phase 2 oracle qualification receipt
│       │   ├── verification-007.json           # Composite actl verification records (secrets scrubbed)
│       │   ├── escalation-010.json             # Synthesized escalation packets + resolution{}
│       │   ├── live-decision-012.json          # Audit copy of the Live Run approval
│       │   ├── logs/                           # Session execution logs
│       │   └── turns/                          # Turn ledger (bundle.txt, response.txt, etc.)
│       ├── mailboxes/                          # Account-partitioned IPC mailboxes
│       │   ├── architect/                      # inbox/ [0750] and outbox/ [0770]
│       │   ├── challenger/                     # inbox/ [0750] and outbox/ [0770]
│       │   ├── implementer/                    # inbox/ [0750] and outbox/ [0770]
│       │   └── curator/                        # inbox/ [0750] and outbox/ [0770]
│       └── workspaces/                         # Standalone clones (--local --no-hardlinks, umask 0007)
│           ├── architect-worktree/             # Scratch clone for the Architect
│           ├── challenger-worktree/            # Scratch clone for the Challenger (reset by actl before each round)
│           ├── implementer-006/                # Isolated Implementer clone (branch wip/006)
│           ├── curator-worktree/               # Phase 4 Curator clone at <contract-tag>
│           └── verify-{challenger,implementer,curator}/ # Ephemeral verification clones
└── profiles/                                   # PERSISTENT per persona (HOME points here)
    ├── architect/                              # Login, config, session store, persistent thread
    ├── challenger/                             # Login, config, session store
    ├── implementer/                            # Login, config, session store
    ├── curator/                                # Login, config, session store
    └── README.md
```

### 1.6 Mechanical Edge Guards & Two-Stage Curation Handoff

1. **Implementer → `actl` (session closure & pre-check guards, solid line):** guarded mechanically before any Offline Run executes. `actl` applies guards `G1–G6` (§5.5); only then do `O1` and `O2` execute. Any guard failure emits a red `ev-{seq}.json` citing the violated guard and routes identically to a failed Offline Run (consuming one `implementer` attempt and passing the guard failure in `prior_attempt.json`).
2. **Curation-plan hand-off, split into two explicit edges** because the plan undergoes both mechanical policy verification and semantic review:
   * **Edge 1: Curator → `actl` (solid, script-accepted):** `actl` runs checks `E1.1–E1.6` (§5.6, the single normative description).
   * **Edge 2: `actl` → Owner (dashed, human-accepted):** once Edge 1 passes, `actl` sets `status: "hold"` and hands the validated plan strictly to the Owner for semantic review of `diff-risk-review.md`, `plan/`, and `backlog-proposal.md`. Automated rejections occur only on Edge 1, bounded by `max_attempts.curator` and escalating to the Owner on exhaustion. Owner revision requests on Edge 2 bypass budget limits entirely and re-invoke the Curator with the Owner's specific change notes.

---

## 2. Core Vocabulary, Invariants & Check IDs

### 2.1 Terms

| Term | Definition |
| --- | --- |
| **Sprint** | One spec delivered end to end (one graph node). Declared by `actl sprint new {slug}`, which mints `{sprint_tag}`, pins `base_sha`, and creates the sprint directory, `state.json`, and a draft `sprint.toml`. |
| **Proof** | A single executable script (`proofs/*.sh`) verifying a specific spec requirement. Exits `0` (pass) or `1` (fail). Must be stage-agnostic (switching between offline mock endpoints and live endpoints via injected environment variables, never conditional test branches). Unconditionally translated into new native test files in the target repository's `test/` directory by the Curator during Phase 4 closeout. |
| **Oracle** | An artifact, not an actor: a frozen, hashed directory `oracle-{seq}/` inside `records/<repo>/<tag>/` containing `proofs/`, `probe.sh`, `scope.txt`, `solution_key.patch`, `mutants/`, `coverage.md`, and `oracle-critique.md`. `actl` stages a temporary copy into a `verify-*` workspace during verification runs so `records/` remains `chmod 700`. A scope-only change (`update_scope`) creates a new oracle with a `parent` pointer. |
| **Test** | The target repository's own tracked regression test suite (`test/`), including graduated proofs from prior specs. Executed automatically by `actl` at `Q4` (as `challenger`), at `O2` in every Phase 3 Offline Run (as `implementer`, after `O1` passes), and at `E1.6` (as `curator`). |
| **Guard** | A mechanical process check (file scope enforcement, legacy test function count conservation, credential leak scan, forbidden-call lint, commit message regex, git tree-equality): `G1–G6` and `E1.1–E1.3`. Proofs judge code; guards judge process. |
| **Actl (`actl`)** | The unified deterministic binary (`bin/actl`, composed of `orchestrator` [`state.py`], `dispatcher` [`dispatch.py`], and `verifier` [`verify.py`]) running under account `actl` that manages `state.json` and `seq`, supervises detached headless `tmux` agent sessions under `systemd` linger via `sudo -u {architect/challenger/implementer/curator}`, enforces mechanical closure and curation guards, executes qualification, Offline and Live verification runs (`runs/verification-{seq}.json`), and stamps `checklist.md` and `{contract-tag}`. |
| **Attempt** | One dispatched persona session of a budgeted stage (`oracle`, `implementer`, `curator`) or one Live Run execution (`live`). Every dispatch consumes one attempt of its stage, whether or not it produces a valid artifact. |
| **Epoch** | The lifetime of one `contract`. `update_scope` and `reopen_oracle` start a new epoch; per-epoch counters reset to the `sprint.toml` baseline. |
| **Offline Run** | Full Phase 3 execution of the oracle (`O1`: `proofs/` + `probe.sh` first, followed by `O2`: the target repo's Test suite) by `actl` (running subprocesses as `sudo -u implementer` inside `workspaces/verify-implementer/` with private `/tmp` and post-run `pkill -9 -u implementer`) after closure guards pass, with real credentials blanked. |
| **Live Run (`L`)** | Phase 3 execution of the oracle (`proofs/` + `probe.sh`) against live external services, gated by `live_run: none \| required` (no default) and `approval_live_run: architect \| owner` (default `architect`), executed via the root-owned privilege-dropping wrapper `/usr/local/bin/actl-live-run` (§5.5). |
| **Solution Key (`solution_key.patch`)** | A reference implementation patch authored solely by the Architect in Phase 1 (updated only by the Architect if Phase 2 qualification exposes a flaw), staged read-only to the Challenger for audit, verified at `Q2–Q4`, and copied into the oracle directory at freeze where its canonical hash is locked. Proves satisfiability (base red, key green) and serves as the Implementer's initial draft when `solution_key_exposure: full`. Never merged directly into the target repository without passing the Implementer, `actl`, and Curator pipeline. |
| **Mutants** | Deliberately sabotaged patches (`mutants/*.patch`) written by the Challenger against `solution_key.patch` that violate a specific spec requirement to test whether the oracle catches them. Evaluated at `Q5` only when `Q2` and `Q3` pass; recorded as `killed: true` (`git apply` succeeded and at least one proof exited `1`) or `killed: false` (surviving mutant or `apply_error: true`), and re-verified against the Curator's graduated native tests in Phase 4 (directly or via `curation-plan/mutants-rebased/`). |
| **Recomputation** | The oracle's end-to-end probe (`probe.sh`), which independently calculates claimed metrics from raw data (e.g., SQL counts, `git show --numstat`) and compares them against the implementation's output (layer 2 of §5.2). |
| **Contract-Hash Git Tag (`{contract-tag}`)** | An internal git tag (`refs/tags/actl/{sprint_tag}/{contract_sha256}`) pinned by `actl` in `repos/target-repo/.git` once Phase 3 Offline and Live runs pass on the identical head commit SHA, serving as the immutable reference tree for the Curator in Phase 4. |

### 2.2 Invariants

| ID | Invariant | Mechanism |
| --- | --- | --- |
| **S** | Every persona invocation runs in its own isolated headless `tmux` session with native sub-agent tools disabled. | `dispatch.py` adapters (§6.2). |
| **C** | A persona may keep its own context across its own turns; what passes between personas is artifacts only. | One account and HOME (`profiles/<persona>`) per persona; the Architect's thread lives in `profiles/architect`. |
| **P** | The Implementer's LLM session cannot read the Challenger's `proofs/`, `probe.sh`, or `mutants/`. | `records/` is `700 actl:actl`; the only repository exposed to agents is the oracle-free `repos/<repo>` export. **Residual risk:** during Offline and Live runs the candidate code executes in the same process tree as a staged oracle copy and could read it. The defences are mutants (`Q5`), the Live Run, and the Curator's graduation checks (`E1.4–E1.5`). |
| **F** | Prefer a different model family for Challenger vs Architect and for Curator vs Implementer. Preferred, never required. | `actl` logs `model_family` per session in `sessions.tsv`, and the Curator discloses same-family pairs in `diff-risk-review.md` (`Same-Family Pairs`, checked at `E1.1`). |

### 2.3 Check IDs

| Phase | IDs | Meaning |
| --- | --- | --- |
| 2 qualification (§5.2) | `Q1` | Null base fails `proofs/` (`null_base: red`). |
| | `Q2` | `solution_key.patch` passes closure guards `G3`, `G5`, `G6` (`solution_key_guards`). |
| | `Q3` | `solution_key.patch` passes `proofs/` + `probe.sh` 3/3 (`solution_key_green`). |
| | `Q4` | `solution_key.patch` passes the repo Test (`solution_key_repo_test`). |
| | `Q5` | Mutant evaluation, gated on `Q2` and `Q3` green. |
| 3 closure guards (§5.5) | `G1` | Oracle pre-flight hash matches `contract` (failure is a `halt`, not an attempt). |
| | `G2` | `closure-{seq}.json` schema and `blocked` preconditions. |
| | `G3` | `git diff {base_sha}..HEAD` within `scope.txt`. |
| | `G4` | Legacy test-function count conservation (when any `test/{file}` is unfrozen). |
| | `G5` | Credential/secret leak scan. |
| | `G6` | Forbidden-call lint. Every guard passes its built-in self-test first. |
| 3 runs (§5.5) | `O1` | Oracle `proofs/` + `probe.sh`. |
| | `O2` | Repo Test suite. |
| | `L` | Live Run. |
| 4 Edge 1 (§5.6) | `E1.1` | Artifacts, trailers, disclosures. |
| | `E1.2` | 100% feature tree-equality (`01..N-1`). |
| | `E1.3` | Commit N adds only new `test/**` files. |
| | `E1.4` | Null-Base Red, per graduated test. |
| | `E1.5` | Non-vacuous mutant-kill transfer. |
| | `E1.6` | Full Test suite green on Commit N. |

`verification-{seq}.json` step records carry both the ID and the command (`{"id": "G3", "cmd": "guard:scope"}`), and `blocking_step` cites an ID (§4.3).

---

## 3. Personas, Authority & Independence Rules

### 3.1 Inter-Persona Context Isolation (Invariant C)

* **Invariant C formulation:** *"A persona may keep its own context across its own turns; what passes between personas is artifacts only."*
* Because **C** restricts the communication channel between distinct personas rather than prohibiting a single persona from maintaining state across its own turns, the Architect's persistent thread (`architect_thread.jsonl`, resumed from `profiles/architect`) across a spec's lifecycle is natively compliant. Every persona has its own account, HOME (`profiles/<persona>`), and session store, so **C** is enforced by the OS rather than by file-permission tricks. `actl` copies the Architect thread and `architect-notes.md` into the vault in `records/` (`chmod 700 actl:actl`) after each turn for recovery only. Leaf personas (Challenger, Implementer, Curator) run fresh per session under their dedicated accounts with static artifacts frontloaded by `actl` (`dispatcher`) for prompt-cache efficiency, and receive their inputs as read-only `{role}-inputs/` directories staged by `actl`.

### 3.2 Persona Roster & Responsibilities

| Persona | Type & Account | Context Lifecycle | Core Responsibilities |
| --- | --- | --- | --- |
| **Owner** | Human | Continuous | Creates sprints (`actl sprint new`), supplies initial intent (Q&A or imported spec), holds live credentials (`/etc/actl/live.env` & `/etc/actl/owner.key`), signs `sprint.toml` when `live_run = required` with `approval_live_run = architect` (or `live-decision.hmac` per run when `owner`), resolves human-level escalations and `halt` records, countersigns any Architect action listed in `owner_review_triggers`, receives immediate parallel alerts on any `live_failed`, approves every curation plan (unconditional), decides which `backlog-proposal.md` items enter the repo backlog, and executes the final `git push` / merge. |
| **Architect** | LLM (Frontier Model A) / `architect` | Persistent per sprint (`architect_thread.jsonl`) | Acts as CTO/authority directly below the Owner. Conducts the Owner Q&A (or reviews an imported spec), authors the spec and `solution_key.patch`, proposes the `sprint.toml` values (including the mandatory choice of `live_run`), reviews the Challenger's `oracle-critique.md` and the `qualification` receipt in Phase 2 to decide whether to lock the oracle (`lock_oracle`, optionally fixing `solution_key.patch` or widening `ALLOW` in `scope.txt`) or loop back to the Challenger (`revise_oracle`), gates Phase 3 Live Runs (`live-decision.json` when `approval_live_run: architect`), and resolves the escalations routed to it (`grant_attempts`, `waive_mutant`, `update_scope`, `reopen_oracle`, `retry_live`), including `live_failed` recovery. Waiving a surviving mutant is an Architect action; the Owner countersigns it when `waive_mutant` is in `owner_review_triggers`. The Architect does not curate the repo backlog (the Owner does); `architect-notes.md` serves as the context-compaction fallback. |
| **`actl`** | Unified Binary (`state.py`, `dispatch.py`, `verify.py`) / `actl` | Stateless / event-driven (persists `state.json`, `qualification`, `verification`, `escalation` receipts, `checklist.md`, and `{contract-tag}`) | Unified deterministic control spine and runner (`bin/actl`). **Orchestrator (`state.py`):** assigns `seq`, tracks attempt counters, `closures_submitted`, and `hard_caps_tripped` and active `tmux` sessions in `state.json`, mechanically mints `contract` once the Architect locks the oracle, assembles escalation records, and dispatches Owner notifications. **Dispatcher (`dispatch.py`):** stages `{role}-inputs/` bundles, frontloads static file prefixes for cache hits, and launches detached headless `tmux` sessions in standalone `workspaces/` clones (`umask 0007`) via `sudo -u {architect/challenger/implementer/curator}`. **Verifier (`verify.py`):** runs `Q1–Q5` (as `challenger`), `G1–G6` with built-in self-tests, the Fail-Fast Offline Run `O1`/`O2` (as `implementer`), the Gated Live Run `L` (via `/usr/local/bin/actl-live-run`), emits secret-scrubbed `verification-{seq}.json` receipts, stamps `checklist.md` and `{contract-tag}`, and runs the Phase 4 Edge 1 checks `E1.1–E1.6` (as `curator`). |
| **Challenger** | LLM Leaf (Frontier Model B, adversarial) / `challenger` | Fresh per session (JIT payload) | Cross-family-preferred adversarial auditor. Audits the read-only spec and `solution_key.patch` for semantic flaws, missing requirement coverage, and weak assertions, and authors the oracle (`proofs/`, `probe.sh`, `mutants/`, `scope.txt`, `coverage.md`, including the mutant → proof mapping) plus `oracle-critique.md` in `challenger-outputs/oracle-draft/` for mechanical qualification by `actl` and review by the Architect. |
| **Implementer** | LLM Leaf (Fast Workforce Model) / `implementer` | Fresh per attempt (JIT payload) | Isolated worker running as account `implementer` inside the standalone local clone `workspaces/implementer-{seq}/` (`chmod 2770 implementer:implementer`, `umask 0007`, with `profiles/implementer` as persistent non-authoritative `HOME` (`chmod 0755`) and outbox locked `0750` during verification). Reads `implementer-inputs/` (including `solution_key.patch` when `solution_key_exposure: full`), checks out branch `wip/{seq}`, and commits work incrementally within `ALLOW` scope for traceability until ready for `actl` verification. Its LLM session is blocked by OS permissions (`chmod 700` on `records/`) from reading the oracle (Invariant **P**) and sees only failing steps/lines from Offline `actl` runs. Emits `closure-{seq}.json` (`done` or `blocked`). |
| **Curator** | LLM Leaf / `curator` | Fresh per session (JIT payload) | Invoked as account `curator` inside `workspaces/curator-worktree/` strictly in Phase 4 once all required Phase 3 `actl` runs (including the Live Run, if required) are green. Reads the staged `curator-inputs/` (`spec`, `approved.diff`, `proofs/*.sh`, non-applying `mutants/*.patch`, and `context.json` carrying `notes[]`, `backlog[]`, `waived_mutants[]`, and `modified_legacy_tests`). Produces the curation plan (`diff-risk-review.md`, `backlog-proposal.md`, `mutants-rebased/*.patch` for any divergent Phase 2 mutants, and `plan/NN-{slug}.patch/.msg` pairs always ending with `NN-graduate-tests.patch/.msg` adding new test files in `test/`). Cannot alter production code or modify/delete prior tests (enforced by `actl` at `E1.2`, `E1.3`, `E1.4`, and `E1.5`). |

### 3.3 Persona Independence Matrix

Every persona invocation runs in its own isolated headless `tmux` session (**S**) spawned by `actl` (`dispatcher`) with native sub-agent tools disabled, and holds its own context (**C**), so session and context separation are a universal baseline and omitted from the cells below. Rows are the persona being constrained; columns are the persona it is compared against.

| Persona (row) | Architect (`architect`) | Challenger (`challenger`) | Implementer (`implementer`) |
| --- | --- | --- | --- |
| **Challenger** | **F** | — | — |
| **Implementer** | **P\*** (only when `solution_key_exposure: hidden`) | **P** | — |
| **Curator** | — | — | **F** |

* **F (Cross-Family Preferred):** Prefer a different frontier model family (Challenger auditing the Architect's spec and `solution_key.patch` to author the oracle and `oracle-critique.md`; Curator reviewing the Implementer's diff and graduating tests). Only the Architect writes the spec and `solution_key.patch`; only the Challenger writes `proofs/`, `probe.sh`, and `mutants/`. `scope.txt` is authored initially by the Challenger and may be surgically widened (`ALLOW` additions only) by the Architect.
* **P (Private Artifacts Unreadable):** Enforced mechanically at the OS filesystem level (`records/` owned by `actl:actl` with `chmod 700`). The Implementer's LLM session is always blocked from the Challenger's test logic (`proofs/*.sh`, `probe.sh`, `mutants/*.patch`). The Challenger always reads `solution_key.patch` in Phase 2; in Phase 3, when `solution_key_exposure: full` (default), `actl` copies `solution_key.patch` into `implementer-inputs/`; when `hidden`, `actl` omits it so it remains unreadable to the Implementer inside `records/`.

---

## 4. Standardized Artifact & Package Schemas

**Naming & Lifecycle Rules:**

* **Sequence naming:** every immutable artifact is named `{kind}-{seq}` (`spec-001.md`, `oracle-003/`, `qualification-004.json`, `contract-005.json`, `closure-006.json`, `verification-007.json`, `escalation-010.json`, `live-decision-012.json`). Each file records `kind`, `seq`, and `parent` (for example, a scope-only oracle points to the oracle it derives from). Agents write only to fixed draft names; `actl` assigns the number when it promotes a file. An Implementer attempt reserves its `seq` at dispatch, and its workspace (`implementer-{seq}`), branch (`wip/{seq}`), and closure (`closure-{seq}`) share that number. No artifact refers to "latest": references use a `seq` or a hash, and `actl` resolves the current objects from `state.json` (`active_spec`, `active_oracle`, `active_contract`).
* **Records** are structured data files emitted by an agent or `actl`. **Plans / Patches** are actionable bundles reviewed and applied during closeout.
* **Single ownership of `solution_key.patch` & adversarial co-evolution of `scope.txt`:** `solution_key.patch` is authored solely by the Architect (updated only by the Architect if Phase 2 qualification exposes a bug or spec refinement), staged read-only to the Challenger for audit, verified at `Q2–Q4`, and copied into the oracle when locked by the Architect so its canonical hash is sealed at freeze. `scope.txt` is authored by the Challenger in Phase 2 and may be widened (`ALLOW` additions only) by the Architect during Phase 2 review or Phase 3 `action: "update_scope"` (with `actl` verifying that `proofs/`, `probe.sh`, `mutants/`, and `solution_key.patch` hashes remain 100% unchanged).
* **Three layers of state:** `sprint.toml` (frozen baseline policy), `state.json` (mutable counters and grants, initialized by `actl sprint new`), and `contract-{seq}.json` (minted once per contract epoch at oracle freeze, immutable throughout the epoch). The contract references `sprint_sha256` and never copies budgets; the effective limit of any budget is baseline plus granted increments. Both `qualification` and `contract` explicitly lock `base_sha`.
* **Reconstruction:** if `state.json` is lost, `actl` replays `qualification`, `verification`, and `escalation` receipts and `sessions.tsv` in `seq` order, using `sprint.toml` for baselines and `resolution.attempts_granted` and `minted_contract` for grants. `seq` is rebuilt as the highest number found in filenames.

### 4.1 Phase 1: Sprint Intake

| Package | From → To | Concrete Form | Example (`2026-10-16_public-profiles`) |
| --- | --- | --- | --- |
| **Sprint declaration** | Owner → `actl` | `actl sprint new {slug} [--spec spec.md]` mints `{sprint_tag}`, pins `base_sha`, creates the directory tree, `state.json` (with `seq` and `run_id`), and a draft `sprint.toml` with every default resolved from `graph.toml`. | `actl sprint new public-profiles` → `2026-10-16_public-profiles`. |
| **Intent & Q&A / imported spec** | Owner ↔ Architect, or Owner → `actl` | **Interactive:** Q&A persisted in the Architect thread. **Imported:** the spec is registered as `spec-001.md` and a short Architect turn authors `solution_key.patch`; any question raises a `hold` for the Owner. Both modes end in the same state. | "Add public profiles to users" → Q&A settles the `is_public` boolean. |
| **Spec** | Architect → Challenger | `spec-{seq}.md` (fixed headings: `Requirements`, `Locked`, `Deferred`), SHA-256 hashed. | `R1`: Guests see name, bio, avatar, photo count of public profiles. `R2`: Never expose email. `R3`: Private profiles return 404. `Locked`: users schema unchanged. `Deferred`: search engine indexing. |
| **Solution key** | Architect → Challenger (audit), Implementer (when `full`) | `solution_key.patch` (authored in the intake phase; staged read-only to the Challenger; locked into the oracle at freeze). | Working reference patch adding `is_public`, route, and serializer to prove the spec is satisfiable. |
| **Sprint policy** | Architect proposes → `actl` freezes → Owner signs when required | `sprint-proposal.toml` in `architect-outputs/`; frozen as `sprint.toml`; `sprint.hmac` over `sprint_tag \|\| sprint_sha256` using `/etc/actl/owner.key`. | See below. |

**Completeness gate.** `actl` refuses to dispatch the first Challenger turn until `sprint.toml` is complete and frozen. The Architect must explicitly choose `live_run` (`none` or `required`; there is no default, because both defaults fail silently in opposite directions). Freezing is automatic when `live_run = none`. When `live_run = required` with `approval_live_run = architect`, the Owner must also sign (`actl sprint sign`), because the Architect is then authorizing use of real secrets. After freezing, only the Owner can change the file (`actl sprint amend`, recorded and re-signed).

```toml
sprint_tag = "2026-10-16_public-profiles"
base_sha = "7c3a11b"
spec_source = "architect_qna"             # architect_qna | imported
after = []                                # optional: sprint_tags this sprint depends on
live_run = "required"                     # none | required (no default)
approval_live_run = "architect"           # architect | owner (only when live_run = required; default architect)
solution_key_exposure = "full"            # full | hidden (default full)
owner_review_triggers = ["waive_mutant"]  # Architect actions that need Owner countersignature (default [])
min_attempts_before_block = 2
max_epochs = 3                            # cap on update_scope / reopen_oracle epochs

[max_attempts]                            # per epoch; illustrative values, defaults live in graph.toml
oracle = 3
implementer = 2
live = 2
curator = 2

[hard_cap.implementer]                    # per persona; an omitted dimension is not enforced
wall_clock = "45m"
turns = 60
```

The **Runtime State & Session Ledger** is `runs/state.json` (`seq`, `epoch`, active stage, `attempts.{oracle,implementer,live,curator}`, `closures_submitted`, `hard_caps_tripped`, granted increments, `active_*`, `tmux` session refs, `status`) and `runs/sessions.tsv` (logs every CLI invocation: `model`, `model_family`, `turns`, `tool_calls`, `tokens`, `cost_usd`, `accepted_items`, `escalation_alerts_sent`). Both exist from `actl sprint new`, so `state.json` can be deterministically reconstructed alongside `runs/qual-*.json`, `runs/ev-*.json`, and `runs/escalation-*.json`.

### 4.2 Phase 2: Oracle Phase

| Package | From → To | Concrete Form | Example |
| --- | --- | --- | --- |
| **Oracle & critique** | Challenger → `actl` → Architect | Directory `oracle-{seq}/`: `proofs/`, `probe.sh`, `scope.txt`, `mutants/`, `coverage.md`, `oracle-critique.md` (+ `solution_key.patch` copied at freeze). | `proofs/02_no_email.sh`, `mutants/contact_leak.patch`, `oracle-critique.md` (critiquing edge cases in the spec and `solution_key.patch`). |
| **Coverage map** | Challenger → oracle | `coverage.md` (frozen and hashed inside the oracle) lists every proof and `probe.sh` a `done` stamp depends on per requirement, and the proofs expected to kill each mutant. | `R1` → proofs 01, 04, `probe.sh`; `R2` → proofs 02, 05, `probe.sh`; `R3` → proof 03; `contact_leak.patch` → 02, 05. |
| **Qualification record** | `actl` → Architect, Challenger | `runs/qualification-{seq}.json` (one per qualification run; records `oracle`, `spec`, `base_sha`, verifies null base fails, `solution_key.patch` passes guards, `proofs/` + `probe.sh` 3/3, and the repo Test, evaluates mutants only when `solution_key_green == "3/3"` recording `killed` and `apply_error`, and classifies `diagnostic_case`: `"none"` \| `"pure_oracle_failure"` \| `"solution_key_conflict"`) | `{"id": "qualification-004", "oracle": "oracle-003", "spec": "spec-001", "base_sha": "7c3a11b", "null_base": "red", "solution_key_guards": "green", "solution_key_green": "3/3", "solution_key_repo_test": "green", "mutants": [{"name": "contact_leak.patch", "killed": true, "apply_error": false}], "diagnostic_case": "none"}` |
| **Oracle decision record** | Architect → `actl` (and Challenger on loop) | `architect-outputs/oracle-decision.json` (`decision`: `"lock_oracle"` \| `"revise_oracle"`, `feedback`: `string` \| `null`) | `{"decision": "lock_oracle", "feedback": null}` (or `{"decision": "revise_oracle", "feedback": "Strengthen 02_no_email.sh to check raw payload for sentinel email string."}`) |
| **Checklist** | Initialized at freeze (`open`); stamped `done` or `waived` by `actl` | `checklist.md` (tracked in `records`; separate `Offline Run` and `Live Run` columns recording `verification-*` hash and head SHA) | `R2 \| proofs 02, 05, probe.sh + Test \| Offline: verification-011 (head: a41c9e0, sha256: 4b1a...) \| Live: verification-013 (head: a41c9e0, sha256: 9c4d...) \| done` (accepted surviving mutants append dedicated `mutant/contact_leak.patch \| waived \| escalation-004 (sha256: ...)` rows) |

### 4.3 Phase 3: Implementation Phase

| Package | From → To | Concrete Form | Example |
| --- | --- | --- | --- |
| **Implementation contract** | `actl` (minted once per epoch when the Architect locks the oracle, immutable) → Implementer, Curator | `contract-{seq}.json`: `epoch`, `base_sha`; `seq` and hashes of the spec, `oracle`, and `qual`; `sprint_sha256`; `scope.txt` reference. It carries no budgets (they live in `sprint.toml`). | `contract-005.json`, epoch 1. |
| **Work order** | `actl` → Implementer | Materialized in `implementer-inputs/`: spec + contract (+ `solution_key.patch` when `full`, + optional `prior_attempt.json` on retry) | Contains zero prose written by `actl`. Defines "done = all `actl` guards, oracle proofs, `probe.sh`, and repo Test suite exit 0". |
| **Implementation closure report** | Implementer → `actl` | `implementer-outputs/closure-{seq}.json` (`reason`: `"done"` \| `"blocked"`, `blocking_step`: a step ID such as `"G3"`, `"O1:02_no_email.sh"`, `"O2:{name}"`, or `null` on a pure architectural block, `notes`: `string[]`, `backlog`: `string[]`, `solution_key_divergence`: `{"requirement_id": string, "rationale": string}` \| `null`) | `{"reason": "done", "blocking_step": null, "notes": ["Reused UserSummarySerializer"], "backlog": ["Add pagination to profile photos"], "solution_key_divergence": null}` |
| **`actl` verification record** | `actl` → `runs/` (untracked) | `runs/verification-{seq}.json` (composite receipt emitted on every closure evaluation, guard rejection, or full `actl` run; literal `/etc/actl/live.env` values scrubbed to `[REDACTED]`) | `{"id": "verification-007", "stage": "offline", "oracle": "oracle-003", "contract": "contract-005.json", "head": "a41c9e0", "exit_code": 1, "steps": [{"id": "G3", "cmd": "guard:scope", "exit_code": 0, "output_sha256": "1a2b..."}, {"id": "O1", "cmd": "bash proofs/02_no_email.sh", "exit_code": 1, "output_sha256": "9f2c..."}], "failing_step": "O1:02_no_email.sh", "failing_line": "FAIL: body contains seeded email"}` |
| **Live decision record** | Architect (or Owner) → `actl` | `architect-outputs/live-decision.json` (when `approval_live_run: architect`) or `live-decision.hmac` (when `owner`), both bound to `contract_sha256` and `head_sha`; `actl` stores an audit copy as `runs/live-decision-{seq}.json` | `{"decision": "approve_live", "contract_sha256": "8f3c...", "head_sha": "a41c9e0", "rationale": "Offline proofs and regression suite green; no outbound network anomalies in diff."}` |
| **Contract-hash git tag (`{contract-tag}`)** | `actl` → `repos/target-repo/.git` (for the Phase 4 Curator & Verifier) | Git tag `refs/tags/actl/{sprint_tag}/{contract_sha256}` pinned when Phase 3 Offline and Live runs pass on the identical head SHA | `refs/tags/actl/2026-10-16_public-profiles/8f3c...` pointing to commit `a41c9e0`. |
| **Escalation record** | `actl` → Architect or Owner | `runs/escalation-{seq}.json`, assembled mechanically by `actl` (schema below). | See examples below. |

**Escalation record schema.** Fields: `stage` (`oracle` \| `implementer` \| `live` \| `curator` \| `architect` \| `actl`), `trigger` (`attempts_exhausted` \| `blocked` \| `session_cap` \| `live_failed` \| `halt`), `to` (`architect` \| `owner`), `legal_actions[]`, `epoch`, `contract`, `attempts: {used, max}`, orthogonal `closures_submitted` and `hard_caps_tripped` counters, `last_closure`, `evidence[]`, `diff_stat`, `log_tail`, `oracle_review` (`null` unless `stage: oracle`), `resolution`, and top-level `minted_contract` stamped by `actl` after resolution. `resolution` holds `by`, `action`, `attempts_granted: {stage, n}`, `waived_mutants[]`, `rationale`, and `owner_countersign` (`null`, or the Owner's signature record when the action is in `owner_review_triggers`). `halt` records carry `reason`: `integrity_mismatch` \| `wrapper_rejected` \| `unsupported_cap` \| `architect_unavailable`. `log_tail` goes to the Architect only and is never forwarded to a later Implementer. The trigger and action vocabulary is §6.3.

**Implementer attempts-exhausted example** (`trigger: attempts_exhausted`; attempts ended with `reason: done` closures and stayed red):

```json
{
  "id": "escalation-010", "stage": "implementer", "trigger": "attempts_exhausted", "to": "architect",
  "legal_actions": ["grant_attempts", "reopen_oracle", "escalate_owner"],
  "epoch": 1, "contract": "contract-005.json", "attempts": {"used": 2, "max": 2},
  "closures_submitted": 2, "hard_caps_tripped": 0, "last_closure": "closure-008.json",
  "evidence": ["verification-007", "verification-009"], "diff_stat": "api/profile.py | 31 +++", "log_tail": "<last 40 lines>",
  "oracle_review": null,
  "resolution": {"by": "architect", "action": "grant_attempts", "attempts_granted": {"stage": "implementer", "n": 2},
                 "waived_mutants": [], "rationale": "Implementer fixed serializer in attempt 2 but missed null avatar fallback; 2 additional attempts sufficient.",
                 "owner_countersign": null},
  "minted_contract": null
}
```

**Session-cap example** (`trigger: session_cap`; session killed by the wall-clock/turn/token/cost supervisor before writing a closure, incrementing `hard_caps_tripped` while `closures_submitted` stays `0`):

```json
{
  "id": "escalation-011", "stage": "implementer", "trigger": "session_cap", "to": "architect",
  "legal_actions": ["grant_attempts", "escalate_owner"],
  "epoch": 1, "contract": "contract-005.json", "attempts": {"used": 1, "max": 2},
  "closures_submitted": 0, "hard_caps_tripped": 1, "last_closure": null, "evidence": [],
  "diff_stat": "api/profile.py | 9 +", "log_tail": "<last 40 lines>", "oracle_review": null,
  "resolution": {"by": "architect", "action": "grant_attempts", "attempts_granted": {"stage": "implementer", "n": 1},
                 "waived_mutants": [], "rationale": "Subprocess hung on external network call; retry with clean sandbox.",
                 "owner_countersign": null},
  "minted_contract": null
}
```

**Blocked example** (`trigger: blocked`; accepted by `actl` only when the preconditions of §5.4 hold: `closures_submitted` ≥ `min_attempts_before_block`; `G1–G6` pass unless `blocking_step` is `G3`; `O2` passes unless `blocking_step` cites an `O2` step; and, when `solution_key_exposure: full` and `blocking_step` cites an `O1` step, `solution_key_divergence` is a valid `{"requirement_id", "rationale"}` object whose `requirement_id` exists in `coverage.md`):

```json
{
  "id": "escalation-012", "stage": "implementer", "trigger": "blocked", "to": "architect",
  "legal_actions": ["update_scope", "reopen_oracle", "grant_attempts", "escalate_owner"],
  "epoch": 1, "contract": "contract-005.json", "attempts": {"used": 2, "max": 2},
  "closures_submitted": 2, "hard_caps_tripped": 0, "last_closure": "closure-008.json",
  "evidence": ["verification-007", "verification-009"], "diff_stat": "api/profile.py | 18 ++", "log_tail": "<last 40 lines>",
  "oracle_review": null,
  "resolution": {"by": "architect", "action": "update_scope", "attempts_granted": null, "waived_mutants": [],
                 "rationale": "Added literal ALLOW api/index.py to scope.txt in oracle-013; actl verified proofs/, probe.sh, mutants/, and solution_key.patch hashes unchanged, verified G3 against solution_key.patch and the implementer-008 diff, stamped qualification-014.json via fast-path, and minted contract-015.json (epoch 2).",
                 "owner_countersign": null},
  "minted_contract": "contract-015.json"
}
```

**Oracle-attempts-exhausted example** (`stage: oracle`; fires only when the Architect emits `decision: "revise_oracle"` or a `lock_oracle` re-check fails with no `max_attempts.oracle` remaining; `action: "waive_mutant"` is mechanically permitted only when `failing_checks` is empty; here the action is listed in `owner_review_triggers`, so the Owner countersigned):

```json
{
  "id": "escalation-004", "stage": "oracle", "trigger": "attempts_exhausted", "to": "architect",
  "legal_actions": ["grant_attempts", "waive_mutant", "escalate_owner"],
  "epoch": 1, "contract": null, "attempts": {"used": 3, "max": 3},
  "closures_submitted": 0, "hard_caps_tripped": 0, "last_closure": null, "evidence": [],
  "diff_stat": null, "log_tail": null,
  "oracle_review": {"latest_oracle": "oracle-002", "latest_sha256": "5d2f...", "qual": "qualification-003.json",
                    "diagnostic_case": "pure_oracle_failure", "failing_checks": [],
                    "surviving_mutants": ["mutants/contact_leak.patch"]},
  "resolution": {"by": "architect", "action": "waive_mutant", "attempts_granted": null,
                 "waived_mutants": ["mutants/contact_leak.patch"],
                 "rationale": "Mutant renames internal dict key without affecting serialized public response schema.",
                 "owner_countersign": {"by": "owner", "at": "2026-10-16T21:40:00Z", "sha256": "c71e..."}},
  "minted_contract": "contract-005.json"
}
```

### 4.4 Phase 4: Closeout Phase

| Package | From → To | Concrete Form | Example |
| --- | --- | --- | --- |
| **Curation plan** | **Edge 1:** Curator → `actl` (solid: checks `E1.1–E1.6`, §5.6)<br>**Edge 2:** `actl` → Owner (dashed; mandatory human trunk supervision) | Written to `curator-outputs/curation-plan/`:<br>1. `diff-risk-review.md`<br>2. `backlog-proposal.md`<br>3. `mutants-rebased/*.patch` (for any Phase 2 mutant failing `git apply --check` on Commit N)<br>4. `plan/` with `NN-{slug}.patch` / `NN-{slug}.msg` pairs (always ending with `NN-graduate-tests.patch/.msg`) | 1. Semantic risk notes on serializer reuse, plus mandatory `Waived Mutants & Residual Risk`, `Modified Legacy Tests`, and `Same-Family Pairs` sections when applicable.<br>2. Merged follow-ups tagged `source: implementer` or `source: curator` (or `none`).<br>3. `actl` applies feature patches (`01-public-profile-serializer.patch`) matching `{contract-tag}` 100%, followed by strictly newly added graduated test files (`02-graduate-tests.patch` in `test/**`), each red against `base_sha` or killing a mapped mutant, with all non-waived `oracle-*/mutants/*.patch` or `mutants-rebased/*.patch` killed, and the full Test green. |
| **Curator context** | `actl` → Curator | `curator-inputs/context.json`: `notes[]`, `backlog[]`, `waived_mutants[]`, `modified_legacy_tests`. | |

---

## 5. Lifecycle Mechanics & Loop Governance

### 5.1 State, Sequence Numbers & Supervisor-Backed Process Liveness (`actl`)

* **Sequence numbers:** `state.json` carries a single `seq` counter, written only by `actl`. `actl` reserves the next value (saves `state.json`) before writing the artifact, so a crash leaves a gap and never a duplicate. Numbers are never reused or reset, including between runs and contract epochs.
* **External state file (`specs/{sprint_tag}/runs/state.json`) vs. epoch-immutable contract:** `actl` (`orchestrator`) initializes `state.json` in `actl sprint new` (scoped to `run_id` across any spec revisions) to track `seq`, `epoch`, the attempt counters (`oracle`, `implementer`, `live`, `curator`), `closures_submitted`, the hard watchdog counter `hard_caps_tripped`, active stage, `active_*` pointers, `status`, active `tmux` session metadata, and any dynamic grants made during escalations. Per-epoch counters reset to the `sprint.toml` baseline when `epoch` increments. `closures_submitted` counts schema-valid closures and is the quantity compared with `min_attempts_before_block`. `contract-{seq}.json` is minted once when the Architect locks the oracle and is never mutated:
  * If additional attempts are granted on escalation (`action: "grant_attempts"`) without changing the spec or oracle, `state.json` and the escalation `resolution` are updated while the contract remains static.
  * `epoch` starts at `1` and increments on `update_scope` (fast-path qualification) and on `reopen_oracle`. Once `epoch` would exceed `max_epochs`, those actions are no longer legal and the escalation routes to the Owner. A new epoch writes a new `qual`, mints a new `contract` (resetting `closures_submitted` and the per-epoch attempt counters to the `sprint.toml` baseline, requiring `attempts_granted: null` in `resolution`), and regenerates the requirement rows (`R_i`) of `checklist.md` from the new oracle's `coverage.md` with `Offline Run` and `Live Run` reset to `open` (while preserving any `mutant/*.patch | waived` rows).
  * If `state.json` is lost or corrupted, all counters, active epochs, and grants are reconstructed deterministically as described in §4 (Reconstruction).
* **Decoupled headless `tmux` supervision, workspace lifecycle & anti-wedge liveness tracking (`dispatch.py`):**
  1. **Non-root workspace creation & teardown (`sudo -u {account}` + `umask 0007`):** all `workspaces/{dir}/` clones are created and wiped via `sudo -u {account}` with `umask 0007` enforced inside `{session}.run.sh` and `chmod 2770 {account}:{account}` on the root clone. This guarantees `actl` (a member of every persona group) has full group read/write access to all nested directories and can execute a clean `sudo -u {account} rm -rf` teardown without `EPERM` or `EACCES`.
  2. **Decoupled process tree (no orphaned children):** agent sessions are never spawned as naked subprocesses of the caller's terminal. `dispatch.py` spawns each session inside a dedicated headless `tmux` session (`spawn_detached_session`). If the caller CLI or SSH session disconnects or crashes, the runner continues unaffected inside `tmux` under `systemd` linger.
  3. **Supervisor-backed liveness over raw PIDs/PGIDs:** liveness is evaluated dynamically via `list_active_tmux_sessions()`, which polls `sudo -u {account} tmux list-sessions -F "#{session_name}|#{session_created}"`, instead of storing fragile PIDs/PGIDs in `state.json`.
  4. **Automatic stale-state pruning (anti-wedge):** whenever sessions are queried or re-inspected (`get_running_sessions`), `actl` cross-references disk metadata against active `tmux` sessions. Any metadata entry for a dead session is immediately unlinked (`meta_file.unlink()`), and `actl` reconciles the transition state from the completed session's artifacts without wedging or double-spending attempts.
  5. **Self-terminating ephemeral runners:** each session executes inside a dynamically generated runner script (`{session}.run.sh`) with `umask 0007`, an explicit `EXIT` trap (`trap cleanup EXIT`), and `remain-on-exit off`. When the process exits (normal completion, fatal error, or the `timeout -k 15s {wall_clock}` watchdog), the runner cleans its active session metadata and terminates the `tmux` socket so it can never remain stuck in a zombie running state.
  6. **Non-destructive attaching & detaching:** interactive observation (`actl attach {session}`) operates via a streaming tail proxy (`stream_session`) over `pipe-pane` log streams. `Ctrl+C` does not send `SIGINT` to the agent child; Python traps `KeyboardInterrupt`, preserves background execution, and presents an interactive menu (`[b] Detach to shell`, `[r] Resume stream`, `[k] Kill session`).

### 5.2 Adversarial Oracle Qualification Loop (Architect ↔ `actl` ↔ Challenger)

1. **Adversarial authoring & mechanical qualification:**
   * **Architect spec & reference key:** at sprint intake, following Q&A (or import), the Architect (`sudo -u architect`) leaves its spec draft and `solution_key.patch` in `architect-outputs/`. After every Architect turn `actl` (account `actl`) copies `architect_thread.jsonl` and `architect-notes.md` into the vault in `records/`, promotes the spec and `solution_key.patch` into `records/{repo}/{sprint_tag}/`, and stages read-only copies in `challenger-inputs/`. The Challenger runs under its own account, so it can neither read the Architect's HOME and session store nor alter the staged inputs; no inode re-creation or permission toggling is needed.
   * **Challenger audit, oracle authoring & critique:** in Phase 2, the cross-family-preferred Challenger (`sudo -u challenger`) audits the read-only spec and `solution_key.patch` for semantic flaws (missing requirement coverage, shared misreadings, weak assertions such as checking `has("email")|not` when an email leaks under a renamed key `contact`) and authors `oracle-draft/` (`proofs/`, `probe.sh`, `mutants/`, `scope.txt`, `coverage.md`, plus `oracle-critique.md`) in `challenger-outputs/`. By default `scope.txt` sets `FROZEN: test/**`.
   * **`scope.txt` rules:** paths are denied unless matched by `ALLOW`. `FROZEN` beats any `ALLOW` glob. Only a literal-path `ALLOW` (no glob) thaws a frozen path. Blanket `ALLOW: **` and `ALLOW: test/**` are invalid.
   * **Mechanical qualification & diagnostic classification (`qualification-{seq}.json`):** `actl` (`verifier`) stages `oracle-draft/` and the canonical `solution_key.patch` from `records/` into `workspaces/verify-challenger/` and runs it as `challenger` against `base_sha`, verifying five checks:
     1. `Q1`: the null base implementation at `base_sha` fails `proofs/` (`null_base: red`).
     2. `Q2`: `solution_key.patch` passes the closure guards `G3`, `G5`, `G6` (`scope.txt`, secret scan, forbidden-call lint) (`solution_key_guards: green`).
     3. `Q3`: `solution_key.patch` passes `proofs/` and `probe.sh` repeatedly (`solution_key_green: 3/3`).
     4. `Q4`: `solution_key.patch` passes the target repo's existing Test suite (`solution_key_repo_test: green`), catching any obsolete existing test in Phase 2 so the Architect can update `solution_key.patch` and surgically add a literal `ALLOW: test/{specific_file}` to `scope.txt`.
     5. `Q5`: **mutant evaluation, gated on `Q2` and `Q3`** (`skipped` otherwise, preventing false `killed: true` results from a broken key). A mutant is `killed: true` iff `git apply` succeeds on `base_sha + solution_key.patch` AND at least one proof (or `probe.sh`) exits `1`. A mutant that fails `git apply` is `killed: false, apply_error: true`. Every mutant must be mapped to proofs in `coverage.md`, or `actl` rejects the draft as malformed.
   * The cleanup rule of §1.5 follows every run. Based on the five checks, `actl` stamps `diagnostic_case`:
     * `"none"`: `Q1` red, `Q2–Q4` green, and all mutants `killed: true` with `apply_error: false`.
     * `"pure_oracle_failure"`: `Q2–Q4` are green (the Architect's key passed everything), but `Q1` is not red or at least one mutant has `killed: false` (survived or `apply_error: true`), proving the Challenger's assertions or mutants need strengthening.
     * `"solution_key_conflict"`: any of `Q2–Q4` is red (a Challenger proof, `scope.txt` rule, or existing repo Test rejected the Architect's key).
2. **Four-layer defense against weak proofs:**
   * **Value-level sentinel proofs:** seed known sentinel strings (e.g., a test email) and fail if the literal string appears anywhere in the raw response payload.
   * **End-to-end probe (`probe.sh`):** inspects actual runtime outputs and performs independent recomputation.
   * **Adversarial mutants:** the Challenger supplies sabotaged patches (`mutants/contact_leak.patch`) that expose weak assertions and remain archived in the oracle for `Q5` and `E1.5`.
   * **Visible residual risk & Owner disclosure:** any surviving mutant (`killed: false`) waived at escalation (recorded in `resolution.waived_mutants`) is stamped as a dedicated `mutant/{name}.patch | waived | escalation-{seq}` row in `checklist.md` and must be explained in `diff-risk-review.md` for Owner review at closeout.
3. **Architect review, locking authority & loop governance:** after every `qual` (including when no `max_attempts.oracle` remains), `actl` stages the results in `architect-inputs/` and invokes the Architect to review `oracle-critique.md` and the `qual` receipt. The Architect writes `oracle-decision.json` (`decision: "lock_oracle" | "revise_oracle"`):
   * **Path 1, lock proofs (`decision: "lock_oracle"`):**
     * When `diagnostic_case == "none"`: if the Architect agrees with the Challenger's proofs and critique, `actl` immediately freezes `oracle-{seq}/` into `records/` (locking the canonical hash of `solution_key.patch`) and mints `contract-{seq}`.
     * When `diagnostic_case == "solution_key_conflict"` (the Challenger caught a flaw in `solution_key.patch` or `scope.txt`): if the Architect agrees with the critique and fixes `solution_key.patch` (and/or widens `ALLOW` in `scope.txt`) without needing changes to `proofs/` or `mutants/`, it emits `lock_oracle`. `actl` immediately re-qualifies (new `qualification-{seq}`) without spending a Challenger attempt; if `diagnostic_case` is now `"none"`, `actl` freezes the oracle and mints the contract, otherwise (a mutant now fails with `apply_error: true` or survives) it routes as `revise_oracle`.
   * **Path 2, return to Challenger (`decision: "revise_oracle"`):** on `pure_oracle_failure` or a disagreed `solution_key_conflict` (the Challenger's proof or scope rule was over-strict), or when the Architect refined the spec in response to `oracle-critique.md`, the Architect records its directive in `oracle-decision.json` (`feedback: "..."`). While `attempts.oracle < max_attempts.oracle`, `actl` stages the new `challenger-inputs/` and dispatches the Challenger (one attempt consumed) to revise `oracle-draft/`.
   * **Attempt exhaustion (`trigger: attempts_exhausted`, `stage: oracle`):** every Challenger dispatch consumes one attempt, including sessions that end without a valid `oracle-draft/`. Fires only when the Architect emits `revise_oracle` (or a `lock_oracle` re-qualification still fails) and no attempts remain. `actl` assembles the escalation record (with `oracle_review` populated from the latest `qual`, including `diagnostic_case`, `failing_checks`, and `surviving_mutants`) and routes it per §6.3. To preserve cross-family independence (**F**), the Architect never edits `proofs/` or `mutants/` directly; it records a `resolution`, choosing:
     1. `grant_attempts`: additional `max_attempts.oracle` budget in `state.json`, or
     2. `waive_mutant`, which `actl` mechanically accepts only when `oracle_review.failing_checks` is empty (`null_base == "red"` and all `solution_key_* == "green"`): the latest oracle freezes, `actl` mints the contract (stamping `minted_contract`), and appends `mutant/{name}.patch | waived | escalation-{seq} (sha256: ...)` rows in `checklist.md`. If `waive_mutant` is in `owner_review_triggers`, `actl` holds until the Owner countersigns, or
     3. `escalate_owner`.

### 5.3 Coverage Map & Checklist Stamping Rule

* `coverage.md` explicitly lists every proof ID (plus `probe.sh`) required to satisfy each requirement (`R_i` → `[proof_a, proof_b, ..., probe.sh]`) and the proofs expected to kill each mutant.
* `specs/{sprint_tag}/checklist.md` tracks `Offline Run` and `Live Run` receipts in separate columns, recording both the `verification-{seq}.json` SHA-256 hash and the literal head commit SHA evaluated:
  * When `live_run: none`, the `Live Run` column is initialized to `n/a`, and `actl` stamps each `R_i` row `Status: done` once all mapped `proofs/`, `probe.sh`, and the target repo's Test suite exit `0` (green) in the composite `Offline Run` receipt on the same head commit SHA.
  * When `live_run: required`, `Status` remains `open` after the `Offline Run` column is populated and only flips to `done` when the `Live Run` column also records `0` (green) receipts for all mapped `proofs/` and `probe.sh` on the identical head commit SHA.
* Once all required Phase 3 runs pass on that identical head commit SHA, `actl` creates/updates `{contract-tag}` in `repos/target-repo/.git` pointing to that head SHA before invoking the Curator in Phase 4.
* Surviving mutants waived in Phase 2 occupy their own `mutant/{name}.patch | waived | escalation-{seq}` rows and never mark a requirement row (`R_i`) as `done` or `waived`.
* Closeout requires zero `open` requirement rows in `checklist.md` (every `R_i` row must be `done`, and any `waived` mutant rows must be disclosed in `diff-risk-review.md`).

### 5.4 Implementation Routing, Attempts & Blocked Escalations

1. **Standalone clone & retry / restart mechanics:** for each attempt, `actl` (`dispatcher`) reserves a `seq`, consumes one `attempts.implementer`, creates a fresh standalone local clone (`sudo -u implementer git clone --local --no-hardlinks` from the `repos/<repo>` export into `workspaces/implementer-{seq}`, owned by `implementer:implementer`, `chmod 2770`, `umask 0007`), sets `implementer-outputs/` to `chmod 0770`, and launches a fresh Implementer session (`sudo -u implementer`, frontloading static prefixes + `solution_key.patch` when `full`) checked out at `base_sha` on branch `wip/{seq}`. The Implementer commits work incrementally onto `wip/{seq}` for full traceability. When the Implementer writes `closure-{seq}.json`, `actl` (`verifier`) locks `implementer-outputs/` to `chmod 0750`, increments `closures_submitted` if the closure is schema-valid, and natively fetches `wip/{seq}` into `workspaces/verify-implementer/` to evaluate the closure guards and the Offline Run, emitting a `verification-{seq}.json` receipt for every closure evaluation. A session that ends without a valid closure (and was not killed by a hard cap) is treated as a red attempt at `G2`. When a closure guard or Offline run is red and `max_attempts.implementer` budget remains, `actl` deletes the previous workspace via `sudo -u implementer rm -rf`, creates a clean standalone clone at `base_sha`, and writes `prior_attempt.json` (previous diff patch, `failing_step` and `failing_line` from the last `verification-{seq}.json`, and `closures_submitted` count) to `implementer-inputs/` strictly as an optional hint. When a red result leaves no attempts, `actl` raises `attempts_exhausted`. `log_tail` from escalation records goes to the Architect only and is never forwarded to a later Implementer.
2. **Deterministic routing on closure `reason`:**
   * **`reason: done`** → triggers `G1–G6` followed immediately by the Fail-Fast Offline Run (§5.5).
   * **`reason: blocked`** → the Implementer halts when it cannot satisfy `actl` verification due to an `ALLOW` scope restriction (including an obsolete existing test in `FROZEN: test/**`), a missing architectural decision, or a suspected over-constrained proof (`blocking_step` cites a step ID from `verification-{seq}.json`, e.g., `"G3"`, `"O1:02_no_email.sh"`, or `"O2:{test}"`, or `null` on a pure architectural block).
   * **Anti-early-give-up guards:** when `closure-{seq}.json` specifies `reason: blocked`, `actl` executes `G1–G6` and `O2` directly against the current worktree (emitting a `verification-{seq}.json`) and mechanically rejects `blocked` (treating an invalid claim as a failed attempt that consumes one `implementer` attempt) unless:
     1. `closures_submitted` ≥ `min_attempts_before_block`,
     2. all of `G1–G6` pass on the current worktree (unless `blocking_step == "G3"`) and the repository's compilation and `O2` pass (unless `blocking_step` cites an `O2` step), and
     3. when `solution_key_exposure: full` and `blocking_step` cites an `O1` step, `closure-{seq}.json` includes a non-null `solution_key_divergence: {"requirement_id": "{R_i}", "rationale": "{non-empty string}"}` where `requirement_id` is mechanically verified to exist in `coverage.md` (explaining which requirement `solution_key.patch` shortcutted). For `G3`, `O2`, or `null` blocks it may be `null`.
   * **Phase 3 obsolete-test escape hatch (`FROZEN: test/**`) & surgical test-diff audit gate:** if an existing regression test in `test/**` fails during Phase 3 because it conflicts with new spec behavior and was not unfrozen in Phase 2, the Implementer cannot edit `test/**` directly. Instead it halts with `reason: blocked` and `blocking_step: "O2:{test}"`. `actl` routes the escalation (`trigger: blocked`) to the Architect, who inspects the failure and resolves via `action: "update_scope"`, surgically adding a literal `ALLOW: test/{specific_file}` to the new oracle's `scope.txt`. Whenever any such rule is active, `G4` enforces that the count of discovered test functions (`test_*`) in `test/{file}` never decreases relative to `base_sha` (unless explicitly pre-authorized in `scope.txt`), and `actl` attaches the verbatim `git diff {base_sha}..HEAD -- test/` extract to both Phase 3 Live Run approval and Phase 4 `diff-risk-review.md` (`Modified Legacy Tests`).
   * **Escalation routing:** once the `blocked` preconditions are met, `actl` assembles the escalation record (`trigger: blocked`, citing `last_closure` and `evidence`) and routes it to the Architect, which records a `resolution`:
     1. **`action: "update_scope"` (fast-path qualification):** the Architect updates `scope.txt` in `architect-outputs/`; `actl` mechanically verifies that (a) `proofs/`, `probe.sh`, `mutants/`, and `solution_key.patch` hashes are identical to the active oracle, (b) `scope.txt` contains no blanket `ALLOW: **` or `ALLOW: test/**` globs and passes `G3` in-memory against both `solution_key.patch` and, when `blocking_step == "G3"`, the Implementer's diff, and (c) **zero test suites are re-executed**: `actl` carries forward the invariant `null_base`, `solution_key_green`, `solution_key_repo_test`, and `mutants` results from the previous `qual`, writes a new `oracle-{seq}/` (with `parent`) and a new `qual-{seq}.json` (stamping the new `manifest_sha256`), increments `epoch`, and mints `contract-{seq}` with a fresh baseline attempt budget.
     2. **`action: "reopen_oracle"`:** if a proof or the spec itself requires revision, the Architect reopens the Phase 2 loop to produce and lock a new oracle, increments `epoch`, and mints a new contract.
     3. **`action: "grant_attempts"`:** rejects the block and grants additional `implementer` attempts in `state.json`.
     4. **`action: "escalate_owner"`:** escalates to the Owner (`status: "hold"`) if product intent must change.
   * **Intra-session hard-cap termination (`trigger: session_cap`):** if a session is killed mid-execution by the wall-clock supervisor (`timeout -k 15s`) or supported native turn/token/cost hard caps before emitting a closure, `actl` increments `hard_caps_tripped`, consumes an attempt (leaving `closures_submitted` unchanged), synthesizes the escalation record from `state.json`, and routes it per §6.3.

### 5.5 Phase 3 Verification: Closure Guards, Fail-Fast Offline Run & Gated Live Run

1. **Closure guards `G1–G6` (before the Offline Run):**
   * **Oracle pre-flight hash check (`G1`):** `actl` (`verifier`) verifies the active oracle in `records/` against `contract-{seq}.json`. A mismatch is a system integrity error: `actl` raises a `halt` (`reason: integrity_mismatch`) and consumes no Implementer attempt.
   * **Closure guards:** upon Implementer → `actl` closure, and before executing untrusted Implementer code, `actl` locks `implementer-outputs/` to `chmod 0750`, validates `closure-{seq}.json` and the `blocked` preconditions (`G2`), fetches `wip/{seq}` into `workspaces/verify-implementer/`, checks `git diff {base_sha}..HEAD` against `ALLOW`/`FROZEN` scope (`G3`), verifies legacy test function counts if any `test/{file}` was unfrozen (`G4`), runs the credential/secret leak scan (`G5`), and runs the forbidden-call lint (`G6`).
   * **Mandatory self-tests:** every guard/scanner must pass its own built-in self-test (verifying it catches known synthetic leaks and forbidden calls) before evaluating the worktree, so a broken lint cannot silently pass before reaching Live Run approval.
2. **Fail-fast Offline Run (`O1` first, `O2` second, executed as account `implementer`):** once the guards are green, `actl` checks out the candidate commit in `workspaces/verify-implementer/`, stages a temporary copy of the oracle readable by `implementer`, and spawns the verification runner as `sudo -u implementer` with a private `/tmp` (`unshare -p --kill-child` / `PrivateTmp=yes`) and credentials blanked:
   * **`O1` (fast feature check):** executes the oracle's `proofs/*.sh` and `probe.sh` first so feature errors fail within seconds.
   * **`O2` (regression armor):** immediately executes the target repository's existing Test suite (`test/`) to guarantee zero regressions against prior specs.
   * **Post-run cleanup:** regardless of exit code, `actl` runs `sudo -u implementer pkill -9 -u implementer`, deletes the staged oracle copy, and wipes the private `/tmp` so no background process spawned during testing survives into later runs.
   * When both `O1` and `O2` exit `0`, `actl` writes the composite green `ev-{seq}.json` (`steps[]`) and stamps the `Offline Run` column (with `ev` hash and head SHA) in `checklist.md`.
3. **Gated Live Run (`L`; `live_run: none | required`, `approval_live_run: architect | owner`; unattended `"auto"` approval is prohibited):**
   * **Authority gate (post-Offline green):** once the Offline Run exits `0` on `{head_sha}`, `actl` pauses before injecting live secrets:
     * `approval_live_run: architect`: the Owner has signed `sprint.hmac` (over `sprint_tag || sprint_sha256`), proving the delegation covers this exact policy. After the Offline Run passes, `actl` invokes the Architect with the green Offline `ev-{seq}.json` and the candidate diff (`git diff {base_sha}..{head_sha}`, plus the `Modified Legacy Tests` diff if any `test/{file}` was unfrozen). The Architect writes `architect-outputs/live-decision.json` (`decision: "approve_live" | "reject_live"`, bound to `contract_sha256` and `head_sha`); `actl` stores an audit copy as `runs/live-decision-{seq}.json`.
     * `approval_live_run: owner`: `actl` sets `status: "hold"` and notifies the Owner, who reviews the diff and signs `live-decision.hmac` over `sprint_tag || contract_sha256 || head_sha`.
   * **Root-owned privilege-dropping wrapper (`/usr/local/bin/actl-live-run`):** live credentials are stored in `/etc/actl/live.env` (`owner: root:root`, `chmod 0400`) and the Owner's HMAC verification key in `/etc/actl/owner.key` (`owner: root:root`, `chmod 0400`), never inside any agent account or human Owner home directory. `actl` is granted a narrow sudoers rule (`actl ALL=(root) NOPASSWD: /usr/local/bin/actl-live-run`). `actl` invokes `sudo /usr/local/bin/actl-live-run {sprint_tag} {head_sha}`, which:
     1. Verifies the approval path for the active mode: `sprint.toml` states `live_run = required`; in `architect` mode, `sprint.hmac` is valid against `/etc/actl/owner.key`, and `architect-outputs/live-decision.json` is owned by account `architect` and matches `contract_sha256` and `{head_sha}`; in `owner` mode, `live-decision.hmac` is valid. Any mismatch exits `1` and is recorded as a `halt` (`reason: wrapper_rejected`).
     2. Loads the allowlisted secret environment variables from `/etc/actl/live.env` into process memory, and
     3. Executes inside `unshare --pid --mount --fork --kill-child` (mounting a private `/tmp`) and drops privileges permanently via `setpriv --reuid=implementer --regid=implementer --init-groups` to execute the stage-agnostic `proofs/*.sh` and `probe.sh` inside `workspaces/verify-implementer/`, followed by the cleanup rule of §1.5. Because no persistent path is trusted for verification and `implementer-outputs/` is locked to `chmod 0750`, the outbox lock is what is read-only during verification.
   * **Secret scrubbing & failure routing (`trigger: "live_failed"`):** `actl-live-run` replaces any literal value present in `/etc/actl/live.env` with `[REDACTED]` before emitting `runs/ev-{seq}.json`. If a Live Run exits ≠ `0`, it consumes one `attempts.live`, `actl` sends an immediate non-blocking alert to the Owner, and routes the escalation record (`trigger: "live_failed"`) to the **Architect** (never directly to the Implementer) while live attempts remain. The Architect resolves with `grant_attempts` (Implementer), `reopen_oracle`, or `retry_live` (one extra live attempt for environment flakes); the loop then repeats Architect action → Offline green again → Live Run again. When a Live Run fails and `attempts.live` has reached `max_attempts.live`, `actl` halts (`status: "hold"`) and routes to the Owner. There is no separate recovery counter.
   * **Success:** when green, `actl` stamps the `Live Run` column (verifying the head SHA matches the `Offline Run` column), marks requirement rows `Status: done` in `checklist.md`, and pins `{contract-tag}` in `repos/target-repo/.git`.

### 5.6 Phase 4 Closeout: Curator Curation, Anti-Slop Proof Graduation & Owner Push (`curator`)

1. **Step 1: Curator curation & proof-to-test graduation (account `curator`):**
   * Once Phase 3 is green, zero `open` rows remain in `checklist.md`, and `{contract-tag}` is pinned, `actl` checks which killed oracle mutants fail `git apply --check` against `{contract-tag}`, stages `spec`, `approved.diff`, `proofs/*.sh`, any non-applying `mutants/*.patch`, and `context.json` (`notes[]`, `backlog[]`, `waived_mutants[]`, and `modified_legacy_tests`) into `curator-inputs/` (`chmod 0750`, `actl:curator`), initializes the standalone clone `workspaces/curator-worktree/` (`chmod 2770 curator:curator`, `umask 0007`) at `{contract-tag}`, and invokes the Curator (`sudo -u curator`).
   * The Curator consumes `curator-inputs/` to author `diff-risk-review.md` (including a mandatory `Waived Mutants & Residual Risk` section if any mutant was waived, a mandatory `Modified Legacy Tests` section containing the verbatim `git diff {base_sha}..{contract-tag} -- test/` extract if any legacy test file was unfrozen in Phase 2/3, and a `Same-Family Pairs` section when applicable), merge the Implementer's backlog items with its own candidates into `backlog-proposal.md` (containing `none` if empty), author `curation-plan/mutants-rebased/{name}.patch` for any staged non-applying Phase 2 mutant, and craft ordered patch/message pairs (`plan/NN-{slug}.patch` and `plan/NN-{slug}.msg`).
   * **Unconditional proof-to-test graduation (strictly new test files on Commit N):** regardless of whether existing legacy tests were unfrozen and updated in `01 .. N-1`, the Curator never modifies existing test files on Commit N. It unconditionally translates all black-box `proofs/*.sh` into new native repository test files inside `test/**` as a dedicated final commit (`plan/NN-graduate-tests.patch` + `.msg`), documenting each graduated proof via a `Graduated-Proof: {proof_script} → {test_file}::{test_name}` trailer in `NN-graduate-tests.msg`.
2. **Step 2: Edge 1 (Curator → `actl`) mechanical policy, tree-equality & anti-slop verification.** `actl` (`verifier`) evaluates `curator-outputs/curation-plan/` in `workspaces/verify-curator/` across six deterministic checks:
   1. **`E1.1` Artifact, trailer & disclosure regex check:** verifies that `diff-risk-review.md`, `backlog-proposal.md`, and matching `plan/NN-{slug}.patch/.msg` pairs exist; checks subject line format, `Spec:` and `Oracle:` trailers on all `.msg` files, a `Graduated-Proof:` trailer for every oracle `proofs/*.sh` script in `NN-graduate-tests.msg`, the `Waived Mutants & Residual Risk` section if any mutant was waived, the `Modified Legacy Tests` section if any legacy test was unfrozen in `scope.txt`, and the `Same-Family Pairs` section if `sessions.tsv` shows a shared `model_family` for an **F** pair.
   2. **`E1.2` 100% feature tree-equality (`01 .. N-1`):** ephemerally applies feature commits `01 .. N-1` in lexicographical order via `git apply --index && git commit -F` onto `base_sha` and verifies 100% bit-for-bit git tree-equality against `{contract-tag}` across all paths (`git diff {contract-tag} HEAD` is empty, zero path exclusions).
   3. **`E1.3` Unconditional strictly new `test/**` files (Commit N):** requires `NN-graduate-tests.patch` to be present and add ≥ 1 file under `test/**` on every sprint without exception. After applying it, `git diff --name-only --no-renames --diff-filter=a {contract-tag} HEAD` must be empty (lowercase `a` excludes Added files, so any modified, deleted, or renamed file fails; `--no-renames` prevents Git copy/rename heuristics from falsely flagging boilerplate) and every path in `git diff --name-only {contract-tag} HEAD` must match `test/**`.
   4. **`E1.4` Null-Base Red, per graduated test (blocks trivial/no-op tests):** in a clean checkout at `base_sha` (without feature commits `01 .. N-1`), `actl` applies only `NN-graduate-tests.patch` and runs each newly added test individually as account `curator`. At least one new test must fail. A graduated test that passes at base is allowed only if `E1.5` shows it failing under at least one mutant that `coverage.md` maps to its originating proof.
   5. **`E1.5` Non-vacuous mutant-kill transfer (closes the `ImportError` / vacuous-test bypass):** on the full Commit N tree (feature commits `01 .. N-1` + `NN-graduate-tests.patch`), `actl` iterates through every killed oracle mutant. If the original patch applies cleanly (`git apply --check`), `actl` uses it; if it fails due to implementation divergence between `solution_key.patch` and Commit N, `actl` requires `curation-plan/mutants-rebased/{name}.patch` and verifies that the rebased patch modifies only production files outside `test/**` and passes `git apply --check` on Commit N. For every non-waived mutant, `actl` applies the patch and executes the newly added `test/**` files as `curator`; the graduated native tests MUST kill 100% of non-waived mutants (`exit` ≠ 0). Together with `E1.4`, every `Graduated-Proof` test is red at base or kills a mapped mutant, so a test that merely imports a new symbol cannot pass.
   6. **`E1.6` Full Test suite green:** on the clean Commit N tree, `actl` executes the repository's full Test suite as `curator` and verifies it exits `0`, followed by `sudo -u curator pkill -9 -u curator` and private `/tmp` cleanup.
3. **Step 3: Edge 2 (`actl` → Owner) approval, final commit & Owner push:**
   * **Dashed edge (`actl` → Owner):** Owner approval of the curation plan is unconditional (there is no `architect` or `auto` approval mode). Once Edge 1 passes, `actl` marks `status: "hold"` in `state.json` and notifies the Owner via the Notification Adapter. If Edge 1 fails, `actl` loops back to the Curator, bounded by `max_attempts.curator` (escalating to the Owner on `attempts_exhausted`). If the Owner requests changes on Edge 2, revisions loop back to the Curator uncapped by budget counters.
   * **Final commit, backlog storage & push:** once approved, `actl` applies the verified `plan/NN-{slug}.patch` + `.msg` commit chain (feature commits + graduated `test/` commit) to `repos/<repo>/`, commits the final stamped `specs/{sprint_tag}/checklist.md` to `records/` (`runs/verification-*.json` remain untracked), presents `backlog-proposal.md` items for the Owner to curate into the repo backlog, and the human Owner pushes to remote trunk.

---

## 6. Budgets & Escalation

### 6.1 Intra-Session Hard Caps vs. Inter-Session Attempt Counters

Both classes are resolved into `sprint.toml` (frozen baselines) and tracked in `state.json` (consumption and grants); the contract references `sprint_sha256` only. The effective limit of any budget is baseline plus granted increments.

```text
effective_limit(dimension, sprint.toml, state.json) -> (limit, mechanism, on_exceed)
```

1. **Intra-session hard caps (`[hard_cap.{persona}]` → increments `hard_caps_tripped` → triggers `session_cap`):**
   * Govern a single CLI invocation: `wall_clock` (`timeout -k 15s {limit}` inside `{session}.run.sh`), `turns`, `tool_calls`, `tokens`, and `cost_usd`.
   * **Orthogonal watchdog counter (`hard_caps_tripped`):** when a session is terminated mid-execution by `wall_clock` or a native engine flag before emitting a handoff artifact (`last_closure: null`), `actl` increments `hard_caps_tripped` without incrementing `closures_submitted` or satisfying `min_attempts_before_block`, consumes one attempt of the stage, and routes the `session_cap` escalation per §6.3.
   * **Native enforcement & fail-closed compatibility halt (MVP):** whenever a CLI engine natively supports a configured `hard_cap` dimension, `dispatch.py` passes and enforces the native flag directly. If a non-null dimension (e.g., `turns`, `tool_calls`, `tokens`, or `cost_usd`) is configured and the target persona's CLI adapter cannot confirm native enforcement support, `actl` refuses to start the session (fail-closed), writes `status: "hold"` to `state.json`, raises a `halt` (`reason: unsupported_cap`), and notifies the Owner identifying the exact unsupported `(cli_engine, dimension)` pair, so the Owner can either omit that dimension (relying on `wall_clock` + post-run `sessions.tsv` telemetry) or switch the persona's CLI engine.
   * **Post-MVP roadmap note (stream-parsed hard caps):** in a post-MVP release, `dispatch.py` will add real-time JSONL/`pipe-pane` stream monitoring to enforce `turns`, `tool_calls`, `tokens`, and `cost_usd` via `SIGTERM`/`SIGKILL` across CLI engines that lack native flags, without halting on startup.
   * **Sub-agent spawner prohibition (Invariant S):** every CLI adapter mechanically disables native in-process sub-agent tools (`AgentTool` / sub-task spawners) so no persona can spawn an in-process child agent inside the same account. Every persona transition must return to `actl`.
   * **Universal wall-clock & `tmux` supervisor:** every CLI engine executes inside a detached headless `tmux` session (`spawn_detached_session` under `loginctl enable-linger`) wrapped in `{session}.run.sh` with `umask 0007`, `timeout -k 15s {limit}`, `remain-on-exit off`, and `trap cleanup EXIT`.
2. **Inter-session attempt counters (`[max_attempts]` → triggers `attempts_exhausted`)** count dispatches of a budgeted stage within an epoch. Every dispatch consumes one attempt, whether or not it yields a valid artifact (`oracle-draft/`, `closure-{seq}.json`, `curation-plan/`). The Architect and the Owner are not attempt-budgeted.
   * `oracle`: Challenger dispatches in Phase 2 (the Architect always gets its post-qualification review turn before exhaustion fires).
   * `implementer`: Phase 3 Implementer ↔ `actl` implementation loop, paired with `closures_submitted` ≥ `min_attempts_before_block` for `blocked` claims.
   * `live`: Live Run executions. A failure beyond `max_attempts.live` halts to the Owner (`status: "hold"`). The old default of one recovery retry corresponds to `max_attempts.live = 2`.
   * `curator`: Phase 4 dispatches caused by automated `actl` rejections on Edge 1; human Owner revisions on Edge 2 are uncapped.
   * Exhaustion occurs when a red result leaves no attempts. Granted attempts are recorded in the escalation `resolution`.

### 6.2 CLI Engine Hard-Cap & Isolation Capabilities (Status as of October 2026)

| CLI Engine | Headless / Hard-Cap Flag Support | Operational & Adapter Rules (`dispatch.py`) |
| --- | --- | --- |
| **Anthropic Claude Code (`claude`)** | Supports `--max-turns {N}`, `--max-budget-usd {amount}`, and `--disallowedTools`. | Force print mode (`-p`) and pass `--disallowedTools Agent` in the adapter, because outside print mode budget flags may be silently ignored and `AgentTool` spawns in-process sub-agents under the same account. Use `--resume {session_id}` for the persistent Architect thread (with the vault copy in `records/` between turns); retain the headless `tmux` + `timeout -k` supervisor. |
| **OpenAI Codex CLI (`codex`)** | Turn and step caps for `codex exec` default to unlimited in stable releases; token budget landed in alpha in Aug 2026. | Do not rely on unverified turn/spend caps; if non-null `turns`/`tool_calls`/`cost_usd` are set in `hard_cap` for a `codex` persona in MVP, `dispatch.py` halts (`status: "hold"`, `halt: unsupported_cap`) and informs the Owner to omit unsupported dimensions (enforcing `wall_clock` via headless `tmux` + `timeout -k` + API spend gateway + `sessions.tsv` telemetry). |
| **Google Antigravity CLI (`agy`)** | Headless flags include `--print-timeout`; no native turn or USD spend cap flags in current CLI releases. | `--print-timeout` returns partial output rather than killing the run, so it cannot serve as a hard cap. Halt (`status: "hold"`, `halt: unsupported_cap`) and inform the Owner if non-null `turns`/`tokens`/`tool_calls`/`cost_usd` are configured in MVP; rely on headless `tmux` + `timeout -k` supervisor for `wall_clock`. |
| **Cursor Agent CLI (`agent`) / OpenCode (`opencode`) / Claw Code** | Headless flags vary; sub-agent tools run inside the parent process account by default. | Disable internal sub-agent tools in tool config; treat native turn/spend caps as unconfirmed unless verified by adapter self-test (fail-closed halt with Owner notification in MVP; stream-parsed enforcement post-MVP); rely on headless `tmux` + `timeout -k` supervisor and post-run telemetry. |

### 6.3 Escalation Routing

Escalation routing is a pure function of recorded values (read from `sprint.toml` and `state.json` in every phase), so a decision can be reproduced from the files:

```text
route(trigger, stage, sprint.toml, state.json) -> (to, legal_actions)   # logged with its inputs
```

| Trigger | Stage | Routes to | Legal actions |
| --- | --- | --- | --- |
| `attempts_exhausted` | `oracle` | Architect | `grant_attempts`, `waive_mutant` (only if `oracle_review.failing_checks` is empty), `escalate_owner` |
| `attempts_exhausted` | `implementer` | Architect | `grant_attempts`, `reopen_oracle`, `escalate_owner` |
| `attempts_exhausted` | `curator` | Owner | `grant_attempts`, `abort` |
| `blocked` | `implementer` | Architect | `update_scope`, `reopen_oracle`, `grant_attempts`, `escalate_owner` |
| `session_cap` | `oracle`, `implementer` | Architect | `grant_attempts`, `escalate_owner` |
| `session_cap` | `architect`, `curator` | Owner | `grant_attempts`, `escalate_owner` |
| `live_failed` | `live` | Architect, plus a non-blocking Owner alert; Owner (hold) once `attempts.live` reaches `max_attempts.live` | `grant_attempts` (implementer), `reopen_oracle`, `retry_live` (+1 live attempt, for environment flakes) |
| `halt` | `actl` (`integrity_mismatch`, `wrapper_rejected`, `unsupported_cap`, `architect_unavailable`) | Owner | `resume`, `abort` |

* **Owner-routed cases are fixed:** the Architect's `escalate_owner`, a failed or capped Architect session, `live_failed` after the live budget, `attempts_exhausted` at the Curator, and every `halt`.
* **`owner_review_triggers`:** if the Architect's `resolution.action` is listed in `sprint.toml`, `actl` sets `status: "hold"` and applies the action only after the Owner's countersignature is recorded in `resolution.owner_countersign`. Listing `waive_mutant` gives the Owner authority over mutant waivers.
* **Notification Adapter:** time of day and Owner availability affect only delivery (terminal, Telegram/webhook, reminders and `escalation_alerts_sent`), never who decides. They apply strictly when targeting the human Owner.
* **Safe default on no response (`hold`):** if an Owner escalation receives no response within the availability window (or if a synchronous Architect invocation fails), the mandatory safe default is `hold` (write `status: "hold"` in `state.json` and await human Owner intervention), never auto-approve.
* **Hold scope:** `hold` applies strictly to the actionable party's decision; an unanswered informational Owner notification (such as the initial parallel alert on `live_failed` while live attempts remain) never blocks a run that the Architect is authorized to resolve.

---

## 7. Open Architectural Decisions Gating `graph.toml` & View Generation

1. **Work items as true graph nodes: decided.** One node per spec. The closure, evidence, tag, checklist, state, and contract schemas are all scoped to a single node. Larger work is expressed as several sprints linked by the optional `after = ["{sprint_tag}"]` field in `sprint.toml`. Parallel work-item nodes (concurrent Implementer loops on disjoint `ALLOW` scopes) remain out of scope until those schemas are re-scoped.
2. **Open: `graph.toml` schema & `.mmd` generator pipeline (Views 01–04).** Finalize the canonical `graph.toml` node/edge schema (including installation defaults for every `sprint.toml` key) and the deterministic generator script that emits the primary Persona Graph (01) alongside derived Views 02 (Swimlane Sequence), 03 (Context and Session Views), and 04 (`actl` Verification & Guard Map).

---

## Appendix A: Revision Log (non-normative)

This appendix records every removal, replacement, and consolidation made relative to the 20:05 draft, and why. Content not listed here was carried over with only mechanical renames. A sentence-level comparison of the two documents (417 comparable statements in the 20:05 draft) was run after drafting; every statement without a close counterpart was reviewed, and each is accounted for by an entry below or was restored (the `challenger-worktree` scratch clone and the "never reset" rule for `seq` were found missing and restored).

### A.1 Removed or replaced mechanisms

| # | Removed or replaced (20:05 draft) | Replacement | Justification |
| --- | --- | --- | --- |
| R1 | Inode re-creation of the spec and key as `actl:plan` `0440` inside `0750 plan-box/`; `unlink()` of `plan`-owned originals; `0750`/`0770` toggling of `plan-box/` (§1.3, §1.5, §3.1, §5.2) | Separate `architect` and `challenger` accounts; read-only `{role}-inputs/` staged by `actl` | The trick existed only because two personas shared `UID plan`. With one account per persona, ordinary permissions give the same guarantee, enforce Invariant C at the OS level, and remove several failure-prone `chmod` sequences. |
| R2 | Removing `architect_thread.jsonl` from `~plan/` before Challenger turns and restoring it before Architect turns (§1.3, §5.2) | Thread stays in `profiles/architect`; a vault copy is kept for recovery only | Same cause as R1. The Challenger can no longer reach the thread, so there is nothing to remove or restore. |
| R3 | Shared `workspaces/plan-worktree/` | `architect-worktree/` and `challenger-worktree/` | Two personas, two scratch clones; sharing one was another cross-persona channel. |
| R4 | One `workspaces/actl-verify/` owned by `<role_uid>:actl` | `verify-challenger/`, `verify-implementer/`, `verify-curator/` | A single directory whose owner flips per role leaves residue between roles and requires gid `actl`. |
| R5 | Group `actl` on all workspaces (`chmod 2770 {role}:actl`) and `setpriv --regid=actl` | Per-role groups; `actl` is a member of each; `--regid=implementer` | Under the old scheme the live-run process (gid `actl`) could reach every role's workspace, defeating the isolation the section claims. |
| R6 | `repos/target-repo` as `chmod 700 actl:actl` | `0750 actl:cloners`, write by `actl` only | The old mode made `sudo -u {role} git clone --local` impossible. Oracle material never lived in `target-repo`, so exposing it does not weaken **P**. |
| R7 | `live-delegation.hmac` (signed "before the spec", "at Phase 1 close", over `sprint_id \|\| base_sha \|\| "architect"`) | `sprint.hmac` over `sprint_tag \|\| sprint_sha256`, required only for `live_run = required` with Architect approval; decision bound to `contract_sha256 \|\| head_sha` | The need was real (the root wrapper must not trust the Architect alone), but the token had three contradictory descriptions and did not bind the contract or policy. |
| R8 | `mutant_waiver_authority` (8 occurrences) | `owner_review_triggers` containing `waive_mutant` | One mechanism for every Architect action the Owner wants to countersign, instead of a knob for a single action. |
| R9 | `approval_archivation_plan` (5 occurrences) | Unconditional Owner approval | The key had a single legal value (`owner`); the other values were declared prohibited. A setting with one legal value is not an option. |
| R10 | "Premise 7" label and the "Premise 5" reference | Invariant **C**; "Premise 5" dropped | Premises 1–4 and 6 were never defined, so the references were orphans from an earlier iteration. The content of Premise 7 is preserved verbatim as **C**; the Premise 5 mention only pointed to `probe.sh` behavior that §5.2 already describes. |
| R11 | "Stage 2a/2b" and "Step 1/2/3" labels, which were reused across phases and used in Phase 2 before being defined | Check IDs `Q1–Q5`, `G1–G6`, `O1`, `O2`, `L`, `E1.1–E1.6` | One permanent ID per check removes ambiguity; no check was dropped. |
| R12 | `risk tier`, `time of day`, and `Owner availability` as routing inputs of `escalation_policy()` | `route(trigger, stage, sprint.toml, state.json)`; time and availability affect notification delivery only | The inputs were never defined or recorded, so routing could not be reproduced from the files. |
| R13 | Six trigger names `retries_oracle_exhausted`, `retries_implementer_exhausted`, `retries_archivist_exhausted`, `live_run_failed`, `hard_cap_exhausted`, `blocked` | `attempts_exhausted` (+ `stage`), `blocked`, `session_cap`, `live_failed`, `halt` | Triggers and stages were conflated. The new set also gives Owner-only stops (integrity mismatch, wrapper rejection, unsupported cap, Architect unavailable) a record, which the old enum lacked. |
| R14 | `retries_*` counters counting only sessions that emitted a valid artifact | `max_attempts.*` counting every dispatch | The old rule left a session that exited without a valid artifact uncounted, allowing an unbounded loop. |
| R15 | `retries_live` "recovery cycle" (default `1`) | `max_attempts.live` (`2` is equivalent); `retry_live` action | A recovery cycle is a loop, not a counter. Only Live Run executions need counting. |
| R16 | Budget block inside `contract-vN.json` ("initial resolved budgets", `solution_key_exposure`, `mutant_waiver_authority`, `live_run`, `approval_*`) | `sprint.toml` baseline; the contract references `sprint_sha256` | Budgets were resolved in `graph.toml`, copied to `state.json`, and copied again to the contract. One frozen source avoids drift. |
| R17 | Versioned names `spec-vN`, `oracles/vN`, `oracle-qual-vN`, `contract-vN` and per-kind `NN` counters (`closure-NN`, `ev-NN`, `escalation-NN`) | `{kind}-{seq}` with a per-sprint `seq` in `state.json` | The same `vN` meant different things (a Phase 2 key fix and a Phase 3 scope fix could both produce `oracle-qual-v2`), and per-epoch counter resets collided with existing `closure-NN` files. |
| R18 | State initialized "at Phase 1 start" under a sprint directory whose name was agreed during Q&A | `actl sprint new` creates the tag, directory, and `state.json` first | The old order was circular and did not support an externally produced spec. |
| R19 | Architect "curates the repo backlog" (§3.2) | Owner selects backlog items (unchanged in §1.4 and §5.6) | The two statements contradicted each other, and the Architect is never invoked in Phase 4. |
| R20 | Null-Base Red sentence "If it fails at collection/compile/import time ..., Check 5 must execute" | Per-test rule in `E1.4` plus `E1.5` | `E1.5` already runs unconditionally, so the conditional could never change the outcome. The per-test rule closes a real gap: one failing test used to satisfy the check for all of them. |
| R21 | Legacy test-count re-check inside Phase 4 (`E1.1` "plus test function count conservation") | `G4` in Phase 3 only | The same diff is proven identical by `E1.2`, and `G4` already enforces the count on it, so the re-check cannot change the result. |
| R22 | `solution_key_divergence` required for every `blocked` closure under `full` | Required only when `blocking_step` cites an `O1` proof step | Scope, test, and architectural blocks have no requirement to cite, so the old rule contradicted the permitted `blocking_step` values. |
| R23 | Oracle-exhaustion example showing `closures_submitted: 3` | `attempts: {used: 3, max: 3}`, `closures_submitted: 0` | `closures_submitted` is a Phase 3 counter and the example had no closures. |
| R24 | "Control edges are never dashed" (§1.2) | Same rule with one exception: human-acceptance edges stay dashed | The old rule contradicted the dashed `actl` → Owner edge defined in the same section. |
| R25 | Mandatory cross-family wording for Challenger and Archivist | Preferred (**F**), with `model_family` logging and `Same-Family Pairs` disclosure | Mandatory diversity cannot be guaranteed by deployment; disclosure is consistent with how residual risk is handled elsewhere. |
| R26 | Persona and path names `plan`, `impl`, `ship`, Archivist, `archivation-plan`, `ship-inputs`, `work-order`, `closures/`, `wip-attempt-N` | `architect`/`challenger`, `implementer`, `curator`, Curator, `curation-plan`, `{role}-inputs/`, `{role}-outputs/`, `implementer-{seq}` | One account per persona named after it; `arch` would have collided with Archivist, hence Curator. The mailbox is symmetric for every role. |
| R27 | Text in §1.1, §1.4 and §6.3 enumerating escalation triggers and Owner routes in prose | One routing table in §6.3, referenced elsewhere | The prose lists had drifted apart (§6.3 listed risk tier; §1.1 and §1.4 did not). Every route still exists in the table or in the fixed Owner-routed list. |
| R28 | Phase 4 Edge 1 described in §1.6 (4 checks), §3.2, §4.4, and §5.6 (6 checks) | §5.6 is normative; other sections point to `E1.x` | The copies used different numbering and wording. All check logic, including the `--no-renames --diff-filter=a` mechanics, is preserved in §5.6. |
| R29 | "Open decision: work items as graph nodes" | Decided: one node per spec; `after` field for dependent sprints | All schemas (closure, evidence, tag, checklist, state, contract) are single-node. This decision was part of the agreed consolidation; revisit it if you want parallel work items. |

### A.2 Added (not present in the 20:05 draft)

`sprint.toml` and `actl sprint new` (including imported-spec intake and the completeness gate), the mandatory explicit `live_run` choice, `owner_review_triggers` and Owner countersignature, `max_epochs`, per-persona `[hard_cap.*]` in the sprint policy, the `halt` record, the unified escalation routing table with `legal_actions`, the check-ID table, the invariants table, `scope.txt` precedence rules, the mutant → proof mapping in `coverage.md` with the per-test `E1.4`/`E1.5` rule, the `Same-Family Pairs` disclosure, the residual-risk statement in **P**, and the `retry_live` and `abort`/`resume` actions.

### A.3 Layout Transition (memo 2026-10-25)

| # | Item | Replacement / Revision | Justification |
| --- | --- | --- | --- |
| L-1 | Three directory lifetimes | `records/` is STORAGE (git, 700); `sprints/` is TRANSIENT; `profiles/` is PERSISTENT; `repos/` holds target repositories | Isolates long-term storage from working memory and per-account CLI state. |
| L-2 | Directory naming | `repos`, `records`, `sprints`, `mailboxes` (`inbox`/`outbox`), `workspaces`, `profiles`, `tools`, `signoffs` | Aligns naming with function; mailboxes is symmetric IPC. |
| L-3 | Closeout archive policy | Archive essential receipts (`sessions.tsv`, `qualification-NNN.json`, `verification-NNN.json`, `closeout.md`) to `records/<repo>/<tag>/closeout/` and delete `sprints/<repo>/<tag>/` | Keeps storage clean while preserving complete audit trail in 700 records. |
| L-4 | Courier transport | UTC-stamped drawer `{stamp}__{repo}__{tag}__{role}-{n}__{purpose}` under `ACTL_COURIER_DIR`; move not copy | Sync is transport, not storage; one drawer per turn. |
| L-5 | Artifact renames | `ev-NNN.json` -> `verification-NNN.json`, `qual-NNN.json` -> `qualification-NNN.json`; kinds `verification` and `qualification` | Clear, self-documenting terminology across verifier, replay, and reconstruct. |
| L-6 | Process tools | `tools/` at top level holds process scripts (`mutate.py`, `unfiles.py`); joins PB-2 immutable list | Separates process tools from product code and keeps them tamper-proof. |
| L-7 | Signoffs | `docs/plan/signoffs/` holds judgment-based acceptance records | Distinguishes mechanical receipts from human / independent review sign-offs. |
| L-8 | Profiles | `profiles/<persona>` holds CLI config, login, transcripts, persistent thread; `HOME` points here; `actl init` writes `profiles/README.md` | Preserves persona login/CLI state across turns without conflating state with instructions. |
| L-9 | Root naming | `ACTL_ROOT` is the universal root name; `/srv/agent-graph` is an example value | Eliminates hard-coded root paths. |
| L-10 | Layout repo scoping | `Layout(root, repo="target-repo")`; `repo` field in `sprint.toml` and `state.json`; wrong-repo guard raises integrity error (exit 3) | Multi-repo support without signature churn; prevents cross-repo state corruption. |
| L-11 | Revisit Stage 4 | Revisit `Layout(root, repo)` vs explicit `repo` parameter at Stage 4 (O-16) | Allows evaluating repo scoping ergonomics before finalizing Stage 4 multi-account architecture. |
| DC-A2 | Profile invariant and closeout spelling | `profiles/<role>` is persistent non-authoritative HOME (`0755`); outbox lock is the verification read-only path; `closeout.md` item 3 uses `hardcap_stripped` | Delta-challenge DC-7/DC-8; memo section 5 and L-8 win. |
