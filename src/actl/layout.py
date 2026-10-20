"""Filesystem layout for the actl graph root."""
from __future__ import annotations

import os
from pathlib import Path

from actl.ids import validate_sprint_tag

ROLES = ("architect", "challenger", "implementer", "curator")


def _check_tag(tag: str) -> str:
    if not isinstance(tag, str) or not validate_sprint_tag(tag):
        raise ValueError(f"Invalid sprint tag: {tag!r}")
    return tag


def _check_role(role: str) -> str:
    if role not in ROLES:
        raise ValueError(f"Unknown role: {role!r}")
    return role


def _check_workspace_name(name: str) -> str:
    if (
        not isinstance(name, str)
        or name in ("", ".", "..")
        or "/" in name
        or "\\" in name
        or "\x00" in name
        or any(ord(c) < 0x20 or ord(c) == 0x7F for c in name)
    ):
        raise ValueError(f"Invalid workspace name: {name!r}")
    return name


def _mkdir(path: Path, mode: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)


class Layout:
    def __init__(self, root: Path | str | None = None) -> None:
        if root is None:
            env = os.environ.get("ACTL_ROOT")
            if env:
                root = env
            else:
                root = Path(os.environ.get("HOME", str(Path.home()))) / "actl-graph"
        if "\x00" in str(root):
            raise ValueError("NUL byte in root path")
        self.root: Path = Path(root).resolve()

    @property
    def actl_repo(self) -> Path:
        return self.root / "actl-repo"

    @property
    def target_repo(self) -> Path:
        return self.root / "repos" / "target-repo"

    @property
    def baseline_file(self) -> Path:
        return self.root / "baseline.json"

    def sprint_dir(self, tag: str) -> Path:
        return self.actl_repo / "specs" / _check_tag(tag)

    def runs_dir(self, tag: str) -> Path:
        return self.sprint_dir(tag) / "runs"

    def logs_dir(self, tag: str) -> Path:
        return self.runs_dir(tag) / "logs"

    def turns_dir(self, tag: str) -> Path:
        return self.runs_dir(tag) / "turns"

    def state_file(self, tag: str) -> Path:
        return self.runs_dir(tag) / "state.json"

    def state_lock(self, tag: str) -> Path:
        return self.runs_dir(tag) / "state.lock"

    def sessions_file(self, tag: str) -> Path:
        return self.runs_dir(tag) / "sessions.tsv"

    def sprint_toml(self, tag: str) -> Path:
        return self.sprint_dir(tag) / "sprint.toml"

    def handoff(self, tag: str) -> Path:
        return self.root / "handoff" / _check_tag(tag)

    def inbox(self, tag: str, role: str) -> Path:
        return self.handoff(tag) / f"{_check_role(role)}-inputs"

    def outbox(self, tag: str, role: str) -> Path:
        return self.handoff(tag) / f"{_check_role(role)}-outputs"

    def workspace(self, name: str, tag: str | None = None) -> Path:
        _check_workspace_name(name)
        if tag is not None:
            _check_tag(tag)
            return self.root / "workspaces" / tag / name
        return self.root / "workspaces" / name

    def homes(self, role: str) -> Path:
        return self.root / "homes" / _check_role(role)

    def ensure_base_tree(self) -> None:
        _mkdir(self.root, 0o755)
        _mkdir(self.actl_repo, 0o700)
        _mkdir(self.actl_repo / "specs", 0o755)
        for d in ("handoff", "workspaces", "repos", "homes"):
            _mkdir(self.root / d, 0o755)
        for role in ROLES:
            _mkdir(self.homes(role), 0o755)

    def ensure_sprint_tree(self, tag: str) -> None:
        _check_tag(tag)
        self.ensure_base_tree()
        for p in (
            self.sprint_dir(tag),
            self.runs_dir(tag),
            self.logs_dir(tag),
            self.turns_dir(tag),
            self.handoff(tag),
        ):
            _mkdir(p, 0o755)
        for role in ROLES:
            _mkdir(self.inbox(tag, role), 0o750)
            _mkdir(self.outbox(tag, role), 0o770)
