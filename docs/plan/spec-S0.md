# spec-S0.md - Stage 0 (workstreams 0A and 0B) specification and proof map
Authored-by: Claude Sonnet 5.5 (Anthropic), model family: Claude
Date: 2026-10-20. Inputs: Design rev. 2, core plan, addendum (wins over core; Design wins over both), `src/actl/INTERFACES.md` (frozen, PB-2/PB-4), atools code facts at HEAD 85523a0 (VERSION v0.1.7).

> Authorship note. The task text asked for a header naming "Claude (Anthropic)". Authored and folded under Claude Sonnet 5.5 (Anthropic) provenance.
> The review items F-11, F-15..F-19, F-24, F-25 and F-27 are not defined anywhere in the attachment (see section 6, last table), so no decision is invented for them.

## 0. Conventions
- MUST/SHOULD/MAY are RFC 2119. Clause IDs `S0-Rk.n` are stable anchors used by proofs and tests.
- Proof convention: exit `0` pass, `1` fail with a line starting `FAIL:`. Exit `4` is reserved for environment problems (missing `tmux`, `git`, `pytest`, audit script). `ENVFAIL:` in a pytest message maps to exit `4`. A harness or syntax error is never allowed to look like a red feature check (PB-1).
- Exit codes of the product CLI (S0-R10, D-8): `0` ok, `1` red, `2` usage/schema/parse, `3` halt, `4` environment.
- Validation error pointer convention (INTERFACES 1.5, frozen): root is `"/"`; a missing required property is reported as `"/<parent>/<prop>"`; an extra property as `"/<extra>"`; type/enum/pattern/minimum violations at the offending value; `~` is `~0` and `/` is `~1`. See SA-22 and SA-23 for the tension with RFC 6901.
- All proofs read the repo under test from `ACTL_REPO` (default: their own repo root) so the same proofs run against stand-ins (section 8).
- Golden facts: `base_sha = 01d880bc3176cdd8f31d72e67bb3eba54d634378`, tag `2026-10-16_public-profiles`, install seq layout `spec-001, solution_key-002, oracle-003, qual-004, contract-005`, `state.seq = 5`.

## 1. Requirements (testable expansion)

### S0-R1 Baseline capture - `actl doctor [--refresh] [--json]`
- S0-R1.1 The command exists, accepts `--json` and `--refresh`, and `run_doctor(layout, refresh=False) -> dict` returns the same dict that `--json` prints and that is written to `$ACTL_ROOT/baseline.json`.
- S0-R1.2 The report has exactly the top-level keys of INTERFACES 3.3: `version, head_sha, git_dirty, git_status_porcelain, ancestors, tool_versions, python_packages, engine_clis, timeout_available, effective_user, actl_root, log_dir, metadata_dir, linger_state, router_has_read_exit_code, suites, audit, installed_sync_diffs, warnings`. Nested key sets are exact: `ancestors` = the four SHAs `5cb7f30 759a0ca a9b3a4e 4da9394` (bool); `tool_versions` = `python3 git tmux bash`; `python_packages` = `pytest jsonschema`; `engine_clis` = `agent codex claude agy aider vibe`; `suites` = `engines session_persistence exit_code` each `{present, exit_code, tail}`; `audit` = `{present, exit_code, pass, fail, skip, warn, self_test_exit_code, tail}`; `installed_sync_diffs` = the three installed-copy paths.
- S0-R1.3 Values: `head_sha` equals `git rev-parse HEAD`; `version` matches `^v[0-9]+\.[0-9]+\.[0-9]+` (a value below `v0.1.4` adds a warning); `tool_versions.tmux` starts with `tmux` (from `tmux -V`); `effective_user` is the process user; `log_dir`/`metadata_dir` honour `ATOOLS_LOG_DIR`/`ATOOLS_SESSION_DIR` (F4); `router_has_read_exit_code` is true iff `src/router/process.py` defines `read_exit_code`; a missing exit-code suite or a missing `read_exit_code` is a recorded warning, never an error.
- S0-R1.4 `baseline.json` is written on the first run only. A later run without `--refresh` leaves the file byte-identical; `--refresh` overwrites it.
- S0-R1.5 Exit `4` when `tmux` is missing or `audit/atools-compliance_audit.sh` is absent (`audit.present = false`, `exit_code = null`); otherwise `0`, even if recorded suites are red (they are data, not failures of `doctor`). Exit `2` on usage errors.
- S0-R1.6 The repo is never modified: `git status --porcelain` is identical before and after, and `proof/out/` is restored (or removed if it did not exist).
- Proof: P-S0-01 (`test_p01_doctor.py`).

### S0-R2 Additive-change rule
- S0-R2.1 Workstream 0A, measured against `ACTL_FORK_POINT`: added files are free; modified files are a subset of `{install.sh, README.md}`; no deleted or renamed files.
- S0-R2.2 Workstream 0B: the set of changed files is exactly `{src/router/process.py}`.
- S0-R2.3 PB-2: `git diff --name-only <fork>..HEAD -- proof fixtures test/actl src/actl/INTERFACES.md` is empty for both workstreams.
- S0-R2.4 The engines suite, the session-persistence suite (when `agent` exists) and the audit keep their baseline results (`audit ... --cursor` exit 0, `--self-test` pass).
- S0-R2.5 Red on base: P-S0-02 also requires that workstream work exists (0A: at least `src/actl/cli.py` and `bin/actl` added; 0B: `process.py` modified), so an empty branch is red.
- Proof: P-S0-02 (`proof/stage0/P-S0-02.sh`, Part 2).

### S0-R3 Layout
- S0-R3.1 `Layout(root)` is the only constructor of target-tree paths. Root = argument, else `$ACTL_ROOT`, else `$HOME/actl-graph`; `self.root` is resolved absolute; a NUL in `root` raises `ValueError`.
- S0-R3.2 Path table (INTERFACES 1.1): `actl_repo`, `target_repo=repos/target-repo`, `baseline_file`, `sprint_dir=actl-repo/specs/{tag}`, `runs_dir`, `logs_dir`, `turns_dir`, `state_file`, `state_lock`, `sessions_file`, `sprint_toml`, `handoff=handoff/{tag}`, `inbox/outbox={role}-inputs/-outputs`, `workspace(name, tag=None)`, `homes(role)`.
- S0-R3.3 Roles are exactly `architect, challenger, implementer, curator`. Unknown roles raise `ValueError`.
- S0-R3.4 Rejected with `ValueError`: tags failing `validate_sprint_tag` (including `..`, absolute, `a/b`, trailing newline, NUL, invalid calendar date); workspace names that are empty, `.`, `..`, contain `/`, `\`, NUL or a control character `< 0x20`/`0x7f`.
- S0-R3.5 `ensure_base_tree()` creates exactly `actl-repo/specs, handoff, workspaces, repos, homes/{4 roles}` and applies `0700` to `actl-repo/` and `0755` to `handoff workspaces repos homes`. `ensure_sprint_tree(tag)` creates sprint, runs, logs, turns, handoff dirs and, per role, inbox `0750` and outbox `0770`. Both are idempotent and apply modes regardless of umask. Modes are asserted with `stat.S_IMODE(os.lstat(p).st_mode)` (identical for UID 0 and non-root). `repos/target-repo` is not created.
- Proof: P-S0-03 (`test_p03_layout.py`).

### S0-R4 Init and sprint creation
- S0-R4.1 `actl init --target <path|url>` clones with `--local --no-hardlinks` (path) and `-c core.hooksPath=/dev/null` into `repos/target-repo`; history is preserved; `--json` keys `actl_root target_repo base_sha created`; repeating with the same target exits `0`; a different target over an existing clone, or a non-git target, exits `2` (SA-5).
- S0-R4.2 `actl sprint new <slug> [--spec FILE]`: slug must match `^[a-z0-9][a-z0-9-]{1,40}\Z` (so `ab`..41 chars OK; `a`, `-ab`, `Ab`, `a_b`, 42 chars, `ab\n`, non-ASCII are exit `2` and create nothing).
- S0-R4.3 Tag = `YYYY-MM-DD_{slug}` from `$ACTL_TODAY` (valid ISO date) else the local date. An existing tag exits `2` and leaves the existing sprint byte-identical.
- S0-R4.4 `base_sha` is the full 40-character HEAD of the target's default branch.
- S0-R4.5 Created: sprint and handoff trees (S0-R3), `runs/state.json` (`run_id = "run-" + sha256(tag)[:12]`, `seq 0`, `epoch 1`, `status draft`, all `active_*` null, counters 0), `runs/sessions.tsv` with exactly the header `seq\tsession\trole\tengine\tmodel\tmodel_family\tturns\ttool_calls\ttokens\tcost_usd\texit_code\taccepted_items\tescalation_alerts_sent\n`, and the draft `sprint.toml` (S0-R8). `live_run` is NOT written.
- S0-R4.6 With `--spec F`: `seq.reserve` yields `1`; `spec-001.md` is a byte copy; `spec-001.md.meta.json` = `{kind: "spec", seq: 1, parent: null, sha256}`; `spec_source = "imported"`, `active_spec = "spec-001.md"`, `runs/seq.highwater = "1\n"`. A missing `F` exits `2`.
- S0-R4.7 `--json` keys: `sprint_tag slug base_sha sprint_dir handoff_dir spec_source active_spec seq`.
- Proof: P-S0-04 (`test_p04_sprint.py`).

### S0-R5 Sequence allocator and reconstruction
- S0-R5.1 `reserve(layout, tag, kind) -> int` holds `fcntl.flock(LOCK_EX)` on `runs/state.lock` (re-entrant per thread), computes `max(state.seq, highwater) + 1`, writes `"<n>\n"` to `seq.highwater` and `state.json` atomically (temp file, fsync, `os.replace`, fsync of the directory), and returns `n` before any artifact is written. Valid kinds: those of `format_artifact_id` plus `implementer`. Errors: `ValueError` (kind/tag), `FileNotFoundError` (no sprint state).
- S0-R5.2 50 parallel reservations (10 processes x 5) return the 50 distinct contiguous numbers `6..55` (golden `seq = 5`), strictly increasing per process; 8 threads in one process are also distinct. Highwater wins over a lower `state.seq`.
- S0-R5.3 A `SIGKILL` at an arbitrary instant leaves `state.json` parseable, `highwater >= every number already returned`, and the next `reserve` returns a number above all of them.
- S0-R5.4 `reconstruct(layout, tag) -> int` returns `max(highwater, highest seq in file/dir names)` scanning `sprint_dir`, `runs_dir`, `handoff/{tag}/*/*` (two levels) and `workspaces/{tag}/implementer-*`; it rewrites a schema-valid `state.json` (restoring `sprint_tag`, `run_id`, `epoch`, `active_contract` from `contract-*.json`) and is idempotent. The next `reserve` continues at `+1`.
- Proofs: P-S0-05 (`test_p05_seq.py`), P-S0-06 (`test_p06_reconstruct.py`).

### S0-R6 Canonical hashing
- S0-R6.1 `file_sha256(path)` = lowercase 64-hex SHA-256 of raw bytes. Missing -> `FileNotFoundError`; symlink/directory/special -> `ValueError`.
- S0-R6.2 `manifest_sha256(dir)` hashes the UTF-8 text of lines `relpath\0exec_flag\0file_sha256\n`, sorted bytewise by `relpath.encode("utf-8")`, `exec_flag = "x"` iff any `0o111` bit else `"-"`; empty directories are ignored; any symlink (also the root) or special file raises `ValueError`; missing dir -> `FileNotFoundError`.
- S0-R6.3 `canonical_json(obj) -> bytes` = `json.dumps(sort_keys, separators=(",",":"), ensure_ascii=False, allow_nan=False)` in UTF-8; NaN/Infinity -> `ValueError`; non-str key -> `TypeError`; lone surrogate -> `ValueError`; non-serialisable -> `TypeError`. `json_sha256` hashes those bytes.
- S0-R6.4 Vectors: `fixtures/golden/vectors/hashing.json` holds 4 file vectors, 6 canonical-JSON vectors and one manifest vector with its exec-bit twin (>= 6 required). They were computed with `hashlib` and cross-checked with `sha256sum`; proofs also compare `file_sha256` with the system `sha256sum`.
- Proof: P-S0-07 (`test_p07_hashing.py`).

### S0-R7 Schemas
- S0-R7.1 Schemas `common state sprint sprint-proposal closure ev qual contract oracle-decision prior_attempt meta attempt` live in `schemas/*.json`, draft 2020-12, top-level `additionalProperties: false` (except the defs-only `common`).
- S0-R7.2 `ev`, `qual`, `contract` require `kind, seq, parent` through `common.json#/$defs/artifact_meta`; `closure` does not require them (agent drafts); the contract schema carries no budget fields.
- S0-R7.3 `validate(kind, obj)` returns a list of `{path, message}` sorted by `(path, message)`, `[]` iff valid, never raises on bad data, raises `ValueError` only for an unknown kind or schema load failure. A non-object root reports `"/"`.
- S0-R7.4 It never delegates to `jsonschema`: results are identical with `sys.modules["jsonschema"] = None` (O-1).
- S0-R7.5 `sprint` may omit `live_run` only when `status == "draft"`; `sprint-proposal` requires `live_run` and rejects `sprint_tag base_sha status spec_source repo_test_cmd`.
- S0-R7.6 Fixtures: 20 valid documents and 54 invalid documents (>= 4 per kind, 11 kinds) in `fixtures/golden/artifacts/`, each invalid case with its exact expected pointer set in `invalid/index.json`.
- Proof: P-S0-08 (`test_p08_schemas.py`).

### S0-R8 Defaults
- S0-R8.1 `config/graph.toml` contains `max_attempts {oracle 3, implementer 2, live 2, curator 2}`, `min_attempts_before_block = 2`, `max_epochs = 3`, `solution_key_exposure = "full"`, `approval_live_run = "architect"`, `owner_review_triggers = []`, `[hard_cap.implementer] wall_clock = "45m", turns = 60`, a non-empty `repo_test_cmd`, a comment calling the numbers the Design's illustrative values, and no `live_run`.
- S0-R8.2 `load_graph_defaults()` equals the parsed TOML; a missing file raises `FileNotFoundError`.
- S0-R8.3 The draft `sprint.toml` equals `fixtures/golden/expected_text/sprint.toml.tmpl` rendered with `status=draft`, byte for byte (SA-8); defaults come from `graph.toml` (editing `max_epochs` in a scratch copy changes the output).
- Proof: P-S0-09 (`test_p09_defaults.py`).

### S0-R9 Golden fixture
- S0-R9.1 `fixtures/golden/` has the layout of addendum 5.8 plus `expected_text/`, `vectors/`, `sprint/scope_overrides/`. It is deterministic, offline, LLM-free, stdlib-only.
- S0-R9.2 `build_golden.sh <dest>` prints the same `base_sha` on every run; every git call sets `GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null -c core.hooksPath=/dev/null`, fixed identity and `2026-01-01T00:00:00+0000`.
- S0-R9.3 `build_golden.sh --install-sprint ROOT [--tag T]` installs `spec-001.md, solution_key-002.patch, oracle-003/ (with solution_key.patch), qual-004.json, contract-005.json, sprint.toml (frozen, live_run none), runs/state.json (seq 5), runs/sessions.tsv` and the target clone, with hashes consistent with S0-R6.
- S0-R9.4 Case table (`expected.d/base.json`): null base red at `O1:01_public.sh`; key green; good green; `bad_scope` G3; `bad_testcount` G4; `bad_secret` G5; `bad_forbidden` G6; `bad_proof_o1` `O1:02_no_email.sh`; `bad_regression_o2` `O2:test_users::test_get_user_unknown_returns_none`; mutants killed exactly by their `coverage.md` proofs (`contact_leak`->02, `private_200`->03, `photo_count_off`->probe only); `avatar_drop` survives all.
- S0-R9.5 Permission proofs use `S_IMODE(os.lstat(...))`.
- Proofs: P-S0-10 (`golden_selfcheck.sh`), P-S0-13 (hook immunity, Part 2).

### S0-R10 CLI skeleton and exit codes
- S0-R10.1 `main(argv) -> int` returns `0` ok, `1` red, `2` usage/schema/parse (also every other non-zero argparse exit), `3` halt, `4` environment. `UsageError->2`, `StateIntegrityError->3`, `EnvError->4`; `SystemExit(c)` with `c in 1..4` from a handler is preserved.
- S0-R10.2 No arguments, an unknown command, a missing positional, a bad slug and an unknown flag all exit `2`; `--help` exits `0`, lists every discovered command, plain text.
- S0-R10.3 `--json` yields a single JSON document on stdout; with `--json` an error prints one JSON object or nothing on stdout.
- S0-R10.4 With `NO_COLOR` set no output contains `ESC [`.
- Proof: P-S0-11 (`test_p11_cli.py`, scratch copy with a test-only `cmd_zz_dummy.py`).

### S0-R11 Gating suite 0A
- S0-R11.1 `proof/run_suite_actl_s0.sh` uses the `run_check` pattern of `run_suite_engines.sh` (log per check in `proof/out/<name>.log`, PASS/FAIL counters, summary line, non-zero exit on failure), a temporary `ACTL_ROOT`, and is idempotent (two runs give the same summary).
- S0-R11.2 It runs P-S0-01..15 and P-S0-26 plus `golden_selfcheck.sh`; exit `1` if any red, `4` on environment problems; `ONLY=<proof>` restricts the run (used by the conformance proof).
- Proof: P-S0-27 (extra, Part 2).

### S0-R12 `scope.py`
- S0-R12.1 `parse(text)` accepts `ALLOW: p` / `FROZEN: p`, ignores blank and full-line `#` lines, strips trailing whitespace, records `line_no`; `is_literal == ("*" not in pattern)`.
- S0-R12.2 `ValueError` for: missing colon or lowercase keyword, empty pattern, leading `/`, `\`, NUL, inline `#`, `.`/`..`/empty segments (`a//b`, `a/`), `? [ ] { }`, and `**` that is not a whole segment (`a**b`, SA-4).
- S0-R12.3 Glob: `*` = zero or more non-`/` characters within a segment (leading `.` included); whole-segment `**` = zero or more segments (`a/**/b` matches `a/b` and `a/x/y/b`).
- S0-R12.4 `match(rules, path)`: literal `ALLOW` exact -> `allowed`; else any `FROZEN` match -> `frozen`; else glob `ALLOW` -> `allowed`; else `denied`. Result is independent of rule order. It raises `ValueError` when `validate(rules)` is non-empty or the path is not a normalised relative POSIX path.
- S0-R12.5 `validate(rules)` returns error strings for: no `ALLOW`; no `FROZEN: test/**`; literal ALLOW/FROZEN conflict on one path; blanket `ALLOW: **` and `ALLOW: test/**`; any glob ALLOW that matches a sentinel (`__root_probe__`, `test/__probe__.py`, `test/sub/__probe__.py`), e.g. `**/*`, `*/**`, `**/*.py`, `*`.
- S0-R12.6 Table: >= 15 cases (23 in the proof), including FROZEN-beats-glob-ALLOW, literal thaw, nested FROZEN inside an ALLOW glob, and deleted-file paths.
- Proof: P-S0-12 (`test_p12_scope.py`).

### S0-R13 Registries
- S0-R13.1 `discover_commands(subparsers)` imports `actl.cmd_*`, calls `register`, returns the sorted module names; a module without `register` raises `ImportError` or `AttributeError`.
- S0-R13.2 `decide_next(layout, tag, session_probe=None)` is pure. Order: terminal/hold first (`done->done`, `aborted->aborted`, `hold->hold_owner`, command `""`), then `next_rules/[!_]*.py` ascending by `(PRIORITY default 100, module name)`, first non-`None` wins, else `{"action":"noop","command":"","reason":"No matching rule for current sprint state"}`. Files starting with `_` are ignored. The result has exactly the keys `action command reason`.
- S0-R13.3 A new `cmd_*.py` or rule file is discovered with no edit to `cli.py`/`next.py`; `actl next --sprint T --json` equals `decide_next`.
- Proof: P-S0-14 (`test_p14_registries.py`).

### S0-R14 Expected-results fragments
- S0-R14.1 `load_expected(dir=None)` merges `*.json` in lexical filename order into `{base_sha, cases, responses}` (default dir `$REPO/fixtures/golden/expected.d`; `responses` defaults to `{}`).
- S0-R14.2 `base`, `s1`, `s2` fragments merge; a duplicate case key or duplicate `base_sha` -> `ValueError`; malformed JSON -> `ValueError`; missing directory -> `FileNotFoundError`.
- Proof: P-S0-15 (`test_p15_expected.py`).

### S0-R15 Interface freeze
- S0-R15.1 `src/actl/INTERFACES.md` section 4 holds exactly one fenced `json` block (71 entries; stages 0A=56, 0B=2, 1=9, 2=4).
- S0-R15.2 Every entry whose stage is in `ACTL_CHECK_STAGES` (default `0A`) must exist; `0B` entries are checked when `ACTL_CHECK_STAGES` has `0B` or `router.process` has `read_exit_code`; stage `1`/`2` entries when their module imports. Check: name exists, kind matches, parameter names and order equal the manifest, return annotation present (class: annotated `__init__`; property: annotated getter; the three error classes subclass `Exception`).
- S0-R15.3 The checker is itself tested: swapped parameters, a missing annotation, a missing name and an unannotated property are all rejected.
- Proof: P-S0-26 (`test_p26_interfaces.py`).

### S0-R16 Exit-code persistence (workstream 0B)
- S0-R16.1 The generated runner's `cleanup` reads `$?` first (`local ec=$?`), writes the integer plus newline to `<session>.exit.tmp`, `mv -f` onto `<session>.exit`, then removes the runner script and metadata JSON; `trap 'exit 143' TERM`, `'exit 129' HUP`, `'exit 130' INT` exist.
- S0-R16.2 `.exit` survives runner cleanup, `cleanup_session_metadata()` and stale pruning.
- S0-R16.3 `spawn_detached_session()` deletes any old `<session>.exit` and `.exit.tmp` before start and when tmux fails to start.
- S0-R16.4 `kill_session()` waits up to 2 s for the pane processes and then overwrites `.exit` with `143`; if they are not gone it deletes `.exit`.
- S0-R16.5 `get_exit_path(name) -> Path` and `read_exit_code(name) -> Optional[int]` (a clean non-negative integer, else `None`) in `router.process`.
- S0-R16.6 No other behaviour change; engines and persistence suites unchanged.
- Proofs: `proof/run_suite_exit_code.sh` checks E1..E10 = P-S0-16..25 (table in section 3).

## 2. Traceability (requirement -> proof)
| Requirement | Proof IDs | Proof artefact |
|---|---|---|
| S0-R1 | P-S0-01 | `test/actl/test_p01_doctor.py` via `proof/stage0/P-S0-01.sh` |
| S0-R2 | P-S0-02 | `proof/stage0/P-S0-02.sh` (git diff vs `ACTL_FORK_POINT`) |
| S0-R3 | P-S0-03 | `test_p03_layout.py` |
| S0-R4 | P-S0-04 | `test_p04_sprint.py` |
| S0-R5 | P-S0-05, P-S0-06 | `test_p05_seq.py`, `test_p06_reconstruct.py` |
| S0-R6 | P-S0-07 | `test_p07_hashing.py`, `vectors/hashing.json` |
| S0-R7 | P-S0-08 | `test_p08_schemas.py`, `artifacts/` |
| S0-R8 | P-S0-09 | `test_p09_defaults.py`, `expected_text/` |
| S0-R9 | P-S0-10, P-S0-13 | `golden_selfcheck.sh`; `P-S0-13.sh` (global hook installed) |
| S0-R10 | P-S0-11 | `test_p11_cli.py` |
| S0-R11 | P-S0-27 (extra) | `P-S0-27.sh` (suite conformance, idempotence) |
| S0-R12 | P-S0-12 | `test_p12_scope.py` |
| S0-R13 | P-S0-14 | `test_p14_registries.py` |
| S0-R14 | P-S0-15 | `test_p15_expected.py` |
| S0-R15 | P-S0-26 | `test_p26_interfaces.py` |
| S0-R16 | P-S0-16..25 (E1..E10) | `proof/run_suite_exit_code.sh` |

| 0B proof | Check | Clause | What makes it red on the fork point |
|---|---|---|---|
| P-S0-16 | E1 exit 0 | S0-R16.1 | no `.exit` file |
| P-S0-17 | E2 exit 7 | S0-R16.1 | no `.exit` file |
| P-S0-18 | E3 timeout -> 124 | S0-R16.1 | no `.exit` file |
| P-S0-19 | E4 one-line integer, no `.tmp` | S0-R16.1 | no `.exit` file |
| P-S0-20 | E5 runner+json removed, `.exit` kept | S0-R16.1/.2 | no `.exit` file |
| P-S0-21 | E6 stale `.exit`/`.tmp` replaced | S0-R16.3 | stale `99` survives |
| P-S0-22 | E7 absent while running, present after kill | S0-R16.1/.4 | never written |
| P-S0-23 | E8 `arouter kill` records >= 128 | S0-R16.4 | never written |
| P-S0-24 | E9 `read_exit_code`/`get_exit_path` | S0-R16.5 | ImportError message |
| P-S0-25 | E10 signalled runner records 129/130/143 | S0-R16.1 | never written |

Every clause above maps to at least one proof; clauses added beyond the addendum are S0-R1.6, S0-R2.5, S0-R3.5 modes-under-umask, S0-R5.3, S0-R7.4, S0-R11.2, S0-R15.3.

## 3. Interfaces and fixtures index
Names, signatures, CLI synopsis and file formats are those of INTERFACES.md sections 1-4 and are not restated or altered here. Fixtures delivered with this spec: `fixtures/golden/{build_golden.sh, target-repo/, sprint/{spec-001.md, solution_key.patch, oracle/, scope_overrides/}, implementations/, stubs/{agent,loginctl}, artifacts/, vectors/, expected_text/, expected.d/base.json}`. Run results obtained in the authoring environment: `golden_selfcheck.sh` exit 0 (all checks); `run_suite_exit_code.sh` against a behavioural model: base variant exit 1 with E1..E10 all red, fixed variant exit 0 with all green (real `tmux` was not available there, so the real `arouter` has not been exercised); a throwaway reference for layout, seq, hashing, scope and the fragment loader passed 126 tests.

## 4. Ambiguity register
INTERFACES.md already uses A-1..A-4; this register continues as SA-n.
| ID | Unclear | Readings | Chosen reading | Why |
|---|---|---|---|---|
| SA-1 | Output of `python -m api.cli profile <id>` ("prints JSON body, exit 0") does not carry the status that R3 needs | body only; `{status, body}` | one line `{"status": int, "body": {...}}`, exit 0 | proofs must see 404 without a second channel |
| SA-2 | `base_sha` stability | rely on git defaults; pin everything | fixed identity, date, hermetic config, files normalised to mode 644 | SHA depends on every input |
| SA-3 | Does `test/**` match the bare path `test`? | yes (zero segments); no | not asserted by any proof | no file named `test` is expected |
| SA-4 | `a**b` | glob; error | `ValueError` | S0-R12 allows `**` only as a whole segment |
| SA-5 | Exit codes for `FileNotFoundError` (missing `--spec`), non-git target, target mismatch, duplicate tag | 2 or 4 | `2` | usage/parse class; 4 is for missing tools |
| SA-6 | G4 needs a thawed test file but `scope.txt` is fixed by addendum 5.8 | extend scope.txt; per-case override | `sprint/scope_overrides/<case>.txt` replaces `oracle/scope.txt` for that case; only `bad_testcount` has one | keeps the oracle text exactly as specified |
| SA-7 | Format of an `O2` failing step | node id; `file::test` | `O2:<file stem>::<test function>` (class dropped) | matches Design example `O2:test_users::test_public` |
| SA-8 | "deterministically formatted" `sprint.toml` | any | byte-exact template, key order as in S0-R8, one trailing newline, no comments | needed for P-S0-09 |
| SA-9 | E10 in the reference accepts a missing `.exit` | accept; require 129/130/143 | require a recorded value | the reference E10 is green on the fork point (vacuous) |
| SA-10 | Reference E-checks share sessions (E4 uses E2, E8 uses E7) | keep; isolate | each check owns its session | a failure must not cascade |
| SA-11 | Reference E7 passes on the fork point (nothing is ever written) | keep; add positive half | after kill the file must exist | removes vacuity |
| SA-12 | PB-1 wants exit 1 on base, but a missing tool is exit 4 | - | exit 4 only for a missing tool/harness; on a host with `tmux`, base gives exit 1 | an exit 4 on the authoring host (no `tmux`) is not evidence of Red |
| SA-13 | Fork point for P-S0-02 is not defined | merge-base; env | `ACTL_FORK_POINT` (default `git merge-base HEAD main`), `ACTL_WORKSTREAM` `0A`/`0B` | needed to run the proof |
| SA-14 | "Authored-by in every file" vs JSON schemas with `additionalProperties: false`, patches, `expected.d` | add field; exempt | JSON documents under `artifacts/`, `expected.d/`, `vectors/` and `.patch` files carry no header; `artifacts/README.md` and this spec state authorship | adding a field breaks the schema proofs; patch headers are possible (leading text is ignored by `git apply`) but were not added |
| SA-15 | Baseline version: addendum A says `2acaf3c`/v0.1.7, S0-R1 says "v0.1.4 or later", attachment HEAD is 85523a0 | - | proofs accept `>= v0.1.4`; `version` is data | no conflict at runtime |
| SA-16 | `validate("common", x)` | error; defs-only | not tested | `common.json` holds only `$defs` |
| SA-17 | Required keys of `sprint` | all; subset | all keys of the template except `live_run` (conditional) | `sprint new` writes every default |
| SA-18 | `meta` and `attempt` schemas are in INTERFACES but not in S0-R7 | omit; include | include | the frozen contract wins |
| SA-19 | `doctor` runs three suites and the audit | cheap; real | real, results recorded | S0-R1 asks for results; P-S0-01 is slow by design |
| SA-20 | `tail` length | any | last 20 lines, at most 2000 characters | bounded baseline file |
| SA-21 | `installed_sync_diffs` when the installed copy is absent | empty; marker | `"MISSING"` plus a warning; identical -> `""` | distinguishes the two |
| SA-22 | INTERFACES writes the root pointer as `"/"`; RFC 6901 says `""` | follow RFC; follow INTERFACES | `"/"` | frozen contract |
| SA-23 | A missing required property is reported at `"/<parent>/<prop>"`, not at the parent instance | follow RFC; follow INTERFACES | INTERFACES | frozen contract |
| SA-24 | Golden qual is `pure_oracle_failure` (one survivor) yet a contract is minted | block; waive | install assumes a prior `waive_mutant` resolution | gives Stage 1/2 a realistic locked state |
| SA-25 | Design samples abbreviate SHAs (`base_sha "7c3a11b"`, `head a41c9e0`) while schemas require 40 hex | accept short; require 40 | require 40 (see Proposed decision C-1) | INTERFACES freezes `^[0-9a-f]{40}\Z` |
| SA-26 | Fixture-grade guards in `golden_selfcheck.sh` (G3-G6) | reuse Stage 1 code; independent | independent shell versions, regex on added lines, `def test_` counting | S0-R9 forbids actl code in the check |
| SA-27 | S0-R9 demands a hermetic git environment everywhere, P-S0-13 demands the real global hook installed | contradictory | P-S0-13 installs the hook via a temporary `HOME` + `core.hooksPath`; the build must still succeed because it is hermetic | proves D-12 |
| SA-28 | `0B` suite on hosts without tmux | skip; exit 4 | exit 4 | never a fake green |

## 5. Design conflicts reported (not resolved silently)
- C-1 Design sample values use 7-character SHAs; the schemas and S0-R4 use 40. Proposed: the Design samples are illustrative (Design conventions say examples are illustrative); keep 40; Owner may amend the Design samples.
- C-2 Design 4.1 lists `owner_review_triggers` free text of actions; INTERFACES 3.2 restricts it to five names. Proposed: keep the enum; extend only with an Owner-approved INTERFACES change (PB-4).
- C-3 `ev.exit_code` enum is `0|1|3` in INTERFACES 3.4 while the Design example only shows `1`. Proposed: keep `0|1|3`.

## 6. Proposed decisions
### O-1 `jsonschema` dependency
Use the in-tree stdlib validator only; `jsonschema` is never imported by `actl`. `doctor` records whether it is installed. Proof: P-S0-08 blocks `jsonschema` and requires identical results. Matches INTERFACES section 6.

### O-2 Name and storage of `solution_key`
`solution_key-{seq}.patch` in `specs/{tag}/` with `*.meta.json` sidecar (`kind solution_key`, `parent` = active spec file); pointer `state.active_solution_key`; at oracle freeze it is copied unchanged as `oracle-{seq}/solution_key.patch` (Design 2.1) and its hash is part of `manifest_sha256`. Promotion deduplicates by `(kind, parent, sha256)`. The golden install follows exactly this (`solution_key-002.patch`).

### O-5 Initial `forbidden.toml` (G6)
Scope: added lines of the candidate diff only, all files except paths matched by `FROZEN`; word-boundary regexes so `retrieval` does not match `eval`. No inline suppression comments (an agent could game them); exceptions only through an Owner-edited `[[allow]]` entry naming rule, path and exact line text.
| Rule | Pattern (ERE, applied to added lines) | Reason |
|---|---|---|
| F001 | `(^\|[^A-Za-z0-9_.])(eval\|exec)\(` | dynamic code |
| F002 | `os\.(system\|popen\|exec[lv]p?e?)\(` | shell escape |
| F003 | `\bsubprocess\b` | process spawn (needs Owner allow per path) |
| F004 | `\b(socket\|urllib\.request\|http\.client\|requests\|httpx\|aiohttp)\b` | network from offline proofs |
| F005 | `\b(pickle\|marshal)\.loads?\(` | unsafe deserialisation |
| F006 | `actl-repo\|/etc/actl\|probe\.sh\|/proofs/\|/mutants/` | oracle access (Invariant P tripwire) |
| F007 | `git +push\|--no-verify\|core\.hooksPath` | repo-safety rules |
| F008 | `\bsudo\b\|chmod +(-R +)?[0-7]*7[0-7]*7` | privilege/permission widening |
Self-test (mandatory before every use, Design 5.5): synthetic positives for each rule and negatives (`retrieval = 1`, `execute_work`) - the golden self-check already carries the F001 positive and the `retrieval` negative.

### O-6 Initial `secrets.toml` (G5)
Scope: added lines of the diff plus `closure.notes/backlog`. No generic high-entropy rule in Stage 0-2 (too many false positives); named patterns only:
| Rule | Pattern |
|---|---|
| S001 | `\b(AKIA\|ASIA)[0-9A-Z]{16}\b` |
| S002 | `\bgh[pousr]_[A-Za-z0-9]{36,}\b` |
| S003 | `\bsk-[A-Za-z0-9]{20,}\b` |
| S004 | `\bxox[baprs]-[A-Za-z0-9-]{10,}\b` |
| S005 | `-----BEGIN [A-Z ]*PRIVATE KEY-----` |
| S006 | `\bAIza[0-9A-Za-z_-]{35}\b` |
| S007 | `(?i)(secret\|token\|passwd\|password\|api[_-]?key)\s*[:=]\s*['"][^'"]{16,}['"]` |
False positives: the Owner may add `[[allow]]` entries keyed by rule id plus the SHA-256 of the exact matched line (no wildcards, no placeholders such as `EXAMPLE`: the golden positive `AKIAIOSFODNN7EXAMPLE` must stay detected). Stage 6 adds the literal-value scan of `/etc/actl/live.env`.

### Review items F-11, F-15..F-19, F-24, F-25, F-27
These identifiers do not occur in the attachment, so their content is unknown to me and I propose nothing for them. Please paste the review text; each will then get a row with a decision and, where it changes a proof, a new clause.

## 7. Red on Base summary
On the fork point: pytest proofs fail with `FAIL: module ... cannot be imported` or `FAIL: bin/actl is missing` (never a collection error, because no `actl` import happens at module level); `run_suite_exit_code.sh` fails E1..E10 with `FAIL: <name>.exit was not written`; `golden_selfcheck.sh` is green because it validates the fixture, not `actl`.

## 8. Vacuity review (D-20)
The three-stand-in matrix is in `proof/stage0/VACUITY_MATRIX.md`.


## 9. Owner Rulings and Errata (Folded from spec-S0-rulings.md)

# spec-S0-rulings.md - errata to spec-S0.md after the Owner rulings of 2026-10-20
Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity

Apply these over spec-S0.md; nothing else in the spec changes.

## Design conflicts (spec-S0.md section 5) - resolved
| ID | Ruling | Effect |
|---|---|---|
| C-1 | 40-hex SHAs everywhere in schemas, state and JSON artifacts; short prefixes are display only | SA-25 closed. Fixtures already use 40-hex; new invalid cases `sprint/short_base_sha` and `contract/short_base_sha` |
| C-2 | `owner_review_triggers` items are `plan_deviation`, `budget_exceeded`, `critical_tripwire`, `manual_flag` | Replaces the five action names of INTERFACES 3.2. Fixtures changed: `sprint-proposal_base` now uses `manual_flag, budget_exceeded`; new valid `sprint_all_owner_triggers`; new invalid `trigger_old_vocabulary` (sprint and sprint-proposal) |
| C-3 | `ev.exit_code` is an integer 0..255 or null | Replaces `0|1|3`. New valid `ev_exit_255`, `ev_exit_null`; invalid cases `exit_code_above_255`, `exit_code_negative`, `exit_code_type` (the old `exit_code_enum` case with value 2 would now be valid and was removed) |

Both C-2 and C-3 change text that INTERFACES.md froze. Under PB-4 `src/actl/INTERFACES.md` (section 3.2, section 3.4 and the manifest where affected) must be edited with the Owner's note before Stage 0A implementation; until then P-S0-08 fixtures and INTERFACES disagree on purpose. Also check: the Design (4.1, 6.3) uses `waive_mutant` and the other escalation actions as the values of `owner_review_triggers`; the new vocabulary is different, so the Design text needs the same amendment or the two documents will contradict each other. The escalation `resolution.action` vocabulary (`grant_attempts`, `waive_mutant`, ...) is unaffected.

## Review items
| Item | Ruling | Where it lands in Stage 0 |
|---|---|---|
| F-11 | INTERFACES section 3 is normative; `schemas/*.json` mirror it with `additionalProperties: false` | P-S0-08 (`test_schema_files_shape` already checks this) |
| F-15 | `wait_session` default timeout 600 s | Stage 1 (S1-R14); no Stage 0 proof |
| F-16 | Missing entities raise `FileNotFoundError`/`KeyError` internally and map to exit 2 (`UsageError`) or 3 (`StateIntegrityError`) | Covered partly by P-S0-04/P-S0-11. Not yet pinned: which missing-entity cases map to 3. SA-5 stays as the working reading (2) |
| F-17 | implementer artifact id is `implementer-{attempt_seq:03d}` | `format_artifact_id` currently lists no `implementer` kind (INTERFACES 1.2); the manifest/INTERFACES text needs that kind added; `parse_seq_from_name` already accepts `implementer-NNN` |
| F-18, F-19 | Logged as proposed decisions, deferred to Stage 2 | None |
| F-24, F-25, F-27 | `state_lock` is thread-local re-entrant on `runs/state.lock` via `fcntl.flock`; exit 3 on acquisition failure | Re-entrancy and cross-process exclusion are exercised by P-S0-05 (threads, 10 processes, SIGKILL). The exit-3-on-lock-failure case has no proof yet; proposed addition: make the lock file unopenable (directory at that path) and expect `OSError` from `state_lock` and exit 3 from `actl sprint new` |

## Counts updated in S0-R7.6
24 valid and 59 invalid documents (11 kinds, at least 4 invalid per kind).
