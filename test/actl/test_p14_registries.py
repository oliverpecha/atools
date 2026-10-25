# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-14 / S0-R13: cmd_*.py and next_rules/*.py are discovered without editing core files. Uses a SCRATCH copy of the repo."""
import json
import sys

import pytest

from helpers import *  # noqa

CMD = """import json

from actl.errors import EnvError, StateIntegrityError, UsageError


def register(subparsers):
    p = subparsers.add_parser("zzdummy", help="test-only dummy command")
    p.add_argument("mode")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=handler)


def handler(args, layout):
    m = args.mode
    if m == "usage":
        raise UsageError("u")
    if m == "integrity":
        raise StateIntegrityError("i")
    if m == "env":
        raise EnvError("e")
    if m == "red":
        return 1
    if m == "sysexit3":
        raise SystemExit(3)
    if args.json:
        print(json.dumps({"ok": True}))
    else:
        print("ok")
    return 0
"""
RULES = {'a_late': 'PRIORITY = 30\n\n\ndef evaluate(layout, tag, session_probe=None):\n    return {"action": "late", "command": "c30", "reason": "r30"}\n', 'b_early': 'PRIORITY = 10\n\n\ndef evaluate(layout, tag, session_probe=None):\n    return {"action": "early", "command": "c10", "reason": "r10"}\n', 'c_default': 'def evaluate(layout, tag, session_probe=None):\n    return {"action": "default", "command": "c100", "reason": "r100"}\n', '_private': 'PRIORITY = 1\n\n\ndef evaluate(layout, tag, session_probe=None):\n    return {"action": "private", "command": "x", "reason": "x"}\n', 'm2_tie': 'PRIORITY = 50\n\n\ndef evaluate(layout, tag, session_probe=None):\n    return {"action": "tie2", "command": "t2", "reason": "t2"}\n', 'm1_tie': 'PRIORITY = 50\n\n\ndef evaluate(layout, tag, session_probe=None):\n    return {"action": "tie1", "command": "t1", "reason": "t1"}\n', 'zz_none': 'PRIORITY = 5\n\n\ndef evaluate(layout, tag, session_probe=None):\n    return None\n'}
DRIVER = """
import json, sys
sys.path.insert(0, %r)
from actl.layout import Layout
from actl import next as nx
lay = Layout(%r)
print(json.dumps(nx.decide_next(lay, %r)))
"""
DISCOVER = """
import argparse, json, sys
sys.path.insert(0, %r)
from actl import cli
p = argparse.ArgumentParser(); sp = p.add_subparsers(dest="cmd", required=True)
try:
    print(json.dumps({"ok": cli.discover_commands(sp)}))
except (ImportError, AttributeError) as e:
    print(json.dumps({"raised": type(e).__name__}))
"""


def _decide(repo, root):
    r = run([sys.executable, "-c", DRIVER % (str(repo / "src"), str(root), TAG)], env={"PYTHONDONTWRITEBYTECODE": "1"})
    if r.returncode != 0: fail("decide_next crashed: %s" % r.stderr[-400:])
    return json.loads(r.stdout)


def _setstatus(root, status):
    p = root / "sprints" / "target-repo" / TAG / "runs" / "state.json"
    d = json.loads(p.read_text()); d["status"] = status; p.write_text(json.dumps(d))


def _clear(rd):
    for f in list(rd.glob("*.py")):
        if f.name != "__init__.py": f.unlink()


@pytest.fixture
def env(tmp_path):
    repo = scratch_repo(tmp_path); root = tmp_path / "root"; install_golden(root)
    rd = repo / "src" / "actl" / "next_rules"
    if not rd.is_dir(): fail("src/actl/next_rules/ missing")
    return repo, root, rd


def test_empty_registry_gives_noop(env):
    repo, root, rd = env
    _clear(rd)
    d = _decide(repo, root)
    if d != {"action": "noop", "command": "", "reason": "No matching rule for current sprint state"}: fail("empty registry must give the documented noop, got %s" % d)


def test_priority_order_default_100_tie_break_and_private_ignored(env):
    repo, root, rd = env
    _clear(rd)
    for n, body in RULES.items(): (rd / (n + ".py")).write_text(body)
    got = _decide(repo, root)
    if got["action"] != "early": fail("lowest PRIORITY must win (10; 5 returns None; _private is ignored), got %s" % got["action"])
    (rd / "b_early.py").unlink()
    got = _decide(repo, root)
    if got["action"] != "late": fail("after removing PRIORITY 10 the PRIORITY 30 rule must win, got %s" % got["action"])
    (rd / "a_late.py").unlink()
    got = _decide(repo, root)
    if got["action"] != "tie1": fail("equal PRIORITY ties break by module name (m1_tie < m2_tie), got %s" % got["action"])
    (rd / "m1_tie.py").unlink(); (rd / "m2_tie.py").unlink()
    got = _decide(repo, root)
    if got["action"] != "default": fail("a rule without PRIORITY defaults to 100, got %s" % got["action"])
    if set(got) != {"action", "command", "reason"}: fail("decide_next keys must be exactly action/command/reason")


def test_terminal_and_hold_states_precede_rules(env):
    repo, root, rd = env
    _clear(rd); (rd / "b_early.py").write_text(RULES["b_early"])
    for status, action in (("done", "done"), ("aborted", "aborted"), ("hold", "hold_owner")):
        _setstatus(root, status)
        got = _decide(repo, root)
        if got["action"] != action or got["command"] != "": fail("status %s must give action %s with empty command, got %s" % (status, action, got))


def test_decide_next_is_pure(env):
    repo, root, rd = env
    _clear(rd); (rd / "b_early.py").write_text(RULES["b_early"])
    before = tree_digest(root)
    _decide(repo, root); _decide(repo, root)
    if tree_digest(root) != before: fail("decide_next modified files under ACTL_ROOT")


def test_actl_next_cli_matches_decide_next_and_dummy_command_is_discovered(env):
    repo, root, rd = env
    _clear(rd); (rd / "b_early.py").write_text(RULES["b_early"])
    (repo / "src" / "actl" / "cmd_zz_dummy.py").write_text(CMD)
    r = run_actl(["next", "--sprint", TAG, "--json"], root=root, repo=repo)
    if r.returncode != 0: fail("actl next exit %s: %s" % (r.returncode, r.stderr[-300:]))
    if jsonout(r) != _decide(repo, root): fail("actl next --json must equal decide_next")
    r = run_actl(["zzdummy", "ok"], root=root, repo=repo)
    if r.returncode != 0 or "ok" not in r.stdout: fail("dummy cmd_*.py was not discovered (core files untouched)")


def test_discover_commands_sorted_and_strict(env):
    repo, root, rd = env
    cmds = repo / "src" / "actl"
    (cmds / "cmd_zz_dummy.py").write_text(CMD)
    r = run([sys.executable, "-c", DISCOVER % str(repo / "src")], env={"PYTHONDONTWRITEBYTECODE": "1"})
    try:
        names = json.loads(r.stdout).get("ok")
    except Exception:
        names = None
    if not names: fail("discover_commands failed: %s %s" % (r.stdout, r.stderr[-300:]))
    if names != sorted(names): fail("discover_commands must return a sorted list")
    for n in ("cmd_doctor", "cmd_init", "cmd_next", "cmd_sprint", "cmd_zz_dummy"):
        if n not in names: fail("%s not discovered: %s" % (n, names))
    (cmds / "cmd_zz_broken.py").write_text("X = 1\n")
    r = run([sys.executable, "-c", DISCOVER % str(repo / "src")], env={"PYTHONDONTWRITEBYTECODE": "1"})
    if "raised" not in r.stdout: fail("a cmd_*.py without register() must raise ImportError/AttributeError")
