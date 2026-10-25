# Runbook: Workstream 0B — Detached Session Exit-Code Persistence (`S0-R16`)

* **Workstream:** `0B` (`wip/s0b-exit-code`)
* **Designated Test Suite:** `bash proof/run_suite_exit_code.sh`
* **Additive & Interface Gate Checks:**
  * `ACTL_WORKSTREAM=0B bash proof/stage0/P-S0-02.sh`
  * `ACTL_CHECK_STAGES=0B bash proof/stage0/P-S0-26.sh`
* **Commit Tag Format:** `(WI-S0-R16)` (every commit subject MUST end with `(WI-S0-R16)`, e.g., `feat(router): persist exit code of detached runs (WI-S0-R16)`).

---

## 1. Hard Blast-Radius & Immutability Rules (`PB-2`, `S0-R2.2`)

1. **Single-File Modification Constraint (`P-S0-02.sh`):**
   * Workstream 0B may **ONLY** modify `src/router/process.py`.
   * `ACTL_WORKSTREAM=0B bash proof/stage0/P-S0-02.sh` enforces:
     * Zero added/untracked files (`added` list must be empty).
     * Zero deleted, renamed, or mode-changed files.
     * `modified` file list must be **exclusively** `src/router/process.py`.
2. **Immutable Paths (NEVER touch):**
   * `proof/` (including `proof/run_suite_exit_code.sh` and `proof/stage0/*`)
   * `fixtures/` (including `fixtures/golden/stubs/*`)
   * `test/actl/`
   * `src/actl/INTERFACES.md`
   * `bin/arouter`, `bin/asessions`, `engines/*`, `hooks/*`, `rules/*`, `install.sh`, `README.md`

---

## 2. Normative Requirements (`S0-R16.1` – `S0-R16.6` & `INTERFACES.md` §1.9, §4)

All edits take place inside `src/router/process.py`:

### 2.1 Dynamic Directory Resolution & Public Helpers (`S0-R16.5`, `E9`, `P-S0-26`)

`P-S0-26` (`test/actl/test_p26_interfaces.py`) introspects `router.process` against `src/actl/INTERFACES.md` Section 4:
```json
{"module": "router.process", "name": "get_exit_path", "kind": "function", "stage": "0B", "params": [{"name": "session_name", "type": "str"}], "returns": "Path"},
{"module": "router.process", "name": "read_exit_code", "kind": "function", "stage": "0B", "params": [{"name": "session_name", "type": "str"}], "returns": "int | None"}
```

1. **Dynamic path resolvers:**
   Keep `LOG_DIR` and `METADATA_DIR` at module level for backwards compatibility, and define helpers that resolve `os.environ` dynamically on every call:
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
   ```
   Update `ensure_environment()`, `get_metadata_path()`, `get_log_path()`, `get_running_sessions()`, and `create_runner_script()` to use `_resolve_metadata_dir()` and `_resolve_log_dir()` so changes to `os.environ["ATOOLS_SESSION_DIR"]` or `os.environ["ATOOLS_LOG_DIR"]` within the same Python process (such as in `E9_read_exit_code_helper`) are always honored.

2. **`get_exit_path(session_name: str) -> Path`:**
   * Parameter name MUST be `session_name: str` and return annotation MUST be `-> Path`.
   * Returns `_resolve_metadata_dir() / f"{session_name}.exit"`.

3. **`read_exit_code(session_name: str) -> Optional[int]`:**
   * Parameter name MUST be `session_name: str` and return annotation MUST be `-> Optional[int]` (or `-> int | None`).
   * Reads `get_exit_path(session_name)` as UTF-8 text, strips whitespace, and returns `int(text)` if and only if `re.fullmatch(r"[0-9]+\Z", text)` matches (clean non-negative integer).
   * Returns `None` if the file does not exist, cannot be read, is negative (e.g. `-3`), or contains non-digits (e.g. `12abc`). Never raises.

### 2.2 Runner Script Exit Persistence & Signal Traps (`S0-R16.1`, `E1`–`E5`, `E10`)

In `create_runner_script(...)`:
1. Compute:
   ```python
   meta_dir = _resolve_metadata_dir()
   meta_dir.mkdir(parents=True, exist_ok=True)
   runner_path = meta_dir / f"{session_name}.run.sh"
   meta_path = get_metadata_path(session_name)
   exit_path = get_exit_path(session_name)
   exit_tmp = meta_dir / f"{session_name}.exit.tmp"
   ```
2. In the generated bash script:
   * `cleanup()` MUST capture `local ec=$?` as its **very first statement**.
   * Write `$ec` followed by a newline (`printf '%s\n' "$ec"`) to `exit_tmp` and atomically rename it onto `exit_path` (`mv -f`), **before** removing `runner_path` and `meta_path`.
   * Register `trap cleanup EXIT` and explicit signal traps `trap 'exit 143' TERM`, `trap 'exit 129' HUP`, and `trap 'exit 130' INT` so an externally signalled runner never records `0` (`F16`, `E10`).

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

### 2.3 Metadata Cleanup & Stale Pruning Preservation (`S0-R16.2`, `E5`)

* `cleanup_session_metadata(session_name)` and the stale `.json` loop in `get_running_sessions()` MUST only remove `<session>.json` and MUST NEVER delete `<session>.exit`.

### 2.4 Pre-Spawn & Spawn-Failure Scrubbing (`S0-R16.3`, `E6`, `E7`)

In `spawn_detached_session(...)`:
1. Before creating the runner script / launching `tmux` (right next to where `log_file` is unlinked), delete any stale `<session>.exit` and `<session>.exit.tmp`:
   ```python
   exit_path = get_exit_path(session_name)
   exit_tmp = exit_path.with_suffix(".exit.tmp")
   for p in (exit_path, exit_tmp):
       try:
           if p.exists():
               p.unlink()
       except Exception:
           pass
   ```
2. In the `if res.returncode != 0:` branch (when `tmux new-session` fails), also unlink `exit_path` and `exit_tmp` alongside `runner_path` and `cleanup_session_metadata(session_name)`.

### 2.5 Unconditional Overwrite on `arouter kill` (`S0-R16.4`, `E7`, `E8`)

In `kill_session(session_name: str, manual: bool = False) -> int`:
1. Add helpers `_record_exit` and `_wait_pids_gone`:
   ```python
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


   def _wait_pids_gone(pids: List[str], timeout: float = 2.0) -> bool:
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
2. In `kill_session()`:
   * After sending `kill -15`, running `tmux kill-session`, and sending `kill -9` to `pids`:
     * Wait up to 2.0 seconds for `pids` to terminate via `_wait_pids_gone(pids, timeout=2.0)`.
     * If `_wait_pids_gone(pids, timeout=2.0)` returns `True`: call `_record_exit(session_name, 143, overwrite=True)` so `<session>.exit` is guaranteed to hold `143` (and no `.exit.tmp` remains).
     * If `_wait_pids_gone(pids, timeout=2.0)` returns `False`: unlink `get_exit_path(session_name)` and `get_exit_path(session_name).with_suffix(".exit.tmp")` so a stuck process is classified as `session_lost`.
   * Note: If `res_kill.returncode != 0` matches `["no server running", "can't find session", "no current target", "server exited unexpectedly"]` because the session exited right after receiving `kill -15`, still run the `_wait_pids_gone(pids)` + `_record_exit(session_name, 143, overwrite=True)` logic before returning `0` so `.exit` is never missed on `arouter kill`.

---

## 3.Gating Checks Matrix (`proof/run_suite_exit_code.sh`)

| Check ID | Test Function | Expected Behavior |
|---|---|---|
| `E1_exit_zero` | `t_zero` | Detached `OK` run writes `0\n` to `e1-ok.exit` |
| `E2_exit_nonzero` | `t_nonzero` | Detached `EXIT7` run writes `7\n` to `e2-7.exit` |
| `E3_exit_timeout_124` | `t_timeout` | Detached `SLEEP` with `-t 2s` times out and writes `124\n` to `e3-to.exit` |
| `E4_exit_file_format` | `t_format` | `.exit` is 1 line, matches `^[0-9]+$`, and no `*.exit.tmp` files exist |
| `E5_runner_removed_exit_kept` | `t_cleanup` | `.run.sh` and `.json` are deleted on exit while `.exit` remains |
| `E6_stale_exit_replaced` | `t_stale` | Pre-existing `99` in `.exit` and `.exit.tmp` are scrubbed and replaced by `0` |
| `E7_no_exit_while_running` | `t_running` | `.exit` does not exist while `SLEEP` is running, and exists after `arouter kill` |
| `E8_kill_records_signal_exit` | `t_kill` | `arouter kill` records integer $\ge 128$ (`143`) in `.exit` |
| `E9_read_exit_code_helper` | `t_helper` | `router.process.read_exit_code` and `get_exit_path` handle valid, missing, negative, and corrupt files |
| `E10_signalled_runner_never_zero` | `t_signalled` | External `SIGTERM` to runner and child records `129`, `130`, or `143` (never `0`) |

---

## 4. Verification Loop Protocol

1. **Syntax Check:**
   ```bash
   python3 -m py_compile src/router/process.py
   ```
2. **Run Designated Exit-Code Suite (E1–E10):**
   ```bash
   bash proof/run_suite_exit_code.sh
   ```
3. **Run Interface & Additive Conformance Gates:**
   ```bash
   ACTL_CHECK_STAGES=0B bash proof/stage0/P-S0-26.sh
   ACTL_WORKSTREAM=0B bash proof/stage0/P-S0-02.sh
   ```
4. **Run Pre-Existing Suite & Compliance Audit:**
   ```bash
   bash proof/run_suite_engines.sh
   bash audit/atools-compliance_audit.sh --cursor
   bash audit/atools-compliance_audit.sh --self-test
   ```
5. **Git Status & Commit Check:**
   ```bash
   git status
   git diff --name-status main
   ```
   * Verify `M src/router/process.py` is the **only** change.
   * Commit on `wip/s0b-exit-code` with `(WI-S0-R16)` at the end of the commit subject.