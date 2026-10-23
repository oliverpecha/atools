# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2, proof text only; not executed.
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for _p in (REPO / "src", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from actl import sprint  # noqa: E402
from actl.layout import Layout  # noqa: E402

GENV = dict(os.environ, GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null",
            GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e")


def git(*a, cwd):
    r = subprocess.run(["git", "-c", "core.hooksPath=/dev/null", *a], cwd=str(cwd), env=GENV,
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r.stdout.strip()


def commit(path, name):
    (path / name).write_text(name)
    git("add", "-A", cwd=path)
    git("commit", "-q", "-m", name, cwd=path)
    return git("rev-parse", "HEAD", cwd=path)


def mkrepo(path, branch="main", commits=2):
    path.mkdir(parents=True)
    git("init", "-q", "-b", branch, cwd=path)
    sha = None
    for i in range(commits):
        sha = commit(path, f"f{i}.txt")
    return sha


@pytest.fixture(autouse=True)
def iso(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    monkeypatch.setenv("ACTL_TODAY", "2026-10-16")


def helper(*names):
    for n in names:
        f = getattr(sprint, n, None)
        if f is not None:
            return f
    pytest.fail(f"FAIL: sprint has none of {names}", pytrace=False)


def new_sprint(lay, slug="demo-slug"):
    return sprint.create_sprint(lay, slug)


# ---------- base_sha = head of DEFAULT branch (S0-R4.4) ----------

def checked_out_other(lay):
    clone = lay.target_repo
    git("checkout", "-q", "-b", "feature", cwd=clone)
    return commit(clone, "feature.txt")


@pytest.mark.parametrize("branch", ["main", "master", "trunk"])
def test_base_sha_default_branch_with_origin_head_and_other_branch_checked_out(tmp_path, branch):
    src = tmp_path / "src"
    sha = mkrepo(src, branch)
    lay = Layout(tmp_path / "root")
    sprint.init_target(lay, str(src))
    head_feature = checked_out_other(lay)
    assert head_feature != sha
    r = new_sprint(lay)
    assert r["base_sha"] == sha and len(sha) == 40


@pytest.mark.parametrize("branch", ["main", "master"])
def test_base_sha_without_origin_head_other_branch_checked_out(tmp_path, branch):
    src = tmp_path / "src"
    sha = mkrepo(src, branch)
    lay = Layout(tmp_path / "root")
    sprint.init_target(lay, str(src))
    git("remote", "set-head", "origin", "-d", cwd=lay.target_repo)
    rc = subprocess.run(["git", "-C", str(lay.target_repo), "symbolic-ref", "refs/remotes/origin/HEAD"],
                        env=GENV, capture_output=True, text=True).returncode
    assert rc != 0
    checked_out_other(lay)
    assert new_sprint(lay)["base_sha"] == sha


def test_base_sha_main_preferred_over_master_without_origin_head(tmp_path):
    src = tmp_path / "src"
    sha_main = mkrepo(src, "main")
    git("checkout", "-q", "-b", "master", cwd=src)
    commit(src, "m.txt")
    git("checkout", "-q", "main", cwd=src)
    lay = Layout(tmp_path / "root")
    sprint.init_target(lay, str(src))
    git("remote", "set-head", "origin", "-d", cwd=lay.target_repo)
    git("checkout", "-q", "-B", "master", "origin/master", cwd=lay.target_repo)
    assert new_sprint(lay)["base_sha"] == sha_main


def test_duplicate_tag_is_value_error_and_leaves_sprint(tmp_path):
    src = tmp_path / "src"
    mkrepo(src)
    lay = Layout(tmp_path / "root")
    sprint.init_target(lay, str(src))
    new_sprint(lay)
    before = lay.state_file("2026-10-16_demo-slug").read_bytes()
    with pytest.raises(ValueError):
        new_sprint(lay)
    assert lay.state_file("2026-10-16_demo-slug").read_bytes() == before


# ---------- init_target ----------

def test_init_path_target_clones_and_is_idempotent(tmp_path):
    src = tmp_path / "src"
    sha = mkrepo(src)
    lay = Layout(tmp_path / "root")
    t = sprint.init_target(lay, str(src))
    assert t == lay.target_repo and (t / ".git").exists()
    assert git("rev-parse", "HEAD", cwd=t) == sha
    assert git("rev-list", "--count", "HEAD", cwd=t) == "2"
    (t / "marker").write_text("m")
    assert sprint.init_target(lay, str(src)) == t
    assert (t / "marker").exists()


def test_init_file_url_target_clones_and_is_idempotent(tmp_path):
    src = tmp_path / "src"
    sha = mkrepo(src)
    url = "file://" + str(src)
    lay = Layout(tmp_path / "root")
    t = sprint.init_target(lay, url)
    assert git("rev-parse", "HEAD", cwd=t) == sha
    (t / "marker").write_text("m")
    assert sprint.init_target(lay, url) == t
    assert (t / "marker").exists()
    assert new_sprint(lay)["base_sha"] == sha


def test_init_different_target_is_value_error_clone_intact(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    mkrepo(a)
    mkrepo(b)
    lay = Layout(tmp_path / "root")
    t = sprint.init_target(lay, str(a))
    (t / "marker").write_text("m")
    with pytest.raises(ValueError):
        sprint.init_target(lay, str(b))
    assert (t / "marker").exists()


def test_init_different_target_with_origin_symlink_loop_still_value_error(tmp_path):
    # Kills sprint.py:112 'and' -> 'or' on CPython <= 3.12 (mutant raises RuntimeError from resolve()).
    a, b = tmp_path / "a", tmp_path / "b"
    mkrepo(a)
    mkrepo(b)
    lay = Layout(tmp_path / "root")
    sprint.init_target(lay, str(a))
    l1, l2 = tmp_path / "loop1", tmp_path / "loop2"
    os.symlink(l2, l1)
    os.symlink(l1, l2)
    git("remote", "set-url", "origin", str(l1), cwd=lay.target_repo)
    with pytest.raises(ValueError):
        sprint.init_target(lay, str(b))


def test_init_non_git_and_invalid_targets(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    lay = Layout(tmp_path / "root")
    with pytest.raises(ValueError):
        sprint.init_target(lay, str(empty))
    with pytest.raises(ValueError):
        sprint.init_target(lay, "")
    with pytest.raises(ValueError):
        sprint.init_target(lay, "a\x00b")


# ---------- _is_git_repo branches (lines 65, 72, 77, 79) ----------

def test_is_git_repo_true_for_subdirectory_of_repo(tmp_path):
    isgit = helper("_is_git_repo", "is_git_repo")
    src = tmp_path / "src"
    mkrepo(src)
    sub = src / "sub"
    sub.mkdir()
    (sub / "f").write_text("x")
    assert isgit(str(sub)) is True  # line 65: rev-parse rc 0 decides; ls-remote would say False


def test_is_git_repo_false_for_plain_dir(tmp_path):
    isgit = helper("_is_git_repo", "is_git_repo")
    d = tmp_path / "plain"
    d.mkdir()
    assert isgit(str(d)) is False


def test_is_git_repo_file_url_true_and_output_captured(tmp_path, capfd):
    isgit = helper("_is_git_repo", "is_git_repo")
    src = tmp_path / "src"
    mkrepo(src)
    capfd.readouterr()
    assert isgit("file://" + str(src)) is True  # lines 77 and 72
    out, err = capfd.readouterr()
    assert out == "" and err == ""


def test_is_git_repo_file_url_missing_is_false_and_quiet(tmp_path, capfd):
    isgit = helper("_is_git_repo", "is_git_repo")
    capfd.readouterr()
    assert isgit("file://" + str(tmp_path / "nope")) is False
    out, err = capfd.readouterr()
    assert out == "" and err == ""


@pytest.mark.parametrize("exc", [OSError("boom"), subprocess.TimeoutExpired("git", 1)])
def test_is_git_repo_false_when_git_raises(tmp_path, monkeypatch, exc):
    isgit = helper("_is_git_repo", "is_git_repo")
    d = tmp_path / "d"
    d.mkdir()

    def boom(*a, **k):
        raise exc

    monkeypatch.setattr(subprocess, "run", boom)
    assert isgit(str(d)) is False  # line 79
    assert isgit("file://" + str(d)) is False


# ---------- CLI level ----------

def run_cli(args, root, cwd):
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"), ACTL_ROOT=str(root), ACTL_TODAY="2026-10-16",
               NO_COLOR="1", GIT_CEILING_DIRECTORIES=str(cwd.parent))
    return subprocess.run([sys.executable, "-m", "actl.cli", *args], env=env, cwd=str(cwd),
                          capture_output=True, text=True, timeout=240)


def test_cli_init_same_target_0_different_2_nongit_2_and_sprint_base_sha(tmp_path):
    cwd = tmp_path / "cwd"
    src, other, empty = tmp_path / "src", tmp_path / "other", tmp_path / "empty"
    sha = mkrepo(src, "trunk")
    mkrepo(other)
    empty.mkdir()
    root = tmp_path / "root"
    r = run_cli(["init", "--target", str(src), "--json"], root, cwd)
    assert r.returncode == 0, r.stderr
    d = json.loads(r.stdout)
    assert set(d) == {"actl_root", "target_repo", "base_sha", "created"}
    assert d["base_sha"] == sha
    assert run_cli(["init", "--target", str(src), "--json"], root, cwd).returncode == 0
    assert run_cli(["init", "--target", str(other), "--json"], root, cwd).returncode == 2
    assert run_cli(["init", "--target", str(empty), "--json"], tmp_path / "root2", cwd).returncode == 2
    git("checkout", "-q", "-b", "feature", cwd=root / "repos" / "target-repo")
    commit(root / "repos" / "target-repo", "feat.txt")
    r = run_cli(["sprint", "new", "demo-slug", "--json"], root, cwd)
    assert r.returncode == 0, r.stderr
    assert json.loads(r.stdout)["base_sha"] == sha
