# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-03 / S0-R3: Layout. Modes are asserted with stat.S_IMODE(os.lstat(p).st_mode) (identical under UID 0 and non-root)."""
import json
import os
import stat

import pytest

from helpers import *  # noqa


def mode(p):
    return stat.S_IMODE(os.lstat(p).st_mode)


def _layout(tmp_path, repo="target-repo"):
    L = need_attr(need("actl.layout"), "Layout")
    return L(tmp_path / "root", repo=repo)


def test_paths_match_design_section_1_5(tmp_path):
    lay = _layout(tmp_path); r = (tmp_path / "root").resolve()
    if lay.root != r: fail("root must be resolved absolute")
    exp = {"records": r / "records", "target_repo": r / "repos" / "target-repo", "baseline_file": r / "baseline.json"}
    for k, v in exp.items():
        if getattr(lay, k) != v: fail("Layout.%s = %s, expected %s" % (k, getattr(lay, k), v))
    s = r / "records" / "target-repo" / TAG; runs = r / "sprints" / "target-repo" / TAG / "runs"
    checks = {"sprint_dir": s, "runs_dir": runs, "logs_dir": runs / "logs", "turns_dir": runs / "turns", "state_file": runs / "state.json",
              "state_lock": runs / "state.lock", "sessions_file": runs / "sessions.tsv", "sprint_toml": s / "sprint.toml", "mailboxes": r / "sprints" / "target-repo" / TAG / "mailboxes"}
    for k, v in checks.items():
        if getattr(lay, k)(TAG) != v: fail("Layout.%s(tag) = %s, expected %s" % (k, getattr(lay, k)(TAG), v))
    for role in ROLES:
        if lay.inbox(TAG, role) != r / "sprints" / "target-repo" / TAG / "mailboxes" / role / "inbox": fail("inbox(%s) wrong" % role)
        if lay.outbox(TAG, role) != r / "sprints" / "target-repo" / TAG / "mailboxes" / role / "outbox": fail("outbox(%s) wrong" % role)
        if lay.profile(role) != r / "profiles" / role: fail("profile(%s) wrong" % role)
    if lay.workspace("implementer-006", TAG) != r / "sprints" / "target-repo" / TAG / "workspaces" / "implementer-006": fail("workspace(name, tag) wrong")
    if lay.workspace("verify-implementer") != r / "sprints" / "target-repo" / TAG / "workspaces" / "verify-implementer": fail("workspace(name) wrong")


def test_default_root_from_env_and_home(tmp_path, monkeypatch):
    L = need_attr(need("actl.layout"), "Layout")
    monkeypatch.setenv("ACTL_ROOT", str(tmp_path / "fromenv"))
    if L().root != (tmp_path / "fromenv").resolve(): fail("default root must be $ACTL_ROOT")
    monkeypatch.delenv("ACTL_ROOT"); monkeypatch.setenv("HOME", str(tmp_path / "h"))
    if L().root != (tmp_path / "h" / "actl-graph").resolve(): fail("default root without ACTL_ROOT must be $HOME/actl-graph")
    with pytest.raises(ValueError): L("bad\x00root")


def test_base_tree_and_modes_applied_regardless_of_umask(tmp_path):
    lay = _layout(tmp_path)
    old = os.umask(0o077)
    try:
        lay.ensure_base_tree(); lay.ensure_base_tree()
        lay.ensure_sprint_tree(TAG); lay.ensure_sprint_tree(TAG)
    finally:
        os.umask(old)
    r = lay.root
    if sorted(p.name for p in r.iterdir()) != ["profiles", "records", "repos", "sprints"]:
        fail("base tree top level wrong: %s" % sorted(p.name for p in r.iterdir()))
    if not (r / "records").is_dir(): fail("records missing")
    if mode(r / "records") != 0o700: fail("records must be 0700, got %o" % mode(r / "records"))
    for d in ("sprints", "repos", "profiles"):
        if mode(r / d) != 0o755: fail("%s must be 0755, got %o" % (d, mode(r / d)))
    for role in ROLES:
        if not (r / "profiles" / role).is_dir(): fail("profiles/%s missing" % role)
        if mode(lay.inbox(TAG, role)) != 0o750: fail("%s inbox must be 0750, got %o" % (role, mode(lay.inbox(TAG, role))))
        if mode(lay.outbox(TAG, role)) != 0o770: fail("%s outbox must be 0770, got %o" % (role, mode(lay.outbox(TAG, role))))
    for p in (lay.sprint_dir(TAG), lay.runs_dir(TAG), lay.logs_dir(TAG), lay.turns_dir(TAG), lay.mailboxes(TAG)):
        if not p.is_dir(): fail("%s was not created by ensure_sprint_tree" % p)
    if (r / "profiles" / "README.md").is_file(): fail("ensure_base_tree must not write profiles/README.md (actl init only, L-8)")
    if (r / "repos" / "target-repo").exists(): fail("ensure_base_tree must not create repos/target-repo")


BAD_TAGS = ["", "..", ".", "../x", "/abs", "a/b", "2026-10-16", "2026-13-40_x", "2026-10-16_A", "2026-10-16_x\n", "x\x00y", "2026-10-16_a\\b"]


@pytest.mark.parametrize("tag", BAD_TAGS)
def test_traversal_and_bad_tags_rejected(tmp_path, tag):
    lay = _layout(tmp_path)
    for fn in (lay.sprint_dir, lay.runs_dir, lay.logs_dir, lay.turns_dir, lay.state_file, lay.state_lock, lay.sessions_file, lay.sprint_toml, lay.mailboxes):
        with pytest.raises(ValueError): fn(tag)
    with pytest.raises(ValueError): lay.inbox(tag, "architect")
    with pytest.raises(ValueError): lay.outbox(tag, "architect")


@pytest.mark.parametrize("role", ["", "root", "Architect", "../architect", "architect/", "implementer ", "actl"])
def test_unknown_roles_rejected(tmp_path, role):
    lay = _layout(tmp_path)
    for fn in (lambda: lay.inbox(TAG, role), lambda: lay.outbox(TAG, role), lambda: lay.profile(role)):
        with pytest.raises(ValueError): fn()


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "/a", "a\\b", "a\x00b", "a\x01b", "a\x7fb", "../x"])
def test_workspace_names_rejected(tmp_path, name):
    lay = _layout(tmp_path)
    with pytest.raises(ValueError): lay.workspace(name)
    with pytest.raises(ValueError): lay.workspace(name, TAG)


def test_repo_scoped_paths_with_default_name(tmp_path):
    L = need_attr(need("actl.layout"), "Layout")
    lay = L(tmp_path / "root")
    assert lay.repo == "target-repo"
    r = (tmp_path / "root").resolve()
    assert lay.target_repo == r / "repos" / "target-repo"
    assert lay.sprint_dir(TAG) == r / "records" / "target-repo" / TAG
    assert lay.runs_dir(TAG) == r / "sprints" / "target-repo" / TAG / "runs"


def test_two_repos_same_tag_no_collision(tmp_path):
    L = need_attr(need("actl.layout"), "Layout")
    r = (tmp_path / "root").resolve()
    lay1 = L(r, repo="cat_app")
    lay2 = L(r, repo="dog_app")
    assert lay1.repo == "cat_app"
    assert lay2.repo == "dog_app"
    assert lay1.sprint_dir(TAG) != lay2.sprint_dir(TAG)
    assert lay1.sprint_dir(TAG) == r / "records" / "cat_app" / TAG
    assert lay2.sprint_dir(TAG) == r / "records" / "dog_app" / TAG
    assert lay1.runs_dir(TAG) != lay2.runs_dir(TAG)
    assert lay1.runs_dir(TAG) == r / "sprints" / "cat_app" / TAG / "runs"
    assert lay2.runs_dir(TAG) == r / "sprints" / "dog_app" / TAG / "runs"


def test_wrong_repo_guard_rejects_mismatch(tmp_path):
    L = need_attr(need("actl.layout"), "Layout")
    seq = need("actl.seq")
    from actl.errors import StateIntegrityError
    r = (tmp_path / "root").resolve()
    lay_cat = L(r, repo="cat_app")
    lay_cat.ensure_sprint_tree(TAG)
    st = {"repo": "cat_app", "run_id": "run-123456789abc", "sprint_tag": TAG, "seq": 1, "epoch": 1,
          "status": "draft", "active_stage": "intake", "active_spec": None, "active_solution_key": None,
          "active_oracle_draft": None, "active_oracle": None, "active_contract": None,
          "attempts": {"oracle": 0, "implementer": 0, "live": 0, "curator": 0}, "closures_submitted": 0,
          "hard_caps_tripped": 0, "grants": {"oracle": 0, "implementer": 0, "live": 0, "curator": 0},
          "tmux_sessions": []}
    lay_cat.state_file(TAG).write_text(json.dumps(st))
    lay_dog = L(r, repo="dog_app")
    with pytest.raises(StateIntegrityError):
        seq.read_state(lay_dog, TAG)


def test_init_writes_profiles_readme(tmp_path):
    need_tool("git")
    tgt = tmp_path / "target"; build_golden(tgt)
    root = tmp_path / "root"
    r = run_actl(["init", "--target", str(tgt)], root=root)
    if r.returncode != 0: fail("init failed: %s" % r.stderr[-300:])
    readme = root / "profiles" / "README.md"
    assert readme.is_file(), "init must write profiles/README.md"
    content = readme.read_text(encoding="utf-8")
    assert "# profiles/" in content
    assert "One folder per persona account" in content


def test_renamed_artifact_kinds():
    ids = need("actl.ids")
    assert ids.format_artifact_id("verification", 7) == "verification-007"
    assert ids.format_artifact_filename("verification", 7) == "verification-007.json"
    assert ids.format_artifact_id("qualification", 4) == "qualification-004"
    assert ids.format_artifact_filename("qualification", 4) == "qualification-004.json"
    assert ids.parse_seq_from_name("verification-007.json") == 7
    assert ids.parse_seq_from_name("qualification-004.json") == 4
