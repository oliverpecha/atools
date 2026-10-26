# spec-S2.md - Stage 2 (Paste Bridge and Promotion) Specification and Proof Map
Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
Date: 2026-10-26. Inputs: Design rev. 2, core plan, addendum, src/actl/INTERFACES.md (frozen, PB-2/PB-4), rulings D-1..D-48.

## 0. Conventions
- MUST/SHOULD/MAY are RFC 2119. Clause IDs S2-Rk.n are stable anchors used by proofs and tests.
- Proof convention: exit 0 on pass, exit 1 on fail with a line starting "FAIL: <req_id>: <reason>". Exit 4 is reserved for environment problems (missing external tool).
- Exit codes of the product CLI (S0-R10, D-8): 0 ok, 1 red, 2 usage/schema/parse/envelope error, 3 halt (state integrity error), 4 environment.
- Envelope marker double-quoting is mandatory in both emitters and parsers per ruling D-44.
- Outbox staging uses mailboxes/.{role}-staging-{pid} with mode 0o770 per ruling D-46.
- Role promotion returns all 7 keys per ruling D-43; challenger draft promotion records staged_to as the promoted oracle-draft path string with no inbox staging.
- All proofs read the repository under test from ACTL_REPO (default: repository root) so the same proofs run against stand-ins.
- Golden facts: base_sha = 01d880bc3176cdd8f31d72e67bb3eba54d634378, tag 2026-10-16_public-profiles, state.seq = 5.

## 1. Requirements (Testable Expansion)

### S2-R1 Turn Ledger and Courier Drawers
- S2-R1.1 Each interaction with an external persona (architect, challenger, curator) constitutes a turn recorded under layout.turns_dir(tag) = sprints/{repo}/{tag}/runs/turns/{role}-{n}/ where n is a 1-based strictly monotonic integer per role.
- S2-R1.2 allocate_turn(layout, tag, role) -> tuple[int, Path] executes under seq.state_lock(layout, tag). It inspects existing turn directories under layout.turns_dir(tag), computes next_n = 1 + max((existing_n for role-{existing_n}), default=0), creates sprints/{repo}/{tag}/runs/turns/{role}-{next_n}/ with mode 0o755 via os.mkdir, and returns (next_n, turn_dir). Valid roles: "architect", "challenger", "curator".
- S2-R1.3 latest_turn(layout, tag, role) -> tuple[int, Path] | None inspects existing turn directories and returns (n, turn_dir) for the highest n of that role, or None if no turn exists.
- S2-R1.4 resolve_turn(layout, tag, turn_id) -> Path validates that turn_id matches ^(architect|challenger|curator)-[1-9][0-9]*$, verifies existence under layout.turns_dir(tag), and returns the Path. Missing directory raises FileNotFoundError; malformed ID raises ValueError.
- S2-R1.5 When ACTL_COURIER_DIR is set in os.environ, file deliveries copy payloads to $ACTL_COURIER_DIR/{stamp}__{repo}__{tag}__{role}-{n}__{purpose}.txt where stamp is UTC YYYYMMDDTHHMMSSZ.
- S2-R1.6 Turn artifacts written by actl: bundle.txt, bundle.json, response.txt, amend-{k}.txt, unpack.json, and repair.txt (when unpack fails).

### S2-R2 actl bundle <purpose>
- S2-R2.1 CLI synopsis: actl bundle <purpose> --sprint <TAG> [--out <FILE|->] [--osc52] [--clip] [--include <PATH>...] [--max-chars <N>] [--model <NAME>] [--json].
- S2-R2.2 Valid purpose values: "architect-intake" (role architect), "challenger" (role challenger), "architect-review" (role architect). "curator" raises UsageError (exit code 2) in Stage 2 (reserved for Stage 5).
- S2-R2.3 allocate_turn is called to create the turn directory. Payload assembly order:
  1. Persona role prompt from prompts/{role}.md (or prompts/architect_review.md for architect-review).
  2. Sprint metadata header: sprint tag, target repository name, base_sha, active contract/spec IDs.
  3. Context sections:
     - architect-intake: target repository file tree listing (git ls-files with byte sizes) and any explicitly included files via --include.
     - challenger: active spec file (spec-{seq}.md), active solution key (solution_key-{seq}.patch) if solution_key_exposure == "full" in sprint.toml, and target repository tree.
     - architect-review: active spec, solution key, and the entire active oracle draft directory (oracle-draft-{seq}/).
  4. Envelope grammar instructions and closing sentinel requirement appended from prompts/_output_contract.md.
- S2-R2.4 bundle_sha256 calculation: computed as lowercase 64-hex SHA-256 of all UTF-8 bytes preceding the final closing sentinel line. The final line appended to bundle.txt is exactly:
  <<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>\n
- S2-R2.5 bundle.json schema conformance: written to turn_dir/bundle.json with keys turn_id (str), role (str), purpose (str), base_sha (str), solution_key_sha256 (str | null), files (list of {path, sha256, bytes}), bundle_sha256 (str, 64-hex), created (ISO-8601 UTC), model_hint (str).
- S2-R2.6 Character limits: --max-chars defaults to 200000. If assembled context exceeds limit, repository tree entries are prioritized by proximity to scope or truncated with an explicit warning table; prompt and contract are never truncated.
- S2-R2.7 Mutual exclusion: passing both --out - (stdout) and --json raises UsageError (exit code 2).
- S2-R2.8 Clipboard helpers: --osc52 emits standard OSC 52 escape sequence (\x1b]52;c;{base64}\x07) to stderr. --clip attempts copying via xclip, wl-copy, or pbcopy if available; absence of clipboard binaries emits a warning without failing.
- S2-R2.9 CLI --json emits: {"turn_id": str, "role": str, "purpose": str, "turn_dir": str, "bundle_path": str, "bundle_sha256": str, "sentinel": str, "chars": int, "files": list, "model_hint": str}.

### S2-R3 Envelope Grammar (Normative)
- S2-R3.1 Top-level response structure: zero or more envelope blocks (FILE or PATCH) followed by exactly one closing sentinel line:
  <<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>
  Double quotes around the 8-hex bundle prefix are mandatory (D-44).
- S2-R3.2 FILE block grammar:
  <<<FILE path="<relpath>" [mode="exec"] [fence="<N>"]>>>\n
  <content>
  <<<END_FILE>>>
  fence="N" allows N in 3..9 (default 3). If fence="N", opening is "<" * N + "FILE ... " + ">" * N and closing is "<" * N + "END_FILE" + ">" * N.
  mode="exec" marks the file executable (chmod 0o755).
- S2-R3.3 PATCH block grammar:
  <<<PATCH path="<relpath>" [new="true"] [fence="<N>"]>>>\n
  <hunk_1>
  ...
  <<<END_PATCH>>>
  Inside a PATCH block with fence N, hunk delimiters scale to length N+4:
  Opening search: "<" * (N+4) + " SEARCH\n"
  Separator:      "=" * (N+4) + "\n"
  Closing replace: ">" * (N+4) + " REPLACE\n"
  Default delimiters (N=3):
  <<<<<<< SEARCH\n
  <search_content>
  =======\n
  <replace_content>
  >>>>>>> REPLACE\n
- S2-R3.4 Path safety rules: path attribute must be a relative POSIX path. Paths with leading /, \, NUL, .., or matching .git (case-insensitive) are rejected with error code E_PATH.
- S2-R3.5 Allowed paths per purpose:
  - architect-intake: sprint.toml, spec-draft.md (optional if spec was imported), solution_key.patch.
  - challenger: oracle-draft/scope.txt, oracle-draft/coverage.md, oracle-draft/probe.sh, oracle-draft/proofs/*.sh, oracle-draft/mutants/*.patch, oracle-draft/oracle-critique.md.
  - architect-review: oracle-decision.json, and optionally modified sprint.toml or oracle-draft/* files.
  Violations raise E_SCOPE.

### S2-R3 Worked Examples (Normative: 6 Good, 6 Bad)

#### Example 1 (Good: Architect Intake - FILE + PATCH)
<<<FILE path="sprint.toml">>>
live_run = "none"
approval_live_run = "architect"
solution_key_exposure = "full"
min_attempts_before_block = 2
max_epochs = 3
repo_test_cmd = "python3 -m pytest test -q -rf"

[max_attempts]
oracle = 3
implementer = 2
live = 2
curator = 2

[hard_cap.implementer]
wall_clock = "45m"
turns = 60
<<<END_FILE>>>
<<<PATCH path="solution_key.patch" new="true">>>
<<<<<<< SEARCH
=======
diff --git a/api/profile.py b/api/profile.py
new file mode 100644
--- /dev/null
+++ b/api/profile.py
@@ -0,0 +1,5 @@
+def render():
+    return 200
>>>>>>> REPLACE
<<<END_PATCH>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 2 (Good: Challenger Oracle Draft with Executable Probe)
<<<FILE path="oracle-draft/scope.txt">>>
FROZEN: test/**
ALLOW: api/profile.py
<<<END_FILE>>>
<<<FILE path="oracle-draft/coverage.md">>>
R1 -> probe.sh
<<<END_FILE>>>
<<<FILE path="oracle-draft/probe.sh" mode="exec">>>
#!/usr/bin/env bash
set -euo pipefail
python3 -m api.cli profile 1
<<<END_FILE>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 3 (Good: Architect Review Decision)
<<<FILE path="oracle-decision.json">>>
{
  "decision": "lock_oracle",
  "feedback": "All requirements verified."
}
<<<END_FILE>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 4 (Good: Scaled Fence Escaping Inner Markers)
<<<<<FILE path="docs/guide.md" fence="5">>>>>
Here is an inner marker:
<<<FILE path="inner.txt">>>
data
<<<END_FILE>>>
<<<<<END_FILE>>>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 5 (Good: Multi-Hunk Patch)
<<<PATCH path="api/users.py">>>
<<<<<<< SEARCH
def old_one():
    pass
=======
def new_one():
    return True
>>>>>>> REPLACE
<<<<<<< SEARCH
def old_two():
    pass
=======
def new_two():
    return True
>>>>>>> REPLACE
<<<END_PATCH>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 6 (Good: Scaled Hunk Delimiters on Fence 4)
<<<<PATCH path="api/service.py" fence="4">>>>
<<<<<<<< SEARCH
SERVICE_PORT = 8080
========
SERVICE_PORT = 9090
>>>>>>>> REPLACE
<<<<END_PATCH>>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 7 (Bad: Sentinel Without Mandatory Double Quotes -> E_SYNTAX_MARKER)
<<<FILE path="sprint.toml">>>
live_run = "none"
<<<END_FILE>>>
<<<END_RESPONSE bundle=a1b2c3d4>>>

#### Example 8 (Bad: Wrong Bundle Prefix -> E_BUNDLE_MISMATCH)
<<<FILE path="sprint.toml">>>
live_run = "none"
<<<END_FILE>>>
<<<END_RESPONSE bundle="deadbeef">>>

#### Example 9 (Bad: Truncated File Block -> E_TRUNCATED)
<<<FILE path="sprint.toml">>>
live_run = "none"

#### Example 10 (Bad: Path Traversal -> E_PATH)
<<<FILE path="../escape.txt">>>
malicious
<<<END_FILE>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 11 (Bad: Duplicate File Block -> E_DUPLICATE)
<<<FILE path="sprint.toml">>>
live_run = "none"
<<<END_FILE>>>
<<<FILE path="sprint.toml">>>
live_run = "required"
<<<END_FILE>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

#### Example 12 (Bad: Search Hunk Not Matching -> E_SEARCH_NOMATCH)
<<<PATCH path="api/users.py">>>
<<<<<<< SEARCH
this_text_does_not_exist_in_the_file()
=======
new_content()
>>>>>>> REPLACE
<<<END_PATCH>>>
<<<END_RESPONSE bundle="a1b2c3d4">>>

### S2-R4 actl unpack <purpose>
- S2-R4.1 CLI synopsis: actl unpack <purpose> --sprint <TAG> [-f <FILE> | --paste | --drawer <PATH>] [--turn <TURN_ID>] [--amend] [--json].
- S2-R4.2 Turn selection: resolved via --turn if provided, else resolves to latest_turn(layout, tag, role) matching the given purpose. If no matching turn exists, raises UsageError (exit code 2).
- S2-R4.3 Input channels: -f reads from path; --paste reads from stdin until line matching ^<<<END_RESPONSE bundle="[0-9a-f]{8}">>>\s*$; --drawer reads from named file in ACTL_COURIER_DIR; default reads stdin to EOF.
- S2-R4.4 Raw input retention: first unpack writes raw bytes to turn_dir/response.txt. If --amend is passed, raw bytes are written to turn_dir/amend-{k}.txt where k is the 1-based amend index.
- S2-R4.5 Step 3 Normalization Rules:
  1. Strip leading UTF-8 Byte Order Mark (\xef\xbb\xbf) if present.
  2. Normalize CRLF (\r\n) and CR (\r) line endings to LF (\n).
  3. Strip single outer Markdown code block wrapping (e.g. ```markdown ... ``` or ``` ... ```) if it encloses all envelope blocks.
  4. Strip horizontal trailing whitespace (spaces and tabs) on sentinel and envelope delimiter lines only; content lines preserve whitespace.
- S2-R4.6 Parsing and Patch Synthesis:
  - Envelope blocks are parsed per S2-R3.
  - PATCH blocks are synthesized into complete files via hermetic patch synthesis (S2-R5).
  - Post-parse validation is performed (S2-R6).
- S2-R4.7 Atomic Outbox Swap (D-46):
  - On validation success, files are written to staging directory sprints/{repo}/{tag}/mailboxes/.{role}-staging-{pid}/ with mode 0o770.
  - If outbox already exists, it is moved to sprints/{repo}/{tag}/mailboxes/.{role}-outbox.prev, the staging directory is renamed to mailboxes/{role}/outbox, and .prev is unlinked.
  - File modes inside outbox: 0o755 for executable scripts (probe.sh, proofs/*.sh), 0o644 for regular files.
- S2-R4.8 unpack.json schema conformance: written to turn_dir/unpack.json containing turn_id, role, purpose, ok (bool), bundle_sha256, response_sha256, amended (bool), outputs (list of {path, sha256, bytes, executable}), errors (list of {code, path, message, detail}), warnings (list of str), repair_path (str | null).
- S2-R4.9 Error vocabulary (Addendum section 7.6): E_TRUNCATED, E_BUNDLE_MISMATCH, E_PATH, E_DUPLICATE, E_SYNTAX_MARKER, E_SEARCH_NOMATCH, E_SEARCH_MULTI, E_PATCH_APPLY, E_JSON, E_TOML, E_SCHEMA, E_SHELL_SYNTAX, E_SCOPE, E_COVERAGE, E_MISSING_REQUIRED, E_SIZE, E_EXISTS.

### S2-R5 Hermetic Patch Synthesis
- S2-R5.1 Target baseline resolution: patches for architect-intake and architect-review are synthesized against a clean temporary checkout of layout.target_repo at base_sha. Patches for challenger are synthesized against base_sha with active solution_key applied.
- S2-R5.2 Search matching:
  - Exactly 1 match: SEARCH block content replaced with REPLACE block content.
  - 0 matches: raises E_SEARCH_NOMATCH with line number and nearest difflib.get_close_matches candidate.
  - >=2 matches: raises E_SEARCH_MULTI with all matched line numbers.
- S2-R5.3 New file handling: new="true" requires target file does not exist (raises E_EXISTS if present) and SEARCH block is empty; REPLACE block content forms the new file.
- S2-R5.4 Multi-block ordering: multiple PATCH blocks targeting the same path are applied sequentially in the order they appear in the response.
- S2-R5.5 Verification: all synthesized files are checked with git diff and git apply --check in an isolated scratch git workspace to ensure valid unified diff syntax.

### S2-R6 Post-Parse Validation
- S2-R6.1 Schema validation:
  - sprint.toml / sprint-proposal.toml validated against schemas/sprint-proposal.json.
  - oracle-decision.json validated against schemas/oracle-decision.json.
  Violations raise E_SCHEMA.
- S2-R6.2 coverage.md grammar and bijection:
  - Grammar: matches ^(R[0-9]+|(?:mutants/)?[A-Za-z0-9_.-]+\.patch)\s*(?:->|->|:)\s*(.+)\Z.
  - Bijection: every requirement R<n> in spec-001.md must be mapped to at least one proof; every mutant patch in oracle-draft/mutants/ must be mapped; every proof referenced in coverage.md must exist in oracle-draft/proofs/ or be probe.sh. Unmapped items raise E_COVERAGE.
- S2-R6.3 Shell script verification:
  - All .sh files under oracle-draft/proofs/ and oracle-draft/probe.sh are validated with bash -n. Syntax errors raise E_SHELL_SYNTAX.
  - Missing set -euo pipefail or #!/usr/bin/env bash emits a warning in unpack.json.
  - Valid scripts are marked executable=True and chmod 0o755.
- S2-R6.4 Scope file verification:
  - oracle-draft/scope.txt is parsed via actl.scope.parse and validated via actl.scope.validate. Syntax or semantic errors raise E_SCOPE.
- S2-R6.5 File constraints:
  - Maximum size per output file is 1 MiB (1,048,576 bytes); larger files raise E_SIZE.
  - Required files per purpose must be present; missing files raise E_MISSING_REQUIRED.

### S2-R7 Repair Prompts
- S2-R7.1 When unpack.json has ok == False, actl unpack writes turn_dir/repair.txt.
- S2-R7.2 Content of repair.txt:
  - Header naming turn_id, role, purpose, and failure status.
  - Itemized error list: error code, path, 1-line reason.
  - For E_SEARCH_NOMATCH: displays the failed SEARCH block, line number, and nearest candidate found in the baseline file.
  - Repair instruction directing the model to output only the corrected blocks or delta patches.
  - Mandatory closing sentinel reminder: <<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>.
- S2-R7.3 Zero oracle leak guarantee: repair.txt must not contain any text from oracle proofs, mutants, or solutions that was not already present in the incoming bundle or the model's own response.

### S2-R8 actl replay <TURN_ID>
- S2-R8.1 CLI synopsis: actl replay <TURN_ID> [--sprint <TAG>] [--json].
- S2-R8.2 Turn resolution: if --sprint is omitted and multiple sprints exist, raises UsageError; if exactly one sprint exists under layout.root, auto-selects that sprint (A-3).
- S2-R8.3 Execution: creates an isolated scratch directory, replays response.txt (and any amend-*.txt in sequence) through Step 3 normalization, parser, patch synthesis, and validation.
- S2-R8.4 Comparison: compares resulting outputs, output hashes, error codes, and ok status against the stored turn_dir/unpack.json.
- S2-R8.5 Exit codes: 0 if replayed execution matches stored unpack.json byte-for-byte; 1 if diffs are detected (printing diff details); 2 on usage error.
- S2-R8.6 CLI --json emits: {"turn_id": str, "match": bool, "stored_ok": bool, "replayed_ok": bool, "diffs": list[str]}.

### S2-R9 actl promote <role>
- S2-R9.1 CLI synopsis: actl promote <role> --sprint <TAG> [--json].
- S2-R9.2 Preconditions: valid role in ("architect", "challenger"); layout.outbox(tag, role) exists and contains valid draft outputs from a successful unpack.
- S2-R9.3 Transactional execution under seq.state_lock(layout, tag):
  - Deduplication: computes content digest (file_sha256 for files, manifest_sha256 for directories) and parent spec ID. If an artifact with identical (kind, parent, sha256) already exists in layout.sprint_dir(tag), that seq is reused. Otherwise, a new seq is reserved via seq.reserve(layout, tag, kind).
  - Artifact promotion: copies files to layout.sprint_dir(tag) as immutable artifacts (spec-{seq:03d}.md, solution_key-{seq:03d}.patch, oracle-draft-{seq:03d}/) and writes companion sidecars (*.meta.json) conforming to schemas/meta.json.
  - State update: updates state.json via seq.update_state with new active_spec, active_solution_key, or active_oracle_draft.
- S2-R9.4 Staging and Return Keys (D-43):
  - Returns exactly 7 keys: {"sprint_tag": str, "role": str, "promoted": list[dict], "staged_to": str, "active_spec": str | None, "active_solution_key": str | None, "active_oracle_draft": str | None}.
  - If role == "architect": copies promoted spec-{seq}.md and solution_key-{seq}.patch to layout.inbox(tag, "challenger") with read-only modes (0o440 regular, 0o550 executable). staged_to is str(layout.inbox(tag, "challenger")).
  - If role == "challenger": no actl role or inbox exists; staged_to is the promoted records path string str(layout.sprint_dir(tag) / f"oracle-draft-{seq:03d}").

### S2-R10 actl next Phase 1-2 Rules
- S2-R10.1 Module actl.next_rules.phase12 defines PRIORITY = 10 (evaluated before Phase 3 rules at PRIORITY = 30).
- S2-R10.2 Decision precedence:
  1. Intake turn needed (spec not active): action = "bundle_architect_intake", command = "actl bundle architect-intake --sprint <TAG>".
  2. Intake response received but not unpacked: action = "unpack_architect_intake", command = "actl unpack architect-intake --sprint <TAG>".
  3. Intake unpacked ok but not promoted: action = "promote_architect", command = "actl promote architect --sprint <TAG>".
  4. Challenger turn needed (oracle draft not active): action = "bundle_challenger", command = "actl bundle challenger --sprint <TAG>".
  5. Challenger response received but not unpacked: action = "unpack_challenger", command = "actl unpack challenger --sprint <TAG>".
  6. Challenger unpacked ok but not promoted: action = "promote_challenger", command = "actl promote challenger --sprint <TAG>".
  7. Architect review turn needed: action = "bundle_architect_review", command = "actl bundle architect-review --sprint <TAG>".
  8. Architect review response received but not unpacked: action = "unpack_architect_review", command = "actl unpack architect-review --sprint <TAG>".
  9. Review decision lock_oracle ready: action = "freeze_contract", command = "actl freeze-contract --sprint <TAG>" (Stage 3).
  10. Unpack failed (repair needed): action = "repair", command = "actl bundle <purpose> --sprint <TAG> --repair".

### S2-R11 Role Prompt Files
- S2-R11.1 System prompts live in prompts/: architect.md, challenger.md, architect_review.md, and shared prompts/_output_contract.md.
- S2-R11.2 Authority statements:
  - architect.md: declares sole authority over specification, scope boundaries, and review approval.
  - challenger.md: declares authority over test generation, mutant design, and critique; forbids modifying spec.
  - architect_review.md: declares authority over accepting or rejecting challenger oracle drafts.
- S2-R11.3 Output contract: prompts/_output_contract.md is the single authoritative source for envelope grammar and closing sentinel instructions, appended to all bundles.

### S2-R12 Bridge Safety
- S2-R12.1 No model response content is executed during bundle, unpack, replay, or promote operations. bash -n syntax checks run with no execution.
- S2-R12.2 Path containment: all extracted files must resolve strictly within the target sandbox/mailbox directory. Any path escaping the directory raises E_PATH.

### S2-R13 Stage 2 Additions Gate (D-41 / P-S2-17)
- S2-R13.1 Per-stage additions proof P-S2-17.sh checks that on wip/s2-bridge against ACTL_FORK_POINT:
  - Added files are restricted to Stage 2 implementation modules, commands, prompts, tests, and proofs.
  - PB-2 frozen paths (INTERFACES.md, proof/stage0/, fixtures/golden/expected.d/base.json, tools/) have zero diff.

## 2. Traceability and Three-Stand-In Vacuity Matrix

| Req ID | Proof ID | Proof Script / Test File | Empty Module (a) | Always-Succeed Stub (b) | Always-Fail Stub (c) | Mutation Classes Killed |
|---|---|---|---|---|---|---|
| S2-R1 | P-S2-01 | test_p01_turns.py / P-S2-01.sh | FAIL (ImportError) | FAIL (missing dir / wrong seq) | FAIL (exits 1) | return 0, sequence off-by-one, missing lock |
| S2-R2 | P-S2-02 | test_p02_bundle.py / P-S2-02.sh | FAIL (ImportError) | FAIL (empty bundle / bad sentinel) | FAIL (exits 1) | sentinel strip off, header omitted, limit logic flipped |
| S2-R3 | P-S2-03 | test_p03_envelope.py / P-S2-03.sh | FAIL (ImportError) | FAIL (accepts unquoted sentinel) | FAIL (exits 1) | quote check removed, fence math N+4 to N |
| S2-R3 | P-S2-04 | test_p04_truncation.py / P-S2-04.sh | FAIL (ImportError) | FAIL (accepts truncated) | FAIL (exits 1) | truncated check inverted, wrong error code |
| S2-R4 | P-S2-05 | test_p05_unpack.py / P-S2-05.sh | FAIL (ImportError) | FAIL (raw txt missing / bad json) | FAIL (exits 1) | BOM strip omitted, CRLF unhandled, amend index off |
| S2-R4 | P-S2-06 | test_p06_atomic_swap.py / P-S2-06.sh | FAIL (ImportError) | FAIL (mode != 0o770 / no atomic swap) | FAIL (exits 1) | chmod omitted, rename order inverted |
| S2-R5 | P-S2-07 | test_p07_patchsynth.py / P-S2-07.sh | FAIL (ImportError) | FAIL (matches 0 or multiple hunks) | FAIL (exits 1) | count check flipped, difflib candidate omitted |
| S2-R5 | P-S2-08 | test_p08_multihunk.py / P-S2-08.sh | FAIL (ImportError) | FAIL (new file exists / order wrong) | FAIL (exits 1) | new file flag ignored, hunk order inverted |
| S2-R6 | P-S2-09 | test_p09_postparse.py / P-S2-09.sh | FAIL (ImportError) | FAIL (accepts invalid schema/scope) | FAIL (exits 1) | schema call skipped, scope validate skipped |
| S2-R6 | P-S2-10 | test_p10_shell_syntax.py / P-S2-10.sh | FAIL (ImportError) | FAIL (accepts invalid bash syntax) | FAIL (exits 1) | bash -n skipped, chmod 0o755 omitted |
| S2-R6 | P-S2-11 | test_p11_coverage.py / P-S2-11.sh | FAIL (ImportError) | FAIL (accepts unmapped requirement) | FAIL (exits 1) | bijection check omitted, regex weakened |
| S2-R7 | P-S2-12 | test_p12_repair.py / P-S2-12.sh | FAIL (ImportError) | FAIL (leaks oracle text / bad format) | FAIL (exits 1) | leak check skipped, candidate line number omitted |
| S2-R8 | P-S2-13 | test_p13_replay.py / P-S2-13.sh | FAIL (ImportError) | FAIL (reports match on diff) | FAIL (exits 1) | comparison check inverted, exit code flipped |
| S2-R9 | P-S2-14 | test_p14_promote.py / P-S2-14.sh | FAIL (ImportError) | FAIL (staged_to wrong / 5 keys) | FAIL (exits 1) | 7 keys not returned, dedup logic inverted |
| S2-R10 | P-S2-15 | test_p15_next_rules.py / P-S2-15.sh | FAIL (ImportError) | FAIL (wrong action / wrong precedence)| FAIL (exits 1) | priority flipped, rule order changed |
| S2-R11 | P-S2-16 | test_p16_prompts.py / P-S2-16.sh | FAIL (FileNotFound) | FAIL (missing contract append) | FAIL (exits 1) | missing persona statement, contract not included |
| S2-R13 | P-S2-17 | P-S2-17.sh | FAIL (script missing)| FAIL (accepts modified frozen files) | FAIL (exits 1) | allowlist bypassed, PB-2 check removed |

## 3. Ambiguity Register

| ID | Unclear Area | Possible Readings | Chosen Reading | Why |
|---|---|---|---|---|
| S2A-1 | Scale of inner hunk delimiters in fence="N". | (a) Fixed 7 characters. (b) Scaled to N+4 characters. | (b) Scaled to N+4 characters. | Addendum 7.5 and O-3 state inner delimiters must scale so hunks can contain arbitrary diff markers without collision. |
| S2A-2 | Normalization of outer Markdown code block fences. | (a) Leave untouched. (b) Strip single enclosing ``` block if it wraps entire response. | (b) Strip single enclosing ``` block. | Chat web UIs frequently wrap model outputs in markdown code blocks; stripping outermost fence prevents parse failure. |
| S2A-3 | promote_role return dictionary key count. | (a) 5 keys (INTERFACES 1.11). (b) 7 keys (INTERFACES 2 CLI synopsis and D-43). | (b) 7 keys. | Ruling D-43 resolves this in favor of 7 keys (including active_solution_key and active_oracle_draft). |
| S2A-4 | Challenger draft promotion staged_to destination. | (a) In inbox/actl. (b) Records path of promoted oracle draft directory. | (b) Records path string. | Ruling D-43 explicitly establishes that no actl persona mailbox exists; challenger staged_to points to records. |
| S2A-5 | Optional vs mandatory quotes around sentinel bundle prefix. | (a) Optional quotes. (b) Mandatory double quotes. | (b) Mandatory double quotes. | Ruling D-44 mandates double quotes in both emitters and parsers to resolve grammar collision. |
| S2A-6 | Permissions of outbox staging directory. | (a) 0o755. (b) 0o770. | (b) 0o770. | Ruling D-46 mandates 0o770 on outbox staging so group permissions match outbox mailbox specification. |
| S2A-7 | Requirement tokens in coverage.md. | (a) Arbitrary text. (b) Exact R<n> IDs and mutant patch paths. | (b) Exact R<n> IDs and mutant patch paths. | Addendum 7.4 S2-R6 and golden fixtures establish bijection between spec requirements, mutants, and proofs. |
| S2A-8 | actl replay without --sprint flag. | (a) Require --sprint always. (b) Auto-select sole sprint under records/sprints. | (b) Auto-select sole sprint if only one exists. | Matches INTERFACES ambiguity A-3 to support shorthand actl replay <role>-<n>. |
| S2A-9 | SEARCH block mismatch diagnostic reporting. | (a) Return line count only. (b) Return line number and difflib candidate. | (b) Return line number and difflib candidate. | Enables repair prompt synthesis to provide actionable repair context without manual review. |
| S2A-10 | Detection of truncated responses. | (a) Any syntax error. (b) Unclosed envelope block or missing sentinel. | (b) Unclosed envelope block or missing sentinel. | Distinguishes truncation (E_TRUNCATED) from syntax errors (E_SYNTAX_MARKER). |
| S2A-11 | actl bundle --out - combined with --json. | (a) Output JSON containing stdout stream. (b) Raise UsageError (exit 2). | (b) Raise UsageError (exit 2). | Standard CLI convention: stdout payload and JSON metadata cannot share stdout. |
| S2A-12 | Deduplication tuple for spec vs solution key vs oracle draft. | (a) sha256 only. (b) (kind, parent, sha256). | (b) (kind, parent, sha256). | Ensures revisions tied to different parent specs receive distinct sequence numbers even if diff is empty. |
| S2A-13 | Handling of sprint.toml vs sprint-proposal.toml in review. | (a) Overwrite frozen sprint.toml. (b) Validate against sprint-proposal.json. | (b) Validate against sprint-proposal.json. | Prevents model from modifying immutable sprint parameters (base_sha, sprint_tag). |
| S2A-14 | Shell script shebang and fail-fast validation. | (a) Fatal error. (b) Warning in unpack.json. | (b) Warning in unpack.json. | Non-fatal: missing shebang is noted, while syntax error (bash -n) is fatal (E_SHELL_SYNTAX). |
| S2A-15 | Repair prompt text leakage boundaries. | (a) Include full oracle files. (b) Strictly zero oracle text outside model input. | (b) Strictly zero oracle text outside model input. | Crucial security invariant: repair prompt must never leak hidden test cases. |
| S2A-16 | Priority of phase12.py rules. | (a) Default 100. (b) PRIORITY = 10. | (b) PRIORITY = 10. | Phase 1-2 turn decisions must precede Phase 3 implementer dispatch rules (PRIORITY = 30). |

## 4. Proposed Decisions and Line-by-Line Rulings Verification

### O-3 (Envelope and Hunk Escape)
Normative fence="N" (N in 3..9, default 3) scales opening/closing envelope markers to length N and inner SEARCH/REPLACE delimiters to length N+4 (<<<<<<< SEARCH, =======, >>>>>>> REPLACE).

### O-9 (Step 3 Normalization Rules)
Formally defined as:
1. UTF-8 BOM removal.
2. CRLF and CR normalization to LF.
3. Outermost Markdown code block fence stripping.
4. Trailing horizontal whitespace stripping on delimiter and sentinel lines only.

### Rulings Verification Table
| Ruling | Text Summary | Compliance in spec-S2.md |
|---|---|---|
| D-34 | Use "verification" and "qualification", never "ev" or "qual" | Verified: used throughout requirements, schemas, and proof definitions. |
| D-41 | Author P-S1-02 and propose P-S2-17 additions proof | Verified: S2-R13 and P-S2-17 specified and mapped. |
| D-43 | promote_role returns 7 keys; challenger staged_to is records path | Verified: S2-R9 explicitly specifies 7 keys and records path string. |
| D-44 | Mandatory double quotes in sentinel emitter and parser | Verified: S2-R3.1, S2-R4.3, and all examples enforce double quotes. |
| D-46 | Outbox atomic swap via mailboxes/.{role}-staging-{pid} with chmod 0o770 | Verified: S2-R4.7 mandates staging dir name and 0o770 permission. |

## 5. Proposed Shared-File Changes
1. src/actl/INTERFACES.md section 1.11: Replace "tuple[int, Path] where n = 1 + max" with "tuple[int, Path] where n = 1 + max((existing_n for {role}-{existing_n} in turns_dir(tag)), default=0)".
2. src/actl/INTERFACES.md section 1.11: Replace promote_role return type comment "Dict {'sprint_tag': str, 'role': str, 'promoted': list[dict], 'staged_to': str, 'active_spec': str | None}" with "Dict {'sprint_tag': str, 'role': str, 'promoted': list[dict], 'staged_to': str, 'active_spec': str | None, 'active_solution_key': str | None, 'active_oracle_draft': str | None}".
3. src/actl/INTERFACES.md section 5: Replace "StepResult & ev" with "StepResult & verification" (D-34).
4. docs/plan/actl_Build_Plan-Stages0to2_addendum.md section 7.5: Replace optional quote regex with mandatory double quotes (D-44).

## 6. Red on Base Summary
Against base 4e16cc3:
- P-S2-01 fails RED: actl.turns cannot be imported.
- P-S2-02 fails RED: cmd_bundle cannot be imported.
- P-S2-03..P-S2-12 fail RED: cmd_unpack / patchsynth / repair modules missing.
- P-S2-13 fails RED: cmd_replay missing.
- P-S2-14 fails RED: cmd_promote / actl.promote missing.
- P-S2-15 fails RED: actl.next_rules.phase12 missing.
- P-S2-16 fails RED: prompts/*.md files missing.
- P-S2-17 fails RED: Stage 2 implementation files not present.
Every check fails cleanly with a FAIL line naming the missing requirement ID, with zero harness errors.
