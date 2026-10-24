# actl Guide: Running Agent Loops with the atools Suite (and, as it lands, actl)

**Revision:** Oct 24, 2026. **Baseline:** `atools` `main` at `6b61504` (`VERSION` v0.1.8; Stage 0 closed, tag `stage-0-verified`), which adds the modular audit runner (`4da9394`), the installed-copy sync checks and the hardened worker protocol on top of persistent session supervision (`5cb7f30`), the interactive sessions explorer (`759a0ca`) and help/listing fixes (`a9b3a4e`). The owner verified `proof/run_suite_engines.sh` and `proof/run_suite_session_persistence.sh` (11/11). Marks: **[updated]**, **[new]**, **[planned]** (specified but not yet merged).

**Where this guide fits.** It tells agents how to run loops that get the build Stages implemented. The plan lives in `actl_Build_Plan-Stages0to2.md` (core) and `actl_Build_Plan-Stages0to2_addendum.md` (Stage specifications, branch protocol in its §11, guide update schedule in its §12); the long-term design is `actl_Design.md`. This guide is updated on the schedule in §10 below.

**Naming.** "atools" is the name of the repository and suite, not a module. Its components are `arouter`, `asessions`, the engine adapters, hooks, rules, skills, the proof suites and the audit script; `actl` (build in progress) joins them.

---

## 1. Overview & Operational Tenets

Manual patch application through web chats is error-prone, hallucination-heavy and unmetered. The suite automates repairs with three coupled parts:

1. **Orchestrator:** `arouter` (tier routing, engine dispatch, watchdog, detached and streamed sessions, process commands), `asessions` (transcripts, token economics, interactive explorer), and the tier entrypoints `acheap`, `abalanced`, `asmart` (wrappers that call `arouter`).
2. **Agent runtime:** headless CLI agents. **Only the Cursor Agent CLI engine is production-ready**; the other adapters are boilerplate stubs (§3D).
3. **Deterministic objective function:** bash proof suites (`proof/run_suite_<title>.sh`) that exit `0` or `1` and are the agent's only valid termination signal.

### The Four Operational Tenets

1. **Decoupled model tiering.** Tiers (`cheap`, `balanced`, `smart`) are independent of prompts.
2. **Exit codes as objective functions.** Only `exit 0` from an unmocked script counts as success.
3. **Executable specification grounding.** A pre-verified specification file named in the prompt (by convention `/tmp/Runbook_<title>.md`) keeps the model on task.
4. **Hard blast-radius envelopes.** Immutable directories, isolated worktrees, wall-clock watchdogs, tool allow/deny lists and pre-commit branch guards bound every run.

### Taxonomy

| Concept | Role |
|---|---|
| Assertion-gated | Discrete checks returning exit `0` that gate progress |
| Test-driven Red-Green | The suite must fail on the base (Red) before it can prove the fix (Green) |
| Red-Green harness | `proof/run_suite_<title>.sh` and logs in `proof/out/` |
| Eval-driven repair | Run, read the failing log, patch minimally, re-run until zero failures |

---

## 2. Architecture & Runtime Mechanics **[updated]**

```text
 operator ──► tier entrypoint (acheap | abalanced | asmart)  ──exec──►  arouter
 arouter: resolves tier→model (~/.cursor/arouter-config.json), parses -d -n -t --engine,
          buffers piped stdin ($PIPED_INPUT → "Context / Input:"), then picks one of three paths:

  (1) -d / --detach ............ tmux session, returns immediately
  (2) stdout is a TTY + cursor . same tmux session, then auto-streams it to your terminal
  (3) otherwise ................ legacy foreground: timeout --foreground, real exit code, no tmux

  tmux paths: src/router/process.py writes <SESSIONS>/<s>.run.sh plus a <s>.boot.sh trampoline (it execs the runner) and starts the trampoline via
              `tmux new-session -d -s <s> -c <cwd>`; console mirrored to <LOGS>/<s>.log (pipe-pane)
  runner:     /usr/bin/timeout --foreground -k <grace> <duration> engines/<name>.sh ...
  agent:      headless CLI, governed by ~/.cursor/cli-config.json, global rules, pre-commit hook
  proof suite ◄── loop until exit 0 ──► git status, stop
```

`<LOGS>` is `$ATOOLS_LOG_DIR`, else `/root/.cursor/logs` when `/root/.cursor` exists, else `~/.cursor/logs`. `<SESSIONS>` is `$ATOOLS_SESSION_DIR`, else `~/.cursor/sessions`.

**Tier argument.** The first positional argument is a tier only if it is `cheap`, `balanced`, `smart`, `auto` or an `a`-prefixed form (`acheap`, `abalanced`, `asmart`); otherwise the tier is `auto` and every positional argument is the prompt. `arouter --get` without a tier prints the `auto` mapping.

### A. Security and process supervision

- **Watchdog (always on).** Every engine runs under `/usr/bin/timeout --foreground -k <grace> <duration>`. Default `12m` (`ATOOLS_TIMEOUT`), grace `3s` (`ATOOLS_KILL_GRACE`); override with `-t/--timeout` (`45s`, `12m`, `1h30m`, bare minutes). On exit `124` or `137` a `[TIMEOUT]` notice is printed (and appears in the log).
- **Permissions.** `install.sh` merges an allowlist (read-only commands, git inspection/branching/commit, `pytest`, `bash proof/run_suite_*.sh`) and a denylist (`rm -rf /`, `git push*`, `git clean -fdx`, `mkfs*`, `dd if=*`, hook bypasses) into `~/.cursor/cli-config.json`; anything else goes to Cursor's `--auto-review` classifier.
- **Branch boundary.** A global pre-commit hook blocks commits outside `wip/*`; the global rules forbid `git push`.
- **Compliance anchors.** `bin/arouter` carries "compliance audit anchors" (`--auto-review`, `--trust`); `audit/atools-compliance_audit.sh --cursor` runs the 49-check audit (including SYNC-01..03: installed copies must match the repo) and `--self-test` verifies the audit itself (spec in `audit/README.md`).
- **Linger.** Every session start runs `loginctl enable-linger $USER` (best effort) so background runs survive logout.

### B. The runtime feedback cycle

1. **Extraction:** the agent reads the specification named in the prompt (by convention `/tmp/Runbook_<title>.md`).
2. **First pass:** `python3 -m compileall`, then `bash proof/run_suite_<title>.sh`.
3. **Diagnosis:** read only the failing `proof/out/<test>.log`.
4. **Surgical patch:** edit the needed lines, never whole files.
5. **Termination:** when all checks pass, run `git status` and stop.

### C. The three execution paths **[updated]**

| | (1) Detached `-d` | (2) Interactive TTY, Cursor engine | (3) Non-TTY or other engine |
|---|---|---|---|
| Process | tmux session; command returns at once | tmux session, output auto-streamed | Child process of the caller |
| Survives SSH drop / closed laptop | Yes | Yes (the stream is only a viewer) | No |
| Watchdog | `-t`, inside the runner | same | `-t`, via `timeout --foreground` |
| Exit status visible to the caller | Not from the spawn call (see §4F) | Not from the stream | Yes, propagated |
| Working directory | Caller's cwd (`tmux -c`) | same | Caller's cwd |
| Log | `<LOGS>/<s>.log` | same | Terminal / caller's redirect |

Interactive Cursor runs are tmux-backed too, and `asessions` does show running sessions (§4D). A detached run's runner removes itself (`trap cleanup EXIT`) and its metadata; the tmux session self-destructs (`remain-on-exit off`). The console log stays.

"Async" works as shorthand; the precise term is **detached** (background) execution, since "async" also means asynchronous I/O.

---

## 2b. actl (Stage 0) **[new]**

`actl` lives in `src/actl/` and starts with `bin/actl`; `install.sh` does not link it yet, so run `~/atools/bin/actl`. Stage 0 provides:

| Command | Purpose |
|---|---|
| `actl doctor [--refresh] [--json]` | Environment baseline. Runs the engines, persistence and exit-code suites and the audit (minutes), writes `$ACTL_ROOT/baseline.json` on the first run only, exits `4` if `tmux` or the audit script is missing |
| `actl init --target <path-or-url> [--json]` | Create the tree under `$ACTL_ROOT` (default `~/actl-graph`) and clone the target repository (for a local path the base is the source repo's checked-out branch) |
| `actl sprint new <slug> [--spec FILE] [--json]` | Mint `YYYY-MM-DD_<slug>` (`$ACTL_TODAY` overrides the date), pin `base_sha`, create `runs/state.json`, `runs/sessions.tsv` and a draft `sprint.toml` |
| `actl next --sprint <TAG> [--json]` | Print the next action (a pure function of the sprint files) |

Exit codes for every command: `0` ok, `1` red, `2` usage or schema error, `3` halt, `4` environment. Every command accepts `--json` and honours `NO_COLOR`. Contract: `src/actl/INTERFACES.md`; specification: `docs/plan/spec-S0.md`; proofs: `bash proof/run_suite_actl_s0.sh` and `PYTHONPATH=src python3 -m pytest -q test/actl`; golden fixture: `fixtures/golden/`. In local mode (one uid) Invariant P is a convention.

## 3. Installation & Setup **[updated]**

### A. Cursor Agent CLI

```bash
curl https://cursor.com/install.sh | bash
which agent || export PATH="$HOME/.local/bin:$PATH"
agent --version
```

### B. Install the suite with the installer

```bash
git clone git@github.com:<org>/atools.git ~/.atools
cd ~/.atools && ./install.sh
```

`install.sh` symlinks `arouter` into `~/.local/bin` and `/usr/local/bin`, writes `acheap`/`abalanced`/`asmart` wrappers (with built-in `--help`), copies `hooks/pre-commit` and `hooks/commit-msg` to `~/.config/git/hooks/` and sets `core.hooksPath`, installs the global rules, copies the repair skill, merges Cursor permissions, then runs the proof suite. Do not create an `arun` binary or symlink `agent-router-cursor.py` / `agent-sessions.py`; they belong to the retired layout. `tmux` must be installed.

### C. Map tiers (CLI only)

```bash
arouter --set cheap gemini-3.8-flash-low
arouter --set balanced gemini-3.8-flash-medium
arouter --set smart gemini-3.8-flash-high
arouter --show
```

### D. Engines: what is real today

| Engine (`--engine`) | Adapter | Status |
|---|---|---|
| `cursor` (default) | `engines/cursor-agent.sh` → `agent --auto-review --trust --model` | **Supported, in daily use** |
| `claude-code`, `openai-codex`, `google-agy`, `aider`, `mistral-vibe` | `engines/*.sh` | **Boilerplate stubs**: syntax, executable bit and "exit 127 when the CLI is missing" are tested; never exercised for real. `claude-code.sh` uses `--dangerously-skip-permissions`. Path (2) above only triggers for the `cursor` engine |

Select with `--engine <adapter>` or `ATOOLS_ENGINE`.

### E. The worker skill (`atools-repair`)

Anti-recursion boundary: the loop runs under one worker skill, `.cursor/skills/atools-repair/SKILL.md`, which deliberately excludes the dispatchers so the agent cannot start nested loops.

```markdown
# Skill: atools Eval-Driven Repair
## Objective
Execute iterative code changes against deterministic test suites without user intervention.
## Operational Protocol
1. Read the provided specification and implementation requirements.
2. NEVER edit, create, modify or mock oracle files, proofs or test fixtures.
3. All progress must be staged and committed on an isolated wip/* branch.
4. Commit format: `<type>(<scope>): <summary> (WI-<id>)` with non-empty `Why:` (bare SHAs), `What changed:` (`- file:` bullets), and `Result:` (metrics/invariants) sections. Never use `--no-verify` or touch other worktrees; adapt from hook stderr if rejected.
5. Execute the designated test suite directly via bash or python runner without modifying file permissions.
6. If failures occur, inspect test logs, apply minimal surgical fixes, and re-run.
7. Once all checks output PASS, verify branch isolation with git status and conclude.
```

---

## 4. Execution Patterns **[updated]**

### A. Preparing a run

1. Create an isolated worktree on a `wip/*` branch and `cd` into it: `git worktree add ../<name> -b wip/<task> && cd ../<name>`. Branch names, merge gates and parallel rules for the build are in the addendum §11.
2. Write `/tmp/Runbook_<title>.md`: goal, files in scope, **immutable paths** (always `proof/`, fixtures and tests that define "done"), the designated test suite (which must already be executable; the skill no longer changes permissions), and the work-item tag to use in commits, `(WI-<id>)` (convention in §4I).
3. Confirm the suite is **Red on base**: it must exit `1` before the agent starts.

### B. Foreground run

```bash
abalanced -t 45m "Follow the 'atools-repair' skill. Specification: /tmp/Runbook_<title>.md. Designated test suite: bash proof/run_suite_<title>.sh. Tag commits (WI-<id>)."
```

In a terminal this streams a tmux-backed session (path 2). `asmart` is for architectural work. Piped context is accepted: `git diff | asmart "Review staged changes"`. Do not wrap the call in another `timeout`.

### C. Detached run

```bash
cd ../<worktree>
arouter -d -n s1-verifier -t 45m balanced "Follow the 'atools-repair' skill. Specification: /tmp/Runbook_actl_s1.md. Designated test suite: bash proof/run_suite_actl_s1.sh. Tag commits (WI-<id>)." < /dev/null
```

| Flag | Meaning |
|---|---|
| `-d`, `--detach` | Spawn a headless tmux session (`remain-on-exit off`) and return |
| `-n`, `--name <tag>` | Session name; default `arun-<tier>-<timestamp>`. Use only lowercase letters, digits and hyphens: the name is also a file name stem and tmux rewrites some characters |
| `-t`, `--timeout <dur>` | Watchdog limit; default `12m` |
| `--engine <adapter>` | Backend; default `cursor` |

| Command | Behaviour |
|---|---|
| `arouter ps` / `list` | Live table (SESSION, TIER, MODEL, ELAPSED, LOG) from `tmux list-sessions`; a session is shown if it has metadata, a log, or an `arun-` name |
| `arouter attach <session>` | Stream proxy over the log (strips `\x1b[3J` and OSC colour queries); raw `tmux attach -t <session>` is also available |
| `arouter logs <session> [-f]` | Show or `tail -f` the console log |
| `arouter kill <session>` | SIGTERM to the pane process, `tmux kill-session`, then SIGKILL |

While streaming, press `Ctrl+C` for the menu: `Enter`/`b` leaves the run in the background, `r` resumes the stream, `k` kills, `s` opens the sessions explorer; a second `Ctrl+C` kills at once.

Working directory: the run starts in the dispatching cwd, so dispatch from inside the worktree. Piped stdin: `arouter` reads stdin with `cat` whenever stdin is not a TTY. **In scripts and harnesses always give it input or redirect `< /dev/null`, otherwise it waits for EOF forever.** The piped text is embedded in the prompt argument.

Size limit: the whole prompt is passed as one command-line argument several times over (JSON-serialized with non-ASCII escaped, shell-quoted into the runner, then to the engine). A single Linux argument is limited to 131071 bytes (measured on the VPS: 131071 accepted, 131072 refused), counted on the JSON-escaped size, so keep instructions small and ASCII-only (the build caps them at 100,000 bytes) and put large material in files the agent reads.

An argument equal to `help`, `-h` or `--help` anywhere on the command line prints help instead of running.

### D. Observing runs and history

```bash
arouter ps                       # what is running
arouter logs -f <session>        # follow the console
asessions                        # on a TTY: interactive explorer (active sessions + last 5 runs)
asessions --list                 # static history table (for pipelines)
asessions <uuid|#> [--summary]   # transcript, or metadata and token economics
asessions rm [-n] [-f] <uuid|#>  # dry-run / force deletion of transcripts and chat records
```

Explorer keys: arrows or `w`/`s` to move, `Enter` to open a history item or attach to an active one, `d` to delete a history item (confirmation), `k` to kill an active session, `h` all history, `b` back, `q` quit. Console logs are raw PTY captures (colours and TUI frames); strip ANSI sequences before searching them.

### E. After the run (always)

```bash
bash proof/run_suite_<title>.sh   # re-run yourself; never trust the agent's claim
git diff --name-only <base>..HEAD -- proof/ fixtures/   # must be empty if those paths are immutable
```

### F. Exit status of a detached run **[updated: Stage 0B, requirement S0-R16]**

The runner records its exit status in `<SESSIONS>/<session>.exit` (Stage 0B, S0-R16): one integer, written atomically from the runner's EXIT trap before cleanup. Meanings: `0` success, `124`/`137` watchdog, `127` missing CLI, `143` after `arouter kill` (written once the pane processes are gone; if they are not gone the file is removed and the run counts as lost). A stale file from a reused name is removed at spawn. A runner signalled from outside records 143 (TERM), 129 (HUP) or 130 (INT) once its foreground child has ended; a SIGKILLed or lost session leaves no file. Poll like this:

```bash
while tmux has-session -t "$S" 2>/dev/null; do sleep 2; done
cat "${ATOOLS_SESSION_DIR:-$HOME/.cursor/sessions}/$S.exit"   # missing file = session lost
```

### G. Cleanup scope

- The runner script and metadata JSON remove themselves.
- `asessions rm` removes transcripts (`~/.cursor/projects/*/agent-transcripts/*`) and chat/SQLite records (`~/.cursor/chats/*/*`) only. It cannot map a UUID to a session name, so it does **not** remove `<LOGS>/<session>.log` (or `.exit`).
- Prune console logs yourself, for example `find ~/.cursor/logs -name '*.log' -mtime +14 -delete`; `actl` will own this for sessions it dispatches.

### H. Parallel runs

One worktree, one branch, one runbook title and one `-n` name per run; suites use `mktemp -d` scratch directories. Mind model rate limits and VPS load.

---

### I. Work-item tags & mechanical commit protocol

Every commit subject ends with exactly one work-item tag `(WI-<id>)`. The rules file, the worker skill, the audit (HARD-05, SKILL-08), and the mechanical `hooks/commit-msg` hook require it. `WI` means *work item*. Ids:

| Tag | Meaning | Example |
|---|---|---|
| `WI-S<n>-R<k>` | Implements requirement `R<k>` of Stage `<n>` (the addendum ids `S0-R16`, `S1-R9`, `S2-R4`; workstreams 0A and 0B both use `S0`) | `feat(router): persist exit code of detached runs (WI-S0-R16)` |
| `WI-S<n>-SPEC`, `WI-S<n>-PROOF` | Authoring pass for Stage `<n>`: specification text; proofs, tests, fixtures and stubs | `test(stage0): add exit-code proof suite (WI-S0-PROOF)` |
| `WI-IFACE` | `src/actl/INTERFACES.md` | `docs(actl): freeze interfaces (WI-IFACE)` |
| `WI-<AREA>-<n>` | Housekeeping, with `AREA` one of `AUDIT`, `DOCS`, `RULES`, `TOOLS` (router, sessions, engines, installer) and `n` the next free number | `docs(plan): refresh baseline (WI-DOCS-2)` |

Rules: one tag per commit (name any other requirements in the body); the tag goes at the end of the subject line; do not retag old commits. Next free housekeeping number: `git log --format=%s | grep -o '(WI-AUDIT-[0-9]*)' | sort -V | tail -1` (change `AUDIT` as needed). Used so far (highest per area on `main`): `AUDIT-3`, `DOCS-4`, `RULES-1`, `TOOLS-2`.

**Mechanical commit format** (`hooks/commit-msg`): subject must match `<type>(<scope>): <summary> (WI-<id>)` where type is one of `feat|fix|refactor|perf|test|proof|audit|eval|spec|chore|docs` (synonyms rejected with a canonical hint). Scope must name a module/subsystem (never `s0`, `stage*`, `v1.2`, `wip`, `main`, `master`). Body must include non-empty `Why:` (cite prior work as bare SHAs like `85523a0`, never `commit <sha>`), `What changed:` with at least one `- <file>: <change>` bullet, and `Result:` with metrics/invariants. Never bypass with `--no-verify` / `-n`.

**Parallel worktree merge policy:** never checkout, rebase, or mutate a branch checked out in another linked worktree. Integrate exclusively via `--no-ff` merge gates on the integration branch.

## 5. Machine-Wide Safety Configuration **[updated]**

Sections 5A and 5B are applied by `install.sh`.

### A. Global rules (`~/.cursor/rules/git-safety.md`)

1. Never commit on `main`/`master`/release branches; work on `wip/*`.
2. All experiments on isolated `wip/*` branches.
3. Never `git push` or modify remote refs.
4. Never commit until tests/proofs pass; end every run with `git status`.
5. Commit protocol: every subject is `<type>(<scope>): <summary> (WI-<id>)` and the message has `Why:`, `What changed:` and `Result:` sections; never bypass hooks (`--no-verify`, `-n`) or touch `core.hooksPath`.
6. Never check out, rebase or mutate a branch that is checked out in another linked worktree; integrate across worktrees with `--no-ff` merges on the integration branch.

### B. Permissions (`~/.cursor/cli-config.json`)

Allowlist, denylist, and the `--auto-review` classifier for the rest. Re-run `./install.sh` to re-merge non-destructively.

### C. Dual Git hooks (`pre-commit` and `commit-msg`)

`install.sh` copies `hooks/pre-commit` and `hooks/commit-msg` to the global path, so repo and installed copies are identical after each install; verify with `diff -u hooks/pre-commit ~/.config/git/hooks/pre-commit` and `diff -u hooks/commit-msg ~/.config/git/hooks/commit-msg`. The pre-commit hook blocks commits outside `wip/*` and delegates to `.git/hooks/pre-commit.local` when present. The commit-msg hook enforces the mechanical subject/body protocol (§4I). Neither has a `/tmp` bypass, so scratch repositories under `/tmp` are subject to the policy: commit on a `wip/*` branch or use `git -c core.hooksPath=/dev/null commit ...`.

---

## 6. Infrastructure Replication Reference **[updated]**

| Component | Location | Function |
|---|---|---|
| Agent CLI | `agent` (`~/.local/bin`) | Cursor Agent binary |
| Router | `bin/arouter` → `~/.local/bin`, `/usr/local/bin` | Tiers, engines, watchdog, three execution paths, process commands |
| Session runtime | `src/router/process.py` | Runner generation, tmux spawn, ps/attach/logs/kill, metadata, linger |
| Runner scripts | `<SESSIONS>/<s>.run.sh`, `<SESSIONS>/<s>.boot.sh` | Ephemeral; remove themselves (`boot.sh` execs `run.sh`) |
| Session metadata | `<SESSIONS>/<s>.json` | Tier, model, engine, start time, prompt, watchdog; removed on exit |
| Exit status | `<SESSIONS>/<s>.exit` | Integer exit status (Stage 0B, S0-R16); survives cleanup; not removed by `asessions rm` |
| Console logs | `<LOGS>/<s>.log` | Raw PTY capture; not removed by `asessions rm` |
| Tier entrypoints | `/usr/local/bin/{acheap,abalanced,asmart}` | Wrappers with `--help`, delegating to `arouter <tier>` |
| Session auditing | `bin/asessions` → `src/sessions/` | Explorer, static list, transcripts, economics, `rm` |
| Engines | `engines/*.sh` | Cursor supported; others stubs |
| Worker skill | `.cursor/skills/atools-repair/SKILL.md` | Headless repair protocol |
| Global rules, guardrails, hooks | `~/.cursor/rules/`, `~/.cursor/cli-config.json`, `~/.config/git/hooks/{pre-commit,commit-msg}` | Policy |
| Tier mapping | `~/.cursor/arouter-config.json` | Edit only via `arouter --set` |
| Proof suites | `proof/run_suite_engines.sh`, `proof/run_suite_session_persistence.sh`, `proof/run_suite_exit_code.sh`, `proof/run_suite_actl_s0.sh`, `proof/run_suite_commit_msg.sh`; `pytest test/actl` | engines 5, persistence 6, exit-code 10, Stage 0A gate 19, commit-msg 16 assertions plus the pytest suite |
| Compliance audit | `audit/atools-compliance_audit.sh --cursor` | 49 checks (18 planned SKIPs); `--self-test`; spec in `audit/README.md` |
| actl CLI (Stage 0) | `bin/actl` → `src/actl/`, `schemas/`, `config/graph.toml` | `doctor`, `init`, `next`, `sprint new`; run it from the repo, `install.sh` does not link it |

---

## 7. Known Limitations

- The skill forbids editing proofs and fixtures but still lets the agent run the designated suite, so where the agent must not see the checks this loop is not sufficient (fine for tooling with public proofs).
- One OS user: `arouter ps` sees only that user's tmux server; paths default to `/root/.cursor` when it exists.
- The persistence suite starts a real detached run (`cheap`, prompt `sleep 1`, `-t 5s`), hard-codes `/root/.cursor/logs`, and so needs `tmux` and the `agent` CLI installed. It does not test working-directory propagation.
- For deterministic detached tests use a private tmux server (`TMUX_TMPDIR`, so your real sessions are never touched), private `ATOOLS_LOG_DIR`/`ATOOLS_SESSION_DIR`, and stubs for `agent` and `loginctl` first in `PATH` (as the Stage 0B suite `proof/run_suite_exit_code.sh` does). tmux gives a new pane the dispatching client's `PATH` (measured on the VPS), so PATH stubs work with a fresh or an existing server; do not rely on other environment variables reaching the pane.
- Only the Cursor engine is exercised; nothing yet restricts sub-agents or separates accounts.
- Console logs accumulate until pruned; the early bytes of a run may be missed because `pipe-pane` is attached after the session starts.

## 8. Verification

```bash
bash proof/run_suite_engines.sh
bash proof/run_suite_session_persistence.sh
bash audit/atools-compliance_audit.sh --cursor
bash audit/atools-compliance_audit.sh --self-test
diff -u hooks/pre-commit ~/.config/git/hooks/pre-commit
bash proof/run_suite_exit_code.sh
bash proof/run_suite_actl_s0.sh
bash proof/run_suite_commit_msg.sh
PYTHONPATH=src python3 -m pytest -q test/actl
diff -u hooks/commit-msg ~/.config/git/hooks/commit-msg
```

All must pass (and the diff be empty) after every change to `bin/`, `src/router/`, `src/sessions/`, `engines/`, `hooks/`, `install.sh` or the skill.

## 9. Open-item register **[updated]**

| Item | Status |
|---|---|
| Start, attach, detach, kill; `ps`; watchdog in tmux; logs; finished vs running | Resolved (§4) |
| Piped stdin in detached runs; cwd and worktrees | Resolved (§4C) |
| `asessions rm` scope | Resolved (§4G) |
| Installed vs repo hook | Resolved: synced by `install.sh` (§5C) |
| Exit status of detached runs | Resolved (§4F, Stage 0B) |
| Log retention owner | **Decided:** mechanisms stay in the suite components; policy for `actl`-dispatched sessions belongs to `actl` |
| Sessions across several OS accounts | **Open:** options and a recommendation are in the addendum §8.3; decided at the start of Stage 4 |
| `.git/hooks/pre-commit.local` inside worktrees | Unverified; do not rely on it |

## 10. Keeping this guide current

The guide is updated when a Stage lands, on the schedule in the addendum §12.1: small after Stage 0 (retire the **[planned]** markers, add `actl doctor`, `run_suite_exit_code.sh` and `run_suite_actl_s0.sh`; applied Oct 24, 2026); **major after Stage 1** (add the hidden-proof loop: `actl dispatch-impl`, `wait`, `verify-impl`, `next`); medium after Stage 2 (`bundle`, `unpack`, `promote`, `replay`); **major after Stage 3** (oracle qualification and the self-hosting decision); then as Stages 4–6 ship. Each update follows the procedure in the addendum §12.2: re-verify every command against `--help` and the merged code, mark changed sections, run the commands once in a scratch worktree, refresh the baseline line, and have the Owner review before the next Stage's implementation starts.
