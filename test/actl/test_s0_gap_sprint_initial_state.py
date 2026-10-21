# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-21), model family: Claude
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parents[1]
for _p in (_REPO / "src", _HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
try:
    import helpers  # noqa: F401  (side effects: path setup only)
except Exception:  # helpers is optional for these tests
    pass

import hashlib
import json
import os
import subprocess

import pytest

from actl import sprint
from actl.layout import Layout


def _git(*args, cwd=None):
    env = dict(os.environ, GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_SYSTEM=os.devnull,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True)


@pytest.fixture
def lay(tmp_path):
    layout = Layout(tmp_path / "actl-root")
    repo = layout.target_repo
    repo.mkdir(parents=True)
    _git("init", "-q", cwd=repo)
    _git("-c", "commit.gpgsign=false", "commit", "--allow-empty", "-q", "-m", "init", cwd=repo)
    return layout


def _strict_ints(obj, path="state"):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _strict_ints(v, f"{path}.{k}")
    elif isinstance(obj, (bool, int)):
        assert type(obj) is int, f"{path} must be a real int, got {obj!r}"


# T7 -- kills: any literal mutation in create_sprint's initial state dict
# (a counter 0->1, epoch 1->0, status "draft"->other, an active_* None->"", tmux_sessions [] ->
# non-empty, a missing/extra key, bool instead of int, wrong run_id derivation).
def test_create_sprint_exact_initial_state(lay):
    res = sprint.create_sprint(lay, "demo")
    tag = res["sprint_tag"]
    st = json.loads(lay.state_file(tag).read_text(encoding="utf-8"))
    zero_roles = {"curator": 0, "implementer": 0, "live": 0, "oracle": 0}
    expected = {
        "active_contract": None, "active_oracle": None, "active_oracle_draft": None,
        "active_solution_key": None, "active_spec": None, "active_stage": None,
        "attempts": dict(zero_roles),
        "closures_submitted": 0,
        "epoch": 1,
        "grants": dict(zero_roles),
        "hard_caps_tripped": 0,
        "run_id": "run-" + hashlib.sha256(tag.encode("utf-8")).hexdigest()[:12],
        "seq": 0,
        "sprint_tag": tag,
        "status": "draft",
        "tmux_sessions": [],
    }
    assert st == expected
    assert set(st) == set(expected)
    _strict_ints(st)
    assert st["tmux_sessions"] == [] and isinstance(st["tmux_sessions"], list)
    for k in ("active_contract", "active_oracle", "active_oracle_draft",
              "active_solution_key", "active_spec", "active_stage"):
        assert st[k] is None, k
    assert res["seq"] == 0

def test_sprint_new_captures_default_branch(tmp_path):
    import subprocess
    from actl import sprint, layout
    target = tmp_path / "target_repo"
    target.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=target, check=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=target, check=True)
    (target / "file.txt").write_text("v1")
    subprocess.run(["git", "add", "file.txt"], cwd=target, check=True)
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-m", "initial on main"], cwd=target, check=True)
    main_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target, capture_output=True, text=True, check=True).stdout.strip()
    
    # Create feature branch with a second commit and switch to it
    subprocess.run(["git", "checkout", "-b", "feature-branch"], cwd=target, check=True)
    (target / "file.txt").write_text("v2")
    subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "commit", "-am", "commit on feature"], cwd=target, check=True)
    
    # Create sprint: base_sha must equal main_sha, not the current feature checkout
    lay = layout.Layout(tmp_path / "actl-root")
    # Move target repository into lay.target_repo
    lay.target_repo.parent.mkdir(parents=True, exist_ok=True)
    target.rename(lay.target_repo)
    
    sprint.create_sprint(lay, "testslug")
    sprint_dirs = list((lay.root / "actl-repo" / "specs").glob("*_testslug"))
    assert len(sprint_dirs) == 1
    st_file = sprint_dirs[0] / "sprint.toml"
    assert f'base_sha = "{main_sha}"' in st_file.read_text(encoding="utf-8")
