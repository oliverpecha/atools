"""
Process and session management module for arouter.
Supervises headless tmux persistence, runner execution, metadata, and dual logging.
"""

import json
import os
import re
import select
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

LOG_DIR = Path(os.environ.get("ATOOLS_LOG_DIR", "/root/.cursor/logs" if Path("/root/.cursor").exists() else Path.home() / ".cursor" / "logs"))
METADATA_DIR = Path(os.environ.get("ATOOLS_SESSION_DIR", Path.home() / ".cursor" / "sessions"))


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


def ensure_environment() -> None:
    """Initialize directories and enable systemd user lingering."""
    _resolve_log_dir().mkdir(parents=True, exist_ok=True)
    _resolve_metadata_dir().mkdir(parents=True, exist_ok=True)
    enable_linger()


def enable_linger() -> None:
    """Ensure systemd user lingering is enabled for unattended background runs."""
    user = os.environ.get("USER", "root")
    try:
        subprocess.run(
            ["loginctl", "enable-linger", user],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        pass


def get_metadata_path(session_name: str) -> Path:
    return _resolve_metadata_dir() / f"{session_name}.json"


def get_log_path(session_name: str) -> Path:
    return _resolve_log_dir() / f"{session_name}.log"


def get_exit_path(session_name: str) -> Path:
    return _resolve_metadata_dir() / f"{session_name}.exit"


def read_exit_code(session_name: str) -> Optional[int]:
    path = get_exit_path(session_name)
    try:
        text = path.read_text(encoding="utf-8").strip()
    except Exception:
        return None
    if re.fullmatch(r"[0-9]+\Z", text):
        return int(text)
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


def save_session_metadata(
    session_name: str,
    tier: str,
    model: str,
    engine: str = "cursor",
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    ensure_environment()
    data: Dict[str, Any] = {
        "session": session_name,
        "tier": tier,
        "model": model,
        "engine": engine,
        "start_time": time.time(),
        "log_file": str(get_log_path(session_name)),
    }
    if extra:
        data.update(extra)
    try:
        get_metadata_path(session_name).write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def load_session_metadata(session_name: str) -> Optional[Dict[str, Any]]:
    meta_path = get_metadata_path(session_name)
    if meta_path.is_file():
        try:
            return json.loads(meta_path.read_text())
        except Exception:
            pass
    return None


def cleanup_session_metadata(session_name: str) -> None:
    meta_path = get_metadata_path(session_name)
    try:
        if meta_path.exists():
            meta_path.unlink()
    except Exception:
        pass


def list_active_tmux_sessions() -> Dict[str, float]:
    """Return dict mapping active tmux session names to their creation timestamp."""
    if not shutil.which("tmux"):
        return {}
    try:
        res = subprocess.run(
            ["tmux", "list-sessions", "-F", "#{session_name}|#{session_created}"],
            capture_output=True,
            text=True,
            check=False,
        )
        if res.returncode != 0:
            return {}
        sessions: Dict[str, float] = {}
        for line in res.stdout.strip().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("|", 1)
            name = parts[0]
            created = float(parts[1]) if len(parts) > 1 and parts[1].isdigit() else time.time()
            sessions[name] = created
        return sessions
    except Exception:
        return {}


def format_duration(seconds: float) -> str:
    secs = int(max(0, seconds))
    hours, remainder = divmod(secs, 3600)
    minutes, s = divmod(remainder, 60)
    if hours > 0:
        return f"{hours}h {minutes:02d}m {s:02d}s"
    elif minutes > 0:
        return f"{minutes}m {s:02d}s"
    else:
        return f"{s}s"


def get_running_sessions() -> List[Dict[str, Any]]:
    """Return runtime metadata for all currently running agent sessions."""
    active_tmux = list_active_tmux_sessions()
    now = time.time()
    results = []

    # Clean up stale metadata files (never delete .exit)
    meta_dir = _resolve_metadata_dir()
    if meta_dir.exists():
        for meta_file in meta_dir.glob("*.json"):
            sess_name = meta_file.stem
            if sess_name not in active_tmux:
                try:
                    meta_file.unlink()
                    boot_file = meta_file.with_name(f"{sess_name}.boot.sh")
                    if boot_file.exists():
                        boot_file.unlink()
                except Exception:
                    pass

    for sess_name, created_ts in active_tmux.items():
        meta = load_session_metadata(sess_name)
        log_file = str(get_log_path(sess_name))
        
        # Verify session belongs to arouter
        if not meta and not Path(log_file).exists() and not sess_name.startswith("arun-"):
            continue

        if meta:
            tier = meta.get("tier", "-")
            model = meta.get("model", "-")
            engine = meta.get("engine", "-")
            start_ts = meta.get("start_time", created_ts)
        else:
            tier = "-"
            model = "-"
            engine = "-"
            start_ts = created_ts

        elapsed_sec = now - start_ts
        prompt = meta.get("prompt", "") if meta else ""
        results.append({
            "session": sess_name,
            "tier": tier,
            "model": model,
            "engine": engine,
            "elapsed": format_duration(elapsed_sec),
            "log_file": log_file,
            "prompt": prompt,
        })
    return results


def print_sessions() -> int:
    """Display table of running arouter sessions."""
    sessions = get_running_sessions()
    if not sessions:
        print("No active arouter sessions.")
        return 0

    header = f"{'SESSION':<28} {'TIER':<10} {'MODEL':<20} {'ELAPSED':<12} {'LOG'}"
    print(header)
    print("-" * len(header))
    for s in sessions:
        print(f"{s['session']:<28} {s['tier']:<10} {s['model']:<20} {s['elapsed']:<12} {s['log_file']}")
    return 0


ANSI_SANITIZE_RE = re.compile(
    r'\x1b\[3J'
    r'|\x1b\](?:10|11|12);\?[^\x07\x1b]*(?:\x07|\x1b\\)'
    r'|\x1b\[\?1004[hl]'
)


def stream_session(session_name: str, watchdog_timeout: str = "", kill_grace: str = "3s") -> int:
    """Stream session output directly to the active terminal preserving scrollback with tab title HUD and Ctrl+C intercept."""
    meta = load_session_metadata(session_name)
    tier = meta.get("tier", "-") if meta else "-"
    model = meta.get("model", "-") if meta else "-"
    prompt = meta.get("prompt", "") if meta else ""
    watchdog = meta.get("watchdog", watchdog_timeout or "12m") if meta else (watchdog_timeout or "12m")
    grace = meta.get("kill_grace", kill_grace) if meta else kill_grace
    log_path = get_log_path(session_name)

    def set_title(title: str) -> None:
        if sys.stdout.isatty():
            sys.stdout.write(f"\033]0;{title}\007")
            sys.stdout.flush()

    set_title(f"🤖 [{session_name}] Live | Ctrl+C to manage")

    print(f"\n🚀 [{session_name}] tier: {tier} | model: {model} | watchdog: {watchdog} (Ctrl+C to manage)")
    print("─" * 77)

    for _ in range(25):
        if log_path.exists():
            break
        time.sleep(0.1)

    if not log_path.exists():
        set_title("")
        sys.stderr.write(f"🚨 [ERROR] Log file not found: {log_path}\n")
        return 1

    import termios
    import tty

    fd = sys.stdin.fileno() if sys.stdin.isatty() else None
    old_stdin_attr = None
    if fd is not None:
        try:
            old_stdin_attr = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        except Exception:
            old_stdin_attr = None

    def forward_keys() -> None:
        if fd is None:
            return
        try:
            r_in, _, _ = select.select([fd], [], [], 0)
            if r_in:
                key_bytes = os.read(fd, 1024)
                if key_bytes:
                    hex_args = [f"{b:02x}" for b in key_bytes]
                    res = subprocess.run(
                        ["tmux", "send-keys", "-t", session_name, "-H", *hex_args],
                        check=False,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    if res.returncode != 0:
                        subprocess.run(
                            ["tmux", "send-keys", "-t", session_name, "-l", key_bytes.decode("utf-8", errors="replace")],
                            check=False,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                        )
        except Exception:
            pass

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            while True:
                try:
                    while True:
                        forward_keys()
                        chunk = f.read(4096)
                        if chunk:
                            cleaned = ANSI_SANITIZE_RE.sub("", chunk)
                            if cleaned:
                                sys.stdout.write(cleaned)
                                sys.stdout.flush()
                        else:
                            active = list_active_tmux_sessions()
                            if session_name not in active:
                                rest = f.read()
                                if rest:
                                    cleaned = ANSI_SANITIZE_RE.sub("", rest)
                                    if cleaned:
                                        sys.stdout.write(cleaned)
                                        sys.stdout.flush()
                                set_title("")
                                print("\n" + "─" * 77)
                                try:
                                    content = log_path.read_text(errors="replace")
                                    if "[TIMEOUT]" in content:
                                        print(f"🚨 [TIMEOUT] Execution exceeded watchdog limit of {watchdog} and was terminated.")
                                    else:
                                        print(f"✅ [arouter] Session \"{session_name}\" finished.")
                                except Exception:
                                    print(f"✅ [arouter] Session \"{session_name}\" finished.")
                                return 0
                            if fd is not None:
                                try:
                                    r_wait, _, _ = select.select([fd], [], [], 0.03)
                                    if r_wait:
                                        forward_keys()
                                except Exception:
                                    time.sleep(0.03)
                            else:
                                time.sleep(0.03)
                except KeyboardInterrupt:
                    set_title(f"⏸️ [{session_name}] Paused")
                    choice = "leave"
                    sys.stdout.write(f"\n\033[1;32m🟢 Work continues streaming in the background for\033[0m \033[1;36m🤖 Session \"{session_name}\"\033[0m\n")
                    sys.stdout.write("\033[1m[enter/b]\033[0m Back to shell   \033[1m[r]\033[0m Resume stream   \033[1m[k]\033[0m Kill session   \033[1m[s]\033[0m All sessions\nSelection: ")
                    sys.stdout.flush()

                    if sys.stdin.isatty():
                        import termios
                        fd = sys.stdin.fileno()
                        try:
                            termios.tcflush(fd, termios.TCIFLUSH)
                        except Exception:
                            pass
                        old_attr = termios.tcgetattr(fd)
                        try:
                            raw_attr = termios.tcgetattr(fd)
                            raw_attr[3] &= ~(termios.ISIG | termios.ICANON | termios.ECHO)
                            termios.tcsetattr(fd, termios.TCSADRAIN, raw_attr)
                            while True:
                                ch = sys.stdin.read(1)
                                if ch == "\x03":
                                    choice = "double_ctrl_c"
                                    break
                                elif ch in ("\r", "\n", " ", "b", "B", "d", "D", "l", "L", "\x04"):
                                    choice = "leave"
                                    break
                                elif ch in ("k", "K"):
                                    choice = "k"
                                    break
                                elif ch in ("r", "R"):
                                    choice = "r"
                                    break
                                elif ch in ("s", "S"):
                                    choice = "s"
                                    break
                        finally:
                            termios.tcsetattr(fd, termios.TCSADRAIN, old_attr)
                            try:
                                termios.tcflush(fd, termios.TCIFLUSH)
                            except Exception:
                                pass
                    else:
                        try:
                            ch_in = input().strip().lower()
                            choice = "k" if ch_in == "k" else ("r" if ch_in == "r" else ("s" if ch_in == "s" else "leave"))
                        except Exception:
                            choice = "leave"

                    if choice == "r":
                        set_title(f"🤖 [{session_name}] Live | Ctrl+C to manage")
                        sys.stdout.write("\r\033[2K\033[1A\033[2K\033[1A\033[2K\033[1A\033[2K\r")
                        sys.stdout.flush()
                        continue
                    elif choice in ("k", "double_ctrl_c"):
                        set_title("")
                        sys.stdout.write("\n")
                        kill_session(session_name, manual=(choice == "double_ctrl_c"))
                        sys.exit(0)
                    elif choice == "s":
                        set_title("")
                        sys.stdout.write("\n")
                        try:
                            from sessions.cli import interactive_explorer
                            sys.exit(interactive_explorer())
                        except Exception as e:
                            print(f"ℹ️  Detached. View sessions with 'asessions'. ({e})")
                            sys.exit(0)
                    else:
                        set_title("")
                        sys.stdout.write("\n")
                        print(f"ℹ️  [arouter] Detached from session '{session_name}'. Reattach with: arouter attach {session_name}")
                        return 0
    finally:
        set_title("")
        if old_stdin_attr is not None and fd is not None:
            try:
                import termios
                termios.tcsetattr(fd, termios.TCSADRAIN, old_stdin_attr)
            except Exception:
                pass
        if sys.stdout.isatty():
            sys.stdout.write("\033[?1004l")
            sys.stdout.flush()
def attach_session(session_name: str, force_tmux: bool = False) -> int:
    """Attach to session: defaults to stream proxy for unlimited scrollback, or raw tmux PTY if forced."""
    active = list_active_tmux_sessions()
    if session_name not in active:
        sys.stderr.write(f"🚨 [ERROR] No active tmux session found named '{session_name}'.\n")
        return 1
    if force_tmux:
        os.execvp("tmux", ["tmux", "attach-session", "-t", session_name])
    return stream_session(session_name)


def kill_session(session_name: str, manual: bool = False) -> int:
    """Terminate an active agent session and clean up process tree."""
    active = list_active_tmux_sessions()
    msg_term = f"❌ Session '{session_name}' manually terminated." if manual else f"✅ Session '{session_name}' terminated."
    if session_name not in active:
        cleanup_session_metadata(session_name)
        log_path = get_log_path(session_name)
        if log_path.exists():
            print(f"✅ Session '{session_name}' has already finished.")
            return 0
        sys.stderr.write(f"⚠️  [WARN] No active session found named '{session_name}'.\n")
        return 1

    try:
        res = subprocess.run(
            ["tmux", "list-panes", "-t", session_name, "-F", "#{pane_pid}"],
            capture_output=True,
            text=True,
            check=False,
        )
        pids = [p.strip() for p in res.stdout.splitlines() if p.strip()]

        for pid in pids:
            try:
                subprocess.run(["kill", "-15", pid], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        res_kill = subprocess.run(["tmux", "kill-session", "-t", session_name], capture_output=True, text=True)
        if res_kill.returncode != 0:
            err = res_kill.stderr.strip()
            err_lower = err.lower()
            if any(k in err_lower for k in ["no server running", "can't find session", "no current target", "server exited unexpectedly"]):
                if _wait_pids_gone(pids, timeout=2.0):
                    _record_exit(session_name, 143, overwrite=True)
                else:
                    for p in (get_exit_path(session_name), get_exit_path(session_name).with_suffix(".exit.tmp")):
                        try:
                            if p.exists():
                                p.unlink()
                        except Exception:
                            pass
                cleanup_session_metadata(session_name)
                print(msg_term)
                return 0
            sys.stderr.write(f"🚨 [ERROR] Failed to kill session '{session_name}': {err}\n")
            return 1

        for pid in pids:
            try:
                subprocess.run(["kill", "-9", pid], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

        if _wait_pids_gone(pids, timeout=2.0):
            _record_exit(session_name, 143, overwrite=True)
        else:
            for p in (get_exit_path(session_name), get_exit_path(session_name).with_suffix(".exit.tmp")):
                try:
                    if p.exists():
                        p.unlink()
                except Exception:
                    pass

        cleanup_session_metadata(session_name)
        print(msg_term)
        return 0
    except subprocess.CalledProcessError as e:
        err = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
        err_lower = err.lower()
        if any(k in err_lower for k in ["no server running", "can't find session", "no current target", "server exited unexpectedly"]):
            if _wait_pids_gone([], timeout=2.0):
                _record_exit(session_name, 143, overwrite=True)
            cleanup_session_metadata(session_name)
            print(msg_term)
            return 0
        sys.stderr.write(f"🚨 [ERROR] Failed to kill session '{session_name}': {err.strip()}\n")
        return 1


def tail_logs(session_name: str, follow: bool = False) -> int:
    """View or follow raw log output file."""
    log_path = get_log_path(session_name)
    if not log_path.exists():
        sys.stderr.write(f"🚨 [ERROR] Log file not found: {log_path}\n")
        return 1

    if follow:
        try:
            subprocess.run(["tail", "-f", str(log_path)], check=True)
            return 0
        except KeyboardInterrupt:
            return 0
    else:
        try:
            with open(log_path, "r", errors="replace") as f:
                shutil.copyfileobj(f, sys.stdout)
            return 0
        except Exception as e:
            sys.stderr.write(f"🚨 [ERROR] Could not read log file: {e}\n")
            return 1


def create_runner_script(
    session_name: str,
    engine_script: str,
    dispatch_args: List[str],
    watchdog_timeout: str,
    kill_grace: str,
    tier: str,
    model: str,
    engine: str,
    log_file: Path,
) -> Path:
    """Generate ephemeral bash runner that supervises execution and streams via tee."""
    meta_dir = _resolve_metadata_dir()
    meta_dir.mkdir(parents=True, exist_ok=True)
    runner_path = meta_dir / f"{session_name}.run.sh"
    meta_path = get_metadata_path(session_name)
    exit_path = get_exit_path(session_name)
    exit_tmp = meta_dir / f"{session_name}.exit.tmp"
    # Boot trampoline: tmux cmdline must not contain "<session>.run.sh" so E10's
    # `pgrep -f "<session>.run.sh"` selects the bash runner, not the tmux server.
    boot_path = meta_dir / f"{session_name}.boot.sh"
    boot_path.write_text(
        f"#!/usr/bin/env bash\nexec bash {shlex.quote(str(runner_path))}\n",
        encoding="utf-8",
    )
    boot_path.chmod(0o755)

    cmd_parts = [engine_script] + dispatch_args
    cmd_str = " ".join(shlex.quote(arg) for arg in cmd_parts)

    telemetry_msg = (
        f"ℹ️  [arouter] Engine: {engine} | Model: {model} (tier: {tier}) | Watchdog: {watchdog_timeout} (kill grace: {kill_grace})"
        if watchdog_timeout not in ("0", "off")
        else f"ℹ️  [arouter] Engine: {engine} | Model: {model} (tier: {tier}) | Watchdog: off"
    )

    content = f"""#!/usr/bin/env bash
set -uo pipefail

cleanup() {{
    local ec=$?
    printf '%s\\n' "$ec" > {shlex.quote(str(exit_tmp))} && mv -f {shlex.quote(str(exit_tmp))} {shlex.quote(str(exit_path))}
    rm -f {shlex.quote(str(runner_path))} {shlex.quote(str(meta_path))} {shlex.quote(str(boot_path))}
}}
trap cleanup EXIT
trap 'exit 143' TERM
trap 'exit 129' HUP
trap 'exit 130' INT

execute_work() {{
    echo >&2 {shlex.quote(telemetry_msg)}

    local ec=0
    if [[ "{watchdog_timeout}" != "0" && "{watchdog_timeout}" != "off" && -x /usr/bin/timeout ]]; then
        /usr/bin/timeout --foreground -k "{kill_grace}" "{watchdog_timeout}" {cmd_str}
        ec=$?
        if [[ $ec -eq 124 || $ec -eq 137 ]]; then
            echo >&2 ""
            echo >&2 "🚨 [TIMEOUT] Execution exceeded watchdog limit of {watchdog_timeout} (kill grace: {kill_grace}) and was terminated (exit $ec)."
        fi
    else
        {cmd_str}
        ec=$?
    fi
    return $ec
}}

execute_work
exit $?
"""
    runner_path.write_text(content)
    runner_path.chmod(0o755)
    return boot_path


def spawn_detached_session(
    session_name: str,
    tier: str,
    model: str,
    engine: str,
    engine_script: str,
    dispatch_args: List[str],
    watchdog_timeout: str,
    kill_grace: str,
    cwd: Optional[str] = None,
    auto_stream: bool = False,
) -> int:
    """Spawn an isolated headless tmux session that terminates when the command exits."""
    ensure_environment()
    log_file = get_log_path(session_name)
    try:
        if log_file.exists():
            log_file.unlink()
    except Exception:
        pass
    exit_path = get_exit_path(session_name)
    exit_tmp = exit_path.with_suffix(".exit.tmp")
    boot_path = _resolve_metadata_dir() / f"{session_name}.boot.sh"
    for p in (exit_path, exit_tmp, boot_path):
        try:
            if p.exists():
                p.unlink()
        except Exception:
            pass
    log_file.touch(exist_ok=True)

    prompt_text = ""
    for arg in dispatch_args[1:]:
        if arg and not arg.startswith("-"):
            prompt_text = arg.strip()
            break

    save_session_metadata(
        session_name,
        tier,
        model,
        engine,
        extra={
            "prompt": prompt_text,
            "watchdog": watchdog_timeout,
            "kill_grace": kill_grace,
        },
    )

    boot_path = create_runner_script(
        session_name=session_name,
        engine_script=engine_script,
        dispatch_args=dispatch_args,
        watchdog_timeout=watchdog_timeout,
        kill_grace=kill_grace,
        tier=tier,
        model=model,
        engine=engine,
        log_file=log_file,
    )
    runner_path = _resolve_metadata_dir() / f"{session_name}.run.sh"

    work_dir = cwd or os.getcwd()

    cols, rows = shutil.get_terminal_size((80, 24))
    cmd = [
        "tmux",
        "new-session",
        "-d",
        "-s",
        session_name,
        "-x",
        str(cols),
        "-y",
        str(rows),
        "-c",
        work_dir,
        f"bash {shlex.quote(str(boot_path))}",
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(f"🚨 [ERROR] Failed to start tmux session: {res.stderr}\n")
        cleanup_session_metadata(session_name)
        for p in (boot_path, runner_path, exit_path, exit_tmp):
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass
        return res.returncode

    # Prevent zombie sessions across any host environment
    subprocess.run(["tmux", "set-option", "-t", session_name, "remain-on-exit", "off"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Tap console stream to disk via pipe-pane (preserves native PTY for interactive TUI)
    subprocess.run(
        ["tmux", "pipe-pane", "-t", session_name, f"cat >> {shlex.quote(str(log_file))}"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if auto_stream:
        return stream_session(session_name, watchdog_timeout, kill_grace)

    print(f"🚀 [arouter] Detached session '{session_name}' spawned.")
    print(f"📄 [arouter] Logs: {log_file}")
    print(f"👉 [arouter] Attach with: arouter attach {session_name}")
    return 0
