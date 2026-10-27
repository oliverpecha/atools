# spec-S1.md - Stage 1 (Verifier and Implementer Loop) Specification and Proof Map
Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
Date: 2026-10-27. Baseline: atools commit 4e16cc3 (VERSION v0.1.8).
Inputs: actl_Design.md (normative), actl_Build_Plan-Stages0to2_addendum.md (amended 2026-10-24), actl_Build_Plan-Stages0to2.md, src/actl/INTERFACES.md (frozen, PB-2/PB-4), docs/plan/spec-S0.md.
Rulings applied: D-24, D-30..D-40 (Layout transition L-1..L-11), D-41, D-42, D-45, D-48, O-17.

## 0. Conventions
- MUST/SHOULD/MAY follow RFC 2119. Clause IDs `S1-Rk.n` are immutable traceability anchors for Stage 1 proofs and pytest suites.
- Proof conventions: scripts exit `0` on pass and `1` on failure with a line starting `FAIL: <clause_id>: <reason>`. Exit `4` is reserved for environment problems (missing `tmux`, `git`, `pytest`, or baseline commits). `ENVFAIL:` in a pytest failure message is mapped by `proof/run_suite_actl_s1.sh` to exit `4`.
- Product CLI exit codes (`S0-R10`, `D-8`): `0` = ok/green, `1` = red (verification check failed), `2` = usage/schema/parse error, `3` = halt (integrity mismatch or guard self-test failure; no attempt consumed), `4` = environment error (missing external tool).
- Layout (`D-30..D-40`): All paths under `$ACTL_ROOT` MUST be constructed via `actl.layout.Layout` methods (`sprint_dir`, `runs_dir`, `logs_dir`, `inbox`, `outbox`, `workspace`, `target_repo`, `profile`).
- Artifact naming (`D-34`): Verification artifact kind is `"verification"` and filename is `verification-{seq:03d}.json` under `layout.runs_dir(tag)`.
- Closure source (`D-42`): `verify_impl` and `dispatch-impl` MUST NOT read `closure-draft.json` from the candidate worktree. Closures are read exclusively from the explicit `closure_path` argument (or `layout.outbox(tag, "implementer") / "closure.json"` when dispatched).
- Dynamic timeout (`D-45`): `wait_session` signature in `INTERFACES.md` is `wait_session(session_name: str, timeout_s: int = 2700, poll_interval_s: float = 1.0) -> dict[str, Any]`. When `timeout_s` is passed as `None` (or omitted by `cmd_wait` / `dispatch-impl`), the effective timeout is computed from `sprint.toml` `[hard_cap.implementer].wall_clock` (default `45m` = `2700s`) + `kill_grace` (`3s` or `$ATOOLS_KILL_GRACE`) + `30s` (`2733s` default).
- Golden fixture facts (`spec-S0.md`): `base_sha = 01d880bc3176cdd8f31d72e67bb3eba54d634378`, tag `2026-10-16_public-profiles`, initial installed sequence `state.seq = 5` (`spec-001.md`, `solution_key-002.patch`, `oracle-003/`, `qualification-004.json`, `contract-005.json`). The first sequence reserved in Stage 1 on a fresh golden sprint install is `6` (`006`).

## 1. Requirements (Testable Expansion)

### S1-R1 Verification Record and StepResult
- S1-R1.1 `actl.verify` re-exports `StepResult` from `actl.schemas` (`actl.verify.StepResult is actl.schemas.StepResult`). Attributes: `id: str`, `cmd: str`, `exit_code: int`, `output_sha256: str` (64 lowercase hex), `output_tail: str = ""`, `duration_ms: int = 0`, `failing_line: str | None = None`.
- S1-R1.2 `StepResult.to_verification_step()` returns strictly `{"id": self.id, "cmd": self.cmd, "exit_code": self.exit_code, "output_sha256": self.output_sha256}`.
- S1-R1.3 `verify_impl(layout, tag, closure_path=None, worktree=None, fail_fast=True, session_info=None, strict_tripwire=False) -> dict[str, Any]` returns a dictionary validating with zero errors against `actl.schemas.validate("verification", doc)`.
- S1-R1.4 Closure Stamping & Parent Linkage:
  - When `closure_path is not None` and points to an existing regular file, `verify_impl` reserves `closure_seq = actl.seq.reserve(layout, tag, "closure")`, stamps `"kind": "closure"`, `"seq": closure_seq`, and `"parent": state["active_contract"]` (e.g. `"contract-005.json"`), atomically writes `layout.runs_dir(tag) / f"closure-{closure_seq:03d}.json"`, increments `state["closures_submitted"]` by `1` via `update_state` (only if the closure parses as a JSON object), and sets `verification["parent"] = f"closure-{closure_seq:03d}.json"`.
  - When `closure_path is None`, `G2` and the post-`O2` blocked check are skipped (unless `session_info` has `lost=True` or `hard_cap=True`, which still records a red `G2`), no closure is stamped, `closures_submitted` is unchanged, and `verification["parent"] = None`.
- S1-R1.5 Fail-Fast vs Blocked Diagnostic Collection:
  - When `fail_fast=True` and `closure.reason != "blocked"`, execution stops at the first step in `G1 -> G2 -> G3 -> G4 -> G5 -> G6 -> O1 -> O2` with `exit_code != 0`.
  - When `closure.reason == "blocked"`, `fail_fast` is forced to `False` across `G3..G6`, `O1` (when `blocking_step` starts with `"O1:"`), and `O2` so all required steps execute before the post-`O2` blocked adjudication.
  - `scan_tripwires` ALWAYS executes before writing `verification-{seq:03d}.json` (even if an earlier step failed under `fail_fast=True`, except on `halt`), populating `verification["tripwires"]`.
- S1-R1.6 `failing_step` is `None` when `verification["exit_code"] == 0`; otherwise it is the `id` of the first failing step (`"G1"`, `"G2"`, `"G3"`, `"G4"`, `"G5"`, `"G6"`, `"O1:<script>"`, `"O2:<stem>::<func>"`, or `"tripwire"`).
- S1-R1.7 `failing_line` is `None` when `verification["exit_code"] == 0`; on failure it is sanitized per `INTERFACES.md` section 6 (`O-8`): strip ANSI CSI (`\x1b\[[0-9;?]*[ -/]*[@-~]`) and OSC (`\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)`), replace `\r`, `\n`, and `\t` with single spaces, replace remaining code points `< 0x20` or `== 0x7f` (and lone `\x1b`) with `?`, and truncate to 300 Unicode code points.

### S1-R2 Pipeline Order, Halt Precedence, and Session State
- S1-R2.1 Execution order in `verify_impl`:
  1. `run_selftests()`
  2. `G1` (oracle manifest integrity)
  3. `G2` pre-check (session `lost`/`hard_cap` check + closure JSON parse & `schemas/closure.json` validation)
  4. `G3` (git diff mode & `scope.match` check)
  5. `G4` (Python AST test count & hollow-test check on thawed `test/**` files)
  6. `G5` (secret regex scan + redaction on added diff lines and closure `notes`/`backlog`)
  7. `G6` (forbidden AST/regex scan on added lines of non-`FROZEN` files)
  8. `O1` (oracle `proofs/*.sh` and `probe.sh`; skipped when `closure.reason == "blocked"` unless `closure.blocking_step` starts with `"O1:"`)
  9. `O2` (`repo_test_cmd` with `--junitxml`)
  10. `G2` blocked post-check (only when `closure.reason == "blocked"` and `G2` pre-check passed)
  11. `scan_tripwires` (merges hits into `verification["tripwires"]`; if `strict_tripwire=True` and `tripwires` is non-empty, forces `exit_code = 1`, setting `failing_step = "tripwire"` and `failing_line = "Tripwire pattern detected in transcript or log"` if no earlier step failed).
- S1-R2.2 Halt vs Red vs Interruption (`D-24`, `O-17`):
  - If `run_selftests()` has any step with `exit_code != 0`, or `G1` detects a manifest mismatch (`exit_code == 3`), verification halts immediately: no subsequent steps run, `attempts["implementer"]` and `closures_submitted` are NOT incremented, `verification["exit_code"] = None`, `verification["halt"] = {"reason": "selftest_failed" | "integrity_mismatch"}`, `state["status"]` is updated to `"hold"`, `runs/verification-{seq:03d}.json` is written, and the CLI exits with code `3`. Halt takes absolute precedence over `session_info` (`hard_cap`/`lost`).
  - If the verifier process itself is interrupted by an unhandled signal before completing atomic write of `verification-{seq:03d}.json`, no partial verification file is left in `runs/`.
- S1-R2.3 Closure Input Classification:
  - In `actl verify-impl --closure <PATH>`, if `<PATH>` does not exist or is a directory/unreadable -> raise `UsageError` (CLI exit `2`, no `verification` artifact written).
  - If `<PATH>` exists (or is read from `outbox/closure.json` after session completion) but contains malformed JSON or fails `schemas.validate("closure", obj)` -> `G2` pre-check fails red (`StepResult(id="G2", exit_code=1)`), `verification["exit_code"] = 1`, `failing_step = "G2"`, CLI exits `1`.
- S1-R2.4 Session Flags & State Counters:
  - When `session_info` has `hard_cap == True` (and no halt occurred), `G2` fails red (`exit_code = 1`, `failing_line = "Session hit watchdog hard cap"`), and `state["hard_caps_tripped"]` is incremented by `1`.
  - When `session_info` has `lost == True` (and no halt occurred), `G2` fails red (`exit_code = 1`, `failing_line = "Session lost or terminated unexpectedly"`).
  - For every non-halt `verify_impl` call, `state["attempts"]["implementer"]` is incremented by `1`.
  - `verification["stage"]` is `"blocked_check"` when evaluating a closure with `reason == "blocked"`, else `"offline"`.

### S1-R3 Guards G1-G6 and run_selftests
- S1-R3.1 `G1`: Loads `contract = json.loads((layout.sprint_dir(tag) / state["active_contract"]).read_text())` and `oracle_dir = layout.sprint_dir(tag) / state["active_oracle"]`. Computes `actl.hashing.manifest_sha256(oracle_dir)`. If it differs from `contract["oracle"]["manifest_sha256"]`, returns `StepResult(id="G1", cmd="manifest_sha256", exit_code=3, ..., failing_line="Oracle manifest digest mismatch: integrity_mismatch")`.
- S1-R3.2 `G2` Pre-check and Post-O2 Blocked Adjudication:
  - **Pre-check (before `G3`):** Checks `session_info` (`lost`/`hard_cap`), parses closure JSON, and validates against `schemas/closure.json` (which enforces `additionalProperties: false`). If `reason == "blocked"` and `blocking_step` is null/empty or `notes` is empty, fails `G2` pre-check.
  - **Post-check (after `O2`, when `reason == "blocked"`):** Adjudicates the four blocked preconditions (Design section 5.4 / Addendum `S1-R3`):
    1. `closures_submitted >= sprint_toml["min_attempts_before_block"]` (including the current stamped closure; fails with `failing_line` containing `"min_attempts_before_block"` if too early).
    2. `G4`, `G5`, and `G6` all passed (`exit_code == 0`), and `G3` passed unless `blocking_step == "G3"`.
    3. `O2` passed unless `blocking_step` starts with `"O2"`.
    4. The executed step named by `blocking_step` actually failed (`exit_code != 0`), AND when `sprint_toml["solution_key_exposure"] == "full"` and `blocking_step` starts with `"O1:"`, `closure["solution_key_divergence"]` is non-null and its `requirement_id` appears on the LHS of a mapping line in `oracle_dir / "coverage.md"`.
  - **Outcome of Blocked Adjudication:**
    - If any precondition (1)-(4) is violated, `G2` is marked red (`exit_code = 1`), `verification["exit_code"] = 1`, `verification["failing_step"] = "G2"`, and `state["status"]` remains `"running"`.
    - If all preconditions (1)-(4) hold, the blocked claim is **confirmed**: `G2` has `exit_code = 0`, `verification["stage"] = "blocked_check"`, `verification["exit_code"] = 1`, `verification["failing_step"] = closure["blocking_step"]`, `verification["failing_line"]` is the failing line of that `blocking_step`, and `verify_impl` updates `state["status"] = "hold"`.
- S1-R3.3 `G3`: Loads scope rules from `layout.sprint_dir(tag) / contract["scope"]["path"]` (or `sprint_dir / "scope_overrides" / f"{case}.txt"` if overridden in `contract["scope"]["path"]`). Runs `git -C <worktree> diff --raw -z --no-renames <base_sha>..HEAD`. Rejects any entry whose new mode is not in `{"100644", "100755", "000000"}` (e.g. symlink `120000` or submodule `160000`) with `exit_code = 1`. Calls `actl.scope.match(rules, path)` for every touched path; if `scope.match` raises `ValueError` or returns `"denied"` or `"frozen"`, `G3` returns `exit_code = 1` with `failing_line = f"Scope violation ({verdict}): {path}"`.
- S1-R3.4 `G4`: Inspects all paths under `test/` (matching `test/**`) where `actl.scope.match(rules, path) == "allowed"` (or any touched `test/**` file when thawed). For each Python test file (`*.py`), parses the file at `base_sha` (`git show <base_sha>:<path>`) and in `<worktree>/<path>` using `ast.parse`.
  - If `<worktree>/<path>` is deleted or fails `ast.parse` (`SyntaxError`), `G4` fails (`exit_code = 1`).
  - Walks the module AST collecting top-level `FunctionDef`/`AsyncFunctionDef` nodes named `test_*` and `FunctionDef`/`AsyncFunctionDef` nodes named `test_*` directly inside `ClassDef` nodes. Nested helper functions inside functions are ignored.
  - If candidate count `<` base count, `G4` fails (`exit_code = 1`, `failing_line` containing `"test function count decreased"`).
  - Inspects every candidate `test_*` function body: after stripping an optional leading docstring (`ast.Expr` wrapping a `Constant(str)`), if the remaining statements consist solely of `ast.Pass`, `ast.Expr(Constant(Ellipsis))`, or `ast.Assert` whose `test` is `Constant(True)`, `G4` fails (`exit_code = 1`, `failing_line` containing `"hollow test"`).
- S1-R3.5 `G5`: Loads `config/secrets.toml` (`[[rules]]` with `id`, `pattern`, `description`, and optional `[[allow]]` with `rule`, `line_sha256`). Scans all added lines (`+...`, excluding `+++ `) from `git diff -U0 <base_sha>..HEAD` and every string in `closure["notes"]` and `closure["backlog"]`. If a line matches a rule's regex and `(rule_id, sha256(raw_line_stripped))` is not in `[[allow]]`, `G5` fails (`exit_code = 1`). The matched substring MUST be replaced with `"[REDACTED]"` in `failing_line` and `output_tail` (`failing_line = f"G5 secret pattern {rule_id} matched in {source}:{line_no}: {redacted_line}"`).
- S1-R3.6 `G6`: Loads `config/forbidden.toml` (`[[rules]]` with `id`, `kind` in `{"ast_call", "regex"}`, `pattern`, `message`, and optional `[[allow]]` with `rule`, `path`, `line`). Evaluates added lines of non-`FROZEN` files in `git diff -U0 <base_sha>..HEAD`:
  - Regex check: applies each rule's regex (`pattern`) to added lines.
  - AST check (for `.py` files that parse cleanly with `ast.parse`): walks `ast.Call` nodes whose line span (`lineno..end_lineno`) intersects added line numbers, resolving call names (`func.id` or `f"{func.value.id}.{func.attr}"`, plus `import as` aliases within the file) against `F001..F005` call targets (`eval`, `exec`, `os.system`, `os.popen`, `os.execl*`, `os.execv*`, `subprocess.*`, `pickle.load`, `pickle.loads`, `marshal.load`, `marshal.loads`).
  - If any rule matches and is not exempted by an exact `(rule, path, stripped_line)` entry in `[[allow]]`, `G6` fails (`exit_code = 1`, `failing_line = f"G6 forbidden call ({rule_id}) at {path}:{line_no}: {message}"`).
- S1-R3.7 `run_selftests() -> list[StepResult]`: Verify `config/secrets.toml` and `config/forbidden.toml` exist and parse cleanly, and run built-in positive and negative synthetic checks for `G1`, `G2`, `G3`, `G4`, `G5`, and `G6` (6 `StepResult` items with IDs `"selftest:G1"`..`"selftest:G6"`). If a config file is missing/corrupt or any synthetic positive/negative check produces the wrong outcome, that step records `exit_code = 3`.

### S1-R4 Out-of-Tree Oracle Staging
- S1-R4.1 `run_o1(oracle_dir, worktree, timeout_s=60, target_cmd=None)` creates a sibling staging directory `stage_dir = worktree.parent / f"{worktree.name}.oracle-stage"`.
- S1-R4.2 Copies ONLY `oracle_dir / "proofs"` (`*.sh`) and `oracle_dir / "probe.sh"` (when present) into `stage_dir`. Never copies `mutants/`, `coverage.md`, `oracle-critique.md`, `scope.txt`, or `solution_key.patch` into `stage_dir` or `worktree`.
- S1-R4.3 Applies mode `0o550` (`r-xr-x---`) to all staged `.sh` scripts and `0o750` to `stage_dir` and `stage_dir / "proofs"`.
- S1-R4.4 In a `finally:` block, unconditionally removes `stage_dir` and the throwaway `HOME` and `TMPDIR` directories via `shutil.rmtree(..., ignore_errors=True)`, even if a proof times out or raises an exception.

### S1-R5 O1 Execution
- S1-R5.1 Executes `stage_dir / "proofs" / "*.sh"` in bytewise lexical filename order, followed by `stage_dir / "probe.sh"`. Step IDs are `f"O1:{script.name}"` (e.g. `"O1:01_public.sh"`, `"O1:probe.sh"`).
- S1-R5.2 Each script is invoked as `["bash", str(staged_script)]` with `cwd=str(worktree)`, `stdin=subprocess.DEVNULL`, `start_new_session=True`, and an allowlisted environment containing ONLY:
  - `PATH`: inherited `os.environ.get("PATH", "/usr/bin:/bin")`
  - `LANG`: `"C.UTF-8"`
  - `HOME`: path to a fresh throwaway directory created per `run_o1` call
  - `TMPDIR`: path to a fresh throwaway temp directory created per `run_o1` call
  - `ACTL_TARGET_CMD`: `target_cmd` if passed, else `os.environ.get("ACTL_TARGET_CMD", "python3 -m api.cli")`
  - `PYTHONDONTWRITEBYTECODE`: `"1"`
- S1-R5.3 Captures combined `stdout` and `stderr`. Computes `output_sha256 = sha256(raw_output_bytes)`. `failing_line` (when `exit_code != 0`) is the last line in output starting with `"FAIL"`, else the last non-empty line, sanitized per `S1-R1.7`.
- S1-R5.4 On `subprocess.TimeoutExpired` after `timeout_s` seconds, kills the process group (`os.killpg(proc.pid, signal.SIGKILL)`), records `exit_code = 124`, and sets `failing_line = f"FAIL: {script.name} timed out after {timeout_s}s"`.

### S1-R6 O2 Execution
- S1-R6.1 `run_o2(worktree, repo_test_cmd=None, timeout_s=120)`: if `repo_test_cmd is None`, uses `"python3 -m pytest test -q -rf"`.
- S1-R6.2 Splits `repo_test_cmd` with `shlex.split(repo_test_cmd)` (`shell=False`). Rejects empty commands, shell metacharacters (`;`, `|`, `&`, `$`, `>`, `<`, `` ` ``), or `argv[0]` not in `("python3", "pytest")`; if `argv[0] == "python3"`, `argv[1:3]` MUST be `["-m", "pytest"]`. Violations raise `ValueError`.
- S1-R6.3 Appends `f"--junitxml={junit_xml_path}"` as a single argument and runs in `cwd=str(worktree)` under the same allowlisted environment pattern as `O1` (`PYTHONDONTWRITEBYTECODE="1"`). The recorded `StepResult.cmd` normalizes the temporary path to `f"{repo_test_cmd} --junitxml=<tmp_xml>"`.
- S1-R6.4 Step ID & Failing Line Normalization (`SA-7`, `S1A-5`):
  - On `exit_code == 0`, returns `[StepResult(id="O2", cmd=normalized_cmd, exit_code=0, output_sha256=..., failing_line=None)]`.
  - On `exit_code != 0`, parses `junit_xml_path` with `xml.etree.ElementTree` to find the first `<testcase>` containing a `<failure>` or `<error>` child. Extracts `classname` and `name` (stripping `[...]` parameter suffixes only if needed, or keeping function name). Normalizes `classname` to `<file_stem>` by taking the last dotted module segment matching `test_*` (for example `"test.test_users"` or `"test.test_users.TestUsers"` -> `"test_users"`), producing `id = f"O2:{file_stem}::{name}"` (fallback `"O2"` if XML is missing/unparseable). `failing_line` includes `f"{file_stem}::{name}"` and the first failure message line, sanitized per `S1-R1.7`.
  - On timeout after `timeout_s`, terminates the process group and returns `exit_code = 124`, `id = "O2"`.

### S1-R7 Verification Emission and prior_attempt.json
- S1-R7.1 `verify_impl` reserves `ver_seq = actl.seq.reserve(layout, tag, "verification")` and writes `layout.runs_dir(tag) / f"verification-{ver_seq:03d}.json"` atomically (write temp file in `runs_dir`, `flush`, `os.fsync`, `os.replace`, `os.fsync` on `runs_dir` fd).
- S1-R7.2 When `verification["exit_code"] == 1`, constructs `prior_attempt = {"diff": git_diff_base_to_head, "failing_step": verification["failing_step"], "failing_line": verification["failing_line"], "closures_submitted": state["closures_submitted"]}`, validates it against `schemas/prior_attempt.json` (strictly 4 keys), and atomically writes `layout.inbox(tag, "implementer") / "prior_attempt.json"` with mode `0o440`.
- S1-R7.3 When `verification["exit_code"] == 0`, unlinks `layout.inbox(tag, "implementer") / "prior_attempt.json"` if present.

### S1-R8 Implementer Skill Governance
- S1-R8.1 `skills/actl-implementer/SKILL.md` is authored in the Stage 1 implementation pass (absent on base `4e16cc3`).
- S1-R8.2 Positive requirements: instructs the implementer to read `mailboxes/implementer/inbox/` (`attempt.json`, `spec`, `contract`, optional `solution_key.patch`, optional `prior_attempt.json`), commit on branch `wip/{seq:03d}`, verify `git status`, and write `mailboxes/implementer/outbox/closure.json`.
- S1-R8.3 Negative governance (Invariant `P`): explicitly prohibits accessing `records/`, `oracle-`, `proofs/`, `probe.sh`, `mutants/`, or running `proof/run_suite_*.sh`, and contains no imperative shell command instructing the agent to read or execute those paths.

### S1-R9 Implementer Workspace Dispatch (`actl dispatch-impl`)
- S1-R9.1 CLI synopsis: `actl dispatch-impl --sprint <TAG> [--mode detach|foreground] [--tier cheap|balanced|smart] [--engine <ENG>] [--no-run] [--strict-tripwire] [--json]`.
- S1-R9.2 Active Session Guard: Before reserving `seq`, checks `state["tmux_sessions"]` and `router.process.list_active_tmux_sessions()`. If any session recorded in `state["tmux_sessions"]` for this sprint is currently active in `tmux` (or listed in `state["tmux_sessions"]` while active), raises `UsageError` (CLI exit `2`, per Addendum `S1-R9` item 1: "Refuse with exit `2` if `state['tmux_sessions']` already contains a live tmux session for this sprint").
- S1-R9.3 Workspace & Inbox Staging:
  1. Reserves `seq = actl.seq.reserve(layout, tag, "implementer")`.
  2. Clones `layout.target_repo` (`--local --no-hardlinks -c core.hooksPath=/dev/null`) into `ws = layout.workspace(f"implementer-{seq:03d}", tag)` and checks out branch `f"wip/{seq:03d}"` at exact commit `contract["base_sha"]`. Installs/preserves repo hooks so commits on `main` are rejected while commits on `wip/{seq:03d}` with valid `WI-` format succeed.
  3. Stages read-only (`0o440`) copies into `inbox = layout.inbox(tag, "implementer")` (unlinking any prior target before copying): `spec` (`state["active_spec"]`), `contract` (`state["active_contract"]`), `solution_key.patch` (when `sprint_toml["solution_key_exposure"] == "full"` and `state["active_solution_key"]` is set), and writes `inbox / "attempt.json"` (`{"seq": seq, "branch": f"wip/{seq:03d}", "sprint_tag": tag, "contract": state["active_contract"], "spec": state["active_spec"]}`, validated against `schemas/attempt.json`).
- S1-R9.4 Static Prompt & `start_session`:
  - Builds a static ASCII instruction referencing `mailboxes/implementer/inbox/` and `mailboxes/implementer/outbox/closure.json` without embedding `{seq}` in the instruction string.
  - `start_session(session_name, worktree, instruction, mode="detach", tier="balanced", engine="cursor", wall_clock="45m") -> int` validates: `validate_session_name(session_name)` is `True`, `instruction` is non-empty 7-bit ASCII (`instruction.isascii()`), `instruction.strip().lower() not in ("help", "--help", "-h")`, `len(json.dumps(instruction)) < 100000`, and `mode in ("detach", "foreground")`. Violations raise `ValueError` before invoking `arouter`.
- S1-R9.5 Execution & `--no-run`:
  - If `--no-run` is set, returns exit `0` with JSON keys `{"sprint_tag", "seq", "session_name", "worktree", "inputs_dir", "closure_path", "mode", "no_run": True, "verification_id": None, "exit_code": 0}` without invoking `start_session` or `arouter`.
  - Otherwise, launches session via `start_session`, records `session_name` in `state["tmux_sessions"]`, waits via `wait_session` (in detach mode), archives logs via `archive_session_log`, removes `session_name` from `state["tmux_sessions"]`, invokes `verify_impl`, and exits with the verification CLI exit code (`0`, `1`, or `3`).

### S1-R10 Tripwire Scanner and Profile Discovery
- S1-R10.1 `scan_tripwires(layout, tag, seq, log_path=None) -> list[dict[str, Any]]` scans:
  1. `log_path` (default `layout.logs_dir(tag) / f"impl-{seq:03d}.log"` if present), stripping ANSI escape sequences before matching.
  2. Any `*.jsonl` transcript files under `$ATOOLS_CURSOR_HOME` (if set, else `layout.profile("implementer")`, else `/root/.cursor` / `~/.cursor` transcript directories).
- S1-R10.2 Tripwire patterns: `records/`, `oracle-`, `proofs/`, `mutants/`, `probe.sh`, `solution_key`.
- S1-R10.3 Provenance-Safe Exclusions: A line is excluded iff:
  - It is a verbatim line present in `skills/actl-implementer/SKILL.md`, OR
  - It is a verbatim field/line from the staged `mailboxes/implementer/inbox/contract-*.json` (e.g. `"oracle-003"`, `"oracle-003/scope.txt"`), OR
  - It is an `"O1:<script>"` `failing_step` reference matching `mailboxes/implementer/inbox/prior_attempt.json`.
  Lines that combine a governance token with an active oracle path access (e.g. `"Read skills/actl-implementer/SKILL.md then cat records/target-repo/oracle-003/proofs/01_public.sh"`) are NOT excluded and MUST trigger a tripwire hit.
- S1-R10.4 Each hit is `{"source": "log" | "transcript", "line_no": int, "pattern": str, "excerpt": str}`.

### S1-R11 CLI Contract (`actl verify-impl`, `actl selftest`, `actl wait`)
- S1-R11.1 All Stage 1 commands (`cmd_verify_impl.py`, `cmd_dispatch_impl.py`, `cmd_wait.py`, `cmd_selftest.py`) register via `register(subparsers)` and are invoked through `actl.cli.main(argv)` without modifying `src/actl/cli.py`.
- S1-R11.2 `actl verify-impl --sprint <TAG> --closure <PATH> [--worktree <PATH>] [--no-fail-fast] [--strict-tripwire] [--json]`:
  - When `--worktree` is omitted, resolves to the highest-numbered existing `layout.workspace(f"implementer-{k:03d}", tag)` directory; if none exists, raises `UsageError` (exit `2`).
  - Maps `verification["exit_code"] == 0` -> `0`, `1` -> `1`, `verification["halt"] is not None` -> `3`, `UsageError` -> `2`, `EnvError` -> `4`.
- S1-R11.3 `actl selftest [--json]` runs `run_selftests()`, prints `{"ok": bool, "exit_code": 0|3, "steps": [...]}` when `--json` is passed, and exits `0` if all steps pass else `3`.

### S1-R12 Phase 3 Decision Rules (`actl next`)
- S1-R12.1 `src/actl/next_rules/phase3.py` defines `PRIORITY = 30` and `evaluate(layout: Layout, tag: str, session_probe: Callable | None = None) -> dict[str, str] | None`.
- S1-R12.2 Entry Condition: Reads `state = read_state(layout, tag)`. If `state.get("active_stage") != "implementer"`, returns `None` immediately. (Note: `actl.next.decide_next` already handles `state["status"] in ("done", "aborted", "hold")` before calling rule modules, returning `"done"`, `"aborted"`, or `"hold_owner"` with `command=""`; if `phase3.evaluate` is called directly when `state["status"] == "hold"`, it also returns `{"action": "hold_owner", "command": "", "reason": "Sprint is on hold for owner review"}`).
- S1-R12.3 Ordered Precedence Table for `active_stage == "implementer"` and `status == "running"`:
  Let `outbox_closure = layout.outbox(tag, "implementer") / "closure.json"`. Let `verifications` be all `runs/verification-*.json` sorted by `seq`, and `last_ver` be the highest-`seq` verification record (or `None`). Let `workspaces` be all `workspaces/implementer-*` sorted by `seq`, and `last_ws_seq` be the highest workspace `seq` (or `0`).
  1. **Active session running:** If `state["tmux_sessions"]` is non-empty and the latest session `s = state["tmux_sessions"][-1]` is reported running by `session_probe(s)` (or `tmux has-session -t s` when `session_probe is None`):
     -> `{"action": "wait", "command": f"actl wait {s} --sprint {tag}", "reason": "Implementer session in progress"}`
  2. **Session lost (finished without `.exit` and unverified):** If `state["tmux_sessions"]` has a session `s` that is no longer running and `read_exit_code(s) is None` (or `session_probe` reports `lost=True`):
     -> `{"action": "verify", "command": f"actl verify-impl --sprint {tag}", "reason": "Session lost without exit code; record red G2 verification"}`
  3. **Unverified closure in outbox:** If `outbox_closure.is_file()` and (`last_ver is None` or `last_ver["seq"] < last_ws_seq` or `outbox_closure` was not yet stamped into `runs/closure-*.json` linked by `last_ver["parent"]`):
     -> `{"action": "verify", "command": f"actl verify-impl --sprint {tag} --closure {outbox_closure}", "reason": "Closure submitted for verification"}`
  4. **Finished attempt workspace without closure and unverified:** If `last_ws_seq > 0` and (`last_ver is None` or `last_ver["seq"] < last_ws_seq`) and not `outbox_closure.is_file()`:
     -> `{"action": "verify", "command": f"actl verify-impl --sprint {tag} --closure {outbox_closure}", "reason": "Session finished without closure; record red G2 verification"}`
  5. **Verified blocked closure confirmed:** If `last_ver is not None` and `last_ver.get("stage") == "blocked_check"` and `last_ver.get("failing_step") != "G2"`:
     -> `{"action": "hold_owner", "command": "", "reason": "Implementer blocked with verified rationale"}`
  6. **Last verification green:** If `last_ver is not None` and `last_ver.get("exit_code") == 0`:
     -> `{"action": "done", "command": "", "reason": "green: nothing more in Stage 1"}`
  7. **Last verification red, budget exhausted, no grants:** If `last_ver is not None` and `last_ver.get("exit_code") == 1` and `state["attempts"]["implementer"] >= sprint_toml["max_attempts"]["implementer"] + state["grants"]["implementer"]`:
     -> `{"action": "escalate_attempts", "command": "", "reason": "Implementer attempt limit reached"}`
  8. **Last verification red, running on granted attempts:** If `last_ver is not None` and `last_ver.get("exit_code") == 1` and `state["attempts"]["implementer"] >= sprint_toml["max_attempts"]["implementer"]` and `state["attempts"]["implementer"] < sprint_toml["max_attempts"]["implementer"] + state["grants"]["implementer"]`:
     -> `{"action": "dispatch", "command": f"actl dispatch-impl --sprint {tag}", "reason": "Dispatching granted implementer attempt"}`
  9. **Last verification red, attempts remaining:** If `last_ver is not None` and `last_ver.get("exit_code") == 1` and `state["attempts"]["implementer"] < sprint_toml["max_attempts"]["implementer"]`:
     -> `{"action": "dispatch", "command": f"actl dispatch-impl --sprint {tag}", "reason": "Retry implementer attempt after red verification"}`
  10. **Initial dispatch (no attempts yet):**
     -> `{"action": "dispatch", "command": f"actl dispatch-impl --sprint {tag}", "reason": "Initial implementer attempt dispatch"}`

### S1-R13 Determinism and Offline Hermetic Purity
- S1-R13.1 `actl.verify` and `actl.guards.*` MUST NOT import network client libraries (`urllib.request`, `http.client`, `socket`, `requests`, `httpx`, `aiohttp`) or invoke live LLMs.
- S1-R13.2 Two consecutive `verify_impl` runs on the same worktree state produce identical `steps` (`id`, `cmd`, `exit_code`, `output_sha256`), `exit_code`, `failing_step`, `failing_line`, and `tripwires` (differing only in `seq`, `id`, `parent` seq, and `StepResult.duration_ms`).

### S1-R14 Completion Protocol (`actl wait` and `wait_session`)
- S1-R14.1 `wait_session(session_name: str, timeout_s: int = 2700, poll_interval_s: float = 1.0) -> dict[str, Any]`:
  - Validates `validate_session_name(session_name)` (`ValueError` if invalid).
  - Verifies `shutil.which("tmux") is not None` (`RuntimeError` / `EnvError` exit `4` if missing).
  - Polls `router.process.list_active_tmux_sessions()` every `poll_interval_s` seconds until `session_name` is absent or `timeout_s` elapses.
- S1-R14.2 Watchdog Overrun: If `session_name` is still active in `tmux` when `timeout_s` elapses, invokes `router.process.kill_session(session_name)` (or `bin/arouter kill <session_name>`), reads `exit_code = router.process.read_exit_code(session_name)` (defaulting to `124` if `143` or `124`), and returns `{"name": session_name, "exit_code": exit_code, "hard_cap": True, "lost": False, "log_sha256": log_sha}`.
- S1-R14.3 Exit-Code Classification & 5s Disappearance Grace:
  - Once `session_name` is absent from `tmux`, polls `router.process.read_exit_code(session_name)` for up to a `5.0s` grace window (or `min(5.0, max(0.2, timeout_s))` when a small test `poll_interval_s` is used, polling at `poll_interval_s` intervals).
  - If `read_exit_code` returns an `int`:
    - `exit_code in (124, 137)` -> `hard_cap = True`, `lost = False`.
    - Any other integer (`0`, `7`, `143`, etc.) -> `hard_cap = False`, `lost = False`.
  - If `read_exit_code` is still `None` after the grace window expires -> `exit_code = None`, `hard_cap = False`, `lost = True`.
  - `log_sha256` is `actl.hashing.file_sha256(router.process.get_log_path(session_name))` if the log file exists, else `None`.

### S1-R15 Log Archiving and Durability Ordering
- S1-R15.1 `archive_session_log(layout, tag, seq, session_name) -> str | None`:
  - Resolves `src_log = router.process.get_log_path(session_name)` and `src_exit = router.process.get_exit_path(session_name)`.
  - If `src_log` exists, copies it to `dst_log = layout.logs_dir(tag) / f"impl-{seq:03d}.log"`, flushes and fsyncs `dst_log`, and verifies `file_sha256(dst_log) == file_sha256(src_log)` (raising `OSError` on mismatch).
  - If `src_exit` exists, copies it to `dst_exit = layout.logs_dir(tag) / f"impl-{seq:03d}.exit"`, flushes and fsyncs `dst_exit`, and verifies `file_sha256(dst_exit) == file_sha256(src_exit)`.
  - Does NOT unlink `src_log` or `src_exit`. Returns `file_sha256(dst_log)` (or `None` if `src_log` does not exist and `dst_log` does not exist).
- S1-R15.2 Unlink-After-Verification-Fsync: `verify_impl` unlinks `src_log` and `src_exit` ONLY AFTER `runs/verification-{seq:03d}.json` has been atomically written and fsynced to disk. If writing `verification-{seq:03d}.json` fails or raises an exception, `src_log` and `src_exit` MUST remain on disk untouched.

### S1-R16 Additive-Change, PB-2 Immutability, and Deliverables Allowlist
- S1-R16.1 Baseline commit: `4e16cc3` (`PB-2` immutability baseline).
- S1-R16.2 On the authoring branch (`wip/author-s1`), `P-S1-02.sh` verifies:
  1. Working tree is clean (`git status --porcelain -z` is empty, ignoring `proof/out/`).
  2. Zero changes (`git diff --name-status -z 4e16cc3..HEAD`) to any PB-2 frozen Stage 0 path (`proof/stage0/`, `proof/run_suite_actl_s0.sh`, `proof/run_suite_exit_code.sh`, `fixtures/golden/expected.d/base.json`, `tools/`, `src/actl/INTERFACES.md`, `schemas/`).
  3. Zero changes to implementation paths (`src/actl/*.py`, `skills/`) on the authoring branch (and when running in implementation mode on `wip/s1-verifier`, `P-S1-02.sh` enforces that `docs/plan/spec-S1.md`, `proof/stage1/`, `test/actl/`, `fixtures/`, `tools/`, and `src/actl/INTERFACES.md` remain unmodified from the Stage 1 authoring pin while allowing only Stage 1 implementation paths).
  4. Exact membership of the 39 Stage 1 authoring deliverables: every changed path in `4e16cc3..HEAD` has status `A` (Added) and belongs to the exact 39-file inventory, and all 39 files exist on disk.

## 2. Clause-Level Traceability and Vacuity Matrix

| Clause IDs | Proof / Test | Positive Control | Negative / Adversarial Control | Empty / Pass / Fail Stand-In Rejection |
|---|---|---|---|---|
| S1-R1.1..R1.7, S1-R7.1, S1-R7.3 | `P-S1-01.sh`, `test_verify_s1.py` | `good.patch` -> exit `0`, `verification-006.json` valid, `prior_attempt.json` absent/removed | `bad_scope.patch` -> exit `1`; checks `load_expected()["cases"]["good"]` | Empty: ImportError; Always-pass: fails schema/step count/file write; Always-fail: fails `exit_code == 0` |
| S1-R16.1..R16.2 | `P-S1-02.sh` | Clean tree, all 39 deliverables present, zero frozen diff | Self-tests reject lookalike prefix (`spec-S1.md.extra`), bad ext (`proof/stage1/foo.txt`), deletion (`D`), rename (`R`) | Empty diff: fails `TOTAL_CHANGES == 0`; Frozen touch: fails PB-2 check |
| S1-R3.3 | `P-S1-03.sh`, `test_guards_s1.py` | `good.patch` -> `G3` exit `0` | `bad_scope.patch` -> `G3` exit `1` (`api/cli.py`); symlink mode `120000` -> `G3` exit `1` | Constant-fail rejected by `good.patch` positive control |
| S1-R3.4 | `P-S1-04.sh`, `P-S1-11.sh`, `test_guards_s1.py` | Thawed `test/test_users.py` with valid added class & `async def test_*` -> `G4` exit `0` | `bad_testcount.patch` (dropped test), hollow bodies (`pass`, `...`, docstring, `assert True`), syntax error -> `G4` exit `1` | Constant-fail rejected by positive control; constant-pass rejected by negative cases |
| S1-R3.5 | `P-S1-05.sh`, `P-S1-12.sh`, `test_guards_s1.py` | Clean diff + `[[allow]]` SHA-256 exempted line -> `G5` exit `0` | `bad_secret.patch` & closure `backlog` secret -> `G5` exit `1`, raw `AKIA...` scrubbed to `[REDACTED]` | Constant-fail rejected by clean/exempted control; unredacted output fails grep |
| S1-R3.6 | `P-S1-06.sh`, `test_guards_s1.py` | Clean `good.patch` (`retrieval = 1`) + `[[allow]]` exception -> `G6` exit `0` | `bad_forbidden.patch` (`eval(`), aliased `import os as _o; _o.system(...)`, regex fallback on syntax-invalid file -> `G6` exit `1` | Constant-fail rejected by `good.patch` control |
| S1-R5.1..R5.4 | `P-S1-07.sh` | `good.patch` -> `run_o1` returns 4 green steps (`01`, `02`, `03`, `probe`) in lexical order | `bad_proof_o1.patch` -> `O1:01_public.sh` green (`0`), `O1:02_no_email.sh` red (`1`, `"seeded email"`) | Constant-fail stub fails `good.patch` control and `01_public.sh == 0` check |
| S1-R3.7, S1-R2.2 | `P-S1-08.sh`, `test_guards_s1.py` | `run_selftests()` returns 6 steps (`G1..G6`) all `exit_code == 0` | Scratch copy with corrupt `config/secrets.toml` -> `run_selftests()` returns `exit_code == 3` and `verify_impl` halts (`exit_code=None`, `halt.reason="selftest_failed"`) | No `except TypeError: pass`; stub ignoring config fails negative control |
| S1-R3.1, S1-R2.2 | `P-S1-09.sh`, `test_verify_s1.py` | Untampered oracle -> `G1` exit `0` | 1-byte tamper in `oracle-003/probe.sh` (+ `hard_cap=True`) -> `G1` exit `3`, `verification.exit_code is None`, `halt.reason == "integrity_mismatch"`, `attempts.implementer == 0` | Constant-fail fails untampered control; constant-pass fails tampered control |
| S1-R3.3 | `P-S1-10.sh` | `unittest.mock.patch("actl.scope.match", wraps=...)` records calls for each diff path on `good.patch` | `scope.match` raising `ValueError` is caught by `G3` and turned into `exit_code == 1` (`denied`) | Stub not calling `actl.scope.match` fails `call_count >= 1` |
| S1-R4.1..R4.4 | `P-S1-13.sh` | Injected proof witnesses `<wt>.oracle-stage` exists outside `<wt>`, mode `0550`, `cwd == <wt>`, no `mutants/` staged, writes witness file | Simulated exception/timeout during `O1` still removes `<wt>.oracle-stage` in `finally` | Empty `run_o1() -> []` fails witness file & 4-step assertion |
| S1-R5.2..R5.4 | `P-S1-14.sh` | Injected proof dumps `env` to witness file; only allowlisted vars (`PATH, LANG, HOME, TMPDIR, ACTL_TARGET_CMD, PYTHONDONTWRITEBYTECODE`) present, `FORBIDDEN_VAR_TEST` absent | Proof sleeping past `timeout_s=1` is killed and returns `exit_code == 124` | Stub not running proof fails witness SHA check |
| S1-R7.2..R7.4 | `P-S1-15.sh` | Red `verify_impl` writes `inbox/prior_attempt.json` with 4 keys and real `git diff`; subsequent green `verify_impl` unlinks `prior_attempt.json` | Schema validation rejects extra keys; verifies no oracle script body in `prior_attempt.json` | Stub not unlinking on green fails second stage |
| S1-R9.1..R9.6, S1A-15 | `P-S1-16.sh` | `dispatch-impl --no-run` creates `implementer-006` at `base_sha` on `wip/006`, stages `inbox/attempt.json`, `spec-001.md`, `contract-005.json`, `solution_key.patch` (mode `0440`), launches 0 tmux sessions | Commit on `main` in cloned workspace is blocked by hook; commit on `wip/006` with `WI-` message succeeds | Stub doing nothing fails workspace & inbox checks |
| S1-R10.1..R10.4 | `P-S1-17.sh`, `P-S1-27.sh`, `test_session_s1.py` | `clean.log` + `clean.jsonl` + governance lines produce `[]` | `dirty_ansi.log` + `dirty_oracle.jsonl` under `ATOOLS_CURSOR_HOME` + mixed governance/attack line produce hits; `strict_tripwire=True` forces `exit_code=1, failing_step="tripwire"` | Stub returning `[]` fails dirty log/transcript checks; stub flagging everything fails `clean.jsonl` check |
| S1-R12.1..R12.3 | `P-S1-18.sh`, `test_next_phase3.py` | Evaluates all 10 precedence rows on valid golden sprint + non-implementer `None` fall-through | Unverified `blocked` closure -> `verify` (Row 3); verified `blocked_check` -> `hold_owner` (Row 5) | Stub returning constant dict fails 10-row matrix |
| S1-R8.1..R8.3 | `P-S1-19.sh` | `skills/actl-implementer/SKILL.md` exists, contains required inbox/outbox/`wip/` instructions, and prohibits `records/`/`oracle`/`proof/` access without imperative leaks | Baseline suites (`run_suite_actl_s0.sh`, `run_suite_exit_code.sh`) verified intact | Missing skill on base `4e16cc3` fails RED cleanly |
| S1-R9.3..R9.5, D-42 | `P-S1-20.sh` | Private tmux server + stub `agent`: Case A (exit `0` + valid outbox closure) -> `verification.exit_code == 0`, `session.exit_code == 0`; Case B (exit `7` + valid outbox closure) -> `verification.exit_code == 0`, `session.exit_code == 7` | Poison `closure-draft.json` inside worktree is ignored when outbox closure is absent -> `G2` red | Stub returning `0` without running `arouter`/writing `verification` fails artifact & `.exit` checks |
| S1-R14.1..R14.3, D-45 | `P-S1-21.sh`, `test_session_s1.py` | Real private tmux session with `SLEEP` and `-t 2s` -> `wait_session` returns `exit_code == 124`, `hard_cap == True`, `lost == False`; dynamic timeout `2733s` derived from `sprint.toml` | `verify_impl` with `hard_cap=True` marks `G2` red and increments `state.hard_caps_tripped` | Uncontrolled mock session replaced by real private tmux session + deterministic unit tests |
| S1-R14.4 | `P-S1-22.sh`, `test_session_s1.py` | Real private tmux session killed via `tmux kill-server` with `.exit` removed -> `wait_session` waits grace window and returns `lost == True, exit_code is None` | Session writing `.exit` within grace window returns `lost == False, exit_code == 0` | Contrasts lost vs normal completion on real private tmux server |
| S1-R15.1..R15.2 | `P-S1-23.sh`, `P-S1-24.sh` | `archive_session_log` copies `.log` and `.exit` to `runs/logs/impl-006.{log,exit}`, verifies SHA-256, and leaves originals intact; `verify_impl` unlinks originals AFTER `verification-006.json` fsync | Simulated failure before `verification` write leaves original `.log` and `.exit` intact on disk | Checks both `.log` and `.exit` hashes and pre/post unlink states |
| S1-R9.2 | `P-S1-25.sh` | Live session on private tmux server recorded in `state["tmux_sessions"]` causes `dispatch-impl` to fail with `UsageError` (exit `2`) before reserving `seq` | Once tmux session terminates, `dispatch-impl --no-run` succeeds (exit `0`) | Distinguishes live tmux collision from `--no-run` workspace staging |
| S1-R9.4 | `P-S1-26.sh` | Valid 99,990-byte ASCII instruction launches stub `arouter` and returns `0` | `>= 100,000` JSON-escaped bytes, non-ASCII (`"caf?"`), `"help"`, and bad session name raise `ValueError` before `arouter` runs | Always-raise stub fails the valid positive control |
| S1-R11.1..R11.3, S1-R13.1..R13.2 | `P-S1-28.sh`, `test_verify_s1.py` | Invokes `actl.cli.main([...])` testing exit codes `0` (green `verify-impl` & `selftest`), `1` (red `verify-impl`), `2` (missing args / bad `--closure`), `3` (tampered oracle halt & broken `selftest`), `4` (missing `tmux` on `wait`) | Runs `verify_impl` twice on identical tree and asserts canonical JSON equality (modulo `seq`, `id`, `duration_ms`) and zero network imports | Tests real CLI parser `actl.cli.main` across all 5 exit codes `0, 1, 2, 3, 4` |
| S1-R6.1..R6.4 | `P-S1-29.sh`, `test_verify_s1.py` | `good.patch` -> `run_o2` returns `[StepResult(id="O2", exit_code=0)]` with normalized `--junitxml=<tmp_xml>` cmd | `bad_regression_o2.patch` -> `id == "O2:test_users::test_get_user_unknown_returns_none"`, `exit_code == 1`; disallowed `repo_test_cmd` raises `ValueError` (never `ImportError`) | Positive control + exact normalized node ID check |

## 3. Ambiguity Register (S1A-1..S1A-15)

| ID | Ambiguity / Tension | Resolution (Normative for Stage 1) |
|---|---|---|
| **S1A-1** | `expected.d` case split between `base.json` and `s1.json`. | `base.json` (frozen) holds the 13 baseline cases (`good`, `bad_*`, `mutant_*`, `null_base`, `solution_key`). `s1.json` defines the 7 Stage 1 verification cases (`closure_invalid_schema`, `closure_blocked_early`, `closure_blocked_valid`, `session_lost_g2`, `session_hard_cap_g2`, `oracle_tamper_g1`, `tripwire_strict`). Both are loaded via `actl.schemas.load_expected()`. |
| **S1A-2** | Closure file lookup and `closure-draft.json` ignore rule (`D-42`). | `verify_impl` only reads `closure_path` when explicitly passed (or `layout.outbox(tag, "implementer") / "closure.json"` when invoked from `dispatch-impl`). Any `closure-draft.json` or `closure.json` inside `<worktree>` is ignored. |
| **S1A-3** | `wait_session` default `timeout_s` (`INTERFACES.md` default `2700` vs `D-45` dynamic derivation). | `wait_session(session_name: str, timeout_s: int = 2700, poll_interval_s: float = 1.0)` preserves the exact `INTERFACES.md` default (`2700`) for `P-S0-26` introspection. If `timeout_s is None` or when called from `cmd_wait` / `dispatch-impl` without `--timeout`, a helper `compute_wait_timeout(sprint_toml) -> int` computes `parse_duration(wall_clock) + parse_duration(kill_grace) + 30` (`2700 + 3 + 30 = 2733`). |
| **S1A-4** | `verification.exit_code` vs CLI exit code on `halt` (`D-24`, `O-17`). | On `G1` integrity mismatch or `run_selftests()` failure, `verification["exit_code"]` is `None`, `verification["halt"]` is `{"reason": "integrity_mismatch" | "selftest_failed"}`, and the CLI returns exit code `3`. |
| **S1A-5** | `O2` JUnit XML `<testcase>` to `StepResult.id` normalization (`SA-7`). | Given `<testcase classname="C" name="N">`, strip any `[...]` parameter suffix from `N` only if `N` is empty without it (keep `N` otherwise), extract the module stem from `C` by taking the segment starting with `test_` (e.g. `test.test_users` or `test.test_users.TestClass` -> `test_users`), and format `f"O2:{stem}::{N}"`. If multiple tests fail, the first failing `<testcase>` in document order is used. |
| **S1A-6** | `attempt.json` and staged inbox files. | Written to `layout.inbox(tag, "implementer")` with mode `0o440` (`attempt.json`, `spec-001.md`, `contract-005.json`, and `solution_key.patch` when `solution_key_exposure == "full"`). Candidate worktree remains `git status --porcelain` clean. |
| **S1A-7** | Default `worktree` resolution when `worktree=None` in `verify_impl` / `cmd_verify_impl`. | Scans `layout.root / "sprints" / layout.repo / tag / "workspaces"` for directories matching `implementer-[0-9]{3,}` via `parse_seq_from_name`, selecting the one with highest `seq`. If none exists, `verify_impl` raises `FileNotFoundError` (translated by `cmd_verify_impl` to `UsageError`, exit `2`). |
| **S1A-8** | `failing_line` sanitization (`O-8`). | Exposed as `actl.verify.sanitize_failing_line(text: str) -> str`: strips CSI `\x1b\[[0-9;?]*[ -/]*[@-~]` and OSC `\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)`, replaces `\r`, `\n`, `\t` with `" "`, replaces code points `< 0x20`, `== 0x7f`, or lone `\x1b` with `"?"`, strips leading/trailing spaces, and slices `[:300]`. |
| **S1A-9** | `G4` AST traversal boundaries. | Counts `ast.FunctionDef` and `ast.AsyncFunctionDef` whose `name.startswith("test_")` at module top-level or directly inside a top-level `ast.ClassDef`. Nested functions inside functions are not counted. |
| **S1A-10** | Persisted representation of confirmed `blocked` closure (`GD-04` item 6). | No custom keys are added to `state.json` or `verification.json` (preserving `additionalProperties: false`). When a `reason == "blocked"` closure passes all post-`O2` blocked preconditions (`S1-R3.2`), `verification["stage"] == "blocked_check"`, `verification["failing_step"] == closure["blocking_step"]` (`!= "G2"`), and `verify_impl` sets `state["status"] = "hold"`. If a blocked closure fails a blocked precondition, `verification["failing_step"] == "G2"` and `state["status"]` stays `"running"`. |
| **S1A-11** | Extra properties or malformed JSON in `closure.json`. | Malformed JSON or extra properties in a submitted closure fail `G2` pre-check (`exit_code = 1`, `failing_step = "G2"`). A non-existent path passed to `--closure` raises `UsageError` (exit `2`). |
| **S1A-12** | `wait_session` 5-second disappearance grace window. | After `session_name` disappears from `tmux list-sessions`, `wait_session` polls `read_exit_code(session_name)` for up to `grace_s = min(5.0, max(0.2, float(timeout_s)))` at `poll_interval_s` intervals before declaring `lost = True`. |
| **S1A-13** | Provenance-safe tripwire exclusions (`GD-04`). | Exclusions match only complete lines or exact JSON property values from `SKILL.md`, staged `contract-*.json`, or `"O1:<script>"` tokens from `prior_attempt.json`. Any line containing a tripwire pattern outside those exact strings is flagged. |
| **S1A-14** | `G6` dual AST + regex scanning and `[[allow]]` exemptions. | Added lines in `git diff -U0 <base_sha>..HEAD` on non-`FROZEN` files are checked by regex (`F001..F008`) AND (for parseable `.py` files) by an AST `Call` visitor checking added line spans (resolving module/function aliases like `import os as _o`). `[[allow]]` entries in `config/forbidden.toml` require exact `(rule, path, line)` match. |
| **S1A-15** | Git hook enforcement in dispatched implementer workspaces. | `dispatch-impl` clones the workspace with `-c core.hooksPath=/dev/null` during clone setup, then copies `hooks/pre-commit` and `hooks/commit-msg` into `<workspace>/.git/hooks/` (mode `0755`) and unsets local `core.hooksPath` so commits in the workspace enforce `wip/*` branch protection and `WI-` commit message formatting. Tested by `P-S1-16.sh`. |

## 4. Proposed Decisions (Closed for Stage 1)

### O-4: G4 Test Preservation Scope
Stage 1 enforces Python AST test counting and hollow-body rejection (`S1-R3.4`) on all thawed `test/**/*.py` files. Non-Python test files are ignored by `G4` in Stage 1 (deferred to Stage 4+).

### O-5: Normative `config/forbidden.toml` Schema and Ruleset (`F001..F008`)
`config/forbidden.toml` contains `[[rules]]` entries with keys `id`, `language` (`"python"` or `"any"`), `kind` (`"ast_call"` or `"regex"`), `pattern` (ERE/Python regex), `applies_to` (`"non_frozen"`), and `message`, plus optional `[[allow]]` tables (`rule`, `path`, `line`):
- `F001` (`ast_call` + `regex`): `(^|[^A-Za-z0-9_.])(eval|exec)\s*\(`  --  `"forbidden call: dynamic code execution (eval/exec)"`
- `F002` (`ast_call` + `regex`): `\bos\.(system|popen|exec[lv]p?e?)\s*\(`  --  `"forbidden call: shell/process execution via os"`
- `F003` (`ast_call` + `regex`): `\bsubprocess\b`  --  `"forbidden call: subprocess module usage"`
- `F004` (`ast_call` + `regex`): `\b(socket|urllib\.request|http\.client|requests|httpx|aiohttp)\b`  --  `"forbidden call: outbound network library"`
- `F005` (`ast_call` + `regex`): `\b(pickle|marshal)\.loads?\s*\(`  --  `"forbidden call: unsafe deserialization"`
- `F006` (`regex`): `(records/|/etc/actl|probe\.sh|/proofs/|/mutants/)`  --  `"forbidden call: oracle or records path reference"`
- `F007` (`regex`): `(git\s+push|--no-verify|core\.hooksPath)`  --  `"forbidden call: git safety bypass"`
- `F008` (`regex`): `(\bsudo\b|chmod\s+(-R\s+)?[0-7]*7[0-7]*7)`  --  `"forbidden call: privilege or mode escalation"`

### O-6: Normative `config/secrets.toml` Schema and Ruleset (`S001..S007`)
`config/secrets.toml` contains `[[rules]]` entries with keys `id`, `pattern`, `description`, and optional `[[allow]]` tables (`rule`, `line_sha256` = 64-hex SHA-256 of `line.strip().encode("utf-8")`):
- `S001`: `\b(AKIA|ASIA)[0-9A-Z]{16}\b` (AWS Access Key ID)
- `S002`: `\bgh[pousr]_[A-Za-z0-9]{36,}\b` (GitHub Token)
- `S003`: `\bsk-[A-Za-z0-9]{20,}\b` (OpenAI / API Secret Key)
- `S004`: `\bxox[baprs]-[A-Za-z0-9-]{10,}\b` (Slack Token)
- `S005`: `-----BEGIN [A-Z ]*PRIVATE KEY-----` (PEM Private Key Header)
- `S006`: `\bAIza[0-9A-Za-z_-]{35}\b` (Google API Key)
- `S007`: `(?i)(secret|token|passwd|password|api[_-]?key)\s*[:=]\s*['"][^'"\s]{16,}['"]` (Generic Secret Assignment)

### O-17: Halt Record `exit_code = null` and Process Exit Code `3`
Ratified per `D-24`: On any `halt` (`integrity_mismatch` or `selftest_failed`), `verification["exit_code"]` is `None`, `verification["halt"]` is `{"reason": ...}`, `state["status"]` becomes `"hold"`, and the CLI exits with status `3`.
