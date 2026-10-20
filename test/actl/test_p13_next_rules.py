# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-29 (extra, S0-R13.2): table-driven state transitions of actl.next.decide_next, driven by one table rule in a SCRATCH repo.
(P-S0-13 is the global-hook proof; the registry-discovery proof is P-S0-14.)"""
import json
import sys

import pytest

from helpers import *  # noqa

TABLE_RULE = """PRIORITY = 20
import json

TABLE = {
    ("running", "implementer", 0): ("dispatch_impl", "actl dispatch-impl"),
    ("running", "implementer", 1): ("verify_impl", "actl verify-impl"),
    ("running", "oracle", 0): ("await_oracle", "actl wait"),
    ("draft", None, 0): ("start_intake", "actl bundle architect-intake"),
}


def evaluate(layout, tag, session_probe=None):
    s = json.loads(layout.state_file(tag).read_text())
    hit = TABLE.get((s["status"], s["active_stage"], s["closures_submitted"]))
    return {"action": hit[0], "command": hit[1], "reason": "table"} if hit else None
"""
DRIVER = """
import json, sys
sys.path.insert(0, %r)
from actl.layout import Layout
from actl import next as nx
print(json.dumps(nx.decide_next(Layout(%r), %r)))
"""
NOOP = {"action": "noop", "command": "", "reason": "No matching rule for current sprint state"}
ROWS = [  # status, active_stage, closures_submitted -> expected (action, command)
    ("draft", None, 0, ("start_intake", "actl bundle architect-intake")),
    ("running", "implementer", 0, ("dispatch_impl", "actl dispatch-impl")),
    ("running", "implementer", 1, ("verify_impl", "actl verify-impl")),
    ("running", "oracle", 0, ("await_oracle", "actl wait")),
    ("running", "curator", 0, ("noop", "")),
    ("running", "implementer", 2, ("noop", "")),
    ("done", "implementer", 0, ("done", "")),
    ("aborted", "oracle", 0, ("aborted", "")),
    ("hold", "implementer", 1, ("hold_owner", "")),
    ("hold", None, 0, ("hold_owner", "")),
]


@pytest.fixture
def world(tmp_path):
    repo = scratch_repo(tmp_path); root = tmp_path / "root"; install_golden(root)
    rd = repo / "src" / "actl" / "next_rules"
    if not rd.is_dir(): fail("src/actl/next_rules/ missing")
    for f in rd.glob("[!_]*.py"): f.unlink()
    (rd / "zz_table.py").write_text(TABLE_RULE)
    return repo, root


def _decide(repo, root):
    r = run([sys.executable, "-c", DRIVER % (str(repo / "src"), str(root), TAG)], env={"PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode != 0: fail("decide_next crashed: " + r.stderr[-400:])
    return json.loads(r.stdout)


def _set(root, **kw):
    p = root / "actl-repo" / "specs" / TAG / "runs" / "state.json"
    d = json.loads(p.read_text()); d.update(kw); p.write_text(json.dumps(d))


@pytest.mark.parametrize("status,stage,closures,want", ROWS)
def test_transition_table(world, status, stage, closures, want):
    repo, root = world
    _set(root, status=status, active_stage=stage, closures_submitted=closures)
    got = _decide(repo, root)
    exp = dict(zip(("action", "command"), want))
    if want[0] == "noop": exp = NOOP
    if got["action"] != exp["action"] or got["command"] != exp["command"]:
        fail("state (%s,%s,%s): got %s, expected %s" % (status, stage, closures, got, want))
    if set(got) != {"action", "command", "reason"}: fail("keys must be action/command/reason: %s" % sorted(got))


def test_sequence_follows_state_changes_without_caching(world):
    repo, root = world
    seq = [("running", "implementer", 0, "dispatch_impl"), ("running", "implementer", 1, "verify_impl"),
           ("hold", "implementer", 1, "hold_owner"), ("running", "implementer", 1, "verify_impl"), ("done", "implementer", 1, "done")]
    for st, sg, cl, act in seq:
        _set(root, status=st, active_stage=sg, closures_submitted=cl)
        if _decide(repo, root)["action"] != act: fail("after (%s,%s,%s) expected %s" % (st, sg, cl, act))


def test_terminal_precedes_matching_rule(world):
    repo, root = world
    _set(root, status="running", active_stage="implementer", closures_submitted=0)
    if _decide(repo, root)["action"] != "dispatch_impl": fail("precondition: table rule must match while running")
    _set(root, status="done")
    if _decide(repo, root)["action"] != "done": fail("status done must win over a matching rule")


def test_pure_no_writes(world):
    repo, root = world
    _set(root, status="running", active_stage="implementer", closures_submitted=0)
    before = tree_digest(root)
    for _ in range(3): _decide(repo, root)
    if tree_digest(root) != before: fail("decide_next wrote under ACTL_ROOT")


def test_unknown_sprint_raises_filenotfound(world):
    repo, root = world
    code = ("import sys; sys.path.insert(0,%r)\nfrom actl.layout import Layout\nfrom actl import next as nx\n"
            "try:\n    nx.decide_next(Layout(%r), '2026-10-17_absent')\nexcept FileNotFoundError:\n    print('FNF')\n") % (str(repo / "src"), str(root))
    r = run([sys.executable, "-c", code])
    if "FNF" not in r.stdout: fail("decide_next on a missing sprint must raise FileNotFoundError, got: %r %s" % (r.stdout, r.stderr[-200:]))
