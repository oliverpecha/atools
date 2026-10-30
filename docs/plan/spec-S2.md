
# spec-S2.md - Stage 2 (Paste Bridge and Promotion) Specification and Proof Map

Authored-by: Gemini Flash 3.8 (Google; accessed via the Gemini web interface; Owner-attested 2026-10-28), model family: Gemini
Date: 2026-10-27. Inputs: Design rev. 2, core plan, addendum, src/actl/INTERFACES.md (frozen, PB-2/PB-4), spec-S0.md, rulings D-1..D-48.

## 0. Conventions

* MUST/SHOULD/MAY are RFC 2119. Clause IDs `S2-Rk.n` are stable anchors used by proofs and tests.
* Proof convention: exit `0` on pass, exit `1` on fail with a line starting `FAIL: <req_id>: <reason>`. Exit `4` is reserved for environment problems (missing `git`, `bash`, `python3`, `pytest`).
* Exit codes of the product CLI (S0-R10, D-8): `0` ok, `1` red, `2` usage/schema/parse/envelope error, `3` halt (state integrity error), `4` environment.
* Envelope marker double-quoting is mandatory in both emitters and parsers per ruling D-44.
* Outbox staging uses `sprints/{repo}/{tag}/mailboxes/.{role}-staging-{pid}` with mode `0o770` per ruling D-46.
* Role promotion returns all 7 keys per ruling D-43; challenger draft promotion records `staged_to` as the promoted `oracle-draft` path string with no inbox staging.
* All proofs read the repository under test from `ACTL_REPO` (default: repository root) so the same proofs run against stand-ins.
* Golden facts: `base_sha = 01d880bc3176cdd8f31d72e67bb3eba54d634378`, tag `2026-10-16_public-profiles`, `state.seq = 5`.

## 1. Requirements (Testable Expansion)

### S2-R1 Turn Ledger and Courier Drawers

* S2-R1.1 Each interaction with an external persona (`architect`, `challenger`, `curator`) constitutes a turn recorded under `layout.turns_dir(tag) = sprints/{repo}/{tag}/runs/turns/{role}-{n}/` where `n` is a 1-based strictly monotonic integer per role.
* S2-R1.2 `allocate_turn(layout, tag, role) -> tuple[int, Path]` executes under `seq.state_lock(layout, tag)`. It inspects existing turn directories under `layout.turns_dir(tag)`, computes `next_n = 1 + max((existing_n for {role}-{existing_n}), default=0)`, creates `sprints/{repo}/{tag}/runs/turns/{role}-{next_n}/` with mode `0o755` via exclusive `os.mkdir`, and returns `(next_n, turn_dir)`. Valid roles: `"architect"`, `"challenger"`, `"curator"`. Unknown role or invalid tag raises `ValueError`.
* S2-R1.3 `latest_turn(layout, tag, role) -> tuple[int, Path] | None` inspects existing turn directories and returns `(n, turn_dir)` for the highest `n` of that role, or `None` if no turn exists. Unknown role or invalid tag raises `ValueError`.
* S2-R1.4 `resolve_turn(layout, tag, turn_id) -> Path` validates that `turn_id` matches `^(architect|challenger|curator)-[1-9][0-9]*\Z`, verifies directory existence under `layout.turns_dir(tag)`, and returns the `Path`. Missing directory raises `FileNotFoundError`; malformed ID or invalid tag raises `ValueError`.
* S2-R1.5 Courier specification: when `ACTL_COURIER_DIR` is set to a non-empty path in `os.environ`, `actl bundle` also creates drawer directory `$ACTL_COURIER_DIR/{stamp}__{repo}__{tag}__{role}-{n}__{purpose}/` (where `stamp` is UTC `YYYYMMDDTHHMMZ`) and writes `bundle.txt` inside it. If `ACTL_COURIER_DIR` is unset or empty, only the turn ledger copy is written.
* S2-R1.6 Turn ledger files are append-only (`unpack` never modifies `bundle.txt` or `bundle.json`): `bundle.txt`, `bundle.json`, `response.txt`, optional `amend-{k}.txt`, `unpack.json`, and `repair.txt` (when `unpack.json` has `ok == False`).

### S2-R2 `actl bundle <purpose>`

* S2-R2.1 CLI synopsis: `actl bundle <purpose> --sprint <TAG> [--out <FILE|->] [--osc52] [--clip] [--include <PATH>...] [--max-chars <N>] [--model <NAME>] [--json]`.
* S2-R2.2 Valid `<purpose>` values: `"architect-intake"` (role `"architect"`), `"challenger"` (role `"challenger"`), `"architect-review"` (role `"architect"`). Passing `"curator"` fails with `UsageError` (exit code `2`) and a message containing `"Stage 5"`. Any other purpose raises `UsageError` (exit code `2`).
* S2-R2.3 `allocate_turn` is called to allocate `{role}-{n}`. Static content is placed before dynamic content (Design §1.3):
1. Role prompt (`prompts/{purpose}.md`) + shared output contract (`prompts/_output_contract.md`).
2. Header listing included files with their 64-hex SHA-256 digests and byte sizes, plus a target repo map (`git ls-files` at `base_sha` with byte sizes).
3. Purpose-specific context:
* `architect-intake`: imported spec (`spec-{seq}.md`) if `active_spec` is set, plus file bodies of paths named by `--include` (resolved from `layout.target_repo` at `base_sha`).
* `challenger`: static prefix `[prompt + contract][spec-{seq}.md][solution_key-{seq}.patch (when solution_key_exposure == "full")]`, then dynamic `[qualification-{seq}.json][oracle-decision.json feedback][prior oracle-draft-{seq}/]` when present.
* `architect-review`: `[prompt + contract][oracle-critique.md][qualification-{seq}.json][oracle-draft summary]`.


4. Refusal rules (S2-R12): `--include` paths escaping `layout.target_repo`, missing at `base_sha`, or referencing `records/` raise `UsageError` (exit code `2`).


* S2-R2.4 `bundle_sha256` is the lowercase 64-hex SHA-256 of all UTF-8 bytes of `bundle.txt` preceding the final sentinel line. Every `bundle.txt` ends with the exact final line:
`<<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>\n`
* S2-R2.5 `bundle.json` is written to `turn_dir/bundle.json` with keys: `turn_id` (`str`), `role` (`"architect"|"challenger"|"curator"`), `purpose` (`str`), `base_sha` (`str`), `solution_key_sha256` (`str | null`), `files` (`list[{"path": str, "sha256": str, "bytes": int}]`), `bundle_sha256` (`str`), `created` (`str`), `model_hint` (`str`, defaults to `"unknown"` when `--model` is omitted).
* S2-R2.6 Character ceiling: `--max-chars` defaults to `200000`. If the assembled bundle exceeds `--max-chars`, `actl bundle` aborts with `UsageError` (exit code `2`) and prints a table of the largest files instead of truncating silently.
* S2-R2.7 Mutual exclusion: passing both `--out -` and `--json` raises `UsageError` (exit code `2`).
* S2-R2.8 Clipboard helpers: `--osc52` writes the OSC 52 sequence (`\x1b]52;c;{base64}\x07`) to `/dev/tty` or `stderr` (never `stdout`, so `--json` stdout stays pure JSON). `--clip` pipes the bundle to `wl-copy`, `xclip`, or `pbcopy` when available on `PATH`.
* S2-R2.9 CLI `--json` emits: `{"turn_id": str, "role": str, "purpose": str, "turn_dir": str, "bundle_path": str, "bundle_sha256": str, "sentinel": str, "chars": int, "files": list, "model_hint": str}`.

### S2-R3 Envelope Grammar (Normative)

* S2-R3.1 Response structure:
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
sentinel     := '<<<END_RESPONSE bundle="' HEX8 '">>>' NL

```


* Marker lines MUST start at column 0 after Step 3 normalization; matching is case-sensitive.
* Double quotes around the 8-hex bundle prefix in `<<<END_RESPONSE bundle="HEX8">>>` are mandatory (D-44). Unquoted sentinels (e.g. `bundle=1f13e141`), malformed attributes, or fence values outside `"3".."9"` fail with `E_SYNTAX_MARKER`.
* The sentinel MUST be the last non-blank line at top level outside any open block. Missing sentinel or unclosed block fails with `E_TRUNCATED`. Trailing non-blank text after the sentinel or multiple sentinels fails with `E_SYNTAX_MARKER`.
* Wrong 8-hex bundle prefix fails with `E_BUNDLE_MISMATCH`.


* S2-R3.2 `FILE` blocks:
* `path` names the output artifact path relative to the role's outbox.
* Duplicate `FILE` blocks with the same `path` (or case-insensitive path collision) within one response fail with `E_DUPLICATE`.
* `fence="N"` (`N` in `3..9`, default `3`): opening marker starts with `'<'*N + 'FILE '` and ends with `'>'*N`; closing marker is strictly `'<'*N + 'END_FILE' + '>'*N`. Inner markers with different fence lengths are treated as verbatim body text.


* S2-R3.3 `PATCH` blocks:
* `out` names the output patch file path relative to the role's outbox (e.g. `solution_key.patch` or `oracle-draft/mutants/contact_leak.patch`).
* `file` names the target repository file being patched relative to `layout.target_repo` (e.g. `api/profile.py` or `api/users.py`).
* When `new="true"` is omitted, the body consists of one or more `hunk(N)` blocks where delimiters scale to `N+4` characters (`<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE` for default `N=3`). When `new="true"` is present, the body is either a single hunk with an empty `SEARCH` section or raw file lines forming the new file.


* S2-R3.4 Path validation (`E_PATH`):
* Both `path`/`out` and `file` must be relative POSIX paths: no leading `/`, no `\`, no NUL byte, no empty segments (`//` or trailing `/`), no `.` or `..` segments, each segment `<= 100` chars, total length `<= 255` chars.
* `file` in a `PATCH` block MUST NOT contain any segment equal to `.git` (case-insensitively, e.g. `.git`, `.GIT`, `.Git`) and MUST NOT traverse any symlink in the target checkout.
* Output paths (`path` in `FILE`, `out` in `PATCH`) must match the allowed prefixes for `<purpose>` (`E_PATH` if outside allowed prefixes):
* `architect-intake`: allowed outputs are `spec-draft.md`, `solution_key.patch`, `sprint-proposal.toml` (or `sprint.toml` as alias per D-51). Required outputs: `solution_key.patch`, exactly one policy file (`sprint-proposal.toml` or its alias `sprint.toml`; either name alone satisfies the single policy-output requirement), and `spec-draft.md` (unless the sprint's `sprint.toml` has `spec_source == "imported"` and `state.json` has `active_spec != null`). Omitting both policy names yields `E_MISSING_REQUIRED`; supplying both policy names together yields `E_DUPLICATE`.
* `challenger`: allowed prefix is `oracle-draft/`. Required outputs: `oracle-draft/proofs/*.sh` (`>= 1`), `oracle-draft/probe.sh`, `oracle-draft/scope.txt`, `oracle-draft/coverage.md`, `oracle-draft/oracle-critique.md`, `oracle-draft/mutants/*.patch` (`>= 1`).
* `architect-review`: allowed outputs are `oracle-decision.json`, plus optional `spec-draft.md`, `solution_key.patch`, `scope.txt`. Required output: `oracle-decision.json`.





### S2-R3 Worked Examples (Normative: 6 Good, 6 Bad)

#### Example 1 (Good: Architect Intake — FILE + PATCH)

```text
<<<FILE path="sprint-proposal.toml">>>
live_run = "none"
approval_live_run = "architect"
solution_key_exposure = "full"
min_attempts_before_block = 2
max_epochs = 3

[max_attempts]
oracle = 3
implementer = 2
live = 2
curator = 2

[hard_cap.implementer]
wall_clock = "45m"
turns = 60
<<<END_FILE>>>
<<<PATCH out="solution_key.patch" file="api/profile.py">>>
<<<<<<< SEARCH
    raise NotImplementedError("public profiles not implemented")
=======
    return 200, {"name": "Ada"}
>>>>>>> REPLACE
<<<END_PATCH>>>
<<<END_RESPONSE bundle="1f13e141">>>

```

#### Example 2 (Good: Challenger Oracle Draft with Executable Probe and Mutant PATCH)

```text
<<<FILE path="oracle-draft/scope.txt">>>
FROZEN: test/**
ALLOW: api/profile.py
<<<END_FILE>>>
<<<FILE path="oracle-draft/coverage.md">>>
R1 -> 01_public.sh, probe.sh
mutants/contact_leak.patch -> 01_public.sh
<<<END_FILE>>>
<<<FILE path="oracle-draft/oracle-critique.md">>>
Critique notes.
<<<END_FILE>>>
<<<FILE path="oracle-draft/probe.sh" mode="exec">>>
#!/usr/bin/env bash
set -euo pipefail
python3 -m api.cli profile 1
<<<END_FILE>>>
<<<FILE path="oracle-draft/proofs/01_public.sh" mode="exec">>>
#!/usr/bin/env bash
set -euo pipefail
python3 -m api.cli profile 1
<<<END_FILE>>>
<<<PATCH out="oracle-draft/mutants/contact_leak.patch" file="api/profile.py">>>
<<<<<<< SEARCH
        "photo_count": len(user["photos"]),
=======
        "photo_count": len(user["photos"]),
        "contact": user["email"],
>>>>>>> REPLACE
<<<END_PATCH>>>
<<<END_RESPONSE bundle="b7eb659a">>>

```

#### Example 3 (Good: Architect Review Decision)

```text
<<<FILE path="oracle-decision.json">>>
{
  "decision": "lock_oracle",
  "feedback": "All requirements verified."
}
<<<END_FILE>>>
<<<END_RESPONSE bundle="06784a4e">>>

```

#### Example 4 (Good: Scaled Fence `fence="5"` Escaping Inner Markers)

```text
<<<<<FILE path="spec-draft.md" fence="5">>>>>
Here is an inner marker example:
<<<FILE path="inner.txt">>>
data
<<<END_FILE>>>
<<<<<END_FILE>>>>>
<<<END_RESPONSE bundle="1f13e141">>>

```

#### Example 5 (Good: Multi-Hunk Patch Merging into `solution_key.patch`)

```text
<<<PATCH out="solution_key.patch" file="api/users.py">>>
<<<<<<< SEARCH
def get_user(user_id):
=======
def get_user(user_id):
    # fetched
>>>>>>> REPLACE
<<<<<<< SEARCH
def list_user_ids():
=======
def list_user_ids():
    # listed
>>>>>>> REPLACE
<<<END_PATCH>>>
<<<END_RESPONSE bundle="1f13e141">>>

```

#### Example 6 (Good: Scaled Hunk Delimiters on `fence="4"`)

```text
<<<<PATCH out="solution_key.patch" file="api/users.py" fence="4">>>>
<<<<<<<< SEARCH
def list_user_ids():
========
def list_user_ids():
    pass
>>>>>>>> REPLACE
<<<<END_PATCH>>>>
<<<END_RESPONSE bundle="1f13e141">>>

```

#### Example 7 (Bad: Sentinel Without Mandatory Double Quotes -> `E_SYNTAX_MARKER`)

```text
<<<FILE path="oracle-decision.json">>>
{"decision": "lock_oracle", "feedback": null}
<<<END_FILE>>>
<<<END_RESPONSE bundle=06784a4e>>>

```

#### Example 8 (Bad: Wrong Bundle Prefix -> `E_BUNDLE_MISMATCH`)

```text
<<<FILE path="oracle-decision.json">>>
{"decision": "lock_oracle", "feedback": null}
<<<END_FILE>>>
<<<END_RESPONSE bundle="deadbeef">>>

```

#### Example 9 (Bad: Truncated File Block -> `E_TRUNCATED`)

```text
<<<FILE path="sprint-proposal.toml">>>
live_run = "none"

```

#### Example 10 (Bad: Path Traversal -> `E_PATH`)

```text
<<<FILE path="../escape.txt">>>
malicious
<<<END_FILE>>>
<<<END_RESPONSE bundle="1f13e141">>>

```

#### Example 11 (Bad: Duplicate File Block -> `E_DUPLICATE`)

```text
<<<FILE path="sprint-proposal.toml">>>
live_run = "none"
<<<END_FILE>>>
<<<FILE path="sprint-proposal.toml">>>
live_run = "required"
<<<END_FILE>>>
<<<END_RESPONSE bundle="1f13e141">>>

```

#### Example 12 (Bad: Search Hunk Not Matching -> `E_SEARCH_NOMATCH`)

```text
<<<PATCH out="solution_key.patch" file="api/users.py">>>
<<<<<<< SEARCH
this_text_does_not_exist_in_the_file()
=======
new_content()
>>>>>>> REPLACE
<<<END_PATCH>>>
<<<END_RESPONSE bundle="1f13e141">>>

```

### S2-R4 `actl unpack <purpose>`

* S2-R4.1 CLI synopsis: `actl unpack <purpose> --sprint <TAG> [-f <FILE> | --paste | --drawer <PATH>] [--turn <TURN_ID>] [--amend] [--json]`.
* S2-R4.2 Turn resolution: if `--turn` is given, resolve that turn and verify `bundle.json["purpose"] == <purpose>` (mismatch raises `UsageError`, exit `2`). Otherwise select the highest-numbered turn `{role}-{n}` whose `bundle.json["purpose"] == <purpose>`. If none exists, raise `UsageError` (exit `2`).
* S2-R4.3 Input channels:
* `-f <FILE>`: reads raw bytes from `<FILE>`.
* `--drawer <PATH>`: reads `<PATH>/response.txt`; if `response.txt` is absent and `<PATH>` contains `bundle.txt` plus exactly one other file, reads that file.
* `--paste`: reads `stdin` line by line, tracking open `<<<FILE...>>>` and `<<<PATCH...>>>` blocks (respecting `fence="N"`), and stops immediately when a line matching `^<<<END_RESPONSE bundle="[0-9a-f]{8}">>>[ \t]*\r?\n?\Z` is read at top level outside any open block.
* Default (stdin): reads `sys.stdin.buffer.read()` to EOF.


* S2-R4.4 Raw byte persistence: before normalization or parsing, saves raw input bytes as `turn_dir/response.txt` (or `turn_dir/amend-{k}.txt` when `--amend` is passed, where `k` is `1 + count(existing amend-*.txt)`). Calling `unpack` without `--amend` on a turn that already has `response.txt` overwrites `response.txt` only if no `amend-*.txt` exists, else raises `UsageError`.
* S2-R4.5 Step 3 Normalization Rules:
1. Strip a leading UTF-8 BOM (`\xef\xbb\xbf`) if present.
2. Convert all `CRLF` (`\r\n`) and lone `CR` (`\r`) line endings to `LF` (`\n`).
3. If the entire response (or the portion preceding/including the sentinel) is wrapped in a single outer Markdown code fence (````...` on a line before the first `<<<` marker and ````` on a line after the last `<<<` marker), strip those two fence lines only. Never strip ````` lines inside a `FILE` or `PATCH` block.
4. Strip trailing horizontal whitespace (`' '` and `'\t'`) on `<<<...>>>` marker lines and hunk delimiter lines (`<<<<<<< SEARCH`, `=======`, `>>>>>>> REPLACE`) only; body and hunk content lines preserve all trailing whitespace.


* S2-R4.6 Error evaluation precedence (deterministic single-error reporting on bad fixtures):
1. `E_TRUNCATED` (unclosed block or missing sentinel) / `E_SYNTAX_MARKER` (malformed marker, unquoted sentinel, bad fence `N`, trailing non-blank lines after sentinel)
2. `E_BUNDLE_MISMATCH` (sentinel 8-hex prefix != `bundle_sha256[:8]`)
3. `E_PATH` (invalid path syntax, traversal `..`, leading `/`, `\`, NUL, `.git` segment, symlink target, or path outside `<purpose>` allowed prefixes)
4. `E_DUPLICATE` (duplicate `FILE` path or case-insensitive path collision)
5. `E_SIZE` (any block body or synthesized output > 1,048,576 bytes or containing NUL bytes in text files)
6. `E_EXISTS` / `E_SEARCH_NOMATCH` / `E_SEARCH_MULTI` / `E_PATCH_APPLY` (during S2-R5 patch synthesis)
7. `E_JSON` / `E_TOML` / `E_SCHEMA` / `E_SHELL_SYNTAX` / `E_SCOPE` / `E_COVERAGE` / `E_MISSING_REQUIRED` (during S2-R6 post-parse validation)


* S2-R4.7 Atomic Outbox Swap and Crash Recovery (D-46):
* All validation and patch synthesis occur in temporary staging directory `sprints/{repo}/{tag}/mailboxes/.{role}-staging-{pid}` created with mode `0o770`.
* Regular files in staging get mode `0o644`; executable scripts (`mode="exec"`, `probe.sh`, `proofs/*.sh`) get mode `0o755`.
* Swap serialization and recovery: under `seq.state_lock(layout, tag)`, if zero errors occurred:
1. If a stale `mailboxes/.{role}-outbox.prev` exists from a prior interrupted swap: if `mailboxes/{role}/outbox` is missing, recover by renaming `.{role}-outbox.prev` back to `mailboxes/{role}/outbox`; otherwise `shutil.rmtree` `.{role}-outbox.prev`.
2. Rename existing `mailboxes/{role}/outbox` (if present) to `mailboxes/.{role}-outbox.prev`.
3. Rename `mailboxes/.{role}-staging-{pid}` to `mailboxes/{role}/outbox` and ensure directory mode `0o770`. If this rename raises `OSError`, rollback by renaming `mailboxes/.{role}-outbox.prev` back to `mailboxes/{role}/outbox` before re-raising.
4. Remove `mailboxes/.{role}-outbox.prev` via `shutil.rmtree`.


* On any validation/parse error: `mailboxes/.{role}-staging-{pid}` is removed in a `finally` block, `mailboxes/{role}/outbox` is left completely untouched (byte-identical to before the call), `unpack.json` (`ok = False`) and `repair.txt` are written to `turn_dir`, and `unpack` exits `2`.
* In `--drawer` mode: on `ok == True`, after verifying `file_sha256` of `turn_dir/response.txt` (or `amend-{k}.txt`), unlinks the drawer files and `rmdir`s the empty drawer directory; on `ok == False`, copies `repair.txt` into the drawer directory.


* S2-R4.8 `--amend` fold semantics: replays `response.txt` followed by `amend-1.txt .. amend-{k}.txt` in numerical order. A later `FILE` block replaces an earlier `FILE` block with the same `path` (and if `path == "solution_key.patch"` or a mutant patch path, supersedes earlier `PATCH` blocks for that `out`); a later `PATCH` block replaces an earlier `PATCH` block with the same `(out, file)` tuple. The resulting union is validated and swapped into `outbox` as a complete generation.

### S2-R5 Hermetic Patch Synthesis

* S2-R5.1 Baseline checkout: for `out == "solution_key.patch"`, `patchsynth` clones `layout.target_repo` at `bundle.json["base_sha"]` into a scratch directory. For `out == "oracle-draft/mutants/<name>.patch"`, it clones `layout.target_repo` at `base_sha` and applies the `solution_key` patch whose `file_sha256` matches `bundle.json["solution_key_sha256"]`. If a `FILE` block directly supplies `solution_key.patch` or `oracle-draft/mutants/<name>.patch` as a raw unified diff, `patchsynth` verifies it applies cleanly on the corresponding baseline checkout via `git apply --check` (failing with `E_PATCH_APPLY` if rejected).
* S2-R5.2 Hunk application (`PATCH` blocks):
* Before opening `worktree / file`, checks every path segment with `os.lstat` in the scratch worktree; any symlink segment raises `E_PATH`.
* For `new="true"`: if `worktree / file` already exists, fails with `E_EXISTS`. If the block uses hunk delimiters and the `SEARCH` text is non-empty, fails with `E_PATCH_APPLY`. Otherwise creates parent directories and writes the replacement body to `worktree / file`.
* For existing files (`new` not `"true"`): if `worktree / file` does not exist, fails with `E_PATH`. For each hunk in order, counts non-overlapping exact occurrences of `search_text` in the current file text:
* `0` matches: fails with `E_SEARCH_NOMATCH`, recording the closest candidate window from the file via `difflib.SequenceMatcher` and its 1-based line number in `detail`.
* `>= 2` matches: fails with `E_SEARCH_MULTI`, recording all 1-based matching line numbers in `detail`.
* `1` match: replaces that occurrence with `replace_text` (subsequent hunks in the same or later `PATCH` blocks for the same `(out, file)` operate on the updated text in sequence).




* S2-R5.3 Hermetic diff generation: runs `git diff --no-color --no-ext-diff --full-index --src-prefix=a/ --dst-prefix=b/ --no-renames` in the scratch worktree under `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `-c core.hooksPath=/dev/null`, `-c core.fsmonitor=false`, with fixed author/committer identity (`actl`, `actl@local`, `2026-01-01T00:00:00+0000`). If the resulting diff is empty or fails `git apply --check` on a fresh baseline checkout, fails with `E_PATCH_APPLY`.

### S2-R6 Post-Parse Validation

* S2-R6.1 JSON and TOML parsing & schema validation:
* `oracle-decision.json`: invalid JSON syntax fails with `E_JSON`; schema errors from `actl.schemas.validate("oracle-decision", doc)` fail with `E_SCHEMA`.
* `sprint-proposal.toml` (or `sprint.toml` in intake/review): invalid TOML syntax fails with `E_TOML`; schema errors from `actl.schemas.validate("sprint-proposal", doc)` (which rejects `repo_test_cmd`, `base_sha`, `sprint_tag`, `status`, `spec_source`) fail with `E_SCHEMA`.


* S2-R6.2 `coverage.md` grammar and bijection (`E_COVERAGE`):
* Blank lines and `#` comment lines are ignored. Every other line must match `^(R[0-9]+|(?:mutants/)?[A-Za-z0-9_.-]+\.patch)\s*(?:->|→|:)\s*(.+)\Z`.
* RHS tokens (comma-separated) must each be `probe.sh`, `proofs/<name>.sh`, `<name>.sh`, or a 2-digit prefix `NN` resolving uniquely to `oracle-draft/proofs/NN_*.sh`, and every referenced script must exist in `oracle-draft/`.
* Every requirement ID `R[0-9]+` present in the active spec (`spec-{seq}.md` or `spec-draft.md`) and every mutant patch in `oracle-draft/mutants/*.patch` must appear on the LHS of at least one mapping line.


* S2-R6.3 Shell script verification (`E_SHELL_SYNTAX`):
* Every `oracle-draft/proofs/*.sh` and `oracle-draft/probe.sh` is checked with `bash -n <script>` (never executed). Non-zero exit from `bash -n` fails with `E_SHELL_SYNTAX`.
* Scripts get mode `0o755` (`executable = True`). If a script lacks a `#!` shebang on line 1 or lacks `set -euo pipefail` / `set -uo pipefail`, a warning string is appended to `unpack.json["warnings"]` (non-fatal).


* S2-R6.4 Scope validation (`E_SCOPE`):
* `oracle-draft/scope.txt` is parsed with `actl.scope.parse` and validated with `actl.scope.validate` from Stage 0. Any `ValueError` or non-empty validation error list fails with `E_SCOPE`.


* S2-R6.5 Required files & size limits:
* Missing any required file for `<purpose>` (§S2-R3.4) fails with `E_MISSING_REQUIRED`.
* Any output file exceeding `1,048,576` bytes (1 MiB) fails with `E_SIZE` (`1,048,576` bytes is accepted; `1,048,577` bytes is rejected).



### S2-R7 Repair Prompts

* S2-R7.1 Whenever `unpack` fails (`ok == False`), it writes `turn_dir/repair.txt` and sets `unpack.json["repair_path"] = str(turn_dir / "repair.txt")`.
* S2-R7.2 `repair.txt` structure:
* Short instruction stating unpack failed for `turn_id` (`<purpose>`).
* One numbered entry per error in `unpack.json["errors"]` containing `code`, `path`, `message`, and (for `E_SEARCH_NOMATCH` / `E_SEARCH_MULTI`) the offending `SEARCH` snippet and nearest candidate with line number from `detail`.
* Instruction to reply with **only the blocks that must change** (for `actl unpack <purpose> --sprint <TAG> --amend`) and to end with the exact sentinel line `<<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>`.


* S2-R7.3 Confidentiality (zero oracle leakage): `repair.txt` is constructed strictly from the error records, target repo files at `base_sha` (or `solution_key` for challenger), and the model's own `response.txt`. It MUST NOT include any text from `records/<repo>/<tag>/oracle-*` or hidden fixtures that was not in `bundle.txt` or `response.txt`.

### S2-R8 `actl replay <TURN_ID>`

* S2-R8.1 CLI synopsis: `actl replay <TURN_ID> [--sprint <TAG>] [--json]`.
* S2-R8.2 Sprint resolution (A-3): if `--sprint` is omitted, scans `$ACTL_ROOT/sprints/{repo}/*`; if exactly one sprint tag directory exists, uses it; if zero or multiple exist, raises `UsageError` (exit `2`).
* S2-R8.3 Pure scratch execution: resolves `turn_dir` via `resolve_turn`, reads `bundle.json`, `response.txt`, and all `amend-{k}.txt` in numerical order, and runs normalization, envelope parsing, hermetic patch synthesis, and post-parse validation in a temporary `mktemp -d` directory without touching `mailboxes/{role}/outbox/` or `turn_dir`.
* S2-R8.4 Comparison: compares replayed `(ok, errors_codes_and_paths, outputs_paths_and_sha256_and_exec)` against stored `turn_dir/unpack.json`. Returns exit `0` (`match = True`) if identical, exit `1` (`match = False`, listing differences in `diffs`) if changed.
* S2-R8.5 CLI `--json` emits: `{"turn_id": str, "match": bool, "stored_ok": bool, "replayed_ok": bool, "diffs": list[str]}`.

### S2-R9 `actl promote <role>`

* S2-R9.1 CLI synopsis: `actl promote <role> --sprint <TAG> [--json]`.
* S2-R9.2 Preconditions: `role` in `("architect", "challenger")`; `layout.outbox(tag, role)` contains valid outputs. Invalid role or missing/invalid outbox files raise `ValueError` (mapped to `UsageError`, exit `2`).
* S2-R9.3 Transactional promotion under `seq.state_lock(layout, tag)`:
* For `role == "architect"`:
1. If `spec-draft.md` exists in outbox: computes `sha = file_sha256(spec-draft.md)` and `parent = None`. Checks `sprint_dir(tag)` for an existing `spec-*.md.meta.json` with `(kind="spec", parent=None, sha256=sha)`. If found, reuses its `seq`; else reserves `seq = reserve(layout, tag, "spec")`, writes `spec-{seq:03d}.md` and `spec-{seq:03d}.md.meta.json`. Sets `active_spec = f"spec-{seq:03d}.md"`.
2. If `solution_key.patch` exists in outbox: computes `sha = file_sha256(solution_key.patch)` and `parent = active_spec`. Deduplicates by `(kind="solution_key", parent=active_spec, sha256=sha)`; if new, reserves `seq = reserve(layout, tag, "solution_key")`, writes `solution_key-{seq:03d}.patch` and `solution_key-{seq:03d}.patch.meta.json`. Sets `active_solution_key = f"solution_key-{seq:03d}.patch"`.
3. If `sprint-proposal.toml` (or `sprint.toml`) exists in outbox: merges proposable policy fields into `records/{repo}/{tag}/sprint.toml` while preserving `sprint_tag`, `base_sha`, `repo`, `spec_source`, and `repo_test_cmd`.
4. Stages read-only copies (`0o440`) of `active_spec` and `active_solution_key` into `layout.inbox(tag, "challenger")` by unlinking any existing target file before copying. Sets `staged_to = str(layout.inbox(tag, "challenger"))`.


* For `role == "challenger"`:
1. Validates `outbox/oracle-draft/` directory; computes `sha = manifest_sha256(outbox / "oracle-draft")` and `parent = state["active_spec"]`.
2. Deduplicates by `(kind="oracle-draft", parent=active_spec, sha256=sha)` across `oracle-draft-*.meta.json` in `sprint_dir(tag)`. If new, reserves `seq = reserve(layout, tag, "oracle-draft")`, copies tree to `sprint_dir(tag) / f"oracle-draft-{seq:03d}"` (applying `0o550` to `probe.sh` and `proofs/*.sh`, `0o440` to regular files), and writes `oracle-draft-{seq:03d}.meta.json`.
3. Sets `active_oracle_draft = f"oracle-draft-{seq:03d}"` and `staged_to = str(sprint_dir(tag) / f"oracle-draft-{seq:03d}")` (D-43).




* S2-R9.4 Return value (D-43): returns all 7 keys in both `promote_role()` and `actl promote --json`:
`{"sprint_tag": str, "role": str, "promoted": list[{"kind": str, "id": str, "seq": int, "sha256": str, "reused": bool}], "staged_to": str, "active_spec": str | None, "active_solution_key": str | None, "active_oracle_draft": str | None}`.

### S2-R10 `actl next` Phase 1–2 Rules

* S2-R10.1 `src/actl/next_rules/phase12.py` defines `PRIORITY = 10` and `evaluate(layout, tag, session_probe=None) -> dict[str, str] | None`. If `state["active_contract"]` is non-null (Phase 3 active), returns `None` so `phase3.py` (`PRIORITY = 30`) handles the sprint.
* S2-R10.2 Deterministic evaluation order (first matching condition wins):
1. **Unpack failed (`repair.txt` present on latest turn `{turn_id}` where `unpack.json` has `ok == False`):**
`action = "repair"`, `command = f"actl unpack {purpose} --sprint {tag} --turn {turn_id} --amend"`, `reason = f"Turn {turn_id} failed unpack; apply repair via --amend"`.
2. **Response waiting for unpack (`response.txt` exists in latest turn `{turn_id}` without `unpack.json`, or a courier drawer for `tag` has `response.txt`):**
`action = f"unpack_{purpose.replace('-', '_')}"`, `command = f"actl unpack {purpose} --sprint {tag}"`, `reason = f"Response ready to unpack for {turn_id}"`.
3. **Architect intake Needed (`active_spec is None` or `active_solution_key is None`):**
* If architect outbox has unpacked `solution_key.patch` (and `spec-draft.md` when not imported) not yet promoted:
`action = "promote_architect"`, `command = f"actl promote architect --sprint {tag}"`, `reason = "Architect intake outputs unpacked and ready to promote"`.
* If an `architect-intake` turn exists without `unpack.json`:
`action = "unpack_architect_intake"`, `command = f"actl unpack architect-intake --sprint {tag}"`, `reason = "Awaiting architect-intake response unpack"`.
* Otherwise:
`action = "bundle_architect_intake"`, `command = f"actl bundle architect-intake --sprint {tag}"`, `reason = "Missing active spec or solution key"`.


4. **Challenger Oracle Draft Needed (`active_oracle_draft is None`):**
* If challenger outbox has unpacked `oracle-draft/` not yet promoted:
`action = "promote_challenger"`, `command = f"actl promote challenger --sprint {tag}"`, `reason = "Challenger oracle draft unpacked and ready to promote"`.
* If a `challenger` turn exists without `unpack.json`:
`action = "unpack_challenger"`, `command = f"actl unpack challenger --sprint {tag}"`, `reason = "Awaiting challenger response unpack"`.
* Otherwise:
`action = "bundle_challenger"`, `command = f"actl bundle challenger --sprint {tag}"`, `reason = "Spec and solution key ready; bundle challenger"`.


5. **Architect Review / Stage 3 Handoff (`active_oracle_draft is not None` and `active_oracle is None`):**
* If `qualification-*.json` exists in `sprint_dir(tag)`:
* If architect outbox has `oracle-decision.json`:
* If `decision == "lock_oracle"`: `action = "qualify_lock"`, `command = ""`, `reason = "Ready for Stage 3 oracle lock and contract minting"`.
* If `decision == "revise_oracle"`: `action = "bundle_challenger"`, `command = f"actl bundle challenger --sprint {tag}"`, `reason = "Architect requested oracle revision"`.


* If an `architect-review` turn exists without `unpack.json`:
`action = "unpack_architect_review"`, `command = f"actl unpack architect-review --sprint {tag}"`, `reason = "Awaiting architect-review response unpack"`.
* Otherwise:
`action = "bundle_architect_review"`, `command = f"actl bundle architect-review --sprint {tag}"`, `reason = "Qualification complete; bundle architect-review"`.


* Otherwise (no qualification receipt yet):
`action = "ready_for_qualification"`, `command = ""`, `reason = "Oracle draft promoted; ready for Stage 3 qualification"`.





### S2-R11 Role Prompt Files

* S2-R11.1 Files in `prompts/`: `architect-intake.md`, `architect-review.md`, `challenger.md`, `curator.md` (Stage 5 stub), and `prompts/_output_contract.md`.
* S2-R11.2 Authority and boundary statements (Design §3.2):
* `architect-intake.md` and `architect-review.md`: state that the Architect authors `spec-draft.md`, `solution_key.patch`, `sprint-proposal.toml`, and `oracle-decision.json`, and MUST NOT author or edit `proofs/*.sh` or `mutants/*.patch`.
* `challenger.md`: states that the Challenger authors `oracle-draft/{proofs/*.sh, probe.sh, scope.txt, coverage.md, oracle-critique.md, mutants/*.patch}`, states the proof contract (exit `0` pass, exit `1` fail with `FAIL:` line, target invoked via `ACTL_TARGET_CMD`), and MUST NOT edit the spec or `solution_key.patch`.


* S2-R11.3 Single-source output contract: `prompts/_output_contract.md` defines the `<<<FILE...>>>`, `<<<PATCH...>>>`, `fence="N"`, and `<<<END_RESPONSE bundle="...">>>` grammar. None of the persona `.md` files duplicate `<<<END_RESPONSE`; `actl bundle` appends `prompts/_output_contract.md` dynamically.

### S2-R12 Safety of the Bridge and Stage 0 Reuse

* S2-R12.1 Non-execution: `actl unpack`, `actl replay`, and `actl promote` NEVER execute any script, shell command, or code from a model response. The only subprocesses invoked are `git` (with `-c core.hooksPath=/dev/null` and `shell=False`) and `bash -n` (syntax check only, `shell=False`).
* S2-R12.2 Path containment: all file reads in `bundle` and all file writes in `unpack`/`promote` are contained within their respective `Layout` directories or scratch workspaces (`_resolve_contained` / `is_relative_to`).
* S2-R12.3 Reuse of Stage 0 modules (`P-S2-16`): Stage 2 imports and calls `actl.scope.parse`/`validate`, `actl.seq.state_lock`/`reserve`/`read_state`/`update_state`, `actl.schemas.validate`, `actl.hashing.file_sha256`/`manifest_sha256`/`canonical_json`, and `actl.layout.Layout`. It does not implement a second scope parser or modify `src/actl/cli.py` or `src/actl/next.py`.

### S2-R13 Stage 2 Additions Gate (D-41)

* S2-R13.1 Proof `proof/stage2/P-S2-18.sh` verifies git diff against `ACTL_FORK_POINT` (default `git merge-base HEAD main`):
* Requires git repository context and valid `ACTL_FORK_POINT` commit.
* Verifies Stage 2 implementation files exist (`src/actl/{turns,bundle,envelope,unpack,patchsynth,repair,replay,promote,cmd_bundle,cmd_unpack,cmd_replay,cmd_promote}.py`, `src/actl/next_rules/phase12.py`, `prompts/*.md`).
* Verifies zero diff on PB-2 frozen Stage 0/interface paths (`src/actl/INTERFACES.md`, `src/actl/cli.py`, `src/actl/next.py`, `proof/stage0/`, `fixtures/golden/expected.d/base.json`, `tools/`).
* Rejects any deleted or renamed pre-existing files outside Stage 2 scope (deletions/renames within Stage 2 scope are permitted).



---

## 2. Traceability and Three-Stand-In Vacuity Matrix

Every requirement `S2-R1`..`S2-R13` maps to executable proofs, and every proof `P-S2-01`..`P-S2-18` maps to exact delivered `test/actl/test_s2_*.py` files matching Addendum §7.7.

| Req ID | Proof ID | Delivered Script & Pytest File | Empty Module (a) | Always-Succeed Stub (b) | Always-Fail Stub (c) | Mutation Classes Killed |
| --- | --- | --- | --- | --- | --- | --- |
| S2-R1, S2-R4, S2-R5 | P-S2-01 | `proof/stage2/P-S2-01.sh` -> `test/actl/test_s2_unpack.py` (`test_p01_good_architect_intake_unpack_and_proof_preview`) & `test/actl/test_s2_turns.py` | FAIL (`ImportError`) | FAIL (no turn dir created; `solution_key.patch` missing or fails `git apply --check`) | FAIL (`RuntimeError` / exit != 0) | seq off-by-one, missing `state_lock`, corrupt patch synthesis, missing courier drawer |
| S2-R3, S2-R4, S2-R6 | P-S2-02 | `proof/stage2/P-S2-02.sh` -> `test/actl/test_s2_unpack.py` (`test_p02_good_challenger_unpack`) | FAIL (`ImportError`) | FAIL (`oracle-draft/` files missing; exec bit != `0o755`; mutants fail apply) | FAIL (`RuntimeError` / exit != 0) | `mode="exec"` ignored, mutant baseline wrong, missing file in outbox |
| S2-R3, S2-R4, S2-R6 | P-S2-03 | `proof/stage2/P-S2-03.sh` -> `test/actl/test_s2_envelope.py` (`test_p03_all_bad_responses_and_worked_examples`) | FAIL (`ImportError`) | FAIL (stub returns `0` / `ok=True` instead of exit `2` and exact `E_*` code) | FAIL (raises unhandled exception or wrong `error_code`) | quote check removed, error precedence flipped, `E_SIZE` boundary `1048576` off-by-one |
| S2-R3, S2-R4 | P-S2-04 | `proof/stage2/P-S2-04.sh` -> `test/actl/test_s2_truncation.py` | FAIL (`ImportError`) | FAIL (stub accepts truncated slices at 20 seeded offsets) | FAIL (stub rejects intact control response) | sentinel check inverted, open-block EOF check removed, seed 79 offset failure |
| S2-R3, S2-R5, S2-R12 | P-S2-05 | `proof/stage2/P-S2-05.sh` -> `test/actl/test_s2_envelope.py` (`test_p05_path_attacks_and_symlinks`) | FAIL (`ImportError`) | FAIL (stub accepts `../x`, `/etc/x`, `\`, NUL, `.GIT`, symlink, case collision) | FAIL (stub lacks `E_PATH` / `E_DUPLICATE` code) | `..` check removed, `.git` case-sensitivity bug, `lstat` symlink check omitted |
| S2-R5, S2-R7 | P-S2-06 | `proof/stage2/P-S2-06.sh` -> `test/actl/test_s2_patchsynth.py` & `test/actl/test_s2_multihunk.py` | FAIL (`ImportError`) | FAIL (stub accepts 0-match and 2-match hunks; no candidate in repair) | FAIL (fails 1-match hunk or `new="true"` creation) | `count != 1` flipped, `difflib` candidate omitted, `E_EXISTS` skipped, multi-hunk order inverted |
| S2-R4 | P-S2-07 | `proof/stage2/P-S2-07.sh` -> `test/actl/test_s2_unpack.py` (`test_p07_normalization_variants`) | FAIL (`ImportError`) | FAIL (output hashes do not match `expected.d/s2.json`) | FAIL (`RuntimeError` on valid variants) | BOM strip removed, CRLF not normalized, markdown fence strip breaks inner blocks, content trailing space stripped |
| S2-R4 | P-S2-08 | `proof/stage2/P-S2-08.sh` -> `test/actl/test_s2_unpack.py` (`test_p08_amend_fold`) & `test/actl/test_s2_atomic_swap.py` | FAIL (`ImportError`) | FAIL (`amend-1.txt` not written; block not replaced; mode != `0o770`) | FAIL (`RuntimeError` on `--amend` or rollback failure) | `--amend` overwrites `response.txt`, stale outbox file leaked, `.prev` rollback omitted |
| S2-R8 | P-S2-09 | `proof/stage2/P-S2-09.sh` -> `test/actl/test_s2_replay.py` | FAIL (`ImportError`) | FAIL (stub returns `0` / `match=True` even when `unpack.json` is mutated) | FAIL (stub returns `1` on unmodified golden turn) | comparison logic inverted, outbox mutated during replay, single-sprint auto-select broken |
| S2-R2, S2-R12 | P-S2-10 | `proof/stage2/P-S2-10.sh` -> `test/actl/test_s2_bundle.py` (`test_p10_bundle_order_limits_and_safety`) | FAIL (`ImportError`) | FAIL (stub accepts `--max-chars 50`, `records/` include, outside-repo include, `--out - --json`) | FAIL (stub fails valid `bundle` invocation) | static/dynamic order swapped, `--max-chars` check `<` vs `>`, path containment skipped |
| S2-R2, S2-R3 | P-S2-11 | `proof/stage2/P-S2-11.sh` -> `test/actl/test_s2_bundle.py` (`test_p11_sentinel_hash_and_mismatch`) | FAIL (`ImportError`) | FAIL (stub sentinel != `sha256(body)[:8]`; accepts wrong bundle sentinel) | FAIL (stub fails valid bundle/unpack round-trip) | `bundle_sha256` includes sentinel line, prefix slice `[:8]` wrong |
| S2-R9 | P-S2-12 | `proof/stage2/P-S2-12.sh` -> `test/actl/test_s2_promote.py` | FAIL (`ImportError`) | FAIL (returns != 7 keys; `spec-001.md` / `.meta.json` missing; modes != `0o440`/`0o550`) | FAIL (`RuntimeError` on valid promotion) | 5 keys instead of 7, dedup ignores `parent`, challenger `staged_to` wrong, `chmod` omitted |
| S2-R7, S2-R12 | P-S2-13 | `proof/stage2/P-S2-13.sh` -> `test/actl/test_s2_repair.py` | FAIL (`ImportError`) | FAIL (repair prompt missing error code/candidate or leaks oracle canary) | FAIL (`RuntimeError` during unpack/repair) | shell injection executed (`$(touch ...)`), hidden oracle text leaked into `repair.txt` |
| S2-R10 | P-S2-14 | `proof/stage2/P-S2-14.sh` -> `test/actl/test_s2_next_rules.py` | FAIL (`ImportError`) | FAIL (`evaluate` returns `None` or `0` instead of exact 10-state action/command table) | FAIL (`RuntimeError` on `decide_next`) | `PRIORITY != 10`, repair precedence below bundle, wrong CLI command string |
| S2-R6 | P-S2-15 | `proof/stage2/P-S2-15.sh` -> `test/actl/test_s2_postparse.py` | FAIL (`ImportError`) | FAIL (accepts bad shell syntax, bad `scope.txt`, unmapped `R3` in `coverage.md`) | FAIL (rejects valid `good_challenger.txt`) | `bash -n` skipped, `chmod 0o755` omitted, `coverage.md` bijection check skipped |
| S2-R6, S2-R12 | P-S2-16 | `proof/stage2/P-S2-16.sh` -> `test/actl/test_s2_postparse.py` (`test_p16_stage0_module_reuse`) | FAIL (modules missing) | FAIL (spy on `actl.scope.validate` / `actl.seq.state_lock` not called, or `cli.py` modified) | FAIL (calls fail) | duplicate scope parser written, `cli.py`/`next.py` modified directly |
| S2-R11 | P-S2-17 | `proof/stage2/P-S2-17.sh` -> `test/actl/test_s2_prompts.py` | FAIL (files missing) | FAIL (empty prompt files lack required persona authority & contract strings) | FAIL (check fails) | missing persona prohibition, `_output_contract.md` duplicated or omitted |
| S2-R13 | P-S2-18 | `proof/stage2/P-S2-18.sh` (git diff additions gate) | FAIL (not git / missing files) | FAIL (fails if not a git repo, or if frozen PB-2 path is dirty, or implementation missing) | FAIL (exits 1) | modified `INTERFACES.md` or `proof/stage0/`, untracked/disallowed file edits |

---

## 3. Ambiguity Register

| ID | Unclear Area | Possible Readings | Chosen Reading | Why |
| --- | --- | --- | --- | --- |
| S2A-1 | Scale of inner hunk delimiters in `fence="N"`. | (a) Fixed 7 characters. (b) Scaled to `N+4` characters. | (b) Scaled to `N+4` characters. | Addendum §7.5 and D-49 (closes O-3) state inner delimiters scale to `N+4` so hunks can contain arbitrary diff markers without collision. |
| S2A-2 | Normalization of outer Markdown code block fences. | (a) Leave untouched. (b) Strip single enclosing ````` block outside top-level `<<<...>>>` markers. | (b) Strip single enclosing ````` block. | Addendum §7.4 S2-R4 step 3 explicitly specifies stripping one enclosing Markdown code fence outside top-level markers. |
| S2A-3 | `promote_role` return dictionary key count. | (a) 5 keys (`INTERFACES.md` §1.11). (b) 7 keys (`INTERFACES.md` §2 CLI synopsis and D-43). | (b) 7 keys. | Ruling D-43 resolves this in favor of 7 keys (`sprint_tag`, `role`, `promoted`, `staged_to`, `active_spec`, `active_solution_key`, `active_oracle_draft`). |
| S2A-4 | Challenger draft promotion `staged_to` destination. | (a) `inbox/actl`. (b) Records path of promoted `oracle-draft-{seq}` directory. | (b) Records path string. | Ruling D-43 establishes that no `actl` role mailbox exists; challenger `staged_to` is `str(layout.sprint_dir(tag) / f"oracle-draft-{seq:03d}")`. |
| S2A-5 | Optional vs mandatory quotes around sentinel bundle prefix. | (a) Optional quotes. (b) Mandatory double quotes. | (b) Mandatory double quotes. | Ruling D-44 mandates double quotes in both emitters and parsers (`<<<END_RESPONSE bundle="HEX8">>>`). |
| S2A-6 | Permissions of outbox staging directory. | (a) `0o755`. (b) `0o770`. | (b) `0o770`. | Ruling D-46 mandates `0o770` on `mailboxes/.{role}-staging-{pid}` so group permissions match `outbox` after rename. |
| S2A-7 | Attributes of `<<<PATCH ...>>>` blocks. | (a) Single `path` attribute. (b) Both `out` (output patch artifact) and `file` (target repo path). | (b) Both `out` and `file` (`<<<PATCH out="..." file="...">>>`). | Addendum §7.4 S2-R5 and §7.5 normatively define `out` and `file` so `architect-intake` can write `out="solution_key.patch"` while patching `file="api/users.py"`. |
| S2A-8 | `actl replay` without `--sprint` flag. | (a) Require `--sprint` always. (b) Auto-select sole sprint under `$ACTL_ROOT/sprints/{repo}/`. | (b) Auto-select sole sprint if only one exists. | Matches `INTERFACES.md` ambiguity A-3 to support shorthand `actl replay <role>-<n>`. |
| S2A-9 | Error precedence when multiple errors exist in a single response. | (a) Arbitrary order. (b) Fixed pipeline order: framing (`E_TRUNCATED`/`E_SYNTAX_MARKER`) -> `E_BUNDLE_MISMATCH` -> `E_PATH` -> `E_DUPLICATE` -> `E_SIZE` -> patchsynth -> post-parse. | (b) Fixed pipeline order (§S2-R4.6). | Ensures deterministic `errors[0]["code"]` across all implementations for `expected.d/s2.json`. |
| S2A-10 | Command recommended by `actl next` when `unpack.json` has `ok == False`. | (a) `actl bundle ... --repair` (unlisted flag). (b) `actl unpack <purpose> --sprint <TAG> --turn <TURN_ID> --amend`. | (b) `actl unpack <purpose> --sprint <TAG> --turn <TURN_ID> --amend`. | `INTERFACES.md` §2 has no `--repair` flag on `actl bundle`; `repair.txt` instructs the user to paste the model's fix into `actl unpack --amend`. |
| S2A-11 | `actl bundle --out -` combined with `--json`. | (a) Interleave on stdout. (b) Reject with `UsageError` (exit `2`). | (b) Reject with `UsageError` (exit `2`). | Addendum §7.4 S2-R2 explicitly specifies that `--out -` with `--json` is rejected with exit `2`. |
| S2A-12 | Deduplication tuple in `promote_role`. | (a) `sha256` only. (b) `(kind, parent, sha256)`. | (b) `(kind, parent, sha256)`. | Addendum §7.4 S2-R9 and `INTERFACES.md` §1.11 require deduplication by `(kind, parent, sha256)`. |
| S2A-13 | `sprint.toml` vs `sprint-proposal.toml` filename in `architect-intake`. | (a) Accept only `sprint-proposal.toml`. (b) Accept `sprint-proposal.toml` (or `sprint.toml` as alias in intake, D-51) and validate against `schemas/sprint-proposal.json`. | (b) Validate against `schemas/sprint-proposal.json` in both cases. | Addendum §7.5 lists `sprint-proposal.toml` while golden `expected.d/s2.json` uses `sprint.toml`; accepting both names and validating against `sprint-proposal.json` satisfies both. |
| S2A-14 | Crash recovery if `unpack` is interrupted mid-swap between the two `os.rename` calls. | (a) Leave `outbox` missing. (b) Hold `state_lock`, roll back `.prev` on rename error, and auto-recover `.prev -> outbox` on next entry if `outbox` is absent. | (b) Lock + rollback + auto-recovery (§S2-R4.7). | Prevents an interrupted swap from permanently losing the prior valid outbox. |

---

## 4. Proposed Decisions and Rulings Verification

* **O-3 (Envelope & Hunk Escape):** Closed (D-49), consistent with `INTERFACES.md` §6: `fence="N"` (`N` in `3..9`, default `3`) scales block markers to `N` and inner hunk delimiters to `N+4`.
* **D-50 (Step 3 Normalization; addendum O-18):** Decided, see §S2-R4.5: strip UTF-8 BOM, convert `CRLF`/`CR` to `LF`, strip one enclosing Markdown fence outside top-level markers, and strip trailing horizontal whitespace on marker and hunk delimiter lines only.
* **Sentinel Quoting (D-44):** Mandatory double quotes around `HEX8` (`<<<END_RESPONSE bundle="HEX8">>>`) in both emitters and parsers.
* **Rulings D-34, D-41, D-43, D-44, D-46:** Verified compliant across all clauses and proofs.
