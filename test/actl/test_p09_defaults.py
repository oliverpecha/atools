# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-09 / S0-R8: graph.toml defaults resolved into the draft sprint.toml (byte-exact)."""
import re
import tomllib

import pytest

from helpers import *  # noqa

TMPL = (GOLDEN / "expected_text" / "sprint.toml.tmpl").read_text()


def _render(tag, base, status="draft", source="architect_qna", live=""):
    return (TMPL.replace("{{sprint_tag}}", tag).replace("{{base_sha}}", base).replace("{{status}}", status)
            .replace("{{spec_source}}", source).replace("{{live_run_line}}", live))


def _init(tmp_path, repo=None):
    need_tool("git")
    tgt = tmp_path / "target"; build_golden(tgt)
    root = tmp_path / "root"
    r = run_actl(["init", "--target", str(tgt)], root=root, repo=repo)
    if r.returncode != 0: fail("init failed: %s" % r.stderr[-300:])
    return root


def test_graph_toml_values_and_illustrative_comment():
    p = REPO / "config" / "graph.toml"
    if not p.exists(): fail("config/graph.toml missing")
    text = p.read_text(); d = tomllib.loads(text)
    if not re.search(r"^\s*#.*illustrative", text, re.I | re.M): fail("graph.toml needs a comment stating the numbers are the Design's illustrative values")
    want = {"min_attempts_before_block": 2, "max_epochs": 3, "solution_key_exposure": "full", "approval_live_run": "architect", "owner_review_triggers": []}
    for k, v in want.items():
        if d.get(k) != v: fail("graph.toml %s = %r, expected %r" % (k, d.get(k), v))
    if d.get("max_attempts") != {"oracle": 3, "implementer": 2, "live": 2, "curator": 2}: fail("graph.toml max_attempts wrong")
    if d.get("hard_cap", {}).get("implementer") != {"wall_clock": "45m", "turns": 60}: fail("graph.toml hard_cap.implementer wrong")
    if not isinstance(d.get("repo_test_cmd"), str) or not d["repo_test_cmd"]: fail("graph.toml repo_test_cmd missing")
    if "live_run" in d: fail("live_run has no default and must not appear in graph.toml (Design 4.1)")


def test_load_graph_defaults_returns_parsed_toml():
    f = need_attr(need("actl.sprint"), "load_graph_defaults")
    if f() != tomllib.loads((REPO / "config" / "graph.toml").read_text()): fail("load_graph_defaults() must equal the parsed graph.toml")
    with pytest.raises(FileNotFoundError): f("/nonexistent/graph.toml")


def test_draft_sprint_toml_equals_golden_text(tmp_path):
    root = _init(tmp_path)
    r = run_actl(["sprint", "new", "demo"], root=root)
    if r.returncode != 0: fail("sprint new failed: %s" % r.stderr[-300:])
    got = (root / "actl-repo" / "specs" / "2026-10-16_demo" / "sprint.toml").read_text()
    want = _render("2026-10-16_demo", BASE_SHA)
    if got != want: fail("draft sprint.toml differs from expected_text/sprint.toml.tmpl:\n--- got\n%s--- want\n%s" % (got, want))


def test_imported_spec_variant_text(tmp_path):
    root = _init(tmp_path); spec = tmp_path / "s.md"; spec.write_text("# s\n")
    r = run_actl(["sprint", "new", "imp", "--spec", str(spec)], root=root)
    if r.returncode != 0: fail("sprint new --spec failed")
    got = (root / "actl-repo" / "specs" / "2026-10-16_imp" / "sprint.toml").read_text()
    if got != _render("2026-10-16_imp", BASE_SHA, source="imported"): fail("imported-spec draft sprint.toml text wrong")


def test_defaults_really_come_from_graph_toml(tmp_path):
    repo = scratch_repo(tmp_path)
    g = repo / "config" / "graph.toml"
    if not g.exists(): fail("config/graph.toml missing")
    t = g.read_text()
    if "max_epochs = 3" not in t: fail("graph.toml lacks the line 'max_epochs = 3'")
    g.write_text(t.replace("max_epochs = 3", "max_epochs = 7"))
    root = _init(tmp_path, repo=repo)
    r = run_actl(["sprint", "new", "demo"], root=root, repo=repo)
    if r.returncode != 0: fail("sprint new failed in the scratch repo: %s" % r.stderr[-300:])
    got = (root / "actl-repo" / "specs" / "2026-10-16_demo" / "sprint.toml").read_text()
    if "max_epochs = 7" not in got: fail("draft sprint.toml ignored the edited graph.toml (defaults are hard-coded)")
