"""actl doctor — environment baseline report."""
from __future__ import annotations

import getpass
import importlib.util
import json
import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

from actl.layout import Layout

REPO_ROOT = Path(__file__).resolve().parents[2]

ANCESTORS = ("5cb7f30", "759a0ca", "a9b3a4e", "4da9394")
ENGINE_CLIS = ("agent", "codex", "claude", "agy", "aider", "vibe")
SUITE_SCRIPTS = {
    "engines": "proof/run_suite_engines.sh",
    "session_persistence": "proof/run_suite_session_persistence.sh",
    "exit_code": "proof/run_suite_exit_code.sh",
}
SYNC_TARGETS = {
    "hooks/pre-commit": Path.home() / ".config/git/hooks/pre-commit",
    "rules/git-safety.md": Path.home() / ".cursor/rules/git-safety.md",
    ".cursor/skills/atools-repair/SKILL.md": Path.home() / ".cursor/skills/atools-repair/SKILL.md",
}


def _run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        stdin=subprocess.DEVNULL,
        **kwargs,
    )


def _first_line(s: str) -> str:
    return (s or "").splitlines()[0] if (s or "").strip() else ""


def _tail(text: str, n: int = 20, max_chars: int = 2000) -> str:
    lines = text.splitlines()
    out = "\n".join(lines[-n:])
    if len(out) > max_chars:
        out = out[-max_chars:]
    return out


def _parse_audit_counts(text: str) -> dict[str, int]:
    counts = {"pass": 0, "fail": 0, "skip": 0, "warn": 0}
    for key in counts:
        m = re.search(rf"\b{key}\b\s*[:=]\s*(\d+)", text, re.I)
        if m:
            counts[key] = int(m.group(1))
        else:
            m2 = re.search(rf"(\d+)\s+{key}", text, re.I)
            if m2:
                counts[key] = int(m2.group(1))
    return counts


def run_doctor(layout: Layout, refresh: bool = False) -> dict[str, Any]:
    warnings: list[str] = []
    proof_out = REPO_ROOT / "proof" / "out"
    proof_out_existed = proof_out.exists()
    existing_files: set[str] = set()
    snapshots: dict[str, bytes] = {}
    if proof_out_existed:
        existing_files = {p.name for p in proof_out.iterdir()}
        for p in proof_out.iterdir():
            if p.is_file() and not p.name.startswith("P-S0-"):
                try:
                    snapshots[p.name] = p.read_bytes()
                except OSError:
                    pass

    try:
        version = (REPO_ROOT / "VERSION").read_text(encoding="utf-8").strip()
        try:
            ver_tuple = tuple(int(x) for x in re.findall(r"\d+", version)[:3])
            if ver_tuple < (0, 1, 4):
                warnings.append(f"VERSION {version} is below v0.1.4")
        except ValueError:
            pass

        head_sha = _run(["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"]).stdout.strip()
        git_status_porcelain = _run(
            ["git", "-C", str(REPO_ROOT), "status", "--porcelain"]
        ).stdout.rstrip("\n")
        git_dirty = bool(git_status_porcelain.strip())

        ancestors: dict[str, bool] = {}
        for sha in ANCESTORS:
            r = _run(["git", "-C", str(REPO_ROOT), "merge-base", "--is-ancestor", sha, "HEAD"])
            ancestors[sha] = r.returncode == 0

        tool_versions: dict[str, str | None] = {
            "python3": _first_line(_run(["python3", "--version"]).stdout or _run(["python3", "--version"]).stderr),
            "git": _first_line(_run(["git", "--version"]).stdout),
            "bash": _first_line(_run(["bash", "--version"]).stdout),
            "tmux": None,
        }
        if shutil.which("tmux"):
            tv = _first_line(_run(["tmux", "-V"]).stdout)
            tool_versions["tmux"] = tv if tv.startswith("tmux") else tv

        python_packages = {
            "pytest": importlib.util.find_spec("pytest") is not None,
            "jsonschema": importlib.util.find_spec("jsonschema") is not None,
        }
        engine_clis = {cli: bool(shutil.which(cli)) for cli in ENGINE_CLIS}
        timeout_available = bool(shutil.which("timeout") or Path("/usr/bin/timeout").is_file())
        effective_user = getpass.getuser()
        actl_root = str(layout.root)
        log_dir = os.environ.get("ATOOLS_LOG_DIR") or (
            "/root/.cursor/logs"
            if Path("/root/.cursor").exists()
            else str(Path.home() / ".cursor" / "logs")
        )
        metadata_dir = os.environ.get("ATOOLS_SESSION_DIR") or str(
            Path.home() / ".cursor" / "sessions"
        )

        if shutil.which("loginctl"):
            lr = _run(["loginctl", "show-user", effective_user, "-p", "Linger"])
            linger_state = lr.stdout.strip() if lr.returncode == 0 else "unknown"
        else:
            linger_state = "unknown"

        process_py = REPO_ROOT / "src" / "router" / "process.py"
        router_has_read_exit_code = bool(
            process_py.is_file() and "def read_exit_code" in process_py.read_text(encoding="utf-8")
        )
        if not router_has_read_exit_code:
            warnings.append("router.process.read_exit_code is not present")

        suites: dict[str, dict[str, Any]] = {}
        for key, rel in SUITE_SCRIPTS.items():
            script = REPO_ROOT / rel
            if not script.is_file():
                suites[key] = {"present": False, "exit_code": None, "tail": ""}
                if key == "exit_code":
                    warnings.append(f"suite script missing: {rel}")
            else:
                r = _run(["bash", str(script)], cwd=str(REPO_ROOT), timeout=600)
                suites[key] = {
                    "present": True,
                    "exit_code": r.returncode,
                    "tail": _tail((r.stdout or "") + (r.stderr or "")),
                }

        audit_script = REPO_ROOT / "audit" / "atools-compliance_audit.sh"
        if not audit_script.is_file():
            audit: dict[str, Any] = {
                "present": False,
                "exit_code": None,
                "pass": 0,
                "fail": 0,
                "skip": 0,
                "warn": 0,
                "self_test_exit_code": None,
                "tail": "",
            }
        else:
            r1 = _run(["bash", str(audit_script), "--cursor"], cwd=str(REPO_ROOT), timeout=600)
            r2 = _run(["bash", str(audit_script), "--self-test"], cwd=str(REPO_ROOT), timeout=600)
            text = (r1.stdout or "") + (r1.stderr or "")
            counts = _parse_audit_counts(text)
            audit = {
                "present": True,
                "exit_code": r1.returncode,
                "pass": counts["pass"],
                "fail": counts["fail"],
                "skip": counts["skip"],
                "warn": counts["warn"],
                "self_test_exit_code": r2.returncode,
                "tail": _tail(text),
            }

        installed_sync_diffs: dict[str, str] = {}
        for rel, installed in SYNC_TARGETS.items():
            repo_file = REPO_ROOT / rel
            if not installed.is_file():
                installed_sync_diffs[rel] = "MISSING"
                warnings.append(f"installed sync target missing: {rel}")
            else:
                r = _run(["diff", "-u", str(repo_file), str(installed)])
                if r.returncode == 0:
                    installed_sync_diffs[rel] = ""
                else:
                    installed_sync_diffs[rel] = r.stdout or r.stderr or "DIFF"
                    warnings.append(f"installed sync target differs: {rel}")

        report: dict[str, Any] = {
            "version": version,
            "head_sha": head_sha,
            "git_status_porcelain": git_status_porcelain,
            "git_dirty": git_dirty,
            "ancestors": ancestors,
            "tool_versions": tool_versions,
            "python_packages": python_packages,
            "engine_clis": engine_clis,
            "timeout_available": timeout_available,
            "effective_user": effective_user,
            "actl_root": actl_root,
            "log_dir": log_dir,
            "metadata_dir": metadata_dir,
            "linger_state": linger_state,
            "router_has_read_exit_code": router_has_read_exit_code,
            "suites": suites,
            "audit": audit,
            "installed_sync_diffs": installed_sync_diffs,
            "warnings": warnings,
        }

        should_write = (not layout.baseline_file.exists()) or refresh
        if should_write:
            layout.root.mkdir(parents=True, exist_ok=True)
            layout.baseline_file.write_text(
                json.dumps(report, indent=2) + "\n", encoding="utf-8"
            )

        return report
    finally:
        if not proof_out_existed:
            if proof_out.exists():
                shutil.rmtree(proof_out, ignore_errors=True)
        else:
            if proof_out.exists():
                for p in list(proof_out.iterdir()):
                    if p.name not in existing_files:
                        try:
                            if p.is_dir():
                                shutil.rmtree(p, ignore_errors=True)
                            else:
                                p.unlink()
                        except OSError:
                            pass
                for name, data in snapshots.items():
                    target = proof_out / name
                    try:
                        if target.read_bytes() != data:
                            target.write_bytes(data)
                    except OSError:
                        pass
