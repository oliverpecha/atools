# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-04 / S0-R4: actl init and actl sprint new (CLI level)."""
import hashlib
import json
import re

import pytest

from helpers import *  # noqa

HEADER = "seq\tsession\trole\tengine\tmodel\tmodel_family\tturns\ttool_calls\ttokens\tcost_usd\texit_code\taccepted_items\tescalation_alerts_sent\n"
NEW_KEYS = {"sprint_tag", "slug", "base_sha", "sprint_dir", "handoff_dir", "spec_source", "active_spec", "seq"}


@pytest.fixture
def inited(tmp_path):
    need_tool("git")
    tgt = tmp_path / "target"; base = build_golden(tgt)
    root = tmp_path / "root"
    r = run_actl(["init", "--target", str(tgt), "--json"], root=root)
    if r.returncode != 0: fail("actl init exit %s: %s" % (r.returncode, r.stderr[-300:]))
    return root, tgt, base, r


def test_init_clones_target_and_reports(inited):
    root, tgt, base, r = inited
    d = jsonout(r)
    if set(d) != {"actl_root", "target_repo", "base_sha", "created"}: fail("init --json keys wrong: %s" % sorted(d))
    if d["base_sha"] != base or base != BASE_SHA: fail("init base_sha %s != golden %s" % (d["base_sha"], BASE_SHA))
    tr = root / "repos" / "target-repo"
    if not (tr / ".git").exists(): fail("target repo not cloned to repos/target-repo")
    if run(["git", "rev-parse", "HEAD"], cwd=tr).stdout.strip() != BASE_SHA: fail("clone HEAD differs from target HEAD")
    if run(["git", "rev-list", "--count", "HEAD"], cwd=tr).stdout.strip() != "1": fail("clone must preserve history (1 commit)")
    r2 = run_actl(["init", "--target", str(tgt), "--json"], root=root)
    if r2.returncode != 0: fail("init must be idempotent for the same target (exit %s)" % r2.returncode)


def test_init_rejects_other_target_and_non_repo(inited, tmp_path):
    root, tgt, base, _ = inited
    other = tmp_path / "other"; build_golden(other)
    r = run_actl(["init", "--target", str(other)], root=root)
    if r.returncode != 2: fail("init with a different target over an existing target-repo must exit 2, got %s" % r.returncode)
    empty = tmp_path / "notarepo"; empty.mkdir()
    r = run_actl(["init", "--target", str(empty)], root=tmp_path / "root2")
    if r.returncode != 2: fail("init with a non-git target must exit 2, got %s" % r.returncode)


def test_sprint_new_happy_path(inited):
    root, tgt, base, _ = inited
    r = run_actl(["sprint", "new", "demo", "--json"], root=root)
    if r.returncode != 0: fail("sprint new exit %s: %s" % (r.returncode, r.stderr[-300:]))
    d = jsonout(r)
    if set(d) != NEW_KEYS: fail("sprint new --json keys wrong: %s" % sorted(d))
    tag = "2026-10-16_demo"
    exp = {"sprint_tag": tag, "slug": "demo", "base_sha": BASE_SHA, "spec_source": "architect_qna", "active_spec": None, "seq": 0}
    for k, v in exp.items():
        if d[k] != v: fail("sprint new %s = %r, expected %r" % (k, d[k], v))
    sd = root / "actl-repo" / "specs" / tag
    if d["sprint_dir"] != str(sd) or d["handoff_dir"] != str(root / "handoff" / tag): fail("sprint_dir/handoff_dir wrong")
    for role in ROLES:
        if not (root / "handoff" / tag / (role + "-inputs")).is_dir() or not (root / "handoff" / tag / (role + "-outputs")).is_dir():
            fail("handoff dirs missing for %s" % role)
    if (sd / "runs" / "sessions.tsv").read_text() != HEADER: fail("sessions.tsv header must be exactly the S0-R4 header")
    st = json.loads((sd / "runs" / "state.json").read_text())
    want_run = "run-" + hashlib.sha256(tag.encode()).hexdigest()[:12]
    for k, v in {"run_id": want_run, "sprint_tag": tag, "seq": 0, "epoch": 1, "status": "draft", "active_spec": None,
                 "active_solution_key": None, "active_oracle_draft": None, "active_oracle": None, "active_contract": None,
                 "closures_submitted": 0, "hard_caps_tripped": 0}.items():
        if st.get(k) != v: fail("state.json %s = %r, expected %r" % (k, st.get(k), v))
    toml = (sd / "sprint.toml").read_text()
    if re.search(r"^live_run\b", toml, re.M): fail("draft sprint.toml must leave live_run UNSET (Design 4.1)")
    if 'status = "draft"' not in toml: fail('draft sprint.toml must contain status = "draft"')
    if 'base_sha = "%s"' % BASE_SHA not in toml: fail("sprint.toml must pin the 40-char base_sha")


def test_duplicate_tag_refused_and_untouched(inited):
    root, *_ = inited
    r = run_actl(["sprint", "new", "dup"], root=root)
    if r.returncode != 0: fail("first sprint new failed")
    p = root / "actl-repo" / "specs" / "2026-10-16_dup" / "sprint.toml"
    before = p.read_bytes()
    r = run_actl(["sprint", "new", "dup"], root=root)
    if r.returncode != 2: fail("duplicate sprint tag must exit 2, got %s" % r.returncode)
    if p.read_bytes() != before: fail("duplicate attempt modified the existing sprint")


@pytest.mark.parametrize("slug", ["", "a", "-ab", "Ab", "a_b", "a b", "a" * 42, "ab\n", "a/b", "..", "\u00e91"])
def test_bad_slugs_exit_2_and_create_nothing(inited, slug):
    root, *_ = inited
    r = run_actl(["sprint", "new", slug], root=root)
    if r.returncode != 2: fail("slug %r must exit 2, got %s" % (slug, r.returncode))
    specs = root / "actl-repo" / "specs"
    if specs.exists() and list(specs.iterdir()): fail("a rejected slug must not create anything under specs/")


@pytest.mark.parametrize("slug", ["ab", "a" * 41, "a-b", "a--b", "0a", "9" * 5])
def test_boundary_good_slugs(inited, slug):
    root, *_ = inited
    r = run_actl(["sprint", "new", slug, "--json"], root=root)
    if r.returncode != 0: fail("slug %r must be accepted, exit %s" % (slug, r.returncode))


def test_spec_import_allocates_seq_1(inited, tmp_path):
    root, *_ = inited
    spec = tmp_path / "myspec.md"; spec.write_bytes(b"# spec\nR1: x\n")
    r = run_actl(["sprint", "new", "imp", "--spec", str(spec), "--json"], root=root)
    if r.returncode != 0: fail("sprint new --spec exit %s: %s" % (r.returncode, r.stderr[-300:]))
    d = jsonout(r); tag = "2026-10-16_imp"; sd = root / "actl-repo" / "specs" / tag
    if d["seq"] != 1 or d["active_spec"] != "spec-001.md" or d["spec_source"] != "imported": fail("import fields wrong: %s" % d)
    if (sd / "spec-001.md").read_bytes() != spec.read_bytes(): fail("spec-001.md must be a byte copy of --spec")
    meta = json.loads((sd / "spec-001.md.meta.json").read_text())
    if meta.get("kind") != "spec" or meta.get("seq") != 1 or meta.get("sha256") != sha256_file(spec): fail("spec-001.md.meta.json wrong: %s" % meta)
    st = json.loads((sd / "runs" / "state.json").read_text())
    if st["seq"] != 1 or st["active_spec"] != "spec-001.md": fail("state.json after import wrong")
    if 'spec_source = "imported"' not in (sd / "sprint.toml").read_text(): fail("sprint.toml spec_source must be imported")
    if (sd / "runs" / "seq.highwater").read_text() != "1\n": fail("seq.highwater must hold '1' + newline after the import")


def test_missing_spec_file_exit_2(inited, tmp_path):
    root, *_ = inited
    r = run_actl(["sprint", "new", "nospec", "--spec", str(tmp_path / "absent.md")], root=root)
    if r.returncode != 2: fail("missing --spec file must exit 2, got %s" % r.returncode)
