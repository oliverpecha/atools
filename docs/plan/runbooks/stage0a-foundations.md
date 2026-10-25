# Runbook: Workstream 0A — `actl` Stage 0 Foundations (`S0-R1` to `S0-R15`)

- **Workstream:** `0A` (`wip/s0a-foundations`)
- **Designated Test Suite:** `bash proof/run_suite_actl_s0.sh`
- **Specification Conformance Gate:** `bash proof/stage0/P-S0-27.sh`
- **Commit Tag Format:** `(WI-S0-R1)` through `(WI-S0-R15)` (every commit subject MUST end with a single `(WI-S0-R<k>)` tag, e.g., `feat(actl): implement layout and ids (WI-S0-R3)`).

---

## 1. Hard Blast-Radius & Immutability Rules (`PB-2`, `S0-R2`)

1. **NEVER edit, create, delete, rename, or `chmod` any file in these immutable paths:**
   - `proof/` (including `proof/stage0/*` and `proof/run_suite_*.sh`)
   - `fixtures/` (including `fixtures/golden/*`)
   - `test/actl/`
   - `src/actl/INTERFACES.md` (DO NOT edit `INTERFACES.md`; `P-S0-02.sh` fails immediately if `src/actl/INTERFACES.md` is modified relative to the fork point)
   - `docs/`, `audit/`
   - Pre-existing `atools` components: `src/router/`, `src/sessions/`, `src/core/`, `bin/arouter`, `bin/asessions`, `engines/`, `hooks/`, `rules/`
2. **Additive-Only Constraint (`P-S0-02.sh`):**
   - `P-S0-02.sh` checks `git diff --name-status` and untracked files against `ACTL_FORK_POINT` (or `git merge-base HEAD main`).
   - Only new (`A`) files under `bin/actl`, `config/graph.toml`, `schemas/*.json`, and `src/actl/**` are permitted (plus optional modifications `M` to `install.sh` or `README.md`, which are not required by any Stage 0A proof).
   - Do **NOT** create Stage 1 or Stage 2 modules (`src/actl/verify.py`, `src/actl/session.py`, `src/actl/turns.py`, `src/actl/promote.py`), because `P-S0-26` auto-checks Stage 1/2 interfaces if those modules are importable.
   - Do **NOT** leave stray temporary files or untracked artifacts inside the repository working tree.

---

## 2. Target Files to Create

Create the following files in the repository:

```text
bin/actl                          # Executable (0755) CLI wrapper
config/graph.toml                 # Installation defaults (S0-R8)
schemas/
├── common.json
├── state.json
├── sprint.json
├── sprint-proposal.json
├── closure.json
├── ev.json
├── qual.json
├── contract.json
├── oracle-decision.json
├── prior_attempt.json
├── meta.json
└── attempt.json
src/actl/
├── __init__.py
├── errors.py                     # UsageError, StateIntegrityError, EnvError
├── layout.py                     # Layout class (S0-R3)
├── ids.py                        # Slug, tag, session, artifact ID helpers (S0-R4, S0-R5, F-17)
├── seq.py                        # state_lock, reserve, reconstruct, read_state, update_state (S0-R5)
├── hashing.py                    # file_sha256, manifest_sha256, canonical_json, json_sha256 (S0-R6)
├── schemas.py                    # stdlib Draft 2020-12 validator, load_expected, StepResult (S0-R7, S0-R14)
├── scope.py                      # ScopeRule, parse, validate, match (S0-R12)
├── sprint.py                     # load_graph_defaults, load_sprint_toml, init_target, create_sprint (S0-R4, S0-R8)
├── doctor.py                     # run_doctor (S0-R1)
├── cli.py                        # discover_commands, main (S0-R10, S0-R13)
├── next.py                       # decide_next (S0-R13)
├── cmd_doctor.py                 # `actl doctor` subcommand
├── cmd_init.py                   # `actl init` subcommand
├── cmd_sprint.py                 # `actl sprint new` subcommand
├── cmd_next.py                   # `actl next` subcommand
└── next_rules/
    └── __init__.py               # Empty package in Stage 0A
```

---

## 3. Interface Contract (`P-S0-26` / `test_p26_interfaces.py`)

`test/actl/test_p26_interfaces.py` introspects all 56 Stage 0A entries in Section 4 of `src/actl/INTERFACES.md`. Every listed class, method, property, and function **MUST**:
1. Have the exact parameter names and parameter order listed in `INTERFACES.md` Section 4 (excluding `self`).
2. Have an explicit return type annotation (`-> ...` on every function/method, `-> Path` on every `@property` getter, and `-> None` on every class `__init__`).
3. Do **NOT** use `from __future__ import annotations` if it interferes with anything, or ensure ` __annotations__` always contains `"return"`. (`inspect.signature` and `fn.__annotations__["return"]` both work with standard annotations and `from __future__ import annotations`).

---

## 4. Module-by-Module Implementation Specification

### 4.1 `bin/actl` & `src/actl/errors.py`

#### `bin/actl` (mode `0755`)
Follow the `bin/asessions` wrapper pattern:
```bash
#!/usr/bin/env bash
set -euo pipefail
REPO_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")/.." && pwd)"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
exec python3 -m actl.cli "$@"
```

#### `src/actl/errors.py`
Must explicitly define `__init__(self, message: str) -> None` on all three exception classes (`P-S0-26` checks `cls.__init__` parameter names `["message"]` and return annotation `"return"`):
```python
class UsageError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class StateIntegrityError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class EnvError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
```

---

### 4.2 `src/actl/ids.py` (`S0-R4`, `S0-R5`, `F-17`)

Implement the exact signatures:
- `validate_slug(slug: str) -> bool`:
  - Returns `bool(isinstance(slug, str) and re.fullmatch(r"^[a-z0-9][a-z0-9-]{1,40}\Z", slug))` (length 2 to 41 chars, lowercase alphanumeric + hyphens, starting with `[a-z0-9]`).
- `mint_sprint_tag(slug: str, today: date | None = None) -> str`:
  - If `not validate_slug(slug)`: raise `ValueError(f"Invalid slug: {slug!r}")`.
  - If `today is not None`: `resolved = today` (verify `isinstance(today, date)`).
  - Else if `os.environ.get("ACTL_TODAY")`: parse `date.fromisoformat(os.environ["ACTL_TODAY"])` (raises `ValueError` if invalid).
  - Else: `resolved = date.today()`.
  - Return `f"{resolved.isoformat()}_{slug}"`.
- `validate_sprint_tag(tag: str) -> bool`:
  - Must be `str` matching `r"^([0-9]{4}-[0-9]{2}-[0-9]{2})_([a-z0-9][a-z0-9-]{1,40})\Z"`.
  - Parse group 1 with `date.fromisoformat(...)`; return `False` on `ValueError`.
- `slug_from_tag(tag: str) -> str`:
  - If `not validate_sprint_tag(tag)`: raise `ValueError(f"Invalid sprint tag: {tag!r}")`.
  - Return `tag.split("_", 1)[1]`.
- `validate_session_name(name: str) -> bool`:
  - Return `bool(isinstance(name, str) and re.fullmatch(r"^[a-z0-9][a-z0-9-]{0,40}\Z", name))`.
- `format_session_name(prefix: str, slug: str, seq: int, tag: str | None = None) -> str`:
  - Validate `validate_session_name(prefix)`, `validate_slug(slug)`, `isinstance(seq, int) and not isinstance(seq, bool) and seq >= 1`. If `tag is not None`, validate `validate_sprint_tag(tag)`. Raise `ValueError` if invalid.
  - Format `seq_str = f"{seq:03d}"`.
  - When `tag is not None`: `h4 = hashlib.sha256(tag.encode("utf-8")).hexdigest()[:4]`, suffix is `f"-{h4}-{seq_str}"`. Max slug length = `41 - len(prefix) - 1 - len(suffix)`. Trim `slug_trimmed = slug[:max_slug].rstrip("-")` (ensure non-empty). Candidate = `f"{prefix}-{slug_trimmed}{suffix}"`.
  - When `tag is None`: suffix is `f"-{seq_str}"`, trim `slug` similarly, candidate = `f"{prefix}-{slug_trimmed}{suffix}"`.
  - Validate `validate_session_name(candidate)` or raise `ValueError`.
- `ARTIFACT_KINDS = ("spec", "solution_key", "oracle", "oracle-draft", "qual", "contract", "closure", "ev", "escalation", "live-decision", "implementer")` (includes `"implementer"` per Ruling `F-17`).
- `format_artifact_id(kind: str, seq: int) -> str`:
  - If `kind not in ARTIFACT_KINDS` or `not isinstance(seq, int)` or `isinstance(seq, bool)` or `seq < 1`: raise `ValueError`.
  - Return `f"{kind}-{seq:03d}"`.
- `format_artifact_filename(kind: str, seq: int) -> str`:
  - Validate `kind` and `seq` as above.
  - `"spec"` -> `f"spec-{seq:03d}.md"`
  - `"solution_key"` -> `f"solution_key-{seq:03d}.patch"`
  - `"oracle"`, `"oracle-draft"`, `"implementer"` -> `f"{kind}-{seq:03d}"`
  - `"qual"`, `"contract"`, `"closure"`, `"ev"`, `"escalation"`, `"live-decision"` -> `f"{kind}-{seq:03d}.json"`.
- `parse_seq_from_name(name: str) -> int | None`:
  - Match `r"^(?:(spec)-([0-9]{3,})\.md|(solution_key)-([0-9]{3,})\.patch|(oracle|oracle-draft|implementer)-([0-9]{3,})|(qual|contract|closure|ev|escalation|live-decision)-([0-9]{3,})\.json)\Z"`.
  - Note: In `test_p06_reconstruct.py` / `S0-R4.6`, sidecar files `spec-001.md.meta.json` may exist alongside `spec-001.md`. Only names matching the regex above return `int(seq_str)`, else `None`.

---

### 4.3 `src/actl/layout.py` (`S0-R3`, `P-S0-03`)

- `ROLES = ("architect", "challenger", "implementer", "curator")`.
- `Layout.__init__(self, root: Path | str | None = None) -> None`:
  - If `root is None`: check `os.environ.get("ACTL_ROOT")`; if set and non-empty, use it; else use `Path(os.environ.get("HOME", str(Path.home()))) / "actl-graph"`.
  - Check `"\x00" in str(root)` -> raise `ValueError("NUL byte in root path")`.
  - Set `self.root: Path = Path(root).resolve()`.
- Helper `_check_tag(tag: str) -> str`:
  - If not `isinstance(tag, str)` or not `validate_sprint_tag(tag)`: raise `ValueError(f"Invalid sprint tag: {tag!r}")`.
  - Return `tag`.
- Helper `_check_role(role: str) -> str`:
  - If `role not in ROLES`: raise `ValueError(f"Unknown role: {role!r}")`.
  - Return `role`.
- Helper `_check_workspace_name(name: str) -> str`:
  - Reject if `not isinstance(name, str)` or `name in ("", ".", "..")` or `"/" in name` or `"\\" in name` or `"\x00" in name` or `any(ord(c) < 0x20 or ord(c) == 0x7F for c in name)`. Raise `ValueError`.
- Properties (`-> Path`):
  - `actl_repo`: `self.root / "actl-repo"`
  - `target_repo`: `self.root / "repos" / "target-repo"`
  - `baseline_file`: `self.root / "baseline.json"`
- Methods (`-> Path`):
  - `sprint_dir(self, tag: str) -> Path`: `self.actl_repo / "specs" / _check_tag(tag)`
  - `runs_dir(self, tag: str) -> Path`: `self.sprint_dir(tag) / "runs"`
  - `logs_dir(self, tag: str) -> Path`: `self.runs_dir(tag) / "logs"`
  - `turns_dir(self, tag: str) -> Path`: `self.runs_dir(tag) / "turns"`
  - `state_file(self, tag: str) -> Path`: `self.runs_dir(tag) / "state.json"`
  - `state_lock(self, tag: str) -> Path`: `self.runs_dir(tag) / "state.lock"`
  - `sessions_file(self, tag: str) -> Path`: `self.runs_dir(tag) / "sessions.tsv"`
  - `sprint_toml(self, tag: str) -> Path`: `self.sprint_dir(tag) / "sprint.toml"`
  - `handoff(self, tag: str) -> Path`: `self.root / "handoff" / _check_tag(tag)`
  - `inbox(self, tag: str, role: str) -> Path`: `self.handoff(tag) / f"{_check_role(role)}-inputs"`
  - `outbox(self, tag: str, role: str) -> Path`: `self.handoff(tag) / f"{_check_role(role)}-outputs"`
  - `workspace(self, name: str, tag: str | None = None) -> Path`:
    - Validate `_check_workspace_name(name)`.
    - If `tag is not None`: validate `_check_tag(tag)` and return `self.root / "workspaces" / tag / name`.
    - Else: return `self.root / "workspaces" / name`.
  - `homes(self, role: str) -> Path`: `self.root / "homes" / _check_role(role)`
- Directory Creation (`ensure_base_tree` and `ensure_sprint_tree`):
  - Always call `os.chmod(path, mode)` explicitly after `mkdir(parents=True, exist_ok=True)` so permissions are applied regardless of process `umask` (`test_base_tree_and_modes_applied_regardless_of_umask` tests with `os.umask(0o077)`!).
  - `ensure_base_tree(self) -> None`:
    - Create `self.root` (`0o755`).
    - Create `self.actl_repo` and `os.chmod(self.actl_repo, 0o700)`.
    - Create `self.actl_repo / "specs"` (`0o755`).
    - For `d` in `("handoff", "workspaces", "repos", "homes")`: create `self.root / d` and `os.chmod(self.root / d, 0o755)`.
    - For `role` in `ROLES`: create `self.homes(role)` and `os.chmod(self.homes(role), 0o755)`.
    - Do **NOT** create `repos/target-repo`.
  - `ensure_sprint_tree(self, tag: str) -> None`:
    - Validate `_check_tag(tag)`.
    - Call `self.ensure_base_tree()`.
    - For `p` in `(self.sprint_dir(tag), self.runs_dir(tag), self.logs_dir(tag), self.turns_dir(tag), self.handoff(tag))`: create `p` and `os.chmod(p, 0o755)`.
    - For `role` in `ROLES`:
      - Create `self.inbox(tag, role)` and `os.chmod(self.inbox(tag, role), 0o750)`.
      - Create `self.outbox(tag, role)` and `os.chmod(self.outbox(tag, role), 0o770)`.

---

### 4.4 `src/actl/hashing.py` (`S0-R6`, `P-S0-07`)

- `file_sha256(path: Path | str) -> str`:
  - Use `p = Path(path)`. Use `st = os.lstat(p)` (raises `FileNotFoundError` if missing).
  - If `stat.S_ISLNK(st.st_mode)` or `not stat.S_ISREG(st.st_mode)`: raise `ValueError(f"Not a regular file: {path}")`.
  - Read raw bytes and return `hashlib.sha256(p.read_bytes()).hexdigest().lower()`.
- `manifest_sha256(directory: Path | str) -> str`:
  - `root = Path(directory)`. Use `st = os.lstat(root)` (raises `FileNotFoundError` if missing).
  - If `stat.S_ISLNK(st.st_mode)` or `not stat.S_ISDIR(st.st_mode)`: raise `ValueError(f"Not a non-symlink directory: {directory}")`.
  - Walk `root` without following symlinks (`os.walk(root, followlinks=False)`):
    - Check every entry in `dirnames` and `filenames` via `os.lstat(full_path)`.
    - If any entry is a symlink (`stat.S_ISLNK`) or special file (neither `stat.S_ISDIR` nor `stat.S_ISREG`, e.g. FIFO/socket/device): raise `ValueError`.
    - For each regular file (`stat.S_ISREG`):
      - `rel = os.path.relpath(full_path, root).replace(os.sep, "/")`
      - `exec_flag = "x" if (entry_stat.st_mode & 0o111) != 0 else "-"`
      - `digest = hashlib.sha256(Path(full_path).read_bytes()).hexdigest().lower()`
      - Collect `(rel.encode("utf-8"), f"{rel}\0{exec_flag}\0{digest}\n".encode("utf-8"))`.
  - Sort rows by `row[0]` (bytewise UTF-8 path order), join `row[1]`, and return `hashlib.sha256(joined).hexdigest().lower()`.
- `canonical_json(obj: Any) -> bytes`:
  - Recursively validate `obj` before/during serialization:
    - Any `dict` with a key where `not isinstance(k, str)` -> raise `TypeError("Dictionary keys must be strings")`.
    - Any `float` where `math.isnan(v) or math.isinf(v)` -> raise `ValueError("NaN/Infinity not allowed")`.
    - Any `str` containing lone surrogates (`any(0xD800 <= ord(ch) <= 0xDFFF for ch in s)`) -> raise `ValueError("Surrogates not allowed")`.
  - Serialize via `s = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)`.
  - Return `s.encode("utf-8")`.
- `json_sha256(obj: Any) -> str`:
  - Return `hashlib.sha256(canonical_json(obj)).hexdigest().lower()`.

---

### 4.5 `src/actl/schemas.py` & `schemas/*.json` (`S0-R7`, `S0-R14`, `P-S0-08`, `P-S0-15`)

#### Critical Verification Step for Schemas
**Before finalizing `schemas/*.json` and `src/actl/schemas.py`, inspect:**
- `fixtures/golden/artifacts/valid/*/*.json` (all 24 valid documents)
- `fixtures/golden/artifacts/invalid/index.json` and `fixtures/golden/artifacts/invalid/*/*.json` (all 59 invalid documents and their exact `expect_paths`!).

#### Rulings Applied (`spec-S0-rulings.md`)
- **C-1:** All SHA fields (`base_sha` in `sprint.json`, `qual.json`, `contract.json`, and `head` in `ev.json`) require `^[0-9a-f]{40}$` (40 lowercase hex chars). All SHA-256 fields require `^[0-9a-f]{64}$`.
- **C-2:** `owner_review_triggers` in `sprint.json` and `sprint-proposal.json` is an array of strings with enum `["plan_deviation", "budget_exceeded", "critical_tripwire", "manual_flag"]`.
- **C-3:** `ev.exit_code` in `ev.json` is `{"type": ["integer", "null"], "minimum": 0, "maximum": 255}`.

#### `schemas/*.json` Requirements (`test_schema_files_shape`)
Create all 12 files in `schemas/`:
`common.json`, `state.json`, `sprint.json`, `sprint-proposal.json`, `closure.json`, `ev.json`, `qual.json`, `contract.json`, `oracle-decision.json`, `prior_attempt.json`, `meta.json`, `attempt.json`.
1. Every schema file MUST have `"$schema": "https://json-schema.org/draft/2020-12/schema"`.
2. Every schema file except `common.json` MUST have top-level `"additionalProperties": false`.
3. `ev.json`, `qual.json`, and `contract.json` MUST reference `"common.json#/$defs/artifact_meta"` (the literal substring `"artifact_meta"` must appear in their file text).
4. `closure.json` MUST NOT have `"kind"`, `"seq"`, or `"parent"` in its top-level `"required"` list (they are optional properties in `closure.json`, with `seq` integer $\ge 1$, `kind` const `"closure"`, `parent` string or null; if any one of `kind`, `seq`, `parent` is provided or check invalid cases in `fixtures/golden/artifacts/invalid/closure/` to see what `closure` invalid fixtures test!).
5. `contract.json` MUST NOT have `"max_attempts"` in its properties.
6. Check `fixtures/golden/artifacts/invalid/index.json` for every single case across all 11 kinds (`state`, `sprint`, `sprint-proposal`, `closure`, `ev`, `qual`, `contract`, `oracle-decision`, `prior_attempt`, `meta`, `attempt`) and make sure both `schemas/*.json` and `validate(kind, obj)` produce the exact `expect_paths` in `index.json`.

#### In-Tree Validator (`validate(kind: str, obj: Any) -> list[dict[str, str]]`)
- **NEVER import `jsonschema`**.
- `VALID_KINDS = ("common", "state", "sprint", "sprint-proposal", "closure", "ev", "qual", "contract", "oracle-decision", "prior_attempt", "meta", "attempt")`.
- If `kind not in VALID_KINDS`: raise `ValueError(f"Unknown schema kind: {kind}")`.
- Pointer format (`INTERFACES.md` 1.5):
  - Root path is `"/"`.
  - Escape token: `tok.replace("~", "~0").replace("/", "~1")`.
  - Child pointer: `f"/{esc}"` if `parent == "/"` else `f"{parent}/{esc}"`.
  - If root `obj` is not a `dict` (e.g. `None`, `int`, `str`, `list`, `bool`, `float`): return `[{"path": "/", "message": "Root value must be a JSON object"}]`.
  - Remember: in Python `isinstance(True, int)` is `True`! When checking JSON `"integer"`, require `isinstance(x, int) and not isinstance(x, bool)`. When checking JSON `"number"`, require `isinstance(x, (int, float)) and not isinstance(x, bool) and not (isinstance(x, float) and (math.isnan(x) or math.isinf(x)))`.
  - When a `required` property `prop` is missing on an object at `ptr`, report `{"path": child_ptr(ptr, prop), "message": f"Missing required property: {prop}"}`.
  - When an `additionalProperties: false` violation occurs for key `k` on an object at `ptr`, report `{"path": child_ptr(ptr, k), "message": f"Additional property not allowed: {k}"}`.
  - Sort and deduplicate returned errors by `(e["path"], e["message"])`.

#### `load_expected(expected_dir: Path | str | None = None) -> dict[str, Any]` (`S0-R14`, `P-S0-15`)
- Default `expected_dir`: `REPO_ROOT / "fixtures" / "golden" / "expected.d"`.
- If `not Path(expected_dir).is_dir()`: raise `FileNotFoundError`.
- Glob `*.json` sorted in lexical filename order (`sorted(Path(expected_dir).glob("*.json"), key=lambda p: p.name)`).
- Initialize `base_sha = None`, `cases: dict[str, Any] = {}`, `responses: dict[str, Any] = {}`.
- For each file:
  - Parse JSON (on `json.JSONDecodeError` or non-`dict` root, raise `ValueError`).
  - If `"base_sha"` in doc:
    - If `base_sha is not None` or `not isinstance(doc["base_sha"], str)`: raise `ValueError("Duplicate or invalid base_sha")`.
    - `base_sha = doc["base_sha"]`
  - If `"cases"` in doc:
    - If `not isinstance(doc["cases"], dict)`: raise `ValueError`.
    - For `k, v` in `doc["cases"].items()`:
      - If `k in cases`: raise `ValueError(f"Duplicate case key: {k}")`.
      - `cases[k] = v`
  - If `"responses"` in doc:
    - If `not isinstance(doc["responses"], dict)`: raise `ValueError`.
    - For `k, v` in `doc["responses"].items()`:
      - If `k in responses`: raise `ValueError(f"Duplicate response key: {k}")`.
      - `responses[k] = v`
- Return `{"base_sha": base_sha, "cases": cases, "responses": responses}`.

#### `StepResult` dataclass (`src/actl/schemas.py`)
```python
@dataclass
class StepResult:
    id: str
    cmd: str
    exit_code: int
    output_sha256: str
    output_tail: str = ""
    duration_ms: int = 0
    failing_line: str | None = None

    def to_ev_step(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cmd": self.cmd,
            "exit_code": self.exit_code,
            "output_sha256": self.output_sha256,
        }
```

---

### 4.6 `src/actl/seq.py` (`S0-R5`, `P-S0-05`, `P-S0-06`)

- **Thread-Local Re-entrant `state_lock(layout: Layout, tag: str) -> Iterator[None]` (`F-24`, `F-25`, `F-27`):**
  - Validate `tag` via `layout.sprint_dir(tag)`.
  - If `not layout.sprint_dir(tag).is_dir()`: raise `FileNotFoundError(f"Sprint dir missing: {tag}")`.
  - Maintain a `threading.local()` instance storing `locks: dict[str, tuple[int, int]]` mapping `str(lock_path)` to `(fd, depth)`.
  - Register `os.register_at_fork(after_in_child=...)` to clear the thread-local state in forked child processes (closing any inherited lock fds so children must re-open and re-acquire `flock`).
  - On entry (`depth == 0`):
    - Ensure `layout.runs_dir(tag)` exists.
    - Open `lock_path = layout.state_lock(tag)` with `os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)`. (Raises `OSError` if `lock_path` is a directory or unopenable).
    - Call `fcntl.flock(fd, fcntl.LOCK_EX)`.
    - Store `(fd, 1)` in thread-local storage.
  - On re-entrant entry (`depth > 0`): increment `depth`.
  - In `finally`: decrement `depth`; when `depth == 0`, call `fcntl.flock(fd, fcntl.LOCK_UN)` and `os.close(fd)` and remove from thread-local dict.
- **Atomic File Writing Helper:**
  - Write to a unique temp file in the same directory (`f".{target.name}.tmp.{os.getpid()}.{threading.get_ident()}"`), `f.flush()`, `os.fsync(f.fileno())`, close, `os.replace(tmp, target)`, then open the parent directory `os.open(parent, os.O_RDONLY)` and `os.fsync(dir_fd)` + `os.close(dir_fd)`.
- **`reserve(layout: Layout, tag: str, kind: str) -> int`:**
  - Validate `tag` via `layout.sprint_dir(tag)` (raises `ValueError` on bad tag).
  - Validate `kind` via `format_artifact_id(kind, 1)` (raises `ValueError` on unknown kind; `"implementer"` is valid!).
  - If `not layout.state_file(tag).is_file()`: raise `FileNotFoundError(f"State file missing for {tag}")`.
  - Inside `with state_lock(layout, tag):`:
    - Read `state = read_state(layout, tag)`.
    - Read `hw_path = layout.runs_dir(tag) / "seq.highwater"`: if present, parse `int(hw_path.read_text().strip())`, else `0`.
    - `next_seq = max(int(state.get("seq", 0)), hw) + 1`.
    - Atomically write `f"{next_seq}\n"` to `hw_path` (with fsync + dir fsync) **before** updating `state.json`.
    - Set `state["seq"] = next_seq`.
    - Atomically write `canonical_json(state)` (or formatted JSON) to `layout.state_file(tag)` (with fsync + dir fsync).
    - Return `next_seq`.
- **`read_state(layout: Layout, tag: str) -> dict[str, Any]`:**
  - `sf = layout.state_file(tag)`. If `not sf.is_file()`: raise `FileNotFoundError`.
  - Parse `json.loads(sf.read_text(encoding="utf-8"))` (raise `ValueError` on JSON error).
- **`update_state(layout: Layout, tag: str, updates: dict[str, Any]) -> dict[str, Any]`:**
  - If `"seq" in updates`: raise `ValueError("seq cannot be modified via update_state")`.
  - Inside `with state_lock(layout, tag):`:
    - `state = read_state(layout, tag)`
    - Merge `updates` into `state` (recursively merging nested dicts `"attempts"` and `"grants"`).
    - Validate `errs = schemas.validate("state", state)`; if `errs`: raise `ValueError(f"Invalid state update: {errs}")`.
    - Atomically write `state` to `layout.state_file(tag)`.
    - Return `state`.
- **`reconstruct(layout: Layout, tag: str) -> int` (`P-S0-06`):**
  - Validate `tag` via `layout.sprint_dir(tag)`.
  - If `not layout.sprint_dir(tag).is_dir()`: raise `FileNotFoundError`.
  - Inside `with state_lock(layout, tag):`:
    - Scan for highest `seq`:
      1. `runs/seq.highwater` (if exists and valid int).
      2. Every file/dir in `layout.sprint_dir(tag)` via `parse_seq_from_name(p.name)`.
      3. Every file/dir in `layout.runs_dir(tag)` via `parse_seq_from_name(p.name)`.
      4. Every file two levels under `layout.handoff(tag)` (`handoff(tag)/*/*`) via `parse_seq_from_name(p.name)`.
      5. Every dir in `layout.root / "workspaces" / tag` via `parse_seq_from_name(p.name)`.
    - Reconstruct `state.json` (even if `state.json` was deleted!):
      - Start from existing `state.json` if readable and valid, else initialize defaults:
        - `run_id = "run-" + hashlib.sha256(tag.encode("utf-8")).hexdigest()[:12]`
        - `sprint_tag = tag`
        - `seq = max_seq`
        - `epoch = 1`
        - `status = "draft"`
        - `active_stage = None`
        - `active_spec = None`, `active_solution_key = None`, `active_oracle_draft = None`, `active_oracle = None`, `active_contract = None`
        - `attempts = {"oracle": 0, "implementer": 0, "live": 0, "curator": 0}`
        - `closures_submitted = 0`, `hard_caps_tripped = 0`
        - `grants = {"oracle": 0, "implementer": 0, "live": 0, "curator": 0}`
        - `tmux_sessions = []`
      - Check `sprint.toml` if present: if `status == "frozen"` and `state["status"] == "draft"`, set `state["status"] = "running"`.
      - Replay artifacts in `sprint_dir(tag)` and `runs_dir(tag)` in ascending `seq` order:
        - `spec-NNN.md`: `active_spec = p.name`
        - `solution_key-NNN.patch`: `active_solution_key = p.name`
        - `oracle-draft-NNN`: `active_oracle_draft = p.name`
        - `oracle-NNN`: `active_oracle = p.name`
        - `qual-NNN.json`: `attempts["oracle"] = max(attempts["oracle"], 1)`
        - `contract-NNN.json`: `active_contract = p.name`; read `epoch` from contract JSON (`state["epoch"] = c.get("epoch", 1)`); if `state["status"] == "draft"`, set `state["status"] = "running"` and `state["active_stage"] = "implementer"`.
      - Set `state["seq"] = max_seq`.
      - Atomically write `f"{max_seq}\n"` to `runs/seq.highwater` and `state` to `layout.state_file(tag)`.
      - Return `max_seq`.

---

### 4.7 `src/actl/scope.py` (`S0-R12`, `P-S0-12`)

- `@dataclass class ScopeRule: kind: str; pattern: str; is_literal: bool; line_no: int`
- `parse(text: str) -> list[ScopeRule]`:
  - If `not isinstance(text, str)`: raise `ValueError`.
  - Iterate `enumerate(text.splitlines(), start=1)`:
    - Strip trailing horizontal/vertical whitespace `line = raw_line.rstrip()`.
    - If `line.strip() == ""` or `line.lstrip().startswith("#")`: continue.
    - Match `m = re.match(r"^(ALLOW|FROZEN):\s+(\S.*)$", line)` (note: must have colon and whitespace and non-empty pattern). If no match: raise `ValueError(f"Line {line_no}: invalid syntax")`.
    - `kind, pat = m.group(1), m.group(2)`
    - Reject if `pat` contains:
      - `"\x00"` or `"\\"` or `"#"` (inline comments rejected!)
      - Starts with `"/"` or ends with `"/"` or contains `"//"`
      - Any char in `"?[]{}"`
      - Any segment in `pat.split("/")` equal to `"."` or `".."`
      - Any segment containing `"**"` where the segment is not `"**"` (e.g. `a**b` raises `ValueError` at `parse` time!).
    - `is_literal = ("*" not in pat)`
    - Append `ScopeRule(kind=kind, pattern=pat, is_literal=is_literal, line_no=line_no)`.
  - Return `rules`.
- Glob matching helper `_glob_match(pattern: str, path: str) -> bool`:
  - Split `pat_segs = pattern.split("/")` and `path_segs = path.split("/")`.
  - Segment matcher `_seg_match(p_seg: str, s_seg: str) -> bool`:
    - Convert `*` in `p_seg` to `[^/]*` (`re.escape` everything else) and `re.fullmatch`. Note: `*` matches leading `.` (e.g. `api/*.py` matches `api/.hidden.py`).
  - Recursive/DP segment match:
    - If `pat_segs[i] == "**"`: matches 0 or more `path_segs` (so `src/**/gen.py` matches both `src/gen.py` and `src/a/b/gen.py`).
- Internal `_match_unchecked(rules: list[ScopeRule], path: str) -> str`:
  1. If any rule has `r.kind == "ALLOW" and r.is_literal and r.pattern == path`: return `"allowed"`.
  2. If any rule has `r.kind == "FROZEN" and _glob_match(r.pattern, path)`: return `"frozen"`.
  3. If any rule has `r.kind == "ALLOW" and not r.is_literal and _glob_match(r.pattern, path)`: return `"allowed"`.
  4. Return `"denied"`.
- `validate(rules: list[ScopeRule]) -> list[str]`:
  - Returns list of error strings (`[]` if valid).
  - Check:
    1. At least one `r.kind == "ALLOW"` exists.
    2. At least one rule has `r.kind == "FROZEN" and r.pattern == "test/**"`.
    3. No literal-vs-literal conflict (`ALLOW` and `FROZEN` both `is_literal` with identical `pattern`).
    4. Syntax/metacharacter validation on each rule's `pattern` (in case `ScopeRule` was constructed manually).
    5. Blanket/sentinel probe: let `allow_globs = [r for r in rules if r.kind == "ALLOW" and not r.is_literal]`. If `_match_unchecked(allow_globs, "__root_probe__") == "allowed"` or `_match_unchecked(allow_globs, "test/__probe__.py") == "allowed"` or `_match_unchecked(allow_globs, "test/sub/__probe__.py") == "allowed"`: append error string.
- `match(rules: list[ScopeRule], path: str) -> str`:
  - Validate `path`: must be `str`, non-empty, not starting/ending with `"/"`, no `"//"`, no `"\\"`, no `"\x00"`, no `"."` or `".."` segments. Else raise `ValueError`.
  - If `validate(rules) != []`: raise `ValueError("Invalid scope ruleset")`.
  - Return `_match_unchecked(rules, path)`.

---

### 4.8 `config/graph.toml` & `src/actl/sprint.py` (`S0-R4`, `S0-R8`, `P-S0-04`, `P-S0-09`)

#### `config/graph.toml`
Must contain a comment with the word `illustrative`, must NOT contain `live_run`, and must match `test_p09_defaults.py`:
```toml
# Installation defaults for actl sprints (Design section 4.1 illustrative values)
approval_live_run = "architect"
 owner_review_triggers = []
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
```
*(Ensure no leading space before `owner_review_triggers`.)*

#### `src/actl/sprint.py`
- `load_graph_defaults(config_path: Path | str | None = None) -> dict[str, Any]`:
  - Default `config_path`: `REPO_ROOT / "config" / "graph.toml"` (determine `REPO_ROOT` from `Path(__file__).resolve().parents[2]`).
  - If `not Path(config_path).is_file()`: raise `FileNotFoundError`.
  - Parse with `tomllib.loads(Path(config_path).read_text(encoding="utf-8"))` (raise `ValueError` on `tomllib.TOMLDecodeError`).
- `load_sprint_toml(layout: Layout, tag: str) -> dict[str, Any]`:
  - `p = layout.sprint_toml(tag)`. If `not p.is_file()`: raise `FileNotFoundError`.
  - Parse with `tomllib.loads(p.read_text(encoding="utf-8"))` (raise `ValueError` on `tomllib.TOMLDecodeError`).
- `init_target(layout: Layout, target: str) -> Path`:
  - Validate `target` is non-empty string without NUL.
  - Check if `target` is a valid git repository (`git rev-parse --git-dir` or `git ls-remote`); if not, raise `ValueError("Not a git repository")`.
  - Resolve `target_norm = str(Path(target).resolve()) if Path(target).exists() else target`.
  - If `layout.target_repo.exists()`:
    - Check if `layout.target_repo / ".git"` exists and its `remote.origin.url` resolved path equals `target_norm`. If identical, return `layout.target_repo` (idempotent!). Otherwise raise `ValueError("target_repo already exists with a different origin")`.
  - Call `layout.ensure_base_tree()`.
  - Clone with hermetic git (`GIT_CONFIG_GLOBAL=/dev/null`, `GIT_CONFIG_SYSTEM=/dev/null`, `-c core.hooksPath=/dev/null`):
    - If `Path(target).exists()`: `git -c core.hooksPath=/dev/null clone -q --local --no-hardlinks <target_norm> <layout.target_repo>`
    - Else: `git -c core.hooksPath=/dev/null clone -q <target> <layout.target_repo>`
  - Return `layout.target_repo`.
- `create_sprint(layout: Layout, slug: str, spec_path: Path | str | None = None) -> dict[str, Any]`:
  - Validate `validate_slug(slug)` (raise `ValueError` if invalid, before creating any directories!).
  - If `spec_path is not None`:
    - `sp = Path(spec_path)`
    - If `not sp.is_file()`: raise `FileNotFoundError(f"Spec file not found: {spec_path}")`.
  - If `not (layout.target_repo / ".git").exists()`: raise `FileNotFoundError("Target repo not initialized")`.
  - Mint `tag = mint_sprint_tag(slug)`.
  - If `layout.sprint_dir(tag).exists()`: raise `ValueError(f"Sprint already exists: {tag}")`.
  - Get `base_sha` = 40-char output of `git -C <layout.target_repo> rev-parse HEAD`.
  - Load defaults via `defaults = load_graph_defaults()`.
  - Call `layout.ensure_sprint_tree(tag)`.
  - Write `runs/sessions.tsv` with header:
    `seq\tsession\trole\tengine\tmodel\tmodel_family\tturns\ttool_calls\ttokens\tcost_usd\texit_code\taccepted_items\tescalation_alerts_sent\n`
  - Write initial `runs/state.json`:
    ```python
    run_id = "run-" + hashlib.sha256(tag.encode("utf-8")).hexdigest()[:12]
    state = {
        "active_contract": None,
        "active_oracle": None,
        "active_oracle_draft": None,
        "active_solution_key": None,
        "active_spec": None,
        "active_stage": None,
        "attempts": {"curator": 0, "implementer": 0, "live": 0, "oracle": 0},
        "closures_submitted": 0,
        "epoch": 1,
        "grants": {"curator": 0, "implementer": 0, "live": 0, "oracle": 0},
        "hard_caps_tripped": 0,
        "run_id": run_id,
        "seq": 0,
        "sprint_tag": tag,
        "status": "draft",
        "tmux_sessions": [],
    }
    ```
  - If `spec_path is not None`:
    - `seq_num = seq.reserve(layout, tag, "spec")` (which allocates `1` and writes `runs/seq.highwater` = `"1\n"` and updates `state["seq"] = 1`).
    - Copy `sp` bytes to `layout.sprint_dir(tag) / "spec-001.md"`.
    - Write `layout.sprint_dir(tag) / "spec-001.md.meta.json"` with `{"kind": "spec", "seq": 1, "parent": None, "sha256": file_sha256(sp)}`.
    - Update `state`: `spec_source = "imported"`, `active_spec = "spec-001.md"`, `seq = 1` via `update_state`.
  - Else:
    - `spec_source = "architect_qna"`, `active_spec = None`, `seq_num = 0`.
  - Format `sprint.toml` using values from `defaults` (`load_graph_defaults()`) matching the exact format of `fixtures/golden/expected_text/sprint.toml.tmpl` (inspect `fixtures/golden/expected_text/sprint.toml.tmpl` directly to ensure byte-for-byte identical formatting!).
  - Return:
    ```python
    {
        "sprint_tag": tag,
        "slug": slug,
        "base_sha": base_sha,
        "sprint_dir": str(layout.sprint_dir(tag)),
        "handoff_dir": str(layout.handoff(tag)),
        "spec_source": spec_source,
        "active_spec": active_spec,
        "seq": seq_num,
    }
    ```

---

### 4.9 `src/actl/doctor.py` (`S0-R1`, `P-S0-01`, `P-S0-28`)

`run_doctor(layout: Layout, refresh: bool = False) -> dict[str, Any]`:
- **CRITICAL (`P-S0-28` / `p02_doctor_empty.sh`):**
  - Do **NOT** call `layout.ensure_base_tree()`. Only create `layout.root.mkdir(parents=True, exist_ok=True)` when writing `layout.baseline_file` (`$ACTL_ROOT/baseline.json`). No other files or directories may be created under `$ACTL_ROOT`.
  - Do **NOT** modify anything in the repository (`git status --porcelain` before and after must be identical).
  - **Preserving `proof/out/`:** Running the suites (`run_suite_engines.sh`, `run_suite_session_persistence.sh`, `run_suite_exit_code.sh`) writes logs into `REPO_ROOT / "proof" / "out"`. Before running those suites, check if `proof_out = REPO_ROOT / "proof" / "out"` exists:
    - If `proof_out` did **not** exist before `run_doctor`, remove `proof_out` (`shutil.rmtree`) in a `finally` block after running the suites.
    - If `proof_out` **did** exist before `run_doctor`, snapshot `existing_files = set(p.name for p in proof_out.iterdir())` and the bytes of any non-`P-S0-*` files. In `finally`, unlink any file in `proof_out` whose name was not in `existing_files`, and restore any non-`P-S0-*` file that existed before. (Never unlink or overwrite `P-S0-*.log` because `run_suite_actl_s0.sh` writes to `proof/out/P-S0-*.log` while running `P-S0-01` and `P-S0-28`!).
- **Report Dictionary Keys (`TOP` in `test_p01_doctor.py`):**
  - `version`: Read `(REPO_ROOT / "VERSION").read_text().strip()`. If below `v0.1.4`, append warning.
  - `head_sha`: `git -C REPO_ROOT rev-parse HEAD` stripped.
  - `git_status_porcelain`: `git -C REPO_ROOT status --porcelain` (raw stdout stripped or rstripped).
  - `git_dirty`: `bool(git_status_porcelain.strip())`.
  - `ancestors`: For each sha in `("5cb7f30", "759a0ca", "a9b3a4e", "4da9394")`, run `git -C REPO_ROOT merge-base --is-ancestor <sha> HEAD` -> `returncode == 0` (`bool`).
  - `tool_versions`: Dict with keys `("python3", "git", "tmux", "bash")`:
    - `python3`: output of `python3 --version` ( first line).
    - `git`: output of `git --version` (first line).
    - `tmux`: if `shutil.which("tmux")`, output of `tmux -V` (must start with `"tmux"`), else `None`.
    - `bash`: output of `bash --version` (first line).
  - `python_packages`: `{"pytest": bool, "jsonschema": bool}` (check via `importlib.util.find_spec`).
  - `engine_clis`: For each cli in `("agent", "codex", "claude", "agy", "aider", "vibe")`: `bool(shutil.which(cli))`.
  - `timeout_available`: `bool(shutil.which("timeout") or Path("/usr/bin/timeout").is_file())`.
  - `effective_user`: `getpass.getuser()`.
  - `actl_root`: `str(layout.root)`.
  - `log_dir`: `os.environ.get("ATOOLS_LOG_DIR") or ("/root/.cursor/logs" if Path("/root/.cursor").exists() else str(Path.home() / ".cursor" / "logs"))`.
  - `metadata_dir`: `os.environ.get("ATOOLS_SESSION_DIR") or str(Path.home() / ".cursor" / "sessions")`.
  - `linger_state`: Run `loginctl show-user <effective_user> -p Linger` if `shutil.which("loginctl")` else `"unknown"`.
  - `router_has_read_exit_code`: `bool("def read_exit_code" in (REPO_ROOT / "src" / "router" / "process.py").read_text())`. If `False`, append a warning to `warnings`.
  - `suites`: Dict with keys `("engines", "session_persistence", "exit_code")` mapping to scripts `proof/run_suite_engines.sh`, `proof/run_suite_session_persistence.sh`, `proof/run_suite_exit_code.sh`:
    - Each value is `{"present": bool, "exit_code": int | None, "tail": str}`.
    - If script exists: run `bash <script>` with `stdin=subprocess.DEVNULL` (for `session_persistence`, if `not shutil.which("agent")` or `not shutil.which("tmux")`, still run or record result быстро; keep `tail` to last 20 lines, max 2000 chars). If `exit_code` suite is missing, append a warning.
  - `audit`:
    - Check `audit_script = REPO_ROOT / "audit" / "atools-compliance_audit.sh"`.
    - If missing: `{"present": False, "exit_code": None, "pass": 0, "fail": 0, "skip": 0, "warn": 0, "self_test_exit_code": None, "tail": ""}`.
    - If present: run `bash <audit_script> --cursor` and `bash <audit_script> --self-test`. Parse pass/fail/skip/warn counts from stdout (or default to `0` ints), record `exit_code`, `self_test_exit_code`, `tail` (last 20 lines, $\le 2000$ chars).
  - `installed_sync_diffs`:
    - Keys: `"hooks/pre-commit"`, `"rules/git-safety.md"`, `".cursor/skills/atools-repair/SKILL.md"`.
    - Installed targets:
      - `"hooks/pre-commit"` -> `Path.home() / ".config/git/hooks/pre-commit"`
      - `"rules/git-safety.md"` -> `Path.home() / ".cursor/rules/git-safety.md"`
      - `".cursor/skills/atools-repair/SKILL.md"` -> `Path.home() / ".cursor/skills/atools-repair/SKILL.md"`
    - If installed file is missing: value is `"MISSING"` and add a warning. Else run `diff -u <repo_file> <installed_file>`: `""` if identical, else diff text + add a warning.
  - `warnings`: `list[str]`.
- **Writing `baseline.json`:**
  - Only write `layout.baseline_file` if `not layout.baseline_file.exists()` or `refresh is True` (and only when `tool_versions["tmux"] is not None` and `audit["present"] is True`, or even if written, note that `cmd_doctor` exits `4` when `tmux` is missing or `not audit["present"]`).
- **Exit Code in `cmd_doctor.py`:**
  - Print `json.dumps(report, indent=2)` when `--json` is passed (else human-readable summary).
  - If `report["tool_versions"]["tmux"] is None` or `not report["audit"]["present"]`: return `4` (note: in `test_missing_audit_script_exits_4_and_records_not_found`, `cmd_doctor` must still output `report` as JSON when `--json` is given and return `4`).
  - Else return `0`.

---

### 4.10 `src/actl/cli.py`, `src/actl/next.py`, and `cmd_*.py` (`S0-R10`, `S0-R13`, `P-S0-11`, `P-S0-14`, `P-S0-29`)

#### `src/actl/cli.py`
- `discover_commands(subparsers: argparse._SubParsersAction) -> list[str]`:
  - Locate package directory `Path(__file__).resolve().parent`.
  - Find all `cmd_*.py` files sorted by stem (`sorted(pkg_dir.glob("cmd_*.py"), key=lambda p: p.stem)`).
  - Clear any cached modules in `sys.modules` whose name starts with `"actl.cmd_"` whose file no longer exists, and import/reload `f"actl.{p.stem}"`.
  - If `not hasattr(mod, "register")` or `not callable(mod.register)`: raise `AttributeError(f"{mod.__name__} lacks register(subparsers)")`.
  - Call `mod.register(subparsers)` and append `p.stem`.
  - Return the sorted list of module stems (`["cmd_doctor", "cmd_init", "cmd_next", "cmd_sprint", ...]`).
- `main(argv: list[str] | None = None) -> int`:
  - If `argv is None`: `argv = sys.argv[1:]`.
  - Pre-scan `want_json = ("--json" in argv)`.
  - Build `ArgumentParser(prog="actl")` with `subparsers = parser.add_subparsers(dest="command", required=True)`.
  - Call `discover_commands(subparsers)`.
  - Parse `args = parser.parse_args(argv)`:
    - Catch `SystemExit as exc`:
      - If `exc.code == 0` (e.g. `--help`): return `0`.
      - Otherwise (argparse usage error): if `want_json`, print `json.dumps({"ok": False, "exit_code": 2, "error": "usage error"})` to stdout; return `2`.
  - Instantiate `layout = Layout()`.
  - Execute `rc = args.func(args, layout)` inside `try ... except`:
    - `UsageError as e` -> code `2`, msg `str(e)`
    - `StateIntegrityError as e` -> code `3`, msg `str(e)`
    - `EnvError as e` -> code `4`, msg `str(e)`
    - `SystemExit as e` -> code `e.code if e.code in (0, 1, 2, 3, 4) else 2`
    - `Exception as e` -> code `3`, msg `f"{type(e).__name__}: {e}"`
    - On caught error: if `want_json` (or `getattr(args, "json", False)`), print `json.dumps({"ok": False, "exit_code": code, "error": msg})` to stdout; else print `f"ERROR: {msg}"` to stderr. Return `code`.
  - Ensure `NO_COLOR` is respected: never emit ANSI escape sequences (`\x1b[`) when `os.environ.get("NO_COLOR")` is set (or never emit ANSI at all in Stage 0A).

#### `src/actl/cmd_*.py` Handlers
- `cmd_doctor.py`: registers `doctor [--refresh] [--json]`.
- `cmd_init.py`: registers `init --target <TARGET> [--json]`. Translates `ValueError`/`RuntimeError` from `init_target` into `UsageError` (exit 2). Outputs `{"actl_root": str(layout.root), "target_repo": str(target_repo), "base_sha": base_sha, "created": created_bool}`.
- `cmd_sprint.py`: registers `sprint` with subparser `new <slug> [--spec <FILE>] [--json]`. Translates `ValueError`/`FileNotFoundError` into `UsageError` (exit 2) and `OSError` into `StateIntegrityError` (exit 3).
- `cmd_next.py`: registers `next --sprint <TAG> [--json]`. Calls `decide_next(layout, args.sprint)`. Translates `ValueError`/`FileNotFoundError` into `UsageError` (exit 2).

#### `src/actl/next.py` (`S0-R13.2`, `P-S0-14`, `P-S0-29`)
- `decide_next(layout: Layout, tag: str, session_probe: Callable[[str], dict[str, Any]] | None = None) -> dict[str, str]`:
  - Validate `tag` via `layout.sprint_dir(tag)` (raises `ValueError` on bad tag).
  - If `not layout.sprint_dir(tag).is_dir()` or `not layout.state_file(tag).is_file()`: raise `FileNotFoundError(f"Sprint not found: {tag}")`.
  - Read `state = read_state(layout, tag)`.
  - **Terminal / Hold Precedence (always evaluated BEFORE rules):**
    - If `state.get("status") == "done"`: return `{"action": "done", "command": "", "reason": "Sprint is done"}`.
    - If `state.get("status") == "aborted"`: return `{"action": "aborted", "command": "", "reason": "Sprint is aborted"}`.
    - If `state.get("status") == "hold"`: return `{"action": "hold_owner", "command": "", "reason": "Sprint is on hold for owner review"}`.
  - **Rule Discovery (`src/actl/next_rules/[!_]*.py`):**
    - Find all `.py` files in `Path(__file__).resolve().parent / "next_rules"` whose filename does NOT start with `"_"`.
    - Load each module dynamically (using `importlib.util.spec_from_file_location` with module name `p.stem` or `f"actl.next_rules.{p.stem}"` so dynamic scratch tests in `test_p14_registries.py` and `test_p13_next_rules.py` never suffer from stale `sys.modules` cache!).
    - Sort loaded modules ascending by `(getattr(mod, "PRIORITY", 100), p.stem)`.
    - For each module, call `res = mod.evaluate(layout, tag, session_probe=session_probe)` (or `mod.evaluate(layout, tag)` if 2-arg).
    - If `res is not None`: return `{"action": str(res["action"]), "command": str(res["command"]), "reason": str(res["reason"])}`.
  - Fallback when no rule matches:
    - Return `{"action": "noop", "command": "", "reason": "No matching rule for current sprint state"}`.

---

## 5. Verification Loop Protocol

1. **Syntax & Compile Check:**
   ```bash
   python3 -m compileall -q src/actl
   ```
2. **Fast Iterative Check (using `ONLY` filter):**
   ```bash
   ONLY=P-S0-03,P-S0-04,P-S0-05,P-S0-06,P-S0-07,P-S0-08,P-S0-09,P-S0-11,P-S0-12,P-S0-14,P-S0-15,P-S0-26,P-S0-29 bash proof/run_suite_actl_s0.sh
   ```
3. **Doctor & Additive Checks:**
   ```bash
   ONLY=P-S0-01,P-S0-02,P-S0-28 bash proof/run_suite_actl_s0.sh
   ```
4. **Full Gating Suite & Conformance Gate:**
   ```bash
   bash proof/run_suite_actl_s0.sh
   bash proof/stage0/P-S0-27.sh
   ```
5. **Immutability & Git Hygiene Audit:**
   ```bash
   git diff --name-only main -- proof fixtures test/actl src/actl/INTERFACES.md
   git status
   ```
   - Ensure the diff against immutable paths is completely empty.
   - Commit all new files on `wip/s0a-foundations` with a valid `(WI-S0-R<k>)` tag in the commit message subject.