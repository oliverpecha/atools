"""Monotonic sequence reservation and state reconstruction."""
from __future__ import annotations

import contextlib
import fcntl
import hashlib
import json
import os
import threading
import tomllib
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from actl.errors import StateIntegrityError
from actl.hashing import canonical_json
from actl.ids import format_artifact_id, parse_seq_from_name
from actl.layout import Layout
from actl import schemas

_tls = threading.local()
_fork_registered = False
_fork_lock = threading.Lock()


def _locks() -> dict[str, tuple[int, int]]:
    d = getattr(_tls, "locks", None)
    if d is None:
        d = {}
        _tls.locks = d
    return d


def _clear_locks_after_fork() -> None:
    locks = getattr(_tls, "locks", None)
    if not locks:
        _tls.locks = {}
        return
    for key, (fd, _depth) in list(locks.items()):
        try:
            os.close(fd)
        except OSError:
            pass
    _tls.locks = {}


def _ensure_fork_hook() -> None:
    global _fork_registered
    with _fork_lock:
        if _fork_registered:
            return
        if hasattr(os, "register_at_fork"):
            os.register_at_fork(after_in_child=_clear_locks_after_fork)
        _fork_registered = True


def _atomic_write(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.parent / f".{target.name}.tmp.{os.getpid()}.{threading.get_ident()}"
    try:
        with open(tmp, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, target)
        dir_fd = os.open(str(target.parent), os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


@contextlib.contextmanager
def state_lock(layout: Layout, tag: str) -> Iterator[None]:
    _ensure_fork_hook()
    layout.sprint_dir(tag)  # validate tag
    if not layout.sprint_dir(tag).is_dir():
        raise FileNotFoundError(f"Sprint dir missing: {tag}")
    lock_path = layout.state_lock(tag)
    key = str(lock_path)
    locks = _locks()
    if key in locks:
        fd, depth = locks[key]
        locks[key] = (fd, depth + 1)
        try:
            yield
        finally:
            fd, depth = locks[key]
            depth -= 1
            if depth == 0:
                fcntl.flock(fd, fcntl.LOCK_UN)
                os.close(fd)
                del locks[key]
            else:
                locks[key] = (fd, depth)
        return

    layout.runs_dir(tag).mkdir(parents=True, exist_ok=True)
    fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        locks[key] = (fd, 1)
        try:
            yield
        finally:
            fd2, depth = locks[key]
            depth -= 1
            if depth == 0:
                fcntl.flock(fd2, fcntl.LOCK_UN)
                os.close(fd2)
                del locks[key]
            else:
                locks[key] = (fd2, depth)
    except BaseException:
        if key not in locks:
            try:
                os.close(fd)
            except OSError:
                pass
        raise


def _check_state_repo(layout: Layout, state: dict[str, Any]) -> None:
    if state.get("repo") != layout.repo:
        raise StateIntegrityError(
            f"state.repo {state.get('repo')!r} != layout.repo {layout.repo!r}"
        )


def read_state(layout: Layout, tag: str) -> dict[str, Any]:
    sf = layout.state_file(tag)
    if not sf.is_file():
        raise FileNotFoundError(f"State file missing for {tag}")
    try:
        state = json.loads(sf.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid state JSON: {exc}") from exc
    if not isinstance(state, dict):
        raise ValueError("State JSON must be an object")
    _check_state_repo(layout, state)
    return state


def update_state(layout: Layout, tag: str, updates: dict[str, Any]) -> dict[str, Any]:
    if "seq" in updates:
        raise ValueError("seq cannot be modified via update_state")
    with state_lock(layout, tag):
        state = read_state(layout, tag)
        for k, v in updates.items():
            if k in ("attempts", "grants") and isinstance(v, dict) and isinstance(state.get(k), dict):
                merged = dict(state[k])
                merged.update(v)
                state[k] = merged
            else:
                state[k] = v
        errs = schemas.validate("state", state)
        if errs:
            raise ValueError(f"Invalid state update: {errs}")
        _atomic_write(layout.state_file(tag), canonical_json(state) + b"\n")
        return state


def reserve(layout: Layout, tag: str, kind: str) -> int:
    layout.sprint_dir(tag)
    format_artifact_id(kind, 1)
    if not layout.state_file(tag).is_file():
        raise FileNotFoundError(f"State file missing for {tag}")
    with state_lock(layout, tag):
        state = read_state(layout, tag)
        hw_path = layout.runs_dir(tag) / "seq.highwater"
        if hw_path.is_file():
            try:
                hw = int(hw_path.read_text(encoding="utf-8").strip())
            except ValueError:
                hw = 0
        else:
            hw = 0
        next_seq = max(int(state.get("seq", 0)), hw) + 1
        _atomic_write(hw_path, f"{next_seq}\n".encode("utf-8"))
        state["seq"] = next_seq
        _atomic_write(layout.state_file(tag), canonical_json(state) + b"\n")
        return next_seq


def _default_state(tag: str, max_seq: int, repo: str = "target-repo") -> dict[str, Any]:
    return {
        "run_id": "run-" + hashlib.sha256(tag.encode("utf-8")).hexdigest()[:12],
        "sprint_tag": tag,
        "repo": repo,
        "seq": max_seq,
        "epoch": 1,
        "status": "draft",
        "active_stage": None,
        "active_spec": None,
        "active_solution_key": None,
        "active_oracle_draft": None,
        "active_oracle": None,
        "active_contract": None,
        "attempts": {"oracle": 0, "implementer": 0, "live": 0, "curator": 0},
        "closures_submitted": 0,
        "hard_caps_tripped": 0,
        "grants": {"oracle": 0, "implementer": 0, "live": 0, "curator": 0},
        "tmux_sessions": [],
    }


def _scan_seq(path: Path) -> int:
    n = parse_seq_from_name(path.name)
    return n if n is not None else 0


def reconstruct(layout: Layout, tag: str) -> int:
    layout.sprint_dir(tag)
    if not layout.sprint_dir(tag).is_dir():
        raise FileNotFoundError(f"Sprint dir missing: {tag}")
    with state_lock(layout, tag):
        max_seq = 0
        hw_path = layout.runs_dir(tag) / "seq.highwater"
        if hw_path.is_file():
            try:
                max_seq = max(max_seq, int(hw_path.read_text(encoding="utf-8").strip()))
            except ValueError:
                pass
        sprint_dir = layout.sprint_dir(tag)
        runs_dir = layout.runs_dir(tag)
        for p in sprint_dir.iterdir() if sprint_dir.is_dir() else []:
            max_seq = max(max_seq, _scan_seq(p))
        for p in runs_dir.iterdir() if runs_dir.is_dir() else []:
            max_seq = max(max_seq, _scan_seq(p))
        mailboxes = layout.mailboxes(tag)
        if mailboxes.is_dir():
            for role_dir in mailboxes.iterdir():
                if not role_dir.is_dir():
                    continue
                for box_dir in role_dir.iterdir():
                    if box_dir.is_dir():
                        for p in box_dir.iterdir():
                            max_seq = max(max_seq, _scan_seq(p))
                    else:
                        max_seq = max(max_seq, _scan_seq(box_dir))
        ws = layout.root / "sprints" / layout.repo / tag / "workspaces"
        if ws.is_dir():
            for p in ws.iterdir():
                max_seq = max(max_seq, _scan_seq(p))

        state: dict[str, Any] | None = None
        sf = layout.state_file(tag)
        if sf.is_file():
            try:
                candidate = json.loads(sf.read_text(encoding="utf-8"))
                if isinstance(candidate, dict) and not schemas.validate("state", candidate):
                    state = candidate
            except (json.JSONDecodeError, ValueError, OSError):
                state = None
        if state is None:
            state = _default_state(tag, max_seq, repo=layout.repo)
        else:
            state["seq"] = max_seq
            state["repo"] = layout.repo
            state["epoch"] = 1
            state["status"] = "draft"
            state["active_stage"] = None
            state["active_spec"] = None
            state["active_solution_key"] = None
            state["active_oracle_draft"] = None
            state["active_oracle"] = None
            state["active_contract"] = None
            state["attempts"] = {"oracle": 0, "implementer": 0, "live": 0, "curator": 0}
            state["grants"] = {"oracle": 0, "implementer": 0, "live": 0, "curator": 0}
            state["closures_submitted"] = 0
            state["hard_caps_tripped"] = 0

        toml_path = layout.sprint_toml(tag)
        if toml_path.is_file():
            try:
                toml_data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
                if toml_data.get("status") == "frozen" and state.get("status") == "draft":
                    state["status"] = "running"
            except (tomllib.TOMLDecodeError, OSError):
                pass

        artifacts: list[tuple[int, Path]] = []
        for directory in (sprint_dir, runs_dir):
            if directory.is_dir():
                for p in directory.iterdir():
                    n = parse_seq_from_name(p.name)
                    if n is not None:
                        artifacts.append((n, p))
        artifacts.sort(key=lambda t: (t[0], t[1].name))

        for _n, p in artifacts:
            name = p.name
            if name.startswith("spec-") and name.endswith(".md") and not name.endswith(".meta.json"):
                state["active_spec"] = name
            elif name.startswith("solution_key-") and name.endswith(".patch"):
                state["active_solution_key"] = name
            elif name.startswith("oracle-draft-"):
                state["active_oracle_draft"] = name
            elif name.startswith("oracle-") and not name.startswith("oracle-draft-"):
                state["active_oracle"] = name
            elif (
                name.startswith("qualification-")
                and name.endswith(".json")
                and not name.endswith(".meta.json")
            ):
                try:
                    q = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    raise ValueError(f"Corrupt qualification artifact {name}: {exc}") from exc
                if not isinstance(q, dict):
                    raise ValueError(f"Qualification artifact {name} is not a dict")
                errs = schemas.validate("qualification", q)
                if errs:
                    raise ValueError(f"Invalid qualification artifact {name}: {errs}")
                attempts = dict(state.get("attempts") or {})
                attempts["oracle"] = int(attempts.get("oracle", 0)) + 1
                state["attempts"] = attempts
            elif name.startswith("contract-") and name.endswith(".json") and not name.endswith(".meta.json"):
                state["active_contract"] = name
                try:
                    c = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    raise ValueError(f"Failed reading contract {name}: {exc}") from exc
                if not isinstance(c, dict):
                    raise ValueError(f"Contract artifact {name} is not a dict")
                ep = c.get("epoch", 0)
                if not isinstance(ep, int) or isinstance(ep, bool) or ep < 1:
                    raise ValueError(f"Invalid contract epoch in {name}: {ep}")
                state["epoch"] = ep
                if state.get("status") in ("draft", "hold"):
                    state["status"] = "running"
                    state["active_stage"] = "implementer"
            elif name.startswith("closure-") and name.endswith(".json") and not name.endswith(".meta.json"):
                try:
                    c = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    raise ValueError(f"Corrupt closure artifact {name}: {exc}") from exc
                if not isinstance(c, dict):
                    raise ValueError(f"Closure artifact {name} is not a dict")
                if not schemas.validate("closure", c):
                    state["closures_submitted"] = int(state.get("closures_submitted", 0)) + 1
                    reason = c.get("reason")
                    if reason == "blocked":
                        state["status"] = "hold"
            elif name.startswith("escalation-") and name.endswith(".json") and not name.endswith(".meta.json"):
                try:
                    esc = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    raise ValueError(f"Corrupt escalation artifact {name}: {exc}") from exc
                if not isinstance(esc, dict):
                    raise ValueError(f"Escalation artifact {name} is not a dict")
                res = esc.get("resolution")
                if isinstance(res, dict):
                    action = res.get("action")
                    grants = dict(state.get("grants") or {"oracle": 0, "implementer": 0, "live": 0, "curator": 0})
                    granted = res.get("attempts_granted")
                    if granted is not None and isinstance(granted, int):
                        stg = esc.get("stage", "implementer")
                        if stg in grants:
                            grants[stg] = int(grants.get(stg, 0)) + granted
                    elif action == "grant_attempts":
                        stg = esc.get("stage", "implementer")
                        cnt = res.get("count", res.get("grant", 1))
                        if isinstance(cnt, int) and stg in grants:
                            grants[stg] = int(grants.get(stg, 0)) + cnt
                    state["grants"] = grants
                    if action in ("grant_attempts", "waive_mutant", "update_scope", "retry_live"):
                        if state.get("status") == "hold":
                            state["status"] = "running"
                    elif res.get("status"):
                        state["status"] = str(res["status"])
                    elif esc.get("status") == "resolved":
                        if state.get("status") == "hold":
                            state["status"] = "running"
            elif (
                name.startswith("verification-")
                and name.endswith(".json")
                and not name.endswith(".meta.json")
            ):
                try:
                    ev = json.loads(p.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError) as exc:
                    raise ValueError(f"Corrupt verification artifact {name}: {exc}") from exc
                if not isinstance(ev, dict):
                    raise ValueError(f"verification artifact {name} is not a dict")
                ev_stage = ev.get("stage")
                attempts = dict(state.get("attempts") or {})
                if ev_stage in attempts:
                    attempts[ev_stage] = int(attempts.get(ev_stage, 0)) + 1
                else:
                    attempts["implementer"] = int(attempts.get("implementer", 0)) + 1
                state["attempts"] = attempts
                if ev.get("hard_cap") or (isinstance(ev.get("session"), dict) and ev["session"].get("hard_cap")):
                    state["hard_caps_tripped"] = int(state.get("hard_caps_tripped", 0)) + 1
                if ev.get("halt"):
                    state["status"] = "hold"

            for cand in (p.with_name(f"{p.name}.meta.json"), p.with_name(f"{p.stem}.meta.json")):
                if cand.is_file() and cand != p:
                    try:
                        meta = json.loads(cand.read_text(encoding="utf-8"))
                        mkind = meta.get("kind")
                        mseq = meta.get("seq", _n)
                        if mkind == "spec":
                            state["active_spec"] = f"spec-{mseq:03d}.md"
                        elif mkind == "solution_key":
                            state["active_solution_key"] = f"solution_key-{mseq:03d}.patch"
                        elif mkind == "oracle-draft":
                            state["active_oracle_draft"] = f"oracle-draft-{mseq:03d}"
                        elif mkind == "oracle":
                            state["active_oracle"] = f"oracle-{mseq:03d}"
                        elif mkind == "contract":
                            state["active_contract"] = f"contract-{mseq:03d}.json"
                    except (json.JSONDecodeError, OSError):
                        pass
                    break

        state["seq"] = max_seq
        state["repo"] = layout.repo
        errs = schemas.validate("state", state)
        if errs:
            raise ValueError(f"State validation failed during reconstruct: {errs}")
        _atomic_write(hw_path, f"{max_seq}\n".encode("utf-8"))
        _atomic_write(layout.state_file(tag), canonical_json(state) + b"\n")
        return max_seq
