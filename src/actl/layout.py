"""Filesystem layout for the actl graph root."""
from __future__ import annotations

import os
from pathlib import Path

from actl.ids import validate_sprint_tag

ROLES = ("architect", "challenger", "implementer", "curator")

PROFILES_README = """# profiles/

One folder per persona account: architect, challenger, implementer, curator.
Each folder holds that persona's CLI state. The account's HOME points here.

Lives here: login and config, session store and transcripts, installed copies of
skills and rules, and the Architect's persistent thread.

Does not live here: the persona's instructions. System prompts, skills and rules are
versioned in the atools repo and delivered by actl on every turn, or installed into
the profile when the account is created. Nothing in a profile is authoritative:
deleting one loses memory, never policy.

Durable results are copied into records/ by actl. A profile is working memory, not an archive.
Empty until Stage 4, when real accounts exist.
"""


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


def _check_repo(repo: str) -> str:
    # Repo names use the same rules as workspace names (memo L-10 / S0-R3).
    try:
        return _check_workspace_name(repo)
    except ValueError as exc:
        raise ValueError(f"Invalid repo name: {repo!r}") from exc


def _mkdir(path: Path, mode: int) -> None:
    path.mkdir(parents=True, exist_ok=True)
    os.chmod(path, mode)


class Layout:
    def __init__(
        self, root: Path | str | None = None, repo: str = "target-repo"
    ) -> None:
        if root is None:
            env = os.environ.get("ACTL_ROOT")
            if env:
                root = env
            else:
                root = Path(os.environ.get("HOME", str(Path.home()))) / "actl-graph"
        if "\x00" in str(root):
            raise ValueError("NUL byte in root path")
        self.root: Path = Path(root).resolve()
        self.repo: str = _check_repo(repo)

    def _resolve_contained(self, target_path: Path) -> Path:
        resolved = target_path.resolve()
        root_resolved = self.root.resolve()
        if not resolved.is_relative_to(root_resolved):
            raise ValueError(f"Path escapes boundary: {target_path} outside {self.root}")
        return target_path

    def _safe_path(self, path: Path) -> Path:
        return self._resolve_contained(path)

    @property
    def records(self) -> Path:
        return self._resolve_contained(self.root / "records")

    @property
    def target_repo(self) -> Path:
        return self._resolve_contained(self.root / "repos" / self.repo)

    @property
    def baseline_file(self) -> Path:
        return self._resolve_contained(self.root / "baseline.json")

    def sprint_dir(self, tag: str) -> Path:
        return self._resolve_contained(self.records / self.repo / _check_tag(tag))

    def runs_dir(self, tag: str) -> Path:
        return self._resolve_contained(
            self.root / "sprints" / self.repo / _check_tag(tag) / "runs"
        )

    def logs_dir(self, tag: str) -> Path:
        return self._resolve_contained(self.runs_dir(tag) / "logs")

    def turns_dir(self, tag: str) -> Path:
        return self._resolve_contained(self.runs_dir(tag) / "turns")

    def state_file(self, tag: str) -> Path:
        return self._resolve_contained(self.runs_dir(tag) / "state.json")

    def state_lock(self, tag: str) -> Path:
        return self._resolve_contained(self.runs_dir(tag) / "state.lock")

    def sessions_file(self, tag: str) -> Path:
        return self._resolve_contained(self.runs_dir(tag) / "sessions.tsv")

    def sprint_toml(self, tag: str) -> Path:
        return self._resolve_contained(self.sprint_dir(tag) / "sprint.toml")

    def mailboxes(self, tag: str) -> Path:
        return self._resolve_contained(
            self.root / "sprints" / self.repo / _check_tag(tag) / "mailboxes"
        )

    def inbox(self, tag: str, role: str) -> Path:
        return self._resolve_contained(
            self.mailboxes(tag) / _check_role(role) / "inbox"
        )

    def outbox(self, tag: str, role: str) -> Path:
        return self._resolve_contained(
            self.mailboxes(tag) / _check_role(role) / "outbox"
        )

    def workspace(self, name: str, tag: str | None = None) -> Path:
        _check_workspace_name(name)
        if tag is not None:
            _check_tag(tag)
            return self._resolve_contained(
                self.root / "sprints" / self.repo / tag / "workspaces" / name
            )
        return self._resolve_contained(
            self.root / "sprints" / self.repo / "workspaces" / name
        )

    def profile(self, role: str) -> Path:
        return self._resolve_contained(self.root / "profiles" / _check_role(role))

    def ensure_base_tree(self) -> None:
        self._resolve_contained(self.root)
        _mkdir(self.root, 0o755)
        _mkdir(self.records, 0o700)
        for d in ("sprints", "repos", "profiles"):
            _mkdir(self._resolve_contained(self.root / d), 0o755)
        for role in ROLES:
            _mkdir(self.profile(role), 0o755)

    def ensure_sprint_tree(self, tag: str) -> None:
        _check_tag(tag)
        self.ensure_base_tree()
        for p in (
            self.sprint_dir(tag),
            self.runs_dir(tag),
            self.logs_dir(tag),
            self.turns_dir(tag),
            self.mailboxes(tag),
            self._resolve_contained(
                self.root / "sprints" / self.repo / tag / "workspaces"
            ),
        ):
            _mkdir(self._resolve_contained(p), 0o755)
        for role in ROLES:
            role_dir = self.mailboxes(tag) / role
            _mkdir(self._resolve_contained(role_dir), 0o755)
            _mkdir(self.inbox(tag, role), 0o750)
            _mkdir(self.outbox(tag, role), 0o770)
