# actl_Build_Plan-Stages0to2 — Incremental Build Plan for `actl` (main document, §0–§4)

**Author:** Vela (independent planner). **Date:** Wednesday, October 14, 2026. **Companion file:** `actl_Build_Plan-Stages0to2_addendum.md` (§A–B, §5–§12).
**Audience:** (a) the Owner (Oliver); (b) the spec-writing and proof-writing agents who receive a handoff request based on this document.
**Inputs reviewed:**

| Short name | File | What it is |
|---|---|---|
| Design | `actl_Design.md` (revision 2) | Normative long-term design: `actl` + 4 personas, invariants S/C/P/F, checks Q1–Q5, G1–G6, O1/O2/L, E1.1–E1.6 |
| Prompt | `Increm_proto_Oct181003.md` (initial prompt) | The Owner's question plus a full dump of the current `atools` repo |
| My | First agent response inside the Prompt file ("Temptative answer 1") | 6-stage plan (Stages 1–6) |
| Chi | `Increm_proto_Oct181003_ag2.md` | Second agent response, 5-stage plan (Stages 0–5) plus design-doc corrections |
| Vela | this document | Independent plan, Stages 0–6 |

**Terminology (read once, applies everywhere).**
- **Stage** = a step of *this build plan* (Stage 0, 1, 2, ...). My and Chi also use "Stage" for their own plans; where numbering differs, the text says whose Stage is meant.
- **Phase** = a step of the *runtime lifecycle* defined in the Design (Phase 1 intake, Phase 2 oracle, Phase 3 implementation, Phase 4 closeout). Phases are what we are building; Stages are how we build it.
- `§n` always refers to a section of the Design unless the text says "this document". Check IDs (`Q1–Q5`, `G1–G6`, `O1`, `O2`, `L`, `E1.1–E1.6`) and invariants (`S`, `C`, `P`, `F`) are used exactly as the Design defines them.
- **MUST / SHOULD / MAY** are used in the RFC 2119 sense in the numbered requirements.

**Document structure.** Stages 0–2 are specified at full detail in the companion addendum (§5 Stage 0, §6 Stage 1, §7 Stage 2). Stages 3–6 are summarized in §8 of the addendum, together with the agreement and disagreement table against My and Chi. Section numbering continues across the two files, and the handoff agents MUST read both.

---

## 0. How the handoff agents must use this document

Each handoff agent receives this document, its addendum, the Design and the `atools` repo. Their job, per Stage, is to produce two things:

1. **A Stage specification** (`spec-S{n}.md`): expands every numbered requirement `S{n}-R{k}` of the addendum into unambiguous, testable language. It MAY add requirements but MUST NOT delete or weaken one. Every requirement in the spec keeps the ID given here.
2. **A proof set** (`proof/stage{n}/*.sh`, plus pytest unit tests in `test/actl/`): executable checks, one or more per requirement, following the project's own proof convention (Design §2.1: a proof is a script that exits `0` on pass and `1` on fail, printing a line that starts with `FAIL:` on failure). The proof obligations `P-S{n}-xx` in the addendum are the minimum; agents MAY add more.

Rules for the agents:
- Where the addendum says **DECIDED**, do not reopen it. Where it says **OPEN**, propose a concrete answer in the spec and flag it in a section titled `Proposed decisions`.
- Do not assume anything about the repo that is not stated in §2. If you need a fact (a flag, a path, a version) re-check it in the repo and record what you saw.
- Proofs must be written against the **golden fixture** (Stage 0, addendum §5.8) so that they can run with no network and no LLM. A proof that needs a live model is a *smoke test* and MUST be labelled `smoke_` and excluded from the gating suite.
- Never edit an existing `atools` file except where a requirement names it. Prefer new files. Every edit to an existing file MUST be a minimal, reversible patch.
- If a requirement conflicts with the Design, the Design wins; report the conflict in `Proposed decisions` instead of resolving it silently.

---

## 1. Why this plan exists (summary of the strategy)

The Design describes a governance system with a deterministic control spine (`actl`), four LLM personas, five POSIX accounts, and many mechanical checks. Building it top-down means nothing is testable for a long time. The Owner's intuition, which this plan adopts, is:

1. Start **inside-out** from the Implementer, because the repo already nearly fits Phase 3.
2. Drive the Architect, Challenger and Curator **semi-manually through ordinary web chats**, with strict payload building (`bundle`), strict parsing (`unpack`) and verification, before any gateway or automation exists.
3. Keep the verification logic (`verify.py`) as a **pure, deterministic, LLM-free library** that is validated against hand-written fixtures first, so that when a model produces something bad, we know the referee is right.

Five working principles follow from this:

- **P1. The manual step is the first adapter.** Every persona is "payload in, parsed files out". A browser tab, `arouter`, and later a detached `tmux` session with `sudo -u` all implement the same contract. Nothing built for the manual path is thrown away (this is also Chi's and My's position).
- **P2. Pure functions, replayable inputs.** Parsing and verification take files in and produce files out. Every raw model response is saved with its hash so any run can be replayed offline.
- **P3. One golden sprint.** A hand-written toy target repo with a complete sprint (spec, key, oracle, mutants, known-good and known-bad implementations) is the test bed for every Stage.
- **P4. Additive, reversible.** `actl` lives beside the existing tools (`src/actl/`, `bin/actl`), reusing their conventions. The existing suite and the compliance audit must stay green after every Stage.
- **P5. Be honest about what local mode enforces.** Until real accounts exist (Stage 4), Invariant `P` is a convention, not a guarantee (§3).

---

## 2. Ground truth: the current `atools` repo and why it must expand

### 2.1 Version and provenance

- `VERSION` in the dump taken for the Prompt reads **`v0.1.0`**. The dump excluded `.git`, `audit/`, `docs/`, `out`, anything starting with `_`, and hidden files. `docs/` holds design and plan documents like this one, so it is irrelevant to the build. The compliance script `audit/atools-compliance_audit.sh` (a 36-point validator per the README) was not part of the dump; the Owner guarantees that subsequent agent runs can access it. Agents MAY therefore rely on it existing, and MUST run it as part of the baseline and of every no-regression check.
- Stage 0 MUST record a **baseline** (addendum `S0-R1`): `VERSION`, `git rev-parse HEAD`, `git status --porcelain`, Python and git versions, which agent CLIs exist (`agent`, `codex`, `claude`, `agy`, `aider`, `vibe`), whether `tmux`, `timeout`, `pytest` exist, and the result of running `proof/run_suite_engines.sh` and the audit script *before any change*.
- The plan assumes the repo is run as `root` on a VPS (`root@MochiClaw:~/atools`) because several modules hard-code `/root/.cursor`.

### 2.2 Inventory and mapping to the Design

| Existing item (v0.1.0) | What it does today | Role in the Design | Action |
|---|---|---|---|
| `bin/arouter` | Tier router (`cheap/balanced/smart` → model via `~/.cursor/arouter-config.json`); `--engine`, `--timeout` with `/usr/bin/timeout --foreground -k`; reads piped stdin and appends it as "Context / Input:"; dispatches to `engines/*.sh`. Its header carries "Mandatory compliance audit anchors" (`--auto-review`, `--trust`) | Seed of `dispatch.py` (§1.3) | Reuse unchanged through Stage 2; extended in Stage 6 |
| `engines/*.sh` (cursor, codex, claude, agy, aider, vibe) | One adapter each; Cursor uses `agent --auto-review --trust`; Claude uses `claude -p ... --dangerously-skip-permissions`; all `exec` in the caller's cwd | Persona runtime adapters | Unchanged now. Claude adapter lacks `--disallowedTools Agent` (Invariant `S`) → Stage 6 |
| `.cursor/skills/atools-repair/SKILL.md` | Tells the agent to read a runbook, edit in scope, **run `bash proof/run_suite_<title>.sh` itself**, fix until PASS | Implementer system prompt | **Not overwritten.** A new skill is added in Stage 1 because the old one violates `P` (the agent would run oracle proofs) |
| `hooks/pre-commit`, `rules/git-safety.md` | Commits only on `wip/*` branches; no push | Matches Implementer branch `wip/{seq}` (§3.2) | Reuse as is |
| `install.sh` | Symlinks, system dispatchers `acheap/abalanced/asmart`, global hook path, merges Cursor allow/deny rules (allows `bash proof/*.sh`, `pytest`, `git commit -m *`; denies `git push*`, `--no-verify`), copies skill, runs suite | Install target for `actl` | Minimal patch to add `bin/actl` symlink and skill copy (Stage 0/1) |
| `proof/run_suite_engines.sh` | Bash `run_check` harness with PASS/FAIL counters and logs under `proof/out/` | Template for `verify.py` runners and for our own gating suites | Pattern reused; file untouched |
| `src/sessions/{cli,reader,storage,renderers}.py`, `bin/asessions` | Reads Cursor transcripts and metadata, estimates tokens and cost | Telemetry source for `runs/sessions.tsv` (§4.1) | Reused in Stage 1 (tripwire) and Stage 6; **hard-coded `/root/.cursor` globs must be parameterized** |
| `src/router/*`, `src/core/*` | TUI and config for tiers | Unchanged | — |
| `bin/asessions` wrapper pattern | `PYTHONPATH=$REPO/src`, `exec python3 src/sessions/cli.py` | Pattern for `bin/actl` | Copied |

Code style observed (follow it): top-level packages under `src/` imported as `from core.x import ...`; plain Python 3; `pathlib`; no third-party dependencies in the shipped tools. New code SHOULD stay stdlib-only; the only permitted extra dependency is `jsonschema` (OPEN O-1 in the addendum).

### 2.3 Why the repo must expand (the gap analysis)

`atools` today is a **launcher with safety rails**: it picks a model, runs one agent session under a watchdog, and keeps commits on `wip/*`. The Design is a **governed pipeline**. The gaps, in order of how soon they bite:

| Gap | Today | Design requirement | First Stage that closes it |
|---|---|---|---|
| Who judges "done" | The agent runs the suite itself (`SKILL.md` step 4) | `actl` runs guards, oracle and repo tests externally after the session; agent sees only `failing_step`/`failing_line` (Inv. `P`, §5.4–5.5) | 1 |
| Typed artifacts | Free text in, free text out | Schema-validated `closure`, `qual`, `ev`, `contract`, `oracle-decision`, `prior_attempt` (§4) | 0 (schemas), 1–3 (use) |
| Identity of things | None | `{kind}-{seq}`, hashes, `base_sha`, contract tag; no "latest" (§4) | 0 |
| Hand-offs between personas | The human copies things | Account-partitioned mailbox `handoff/` with `*-inputs/` and `*-outputs/` and promotion by `actl` (§1.5) | 0 (layout), 2 (bundle/unpack, promote) |
| Persona independence | One session type | Four personas, cross-family preferred (`F`), fresh context (`C`) | 2–3 |
| Mechanical qualification of an oracle | None | `Q1–Q5` with `diagnostic_case` (§5.2) | 3 |
| Attempts, budgets, escalation | Watchdog timeout only | Counters, epochs, escalation router (§5.4, §6) | 4 |
| Closeout | None | Curator plan and `E1.1–E1.6` (§5.6) | 5 |
| Isolation | Single uid, `--dangerously-skip-permissions` / `--trust` | Five accounts, tmux supervision, live-run wrapper (§1.3, §1.5, §5.5) | 4 (first account), 6 |
| Portability | `/root/.cursor` hard-coded | Per-account `HOME` | 1 (parameterize), 4 |

The expansion is *additive*: `src/actl/` is a new top-level package beside `src/router/` and `src/sessions/`. Nothing in the existing tools needs to change for Stages 0–2 except two tiny, reversible edits (installer symlink; optional `HOME`-aware glob helper).

---

## 3. What local mode does and does not enforce (read before writing any proof)

| Item | Stages 0–3 (single uid, local mode) | From Stage 4 / 6 |
|---|---|---|
| Invariant `P` (Implementer cannot read oracle) | **Convention only.** Oracle lives in `actl-repo/` (created `700`), but the agent runs as the same uid and *can* read it. Mitigations: never put oracle paths in any prompt; clone to a workspace outside `ACTL_ROOT/actl-repo`; transcript tripwire (Stage 1, `S1-R10`) flags any access | Real: dedicated `implementer` account (Stage 4); all accounts (Stage 6) |
| Invariant `C` | By discipline: only artifacts in `*-inputs/` are given to a persona | OS-enforced with per-persona `HOME` |
| Invariant `S` (no sub-agents, own session) | Not enforced | Stage 6 (`--disallowedTools Agent`, tmux) |
| Invariant `F` (cross-family) | Recorded by hand: `bundle` asks for the model name; stored per turn | `sessions.tsv` `model_family` |
| Guards `G1–G6`, `O1`, `O2`, `Q1–Q5` | Fully enforced (they are pure logic) | same |

Any spec or proof that claims `P` is enforced in local mode is wrong. Proofs may assert that the tripwire fires; they must not assert isolation.

---

## 4. Stage map

| Stage | Name | Design Phases touched | Output the Owner can see |
|---|---|---|---|
| **0** | Foundations: layout, identity, schemas, golden sprint | all (structure only) | `actl init`, `actl sprint new`, `actl doctor`; a golden sprint that every later proof reuses |
| **1** | Verifier and Implementer loop | 3 | `actl verify-impl` and `actl dispatch-impl`: Implementer runs through `arouter`, verified externally, retry hints produced |
| **2** | Paste bridge and promotion | 1, 2 (transport only) | `actl bundle` / `actl unpack` / `actl promote` / `actl replay`; Architect and Challenger driven by web chats |
| 3 | Oracle qualification (`Q1–Q5`) and lock | 2 | Full Architect ↔ Challenger ↔ qual loop; contract minted |
| 4 | Budgets, escalation, first real account | 3 (control flow) | `route()`; attempt counters; `implementer` Linux account |
| 5 | Curator and `E1.1–E1.6` | 4 | Curation plan verified |
| 6 | Hardening: dispatch, accounts, live wrapper | all | tmux supervision, 5 accounts, `actl-live-run` |

Stages 0–2 are specified at full detail in the addendum (§5–§7). Stages 3–6 are summarized in addendum §8.

*End of main document. Continue with `actl_Build_Plan-Stages0to2_addendum.md`.*
