
# `actl` Interface Freeze (Stages 0–2)

Authored-by: Gemini Argon 4 High (Challengers: GPT-6 Sol, Claude Sonnet 5.5)
Baseline: `atools` commit `2acaf3c`, `VERSION` `v0.1.7`
Revision note: 2026-10-19 baseline header moved to 2acaf3c / v0.1.7; no interface changed; approved by Owner (PB-4).
Revision note: 2026-10-19 error types, scope parse/validate split, validator error paths, state_lock threading, reserve highwater, run_id rule and verify_impl effects clarified; `actl.errors` added (3 entries); no signature removed; applied at Owner request (PB-4).
Status: Normative interface contract for `S0-R15` (`PB-2`, `PB-4`). Changes after Owner acceptance require explicit Owner approval and a revision note in this file.

---

## 1. Public Cross-Stage Python Interfaces

All `actl` modules live under `src/actl/` and are imported as `actl.<module>` with `PYTHONPATH=$REPO/src`. Pre-existing suite components are imported as `router.<module>`, `sessions.<module>`, and `core.<module>`.

### 1.1 `actl.layout` (`src/actl/layout.py`) — Owning Stage: Stage 0A (`S0-R3`)

Constructs and validates all paths under `$ACTL_ROOT` (default `$HOME/actl-graph`). Valid roles are `"architect"`, `"challenger"`, `"implementer"`, `"curator"`. All methods reject empty strings, leading `/`, `\`, NUL bytes, `.` or `..` path segments, and paths resolving outside their parent directory by raising `ValueError`.

* **`Layout(root: Path | str | None = None) -> None`** (`kind: class`)
* **Preconditions:** `root` is `None` or a valid filesystem path.
* **Return value:** Initialized `Layout` instance (`self.root` resolved to absolute `Path`).
* **Errors raised:** `ValueError` if `root` contains NUL bytes.
* **Side effects:** Reads `os.environ.get("ACTL_ROOT")` when `root is None`; touches no files.
* **Idempotence:** Pure / idempotent.


* **`Layout.actl_repo -> Path`** (`kind: property`) / **`Layout.target_repo -> Path`** (`kind: property`) / **`Layout.baseline_file -> Path`** (`kind: property`)
* **Preconditions:** Valid `Layout` instance.
* **Return value:** `Path` to `$ACTL_ROOT/actl-repo`, `$ACTL_ROOT/repos/target-repo`, and `$ACTL_ROOT/baseline.json` respectively.
* **Errors raised:** None.
* **Side effects:** None.
* **Idempotence:** Pure / idempotent.


* **`Layout.sprint_dir(tag: str) -> Path`** / **`Layout.runs_dir(tag: str) -> Path`** / **`Layout.logs_dir(tag: str) -> Path`** / **`Layout.turns_dir(tag: str) -> Path`** / **`Layout.state_file(tag: str) -> Path`** / **`Layout.state_lock(tag: str) -> Path`** / **`Layout.sessions_file(tag: str) -> Path`** / **`Layout.sprint_toml(tag: str) -> Path`** / **`Layout.handoff(tag: str) -> Path`** (`kind: method`)
* **Preconditions:** `tag` is a single relative POSIX path segment passing `actl.ids.validate_sprint_tag(tag)`.
* **Return value:** `Path` under `$ACTL_ROOT/actl-repo/specs/{tag}` (`sprint_dir`, `runs_dir` = `.../runs`, `logs_dir` = `.../runs/logs`, `turns_dir` = `.../runs/turns`, `state_file` = `.../runs/state.json`, `state_lock` = `.../runs/state.lock`, `sessions_file` = `.../runs/sessions.tsv`, `sprint_toml` = `.../sprint.toml`) or `$ACTL_ROOT/handoff/{tag}` (`handoff`).
* **Errors raised:** `ValueError` on invalid `tag` or traversal attempt.
* **Side effects:** None.
* **Idempotence:** Pure / idempotent.


* **`Layout.inbox(tag: str, role: str) -> Path`** / **`Layout.outbox(tag: str, role: str) -> Path`** (`kind: method`)
* **Preconditions:** `tag` passes `validate_sprint_tag(tag)`; `role` is in `("architect", "challenger", "implementer", "curator")`.
* **Return value:** `Path` to `$ACTL_ROOT/handoff/{tag}/{role}-inputs` (`inbox`) or `$ACTL_ROOT/handoff/{tag}/{role}-outputs` (`outbox`).
* **Errors raised:** `ValueError` on invalid `tag` or unknown `role`.
* **Side effects:** None.
* **Idempotence:** Pure / idempotent.


* **`Layout.workspace(name: str, tag: str | None = None) -> Path`** (`kind: method`)
* **Preconditions:** `name` is a single relative segment (no `/`, `..`, `\`, NUL, or control chars `< 0x20` / `0x7f`); `tag` (if provided) passes `validate_sprint_tag(tag)`.
* **Return value:** `Path` to `$ACTL_ROOT/workspaces/{tag}/{name}` when `tag` is provided, else `$ACTL_ROOT/workspaces/{name}`.
* **Errors raised:** `ValueError` on invalid `name`.
* **Side effects:** None.
* **Idempotence:** Pure / idempotent.


* **`Layout.homes(role: str) -> Path`** (`kind: method`)
* **Preconditions:** `role` is in `("architect", "challenger", "implementer", "curator")`.
* **Return value:** `Path` to `$ACTL_ROOT/homes/{role}`.
* **Errors raised:** `ValueError` on unknown `role`.
* **Side effects:** None.
* **Idempotence:** Pure / idempotent.


* **`Layout.ensure_base_tree() -> None`** (`kind: method`)
* **Preconditions:** Process has write permission on `self.root.parent`.
* **Return value:** `None`.
* **Errors raised:** `OSError` on filesystem permission failure.
* **Side effects:** Creates `$ACTL_ROOT/{actl-repo/specs,handoff,workspaces,repos,homes/{role}}`; applies `0700` to `actl-repo/` and `0755` to `handoff/`, `workspaces/`, `repos/`, `homes/`.
* **Idempotence:** Idempotent.


* **`Layout.ensure_sprint_tree(tag: str) -> None`** (`kind: method`)
* **Preconditions:** `tag` passes `validate_sprint_tag(tag)`.
* **Return value:** `None`.
* **Errors raised:** `ValueError` on invalid `tag`; `OSError` on filesystem error.
* **Side effects:** Calls `ensure_base_tree()`; creates `sprint_dir(tag)`, `runs_dir(tag)`, `logs_dir(tag)`, `turns_dir(tag)`, `handoff(tag)`, and for each role creates `inbox(tag, role)` (`0750`) and `outbox(tag, role)` (`0770`).
* **Idempotence:** Idempotent.



### 1.2 `actl.ids` (`src/actl/ids.py`) — Owning Stage: Stage 0A (`S0-R4`, `S0-R5`, `S1-R9`, `S2-R9`)

* **`validate_slug(slug: str) -> bool`** (`kind: function`)
* **Preconditions:** `slug` is a `str`.
* **Return value:** `True` iff `slug` matches `^[a-z0-9][a-z0-9-]{1,40}\Z`.
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure.


* **`mint_sprint_tag(slug: str, today: date | None = None) -> str`** (`kind: function`)
* **Preconditions:** `validate_slug(slug)` is `True`.
* **Return value:** `f"{resolved_date.isoformat()}_{slug}"` (`YYYY-MM-DD_{slug}`), where `resolved_date` is `today`, else `date.fromisoformat(os.environ["ACTL_TODAY"])` if `ACTL_TODAY` is set, else `date.today()`.
* **Errors raised:** `ValueError` if `slug` or `ACTL_TODAY` is invalid. **Side effects:** Reads `ACTL_TODAY` / local date if `today is None`. **Idempotence:** Idempotent for fixed `today` or `ACTL_TODAY`.


* **`validate_sprint_tag(tag: str) -> bool`** (`kind: function`)
* **Preconditions:** `tag` is a `str`.
* **Return value:** `True` iff `tag` matches `^[0-9]{4}-[0-9]{2}-[0-9]{2}_[a-z0-9][a-z0-9-]{1,40}\Z` and the date prefix is a valid calendar date.
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure.


* **`slug_from_tag(tag: str) -> str`** (`kind: function`)
* **Preconditions:** `validate_sprint_tag(tag)` is `True`.
* **Return value:** The `{slug}` suffix after `YYYY-MM-DD_`.
* **Errors raised:** `ValueError` if `tag` is invalid. **Side effects:** None. **Idempotence:** Pure.


* **`validate_session_name(name: str) -> bool`** (`kind: function`)
* **Preconditions:** `name` is a `str`.
* **Return value:** `True` iff `name` matches `^[a-z0-9][a-z0-9-]{0,40}\Z` (`S1-R9`).
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure.


* **`format_session_name(prefix: str, slug: str, seq: int, tag: str | None = None) -> str`** (`kind: function`)
* **Preconditions:** `prefix` (`"impl"`), `slug` valid, `seq >= 1`.
* **Return value:** When `tag` is given, `f"{prefix}-{slug_trimmed}-{sha256(tag)[:4]}-{seq:03d}"` (else `f"{prefix}-{slug_trimmed}-{seq:03d}"`), guaranteed to satisfy `validate_session_name` (≤ 41 chars).
* **Errors raised:** `ValueError` if inputs cannot form a valid session name. **Side effects:** None. **Idempotence:** Pure.


* **`format_artifact_id(kind: str, seq: int) -> str`** (`kind: function`)
* **Preconditions:** `kind` in `("spec", "solution_key", "oracle", "oracle-draft", "qual", "contract", "closure", "ev", "escalation", "live-decision")`; `seq >= 1`.
* **Return value:** `f"{kind}-{seq:03d}"`.
* **Errors raised:** `ValueError` on unknown `kind` or `seq < 1`. **Side effects:** None. **Idempotence:** Pure.


* **`format_artifact_filename(kind: str, seq: int) -> str`** (`kind: function`)
* **Preconditions:** Same as `format_artifact_id`.
* **Return value:** `f"spec-{seq:03d}.md"` for `spec`, `f"solution_key-{seq:03d}.patch"` for `solution_key`, `f"{kind}-{seq:03d}"` for directory kinds (`oracle`, `oracle-draft`), and `f"{kind}-{seq:03d}.json"` for JSON record kinds (`qual`, `contract`, `closure`, `ev`, `escalation`, `live-decision`).
* **Errors raised:** `ValueError` on unknown `kind` or `seq < 1`. **Side effects:** None. **Idempotence:** Pure.


* **`parse_seq_from_name(name: str) -> int | None`** (`kind: function`)
* **Preconditions:** `name` is a filename or directory basename.
* **Return value:** Extracted integer `seq` if `name` matches `^(?:(spec)-([0-9]{3,})\.md|(solution_key)-([0-9]{3,})\.patch|(oracle|oracle-draft|implementer)-([0-9]{3,})|(qual|contract|closure|ev|escalation|live-decision)-([0-9]{3,})\.json)\Z`, else `None`.
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure.



### 1.3 `actl.seq` (`src/actl/seq.py`) — Owning Stage: Stage 0A (`S0-R5`)

* **`state_lock(layout: Layout, tag: str) -> Iterator[None]`** (`kind: function`)
* **Preconditions:** `layout.sprint_dir(tag)` exists.
* **Return value:** Context manager yielding `None`.
* **Errors raised:** `FileNotFoundError` if sprint directory does not exist; `OSError` on lock failure.
* **Side effects:** Keeps a re-entrancy depth counter in `threading.local()` keyed on the resolved path of `layout.state_lock(tag)`, so only the thread holding the lock can re-enter; other threads and other processes block in `fcntl.flock(fd, fcntl.LOCK_EX)` on their own descriptors. Acquires the `flock` on the `0 -> 1` transition and releases it on `1 -> 0`. The depth table and any open lock descriptor are discarded in a forked child (`os.register_at_fork(after_in_child=...)`), which must re-acquire the lock. The lock MUST NOT be held while waiting on a tmux session, an LLM or a network call.
* **Idempotence:** Re-entrant within a thread.


* **`reserve(layout: Layout, tag: str, kind: str) -> int`** (`kind: function`)
* **Preconditions:** `layout.state_file(tag)` exists; `kind` is a valid artifact kind for `format_artifact_id` (or `"implementer"` for attempt workspaces).
* **Return value:** Newly allocated monotonic integer `seq >= 1`.
* **Errors raised:** `FileNotFoundError` if sprint state does not exist; `ValueError` on invalid `tag` or `kind`; `OSError` on lock/write failure.
* **Side effects:** Executes inside `with state_lock(layout, tag):`. Acquires `fcntl.flock(..., LOCK_EX)` on `runs/state.lock`; reads `runs/state.json`; reads `runs/seq.highwater` (absent means `0`); computes `new_seq = max(state["seq"], highwater) + 1`; writes `new_seq` to `runs/seq.highwater` (temp file, `os.fsync`, `os.replace`, directory `os.fsync`) before touching `state.json`, so a crash leaves a gap and never a duplicate (S0-R5); then sets `state["seq"] = new_seq`; writes temp file in `runs/`, `os.fsync`, `os.replace` onto `runs/state.json`, `os.fsync` on `runs/`; releases lock.
* **Idempotence:** Non-idempotent (strictly increases `seq` on every call).


* **`reconstruct(layout: Layout, tag: str) -> int`** (`kind: function`)
* **Preconditions:** `layout.sprint_dir(tag)` exists.
* **Return value:** Highest `seq` integer (`>= 0`) across `runs/seq.highwater` (written by `reserve` before returning), `sprint_dir(tag)`, `runs_dir(tag)`, `handoff(tag)/*/*` (two levels, file names only), and `$ACTL_ROOT/workspaces/{tag}/implementer-*` via `parse_seq_from_name`. Replays existing `*.meta.json`, `qual-*.json`, `contract-*.json`, `closure-*.json`, `ev-*.json`, and `escalation-*.json` in `seq` order to deterministically restore `run_id`, `sprint_tag`, `active_spec`, `active_solution_key`, `active_oracle_draft`, `active_oracle`, `active_contract`, `epoch`, `status`, `active_stage`, `attempts`, `closures_submitted`, `hard_caps_tripped`, and `grants`.
* **Errors raised:** `FileNotFoundError` if `sprint_dir(tag)` is missing; `OSError` on write failure.
* **Side effects:** Under `runs/state.lock`, rebuilds or updates `runs/state.json` atomically with `seq = max_seq`.
* **Idempotence:** Idempotent when no new artifacts are created between calls.


* **`read_state(layout: Layout, tag: str) -> dict[str, Any]`** (`kind: function`)
* **Preconditions:** `layout.state_file(tag)` exists.
* **Return value:** Parsed `state.json` dictionary.
* **Errors raised:** `FileNotFoundError`, `ValueError` (invalid JSON). **Side effects:** Reads `runs/state.json`. **Idempotence:** Idempotent.


* **`update_state(layout: Layout, tag: str, updates: dict[str, Any]) -> dict[str, Any]`** (`kind: function`)
* **Preconditions:** `layout.state_file(tag)` exists; `updates` does not modify `seq` (which only `reserve` and `reconstruct` may advance), performs a recursive dictionary merge for nested dicts (`attempts`, `grants`), and passes `schemas.validate("state", merged)`.
* **Return value:** Updated `state.json` dictionary.
* **Errors raised:** `FileNotFoundError`, `ValueError` if updated state fails `state` schema validation.
* **Side effects:** Executes inside `with state_lock(layout, tag):`. Atomically updates `runs/state.json` under `runs/state.lock`.
* **Idempotence:** Idempotent for identical `updates` key/value pairs.



### 1.4 `actl.hashing` (`src/actl/hashing.py`) — Owning Stage: Stage 0A (`S0-R6`)

* **`file_sha256(path: Path | str) -> str`** (`kind: function`)
* **Preconditions:** `path` points to an existing regular file (not a symlink, directory, or special file).
* **Return value:** 64-char lowercase hex SHA-256 of raw bytes.
* **Errors raised:** `FileNotFoundError` if missing; `ValueError` if `path` is a symlink, directory, or special file.
* **Side effects:** Reads `path`. **Idempotence:** Pure / idempotent.


* **`manifest_sha256(directory: Path | str) -> str`** (`kind: function`)
* **Preconditions:** `directory` is an existing non-symlink directory containing only regular files and subdirectories.
* **Return value:** 64-char lowercase hex SHA-256 of the UTF-8 manifest formed by sorting all regular files under `directory` bytewise by POSIX relative path (`relpath.encode("utf-8")`) and concatenating `f"{relpath}\0{exec_flag}\0{file_sha256}\n"` where `exec_flag` is `"x"` if `(st_mode & 0o111) != 0` else `"-"`. Empty directories are ignored.
* **Errors raised:** `FileNotFoundError` if `directory` does not exist; `ValueError` if `directory` or any nested entry is a symlink or special file (FIFO, socket, device).
* **Side effects:** Reads directory tree under `directory`. **Idempotence:** Pure / idempotent.


* **`canonical_json(obj: Any) -> bytes`** (`kind: function`)
* **Preconditions:** `obj` is JSON-serializable with no `NaN`, `Infinity`, or `-Infinity`; all dictionary keys are strictly `str`.
* **Return value:** UTF-8 bytes from `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")`.
* **Errors raised:** `TypeError` on non-string dictionary keys; `ValueError` on `NaN`, `Infinity`, or `-Infinity` floats; `ValueError` on lone or unpaired UTF-16 surrogates (U+D800..U+DFFF) before UTF-8 encoding; `TypeError` on non-serializable objects.
* **Side effects:** None. **Idempotence:** Pure.


* **`json_sha256(obj: Any) -> str`** (`kind: function`)
* **Preconditions:** Same as `canonical_json(obj)`.
* **Return value:** 64-char lowercase hex SHA-256 of `canonical_json(obj)`.
* **Errors raised:** `ValueError` or `TypeError`. **Side effects:** None. **Idempotence:** Pure.



### 1.5 `actl.schemas` (`src/actl/schemas.py`) — Owning Stage: Stage 0A (`S0-R7`, `S0-R14`, `S0-R15`)

* **`validate(kind: str, obj: Any) -> list[dict[str, str]]`** (`kind: function`)
* **Preconditions:** `kind` is in `("common", "state", "sprint", "sprint-proposal", "closure", "ev", "qual", "contract", "oracle-decision", "prior_attempt", "meta", "attempt")`.
* **Return value:** List of `{"path": str, "message": str}` dicts sorted by `(path, message)` produced exclusively by the in-tree stdlib validator (never delegating to `jsonschema`). `path` is the RFC 6901 JSON Pointer of the failing instance location (decimal array indices; `~` escaped as `~0`, `/` as `~1`), with the root written as `"/"`. A `type`, `enum`, `const`, `pattern`, `minimum`, `minLength` or `maxLength` violation reports the offending value (for example `/steps/0/exit_code`); a missing `required` property reports the property that should exist (`/<parent>/<prop>`); a rejected `additionalProperties` reports the extra property; `anyOf`/`oneOf` report one entry at the instance with all branch failures in `message`. Raises `ValueError` at schema load if a schema contains an unsupported keyword. Empty list `[]` iff `obj` conforms to `schemas/{kind}.json`.
* **Errors raised:** `ValueError` ONLY if `kind` is unknown or schema load fails. Never raises on invalid `obj` data.
* **Side effects:** Reads `schemas/*.json`. **Idempotence:** Pure / idempotent.


* **`load_expected(expected_dir: Path | str | None = None) -> dict[str, Any]`** (`kind: function`)
* **Preconditions:** `expected_dir` (default `$REPO/fixtures/golden/expected.d`) exists and contains `*.json` fragments.
* **Return value:** Merged dictionary `{"base_sha": str, "cases": dict[str, Any], "responses": dict[str, Any]}` loaded in lexical filename order.
* **Errors raised:** `FileNotFoundError` if directory missing; `ValueError` on malformed JSON or duplicate key conflict across fragments.
* **Side effects:** Reads `expected.d/*.json`. **Idempotence:** Pure / idempotent.


* **`StepResult(id: str, cmd: str, exit_code: int, output_sha256: str, output_tail: str = "", duration_ms: int = 0, failing_line: str | None = None) -> None`** (`kind: class`, dataclass; defined in `actl.schemas` in Stage 0A and re-exported in `actl.verify` in Stage 1)
* **Preconditions:** `id` and `cmd` non-empty strings; `output_sha256` is 64-char hex.
* **Return value:** `StepResult` instance.
* **Errors raised:** `TypeError` on missing required fields. **Side effects:** None. **Idempotence:** Pure.


* **`StepResult.to_ev_step() -> dict[str, Any]`** (`kind: method`)
* **Preconditions:** Valid `StepResult` instance.
* **Return value:** `{"id": self.id, "cmd": self.cmd, "exit_code": self.exit_code, "output_sha256": self.output_sha256}`.
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure.



### 1.6 `actl.scope` (`src/actl/scope.py`) — Owning Stage: Stage 0A (`S0-R12`)

* **`ScopeRule(kind: str, pattern: str, is_literal: bool, line_no: int) -> None`** (`kind: class`, dataclass)
* **Preconditions:** `kind` in `("ALLOW", "FROZEN")`; `pattern` non-empty POSIX relative pattern; `is_literal == ("*" not in pattern)`; `line_no >= 1`.
* **Return value:** `ScopeRule` instance. **Errors raised:** `TypeError`. **Side effects:** None. **Idempotence:** Pure.


* **`parse(text: str) -> list[ScopeRule]`** (`kind: function`)
* **Preconditions:** `text` is a `str`.
* **Return value:** Ordered list of `ScopeRule` objects (blank lines and `#` comments ignored).
* **Errors raised:** `ValueError` if any non-comment line fails `^(ALLOW|FROZEN):\s*(\S.*)$`, or whose pattern has a leading `/`, a `\`, a NUL, an inline `#` comment, or any `.`, `..` or empty segment (for example `a//b` or a trailing `/`).
* **Side effects:** None. **Idempotence:** Pure.


* **`validate(rules: list[ScopeRule]) -> list[str]`** (`kind: function`)
* **Preconditions:** `rules` is a `list[ScopeRule]`.
* **Return value:** List of human-readable error strings (`[]` if valid). Never calls `match(rules, ...)` (uses internal `_match_unchecked` to prevent recursion). Trailing whitespace is stripped and inline `#` comments are rejected by `parse`, not here; rejects empty `ALLOW` sets, missing `FROZEN: test/**`, literal-vs-literal conflicts on the same path, metacharacters outside `*` and `**`, `**` not bounded by `/` or string ends, and any non-literal `ALLOW` rule under which `_match_unchecked(allow_only_rules, "__root_probe__") == "allowed"`, `_match_unchecked(allow_only_rules, "test/__probe__.py") == "allowed"`, or `_match_unchecked(allow_only_rules, "test/sub/__probe__.py") == "allowed"` where `allow_only_rules = [r for r in rules if r.kind == "ALLOW"]`. `**` matches zero or more path segments (`a/**/b` matches `a/b` and `a/x/b`).
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure.


* **`match(rules: list[ScopeRule], path: str) -> str`** (`kind: function`)
* **Preconditions:** `validate(rules) == []`; `path` is a normalized relative POSIX path (no leading `/`, `..`, `\`, or NUL).
* **Return value:** `"allowed"`, `"denied"`, or `"frozen"`. Evaluation order: (1) literal `ALLOW` exact match → `"allowed"`; (2) any `FROZEN` match → `"frozen"`; (3) any `ALLOW` glob match → `"allowed"`; (4) default → `"denied"`.
* **Errors raised:** `ValueError` if `validate(rules)` is non-empty or `path` is invalid.
* **Side effects:** None. **Idempotence:** Pure.



### 1.7 `actl.sprint` & `actl.doctor` (`src/actl/sprint.py`, `src/actl/doctor.py`) — Owning Stage: Stage 0A (`S0-R1`, `S0-R4`, `S0-R8`)

* **`load_graph_defaults(config_path: Path | str | None = None) -> dict[str, Any]`** (`actl.sprint`, `kind: function`)
* **Preconditions:** `config_path` (default `$REPO/config/graph.toml`) exists and is valid TOML.
* **Return value:** Parsed TOML dict of installation defaults (`S0-R8`).
* **Errors raised:** `FileNotFoundError`, `ValueError` (TOML parse error). **Side effects:** Reads `config/graph.toml`. **Idempotence:** Pure / idempotent.


* **`load_sprint_toml(layout: Layout, tag: str) -> dict[str, Any]`** (`actl.sprint`, `kind: function`)
* **Preconditions:** `layout.sprint_toml(tag)` exists.
* **Return value:** Parsed `sprint.toml` dictionary.
* **Errors raised:** `FileNotFoundError`, `ValueError`. **Side effects:** Reads `specs/{tag}/sprint.toml`. **Idempotence:** Pure / idempotent.


* **`init_target(layout: Layout, target: str) -> Path`** (`actl.sprint`, `kind: function`)
* **Preconditions:** `target` is a valid git repository path or URL.
* **Return value:** `layout.target_repo`.
* **Errors raised:** `ValueError` if `target` is empty or `target_repo` already exists with a different origin; `RuntimeError` if `git clone` fails.
* **Side effects:** Calls `layout.ensure_base_tree()`; clones `target` into `$ACTL_ROOT/repos/target-repo` (`--local --no-hardlinks` for local paths, with `-c core.hooksPath=/dev/null`).
* **Idempotence:** Idempotent if called again with the same `target`.


* **`create_sprint(layout: Layout, slug: str, spec_path: Path | str | None = None) -> dict[str, Any]`** (`actl.sprint`, `kind: function`)
* **Preconditions:** `validate_slug(slug)` is `True`; `layout.target_repo` is a valid git repo; minted `sprint_tag` does not exist; `spec_path` (if given) is an existing file.
* **Return value:** Dict with keys `sprint_tag`, `slug`, `base_sha`, `sprint_dir`, `handoff_dir`, `spec_source`, `active_spec`, `seq`.
* **Errors raised:** `ValueError` on invalid slug or existing sprint tag; `FileNotFoundError` if `target_repo` or `spec_path` is missing.
* **Side effects:** Creates sprint and handoff trees, `runs/state.json`, `runs/sessions.tsv` (header row), draft `sprint.toml` (`status = "draft"`, `live_run` omitted), and if `spec_path` is provided, reserves `seq = 1`, copies `spec-001.md` + `spec-001.md.meta.json`, and sets `spec_source = "imported"` and `active_spec = "spec-001.md"`.
* **Idempotence:** Non-idempotent (refuses duplicate `sprint_tag` on the same date).


* **`run_doctor(layout: Layout, refresh: bool = False) -> dict[str, Any]`** (`actl.doctor`, `kind: function`)
* **Preconditions:** `layout` is a `Layout` instance.
* **Return value:** Baseline report dict matching `baseline.json` (§3.3).
* **Errors raised:** None (missing dependencies such as `tmux` or `audit/atools-compliance_audit.sh` are recorded as `not_found` in the returned report dictionary; mapped to exit code `4` by CLI).
* **Side effects:** Runs environment checks and read-only suites (snapshotting and restoring `$REPO_DIR/proof/out/` or removing it if initially absent so `git status --porcelain` remains clean); writes `$ACTL_ROOT/baseline.json` if missing or `refresh=True`; never modifies the repository.
* **Idempotence:** Idempotent (`baseline.json` written once unless `refresh=True`).



### 1.8 `actl.cli` & `actl.next` (`src/actl/cli.py`, `src/actl/next.py`) — Owning Stage: Stage 0A (`S0-R10`, `S0-R13`)

* **`discover_commands(subparsers: argparse._SubParsersAction) -> list[str]`** (`actl.cli`, `kind: function`)
* **Preconditions:** `subparsers` is an `argparse` subparsers action.
* **Return value:** Sorted list of discovered module names (`["cmd_doctor", "cmd_init", ...]`).
* **Errors raised:** `ImportError` or `AttributeError` if a `src/actl/cmd_*.py` module lacks `register(subparsers)`.
* **Side effects:** Imports all `actl.cmd_*` modules and invokes `mod.register(subparsers)`. **Idempotence:** Idempotent per parser instance.


* **`UsageError(message: str) -> None`** / **`StateIntegrityError(message: str) -> None`** / **`EnvError(message: str) -> None`** (`actl.errors`, `kind: class`; each subclasses `Exception`; Owning Stage: Stage 0A, `S0-R10`)
* **Preconditions:** `message` is a `str`.
* **Return value:** Exception instance. `UsageError` maps to exit code `2`, `StateIntegrityError` to `3`, `EnvError` to `4` (named `EnvError` because `EnvironmentError` is an alias of `OSError` in Python 3).
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure.

* **`main(argv: list[str] | None = None) -> int`** (`actl.cli`, `kind: function`)
* **Preconditions:** `argv` is a list of CLI argument strings or `None` (`sys.argv[1:]`). Subparsers use `required=True`.
* **Return value:** Exit code in `{0, 1, 2, 3, 4}` (`S0-R10`).
* **Errors raised:** None. Pre-scans `argv` for `--json` before `argparse` execution. Explicitly maps exception types: `UsageError -> 2`, `StateIntegrityError -> 3`, `EnvError -> 4` (all three defined in `actl.errors`). Catches `SystemExit(code)` (`0` preserved for `--help`/`--version`, which always emit plain text; `code in (1,2,3,4)` preserved from handlers; other non-zero `argparse` exits mapped to `2`). Command handlers MUST translate library failures (`ValueError`, `FileNotFoundError`, `OSError`) into `UsageError`, `StateIntegrityError` or `EnvError`; `main` maps only those three types. Any other unhandled exception maps to `3` (never `1`, which is reserved for red results) and its type name is placed in the `--json` `error` field. Preserves exit code `3` across CLI tables for corrupt state/integrity halts. When `--json` is present on any error exit, emits `{"ok": false, "exit_code": int, "error": str}` to stdout.
* **Side effects:** Executes the selected subcommand. **Idempotence:** Depends on subcommand.


* **`decide_next(layout: Layout, tag: str, session_probe: Callable[[str], dict[str, Any]] | None = None) -> dict[str, str]`** (`actl.next`, `kind: function`)
* **Preconditions:** `layout.sprint_dir(tag)` exists.
* **Return value:** `{"action": str, "command": str, "reason": str}`.
* **Errors raised:** `FileNotFoundError` if sprint directory does not exist; `ValueError` on invalid `tag`.
* **Side effects:** None (pure inspection of files under `layout`). **Idempotence:** Pure / idempotent.
* **Stage 0 Behavior:** Evaluates Terminal/Hold checks (`state.status == "done"` -> `action="done"`, `"aborted"` -> `"aborted"`, `"hold"` -> `"hold_owner"`, `command=""`), then discovers `src/actl/next_rules/[!_]*.py` in ascending `(PRIORITY, __name__)` order (empty registry in Stage 0; Phase 1–3 rules specified in addendum S1-R12 and S2-R10).


* **Registry Entry Point 1 — `src/actl/cmd_*.py`:**
* Signature: `register(subparsers: argparse._SubParsersAction) -> None`
* Every `cmd_*.py` module registers its subcommand(s) on `subparsers` and binds `parser.set_defaults(func=handler)` where `handler(args: argparse.Namespace, layout: Layout) -> int`.


* **Registry Entry Point 2 — `src/actl/next_rules/*.py`:**
* Module attributes & signature:
* `PRIORITY: int` — integer priority (`phase12.py` = `10`, `phase3.py` = `30`, default if omitted = `100`).
* `evaluate(layout: Layout, tag: str, session_probe: Optional[Callable] = None) -> dict[str, str] | None` — pure function returning `{"action": str, "command": str, "reason": str}` when matched, or `None` to fall through.


* **Evaluation order:** `actl.next.decide_next` discovers all `src/actl/next_rules/[!_]*.py` modules, sorts them ascending by `(getattr(mod, "PRIORITY", 100), mod.__name__)`, and returns the first non-`None` dict returned by `mod.evaluate(layout, tag)`. If all rules return `None`, returns `{"action": "noop", "command": "", "reason": "No matching rule for current sprint state"}`.



### 1.9 `router.process` (`src/router/process.py`) — Owning Stage: Stage 0B (`S0-R16`)

* **`get_exit_path(session_name: str) -> Path`** (`kind: function`)
* **Preconditions:** `session_name` is a non-empty session name string.
* **Return value:** `Path` to `<METADATA_DIR>/<session_name>.exit` where `METADATA_DIR` is resolved dynamically on every call from `os.environ.get("ATOOLS_SESSION_DIR")` (default `Path.home() / ".cursor" / "sessions"`), and `get_log_path` similarly resolves `os.environ.get("ATOOLS_LOG_DIR")` dynamically (catching `OSError` when probing `/root/.cursor`).
* **Errors raised:** None. **Side effects:** None. **Idempotence:** Pure / idempotent.


* **`read_exit_code(session_name: str) -> int | None`** (`kind: function`)
* **Preconditions:** `session_name` is a `str`.
* **Return value:** `int` if `get_exit_path(session_name)` exists and its stripped UTF-8 text matches `re.fullmatch(r"[0-9]+\Z", text)`; otherwise `None`.
* **Errors raised:** None (all I/O and parse exceptions return `None`).
* **Side effects:** Reads `<METADATA_DIR>/<session_name>.exit`. **Idempotence:** Idempotent.



---

### 1.10 `actl.verify`, `actl.stage`, `actl.session` — Owning Stage: Stage 1 (`S1-R1`..`S1-R15`)

* **`run_selftests() -> list[StepResult]`** (`actl.verify`, `kind: function`)
* **Preconditions:** `config/secrets.toml` and `config/forbidden.toml` exist.
* **Return value:** List of `StepResult` for built-in synthetic positive/negative cases of `G1–G6` (`exit_code = 0` on pass, `3` on failure).
* **Errors raised:** None (errors captured as `exit_code = 3`). **Side effects:** Uses temporary in-memory/scratch fixtures only. **Idempotence:** Pure / idempotent.


* **`check_guards(layout: Layout, tag: str, worktree: Path, closure_path: Path | None = None, fail_fast: bool = True) -> list[StepResult]`** (`actl.verify`, `kind: function`)
* **Preconditions:** Active contract and oracle exist in `sprint_dir(tag)`; `worktree` is a git checkout descending from `base_sha`.
* **Return value:** Ordered `list[StepResult]` for `G1` → `G2` → `G3` → `G4` → `G5` → `G6`. Stops on first non-zero step when `fail_fast=True` and always stops immediately on `exit_code == 3` (`halt`).
* **Errors raised:** `FileNotFoundError` if sprint/worktree missing.
* **Side effects & behavior:** Runs `G1 -> G2 -> G3 -> G4 -> G5 -> G6`. `G3` uses `git diff --raw -z --no-renames {base_sha}..HEAD`, rejects modes outside `100644`/`100755`/`000000`, and converts `scope.match` `ValueError`s into red `G3` (`exit_code = 1`). When `closure.reason == "blocked"`, `fail_fast` is forced to `False` across `G3–G6`. **Idempotence:** Pure / idempotent.


* **`run_o1(oracle_dir: Path, worktree: Path, timeout_s: int = 60, target_cmd: str | None = None) -> list[StepResult]`** (`actl.verify`, `kind: function`)
* **Preconditions:** `oracle_dir` contains `proofs/*.sh` and `probe.sh`; `worktree` is an isolated verification clone.
* **Return value:** `list[StepResult]` for each `proofs/*.sh` (lexical order) and `probe.sh`.
* **Errors raised:** `FileNotFoundError` if `oracle_dir` or `worktree` is missing.
* **Side effects:** Stages ONLY `proofs/` and `probe.sh` into a sibling scratch directory `<worktree>.oracle-stage/` outside `worktree`, executes each with `cwd=worktree` and allowlisted env (`PATH`, `LANG`, `HOME`, `TMPDIR`, `ACTL_TARGET_CMD`), and removes `<worktree>.oracle-stage/` plus throwaway `HOME`/`TMPDIR` in a `finally` block.
* **Idempotence:** Idempotent on a clean `worktree`.


* **`run_o2(worktree: Path, repo_test_cmd: str | None = None, timeout_s: int = 120) -> list[StepResult]`** (`actl.verify`, `kind: function`)
* **Preconditions:** `worktree` exists.
* **Return value:** Single-element `list[StepResult]` with `id = "O2"` on pass or `"O2:{classname}::{name}"` (from JUnit XML, fallback `"O2"`) on failure (`S1-R6`).
* **Errors raised:** `FileNotFoundError`.
* **Side effects:** Splits `repo_test_cmd` with `shlex.split` (`shell=False`), validates `argv[0] in ("python3", "pytest")`, appends `--junitxml=<tmp_xml>`, and runs inside `worktree`. **Idempotence:** Idempotent.


* **`verify_impl(layout: Layout, tag: str, closure_path: Path | None = None, worktree: Path | None = None, fail_fast: bool = True, session_info: dict[str, Any] | None = None, strict_tripwire: bool = False) -> dict[str, Any]`** (`actl.verify`, `kind: function`)
* **Preconditions:** Sprint `tag` has an active contract and oracle. `closure_path=None` evaluates no closure (`G2` and the blocked-precondition check are skipped, nothing is stamped, `closures_submitted` is unchanged); `worktree=None` resolves to the attempt workspace `layout.workspace(f"implementer-{attempt_seq:03d}", tag)` (proposed; Owner to confirm).
* **Return value:** Validated `ev-{seq}.json` dict (`exit_code` in `{0, 1, 3}`).
* **Errors raised:** `FileNotFoundError`, `ValueError`.
* **Side effects:** Accepts `closure_path` at either `implementer-outputs/closure.json` or `closure-{seq:03d}.json`, stamps `kind="closure"`, `seq`, `parent=contract_id` into `runs/closure-{seq:03d}.json`, sets `ev.parent = f"closure-{attempt_seq:03d}.json"`, forces `G2` red if `session_info` has `lost=True` or `hard_cap=True`, evaluates post-`O2` blocked preconditions when `reason == "blocked"`, writes `runs/ev-{seq:03d}.json` (plus `handoff/{tag}/implementer-inputs/prior_attempt.json` when `exit_code == 1`, S1-R7), increments `closures_submitted` once per stamped closure via `update_state`, merges `scan_tripwires` output into `ev.tripwires` (a non-empty result makes the run red when `strict_tripwire=True`), and only then unlinks original `<LOG_DIR>/<session>.log` and `<METADATA_DIR>/<session>.exit`.
* **Idempotence:** Non-idempotent (reserves a new `seq` and writes `runs/ev-{seq}.json` per call; deterministic outputs modulo `seq`, `id`, and `duration_ms`).


* **Session Helpers (`actl.session`, Stage 1 — names frozen here, full runtime behavior in `S1-R9`, `S1-R10`, `S1-R14`, `S1-R15`):**
* **`start_session(session_name: str, worktree: Path, instruction: str, mode: str = "detach", tier: str = "balanced", engine: str = "cursor", wall_clock: str = "45m") -> int`** (`kind: function`)
* **Preconditions:** `validate_session_name(session_name)` is `True`; `instruction` is ASCII-only, not `"help"`, and `len(json.dumps(instruction)) < 100000` (`S1-R9`); `mode` in `("detach", "foreground")`.
* **Return value:** Process launch exit code (`0` on detached spawn or foreground pass).
* **Errors raised:** `ValueError` on invalid session name or instruction; `RuntimeError` if `arouter`/`tmux` is missing.
* **Side effects:** Invokes `bin/arouter` with `cwd=worktree` and `stdin=DEVNULL`.
* **Idempotence:** Non-idempotent (spawns a session).


* **`wait_session(session_name: str, timeout_s: int = 2700, poll_interval_s: float = 1.0) -> dict[str, Any]`** (`kind: function`)
* **Preconditions:** `validate_session_name(session_name)` is `True`.
* **Return value:** `{"name": str, "exit_code": int | None, "hard_cap": bool, "lost": bool, "log_sha256": str | None}` (`S1-R14`).
* **Errors raised:** `ValueError` on invalid name; `RuntimeError` if `shutil.which("tmux")` is `None` (mapped to exit code `4`).
* **Side effects:** Polls `tmux list-sessions`; calls `arouter kill` on watchdog overrun; reads `.exit` via `router.process.read_exit_code`.
* **Idempotence:** Idempotent once session has exited and `.exit` file remains on disk. Must be called prior to `archive_session_log` (reads `.exit`; unlinked only after `ev` is written).


* **`archive_session_log(layout: Layout, tag: str, seq: int, session_name: str) -> str | None`** (`kind: function`)
* **Preconditions:** Session `session_name` has terminated.
* **Return value:** 64-char hex SHA-256 of raw `<LOG_DIR>/<session_name>.log`, or `None` if no log file exists (`S1-R15`).
* **Errors raised:** `OSError`.
* **Side effects:** Copies `<LOG_DIR>/<session_name>.log` to `runs/logs/impl-{seq:03d}.log` and `<METADATA_DIR>/<session_name>.exit` to `runs/logs/impl-{seq:03d}.exit` and verifies SHA-256; copies and verifies SHA-256 without unlinking; unlink handled by verify_impl after ev fsync (and after `ev` persistence when called from `dispatch-impl`).
* **Idempotence:** Not idempotent once original log is unlinked (returns existing hash if `runs/logs/impl-{seq:03d}.log` already exists).


* **`scan_tripwires(layout: Layout, tag: str, seq: int, log_path: Path | None = None) -> list[dict[str, Any]]`** (`kind: function`)
* **Preconditions:** `tag` valid, `seq >= 1`.
* **Return value:** List of `{"source": "transcript" | "log", "line_no": int, "pattern": str, "excerpt": str}` dicts (`S1-R10`).
* **Errors raised:** None.
* **Side effects:** Scans ANSI-stripped `log_path` and Cursor transcripts while ignoring lines originating from `skills/actl-implementer/SKILL.md`, `implementer-inputs/contract-*.json`, and `O1:` step tokens in `implementer-inputs/prior_attempt.json`. **Idempotence:** Pure / idempotent.





### 1.11 `actl.turns` & `actl.promote` — Owning Stage: Stage 2 (`S2-R1`, `S2-R9`)

* **`allocate_turn(layout: Layout, tag: str, role: str) -> tuple[int, Path]`** (`actl.turns`, `kind: function`)
* **Preconditions:** `role` in `("architect", "challenger", "curator")`.
* **Return value:** `(n, turn_dir)` where `n = 1 + max((existing_n for {role}-{existing_n} in turns_dir(tag)), default=0)` created atomically via `os.mkdir` under `runs/state.lock`.
* **Errors raised:** `ValueError` on invalid `tag` or `role`; `OSError`.
* **Side effects:** Creates `runs/turns/{role}-{n}/`. **Idempotence:** Non-idempotent (increments per-role turn index `n`).


* **`latest_turn(layout: Layout, tag: str, role: str) -> tuple[int, Path] | None`** (`actl.turns`, `kind: function`)
* **Preconditions:** `role` in `("architect", "challenger", "curator")`.
* **Return value:** `(n, turn_dir)` for the highest existing `n` of `role`, or `None` if none exists.
* **Errors raised:** `ValueError`. **Side effects:** Reads `runs/turns/`. **Idempotence:** Pure / idempotent.


* **`resolve_turn(layout: Layout, tag: str, turn_id: str) -> Path`** (`actl.turns`, `kind: function`)
* **Preconditions:** `turn_id` matches `^(architect|challenger|curator)-[1-9][0-9]*$` and exists under `layout.turns_dir(tag)`.
* **Return value:** `Path` to `runs/turns/{turn_id}`.
* **Errors raised:** `ValueError` on bad format; `FileNotFoundError` if directory does not exist. **Side effects:** None. **Idempotence:** Pure.


* **`promote_role(layout: Layout, tag: str, role: str) -> dict[str, Any]`** (`actl.promote`, `kind: function`)
* **Preconditions:** `role` in `("architect", "challenger")`; `layout.outbox(tag, role)` contains validated outputs.
* **Return value:** Dict `{"sprint_tag": str, "role": str, "promoted": list[dict], "staged_to": str, "active_spec": str | None}` (`S2-R9`).
* **Errors raised:** `ValueError` on invalid role or invalid/missing draft outputs; `FileNotFoundError`.
* **Side effects:** Under `runs/state.lock`, computes content digest (`file_sha256` or `manifest_sha256`) and parent (`None` for `spec`; resulting `active_spec` for `solution_key` and `oracle-draft`). Reuses an existing artifact `seq` iff an artifact in `sprint_dir(tag)` has identical `(kind, parent, sha256)`; otherwise reserves a new `seq` via `actl.seq.reserve` and writes immutable `spec-{seq:03d}.md`, `solution_key-{seq:03d}.patch`, or `oracle-draft-{seq:03d}/` plus `*.meta.json`. Always updates `active_spec`, `active_solution_key`, and `active_oracle_draft` in `runs/state.json` and stages read-only copies into `inbox(tag, next_role)` by unlinking any existing target file before copying and applying `0550` to executable scripts (`proofs/*.sh`, `probe.sh`) and `0440` to regular files.
* **Idempotence:** Idempotent for identical draft content (same SHA-256 / `manifest_sha256` allocates no new `seq`).



---

## 2. CLI Synopsis (Stages 0–2)

Every command supports `--json` (emits a single JSON object to stdout) and honors `NO_COLOR`.
Exit codes (`S0-R10`): `0` = ok/green, `1` = red (check/replay failed), `2` = usage/schema/parse/envelope error, `3` = halt (integrity or guard self-test failure; no attempt consumed), `4` = environment error (missing required external tool).

| Command & Synopsis | Stage | Exit Codes | `--json` Top-Level Keys |
| --- | --- | --- | --- |
| `actl doctor [--refresh] [--json]` | 0A (`S0-R1`) | `0`, `2`, `4` | Same keys as `baseline.json` (§3.3) |
| `actl init --target <PATH\|URL> [--json]` | 0A (`S0-R4`) | `0`, `2`, `4` | `actl_root`, `target_repo`, `base_sha`, `created` |
| `actl sprint new <slug> [--spec <FILE>] [--json]` | 0A (`S0-R4`) | `0`, `2`, `4` | `sprint_tag`, `slug`, `base_sha`, `sprint_dir`, `handoff_dir`, `spec_source`, `active_spec`, `seq` |
| `actl next --sprint <TAG> [--json]` | 0A/1/2 (`S0-R13`, `S1-R12`, `S2-R10`) | `0`, `2`, `3`, `4` | `action`, `command`, `reason` |
| `actl selftest [--json]` | 1 (`S1-R3`) | `0`, `2`, `3`, `4` | `ok`, `exit_code`, `steps` |
| `actl verify-impl --sprint <TAG> --closure <PATH> [--worktree <PATH>] [--no-fail-fast] [--strict-tripwire] [--json]` | 1 (`S1-R11`) | `0`, `1`, `2`, `3`, `4` | Exact `ev-{seq}.json` keys (§3.4) |
| `actl dispatch-impl --sprint <TAG> [--mode detach\|foreground] [--tier cheap\|balanced\|smart] [--engine <ENG>] [--no-run] [--strict-tripwire] [--json]` | 1 (`S1-R9`) | `0`, `1`, `2`, `3`, `4` | `sprint_tag`, `seq`, `session_name`, `worktree`, `inputs_dir`, `closure_path`, `mode`, `no_run`, `ev_id`, `exit_code` |
| `actl wait <SESSION_NAME> [--sprint <TAG>] [--timeout <SEC>] [--json]` | 1 (`S1-R14`) | `0`, `1`, `2`, `4` | `name`, `exit_code`, `hard_cap`, `lost`, `log_sha256` |
| `actl bundle <purpose> --sprint <TAG> [--out <FILE|->] [--osc52] [--clip] [--include <PATH>...] [--max-chars <N>] [--model <NAME>] [--json]` | 2 (`S2-R2`) | `0`, `2`, `4` | `turn_id`, `role`, `purpose`, `turn_dir`, `bundle_path`, `bundle_sha256`, `sentinel`, `chars`, `files`, `model_hint` |
| `actl unpack <purpose> --sprint <TAG> [-f <FILE> \| --paste] [--turn <TURN_ID>] [--amend] [--json]` | 2 (`S2-R4`) | `0`, `2`, `3`, `4` | Exact `unpack.json` keys (§3.6) |
| `actl replay <TURN_ID> [--sprint <TAG>] [--json]` | 2 (`S2-R8`) | `0`, `1`, `2`, `3`, `4` | `turn_id`, `match`, `stored_ok`, `replayed_ok`, `diffs` |
| `actl promote <role> --sprint <TAG> [--json]` | 2 (`S2-R9`) | `0`, `2`, `3`, `4` | `sprint_tag`, `role`, `promoted`, `staged_to`, `active_spec`, `active_solution_key`, `active_oracle_draft` |

---

## 3. File Formats & Schemas

All JSON Schemas in `schemas/*.json` use Draft 2020-12 with `additionalProperties: false`. Sequenced immutable JSON artifacts (`closure`, `ev`, `qual`, `contract`) require `kind` (`str`), `seq` (`int >= 1`), and `parent` (`str | null`) via `schemas/common.json#/$defs/artifact_meta`. Sidecar metadata files (`*.meta.json`) use `schemas/meta.json`. Unsequenced files (`state.json`, `sprint.toml`, `sprint-proposal.toml`, `closure-draft.json`, `oracle-decision.json`, `prior_attempt.json`, `attempt.json`) do not require `kind` or `parent` (`attempt.json` records `seq` and `branch` for the dispatched workspace).

### 3.1 `state.json` (`specs/{sprint_tag}/runs/state.json` — `schemas/state.json`)

* `run_id`: `str` (`run-` followed by the first 12 hex characters of the SHA-256 of `sprint_tag`; deterministic so `reconstruct` can rebuild it; proposed, Owner to confirm)
* `sprint_tag`: `str` (`^[0-9]{4}-[0-9]{2}-[0-9]{2}_[a-z0-9][a-z0-9-]{1,40}$`)
* `seq`: `int >= 0` (monotonic counter; only field mutated in Stage 0)
* `epoch`: `int >= 1` (initialized to `1`)
* `status`: `"draft" | "running" | "hold" | "done" | "aborted"` (initialized to `"draft"`)
* `active_stage`: `"intake" | "oracle" | "implementer" | "live" | "curator" | "closeout" | null`
* `active_spec`: `str | null` (e.g. `"spec-001.md"`)
* `active_solution_key`: `str | null` (e.g. `"solution_key-002.patch"`)
* `active_oracle_draft`: `str | null` (e.g. `"oracle-draft-003"`)
* `active_oracle`: `str | null` (e.g. `"oracle-003"`)
* `active_contract`: `str | null` (e.g. `"contract-005.json"`)
* `attempts`: `{"oracle": int >= 0, "implementer": int >= 0, "live": int >= 0, "curator": int >= 0}`
* `closures_submitted`: `int >= 0`
* `hard_caps_tripped`: `int >= 0`
* `grants`: `{"oracle": int >= 0, "implementer": int >= 0, "live": int >= 0, "curator": int >= 0}`
* `tmux_sessions`: `list[str]`

### 3.2 `sprint.toml` (`specs/{sprint_tag}/sprint.toml` — `schemas/sprint.json`) & `config/graph.toml`

* `sprint_tag`: `str` (`YYYY-MM-DD_{slug}`)
* `base_sha`: `str` (`^[0-9a-f]{40}\Z`)
* `status`: `"draft" | "frozen"` (default `"draft"` in `actl sprint new`)
* `spec_source`: `"architect_qna" | "imported"`
* `after`: `list[str]` (default `[]`)
* `live_run`: `"none" | "required"` (optional in `schemas/sprint.json` when `status == "draft"`, required when `status == "frozen"` and in `schemas/sprint-proposal.json`; `schemas/sprint-proposal.json` forbids `sprint_tag`, `base_sha`, `status`, `spec_source`, and `repo_test_cmd`)
* `approval_live_run`: `"architect" | "owner"` (default `"architect"`)
* `solution_key_exposure`: `"full" | "hidden"` (default `"full"`)
* `owner_review_triggers`: `list["grant_attempts" | "waive_mutant" | "update_scope" | "reopen_oracle" | "retry_live"]` (default `[]`)
* `min_attempts_before_block`: `int >= 1` (default `2`)
* `max_epochs`: `int >= 1` (default `3`)
* `repo_test_cmd`: `str` (default `"python3 -m pytest test -q -rf"`)
* `max_attempts`: `{"oracle": int >= 1, "implementer": int >= 1, "live": int >= 1, "curator": int >= 1}` (defaults: `3, 2, 2, 2`)
* `hard_cap`: `{"implementer": {"wall_clock"?: str, "turns"?: int, "tool_calls"?: int, "tokens"?: int, "cost_usd"?: number}, ...}` (default `implementer = {"wall_clock": "45m", "turns": 60}`)

### 3.3 `baseline.json` (`$ACTL_ROOT/baseline.json` — `S0-R1`)

* `version`: `str`, `head_sha`: `str`, `git_dirty`: `bool`, `git_status_porcelain`: `str`
* `ancestors`: `{"5cb7f30": bool, "759a0ca": bool, "a9b3a4e": bool, "4da9394": bool}`
* `tool_versions`: `{"python3": str, "git": str, "tmux": str | null, "bash": str}`
* `python_packages`: `{"pytest": bool, "jsonschema": bool}`
* `engine_clis`: `{"agent": bool, "codex": bool, "claude": bool, "agy": bool, "aider": bool, "vibe": bool}`
* `timeout_available`: `bool`, `effective_user`: `str`, `actl_root`: `str`, `log_dir`: `str`, `metadata_dir`: `str`, `linger_state`: `str`, `router_has_read_exit_code`: `bool`
* `suites`: `{"engines": {"present": bool, "exit_code": int | null, "tail": str}, "session_persistence": {...}, "exit_code": {...}}`
* `audit`: `{"present": bool, "exit_code": int | null, "pass": int, "fail": int, "skip": int, "warn": int, "self_test_exit_code": int | null, "tail": str}`
* `installed_sync_diffs`: `{"hooks/pre-commit": str, "rules/git-safety.md": str, ".cursor/skills/atools-repair/SKILL.md": str}`
* `warnings`: `list[str]`

### 3.4 `ev-{seq}.json`, `StepResult`, `session`, and Other Stage 0 Schemas (`S0-R7`, `S1-R1`, `S1-R14`)

* **`ev-{seq}.json` (`schemas/ev.json`):**
* `kind`: `"ev"`, `seq`: `int >= 1`, `parent`: `str | null`, `id`: `str` (`^ev-[0-9]{3,}$`)
* `stage`: `"guards" | "offline" | "live" | "blocked_check"`
* `oracle`: `str`, `contract`: `str`, `head`: `str` (`^[0-9a-f]{40}\Z`), `exit_code`: `0 | 1 | 3`
* `parent`: `str | null` (set to evaluated closure filename `"closure-{seq:03d}.json"` when evaluating a closure)
* `steps`: `list[{"id": str, "cmd": str, "exit_code": int, "output_sha256": str}]` (produced by `StepResult.to_ev_step()`)
* `failing_step`: `str | null`, `failing_line`: `str | null` (max 300 chars, single line)
* `tripwires`: `list[{"source": "transcript" | "log", "line_no": int, "pattern": str, "excerpt": str}]`
* `halt`: `{"reason": "integrity_mismatch" | "selftest_failed" | "wrapper_rejected" | "unsupported_cap" | "architect_unavailable"} | null`
* `session`: `{"name": str, "exit_code": int | null, "hard_cap": bool, "lost": bool, "log_sha256": str | null} | null`


* **`closure.json` / `closure-{seq}.json` (`schemas/closure.json`):**
* `kind`: `"closure"` (optional in agent drafts, required and stamped by `actl` upon promotion), `seq`: `int >= 1` (optional in `closure-draft.json`, required and stamped by `actl` on `runs/closure-{seq:03d}.json`), `parent`: `str | null` (optional in `closure-draft.json`, required and stamped by `actl` on `runs/closure-{seq:03d}.json`)
* `reason`: `"done" | "blocked"`, `blocking_step`: `str | null`, `notes`: `list[str]`, `backlog`: `list[str]`
* `solution_key_divergence`: `{"requirement_id": str, "rationale": str} | null`


* **`qual-{seq}.json` (`schemas/qual.json`):**
* `kind`: `"qual"`, `seq`: `int >= 1`, `parent`: `str | null`, `id`: `str` (`^qual-[0-9]{3,}$`)
* `oracle`: `str`, `spec`: `str`, `base_sha`: `str`, `manifest_sha256`: `str` (`^[0-9a-f]{64}$`)
* `null_base`: `"red" | "green"`, `solution_key_guards`: `"green" | "red"`, `solution_key_green`: `str` (`^[0-3]/3$`), `solution_key_repo_test`: `"green" | "red"`
* `mutants`: `list[{"name": str, "killed": bool, "apply_error": bool}]`
* `diagnostic_case`: `"none" | "pure_oracle_failure" | "solution_key_conflict"`


* **`contract-{seq}.json` (`schemas/contract.json`):**
* `kind`: `"contract"`, `seq`: `int >= 1`, `parent`: `str | null`, `id`: `str` (`^contract-[0-9]{3,}$`), `epoch`: `int >= 1`, `base_sha`: `str`
* `spec`: `{"seq": int, "id": str, "sha256": str}`, `oracle`: `{"seq": int, "id": str, "manifest_sha256": str}`, `qual`: `{"seq": int, "id": str, "sha256": str}`
* `sprint_sha256`: `str`, `scope`: `{"path": str, "sha256": str}`


* **`oracle-decision.json` (`schemas/oracle-decision.json`):**
* `decision`: `"lock_oracle" | "revise_oracle"`, `feedback`: `str | null`


* **`*.meta.json` sidecar (`schemas/meta.json`, `S2-R9`):**
* `kind`: `"spec" | "solution_key" | "oracle-draft"`, `seq`: `int >= 1`, `parent`: `str | null`, `sha256`: `str` (`^[0-9a-f]{64}$`)


* **`attempt.json` (`handoff/{tag}/implementer-inputs/attempt.json` — `schemas/attempt.json`, `S1-R8`, `S1-R9`):**
* `seq`: `int >= 1`, `branch`: `str` (`^wip/[0-9]{3,}$`), `sprint_tag`: `str` (optional), `contract`: `str` (optional), `spec`: `str` (optional)



### 3.5 `prior_attempt.json` (`handoff/{tag}/implementer-inputs/prior_attempt.json` — `schemas/prior_attempt.json`)

Strictly four keys (`additionalProperties: false`, `P-S1-15`):

* `diff`: `str` (output of `git diff {base_sha}..HEAD`)
* `failing_step`: `str | null` (e.g. `"G3"`, `"O1:02_no_email.sh"`, `"O2:test_users::test_public"`)
* `failing_line`: `str | null` (single line, max 300 chars)
* `closures_submitted`: `int >= 0`

### 3.6 Turn Ledger Files (`specs/{sprint_tag}/runs/turns/{role}-{n}/` — `S2-R1`, `S2-R4`, `S2-R7`)

* **`bundle.txt`:** Full prompt payload ending with final line `<<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>\n`, where `bundle_sha256` is the 64-char hex SHA-256 of all UTF-8 bytes of `bundle.txt` preceding that final line.
* **`bundle.json`:** `{"turn_id": str, "role": "architect"|"challenger"|"curator", "purpose": str, "base_sha": str, "solution_key_sha256": str | null, "files": list[{"path": str, "sha256": str, "bytes": int}], "bundle_sha256": str, "created": str, "model_hint": str}`.
* **`coverage.md` grammar (`S2-R6`, `G2`):** UTF-8 text; blank lines and `#` heading lines are ignored; every mapping line matches `^(R[0-9]+|(?:mutants/)?[A-Za-z0-9_.-]+\.patch)\s*(?:->|→|:)\s*(.+)\Z`, where the RHS is a comma-separated list of proof tokens (`proofs/<name>.sh`, `<name>.sh`, `probe.sh`, or 2-digit prefix `NN` resolving uniquely to `proofs/NN_*.sh`).
* **`runs/sessions.tsv` header (`S0-R4`):** `seq\tsession\trole\tengine\tmodel\tmodel_family\tturns\ttool_calls\ttokens\tcost_usd\texit_code\taccepted_items\tescalation_alerts_sent\n`.
* **`response.txt`:** Raw, unmodified bytes received by the first `actl unpack` call on that turn.
* **`amend-{k}.txt`:** Raw, unmodified bytes received by the `k`-th (`1`-indexed) `actl unpack --amend` call on that turn.
* **`unpack.json`:** `{"turn_id": str, "role": str, "purpose": str, "ok": bool, "bundle_sha256": str, "response_sha256": str, "amended": bool, "outputs": list[{"path": str, "sha256": str, "bytes": int, "executable": bool}], "errors": list[{"code": str, "path": str, "message": str, "detail": str | null}], "warnings": list[str], "repair_path": str | null}`. Fixed `errors[].code` vocabulary: `E_TRUNCATED`, `E_BUNDLE_MISMATCH`, `E_PATH`, `E_DUPLICATE`, `E_SYNTAX_MARKER`, `E_SEARCH_NOMATCH`, `E_SEARCH_MULTI`, `E_PATCH_APPLY`, `E_JSON`, `E_TOML`, `E_SCHEMA`, `E_SHELL_SYNTAX`, `E_SCOPE`, `E_COVERAGE`, `E_MISSING_REQUIRED`, `E_SIZE`, `E_EXISTS` (Addendum §7.6).
* **`repair.txt`:** Generated only when `unpack.json` has `ok == False`; ends with the requirement to close with `<<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>`.

### 3.7 `expected.d` Fragment Schema (`fixtures/golden/expected.d/*.json` — `S0-R14`, `§5.8`, `§7.9`)

Each fragment is a JSON object with optional keys:

* `base_sha`: `str` (defined in `base.json`)
* `cases`: `dict[str, {"applies_on": "base" | "base+key", "expect": {"step": str, "exit": 0 | 1 | 3, "failing_step": str | null, "failing_line_contains": str | null}}]`
* `responses`: `dict[str, {"purpose": "architect-intake" | "challenger" | "architect-review", "turn": str, "expect": {"exit": 0 | 2, "error_code": str | null, "output_hashes": dict[str, str]}}]`

---

## 4. Machine-Readable Interface Manifest (`interfaces.json`)

Introspection contract for `P-S0-26`:

1. `kind` is one of `"class"`, `"function"`, `"method"` (`name` = `"ClassName.method_name"`), or `"property"` (`name` = `"ClassName.prop_name"`). `self` is omitted from `params`.
2. `P-S0-26` MUST verify all entries whose `"stage"` is in `os.environ.get("ACTL_CHECK_STAGES", "0A").split(",")`. For `"stage": "0B"`, if `"0B"` is not in `ACTL_CHECK_STAGES`, `P-S0-26` verifies `"0B"` entries only if `hasattr(router.process, "read_exit_code")` is `True` (so `wip/s0a-foundations` passes before `wip/s0b-exit-code` merges). For `"stage": "1"` and `"2"`, `P-S0-26` verifies them whenever their `actl.*` module is importable.

```json
[
  {"module": "actl.errors", "name": "UsageError", "kind": "class", "stage": "0A", "params": [{"name": "message", "type": "str"}], "returns": "None"},
  {"module": "actl.errors", "name": "StateIntegrityError", "kind": "class", "stage": "0A", "params": [{"name": "message", "type": "str"}], "returns": "None"},
  {"module": "actl.errors", "name": "EnvError", "kind": "class", "stage": "0A", "params": [{"name": "message", "type": "str"}], "returns": "None"},
  {"module": "actl.layout", "name": "Layout", "kind": "class", "stage": "0A", "params": [{"name": "root", "type": "Path | str | None"}], "returns": "None"},
  {"module": "actl.layout", "name": "Layout.actl_repo", "kind": "property", "stage": "0A", "params": [], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.target_repo", "kind": "property", "stage": "0A", "params": [], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.baseline_file", "kind": "property", "stage": "0A", "params": [], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.sprint_dir", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.runs_dir", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.logs_dir", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.turns_dir", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.state_file", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.state_lock", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.sessions_file", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.sprint_toml", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.handoff", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.inbox", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}, {"name": "role", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.outbox", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}, {"name": "role", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.workspace", "kind": "method", "stage": "0A", "params": [{"name": "name", "type": "str"}, {"name": "tag", "type": "str | None"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.homes", "kind": "method", "stage": "0A", "params": [{"name": "role", "type": "str"}], "returns": "Path"},
  {"module": "actl.layout", "name": "Layout.ensure_base_tree", "kind": "method", "stage": "0A", "params": [], "returns": "None"},
  {"module": "actl.layout", "name": "Layout.ensure_sprint_tree", "kind": "method", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "None"},
  {"module": "actl.ids", "name": "validate_slug", "kind": "function", "stage": "0A", "params": [{"name": "slug", "type": "str"}], "returns": "bool"},
  {"module": "actl.ids", "name": "mint_sprint_tag", "kind": "function", "stage": "0A", "params": [{"name": "slug", "type": "str"}, {"name": "today", "type": "date | None"}], "returns": "str"},
  {"module": "actl.ids", "name": "validate_sprint_tag", "kind": "function", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "bool"},
  {"module": "actl.ids", "name": "slug_from_tag", "kind": "function", "stage": "0A", "params": [{"name": "tag", "type": "str"}], "returns": "str"},
  {"module": "actl.ids", "name": "validate_session_name", "kind": "function", "stage": "0A", "params": [{"name": "name", "type": "str"}], "returns": "bool"},
  {"module": "actl.ids", "name": "format_session_name", "kind": "function", "stage": "0A", "params": [{"name": "prefix", "type": "str"}, {"name": "slug", "type": "str"}, {"name": "seq", "type": "int"}, {"name": "tag", "type": "str | None"}], "returns": "str"},
  {"module": "actl.ids", "name": "format_artifact_id", "kind": "function", "stage": "0A", "params": [{"name": "kind", "type": "str"}, {"name": "seq", "type": "int"}], "returns": "str"},
  {"module": "actl.ids", "name": "format_artifact_filename", "kind": "function", "stage": "0A", "params": [{"name": "kind", "type": "str"}, {"name": "seq", "type": "int"}], "returns": "str"},
  {"module": "actl.ids", "name": "parse_seq_from_name", "kind": "function", "stage": "0A", "params": [{"name": "name", "type": "str"}], "returns": "int | None"},
  {"module": "actl.seq", "name": "state_lock", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}], "returns": "Iterator[None]"},
  {"module": "actl.seq", "name": "reserve", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "kind", "type": "str"}], "returns": "int"},
  {"module": "actl.seq", "name": "reconstruct", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}], "returns": "int"},
  {"module": "actl.seq", "name": "read_state", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}], "returns": "dict[str, Any]"},
  {"module": "actl.seq", "name": "update_state", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "updates", "type": "dict[str, Any]"}], "returns": "dict[str, Any]"},
  {"module": "actl.hashing", "name": "file_sha256", "kind": "function", "stage": "0A", "params": [{"name": "path", "type": "Path | str"}], "returns": "str"},
  {"module": "actl.hashing", "name": "manifest_sha256", "kind": "function", "stage": "0A", "params": [{"name": "directory", "type": "Path | str"}], "returns": "str"},
  {"module": "actl.hashing", "name": "canonical_json", "kind": "function", "stage": "0A", "params": [{"name": "obj", "type": "Any"}], "returns": "bytes"},
  {"module": "actl.hashing", "name": "json_sha256", "kind": "function", "stage": "0A", "params": [{"name": "obj", "type": "Any"}], "returns": "str"},
  {"module": "actl.schemas", "name": "validate", "kind": "function", "stage": "0A", "params": [{"name": "kind", "type": "str"}, {"name": "obj", "type": "Any"}], "returns": "list[dict[str, str]]"},
  {"module": "actl.schemas", "name": "load_expected", "kind": "function", "stage": "0A", "params": [{"name": "expected_dir", "type": "Path | str | None"}], "returns": "dict[str, Any]"},
  {"module": "actl.schemas", "name": "StepResult", "kind": "class", "stage": "0A", "params": [{"name": "id", "type": "str"}, {"name": "cmd", "type": "str"}, {"name": "exit_code", "type": "int"}, {"name": "output_sha256", "type": "str"}, {"name": "output_tail", "type": "str"}, {"name": "duration_ms", "type": "int"}, {"name": "failing_line", "type": "str | None"}], "returns": "None"},
  {"module": "actl.schemas", "name": "StepResult.to_ev_step", "kind": "method", "stage": "0A", "params": [], "returns": "dict[str, Any]"},
  {"module": "actl.scope", "name": "ScopeRule", "kind": "class", "stage": "0A", "params": [{"name": "kind", "type": "str"}, {"name": "pattern", "type": "str"}, {"name": "is_literal", "type": "bool"}, {"name": "line_no", "type": "int"}], "returns": "None"},
  {"module": "actl.scope", "name": "parse", "kind": "function", "stage": "0A", "params": [{"name": "text", "type": "str"}], "returns": "list[ScopeRule]"},
  {"module": "actl.scope", "name": "validate", "kind": "function", "stage": "0A", "params": [{"name": "rules", "type": "list[ScopeRule]"}], "returns": "list[str]"},
  {"module": "actl.scope", "name": "match", "kind": "function", "stage": "0A", "params": [{"name": "rules", "type": "list[ScopeRule]"}, {"name": "path", "type": "str"}], "returns": "str"},
  {"module": "actl.sprint", "name": "load_graph_defaults", "kind": "function", "stage": "0A", "params": [{"name": "config_path", "type": "Path | str | None"}], "returns": "dict[str, Any]"},
  {"module": "actl.sprint", "name": "load_sprint_toml", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}], "returns": "dict[str, Any]"},
  {"module": "actl.sprint", "name": "init_target", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "target", "type": "str"}], "returns": "Path"},
  {"module": "actl.sprint", "name": "create_sprint", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "slug", "type": "str"}, {"name": "spec_path", "type": "Path | str | None"}], "returns": "dict[str, Any]"},
  {"module": "actl.doctor", "name": "run_doctor", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "refresh", "type": "bool"}], "returns": "dict[str, Any]"},
  {"module": "actl.cli", "name": "discover_commands", "kind": "function", "stage": "0A", "params": [{"name": "subparsers", "type": "argparse._SubParsersAction"}], "returns": "list[str]"},
  {"module": "actl.cli", "name": "main", "kind": "function", "stage": "0A", "params": [{"name": "argv", "type": "list[str] | None"}], "returns": "int"},
  {"module": "actl.next", "name": "decide_next", "kind": "function", "stage": "0A", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "session_probe", "type": "Callable[[str], dict[str, Any]] | None"}], "returns": "dict[str, str]"},
  {"module": "router.process", "name": "get_exit_path", "kind": "function", "stage": "0B", "params": [{"name": "session_name", "type": "str"}], "returns": "Path"},
  {"module": "router.process", "name": "read_exit_code", "kind": "function", "stage": "0B", "params": [{"name": "session_name", "type": "str"}], "returns": "int | None"},
  {"module": "actl.verify", "name": "run_selftests", "kind": "function", "stage": "1", "params": [], "returns": "list[StepResult]"},
  {"module": "actl.verify", "name": "check_guards", "kind": "function", "stage": "1", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "worktree", "type": "Path"}, {"name": "closure_path", "type": "Path | None"}, {"name": "fail_fast", "type": "bool"}], "returns": "list[StepResult]"},
  {"module": "actl.verify", "name": "run_o1", "kind": "function", "stage": "1", "params": [{"name": "oracle_dir", "type": "Path"}, {"name": "worktree", "type": "Path"}, {"name": "timeout_s", "type": "int"}, {"name": "target_cmd", "type": "str | None"}], "returns": "list[StepResult]"},
  {"module": "actl.verify", "name": "run_o2", "kind": "function", "stage": "1", "params": [{"name": "worktree", "type": "Path"}, {"name": "repo_test_cmd", "type": "str | None"}, {"name": "timeout_s", "type": "int"}], "returns": "list[StepResult]"},
  {"module": "actl.verify", "name": "verify_impl", "kind": "function", "stage": "1", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "closure_path", "type": "Path | None"}, {"name": "worktree", "type": "Path | None"}, {"name": "fail_fast", "type": "bool"}, {"name": "session_info", "type": "dict[str, Any] | None"}, {"name": "strict_tripwire", "type": "bool"}], "returns": "dict[str, Any]"},
  {"module": "actl.session", "name": "start_session", "kind": "function", "stage": "1", "params": [{"name": "session_name", "type": "str"}, {"name": "worktree", "type": "Path"}, {"name": "instruction", "type": "str"}, {"name": "mode", "type": "str"}, {"name": "tier", "type": "str"}, {"name": "engine", "type": "str"}, {"name": "wall_clock", "type": "str"}], "returns": "int"},
  {"module": "actl.session", "name": "wait_session", "kind": "function", "stage": "1", "params": [{"name": "session_name", "type": "str"}, {"name": "timeout_s", "type": "int"}, {"name": "poll_interval_s", "type": "float"}], "returns": "dict[str, Any]"},
  {"module": "actl.session", "name": "archive_session_log", "kind": "function", "stage": "1", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "seq", "type": "int"}, {"name": "session_name", "type": "str"}], "returns": "str | None"},
  {"module": "actl.session", "name": "scan_tripwires", "kind": "function", "stage": "1", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "seq", "type": "int"}, {"name": "log_path", "type": "Path | None"}], "returns": "list[dict[str, Any]]"},
  {"module": "actl.turns", "name": "allocate_turn", "kind": "function", "stage": "2", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "role", "type": "str"}], "returns": "tuple[int, Path]"},
  {"module": "actl.turns", "name": "latest_turn", "kind": "function", "stage": "2", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "role", "type": "str"}], "returns": "tuple[int, Path] | None"},
  {"module": "actl.turns", "name": "resolve_turn", "kind": "function", "stage": "2", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "turn_id", "type": "str"}], "returns": "Path"},
  {"module": "actl.promote", "name": "promote_role", "kind": "function", "stage": "2", "params": [{"name": "layout", "type": "Layout"}, {"name": "tag", "type": "str"}, {"name": "role", "type": "str"}], "returns": "dict[str, Any]"}
]

```

---

## 5. Dependency Map (Stage 1 and Stage 2 Requirements → Stage 0 Names)

| Requirement | Stage 0 Names Used |
| --- | --- |
| **`S1-R1`** (`StepResult` & `ev`) | `actl.schemas.StepResult`, `actl.schemas.StepResult.to_ev_step`, `actl.schemas.validate("ev", ...)`, `actl.hashing.file_sha256` |
| **`S1-R2`** (Order, halt vs red) | `actl.schemas.StepResult`, CLI exit codes (`0` ok, `1` red, `3` halt) |
| **`S1-R3`** (Guards `G1–G6` & self-tests) | `actl.hashing.manifest_sha256` (`G1`), `actl.schemas.validate("closure", ...)` (`G2`), `actl.scope.parse`, `actl.scope.validate`, `actl.scope.match` (`G3`, `G4`), `actl.layout.Layout` |
| **`S1-R4`** (Oracle staging for `O1`) | `actl.layout.Layout.sprint_dir`, `actl.layout.Layout.workspace` |
| **`S1-R5`** (`O1` execution) | `actl.schemas.StepResult`, `actl.hashing.file_sha256` |
| **`S1-R6`** (`O2` execution) | `actl.sprint.load_sprint_toml` (`repo_test_cmd`), `actl.schemas.StepResult`, `actl.hashing.file_sha256` |
| **`S1-R7`** (`ev` & `prior_attempt` emission) | `actl.seq.reserve`, `actl.seq.read_state`, `actl.ids.format_artifact_id`, `actl.ids.format_artifact_filename`, `actl.hashing.canonical_json`, `actl.schemas.validate` (`"ev"`, `"prior_attempt"`), `actl.layout.Layout.runs_dir`, `actl.layout.Layout.inbox` |
| **`S1-R8`** (Implementer skill) | `actl.layout.Layout.inbox`, `actl.layout.Layout.outbox`, `actl.ids.format_artifact_filename("closure", seq)`, `schemas/closure.json`, `schemas/closure-draft.json`, `schemas/attempt.json` (`attempt.json`) |
| **`S1-R9`** (`actl dispatch-impl`) | `actl.cli` (`register`), `actl.layout.Layout` (`target_repo`, `workspace`, `inbox`, `outbox`), `actl.seq.reserve`, `actl.seq.update_state`, `actl.ids.slug_from_tag`, `actl.ids.format_session_name`, `actl.ids.validate_session_name`, `actl.sprint.load_sprint_toml` |
| **`S1-R10`** (Tripwire) | `actl.layout.Layout` (`actl_repo`, `logs_dir`), `actl.schemas.validate("ev", ...)` |
| **`S1-R11`** (`actl verify-impl`) | `actl.cli` (`register`), `actl.layout.Layout`, `actl.ids.parse_seq_from_name`, `actl.schemas.load_expected` (in tests) |
| **`S1-R12`** (`actl next` Phase 3 rules) | `actl.next.decide_next`, `next_rules/phase3.py` (`PRIORITY=30`, `evaluate`), `actl.layout.Layout`, `actl.seq.read_state`, `router.process.read_exit_code`, `router.process.get_exit_path` |
| **`S1-R13`** (Determinism) | `actl.hashing.canonical_json`, `actl.hashing.json_sha256`, `actl.hashing.file_sha256`, `actl.hashing.manifest_sha256` |
| **`S1-R14`** (Completion protocol & `actl wait`) | `router.process.get_exit_path`, `router.process.read_exit_code`, `actl.ids.validate_session_name`, `actl.cli` (`register`) |
| **`S1-R15`** (Log handling & retention) | `actl.layout.Layout.logs_dir`, `actl.hashing.file_sha256`, `router.process.get_exit_path` |
| **`S2-R1`** (Turn ledger) | `actl.layout.Layout.turns_dir`, `actl.hashing.file_sha256`, `actl.hashing.canonical_json` |
| **`S2-R2`** (`actl bundle`) | `actl.cli` (`register`), `actl.layout.Layout` (`sprint_dir`, `target_repo`, `turns_dir`, `inbox`), `actl.seq.read_state`, `actl.sprint.load_sprint_toml`, `actl.hashing.file_sha256` |
| **`S2-R3`** (Envelope grammar) | `actl.hashing.file_sha256` (bundle prefix check) |
| **`S2-R4`** (`actl unpack`) | `actl.cli` (`register`), `actl.layout.Layout` (`turns_dir`, `outbox`), `actl.hashing.file_sha256`, `actl.hashing.canonical_json` |
| **`S2-R5`** (Patch synthesis) | `actl.layout.Layout` (`target_repo`, `sprint_dir`), `actl.seq.read_state` |
| **`S2-R6`** (Post-parse validation) | `actl.schemas.validate` (`"oracle-decision"`, `"sprint"`, `"sprint-proposal"`), `actl.scope.parse`, `actl.scope.validate` |
| **`S2-R7`** (Repair prompts) | `actl.layout.Layout.turns_dir` |
| **`S2-R8`** (`actl replay`) | `actl.cli` (`register`), `actl.layout.Layout` (`turns_dir`, `target_repo`), `actl.hashing.canonical_json`, `actl.schemas.load_expected` (in tests) |
| **`S2-R9`** (`actl promote`) | `actl.cli` (`register`), `actl.layout.Layout` (`sprint_dir`, `outbox`, `inbox`), `actl.seq.reserve`, `actl.seq.read_state`, `actl.seq.update_state`, `actl.ids.format_artifact_id`, `actl.ids.format_artifact_filename`, `actl.hashing.file_sha256`, `actl.hashing.manifest_sha256` |
| **`S2-R10`** (`actl next` Phases 1–2 rules) | `actl.next.decide_next`, `next_rules/phase12.py` (`PRIORITY=10`, `evaluate`), `actl.layout.Layout`, `actl.seq.read_state` |
| **`S2-R11`** (Role prompt files) | `actl.layout.Layout` (`inbox`, `outbox` conventions) |
| **`S2-R12`** (Bridge safety) | `actl.layout.Layout` (`actl_repo`, `target_repo`), `actl.scope.parse`, `actl.scope.validate` |

---

## 6. Proposed Decisions (Open Items & Authority Conflicts)

* **O-1 (Single deterministic stdlib validator):** `src/actl/schemas.py` uses ONLY its built-in deterministic stdlib validator (never delegating to `jsonschema` even if installed) so error paths and messages are 100% identical across all hosts.
* **O-2 (`solution_key` naming & state pointer):** `state.json` tracks `active_solution_key` and `active_oracle_draft` explicitly, and `promote_role` deduplicates by `(kind, parent, sha256)` where `parent == state["active_spec"]`.
* **O-3 (Envelope & hunk escape):** Normative `fence="N"` (`N` in `3..9`, default `3`) on `FILE` and `PATCH` blocks scales both the block closing marker (`<`*N + `END_FILE`/`END_PATCH` + `>`*N) and inner `PATCH` hunk delimiters (`<`*(N+4) + ` SEARCH`, `=`*(N+4), `>`*(N+4) + ` REPLACE`).
* **O-8 (`failing_line` sanitization):** Strip ANSI CSI (`\x1b\[[0-9;?]*[ -/]*[@-~]`) and OSC (`\x1b\][^\x07\x1b]*(?:\x07|\x1b\\)`), replace `\r`, `\n`, and `\t` with single spaces, replace remaining code points `< 0x20` or `== 0x7f` (and lone `\x1b`) with `?`, and truncate to 300 Unicode code points.

---

## 7. Ambiguity Register

| ID | What is Unclear | Possible Readings | Chosen Reading | Why |
| --- | --- | --- | --- | --- |
| **A-1** | Exact byte placement of the executable flag (`x`/`-`) in `manifest_sha256` (`S0-R6` says `"{relpath}\0{file_sha256}\n" extended with an x/- flag`). | (a) `"{relpath}\0{exec_flag}\0{file_sha256}\n"`<br>(b) `"{relpath}\0{file_sha256}\0{exec_flag}\n"` | **(a)** `f"{relpath}\0{exec_flag}\0{file_sha256}\n"` where `exec_flag` is `"x"` if `(st_mode & 0o111) != 0` else `"-"`. | Places metadata attributes (`relpath`, `exec_flag`) before the fixed 64-char digest and keeps NUL delimiters between all fields. Frozen here so all Stage 0–3 agents compute identical digests. |
| **A-2** | `P-S0-26` runs in `run_suite_actl_s0.sh` (Stage 0A), before Stage 0B (`router.process.read_exit_code`) or Stage 1/2 modules exist, yet `INTERFACES.md` covers Stages 0–2. | (a) List only Stage 0A in `interfaces.json`.<br>(b) List all Stage 0–2 public boundary symbols with a `"stage"` field (`"0A"`, `"0B"`, `"1"`, `"2"`). | **(b)** Include `"stage"` on every `interfaces.json` entry; `P-S0-26` requires all `"0A"` entries in Stage 0A and checks `"0B"`/`"1"`/`"2"` entries when their module is present. | Satisfies both `PB-2` (single immutable `INTERFACES.md` across Stages 0–2) and `§11.1` (Stage 0A branch runs before 0B, 1, and 2). Defining `StepResult` in `actl.schemas` (re-exported in `actl.verify`) makes `StepResult` testable in Stage 0A. |
| **A-3** | `S2-R8` writes `actl replay <role>-<n>` without `--sprint TAG`, whereas `turns/` lives under `specs/{sprint_tag}/runs/turns/`. | (a) Require `--sprint TAG`.<br>(b) Accept optional `--sprint TAG`; if omitted, resolve `<TURN_ID>` if it is a path or auto-select the sole sprint under `specs/`. | **(b)** `actl replay <TURN_ID> [--sprint <TAG>] [--json]`. | Supports the exact shorthand `actl replay <role>-<n>` in `S2-R8` for single-sprint roots while remaining unambiguous when multiple sprints exist. |
| **A-4** | `S0-R7` states "Every artifact schema requires `kind`, `seq` and `parent` via `common.json`", while `P-S1-15` requires `prior_attempt.json` to have *only* 4 keys and `S2-R6` validates `oracle-decision.json` and `sprint-proposal.toml` before any `seq` is assigned. | (a) Force `kind`, `seq`, `parent` onto all 8 schemas.<br>(b) Require `kind`, `seq`, `parent` on sequenced `{kind}-{seq}` artifact schemas (`closure`, `ev`, `qual`, `contract`) and omit them on unsequenced files (`state`, `sprint`, `oracle-decision`, `prior_attempt`). | **(b)** Require `kind`, `seq`, `parent` via `common.json#/$defs/artifact_meta` on `closure`, `ev`, `qual`, `contract`; unsequenced schemas use `common.json` primitive `$defs` only. | Matches Design §4 ("every immutable artifact is named `{kind}-{seq}` ... Each file records `kind`, `seq`, and `parent`") and satisfies `P-S1-15`, `P-S0-09`, and `S2-R6` without conflict. |
