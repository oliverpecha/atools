"""Sprint lifecycle: graph defaults, target init, create_sprint."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import tomllib

from actl.hashing import file_sha256
from actl.ids import mint_sprint_tag, validate_slug
from actl.layout import Layout
from actl import seq

REPO_ROOT = Path(__file__).resolve().parents[2]

SESSIONS_HEADER = (
    "seq\tsession\trole\tengine\tmodel\tmodel_family\tturns\ttool_calls\ttokens\t"
    "cost_usd\texit_code\taccepted_items\tescalation_alerts_sent\n"
)


def load_graph_defaults(config_path: Path | str | None = None) -> dict[str, Any]:
    if config_path is None:
        config_path = REPO_ROOT / "config" / "graph.toml"
    p = Path(config_path)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    try:
        return tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid graph.toml: {exc}") from exc


def load_sprint_toml(layout: Layout, tag: str) -> dict[str, Any]:
    p = layout.sprint_toml(tag)
    if not p.is_file():
        raise FileNotFoundError(str(p))
    try:
        return tomllib.loads(p.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"Invalid sprint.toml: {exc}") from exc


def _git_env() -> dict[str, str]:
    env = os.environ.copy()
    env["GIT_CONFIG_GLOBAL"] = "/dev/null"
    env["GIT_CONFIG_SYSTEM"] = "/dev/null"
    return env


def _is_git_repo(target: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=target if Path(target).exists() else None,
            capture_output=True,
            text=True,
            env=_git_env(),
            timeout=30,
        )
        if r.returncode == 0:
            return True
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        r = subprocess.run(
            ["git", "ls-remote", target],
            capture_output=True,
            text=True,
            env=_git_env(),
            timeout=60,
        )
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _origin_url(repo: Path) -> str | None:
    r = subprocess.run(
        ["git", "-C", str(repo), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
        env=_git_env(),
    )
    if r.returncode != 0:
        return None
    return r.stdout.strip()


def init_target(layout: Layout, target: str) -> Path:
    if not isinstance(target, str) or not target or "\x00" in target:
        raise ValueError("Invalid target")
    if not _is_git_repo(target):
        raise ValueError("Not a git repository")
    target_norm = str(Path(target).resolve()) if Path(target).exists() else target
    if layout.target_repo.exists():
        git_dir = layout.target_repo / ".git"
        if git_dir.exists():
            origin = _origin_url(layout.target_repo)
            if origin is not None:
                try:
                    origin_resolved = str(Path(origin).resolve()) if Path(origin).exists() else origin
                except OSError:
                    origin_resolved = origin
                if origin_resolved == target_norm or origin == target_norm:
                    return layout.target_repo
                # also compare resolved paths
                if Path(target).exists() and Path(origin).exists():
                    if Path(origin).resolve() == Path(target).resolve():
                        return layout.target_repo
        raise ValueError("target_repo already exists with a different origin")
    layout.ensure_base_tree()
    if Path(target).exists():
        cmd = [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "clone",
            "-q",
            "--local",
            "--no-hardlinks",
            target_norm,
            str(layout.target_repo),
        ]
    else:
        cmd = [
            "git",
            "-c",
            "core.hooksPath=/dev/null",
            "clone",
            "-q",
            target,
            str(layout.target_repo),
        ]
    r = subprocess.run(cmd, capture_output=True, text=True, env=_git_env())
    if r.returncode != 0:
        raise ValueError(f"git clone failed: {r.stderr.strip()}")
    return layout.target_repo


def _format_sprint_toml(
    tag: str,
    base_sha: str,
    status: str,
    spec_source: str,
    defaults: dict[str, Any],
    live_run_line: str = "",
) -> str:
    ma = defaults["max_attempts"]
    hc = defaults.get("hard_cap", {}).get("implementer", {})
    ort = defaults.get("owner_review_triggers", [])
    if ort:
        # rare in Stage 0A draft path; keep simple empty-list formatting for defaults
        items = ", ".join(f'"{x}"' for x in ort)
        ort_line = f"owner_review_triggers = [{items}]"
    else:
        ort_line = "owner_review_triggers = []"
    return (
        f'sprint_tag = "{tag}"\n'
        f'base_sha = "{base_sha}"\n'
        f'status = "{status}"\n'
        f'spec_source = "{spec_source}"\n'
        f"after = []\n"
        f"{live_run_line}"
        f'approval_live_run = "{defaults["approval_live_run"]}"\n'
        f'solution_key_exposure = "{defaults["solution_key_exposure"]}"\n'
        f"{ort_line}\n"
        f"min_attempts_before_block = {defaults['min_attempts_before_block']}\n"
        f"max_epochs = {defaults['max_epochs']}\n"
        f'repo_test_cmd = "{defaults["repo_test_cmd"]}"\n'
        f"\n"
        f"[max_attempts]\n"
        f"oracle = {ma['oracle']}\n"
        f"implementer = {ma['implementer']}\n"
        f"live = {ma['live']}\n"
        f"curator = {ma['curator']}\n"
        f"\n"
        f"[hard_cap.implementer]\n"
        f'wall_clock = "{hc.get("wall_clock", "45m")}"\n'
        f"turns = {hc.get('turns', 60)}\n"
    )


def create_sprint(
    layout: Layout, slug: str, spec_path: Path | str | None = None
) -> dict[str, Any]:
    if not validate_slug(slug):
        raise ValueError(f"Invalid slug: {slug!r}")
    sp: Path | None = None
    if spec_path is not None:
        sp = Path(spec_path)
        if not sp.is_file():
            raise FileNotFoundError(f"Spec file not found: {spec_path}")
    if not (layout.target_repo / ".git").exists():
        raise FileNotFoundError("Target repo not initialized")
    tag = mint_sprint_tag(slug)
    if layout.sprint_dir(tag).exists():
        raise ValueError(f"Sprint already exists: {tag}")
    r = subprocess.run(
        ["git", "-C", str(layout.target_repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
        env=_git_env(),
    )
    if r.returncode != 0:
        raise ValueError("Failed to resolve base_sha")
    base_sha = r.stdout.strip()
    defaults = load_graph_defaults()
    layout.ensure_sprint_tree(tag)
    layout.sessions_file(tag).write_text(SESSIONS_HEADER, encoding="utf-8")
    run_id = "run-" + hashlib.sha256(tag.encode("utf-8")).hexdigest()[:12]
    state: dict[str, Any] = {
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
    from actl.hashing import canonical_json

    layout.state_file(tag).write_bytes(canonical_json(state) + b"\n")

    if sp is not None:
        seq_num = seq.reserve(layout, tag, "spec")
        dest = layout.sprint_dir(tag) / "spec-001.md"
        dest.write_bytes(sp.read_bytes())
        meta = {
            "kind": "spec",
            "seq": 1,
            "parent": None,
            "sha256": file_sha256(sp),
        }
        (layout.sprint_dir(tag) / "spec-001.md.meta.json").write_text(
            json.dumps(meta, indent=2) + "\n", encoding="utf-8"
        )
        state = seq.update_state(
            layout,
            tag,
            {
                "active_spec": "spec-001.md",
            },
        )
        # note: update_state cannot set seq; reserve already set it
        spec_source = "imported"
        active_spec: str | None = "spec-001.md"
    else:
        spec_source = "architect_qna"
        active_spec = None
        seq_num = 0

    toml_text = _format_sprint_toml(
        tag, base_sha, "draft", spec_source, defaults, live_run_line=""
    )
    layout.sprint_toml(tag).write_text(toml_text, encoding="utf-8")

    return {
        "sprint_tag": tag,
        "slug": slug,
        "base_sha": base_sha,
        "sprint_dir": str(layout.sprint_dir(tag)),
        "handoff_dir": str(layout.handoff(tag)),
        "spec_source": spec_source,
        "active_spec": active_spec,
        "seq": seq_num,
    }
