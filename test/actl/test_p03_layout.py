# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-03 / S0-R3: Layout. Modes are asserted with stat.S_IMODE(os.lstat(p).st_mode) (identical under UID 0 and non-root)."""
import os
import stat

import pytest

from helpers import *  # noqa


def mode(p):
    return stat.S_IMODE(os.lstat(p).st_mode)


def _layout(tmp_path):
    L = need_attr(need("actl.layout"), "Layout")
    return L(tmp_path / "root")


def test_paths_match_design_section_1_5(tmp_path):
    lay = _layout(tmp_path); r = (tmp_path / "root").resolve()
    if lay.root != r: fail("root must be resolved absolute")
    exp = {"actl_repo": r / "actl-repo", "target_repo": r / "repos" / "target-repo", "baseline_file": r / "baseline.json"}
    for k, v in exp.items():
        if getattr(lay, k) != v: fail("Layout.%s = %s, expected %s" % (k, getattr(lay, k), v))
    s = r / "actl-repo" / "specs" / TAG; runs = s / "runs"
    checks = {"sprint_dir": s, "runs_dir": runs, "logs_dir": runs / "logs", "turns_dir": runs / "turns", "state_file": runs / "state.json",
              "state_lock": runs / "state.lock", "sessions_file": runs / "sessions.tsv", "sprint_toml": s / "sprint.toml", "handoff": r / "handoff" / TAG}
    for k, v in checks.items():
        if getattr(lay, k)(TAG) != v: fail("Layout.%s(tag) = %s, expected %s" % (k, getattr(lay, k)(TAG), v))
    for role in ROLES:
        if lay.inbox(TAG, role) != r / "handoff" / TAG / (role + "-inputs"): fail("inbox(%s) wrong" % role)
        if lay.outbox(TAG, role) != r / "handoff" / TAG / (role + "-outputs"): fail("outbox(%s) wrong" % role)
        if lay.homes(role) != r / "homes" / role: fail("homes(%s) wrong" % role)
    if lay.workspace("implementer-006", TAG) != r / "workspaces" / TAG / "implementer-006": fail("workspace(name, tag) wrong")
    if lay.workspace("verify-implementer") != r / "workspaces" / "verify-implementer": fail("workspace(name) wrong")


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
    if sorted(p.name for p in r.iterdir()) != ["actl-repo", "handoff", "homes", "repos", "workspaces"]:
        fail("base tree top level wrong: %s" % sorted(p.name for p in r.iterdir()))
    if not (r / "actl-repo" / "specs").is_dir(): fail("actl-repo/specs missing")
    if mode(r / "actl-repo") != 0o700: fail("actl-repo must be 0700, got %o" % mode(r / "actl-repo"))
    for d in ("handoff", "workspaces", "repos", "homes"):
        if mode(r / d) != 0o755: fail("%s must be 0755, got %o" % (d, mode(r / d)))
    for role in ROLES:
        if not (r / "homes" / role).is_dir(): fail("homes/%s missing" % role)
        if mode(lay.inbox(TAG, role)) != 0o750: fail("%s-inputs must be 0750, got %o" % (role, mode(lay.inbox(TAG, role))))
        if mode(lay.outbox(TAG, role)) != 0o770: fail("%s-outputs must be 0770, got %o" % (role, mode(lay.outbox(TAG, role))))
    for p in (lay.sprint_dir(TAG), lay.runs_dir(TAG), lay.logs_dir(TAG), lay.turns_dir(TAG), lay.handoff(TAG)):
        if not p.is_dir(): fail("%s was not created by ensure_sprint_tree" % p)
    if (r / "repos" / "target-repo").exists(): fail("ensure_base_tree must not create repos/target-repo")


BAD_TAGS = ["", "..", ".", "../x", "/abs", "a/b", "2026-10-16", "2026-13-40_x", "2026-10-16_A", "2026-10-16_x\n", "x\x00y", "2026-10-16_a\\b"]


@pytest.mark.parametrize("tag", BAD_TAGS)
def test_traversal_and_bad_tags_rejected(tmp_path, tag):
    lay = _layout(tmp_path)
    for fn in (lay.sprint_dir, lay.runs_dir, lay.logs_dir, lay.turns_dir, lay.state_file, lay.state_lock, lay.sessions_file, lay.sprint_toml, lay.handoff):
        with pytest.raises(ValueError): fn(tag)
    with pytest.raises(ValueError): lay.inbox(tag, "architect")
    with pytest.raises(ValueError): lay.outbox(tag, "architect")


@pytest.mark.parametrize("role", ["", "root", "Architect", "../architect", "architect/", "implementer ", "actl"])
def test_unknown_roles_rejected(tmp_path, role):
    lay = _layout(tmp_path)
    for fn in (lambda: lay.inbox(TAG, role), lambda: lay.outbox(TAG, role), lambda: lay.homes(role)):
        with pytest.raises(ValueError): fn()


@pytest.mark.parametrize("name", ["", ".", "..", "a/b", "/a", "a\\b", "a\x00b", "a\x01b", "a\x7fb", "../x"])
def test_workspace_names_rejected(tmp_path, name):
    lay = _layout(tmp_path)
    with pytest.raises(ValueError): lay.workspace(name)
    with pytest.raises(ValueError): lay.workspace(name, TAG)
