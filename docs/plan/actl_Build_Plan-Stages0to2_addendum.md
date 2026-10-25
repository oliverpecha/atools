# actl_Build_Plan-Stages0to2_addendum — Addendum to the core document

**Author:** Vela. **Revision:** Wednesday, October 14, 2026; amended Saturday, October 24, 2026 (see Revision log) (measurements from the VPS folded in). **Baseline:** `atools` `main` at `2acaf3c`, `VERSION` v0.1.7 (audit runner `4da9394`; the facts in §B were measured at `a9b3a4e`, `VERSION` v0.1.2, an ancestor).
**Revision log.** 2026-10-24: Stage 0 closed (tag `stage-0-verified`, `VERSION` v0.1.8). Since the lock (2026-10-14): requirements S0-R4..R16 and parts of S1/S2 were tightened (WI-DOCS-3); the baseline moved to `2acaf3c`; sections 5.3, 5.5, 5.9 and 9 were brought in line with the delivered Stage 0; decisions D-22..D-29 were added; open items O-1, O-2 and O-8 were closed; the text of D-21 was corrected because `hooks/commit-msg` now checks the tag (the decision is unchanged). Deviation recorded: Gate D ran after the Stage 0 implementation; from Stage 1 on it MUST run before implementation (section 11.4, step 2). The Stage 1 and Stage 2 requirement changes of 2026-10-18 have not had an independent review yet; they get one in the Stage 1/2 authoring pass.

**Relation to other files**

| File | Role |
|---|---|
| `actl_Design.md` | Broader long-term design. Untouched. Normative when in doubt. |
| `actl_Build_Plan-Stages0to2.md` (core document) | Introduces the migration: handoff rules (§0), strategy (§1), the `atools` ground truth and gap analysis (§2), local-mode honesty (§3), Stage map (§4). Content unchanged. |
| **this addendum** | Everything that detailed and corrected the core: the Stage 0, 1, 2 specifications (§5–§7), Stages 3–6 and the comparison with My and Chi (§8), decisions (§9), handoff checklist (§10), the branch protocol and the path to progress (§11), and the maintenance TODO for the guide (§12). It also carries the facts verified or measured on the VPS (§B). |
| `actl_Guide.md` (formerly `eval-repair-guide_*`) | How agents run `atools` loops to get Stages implemented. Maintained on a schedule (§12). |
| `actl_Handoff_Prompts.md` | Operational, not part of the lock: ready-to-paste authoring and challenge prompts. |

**Reading order for the handoff agents:** core document, then this addendum. **Where they conflict, this addendum wins.** Terminology is as defined in the core (Stage, Phase, `§n` = Design section unless stated, My / Chi / Vela, MUST/SHOULD/MAY), plus: **atools** is the repository and suite name, not a module; its components are `arouter` (`src/router/`), `asessions` (`src/sessions/`), `src/core/`, `engines/`, `hooks/`, `rules/`, skills, `proof/`, `audit/`, `install.sh`; `actl` is a new component added to the same repository.

---

## A. What this addendum changes in the core document

| Core document says | Now |
|---|---|
| Baseline is v0.1.0 / the Oct 4 commits (§2.1) | Baseline is `2acaf3c`, `VERSION` v0.1.7 (modular audit runner adopted in `4da9394`, installed-copy sync checks added), on top of `a9b3a4e`, `5cb7f30` (persistent sessions) and `759a0ca` (explorer). `docs/` and `audit/` are excluded from the dump on purpose; the Owner guarantees the audit script is reachable. |
| `arouter` is a tier router with a watchdog (§2.2) | It also has detached tmux sessions, `ps/attach/logs/kill`, three execution paths, and `src/router/process.py`. Background execution **exists** and is consumed, not built (Stage 6 shrinks). |
| Stage 4 or 6 builds tmux supervision (Stage map §4; My/Chi agreement rows) | Consume the existing layer. One small change is added to Stage 0 (exit-code persistence, S0-R16). |
| Stage map §4 | Same Stages; Stage 0 has two workstreams (0A foundations, 0B exit-code persistence); Stages 1 and 2 run in parallel after Stage 0; see §11. |
| "Existing tools" / "atools change" (various) | Read "pre-existing suite components (`arouter`, `asessions`, engines)" and "a change to a named suite component". |
| Additive-only rule (P4, §1) | Allowed existing-file edits: `install.sh`, `README.md`, `src/router/process.py` (Stage 0B only), and the two `ATOOLS_CURSOR_HOME` edits (Stage 1). |
| Heuristic or unspecified detection of a finished detached run | Deterministic: the exit-code file written by Stage 0B, polled by Stage 1 (S1-R14). |
| Local mode, `P` convention (§3) | Unchanged. |

## B. Verified and measured facts

Sources: shared diffs of `5cb7f30`, `759a0ca`, `a9b3a4e` (code facts); checks run on the VPS `root@MochiClaw` on Oct 18, 2026 (marked **measured**); one sandbox observation (marked **sandbox**, to be re-measured).

| # | Fact | Consequence |
|---|---|---|
| F1 | `arouter` takes the tmux path when `-d` is given **or** stdout is a TTY and the engine is `cursor` (then it auto-streams). Otherwise (non-TTY, or another engine) it runs the legacy foreground `timeout --foreground` and propagates the real exit code | Interactive Cursor runs are tmux-backed too. A harness (non-TTY) MUST pass `-d` for a detached run; without it, it gets a blocking foreground run |
| F2 | `PIPED_INPUT=$(cat)` runs whenever stdin is not a TTY | A harness without input MUST redirect `< /dev/null`, or `arouter` blocks waiting for EOF |
| F3 | Dispatch args are `json.dumps`-serialized (ASCII-escaped) into one `python3 -c` argument, shell-quoted into the runner, then passed as one argument to the engine. **Measured:** a single argument of 131071 bytes is accepted, 131072 is refused (`Argument list too long`) | The 131071-byte single-argument limit applies to the JSON-escaped size; non-ASCII characters expand up to six bytes each. The 100,000-byte ceiling of S1-R9 stands |
| F4 | `LOG_DIR` = `$ATOOLS_LOG_DIR`, else `/root/.cursor/logs` if `/root/.cursor` exists, else `~/.cursor/logs`; `METADATA_DIR` = `$ATOOLS_SESSION_DIR`, else `~/.cursor/sessions`. Per session: `<s>.json`, `<s>.run.sh`, `<s>.log` | Env overrides allow isolated tests and per-account placement |
| F5 | The runner is `execute_work; exit $?` with `trap cleanup EXIT` removing the runner and the metadata; the exit status is stored nowhere | Stage 0B (S0-R16) |
| F6 | The log is produced by tmux `pipe-pane`, attached after session creation; it is the raw PTY stream (ANSI, TUI frames) | `actl` strips ANSI before scanning; a few early bytes may be missed |
| F7 | Every session start runs `loginctl enable-linger $USER` (best effort) | Design §1.3 linger is already in code, so Chi's linger vs `pkill -9 -u` collision is real; tests stub `loginctl` |
| F8 | `ps` lists a tmux session only if it has metadata, a log file, or an `arun-` name | `actl` sessions are started through `arouter`, so they appear |
| F9 | tmux uses its default socket (per uid) | `arouter ps` sees only the caller's sessions (O-12) |
| F10 | `asessions` on a TTY opens an explorer with **active** sessions and the last 5 runs; `rm` removes transcripts and chat/SQLite records only and cannot map a UUID to a session name, so logs and exit files stay | Log retention for `actl` sessions is `actl`'s (§9, D-16) |
| F11 | `arouter` prints help if any argument equals `--help`, `-h` or `help` | An instruction is never exactly `help` |
| F12 | `proof/run_suite_session_persistence.sh` is not stubbed: it needs `tmux` and the `agent` CLI, uses `/root/.cursor/logs`, and does not test cwd propagation | Detached proofs use the private-environment recipe (§6.6) |
| F13 | **Measured:** a stub `agent` placed first in the caller's `PATH` was found by a pane created with `tmux new-session -d` on a tmux server that was **already running** (the server had been started without the stub on its `PATH`). The likely mechanism is that tmux builds a new pane's `PATH` from the dispatching client. Other environment variables were not tested and MUST NOT be relied on | PATH stubs work with a fresh or an existing server; stub behaviour is chosen by words in the prompt, not by environment variables; `actl doctor` records the tmux version (S0-R1) |
| F14 | The runner prints `[TIMEOUT]` into the pane (hence the log) on exit 124/137 | Secondary signal; the exit-code file is primary |
| F15 | The repo `hooks/pre-commit` has no `/tmp` bypass and is copied to `~/.config/git/hooks/` by `install.sh` | Scratch repos use `-c core.hooksPath=/dev/null` or a `wip/*` branch |
| F16 | **Measured (VPS, bash 5.2.21):** in a script whose only trap is `trap '...ec=$?...' EXIT`, an external SIGTERM ran the trap but `$?` inside it was **0** (the job's wait status was 143). With an additional `trap 'exit 143' TERM`, the trap saw 143, but only after the foreground child (`sleep 5`) had finished, about 4 s after the signal. **Sandbox (bash 5.3.9), not yet measured on the VPS:** SIGTERM followed at once by SIGHUP to the whole process group (what `tmux kill-session` does) left no file | A runner killed from outside must not record `0`: explicit signal traps, and an unconditional overwrite in the kill path (S0-R16); a missing file after the session is gone means "lost" |

---

## 5. Stage 0 — Foundations: layout, identity, schemas, scope matcher, golden sprint, exit-code persistence

Stage 0 has two workstreams that can run on separate branches and are both required before Stages 1 and 2: **0A Foundations** (all new `actl` files, S0-R1 to S0-R15) and **0B Exit-code persistence** (one existing file, S0-R16).

### 5.1 Goal

Create the shared building blocks every later Stage depends on, and the golden sprint that proves them: `actl` can create a sprint, allocate sequence numbers safely, validate every artifact kind, hash consistently, evaluate `scope.txt` rules, and discover commands and `next` rules through registries; and a detached run's exit status is persisted deterministically.

### 5.2 Scope and non-goals

In scope: package skeleton, CLI and `next` registries, path layout, `seq` allocator, canonical hashing, JSON Schemas, `scope.py`, `graph.toml` defaults, `actl init`, `actl sprint new`, `actl doctor`, `INTERFACES.md`, golden fixture, gating suites, and the exit-code change in `src/router/process.py`.
Out of scope: `run_as`/`sudo` wrappers, any `ACTL_ISOLATION` switch (deferred to Stage 4, §8.2), dispatching LLMs, counters beyond `seq`, escalation, new tmux code.

### 5.3 Repository additions

```text
atools/
├── bin/actl                          # copy of the bin/asessions wrapper pattern (PYTHONPATH=src)
├── src/actl/
│   ├── __init__.py  cli.py           # argparse + auto-discovery of cmd_*.py; exit-code table (S0-R10)
│   ├── next.py                       # decide_next + auto-discovery of next_rules/*.py
│   ├── layout.py  ids.py  seq.py  hashing.py  schemas.py  scope.py  sprint.py  doctor.py  errors.py
│   ├── cmd_init.py  cmd_sprint.py  cmd_doctor.py  cmd_next.py
│   ├── next_rules/                   # empty registry in Stage 0 (a dummy rule in tests)
│   └── INTERFACES.md                 # the interface freeze (S0-R15), with a machine-readable block
├── schemas/  common.json state.json sprint.json closure.json verification.json qualification.json contract.json oracle-decision.json prior_attempt.json sprint-proposal.json meta.json attempt.json
├── config/graph.toml                 # installation defaults (illustrative values from Design §4.1)
├── fixtures/golden/                  # §5.8
├── proof/run_suite_actl_s0.sh  proof/stage0/*.sh            # workstream 0A
├── proof/run_suite_exit_code.sh                              # workstream 0B (reference in §5.9)
├── test/actl/                        # pytest (stdlib + pytest only)
└── edit (0B): src/router/process.py
```

### 5.4 Numbered requirements

**S0-R1 Baseline capture (`actl doctor [--json]`).** MUST report and write to `ACTL_ROOT/baseline.json` (first run only; `--refresh` overwrites): `VERSION` (expected `v0.1.4` or later); `git rev-parse HEAD`; dirty/clean; whether `5cb7f30`, `759a0ca`, `a9b3a4e`, `4da9394` are ancestors; `python3`, `git`, `tmux` (including `tmux -V`) and `bash` versions; `pytest` and `jsonschema` availability; presence of the `agent` CLI (the persistence suite needs it) and of the other engine CLIs; `timeout`; effective user; `ACTL_ROOT`; the resolved `LOG_DIR` and `METADATA_DIR` (F4); linger state (`loginctl show-user`); a feature probe whether `router.process` exposes `read_exit_code` (S0-R16; absent is a recorded warning in 0A, and a precondition failure for Stage 1); the result (exit code and tail) of `proof/run_suite_engines.sh`, `proof/run_suite_session_persistence.sh`, `proof/run_suite_exit_code.sh` (when present) and `audit/atools-compliance_audit.sh --cursor` plus its `--self-test` (record the pass, fail, skip and warn counts; skips are expected and `--strict` is not used); and the output of `diff -u` between each repo file and its installed copy (`hooks/pre-commit`, `rules/git-safety.md`, `.cursor/skills/atools-repair/SKILL.md`) (non-empty is a recorded warning). It exits `4` if `tmux` is missing or the audit script is not found (recorded `not_found`) and never modifies the repo.

**S0-R2 Additive-change rule.** Measured against the workstream's fork point, workstream 0A consists of new files plus (at most) patches to `install.sh` (link `bin/actl`; loop copying `skills/*`) and `README.md`; workstream 0B changes only `src/router/process.py` plus its new proof suite. The three `atools` suites and the audit keep their results.

**S0-R3 Layout.** `Layout(root, repo="target-repo")` is the only code constructing paths for the target tree. Default root: `$ACTL_ROOT`, else `$HOME/actl-graph`. It exposes at least `records`, `sprint_dir(tag)`, `runs_dir(tag)`, `mailboxes(tag)`, `inbox(tag, role)`, `outbox(tag, role)`, `workspace(name, tag=None)`, `target_repo`, `profile(role)`. Roles are exactly `architect`, `challenger`, `implementer`, `curator`. The tree mirrors Design §1.5:

```text
$ACTL_ROOT/
├── records/<repo>/<tag>/ (700) └── {sprint.toml, spec-001.md, oracle-003/, contract-005.json, closeout/, ...}
├── sprints/<repo>/<tag>/     └── runs/{state.json, sessions.tsv, logs/}, mailboxes/{role}/{inbox,outbox}, workspaces/
├── profiles/{role}/          └── persistent per-persona CLI state (empty until Stage 4, profiles/README.md)
├── repos/<repo>/             └── git repository (from `actl init --target <path-or-url> [--name <repo>]`)
└── tools/                    └── process scripts (mutate.py, unfiles.py)
```

Modes from §1.5 are *applied* (`700`, `0750`/`0770`) even though local mode cannot make them effective. Path inputs are validated (no `..`, no absolute path where a relative one is expected).

**S0-R4 Sprint creation.** `actl init --target <git path|url> [--name <repo>]` creates the tree, writes `profiles/README.md`, and clones the target into `repos/<repo>` (`git clone --local --no-hardlinks` for a path, default name `target-repo`). `actl sprint new <slug> [--spec file]` MUST: validate `slug` against `^[a-z0-9][a-z0-9-]{1,40}\Z`; mint `sprint_tag = YYYY-MM-DD_{slug}` from `$ACTL_TODAY` (if set to `YYYY-MM-DD`) else the local date (refuse if it exists); pin `base_sha` as the full 40-char HEAD of the target's default branch; record `repo = layout.repo` in `state.json` and `sprint.toml`; create the sprint, mailboxes, and runs directories, `runs/state.json` (S0-R5), `runs/sessions.tsv` with header `seq\tsession\trole\tengine\tmodel\tmodel_family\tturns\ttool_calls\ttokens\tcost_usd\texit_code\taccepted_items\tescalation_alerts_sent\n`, and a deterministically formatted draft `sprint.toml` with every default resolved from `config/graph.toml`, `live_run` left **unset** (no default per Design §4.1) and `status = "draft"`. With `--spec`, it is copied as `spec-{seq}.md` using a newly allocated `seq`, and `spec_source = "imported"` and `active_spec = "spec-001.md"` are recorded.

**S0-R5 Sequence allocator and state.** `seq.reserve(layout, tag, kind) -> int` MUST: take an exclusive `fcntl.flock` on `runs/state.lock`; read `state.json` and `runs/seq.highwater` (if present); set `next_seq = max(state["seq"], highwater) + 1`; write `f"{next_seq}\n"` + `fsync` to `runs/seq.highwater`; write `state.json` atomically (temp file in `runs/`, `fsync`, `os.replace`, `fsync` of `runs/`); release the lock; and return `next_seq` **before** any artifact is written. Numbers are never reused. 50 parallel reservations MUST yield 50 distinct numbers. `state.json` includes `repo`, `active_solution_key` and `active_oracle_draft` alongside `active_spec`, `active_oracle`, `active_contract`. `seq.reconstruct(layout, tag)` rebuilds `seq = max(highwater, max_artifact_seq)` across `sprint_dir(tag)` (`records/<repo>/<tag>`), `runs_dir(tag)` (`sprints/<repo>/<tag>/runs`), `mailboxes(tag)/*/*` (two levels, file names only), and sprint-scoped `workspaces/{tag}/implementer-*`, and replays existing `*.meta.json`, `qualification-*.json`, `contract-*.json`, `closure-*.json`, `verification-*.json`, and `escalation-*.json` files in `seq` order to restore `repo`, `active_*` pointers, `epoch`, `status`, `attempts`, `closures_submitted`, `hard_caps_tripped`, and `grants`.

**S0-R6 Canonical hashing.** `hashing` defines once:
- `file_sha256(path)`: SHA-256 of raw on-disk file bytes, lowercase 64-char hex. This is the universal digest domain for `sprint_sha256`, `contract_sha256`, `spec.sha256`, `qual.sha256`, and `scope.sha256`.
- `manifest_sha256(dir)`: SHA-256 of the UTF-8 text formed, for every regular file under `dir` sorted by POSIX relative path (`relpath.encode("utf-8")`), by the line `f"{relpath}\0{exec_flag}\0{file_sha256}\n"` where `exec_flag` is `"x"` if `(st_mode & 0o111) != 0` else `"-"`. Symlinks and special files are errors; empty directories are ignored.
- `canonical_json(obj)` (UTF-8, sorted keys, separators `(",", ":")`, `ensure_ascii=False`, `allow_nan=False`) and `json_sha256(obj)`.
The spec MUST include at least six independently computed test vectors.

**S0-R7 Schemas.** One JSON Schema (draft 2020-12, `additionalProperties: false`) per kind, validated by a single deterministic stdlib validator in `actl.schemas` (no delegation to third-party `jsonschema`). Sequenced `actl`-stamped artifacts (`verification`, `qualification`, `contract`) require `kind`, `seq`, and `parent` (nullable) via `common.json#/$defs/artifact_meta`. In `closure`, `kind`, `seq`, and `parent` are optional so agent-authored drafts validate before promotion. Unsequenced files (`state`, `sprint`, `sprint-proposal`, `oracle-decision`, `prior_attempt`) omit `kind` and `parent`. Both `sprint` and `state` record a `repo` field. `sprint` allows `live_run` to be omitted only when `status == "draft"` and requires it when `status == "frozen"`; `sprint-proposal` permits only proposable policy keys (`live_run` required, `approval_live_run`, `solution_key_exposure`, `owner_review_triggers`, `min_attempts_before_block`, `max_epochs`, `max_attempts`, `hard_cap`) and rejects `sprint_tag`, `base_sha`, `status`, `spec_source`, and `repo_test_cmd`. Field lists come from Design §4.2–4.3; where the Design gives only an example, the spec agent infers types and records the inference:
- `closure`: `reason` (`done|blocked`), `blocking_step` (string|null), `notes` (string[]), `backlog` (string[]), `solution_key_divergence` (`{requirement_id, rationale}`|null).
- `verification`: `id`, `stage` (`guards|offline|live|blocked_check`), `oracle`, `contract`, `head`, `exit_code`, `steps[]` (`id`, `cmd`, `exit_code`, `output_sha256`), `failing_step`, `failing_line`, `tripwires[]`, `halt` (null or `{reason}`), `session` (null or `{name, exit_code, hard_cap, lost, log_sha256}`).
- `qualification`: all fields of the Design example in §4.2, with `mutants[]` = `{name, killed, apply_error}`, `null_base` (`red|green`), `solution_key_guards`, `solution_key_repo_test` (`green|red`), `solution_key_green` (`"3/3"` or `"n/3"`), `diagnostic_case` (`none|pure_oracle_failure|solution_key_conflict`), `manifest_sha256`.
- `contract`: `epoch`, `base_sha`, `spec` (seq+sha256), `oracle` (seq+manifest_sha256), `qual` (seq+sha256), `sprint_sha256`, `scope` reference; no budgets.
- `oracle-decision`: `decision` (`lock_oracle|revise_oracle`), `feedback` (string|null).
- `prior_attempt`: `diff`, `failing_step`, `failing_line`, `closures_submitted`.
- `state`, `sprint` (the `sprint.toml` after TOML→JSON, each carrying `repo`).
`schemas.validate(kind, obj)` returns a list of `{path, message}` errors (empty = valid) and never raises on invalid data.

**S0-R8 Defaults.** `config/graph.toml` holds the installation defaults used to resolve a draft `sprint.toml`: `max_attempts` (oracle 3, implementer 2, live 2, curator 2), `min_attempts_before_block = 2`, `max_epochs = 3`, `solution_key_exposure = "full"`, `approval_live_run = "architect"`, `owner_review_triggers = []`, `[hard_cap.implementer]` (`wall_clock = "45m"`, `turns = 60`), `repo_test_cmd`. A comment states these are the Design's illustrative numbers.

**S0-R9 Golden fixture.** §5.8. Deterministic, no network, runnable by `pytest` and `bash` only. `build_golden.sh` supports `--install-sprint <ACTL_ROOT> [--tag <TAG>]` to deterministically populate `spec-001.md`, `solution_key-002.patch`, `oracle-003/`, `qualification-004.json`, `contract-005.json`, and `runs/state.json` for Stage 1/2 proofs before Stage 3 exists. Every git call in `build_golden.sh`, test helpers, and proofs MUST use a hermetic git environment (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `-c core.hooksPath=/dev/null`, fixed author/committer name, email, and timestamp). Permission proofs (`P-S0-03`, `P-S2-12`) MUST assert `stat.S_IMODE(os.lstat(path).st_mode)` bitmasks rather than write-denial side effects so they behave identically under UID 0 (`root`) and non-root accounts.

**S0-R10 CLI skeleton and exit codes.** `0` ok/green, `1` red (a check failed), `2` usage or schema/parse error, `3` halt (integrity problem; no attempt consumed), `4` environment error (missing tool). Every command supports `--json` and honours `NO_COLOR` like `core/terminal.py`.

**S0-R11 Gating suite (0A).** `proof/run_suite_actl_s0.sh` follows the `run_check` pattern of `proof/run_suite_engines.sh` (log per check in `proof/out/`, PASS/FAIL counters, non-zero exit on failure), is idempotent, and uses a temp `ACTL_ROOT`.

**S0-R12 `scope.py`.** The `scope.txt` parser and matcher. Format: lines `ALLOW: pattern` and `FROZEN: pattern`; blank lines and full-line `#` comments are ignored; trailing whitespace is stripped; inline `#` comments, leading `/`, `\`, NUL, empty segments (`//`), `.` and `..` segments are rejected with `ValueError`. Glob dialect: `*` matches zero or more non-`/` characters within one segment (including leading `.`); `**` (only as full segment `**`, `/**`, `**/`, `/**/`) matches zero or more path segments (`a/**/b` matches both `a/b` and `a/x/y/b`); no other metacharacters (`?`, `[`, `]`, `{`, `}` are rejected). `validate(rules)` requires at least one `ALLOW` rule, requires `FROZEN: test/**` to be present, rejects literal-vs-literal conflicts on the same path, and probes sentinel paths (`__root_probe__`, `test/__probe__.py`, `test/sub/__probe__.py`) to reject any glob that allows arbitrary root paths or thaws `test/**` via a non-literal pattern (e.g., `**/*`, `*/**`, `**/*.py`).

**S0-R13 Registries.** `cli.py` discovers `src/actl/cmd_*.py` (each exports `register(subparsers)`); `next.py` discovers `src/actl/next_rules/*.py` and evaluates rules in a documented fixed order; `decide_next(layout, tag) -> {action, command, reason}` is pure.

**S0-R14 Expected-results fragments.** `fixtures/golden/expected.d/base.json` plus a loader that merges all `expected.d/*.json`.

**S0-R15 Interface freeze.** `src/actl/INTERFACES.md` lists the signatures of `Layout`, `seq.reserve/reconstruct`, `hashing.*`, `schemas.validate`, `scope.parse/validate/match`, `decide_next`, the registry entry points, and the `StepResult`/`ev` shapes. It contains a fenced, machine-readable block (`interfaces.json`: module, name, kind, parameter names and types, return type for every public name). It is the contract for Stages 1 and 2; later changes need the Owner's approval and a note in the file. Proof `P-S0-26` imports the implemented modules and checks that each listed name exists with a compatible signature (parameter names and order, return annotation present).

**S0-R16 Exit-code persistence (workstream 0B).** In `src/router/process.py` only:
1. The generated runner's `cleanup` function reads `$?` as its **first statement** (`local ec=$?`), writes it to a temp file in the same directory, `mv -f`s that onto `<METADATA_DIR>/<session>.exit`, and only then removes the runner script and the metadata JSON. The file holds the integer and a newline. The runner also defines `trap 'exit 143' TERM`, `trap 'exit 129' HUP` and `trap 'exit 130' INT`, because a bare EXIT trap records `0` after an external SIGTERM (F16). These traps run only after the foreground child has ended.
2. The runner does not delete `.exit`; neither do `cleanup_session_metadata()` nor the stale-metadata pruning in `get_running_sessions()` (which only globs `*.json`).
3. `spawn_detached_session()` deletes an existing `<session>.exit` and `<session>.exit.tmp` before starting (next to where it unlinks the old log) and also when the tmux start fails.
4. `kill_session()`, after it has killed the pane processes, waits (at most 2 s) until they are gone and then **unconditionally overwrites** `<session>.exit` with `143` (atomic temp file plus rename). The overwrite is safe because the killed runner can no longer write.
5. Helpers `get_exit_path(session_name) -> Path` and `read_exit_code(session_name) -> Optional[int]` (`None` when missing or not a clean integer).
6. No other behaviour changes (tmux options, argument handling, printed messages) except two: the session directories are resolved at call time (`_resolve_metadata_dir`, `_resolve_log_dir`, same defaults as F4), and the runner is started through an ephemeral `<session>.boot.sh` trampoline that `exec`s `<session>.run.sh`, so that `pgrep -f <session>.run.sh` selects the runner and not the tmux server (E10). `.boot.sh` is removed with the runner, by `cleanup_session_metadata()`, by the stale sweep in `get_running_sessions()` and when the tmux start fails. The engines and persistence suites pass unchanged.
Meanings: `0` success; `124`/`137` watchdog; `127` missing CLI; `129`/`130`/`143` signalled from outside or killed with `arouter kill`. A missing file after the session is gone means "lost" (SIGKILL, tmux server death, reboot). Nothing may rely on the engine's exit status being visible any other way, and no killed session may record `0`.

### 5.5 Proof obligations (minimum)

| ID | Proves | Method |
|---|---|---|
| P-S0-01 | `S0-R1`: all fields reported; baseline written once; `--refresh` overwrites; missing `tmux` or audit → exit `4` | run twice; PATH manipulation |
| P-S0-02 | `S0-R2`: only allowed files changed per workstream; suites and audit unchanged | `git diff --name-status` against the fork point; edits to pinned paths must match an allowlist of attested blobs inside the proof (D-28) |
| P-S0-03 | `S0-R3`: tree matches Design §1.5; modes applied; traversal rejected | stat every path |
| P-S0-04 | `S0-R4`: happy path; bad slug; duplicate; `live_run` unset; `--spec` import allocates a seq | CLI |
| P-S0-05 | `S0-R5`: 50 parallel `reserve` give distinct monotonic numbers; `kill -9` mid-reserve leaves no duplicate | multiprocess |
| P-S0-06 | `S0-R5`: `reconstruct` after deleting `state.json` equals the highest seq | file test |
| P-S0-07 | `S0-R6`: six `sha256sum`-checked vectors; exec-bit change alters the manifest hash; symlink rejected | cross-check |
| P-S0-08 | `S0-R7`: every golden artifact validates; ≥ 3 mutated invalid documents per schema are rejected at the right path | table-driven |
| P-S0-09 | `S0-R8`: resolved draft `sprint.toml` equals the golden text | file compare |
| P-S0-10 | `S0-R9`: golden self-check in plain shell (no `actl` code): base red, key green three times plus repo tests, each mutant killed by its mapped proof except the surviving one, `good.patch` green, each `bad_*` fails at its declared step | bash |
| P-S0-11 | `S0-R10`: exit-code table over scripted good and bad invocations | CLI |
| P-S0-12 | `S0-R12`: glob table (≥ 15 cases incl. `FROZEN` beats `ALLOW`, literal thaw, blanket-`ALLOW` rejection, deletion) | unit |
| P-S0-13 | `S0-R9`: with the real global hook installed, building the golden repo in a `mktemp -d` directory succeeds | integration |
| P-S0-14 | `S0-R13`: a dummy `cmd_*.py` and `next_rules/*.py` are discovered without editing core files | unit |
| P-S0-15 | `S0-R14`: the fragment loader merges `base`, `s1`, `s2` | unit |
| P-S0-16..25 | `S0-R16`: the ten checks `E1`–`E10` of `proof/run_suite_exit_code.sh` (§5.9): exit `0`, nonzero exit, timeout `124`, file format (one integer line, no `.tmp` left), runner and metadata removed while `.exit` stays, stale file replaced, no `.exit` while running, `arouter kill` records 129, 130 or 143 (exact 143 asserted by the pytest `test_kill_overwrites_129_with_143`), `read_exit_code` helper, runner signalled from outside never records `0` | private tmux server, stub `agent` and `loginctl` |
| P-S0-26 | `S0-R15`: `INTERFACES.md` conformance (signature introspection against the machine-readable block) | unit |

### 5.6 Exit criteria

All `P-S0-*` pass in `proof/run_suite_actl_s0.sh` and `proof/run_suite_exit_code.sh`; `proof/run_suite_exit_code.sh` is Red on the fork point; baseline recorded; the engines suite, the persistence suite and the audit still match; the Owner can run `actl init` and `actl sprint new demo` on a scratch root and read an exit code from a finished detached run.

### 5.7 Risks

Hashing and `seq` rules are load-bearing (G1, contract, reconstruction); ambiguity is expensive later, hence the vectors. `jsonschema` availability: O-1. The `.exit` file depends on bash signal semantics that differ between versions (F16); the proofs run on the VPS shell and `doctor` records the bash version.

### 5.8 The golden sprint fixture (the most reusable deliverable of the plan)

`fixtures/golden/`: a complete, hand-verified sprint on a tiny stdlib-only Python target mirroring the Design's example (public profiles).

```text
fixtures/golden/
├── target-repo/                  # source tree; build_golden.sh makes a real git repo with a pinned commit
│   ├── api/profile.py            # render_profile(user_id) -> (status, body); in-memory users
│   ├── api/cli.py                # `python -m api.cli profile <id>` prints JSON body, exit 0
│   ├── api/users.py
│   └── test/test_users.py        # 4 existing regression tests (one on a file scope can thaw)
├── sprint/
│   ├── scope_overrides/          # per-case scope.txt replacements (bad_testcount.txt only; keeps oracle/scope.txt exact, SA-6)
│   ├── spec-001.md               # R1 guests see name, bio, avatar, photo count of public profiles; R2 never expose email; R3 private profiles return 404; Locked: users schema unchanged; Deferred: indexing
│   ├── solution_key.patch
│   └── oracle/
│       ├── proofs/01_public.sh  02_no_email.sh  03_private_404.sh
│       ├── probe.sh              # recomputes photo count from raw data
│       ├── scope.txt             # FROZEN: test/**   ALLOW: api/profile.py   ALLOW: api/users.py
│       ├── coverage.md  oracle-critique.md
│       └── mutants/  contact_leak.patch (killed by 02)  private_200.patch (killed by 03)
│                     photo_count_off.patch (killed by probe.sh only)  avatar_drop.patch (deliberately SURVIVES)
├── implementations/              # candidate patches on base_sha, one per case
│   ├── good.patch  bad_scope.patch(G3)  bad_secret.patch(G5)  bad_testcount.patch(G4)
│   ├── bad_forbidden.patch(G6)  bad_proof_o1.patch(O1:02_no_email.sh)  bad_regression_o2.patch(O2)
├── stubs/                        # PATH stubs for deterministic detached runs (Stage 1): agent, loginctl
├── closures/                     # closure samples: good, schema-invalid, blocked-too-early, done
├── artifacts/valid  artifacts/invalid   # schema examples for P-S0-08 (>= 3 invalid per schema, expected error path)
├── responses/  turns/            # Stage 2 inputs, generated by make_responses.sh (§7.9)
├── expected_text/                # sprint.toml.tmpl: byte-exact draft sprint.toml template (P-S0-09)
├── vectors/                      # hashing.json: independently computed hash vectors (P-S0-07)
└── expected.d/base.json          # the cross-stage contract: case → expected step, exit code, failing_line
```

`build_golden.sh` creates the git repo with fixed author and date (stable SHA) and records `base_sha`. Proofs read the program under test from `ACTL_TARGET_CMD` (default `python3 -m api.cli`), so the same proofs can run as a pretend "live" stage. `expected` schema: `{"base_sha": str, "cases": {"<name>": {"applies_on": "base|base+key", "expect": {"step": str, "exit": 0|1, "failing_step": str|null, "failing_line_contains": str|null}}}}`. Later Stages read it and never hard-code expectations. The fixture is verified by `proof/stage0/golden_selfcheck.sh` (P-S0-10), which uses no `actl` code.

### 5.9 Workstream 0B reference (change and proof suite)

The reference is a starting point; the proof suite is normative. In `src/router/process.py`, in `create_runner_script(...)`, after `meta_path = get_metadata_path(session_name)`:

```python
    exit_path = METADATA_DIR / f"{session_name}.exit"
    exit_tmp = METADATA_DIR / f"{session_name}.exit.tmp"
```

and in the generated script (doubled braces because the template is an f-string) replace `cleanup` and add the signal traps:

```python
cleanup() {{
    local ec=$?
    printf '%s\n' "$ec" > {shlex.quote(str(exit_tmp))} && mv -f {shlex.quote(str(exit_tmp))} {shlex.quote(str(exit_path))}
    rm -f {shlex.quote(str(runner_path))} {shlex.quote(str(meta_path))}
}}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 129' HUP
trap 'exit 130' INT
```

In `spawn_detached_session(...)`, next to the existing log unlink (and in the tmux-failure branch), delete `get_exit_path(session_name)` and its `.exit.tmp`. Add the helpers:

```python
def _resolve_metadata_dir() -> Path:
    env_dir = os.environ.get("ATOOLS_SESSION_DIR")
    return Path(env_dir) if env_dir else (Path.home() / ".cursor" / "sessions")

def _resolve_log_dir() -> Path:
    env_dir = os.environ.get("ATOOLS_LOG_DIR")
    if env_dir:
        return Path(env_dir)
    try:
        if Path("/root/.cursor").exists():
            return Path("/root/.cursor/logs")
    except OSError:
        pass
    return Path.home() / ".cursor" / "logs"

def get_exit_path(session_name: str) -> Path:
    return _resolve_metadata_dir() / f"{session_name}.exit"

def read_exit_code(session_name: str) -> Optional[int]:
    try:
        text = get_exit_path(session_name).read_text(encoding="utf-8").strip()
        return int(text) if re.fullmatch(r"[0-9]+\Z", text) else None
    except Exception:
        return None

def _record_exit(session_name: str, code: int, overwrite: bool = False) -> None:
    if not overwrite and read_exit_code(session_name) is not None:
        return
    path = get_exit_path(session_name)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".exit.tmp")
    try:
        tmp.write_text(f"{code}\n", encoding="utf-8")
        os.replace(tmp, path)
    except Exception:
        pass

def _wait_pids_gone(pids, timeout: float = 2.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        alive = False
        for p in pids:
            try:
                os.kill(int(p), 0)
                alive = True
            except (ProcessLookupError, ValueError):
                pass
            except PermissionError:
                alive = True
        if not alive:
            return True
        time.sleep(0.05)
    return False
```

*(In `kill_session()`, after the `kill -9` loop: if `_wait_pids_gone(pids)` returns `True`, call `_record_exit(session_name, 143, overwrite=True)`; if it returns `False`, unlink `<session>.exit` so a stuck runner is classified as `session_lost`.)*

Proof suite `proof/run_suite_exit_code.sh` (authored first, immutable for the implementer). It isolates itself from the real environment: a private tmux server (so the Owner's real sessions are never touched and `kill-server` is safe), private log and session directories, stub `agent` and stub `loginctl` first in `PATH` (F13).

```bash
#!/usr/bin/env bash
set -uo pipefail
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="$REPO_DIR/proof/out"; mkdir -p "$OUT_DIR"
PASS=0; FAIL=0
command -v tmux >/dev/null 2>&1 || { echo "FAIL: tmux not installed"; exit 4; }

T="$(mktemp -d)"
export TMUX_TMPDIR="$T/tmux" ATOOLS_LOG_DIR="$T/logs" ATOOLS_SESSION_DIR="$T/sess"
mkdir -p "$TMUX_TMPDIR" "$ATOOLS_LOG_DIR" "$ATOOLS_SESSION_DIR" "$T/bin"
printf '#!/usr/bin/env bash\nexit 0\n' > "$T/bin/loginctl"
cat > "$T/bin/agent" <<'EOF'
#!/usr/bin/env bash
case "$*" in
  *EXIT7*) exit 7 ;;
  *SLEEP*) exec sleep 60 ;;
  *)       exit 0 ;;
esac
EOF
chmod +x "$T/bin/loginctl" "$T/bin/agent"
export PATH="$T/bin:$PATH"
trap 'tmux kill-server >/dev/null 2>&1; rm -rf "$T"' EXIT

check() { local n="$1"; shift
  if "$@" > "$OUT_DIR/$n.log" 2>&1; then echo "Running $n... [PASS]"; PASS=$((PASS+1))
  else echo "Running $n... [FAIL] (see $OUT_DIR/$n.log)"; FAIL=$((FAIL+1)); fi; }
wait_gone() { local s="$1" n=$(( ${2:-20} * 10 )); while (( n-- > 0 )); do tmux has-session -t "$s" 2>/dev/null || return 0; sleep 0.1; done; return 1; }
run_detached() { "$REPO_DIR/bin/arouter" cheap -d -n "$1" -t "$2" "$3" < /dev/null; }
exit_of() { cat "$ATOOLS_SESSION_DIR/$1.exit" 2>/dev/null; }

t_zero()    { run_detached ec-ok 20s OK && wait_gone ec-ok && [[ "$(exit_of ec-ok)" == "0" ]]; }
t_nonzero() { run_detached ec-7 20s EXIT7 && wait_gone ec-7 && [[ "$(exit_of ec-7)" == "7" ]]; }
t_timeout() { run_detached ec-to 2s SLEEP && wait_gone ec-to 25 && [[ "$(exit_of ec-to)" == "124" ]]; }
t_format()  { [[ "$(exit_of ec-7)" =~ ^[0-9]+$ ]] && [[ "$(wc -l < "$ATOOLS_SESSION_DIR/ec-7.exit")" -eq 1 ]] && ! ls "$ATOOLS_SESSION_DIR"/*.exit.tmp >/dev/null 2>&1; }
t_cleanup() { [[ ! -e "$ATOOLS_SESSION_DIR/ec-ok.run.sh" && ! -e "$ATOOLS_SESSION_DIR/ec-ok.json" && -e "$ATOOLS_SESSION_DIR/ec-ok.exit" ]]; }
t_stale()   { echo 99 > "$ATOOLS_SESSION_DIR/ec-stale.exit"; run_detached ec-stale 20s OK && wait_gone ec-stale && [[ "$(exit_of ec-stale)" == "0" ]]; }
t_running() { run_detached ec-run 30s SLEEP && sleep 1 && tmux has-session -t ec-run && [[ ! -e "$ATOOLS_SESSION_DIR/ec-run.exit" ]]; }
t_kill()    { "$REPO_DIR/bin/arouter" kill ec-run && wait_gone ec-run 10 && sleep 0.5 && [[ "$(exit_of ec-run)" =~ ^[0-9]+$ ]] && (( $(exit_of ec-run) >= 128 )); }
t_helper()  { PYTHONPATH="$REPO_DIR/src" python3 -c "
from router.process import read_exit_code
assert read_exit_code('ec-7') == 7
assert read_exit_code('does-not-exist') is None"; }
t_signalled() {
  run_detached ec-st 30s SLEEP || return 1
  sleep 1
  local pid; pid="$(pgrep -f "$ATOOLS_SESSION_DIR/ec-st.run.sh" | head -1)"; [[ -n "$pid" ]] || return 1
  kill -TERM "$pid"; pkill -TERM -P "$pid" 2>/dev/null
  wait_gone ec-st 15 || return 1
  local v; v="$(exit_of ec-st)"; [[ -z "$v" || "$v" != "0" ]]
}

check E1_exit_zero t_zero;            check E2_exit_nonzero t_nonzero
check E3_exit_timeout_124 t_timeout;  check E4_exit_file_format t_format
check E5_runner_removed_exit_kept t_cleanup; check E6_stale_exit_replaced t_stale
check E7_no_exit_while_running t_running;    check E8_kill_records_signal_exit t_kill
check E9_read_exit_code_helper t_helper;     check E10_signalled_runner_never_zero t_signalled
echo "=========================================="; echo "Suite Summary: $PASS Passed, $FAIL Failed"; echo "=========================================="
[[ $FAIL -eq 0 ]]
```

Acceptance: the suite exits `1` before the change and `0` after; the engines suite, the persistence suite and the audit still pass; `git diff --name-only <fork>..HEAD` for the 0B branch lists only `src/router/process.py` (the suite file is committed beforehand, as part of the authoring pass).

---

## 6. Stage 1 — Verifier and Implementer loop

### 6.1 Goal

Run Phase 3 end to end on the golden sprint with a real Implementer session launched through `arouter`, while **`actl`, not the agent, decides pass/fail** (Design §5.4–5.5). Produce `verify.py`, the single verification engine reused by Stages 3 and 5.

### 6.2 Scope and non-goals

In scope: `verify.py` with `G1–G6`, `O1`, `O2`; guard self-tests; oracle staging; `ev` and `prior_attempt` emission; the new Implementer skill; `actl dispatch-impl`, `actl verify-impl`, `actl wait`; completion protocol; log handling; tripwire; `HOME`-aware transcript lookup; `actl next` rules for Phase 3.
Out of scope: attempt budgets and escalation (Stage 4), `Q1–Q5` (Stage 3, built from this Stage's primitives), live runs, accounts, new tmux code.
Prerequisite: Stage 0 merged (both workstreams). The Implementer uses the existing tiers; the hybrid is expected (Implementer through `arouter`, other personas through web chats; Chi's "hybrid day-1 dispatch", adopted).

### 6.3 Additions (new files unless noted)

```text
src/actl/verify.py          # StepResult, check_guards(), run_o1(), run_o2(), verify_impl()
src/actl/guards/            # g1_oracle_hash.py g2_closure.py g3_scope.py g4_tests.py g5_secrets.py g6_forbidden.py
src/actl/stage.py           # clone, input staging, oracle staging
src/actl/session.py         # wraps arouter: start, poll, read exit code, copy logs (S1-R9, R14, R15)
src/actl/cmd_verify_impl.py cmd_dispatch_impl.py cmd_wait.py   src/actl/next_rules/phase3.py
config/forbidden.toml  config/secrets.toml
skills/actl-implementer/SKILL.md       # NEW skill; atools-repair/SKILL.md is NOT modified
proof/run_suite_actl_s1.sh  proof/stage1/*.sh  test/actl/test_verify_*.py
edit (minimal): src/core/config.py + src/sessions/storage.py -> resolve the Cursor home from $ATOOLS_CURSOR_HOME, default "/root/.cursor" unchanged
```

### 6.4 Numbered requirements

**S1-R1 StepResult and `ev`.** Every check returns `StepResult{id, cmd, exit_code, output_sha256, output_tail, duration_ms, failing_line}`. `verify_impl(...)` returns an `ev` document containing the executed steps and the first `failing_step`/`failing_line`. It runs fail-fast by default but accepts `fail_fast: bool` (Stage 4's `blocked` evaluation needs `G1–G6` and `O2` regardless).

**S1-R2 Order, halt vs red.** Order: self-tests → `G1` → `G2` (structural/schema check) → `G3` → `G4` → `G5` → `G6` → `O1` (skipped when `closure.reason == "blocked"` unless `blocking_step` cites `O1`) → `O2` → `G2` post-check (when `closure.reason == "blocked"`). A `G1` mismatch or a guard self-test failure is a **halt** (exit `3`, `ev.halt = {"reason": "integrity_mismatch" | "selftest_failed"}`, no attempt consumed). Every other failure is **red** (exit `1`). If `session_info` has `lost == True` or `hard_cap == True`, `G2` is unconditionally red (`exit_code = 1`) even if a closure file exists on disk.

**S1-R3 Guards.**
- `G1`: `manifest_sha256(oracle_dir)` equals `contract["oracle"]["manifest_sha256"]`.
- `G2`: Validates the closure against `schemas/closure.json`. When `reason == "blocked"`, `verify_impl` forces `fail_fast = False` across `G3–G6` and `O2`, then adjudicates the §5.4 blocked preconditions: (1) `closures_submitted >= min_attempts_before_block`, (2) `G4`, `G5`, and `G6` all pass (`G3` may fail only when `blocking_step == "G3"`), (3) `O2` passes unless `blocking_step` starts with `"O2"`, and (4) when `solution_key_exposure == "full"` and `blocking_step` starts with `"O1:"`, `solution_key_divergence` is non-null and its `requirement_id` exists in `coverage.md`.
- `G3`: Run `git diff --raw -z --no-renames {base_sha}..HEAD` in the verify workspace. Any entry whose new file mode is not `100644`, `100755`, or `000000` (e.g. symlink `120000` or gitlink `160000`) fails `G3`. Every touched path is checked with `scope.match`; if `scope.match` raises `ValueError` (e.g. backslash or control character in filename), `G3` records `"denied"` (red `G3`, exit `1`) and never crashes `verify_impl`.
- `G4`: runs only when some `test/{file}` is thawed. For each, parse base and HEAD with Python's `ast`; count `FunctionDef`/`AsyncFunctionDef` named `test_*` (module level and in classes); HEAD ≥ base. Also (Chi's refinement, adopted) reject a test whose body is only `pass`, `...`, a docstring or `assert True`. An unparsable file is red. Python only in Stage 1 (O-4).
- `G5`: scan the *added* lines of the diff and the closure's `notes`/`backlog` with the regexes in `config/secrets.toml` (private-key headers, cloud/API key shapes, `(api|secret|token|password)\s*[:=]\s*['"][^'"\s]{16,}['"]`) plus Owner-listed literals. Output never echoes the secret (rule id, path, line only).
- `G6`: data-driven rules in `config/forbidden.toml` (`id`, `language`, `kind` = `ast_call|regex`, `pattern`, `applies_to`, `message`). The spec proposes the initial list (O-5); it includes at least `shell=True`, `os.system`, outbound network clients in production code, `git push` text in scripts, `rm -rf /` shapes, and writes outside the working tree.
- Self-tests: each guard ships synthetic positive and negative cases, run before every evaluation and on demand (`actl selftest`).

**S1-R4 Oracle staging.** For `O1`, copy **only** `proofs/` and `probe.sh` into a private sibling directory `<worktree>.oracle-stage/` outside `worktree` (preserving `0550` executable modes), and invoke `bash <stage_dir>/proofs/<script>.sh` with `cwd = worktree` so candidate code inspecting `.` cannot enumerate oracle files. Remove `<worktree>.oracle-stage/` in a `finally` block.

**S1-R5 O1.** Run `proofs/*.sh` in lexical order, then `probe.sh`, each as `bash <script>` with cwd = the verify workspace (a clean `git clone --local --no-hardlinks` of the candidate branch); environment built from an **allowlist** (`PATH`, `LANG`, `HOME` = a throwaway dir, `TMPDIR`, `ACTL_TARGET_CMD`, nothing else, so credentials are blank by construction); per-script timeout (default 60 s); stdout+stderr captured. `failing_line` = the last output line starting `FAIL`, else the last non-empty line, truncated to 300 chars. Exit `0` passes, anything else fails.

**S1-R6 O2.** Parse `repo_test_cmd` from `sprint.toml` (owner/config-controlled only, never from LLM `sprint-proposal.toml`) via `shlex.split` with `shell=False`. The executable (`argv[0]`) MUST be in `("python3", "pytest")`. Append `f"--junitxml={junit_tmp_path}"` as a discrete argv element; parse the XML to produce `failing_step = "O2:{classname}::{name}"` (fallback `"O2"`).

**S1-R7 Emission.** `verify_impl` writes `runs/verification-{seq}.json` (seq reserved first). On red it writes `sprints/<repo>/<tag>/mailboxes/implementer/inbox/prior_attempt.json` with `diff` (`git diff {base_sha}..HEAD`), `failing_step`, `failing_line`, `closures_submitted`. Nothing else (no log tail, no oracle content) reaches `mailboxes/implementer/inbox/` (Design §5.4: `log_tail` goes to the Architect only). `verification` records `output_sha256` per step.

**S1-R8 Implementer skill.** Instructs the agent to read `mailboxes/implementer/inbox/` (`attempt.json` containing `seq` and `branch`, `spec`, `contract`, optional `solution_key.patch`, optional `prior_attempt.json`), commit on the pre-checked-out `wip/{seq}` branch, and write `mailboxes/implementer/outbox/closure.json` (or `closure-{seq:03d}.json`). `actl` stamps `kind`, `seq`, `parent` and promotes `closure.json` to `runs/closure-{seq:03d}.json` (recording `"closure-{seq:03d}.json"` in `verification.parent`).

**S1-R9 `actl dispatch-impl`.** `actl dispatch-impl --sprint TAG [--mode detach|foreground] [--tier balanced] [--engine cursor] [--no-run]`:
1. Refuse with exit `2` if `state["tmux_sessions"]` already contains a live tmux session for this sprint. Otherwise reserve `seq`; create `$ACTL_ROOT/sprints/{repo}/{tag}/workspaces/implementer-{seq:03d}` as a standalone local clone at `base_sha` on branch `wip/{seq:03d}`; stage `mailboxes/implementer/inbox/` (including `attempt.json`).
2. Build a **byte-identical static instruction** across attempts referencing the sprint's `mailboxes/implementer/inbox/` and `mailboxes/implementer/outbox/closure.json` (no per-attempt `{seq}` embedded in the prompt text).
3. **Detach mode:** session name is `format_session_name("impl", slug, seq, tag)` (`impl-{slug_trimmed}-{tag_hash4}-{seq:03d}`).
4. **Foreground mode (tests, short jobs):** same without `-d`; non-TTY stdout selects the legacy path (F1), which blocks and returns the real exit code but is not protected against the death of the harness.
5. After the session completes (S1-R14, S1-R15), call `verify_impl`. The command prints a one-screen summary and exits with the verify exit code. `--no-run` stages everything and stops, so a human can run any other agent by hand.

**S1-R10 Tripwire (honest-mode `P`).** Scan the Cursor transcript and ANSI-stripped console log for references to `$ACTL_ROOT/records`, `records/`, or path accesses to `oracle-`, `proofs/`, `mutants/`, or `probe.sh`, explicitly excluding lines from `skills/actl-implementer/SKILL.md`, `mailboxes/implementer/inbox/contract-*.json`, and `O1:<script>` tokens inside `mailboxes/implementer/inbox/prior_attempt.json`. Matches go to `verification.tripwires[]` with line numbers. A tripwire is a warning in Stage 1; `--strict-tripwire` makes it red and becomes the default at Stage 4.

**S1-R11 `actl verify-impl`.** `actl verify-impl --sprint TAG --closure PATH [--worktree PATH] [--no-fail-fast] [--json]`; exit codes per S0-R10. It can run by hand on any worktree, which is how golden cases are tested without an LLM.

**S1-R12 `actl next` (Phase 3 rules).** Pure rules registered under `next_rules/phase3.py` recommending one action with the exact command: stage a work order; dispatch the Implementer; **session running** → `arouter logs -f <name>` or `arouter attach <name>`; **session finished with exit-code file** and closure present → `actl verify-impl ...`; **session finished, no closure** → red at `G2`, then re-dispatch; **session lost** → inspect and re-dispatch; read `prior_attempt.json` and re-dispatch; "green: nothing more in Stage 1".

**S1-R13 Determinism.** `verify.py` and `guards/*` import no network libraries, call no LLM and do not read the clock for decisions. Identical inputs give identical `verification` (modulo `duration_ms`).

**S1-R14 Completion protocol (uses S0-R16).** `actl wait <name> [--timeout S]` and `dispatch-impl` share one routine:
1. Poll once per second until the session name is absent from `tmux list-sessions`; give up at `wall_clock + kill grace + 30 s` (then `arouter kill` and classify `hard_cap`).
2. Read `<METADATA_DIR>/<name>.exit` (`read_exit_code`). Present → the exit code is authoritative: `124`/`137` → `hard_cap` (Design `session_cap`); other nonzero is recorded and verification still runs.
3. Session gone and the file still missing after a 5 s grace → `session_lost` (SIGKILL, tmux server died, reboot): red at `G2`, flagged to the Owner, never a pass.
4. Verification never trusts the exit code for pass/fail; it only classifies why a run failed (a closure decides, as in the Design).
5. The result is recorded in `verification.session = {name, exit_code, hard_cap, lost, log_sha256}`.
Directory resolution follows F4 exactly (env override, else default); production leaves the overrides unset so the Owner's `arouter ps`, `attach` and `asessions` keep seeing the sessions.

**S1-R15 Log handling and retention.** `archive_session_log` copies `<LOG_DIR>/<name>.log` to `runs/logs/impl-{seq:03d}.log` and `<METADATA_DIR>/<name>.exit` to `runs/logs/impl-{seq:03d}.exit` and verifies the SHA-256. The original `<LOG_DIR>/<name>.log` and `<METADATA_DIR>/<name>.exit` are unlinked **only after** `runs/verification-{seq:03d}.json` is durably written to disk (per `D-16`). Retention of `runs/logs/` is `actl gc` (Stage 4).

### 6.5 Proof obligations (minimum)

| ID | Proves | Method |
|---|---|---|
| P-S1-01 | Golden `good.patch`: all steps green, exit `0`, `ev` schema-valid | `verify-impl` on fixture |
| P-S1-02..07 | Each `bad_*.patch` fails at the step in `expected.d/s1.json` with the expected `failing_line` substring | one proof per case |
| P-S1-08 | Every guard self-test passes; a deliberately broken guard (temp copy) causes a **halt** (exit `3`) | mutation of guard code |
| P-S1-09 | `G1`: one changed byte in the oracle → halt, nothing attempt-related written | tamper test |
| P-S1-10 | `G3` uses `scope.match` (no second implementation) | grep + behaviour |
| P-S1-11 | `G4`: removed test, hollow test, commented-out test, tests in a class, async tests | unit |
| P-S1-12 | `G5`: seeded fake keys caught; the matched secret appears in no output file | grep outputs |
| P-S1-13 | Staging: during `O1` the workspace holds `proofs/` and `probe.sh` only; removed even after a timeout | `find` in a hook proof |
| P-S1-14 | `O1` env allowlist: a proof printing `env` shows only allowed names | proof fixture |
| P-S1-15 | `prior_attempt.json` has only the four allowed keys and no oracle text beyond `failing_line` | schema + grep |
| P-S1-16 | `dispatch-impl --no-run` stages exactly the expected inputs and a clone on `wip/{seq}`; the global hook rejects a commit on `main` in the clone | git test |
| P-S1-17 | Tripwire fires on a synthetic transcript and on an ANSI-laden log mentioning `proofs/01_public.sh`; clean inputs give none | fixtures |
| P-S1-18 | `decide_next` Phase 3 table (≥ 10 states) | unit |
| P-S1-19 | The three `atools` suites and the audit are unchanged | baseline compare |
| P-S1-20 | Normal completion: stub agent writes a valid closure; session appears in `arouter ps`, vanishes; exit-code file `0`; `ev` written | §6.6 recipe |
| P-S1-21 | Nonzero engine exit with a valid closure: exit recorded, verification still decides | §6.6 |
| P-S1-22 | Watchdog: stub sleeps beyond `-t 3s`; exit `124`; classified `hard_cap`; red at `G2` | §6.6 |
| P-S1-23 | Exit `0` but no closure: red at `G2` | §6.6 |
| P-S1-24 | Session lost (private tmux server killed): `session_lost`, red, never green | §6.6 |
| P-S1-25 | cwd: the stub records `pwd`; it equals the clone path | §6.6 |
| P-S1-26 | Instruction rejected before `arouter` is invoked when non-ASCII, oversized, or when the session name is invalid | unit |
| P-S1-27 | Log copied to `runs/logs/`, hash matches `ev.session.log_sha256`, originals deleted; kept if the copy fails | §6.6 |
| P-S1-28 | `arouter` called with `< /dev/null` does not block (timeout-guarded) | §6.6 |
| `smoke_S1_01` | One real `abalanced` run on the golden sprint; result recorded, **not gating** | manual |

Detached proofs need `tmux`; without it they exit `4` and the skip is recorded, not silent.

### 6.6 Deterministic detached-proof recipe

Detached behaviour is tested without an LLM by isolating from the real environment (the recipe the Stage 0B suite already uses): export a private `TMUX_TMPDIR` (the Owner's real sessions are never touched, and `tmux kill-server` on the private socket is safe); private `ATOOLS_LOG_DIR` and `ATOOLS_SESSION_DIR`; put stub `agent` and stub `loginctl` first in `PATH` (the latter prevents `enable-linger` side effects, F7). The stubs reach the pane because tmux builds the pane's `PATH` from the dispatching client (F13, measured), so this works with a fresh or an existing server. Do not rely on other environment variables reaching the pane; control the stub's behaviour through words in the prompt (`EXIT7`, `SLEEP`, `WRITE_CLOSURE`). Clean up with `tmux kill-server` on the private socket. Stubs live in `fixtures/golden/stubs/`.

### 6.7 Exit criteria

All gating proofs pass; one smoke run is logged (even a failing model run is data about prompt quality, not about the verifier).

### 6.8 Risks

(1) `failing_line` is a leak channel for oracle content by design (Design §5.4); keep it to one line. (2) Local mode cannot protect the oracle (core §3). (3) The log is a raw PTY capture with a small start-up race (F6). (4) PATH propagation into tmux panes is a measured behaviour of the installed tmux version, which `doctor` records.

---

## 7. Stage 2 — Paste bridge and promotion

### 7.1 Goal

Make the manual Architect and Challenger loop (later the Curator) safe and fast: one command builds the payload to paste into a web chat; one command turns the pasted answer into validated files, or prints exactly how to ask the model to fix it. Add the minimal promotion step that turns drafts into immutable `{kind}-{seq}` artifacts and stages the next persona's inputs.

### 7.2 Scope and non-goals

In scope: `bundle`, `unpack`, `replay`, `promote`, turn ledger, repair prompts, role prompts, `actl next` rules for Phases 1–2 (transport).
Out of scope: running `Q1–Q5` and freezing an oracle or minting a contract (Stage 3); automatic dispatch of web personas (impossible by design); attempt counters. These commands are pure file operations and do not use the detached-session layer. (Later, a persona MAY be run through the Cursor engine by piping a bundle into `arouter -d` and feeding the log to `unpack`; tracked for Stage 3.)

### 7.3 Additions

```text
src/actl/bundle.py  unpack.py  envelope.py  patchsynth.py  promote.py  turns.py  repair.py  replay.py
src/actl/cmd_bundle.py  cmd_unpack.py  cmd_promote.py  cmd_replay.py  next_rules/phase12.py
prompts/architect-intake.md  architect-review.md  challenger.md  curator.md (stub, Stage 5)  _output_contract.md
proof/run_suite_actl_s2.sh  proof/stage2/*.sh  test/actl/test_envelope*.py ...
fixtures/golden/make_responses.sh  fixtures/golden/responses/  fixtures/golden/turns/  fixtures/golden/expected.d/s2.json     # §7.9
```

### 7.4 Numbered requirements

**S2-R1 Turn ledger & Courier.** Every `bundle` acquires `runs/state.lock`, computes `n = 1 + max((existing_n for {role}-{existing_n}), default=0)`, and creates `sprints/<repo>/<tag>/runs/turns/{role}-{n}/` via exclusive `os.mkdir` containing `bundle.txt`, `bundle.json` (`{turn_id, role, purpose, base_sha, solution_key_sha256, files:[{path, sha256, bytes}], bundle_sha256, created, model_hint}`), later `response.txt`, `unpack.json`, and optional `amend-{k}.txt`. Directories are append-only; `unpack` never edits `bundle.*`.
Courier specification: `ACTL_COURIER_DIR` points at the courier root (VPS: `/home/syncer/Sync/courier`). If unset, `actl` writes only the ledger copy. Drawer name: `{stamp}__{repo}__{tag}__{role}-{n}__{purpose}` (`stamp` is UTC `YYYYMMDDTHHMMZ`, `__` separates fields). Drawer contents mirror the ledger turn folder: `bundle.txt`, `response.txt`, optional `amend-N.txt`, `repair.txt`. Identity comes from the sentinel `ENDRESPONSE bundle=<hex8>` inside the response, not from filenames.

**S2-R2 `actl bundle <purpose> --sprint TAG [--out FILE|-] [--osc52] [--clip] [--include PATH...] [--max-chars N] [--model NAME]`.** Purposes:
- `architect-intake`: role prompt + output contract + imported spec (if any) + repo map + files named by `--include`.
- `challenger`: static prefix `[prompt + contract][spec-{seq}.md][solution_key]`, then dynamic `[qualification receipt][oracle-decision.json feedback][prior oracle]` when present.
- `architect-review`: `[prompt + contract][oracle-critique.md][qualification-{seq}.json][oracle summary]` (Stage 3 supplies `qualification`; Stage 2 uses the golden `qualification` fixture).
- `curator`: stub that fails with a clear "Stage 5" message.
Rules: static content first, dynamic last (Design §1.3); a header lists included files with hashes and sizes; a **repo map** (`git ls-files` at `base_sha` with byte sizes) is always included, file bodies only for `--include`d paths; if total characters exceed `--max-chars` (default 200000) it aborts with a table of the largest files instead of truncating silently; `bundle_sha256` is defined as the lowercase hex SHA-256 of the UTF-8 bytes of `bundle.txt` **up to and excluding** the final line `<<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>\n`. Every `bundle.txt` ends with that exact sentinel line. When `--json` is passed, `--out -` is rejected with exit `2` and `--osc52` writes escape sequences to `/dev/tty` (or stderr) so stdout remains a single valid JSON object. `--model` stores the model name in `bundle.json` (the `F` check later); if omitted, it prints a reminder and records `unknown`. Output defaults to a file plus a stdout summary; `--osc52` emits the OSC 52 clipboard escape (works through SSH in many terminals); `--clip` uses `wl-copy`/`xclip`/`pbcopy` when found. If `ACTL_COURIER_DIR` is set, `actl` also writes the drawer copy.

**S2-R3 Envelope grammar.** Normative in §7.5. Output files travel in `FILE` blocks, code edits in `PATCH` blocks. Prose outside blocks is preserved in `response.txt` and ignored.

**S2-R4 `actl unpack <purpose> --sprint TAG [-f FILE | --paste | --drawer PATH | < stdin] [--turn TURN_ID] [--amend] [--json]`.**
1. Resolve the target turn: if `--turn` is given, use it (verifying `bundle.json.purpose == <purpose>`); otherwise select the highest-numbered turn `{role}-{n}` whose `bundle.json.purpose == <purpose>`. In `--drawer <path>` mode, read `response.txt`; if missing and exactly one other file besides `bundle.txt` exists, use that one. In `--paste` mode, read stdin line-by-line tracking open `<<<FILE...>>>` and `<<<PATCH...>>>` blocks (honoring `fence="N"`) and stop only when a line matching `^<<<END_RESPONSE bundle="[0-9a-f]{8}">>>\s*$` appears at top level outside any open block.
2. Save raw bytes as `response.txt` (or `amend-{k}.txt` when `--amend` is set) **before** parsing.
3. Normalize: strip UTF-8 BOM, convert `CRLF -> LF`, strip one enclosing Markdown code fence (`` ``` ``...) only outside top-level `<<<...>>>` markers, and strip trailing horizontal whitespace on `<<<...>>>` marker lines and hunk delimiter lines.
4. Parse blocks per §7.5; the top-level sentinel must be the last non-blank line and match `bundle_sha256[:8]` (`E_BUNDLE_MISMATCH` or `E_TRUNCATED`).
5. Validate (`S2-R6`) and synthesize patches (`S2-R5`) in a **temporary staging directory** (`sprints/<repo>/<tag>/mailboxes/.{role}-staging-{pid}`).
6. All-or-nothing directory swap: with zero errors, atomically replace the entire `sprints/<repo>/<tag>/mailboxes/{role}/outbox/` directory with the validated staging directory (removing any prior `*-outputs.prev`, renaming `*-outputs` -> `*-outputs.prev`, renaming staging -> `*-outputs`, then removing `*-outputs.prev` so omitted files never leak from old turns). After success under `--drawer`, move the response into the ledger after hash check and remove the empty drawer. On any error, leave outbox untouched, write `unpack.json` and `repair.txt` (adding `repair.txt` to the drawer if in `--drawer` mode), and exit `2`.
`--amend` replays `response.txt` followed by `amend-1.txt .. amend-{k}.txt` in order: `FILE` blocks replace earlier `FILE` blocks with the same `path`; `PATCH` blocks replace earlier `PATCH` blocks with the same `(out, file)` tuple; the resulting union is validated and published as a complete generation.

**S2-R5 Patch synthesis.** For every `PATCH` block, validate both `out` (against the §7.5 purpose table) and `file` (relative POSIX path; reject any path component equal to `.git` case-insensitively with `E_PATH`; reject any symlink component in the scratch checkout via `lstat` / `O_NOFOLLOW` with `E_PATH`). Create a scratch checkout at `base_sha` (for `out="solution_key.patch"`) or at `base_sha` with the `solution_key` matching `bundle.json.solution_key_sha256` committed (for `out="oracle-draft/mutants/<name>.patch"`). Run all git commands under a hermetic environment (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `-c core.hooksPath=/dev/null`, `-c core.fsmonitor=false`, fixed `GIT_AUTHOR_*` and `GIT_COMMITTER_*`), synthesize diffs via `git diff --no-color --no-ext-diff --full-index --src-prefix=a/ --dst-prefix=b/ --no-renames`, and verify with `git apply --check` on a fresh checkout. Applies each hunk requiring the SEARCH text to match **exactly once** (0 matches → `E_SEARCH_NOMATCH` with the nearest candidate by `difflib` and its line number; more than one → `E_SEARCH_MULTI` with line numbers). Several `PATCH` blocks with the same `out` merge into one patch. `new="true"` creates a file from the block body; creating an existing file is `E_EXISTS`.

**S2-R6 Validation after parsing.** Validate `oracle-decision.json` against `schemas/oracle-decision.json` and `sprint-proposal.toml` against `schemas/sprint-proposal.json` (`repo_test_cmd` prohibited). Parse `coverage.md` using the normative line grammar: ignore blank lines and `#` headings; every mapping line must match `^(R[0-9]+|(?:mutants/)?[A-Za-z0-9_.-]+\.patch)\s*(?:->|→|:)\s*(.+)\Z` where the RHS is a comma-separated list of proof tokens (`proofs/<name>.sh`, `<name>.sh`, `probe.sh`, or a 2-digit prefix `NN` resolving uniquely to `proofs/NN_*.sh`); every `oracle-draft/mutants/*.patch` must appear on the LHS and every referenced proof must exist in `oracle-draft/` (`E_COVERAGE`). In `architect-intake`, `spec-draft.md` is optional when `sprint.toml` has `spec_source == "imported"` and `state.json` already has a non-null `active_spec`. `proofs/*.sh` and `probe.sh` pass `bash -n`, get the executable bit, and SHOULD start with a shebang and `set -euo pipefail` (warning only); `scope.txt` is parsed with `scope.py` from Stage 0 (blanket `ALLOW` rejected); required files per purpose (§7.5 table) must be present (`E_MISSING_REQUIRED`); no output path may escape its allowed prefix, exceed 1 MiB, contain NUL bytes, or collide case-insensitively with another.

**S2-R7 Repair prompts.** On any error `unpack` prints (and saves as `repair.txt`) a paste-ready message: a short instruction, one numbered entry per error with `code`, `path`, a one-line cause and (for search failures) the offending SEARCH text and nearest candidate, then the instruction to answer with **only the blocks that must change** plus the sentinel. Error codes are fixed (§7.6). The message contains no oracle content beyond what the model sent.

**S2-R8 `actl replay <role>-<n> [--sprint TAG]`.** Re-runs steps 3–5 of `unpack` in a scratch directory by folding `response.txt` and all `amend-{k}.txt` files in numerical order against the stored `bundle.json` (using the pinned `base_sha` and `solution_key_sha256` artifact from `records/<repo>/<tag>/`, without mutating `sprints/<repo>/<tag>/mailboxes/{role}/outbox/`), and compares the resulting `ok`, `errors`, and `outputs` against stored `unpack.json`: exit `0` if identical, `1` if changed.

**S2-R9 `actl promote <role> --sprint TAG`.** For a role's valid outputs: hold `runs/state.lock` across the entire check-reserve-write-stage transaction; deduplicate artifacts by `(kind, parent, sha256)` (where `solution_key` and `oracle-draft` set `parent = state["active_spec"]`); copy drafts into `records/<repo>/<tag>/` as immutable files with Design naming (`spec-{seq}.md`; the key as `solution_key-{seq}.patch` — O-2; Challenger drafts as a candidate directory `oracle-draft-{seq}/`, not frozen); record `kind`, `seq`, `parent`, `sha256` in a sidecar `*.meta.json`; update `active_spec`, `active_solution_key`, and `active_oracle_draft` in `state.json`; always refresh read-only staged files (`0440` regular, `0550` executable) in the next role's inbox `sprints/<repo>/<tag>/mailboxes/{next_role}/inbox/` by unlinking existing targets before copying (Architect → Challenger: spec and key; Challenger → actl: oracle draft). No "latest" pointers. Idempotent for identical content (same `(kind, parent, sha256)` → no new `seq`).

**S2-R10 `actl next` (Phases 1–2 rules).** Registered under `next_rules/phase12.py`; recognizes missing spec, missing key, unpromoted drafts, a challenger bundle ready, a response waiting for unpack, a failed unpack with `repair.txt`, and "ready for Stage 3 qualification". Pure and table-tested.

**S2-R11 Role prompt files.** `prompts/*.md` state each persona's authority from Design §3.2 (the Challenger writes proofs/probe/mutants/scope/coverage/critique and never the spec; the Architect writes spec, key, sprint proposal and decisions and never edits proofs or mutants), the proof contract (exit `0/1`, `FAIL:` line, stage-agnostic via `ACTL_TARGET_CMD`). The output contract is appended from `prompts/_output_contract.md`, never copied by hand.

**S2-R12 Safety of the bridge.** `unpack` never executes anything from a response; the only commands it runs are `git` on scratch checkouts, `bash -n`, and schema/TOML parsing. `bundle` refuses files under `records/` other than the artifacts a purpose lists, and refuses `--include` paths outside the target repo at `base_sha`.

### 7.5 Envelope grammar (normative)

Marker lines start in column 0 after normalization; matching is case-sensitive. Optional `fence="N"` (`N` in `"3".."9"`, default `3`) scales both the closing block marker (`<`×N + `END_FILE` / `END_PATCH` + `>`×N) and inner hunk delimiters (`<`×(N+4) + ` SEARCH`, `=`×(N+4), `>`×(N+4) + ` REPLACE`):

```text
response     := (prose | block)* sentinel
block        := file_block | patch_block
file_block   := '<<<FILE path="' PATH '"' [' mode="exec"'] [' fence="' N '"'] '>>>' NL
                body
                '<'*N 'END_FILE' '>'*N NL
patch_block  := '<<<PATCH out="' OUTPATH '" file="' REPOPATH '"' [' new="true"'] [' fence="' N '"'] '>>>' NL
                ( hunk(N)+ | body-if-new )
                '<'*N 'END_PATCH' '>'*N NL
hunk(N)      := '<'*(N+4) ' SEARCH' NL text '='*(N+4) NL text '>'*(N+4) ' REPLACE' NL
sentinel     := '<<<END_RESPONSE bundle=' ['"'] HEX8 ['"'] '>>>' NL
```

- `body` and hunk texts are verbatim; the parser interprets only the exact closing marker line for the active `fence="N"`.
- Paths are relative POSIX: no leading `/`, no `..`, no backslash, no NUL, segments ≤ 100 chars, total ≤ 255.
- For `architect-intake`, `spec-draft.md` is required unless `sprint.toml` has `spec_source = "imported"` and `state.json` has `active_spec != null`.
- For `PATCH` blocks, `file` MUST NOT contain a `.git` path segment (case-insensitive) or traverse a symlink (`E_PATH`).
- Allowed output prefixes (violations are `E_PATH`):

| Purpose | Required outputs | Allowed prefixes |
|---|---|---|
| architect-intake | `spec-draft.md`, `solution_key.patch` (from PATCH blocks), `sprint-proposal.toml` | those three names |
| challenger | `oracle-draft/proofs/*.sh` (≥ 1), `oracle-draft/probe.sh`, `oracle-draft/scope.txt`, `oracle-draft/coverage.md`, `oracle-draft/oracle-critique.md`, `oracle-draft/mutants/*.patch` (≥ 1, from PATCH blocks) | `oracle-draft/` |
| architect-review | `oracle-decision.json`; optionally `spec-draft.md`, `solution_key.patch`, `scope.txt` (ALLOW additions only; checked in Stage 3) | those names |

### 7.6 Error codes (fixed vocabulary)

`E_TRUNCATED`, `E_BUNDLE_MISMATCH`, `E_PATH`, `E_DUPLICATE`, `E_SYNTAX_MARKER`, `E_SEARCH_NOMATCH`, `E_SEARCH_MULTI`, `E_PATCH_APPLY`, `E_JSON`, `E_TOML`, `E_SCHEMA`, `E_SHELL_SYNTAX`, `E_SCOPE`, `E_COVERAGE`, `E_MISSING_REQUIRED`, `E_SIZE`, `E_EXISTS`.

### 7.7 Proof obligations (minimum)

| ID | Proves | Method |
|---|---|---|
| P-S2-01 | Good architect-intake response unpacks; `solution_key.patch` passes `git apply --check`; applying it on `base_sha` turns the golden proofs green (Q1/Q3 preview in shell) | golden response |
| P-S2-02 | Good challenger response unpacks into `oracle-draft/` with exec bits; every mutant applies on base+key | golden response |
| P-S2-03 | Each `responses/bad_*` gives its expected single error code, exit `2`, and writes nothing into `*-outputs/` | table-driven |
| P-S2-04 | Truncation at 20 seeded random offsets of a good response never succeeds | property test |
| P-S2-05 | Path attacks (`../x`, `/etc/x`, backslash, NUL, case collision, over-long) rejected | table |
| P-S2-06 | SEARCH matching 0 / 2 times → right code; repair prompt has the nearest candidate | fixture |
| P-S2-07 | Fence-wrapped, CRLF, BOM and trailing-space variants unpack to identical output hashes | variants |
| P-S2-08 | `--amend` replaces only the named blocks; the union validates | two-step fixture |
| P-S2-09 | `replay` returns 0 on all stored golden turns, 1 after a deliberate parser change in a temp copy | parser mutation |
| P-S2-10 | `bundle`: static before dynamic; header hashes correct; over-limit aborts with the file table; refuses `records` paths and outside-repo `--include` | CLI |
| P-S2-11 | Sentinel equals `bundle_sha256[:8]`; another bundle's sentinel is rejected | CLI |
| P-S2-12 | `promote`: naming, `.meta.json`, `state.json` pointers, idempotence, read-only staging | CLI |
| P-S2-13 | `unpack` never executes response content (a `$(touch /tmp/pwned)` canary creates no file) | canary |
| P-S2-14 | `decide_next` Phase 1–2 table (≥ 10 states) | unit |
| P-S2-15 | Produced `proofs/*.sh` are executable and pass `bash -n`; bad shell → `E_SHELL_SYNTAX` | fixture |
| P-S2-16 | Stage 2 reuses `scope.py` (no second parser) and registers only through the registries; no edit to `cli.py`/`next.py` | grep + diff |
| `smoke_S2_01` | One real round trip: bundle → web chat of a *different family* than the Architect's → unpack; log repair rounds | manual |

### 7.8 Exit criteria

All gating proofs pass; the golden intake-to-challenger-draft pipeline runs from stored responses with no LLM; one real web round trip per persona is logged (`model`, repair rounds, characters in/out).

### 7.9 Response fixtures (generated)

The `good_*` response fixtures must unpack to the golden sprint's files byte for byte, so they are produced by `fixtures/golden/make_responses.sh` from the golden spec, key and oracle files and from stored turn directories (`fixtures/golden/turns/<role>-1/bundle.json` and `bundle.txt`, whose hash supplies each sentinel), not copied by hand. The `bad_*` and `variant_*` files are derived from the `good_*` ones by the same script. Set: `good_architect_intake`, `good_challenger`, `good_architect_review_lock`, `good_architect_review_revise`; malformed: `bad_truncated`, `bad_no_sentinel`, `bad_wrong_bundle`, `bad_path_traversal`, `bad_dup_path`, `bad_search_nomatch`, `bad_search_multi`, `bad_json`, `bad_shell_syntax`, `bad_scope_blanket`, `bad_coverage_unmapped_mutant`; cosmetic: `variant_fenced`, `variant_crlf_bom`. Each carries a header comment naming its expected result; expectations (single error code, exit code, output hashes) live in `expected.d/s2.json`.

---

## 8. Stages 3–6, comparison with My and Chi, and the multi-account question

### 8.1 Stages 3–6 in brief (detailed specs come after Stage 2 is proven)

**Stage 3 — Oracle qualification and lock.** Compose `Q1–Q5` from the Stage 1 primitives in `verify.py` (no second engine): `Q1` null base red; `Q2` key passes `G3/G5/G6`; `Q3` key passes `O1` three times; `Q4` key passes the repo suite; `Q5` mutants (gated on `Q2` and `Q3`; `killed` / `apply_error`); then `diagnostic_case`. First validate the referee on the golden oracle, including the deliberately surviving `avatar_drop.patch` → `pure_oracle_failure`; then run the real Architect ↔ Challenger ↔ qual ↔ Architect-review loop through web chats. `lock_oracle` with `diagnostic_case == none` freezes `oracle-{seq}/`, mints `contract-{seq}.json`, initializes `checklist.md` and stages `implementer-inputs/`. The `solution_key_conflict` re-qualification path (no Challenger attempt spent) is included. This Stage is also where **self-hosting** becomes possible: later Stages can be run as `actl` sprints with hidden proofs (see §12).

**Stage 4 — Budgets, escalation, first real account.** Counters (`attempts.*`, `closures_submitted`, `hard_caps_tripped`, epochs); pure `route(trigger, stage, sprint, state)` tested table-driven against Design §6.3; escalation records; the §5.4 `blocked` preconditions; `update_scope` fast path; `--strict-tripwire` by default; `actl gc`. Revisit `Layout(root, repo)` against an explicit `repo` argument at Stage 4 (O-16), with the learnings gathered by then. Create **only** the `implementer` Linux account first (own `HOME`, Cursor login, `arouter` config and `~/.cursor/{sessions,logs}` tree; `asessions` and the runner paths assume `/root/.cursor` and must be parameterized, already started in Stage 1), and verify `P` for real. The multi-account session mechanism (§8.3) takes effect here.

**Stage 5 — Curator and `E1.1–E1.6`.** Contract-tag pinning, `curator-inputs/` staging, the six Edge-1 checks as `verify.py` functions (pytest node IDs in `Graduated-Proof` trailers, per Chi), Curator driven first through the Stage 2 bridge, later through `arouter`. Include the deferred `records/<repo>/closeouts.tsv` index (memo section 5).

**Stage 6 — Hardening.** `dispatch.py` reuses `src/router/process.py` through a thin adapter instead of rebuilding tmux supervision. Remaining: `sudo -u {account}` execution, umask/group modes, Invariant `S` flags for non-Cursor engines (`--disallowedTools Agent` for Claude), `unsupported_cap` halts, `sessions.tsv` telemetry, the remaining accounts, and the `actl-live-run` wrapper (`live_run: none` stays the working mode until everything else is boring). Linger is already enabled by `process.py` (F7), so the linger vs `pkill -9 -u` collision (Design §1.3 vs §1.5/§5.5) must be resolved here: use targeted teardown (`arouter kill`, the session's process tree) instead of account-wide `pkill -9`, or drop linger for persona accounts. All Stages assume the `cursor` engine; other engines are out of scope until exercised, so `F` (cross-family) is satisfied through web chats or other models behind Cursor.

### 8.2 Agreement and disagreement with My and Chi

"My" is the first agent (Stages 1–6). "Chi" is the second (Stages 0–5 plus design corrections).

| Topic | My | Chi | Vela | Verdict |
|---|---|---|---|---|
| Build inside-out from the Implementer | Stage 1 | Stage 1 | Stage 1 | All agree |
| New Invariant-`P` skill because `SKILL.md` runs the proof suite | Yes | Yes | Yes, as a **new** skill file | All agree |
| `manual-web` is a first-class engine and survives automation | Yes | Yes | Yes | All agree |
| Delimited multi-file envelope, traversal guard, auto `chmod +x`, validation at unpack | Yes | Yes | Yes, plus sentinel with bundle id, all-or-nothing, amend mode | Agree; Vela extends |
| Code from a web LLM | Raw unified diffs + `git apply --check` | SEARCH/REPLACE then `git diff` | SEARCH/REPLACE, exact-once match | Vela follows Chi (hunk headers are fragile) |
| One verification engine reused by `Q` | Two scripts | One `verify.py` | One `verify.py` | Vela follows Chi |
| Oracle files staged for `O1` | Not discussed | Only `proofs/` and `probe.sh` | Same | Vela follows Chi |
| `G4` | Counts `def test_*` | AST + hollow-test rejection | AST | Vela follows Chi |
| Pytest node IDs in `Graduated-Proof` trailers | Not discussed | Yes | Yes (Stage 5) | Vela follows Chi |
| When `state.py` pieces appear | All at Stage 4 | Full v0 at Stage 0–2 | `seq` at 0, minimal `promote` at 2, counters/routing at 4 | Between the two |
| Target tree from day one | Ad hoc, retrofit | Full tree at Stage 0 | Full tree under `$ACTL_ROOT` at Stage 0 | Vela follows Chi |
| `ACTL_ISOLATION=local\|posix` flag and `run_as()` in Stage 0 | No | Yes | **No** | Disagree with Chi: the flip is not free (per-account `HOME`, CLI logins, group modes, `safe.directory`, tokens); abstract when the first real account is built (Stage 4) |
| Local mode enforces `P` structurally | No | Yes | **No**; convention + tripwire | Disagree with Chi |
| First real account | Stage 5 (all five) | Stage 5 (all five) | Stage 4: `implementer` alone | Disagree with both |
| Hybrid dispatch (Implementer via `arouter`, others via web) | Implied | Explicit | Explicit | Agree with Chi |
| Golden fixture with `expected.d` as the cross-stage contract | Hand-seeded toy | Hand-seeded toy | Formal fixture with good and bad implementations, a surviving mutant and a shell self-check | Vela formalizes |
| Raw-response replay, repair prompt, turn ledger | No | No | Yes | Vela only |
| `actl next` pure-function manual driver | No | No | Yes | Vela only |
| Hard-coded `/root/.cursor` breaks per-account `HOME` | Not noticed | Not noticed | Parameterized at Stage 1 | Vela only |
| `arouter` compliance anchors and the audit script as no-regression gate | Not noticed | Not noticed | Baseline + no-regression | Vela only |
| Tmux supervision and watchdog | Build in Stage 5 | Build in Stage 5 | **Already exists**; consume it; one small change (S0-R16: exit code, with explicit signal handling) | Vela differs because the layer was merged |
| Linger vs `pkill -9 -u` | Not noticed | Flagged | Confirmed present in code; fix in Stage 6 | Agree with Chi |
| Curator before or after hardening | After accounts | Stage 4, before hardening | Stage 5, before hardening | Vela follows Chi |
| Clipboard handling | `xclip`/`pbcopy` | Not discussed | Plus OSC 52 and `--paste` for SSH | Vela extends |
| Parallel branches, interface freeze, registries, Red-on-base, immutable proofs | No | No | Yes (§11) | Vela only |

### 8.3 Multi-account sessions (O-12): what to pick, and when

From Stage 4, personas run under separate Linux accounts. tmux's default socket is per user, so `arouter ps` in one account never sees another account's sessions, and `actl` (a member of every persona group, but another uid) cannot list them without `sudo`.

| Option | How it works | Pros | Cons |
|---|---|---|---|
| **A. Query per account** | `actl` runs `sudo -u {account} arouter ps` (needs a `--json` flag) and `sudo -u {account} tmux has-session` | Matches Design §5.1 wording; no shared state | A `sudo` call per poll; sudoers rule; new flag |
| **B. Shared tmux socket** | One socket path, group permission | `arouter ps` shows all | Any member can attach, kill and `send-keys` into another persona's pane: breaks `C` and `P`. **Rejected** |
| **C. File-based ledger** | Each account runs `arouter` with `ATOOLS_SESSION_DIR`/`ATOOLS_LOG_DIR` in a group-readable directory (for example `sprints/{repo}/{sprint}/runs-{role}/`); `actl` reads `<s>.json` (running) and `<s>.exit` (finished) with no `sudo` | Deterministic; least privilege; built on S0-R16 | Cannot tell "still running" from "lost" without a liveness hint; the Owner's `arouter ps` must be pointed at those directories |
| **D. One server owned by `actl`** | `actl` owns the tmux server; each pane runs `sudo -u {account} ...` | `arouter ps` shows all | The pty and server belong to `actl`, contradicting "zero LLM sessions under `actl`". Not recommended |

**Recommendation: C, with A used only as the liveness cross-check** (`sudo -u {account} tmux has-session` when the exit-code file is missing). It is a **Stage 4** decision. Stages 0–3 are single-user and unaffected, and the exit-code file (S0-R16) is what makes option C possible, so nothing needs to be picked now. At the start of Stage 4 the Owner confirms C+A (or another row) and the group-readable directory layout; whether `arouter ps` gains a `--json` output (O-13) matters only for A.

---

## 9. Decisions

### 9.1 DECIDED (do not reopen in specs)

- D-1 Stages 0–2 add no LLM automation except `dispatch-impl` through the existing `arouter`.
- D-2 `src/actl/` is a new top-level package; `bin/actl` follows the `bin/asessions` wrapper pattern.
- D-3 Stages 0–3 run in local mode on one uid; `P` is a convention (core §3).
- D-4 One `verify.py`; no per-stage duplicate verifiers.
- D-5 Code transported from web chats is SEARCH/REPLACE; `actl` generates the patch files.
- D-6 Existing files are modified only where named (Stage 0B: `process.py`; Stage 0A: `install.sh`, `README.md`; Stage 1: the two `$ATOOLS_CURSOR_HOME` edits).
- D-7 The golden fixture is the single source of expected results (`expected.d/`).
- D-8 Exit-code table of S0-R10.
- D-9 `docs/` and `audit/` are outside the build; the Owner guarantees the audit script is reachable; it is part of every no-regression check.
- D-10 The existing detached layer (`arouter -d`, `ps`, `attach`, `logs`, `kill`) is the only background mechanism; no new tmux code in Stages 0–2.
- D-11 Instructions passed to `arouter` are short, ASCII-only and bounded (S1-R9); large material is read from files.
- D-12 Scratch repositories never depend on a hook bypass; they set `core.hooksPath=/dev/null`.
- D-13 Branch protocol of §11 (worktrees, interface freeze, registries, Red on base, immutable proofs).
- D-14 Exit-code contract S0-R16 (with explicit signal traps and the unconditional kill-path overwrite) and completion protocol S1-R14. The wall-clock heuristic is dropped.
- D-15 Invocation rules: `-d` and `< /dev/null` for harness runs, session-name regex, production leaves the log/session env vars unset (S1-R9, S1-R14).
- D-16 Log retention: mechanisms stay in the suite components; the policy for sessions `actl` dispatches belongs to `actl` (copy to `runs/logs/`, delete originals after `ev` is written, `actl gc --older-than <days>`, default 30, from Stage 4). Reason: `asessions rm` works by transcript UUID, logs and exit files by session name, and nothing maps one to the other. Manual runs are pruned by the Owner.
- D-17 Terminology: atools = repo/suite name, `actl` = new component.
- D-18 The former separate task "T1" is Stage 0B; there is no separate runbook file.
- D-19 `actl_Guide-*` is maintained on the schedule of §12.
- D-20 Mutation interpretation: before implementation, reviewers apply the three-stand-in vacuity review; after implementation, a cross-family reviewer plants mutants (§10 item 5).
- D-21 Work-item tag protocol: guide §4I (PB-10). The tag is mandatory for agents (rules, skill, audit) and is checked by the `commit-msg` hook (`hooks/commit-msg`, WI-RULES-1).
- D-22 Identifiers and hashes: every SHA in schemas, state and artifacts is 40 lowercase hex; schema patterns end in `\Z` (Python `re` dialect); short prefixes are display only.
- D-23 `owner_review_triggers` takes the Design 6.3 action names (`grant_attempts`, `waive_mutant`, `update_scope`, `reopen_oracle`, `retry_live`); an Owner ruling of 2026-10-20 that replaced them was reverted because the Design wins.
- D-24 `ev.exit_code` is an integer `0..255` or `null` (`null` = interrupted or halted before a verdict; the process-level code is in `ev.session.exit_code`).
- D-25 `actl` validates schemas with the in-tree stdlib validator only and never imports `jsonschema` (closes O-1).
- D-26 The solution key is stored as `solution_key-{seq}.patch` with a `*.meta.json` sidecar (`parent` = the active spec file) and the pointer `state.active_solution_key`; promotion deduplicates by `(kind, parent, sha256)` (closes O-2).
- D-27 Detached sessions start through an ephemeral `<session>.boot.sh` trampoline (S0-R16 item 6).
- D-28 PB-2 is enforced by `P-S0-02` with an allowlist of attested blobs. Authoring-side edits to pinned paths after the pin need the Owner's approval, a `WI-S<n>-PROOF`, `WI-S<n>-SPEC` or `WI-IFACE` tag, and a Gate D delta review.
- D-29 Mutation standing rule: every stage merge re-runs the mutation harness on the Stage 0 modules with a seed not used before; a real gap in a protected file blocks the merge (`proof/stage0/SURVIVOR_ANALYSIS.md`, section G).
- D-30 (L-1) Layout H1: one `ACTL_ROOT` with three lifetimes: `records/` is STORAGE (git, actl only, chmod 700), `sprints/` is TRANSIENT working memory (deleted after closeout), `profiles/` is PERSISTENT per-persona CLI state, `repos/` holds the target repositories.
- D-31 (L-2) Names: `repos`, `records`, `sprints`, `mailboxes` (with `inbox`/`outbox`), `workspaces`, `profiles`, `tools`, `signoffs`. "Hand-off" stays the name of the act; `mailboxes/` is where it happens.
- D-32 (L-3) Sprint closeout is "archive, then delete". Keep in `records/<repo>/<tag>/closeout/`: `sessions.tsv`, the final green verification receipt, the qualification receipt, and `closeout.md` (memo section 5). Toss logs, workspaces, mailboxes and raw turns. `closeout.md` lives in `records`, not in the target repo.
- D-33 (L-4) Courier: Sync is a transport, not storage. One copy, moved not copied, every name UTC-stamped, one drawer per turn (`{stamp}__{repo}__{tag}__{role}-{n}__{purpose}`).
- D-34 (L-5) Artifact renames: `ev-NNN.json` becomes `verification-NNN.json`; `qual-NNN.json` becomes `qualification-NNN.json`. Kinds `verification` and `qualification`.
- D-35 (L-6) `tools/` at the repo top level holds process scripts: `tools/mutate.py` (mutation harness, D-29) and `tools/unfiles.py`. `tools/` joins the PB-2 immutable list.
- D-36 (L-7) `docs/plan/signoffs/` holds records of judgment-based acceptances (independent challenge verdicts, Owner approvals). Mechanical acceptances leave only receipts.
- D-37 (L-8) `profiles/<persona>` is the account's persistent state directory, and `HOME` points to it. Holds login, CLI config, transcripts, installed copies of skills and rules, and the Architect's persistent thread. Does NOT hold instructions. `actl init` writes `profiles/README.md`.
- D-38 (L-9) `ACTL_ROOT` is the only root name; `/srv/agent-graph` is an example value. Sprint tags keep Design format `YYYY-MM-DD-slug` (hyphen).
- D-39 (L-10) `Layout(root, repo="target-repo")`: one Layout per repository, so existing method signatures stay unchanged and the golden fixture works through the default. A `repo` field is recorded in `sprint.toml` and `state.json`. Every function that loads state checks it equals `layout.repo` and raises the existing integrity error (exit 3). One proof: "wrong-repo Layout rejected". The earlier narrower `Layout.target_repo(name)` amendment is superseded.
- D-40 (L-11) Revisit `Layout(root, repo)` against an explicit `repo` argument at Stage 4 (O-16), with the learnings gathered by then.

### 9.2 OPEN (spec agents propose an answer; the Owner decides where noted)

- **O-1** `jsonschema` as a dependency, or a minimal vendored validator (the repo ships no dependencies). **Closed (D-25).**
- **O-2** Name and storage of `solution_key` between Architect promotion and oracle freeze (proposal: `solution_key-{seq}.patch`). **Closed (D-26).**
- **O-3** Envelope escape for bodies containing marker lines.
- **O-4** `G4` for non-Python test suites.
- **O-5** Initial `forbidden.toml` rules.
- **O-6** Initial `secrets.toml` patterns and false-positive handling.
- **O-8** Sanitizing `failing_line` so it cannot carry large oracle excerpts (a length cap exists; character rules do not). **Closed (INTERFACES §6, O-8).**
- **O-9** Whether `bundle` offers a zipped or chunked form for chats that accept uploads.
- **O-12** Multi-account session mechanism: recommended C+A (§8.3); **Owner decides at the start of Stage 4**.
- **O-13** Whether `arouter ps` gains `--json` (only needed for option A).
- **O-14** Whether `.git/hooks/pre-commit.local` is found when committing from a worktree (unverified; do not rely on it).
- **O-15** Whether tmux propagates non-`PATH` environment variables to a pane on an already-running server (not measured; do not rely on it, F13).
- **O-16** Revisit `Layout(root, repo)` against an explicit `repo` argument at Stage 4, with the learnings gathered by then (memo L-11).

### 9.3 CLOSED

Prompt size (S1-R9, F3 measured), exit status of detached runs (S0-R16, S1-R14), log retention (D-16), whether PATH stubs reach a pane (F13 measured).

---

## 10. Handoff checklist for the spec and proof agents

1. Read the core document and this addendum completely; read the Design sections cited by each requirement.
2. Produce `spec-S0.md` (covering workstreams 0A and 0B, and a draft of `INTERFACES.md` including its machine-readable block), `spec-S1.md`, `spec-S2.md`, each with: requirement text per ID, interfaces (signatures, CLI synopsis, file formats), error and exit behaviour, a traceability table (`requirement → proof ID`), an ambiguity register and `Proposed decisions` (answers to OPEN items and any conflict with the Design).
3. Produce the proof sets under `proof/stage{0,1,2}/`, the gating suites (`run_suite_actl_s0.sh`, `run_suite_exit_code.sh`, `run_suite_actl_s1.sh`, `run_suite_actl_s2.sh`), and pytest tests; mark LLM-dependent checks `smoke_`. Every suite must be Red on base (PB-1), failing with `FAIL:` lines that name the missing feature, not with harness errors (a missing tool is exit `4`).
4. Produce the golden fixture (§5.8), the stubs (§6.6), the generated response fixtures (§7.9) and the `expected.d` fragments.
5. Do not implement `actl` in the authoring pass. Proof quality is checked in two phases (D-20). **Before implementation:** each proof is reviewed for vacuity against three stand-ins: an empty module, an always-succeed stub (functions return success, empty or permissive values) and an always-fail stub (functions raise or return failure); a proof that passes against a stand-in it should reject is fixed. **After implementation, before merge:** a reviewer from a different model family than the implementer plants realistic mutants (flip a comparison, skip a check, drop a branch, off-by-one) in each new module and confirms at least one proof goes red per mutant; survivors become new proofs (the Design's `E1.5` idea).
6. Report ambiguities rather than assume. A spec that silently resolves a Design conflict is rejected.

---

## 11. Branch protocol and path to progress

### 11.1 Branches and dependencies

| Branch (worktree) | Covers | Starts | Merges |
|---|---|---|---|
| `wip/s0a-foundations` | S0-R1 … R15 | After the authoring pass | First (any order with 0B) |
| `wip/s0b-exit-code` | S0-R16 | After the authoring pass | First (any order with 0A) |
| `wip/s1-verifier` | Stage 1 | After 0A and 0B are on `main` | After rebase; either order with Stage 2 |
| `wip/s2-bridge` | Stage 2 | After 0A is on `main` (0B not needed) | After rebase; either order with Stage 1 |

Runbook titles: `actl_s0`, `exit_code`, `actl_s1`, `actl_s2`; suites `proof/run_suite_<title>.sh`.

### 11.2 Rules

- **PB-1 Red on base.** Every gating suite exits `1` on the branch's starting commit; a suite that is green before work starts is rejected.
- **PB-2 Immutable proofs.** The implementer's Runbook lists `proof/`, `fixtures/`, `test/actl/`, `src/actl/INTERFACES.md` and `tools/` as immutable. After every run `git diff --name-only <start>..HEAD -- proof fixtures test/actl src/actl/INTERFACES.md tools` MUST be empty, else the run is discarded.
- **PB-3 Registries and fragments** (S0-R13, S0-R14): after Stage 0 no Stage edits `cli.py`, `next.py` or another Stage's `expected.d` fragment.
- **PB-4 Interface freeze** (S0-R15): changes after Stage 0 need the Owner's approval.
- **PB-5 Merge gates.** Every merge: the engines, session-persistence and exit-code suites green, the compliance audit green (`audit/atools-compliance_audit.sh --cursor` exits 0 and `--self-test` passes, SYNC-01..03 pass; skips are expected), the stage suites green, empty `diff -u` between the repo and installed copies of the hook, the rules and the worker skill; Stages 1 and 2 also rebase on `main` and run `run_suite_actl_s0.sh`; every implementation merge also passes the post-implementation mutation review (§10 item 5).
- **PB-6 Unique names** for sessions (`s0a-foundations`, `s0b-exit-code`, `s1-verifier`, `s2-bridge`), runbook titles and scratch directories (`mktemp -d`).
- **PB-7 Run from inside the worktree** (detached runs inherit the cwd; F1, F4).
- **PB-8 Hygiene.** Archive or delete `~/.cursor/logs/<session>.log` and the exit-code files when a task ends; `asessions rm` does not remove them.
- **PB-9 Author independence.** Spec/proof authors use a different model family from the implementing agent where available (the Design's `F`, applied to the build); the challenger differs from the authors.
- **PB-10 Work-item tags.** Every commit subject ends with one `(WI-<id>)` tag in the format defined in the guide §4I: `WI-S<n>-R<k>` for implementation, `WI-S<n>-SPEC` / `WI-S<n>-PROOF` / `WI-IFACE` for the authoring pass, `WI-<AREA>-<n>` for housekeeping.

### 11.3 Per-branch execution (how agents run it)

```bash
git worktree add ../atools-s1 -b wip/s1-verifier && cd ../atools-s1
cp spec-S1.md /tmp/Runbook_actl_s1.md
bash proof/run_suite_actl_s1.sh; echo $?          # must be 1 (Red on base)
arouter -d -n s1-verifier -t 45m balanced \
  "Follow the 'atools-repair' skill. Specification: /tmp/Runbook_actl_s1.md. Designated test suite: bash proof/run_suite_actl_s1.sh. Tag commits (WI-<id>)." < /dev/null
arouter ps ; arouter logs -f s1-verifier          # observe; arouter attach s1-verifier to join
```

Then re-run the suite yourself, check PB-2, and merge through PB-5. Operational details live in `actl_Guide-*`.

### 11.4 Path to progress

1. **De-risk checks** (done Oct 14 on the VPS; results are facts F3, F13, F16). Remaining measurement: the SIGTERM-then-SIGHUP group case (F16) and O-15, folded into the 0B authoring pass.
2. **Authoring pass** (parallel agents; prompts in `actl_Handoff_Prompts-*`): `INTERFACES.md` first; after the Owner accepts it, the Stage 0 (0A and 0B), Stage 1 and Stage 2 specs, proofs and fixtures in parallel; integrate; run every gating suite (each must exit `1`) and the golden self-check (must exit `0`); cross-family challenge; Owner gate on the OPEN items; commit to `main`.
3. **Stage 0:** implement 0A and 0B on two worktrees in parallel; merge through PB-5; run `actl doctor` and keep `baseline.json`. **Guide update #1 (§12).**
4. **Stages 1 and 2:** implement on two worktrees in parallel after Stage 0; merge through PB-5. **Guide updates #2 and #3.**
5. **Stage 3:** qualification loop; decide whether later Stages are built as `actl` sprints with hidden proofs (self-hosting). **Guide update #4.**
6. **Stages 4–6** as in §8.1, each followed by its guide update.

Fallback if 0B slips: Stage 1 specs and proofs still proceed; Stage 1 *implementation* waits, because S1-R14 reads the exit-code file. `dispatch-impl --mode foreground` (blocking, real exit code, not protected against the death of the harness) may be used in unit tests meanwhile.

---

## 12. TODO — keeping `actl_Guide-*` current

The guide tells agents how to run loops with the suite. Update it at these points; each update is a small task for a documentation agent, reviewed by the Owner, and is listed in the Stage's exit criteria.

### 12.0 Immediate edits (rename and fold of the former T1)

Done at lock: the guide was renamed to `actl_Guide.md`, the former T1 references were replaced by Stage 0B (S0-R16), the PATH-stub and signal-semantics statements were aligned with F13 and F16, and the cross-references point to addendum §8.3 and §11.

### 12.1 Update schedule

| Trigger | Weight | What changes in the guide |
|---|---|---|
| **After Stage 0 (0A and 0B merged)** | Small | Flip the exit-code file from **[planned]** to available (§4F, §6, §8: add `run_suite_exit_code.sh` and `run_suite_actl_s0.sh`); add `actl doctor` as the pre-flight step and `actl sprint new` for sprint setup; document the golden fixture, the worktree/branch conventions and the merge gate (PB-5); remove "missing file = lost" caveats that no longer apply |
| **After Stage 1** | **Major** | Add a second loop beside the public-proof loop: the hidden-proof loop with `actl dispatch-impl`, `actl wait`, `actl verify-impl`, `actl next`, the `actl-implementer` skill (the agent never runs proofs), `closure` and `prior_attempt`, log copy to `runs/logs/`, tripwire warnings; state which loop to use for what (public proofs for building tooling, hidden proofs once the oracle exists); update §7 limitations (Invariant `P` still a convention) |
| After Stage 2 | Medium | Add the web-chat workflow: `actl bundle`, `unpack`, `promote`, `replay`, repair prompts, the envelope format, recording `--model` for cross-family checks; handoff requests for spec agents can be produced with `bundle` |
| **After Stage 3** | **Major** | Oracle qualification (`Q1–Q5`) and contract minting replace the manual "Red on base" check; Runbook ↔ spec/contract mapping; the self-hosting decision (build later Stages as `actl` sprints) and how to run them |
| After Stage 4 | Medium | The `implementer` account, per-account directories (O-12 outcome), strict tripwire by default, escalations and operator actions, `actl gc` and log retention, updated limitations |
| After Stage 5 | Small | Closeout flow: curation plan review, graduated tests |
| After Stage 6 | Medium | Remaining accounts, Invariant `S` flags and other engines (only if exercised), live-run handling, linger/teardown policy |

### 12.2 Procedure for each update

1. Re-verify every command in the guide against `--help` output and the merged code; do not copy from the plan.
2. Mark changed sections **[updated]**, new ones **[new]**, and retire **[planned]** markers.
3. Run the guide's commands once in a scratch worktree.
4. Refresh the baseline commit and version line, and the open-item register.
5. The Owner reviews; the update merges before the next Stage's implementation starts.

*End of addendum.*
