# spec-S1.md - Stage 1 (Verifier and Implementer Loop) Specification and Proof Map
Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
Date: 2026-10-26. Baseline: atools commit 4e16cc3 (VERSION v0.1.8).
Inputs: actl_Design.md (normative), actl_Build_Plan-Stages0to2_addendum.md (amended 2026-10-24), actl_Build_Plan-Stages0to2.md, src/actl/INTERFACES.md (frozen, PB-2/PB-4).
Rulings applied: D-24, D-30..D-40 (Layout transition L-1..L-11), D-41, D-42, D-45, O-17.

## 0. Conventions
- MUST/SHOULD/MAY follow RFC 2119.
- Clause IDs S1-Rk.n provide immutable traceability anchors for Stage 1 proofs and pytest suites.
- Proof conventions: scripts exit 0 on pass and 1 on failure with a line starting with "FAIL: <requirement_id>: <reason>". Exit 4 is reserved for environment preconditions (missing external tool like tmux, git, pytest). ENVFAIL: in pytest maps to exit 4.
- Product CLI exit codes: 0 = ok/green, 1 = red (replay/assertion failure), 2 = usage/schema/parse error, 3 = halt (state integrity or guard self-test failure; no attempt consumed), 4 = environment error.
- Layout: All paths constructed strictly via actl.layout.Layout methods (records/, sprints/, mailboxes/, profiles/).
- Per D-34, artifact kind is "verification" (not "ev"). Filename is verification-{seq:03d}.json.
- Per D-42, verify_impl and dispatch-impl MUST NOT read closure-draft.json from the workspace worktree. Staged closures are read exclusively from mailboxes/implementer/outbox/closure.json or runs/closure-{seq:03d}.json.
- Per D-45, wait_session timeout_s defaults dynamically to wall_clock + kill_grace + 30s.
- Per D-24 and O-17, verification.exit_code holds 0..255 or null; on halt or interruption prior to verifier verdict, exit_code is null and the process exits with code 3.

## 1. Requirements (Testable Expansion)

### S1-R1 Verification Record and StepResult
- S1-R1.1 StepResult is re-exported by actl.verify from actl.schemas. Fields: id (str), cmd (str), exit_code (int), output_sha256 (64-hex str), output_tail (str, default empty), duration_ms (int >= 0, default 0), failing_line (str | null, default None).
- S1-R1.2 StepResult.to_verification_step() produces exactly {"id": self.id, "cmd": self.cmd, "exit_code": self.exit_code, "output_sha256": self.output_sha256}.
- S1-R1.3 verify_impl(layout, tag, closure_path=None, worktree=None, fail_fast=True, session_info=None, strict_tripwire=False) returns a dictionary strictly conforming to schemas/verification.json.
- S1-R1.4 Verification Parent & Stamping: The evaluated closure is read from closure_path (or defaults to mailboxes/implementer/outbox/closure.json). On evaluation, the verifier stamps it to runs/closure-{seq:03d}.json (where seq matches verification seq). verification.parent is f"closure-{seq:03d}.json", or null if no closure was supplied or present.
- S1-R1.5 Pipeline Fail-Fast & Finalization: When fail_fast=True, verification stops executing subsequent validation steps immediately on the first non-zero StepResult. However, artifact finalization (writing verification-{seq:03d}.json, updating state, writing prior_attempt.json on exit_code 1, and archiving session logs) always executes. When closure.reason == "blocked", fail_fast is forced to False across G3-G6 and O2 to collect all diagnostic data before evaluating the G2 blocked post-check.
- S1-R1.6 failing_step is null when all executed steps succeed (exit_code 0); otherwise it contains the identifier of the first failing step (e.g. "G3", "O1:02_no_email.sh", "O2:test_users::test_public", "tripwire").
- S1-R1.7 failing_line is null on success; on failure it contains at most 300 Unicode code points, stripped of ANSI CSI and OSC escape sequences per O-8, with newlines and control characters (< 0x20) replaced by spaces.

### S1-R2 Pipeline Order, Halt Precedence, and Session State
- S1-R2.1 Pipeline execution order is strictly: run_selftests() -> G1 (oracle tamper) -> G2 (closure schema pre-check) -> G3 (scope) -> G4 (test preservation) -> G5 (secrets) -> G6 (forbidden code) -> O1 (oracle proofs) -> O2 (repo tests) -> strict tripwire scan -> G2 (blocked precondition post-check, if reason == "blocked").
- S1-R2.2 Absolute Halt Precedence: Any integrity violation in G1 OR guard self-test failure in run_selftests() halts the pipeline immediately without executing subsequent steps and without incrementing attempts.implementer. The verification record sets verification.exit_code = null, verification.halt = {"reason": "integrity_mismatch" | "selftest_failed"}, the sprint status is set to "hold", and the CLI process exits with code 3. This halt condition strictly supersedes any session_info flags.
- S1-R2.3 Red vs CLI Usage Error: Malformed CLI arguments or unparseable inputs raise UsageError resulting in process exit code 2. In contrast, a submitted closure failing schema validation during verification fails guard G2 with StepResult(id="G2", exit_code=1), recording verification.exit_code = 1, incrementing attempts.implementer, writing prior_attempt.json, and exiting CLI with code 1.
- S1-R2.4 Session Handling: If session_info is provided with lost=True or hard_cap=True (and no earlier self-test or G1 halt occurred), G2 is forced red (exit_code 1), failing_step is set to "G2", and failing_line states the watchdog termination reason. If hard_cap=True, state.hard_caps_tripped is incremented by 1.

### S1-R3 Guards G1-G6 and run_selftests
- S1-R3.1 G1 (Oracle Integrity): Compares manifest_sha256(oracle_dir) with active contract's oracle.manifest_sha256. Mismatch raises exit code 3 halt ("integrity_mismatch").
- S1-R3.2 G2 (Closure Schema): Validates closure against schemas/closure.json. When closure.reason == "blocked", ensures: (a) attempts.implementer >= min_attempts_before_block, (b) notes and backlog non-empty, (c) blocking_step matches one executed failing step id, (d) post-O2 verification confirms blocking_step actually failed.
- S1-R3.3 G3 (Scope): Executes git diff --raw -z --no-renames {base_sha}..HEAD in worktree. File modes outside {100644, 100755, 000000} fail G3. Every path is checked against actl.scope.match(rules, path). Any "denied" or "frozen" path fails G3.
- S1-R3.4 G4 (Test Count and AST Guard): When any test/** path is thawed/allowed by scope, parses Python AST of base_sha and candidate HEAD. Counts FunctionDef and AsyncFunctionDef whose names start with "test_" (both top-level and inside test classes). Count in candidate must be >= base. Candidate test functions must not be hollow (cannot consist only of pass, ellipsis, docstring, or assert True). Syntax errors fail G4.
- S1-R3.5 G5 (Secrets): Scans added diff lines (lines starting with '+' but not '+++') and closure notes/backlog against config/secrets.toml regex patterns. Exact matched line SHA-256 present in [[allow]] table is exempted. Matched secrets are redacted from failing_line and output tails.
- S1-R3.6 G6 (Forbidden Calls): Normative dual AST and regex scanning. Scans added lines on non-FROZEN paths against config/forbidden.toml. Python files are parsed into AST to inspect Call nodes; non-Python or syntax-invalid additions are checked against regex patterns. Matching calls without [[allow]] exception fail G6.
- S1-R3.7 run_selftests() executes synthetic in-memory positive and negative cases for G1-G6. Returns list[StepResult]. If any test fails, returns exit_code 3.

### S1-R4 Out-of-Tree Oracle Staging
- S1-R4.1 Active oracle proofs/ directory and probe.sh are staged into a temporary directory sibling to worktree: <worktree>.oracle-stage/.
- S1-R4.2 No oracle file or directory is copied into, modified in, or left inside candidate worktree.
- S1-R4.3 Staged proof files and probe.sh are set to mode 0550.
- S1-R4.4 The staging directory is unconditionally unlinked in a finally block upon completion of O1, even if proofs fail or an exception is raised.

### S1-R5 O1 Execution
- S1-R5.1 Staged proofs in <worktree>.oracle-stage/proofs/*.sh are executed in lexical filename order, followed by <worktree>.oracle-stage/probe.sh.
- S1-R5.2 Execution environment is strictly allowlisted: PATH, LANG, LC_ALL, throwaway HOME, throwaway TMPDIR, and ACTL_TARGET_CMD. All caller environment variables not in this allowlist are purged.
- S1-R5.3 cwd is set to candidate worktree root.
- S1-R5.4 Per-proof timeout is timeout_s (default 60s). Overrun terminates process group and records exit code 124.

### S1-R6 O2 Execution
- S1-R6.1 Reads repo_test_cmd from sprint.toml (default: "python3 -m pytest test -q -rf").
- S1-R6.2 Parses repo_test_cmd using shlex.split(posix=True) with shell=False.
- S1-R6.3 argv[0] MUST be in ("python3", "pytest"); any other executable raises ValueError / UsageError.
- S1-R6.4 Appends --junitxml=<tmp_xml> to argv, executes in worktree, and parses JUnit XML to extract failing node. If classname matches test file stem, formats as O2:{file_stem}::{name}, else O2:{classname}::{name}. On timeout (default 120s), records exit code 124.

### S1-R7 Verification Emission and prior_attempt.json
- S1-R7.1 Verification artifact is atomically written to runs/verification-{seq:03d}.json via temp file and os.replace, followed by directory fsync.
- S1-R7.2 Stamped closure is atomically written to runs/closure-{seq:03d}.json with kind="closure", seq=seq, parent=contract_id.
- S1-R7.3 When verification.exit_code == 1, writes mailboxes/implementer/inbox/prior_attempt.json containing strictly 4 keys: diff (git diff {base_sha}..HEAD), failing_step, failing_line, closures_submitted.
- S1-R7.4 If verification.exit_code == 0, removes any existing prior_attempt.json from implementer inbox.

### S1-R8 Implementer Skill Governance
- S1-R8.1 skills/actl-implementer/SKILL.md is evaluated against governance criteria.
- S1-R8.2 Required instructions: reading mailboxes/implementer/inbox/, reading attempt.json, writing mailboxes/implementer/outbox/closure.json, isolated git commits on wip/{seq:03d}, checking git status.
- S1-R8.3 Forbidden instructions: running proof suites (proof/*.sh), accessing records/, accessing oracle directories, reading solution_key.patch.

### S1-R9 Implementer Workspace Dispatch (actl dispatch-impl)
- S1-R9.1 Syntax: actl dispatch-impl --sprint <TAG> [--mode detach|foreground] [--tier cheap|balanced|smart] [--engine <ENG>] [--no-run] [--strict-tripwire] [--json].
- S1-R9.2 Preflight: Verifies no active tmux session matches formatted session name. Raises StateIntegrityError (exit 3) if active session exists.
- S1-R9.3 Workspace Isolation: Clones target_repo at base_sha into workspaces/implementer-{seq:03d} with git checkout -b wip/{seq:03d}.
- S1-R9.4 Staging: Copies active spec and contract to mailboxes/implementer/inbox/. Writes attempt.json (seq, branch, sprint_tag, contract, spec) to inbox.
- S1-R9.5 Prompt construction: Single static instruction. Total serialized JSON length < 100,000 bytes. Fails if instruction contains "help".
- S1-R9.6 --no-run flag creates workspace and stages inbox without launching a session, returning exit 0.

### S1-R10 Tripwire Scanner and Profile Sanitization
- S1-R10.1 Scans candidate ANSI-stripped console logs and Cursor JSONL transcripts for references to proofs/, probe.sh, oracle, solution_key.
- S1-R10.2 Excludes lines originating from skills/actl-implementer/SKILL.md, contract-*.json, and prior_attempt.json failing_step tokens.
- S1-R10.3 When strict_tripwire=True and no earlier step failed, any tripped wire forces verification exit_code = 1 with failing_step = "tripwire".
- S1-R10.4 Honors ATOOLS_CURSOR_HOME environment variable for profile and transcript discovery.

### S1-R11 CLI Contract (actl verify-impl and actl selftest)
- S1-R11.1 Syntax: actl verify-impl --sprint <TAG> [--closure <PATH>] [--worktree <PATH>] [--no-fail-fast] [--strict-tripwire] [--json]. Exits: 0 = green, 1 = red, 2 = usage/schema error, 3 = halt, 4 = environment error. If --closure is omitted, defaults to mailboxes/implementer/outbox/closure.json; if that file is absent, proceeds with workspace verification and parent=null.
- S1-R11.2 actl selftest [--json] runs run_selftests() and exits 0 on all pass, 3 on any failure.

### S1-R12 Phase 3 Decision Rules (actl next)
- S1-R12.1 Implemented in src/actl/next_rules/phase3.py with PRIORITY = 30.
- S1-R12.2 Strict Ordered Precedence Table (First matching condition wins):
  1. Active tmux session running -> {"action": "wait", "command": "actl wait <session>", "reason": "Implementer session in progress"}
  2. Sprint status == "hold" -> {"action": "hold_owner", "command": "", "reason": "Sprint is on hold due to integrity violation or self-test failure"}
  3. Finished session, closure present with reason == "blocked", preconditions met -> {"action": "hold_owner", "command": "", "reason": "Implementer blocked with valid rationale"}
  4. Finished session with exit code, closure present in outbox -> {"action": "verify", "command": "actl verify-impl --sprint <tag> --closure <path>", "reason": "Closure submitted for verification"}
  5. Finished session, no closure written -> {"action": "verify", "command": "actl verify-impl --sprint <tag>", "reason": "Verify workspace after session exit without closure"}
  6. Last verification green (exit_code 0) -> {"action": "promote", "command": "actl promote implementer --sprint <tag>", "reason": "Verification passed"}
  7. Last verification red, attempts >= max_attempts, grants == 0 -> {"action": "escalate_attempts", "command": "", "reason": "Implementer attempt limit reached"}
  8. Last verification red, attempts >= max_attempts, grants > 0 -> {"action": "dispatch", "command": "actl dispatch-impl --sprint <tag>", "reason": "Dispatching granted implementer attempt"}
  9. Last verification red, attempts < max_attempts -> {"action": "dispatch", "command": "actl dispatch-impl --sprint <tag>", "reason": "Retry implementer attempt"}
  10. Active stage is not implementer -> returns None (falls through to lower priority rules).

### S1-R13 Determinism and Offline Hermetic Purity
- S1-R13.1 Gating verification executes zero network calls and invokes no live LLMs.
- S1-R13.2 Deterministic Output Normalization: Repeated verify_impl execution on identical worktree produces identical StepResult sequences, command exit codes, and output_sha256 digests. StepResult duration_ms is excluded from equality and determinism assertions. Dynamic command arguments such as temporary junitxml paths (--junitxml=/tmp/...) are normalized to --junitxml=<tmp_xml> before computing command strings and output digests.

### S1-R14 Session Monitoring (actl wait and wait_session)
- S1-R14.1 wait_session(session_name, timeout_s=None, poll_interval_s=1.0) polls tmux list-sessions and router.process.read_exit_code.
- S1-R14.2 Derives timeout_s dynamically if None: wall_clock (from sprint.toml hard_cap) + kill_grace (3s) + 30s buffer.
- S1-R14.3 If session exits with 124 or 137, marks hard_cap = True.
- S1-R14.4 If session disappears from tmux without .exit within 5 seconds, marks lost = True.

### S1-R15 Log Archiving and Retention
- S1-R15.1 archive_session_log(layout, tag, seq, session_name) copies raw log to runs/logs/impl-{seq:03d}.log and .exit to runs/logs/impl-{seq:03d}.exit.
- S1-R15.2 Verifies copied file SHA-256 matches source before proceeding.
- S1-R15.3 Original session log and .exit are unlinked ONLY after verification record has been fsynced to disk.

### S1-R16 Additive-Change, PB-2 Immutability, and Target Scope Rules
- S1-R16.1 Baseline commit: 4e16cc3 (PB-2 immutability baseline).
- S1-R16.2 Authoring Branch Policy (P-S1-02): Branch wip/author-s1 must have non-empty changes relative to 4e16cc3, but zero modifications to frozen paths: proof/stage0/, fixtures/golden/expected.d/base.json, src/actl/INTERFACES.md, tools/.
- S1-R16.3 Implementer Target Modification Allowlist: During candidate verification in Stage 2, candidate patches are permitted to modify ONLY: src/core/config.py, src/sessions/storage.py, install.sh, README.md.

## 2. Traceability and Vacuity Matrix

| Req ID | Proof ID | Target Script / Test | Empty Stand-In | Always-Pass Stand-In | Always-Fail Stand-In | Mutation Classes Killed (Seed 73) |
|---|---|---|---|---|---|---|
| S1-R1 | P-S1-01 | proof/stage1/P-S1-01.sh | FAIL (missing module) | FAIL (expects real run) | FAIL (rejects red) | Comparison flip, return code swap |
| S1-R16| P-S1-02 | proof/stage1/P-S1-02.sh | FAIL (empty diff) | FAIL (detects frozen touch) | FAIL (blocks valid adds) | Allowlist inversion, path check removal |
| S1-R3 | P-S1-03 | proof/stage1/P-S1-03.sh | FAIL (missing module) | FAIL (accepts bad scope) | FAIL (checks exact G3 line) | Regex negation, scope match bypass |
| S1-R3 | P-S1-04 | proof/stage1/P-S1-04.sh | FAIL (missing module) | FAIL (accepts test drop) | FAIL (checks exact G4 line) | AST counter decrement, hollow check drop |
| S1-R3 | P-S1-05 | proof/stage1/P-S1-05.sh | FAIL (missing module) | FAIL (accepts leaked secret) | FAIL (checks exact G5 line) | Regex boundary removal, allowlist bypass |
| S1-R3 | P-S1-06 | proof/stage1/P-S1-06.sh | FAIL (missing module) | FAIL (accepts forbidden call)| FAIL (checks exact G6 line) | AST call matcher drop, keyword swap |
| S1-R5 | P-S1-07 | proof/stage1/P-S1-07.sh | FAIL (missing module) | FAIL (accepts seeded fail) | FAIL (checks exact O1 step) | Proof exit code check inversion |
| S1-R3 | P-S1-08 | proof/stage1/P-S1-08.sh | FAIL (missing module) | FAIL (rejects broken guard) | FAIL (expects self-test pass)| Self-test error code flip, exit code 3 bypass |
| S1-R3 | P-S1-09 | proof/stage1/P-S1-09.sh | FAIL (missing module) | FAIL (accepts tampered oracle)| FAIL (checks halt code 3) | Manifest hash comparison flip |
| S1-R3 | P-S1-10 | proof/stage1/P-S1-10.sh | FAIL (missing module) | FAIL (bypasses scope parser) | FAIL (checks exact scope error)| Scope rule validation bypass |
| S1-R3 | P-S1-11 | proof/stage1/P-S1-11.sh | FAIL (missing module) | FAIL (accepts pass body) | FAIL (checks AST test count) | AST node visitor filter swap |
| S1-R3 | P-S1-12 | proof/stage1/P-S1-12.sh | FAIL (missing module) | FAIL (leaves unredacted line) | FAIL (checks redacted line) | Secret scrubbing substitution removal |
| S1-R4 | P-S1-13 | proof/stage1/P-S1-13.sh | FAIL (missing module) | FAIL (leaves staged files) | FAIL (checks staged cleanup) | Finally block cleanup removal |
| S1-R5 | P-S1-14 | proof/stage1/P-S1-14.sh | FAIL (missing module) | FAIL (permits dirty env) | FAIL (checks env allowlist) | Env dictionary filtering removal |
| S1-R7 | P-S1-15 | proof/stage1/P-S1-15.sh | FAIL (missing module) | FAIL (accepts extra keys) | FAIL (validates 4 keys) | Prior attempt schema key validation |
| S1-R9 | P-S1-16 | proof/stage1/P-S1-16.sh | FAIL (missing module) | FAIL (launches session) | FAIL (verifies staged inbox) | Argument parsing flag inversion |
| S1-R10| P-S1-17 | proof/stage1/P-S1-17.sh | FAIL (missing module) | FAIL (ignores tripwires) | FAIL (checks transcript line) | Tripwire regex matching bypass |
| S1-R12| P-S1-18 | proof/stage1/P-S1-18.sh | FAIL (missing module) | FAIL (returns wrong action) | FAIL (checks 10 state rules) | Priority ordering, state dictionary lookup |
| S1-R8 | P-S1-19 | proof/stage1/P-S1-19.sh | FAIL (missing skill) | FAIL (accepts forbidden term)| FAIL (checks required items) | Skill grep checklist pattern removal |
| S1-R9 | P-S1-20 | proof/stage1/P-S1-20.sh | FAIL (missing module) | FAIL (ignores exit 7) | FAIL (verifies exit 7 in ev) | Wrapper execution exit code propagation |
| S1-R14| P-S1-21 | proof/stage1/P-S1-21.sh | FAIL (missing module) | FAIL (ignores timeout 124) | FAIL (verifies hard_cap=True)| Timeout return code constant check |
| S1-R14| P-S1-22 | proof/stage1/P-S1-22.sh | FAIL (missing module) | FAIL (ignores missing .exit) | FAIL (verifies lost=True) | File existence grace period check |
| S1-R15| P-S1-23 | proof/stage1/P-S1-23.sh | FAIL (missing module) | FAIL (skips archive) | FAIL (checks copied SHA-256) | File copy and hash comparison bypass |
| S1-R15| P-S1-24 | proof/stage1/P-S1-24.sh | FAIL (missing module) | FAIL (early log unlink) | FAIL (checks unlinked log) | Unlink ordering after verification write |
| S1-R9 | P-S1-25 | proof/stage1/P-S1-25.sh | FAIL (missing module) | FAIL (accepts duplicate sess)| FAIL (checks exit code 3) | Active session collision detection |
| S1-R9 | P-S1-26 | proof/stage1/P-S1-26.sh | FAIL (missing module) | FAIL (accepts 100k+ bytes) | FAIL (checks size ceiling) | Prompt character length boundary check |
| S1-R10| P-S1-27 | proof/stage1/P-S1-27.sh | FAIL (missing module) | FAIL (ignores env override) | FAIL (checks custom home) | Config path resolution fallback |
| S1-R11| P-S1-28 | proof/stage1/P-S1-28.sh | FAIL (missing module) | FAIL (wrong CLI code) | FAIL (checks CLI codes) | Subcommand exit code mapping |
| S1-R6 | P-S1-29 | proof/stage1/P-S1-29.sh | FAIL (missing module) | FAIL (accepts bad regression)| FAIL (checks O2 test name) | JUnit XML parser node extraction |

## 3. Ambiguity Register

| ID | Ambiguity / Contradiction | Options Considered | Selected Reading | Justification |
|---|---|---|---|---|
| S1A-1 | Golden cases mapping across base.json and s1.json. | (a) Overwrite base.json cases in s1.json.<br>(b) Define only new Stage 1 cases in s1.json and load merged expected dict. | (b) Define only Stage 1 cases in s1.json. | Preserves PB-2 immutability of base.json and complies with load_expected() uniqueness checks. |
| S1A-2 | Outbox closure path. | (a) Use legacy path.<br>(b) Use layout.outbox(tag, "implementer") / "closure.json". | (b) Use layout.outbox(). | Complies with layout transition (L-3, D-30..D-40) and D-42. |
| S1A-3 | Dynamic watchdog timeout parameter. | (a) Hardcode 2700.<br>(b) Default timeout_s to None in implementation, derive from hard_cap. | (b) timeout_s: int | None = None. | Fully aligns runtime watchdog with sprint.toml hard_cap configuration. |
| S1A-4 | Verification record on halt. | (a) Set exit_code = 3 in record.<br>(b) Set exit_code = null in record, exit process with code 3. | (b) exit_code = null in record. | Complies with normative schema schemas/verification.json and D-24. |
| S1A-5 | O2 failing step formatting. | (a) O2:{classname}::{name}<br>(b) O2:{file_stem}::{name} | Normalize classname: if it matches test filename stem, format as O2:test_users::test_name. | Matches golden fixture expected.d/base.json assertions. |
| S1A-6 | attempt.json location. | (a) Write to worktree root.<br>(b) Write to mailboxes/implementer/inbox/attempt.json and symlink/copy. | (b) Write to implementer inbox. | Preserves clean git status of candidate worktree at base_sha. |
| S1A-7 | Worktree argument resolution when None. | (a) Fail with ValueError.<br>(b) Resolve to latest implementer workspace layout.workspace(f"implementer-{attempt_seq:03d}", tag). | (b) Resolve to active attempt workspace. | Enables direct CLI invocation without redundant path flags. |
| S1A-8 | Failing line sanitization. | (a) Drop line.<br>(b) Strip ANSI, replace control characters < 0x20 with space, truncate to 300 code points. | (b) O-8 sanitization algorithm. | Protects downstream JSON parsing and display terminals from corruption. |
| S1A-9 | G4 test counting for parameterized tests. | (a) Count runtime expansions.<br>(b) Count static AST FunctionDef / AsyncFunctionDef. | (b) Count AST function definitions. | Offline static analysis cannot safely execute untrusted test decorators. |
| S1A-10| G2 blocked reason verification timing. | (a) Verify preconditions before running tests.<br>(b) Verify notes/backlog before, verify blocking failure post-O2. | (b) Split pre-check and post-check. | Ensures candidate actually fails at the claimed blocking step. |
| S1A-11| Behavior when closure.json contains extra unparsed fields. | (a) Ignore extra fields.<br>(b) Fail G2 schema validation. | (b) Fail G2 schema validation. | schemas/closure.json enforces additionalProperties: false. |
| S1A-12| Handling SIGKILL or immediate container exit in wait_session. | (a) Hang indefinitely.<br>(b) Detect tmux session disappearance, wait 5s grace for .exit, then mark lost=True. | (b) 5s grace then lost=True. | Eliminates zombie waits in unattended CI/VPS environments. |
| S1A-13| Tripwire false positive handling on governance files. | (a) Scan whole tree.<br>(b) Exclude designated governance inputs (SKILL.md, contract, prior_attempt). | (b) Allowlist designated inputs. | Prevents self-tripping on required instruction text. |
| S1A-14| G6 AST scanning vs. regex scanning. | (a) Regex only.<br>(b) Dual AST call visitor + regex fallback for added lines. | (b) Dual AST + regex. | Kills string obfuscation and multi-line invocation evasion mutants. |
| S1A-15| Implementer commit message format verification. | (a) Ignore commits.<br>(b) Validate commit-msg hook passes on wip/{seq:03d}. | (b) Pre-commit and commit-msg enforcement. | Enforces strict repository governance across all agent worktrees. |

## 4. Proposed Decisions

### O-4: G4 Test Count for Non-Python Targets
Stage 1 enforces AST-based test preservation for Python repositories. For non-Python target repositories, G4 falls back to counting occurrences of framework-specific test declaration patterns defined in sprint.toml (e.g. test_pattern = "^\\s*it\\("). Golden repo is Python; AST is normative.

### O-5: Initial config/forbidden.toml Ruleset
Applied by G6 to added lines on non-FROZEN paths:
- F001: Dynamic code execution (eval, exec).
- F002: Shell escape via os (system, popen, exec*).
- F003: Subprocess spawning (subprocess.run, Popen) without path allowlist.
- F004: Network socket and HTTP libraries (socket, requests, httpx, urllib, aiohttp).
- F005: Unsafe serialization (pickle, marshal).
- F006: Direct access to oracle paths (/oracle, probe.sh, /proofs/, /mutants/).
- F007: Repository safety bypass (git push, --no-verify, core.hooksPath).
- F008: Privilege escalation (sudo, chmod 777).

### O-6: Initial config/secrets.toml Ruleset
Applied by G5 to diff additions and closure notes:
- S001: AWS Access Keys ((?:AKIA|ASIA)[0-9A-Z]{16}).
- S002: GitHub Tokens (gh[pousr]_[A-Za-z0-9]{36,}).
- S003: OpenAI API Keys (sk-[A-Za-z0-9]{20,}).
- S004: Slack Tokens (xox[baprs]-[A-Za-z0-9-]{10,}).
- S005: Private Keys (-----BEGIN [A-Z ]*PRIVATE KEY-----).
- S006: Google API Keys (AIza[0-9A-Za-z_-]{35}).
- S007: Generic Secret Assignments ((?i)(password|secret|api_key|token)\s*[:=]\s*['"][^'"]{16,}['"]).

### O-17: Process Exit Code 3 vs. verification.exit_code = null on Halt
Confirmed and adopted: When a verification halt occurs (integrity violation or guard self-test failure), verification.exit_code is null in JSON. The CLI processes (actl verify-impl, actl selftest, actl dispatch-impl) exit with process status code 3.
