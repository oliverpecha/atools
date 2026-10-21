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

import json
import sys
import types

import pytest

from actl import next as nxt
from actl.layout import Layout

TAG = "2026-10-16_demo"
REC = "t9_gap_recorder"


@pytest.fixture
def env(tmp_path, monkeypatch):
    lay = Layout(tmp_path / "root")
    lay.ensure_sprint_tree(TAG)
    lay.state_file(TAG).write_text(json.dumps({"status": "draft"}), encoding="utf-8")
    pkg = tmp_path / "pkg"
    rules = pkg / "next_rules"
    rules.mkdir(parents=True)
    monkeypatch.setattr(nxt, "__file__", str(pkg / "next.py"))
    for name in dir(nxt):
        if name.upper().endswith("RULES_DIR"):
            monkeypatch.setattr(nxt, name, rules)
    rec = types.ModuleType(REC)
    rec.calls = []
    monkeypatch.setitem(sys.modules, REC, rec)
    yield lay, rules, rec
    for key in [k for k in sys.modules if k.startswith("actl.next_rules.zz_gap")]:
        del sys.modules[key]


def _write(rules, stem, body):
    (rules / f"{stem}.py").write_text(f"import {REC} as rec\nPRIORITY = 10\n{body}", encoding="utf-8")


def _probe(name):
    return {"name": name}


RESULT = {"action": "a-1", "command": "c-1", "reason": "r-1"}
RET = f"    return {RESULT!r}\n"


# T9 -- kills: signature inspection removed/inverted so session_probe is never passed to a rule
# that names it (positional-or-keyword or keyword-only), or is passed to rules that do not accept it.
@pytest.mark.parametrize("sig", ["layout, tag, session_probe=None", "layout, tag, *, session_probe=None"],
                         ids=["pos-or-kw", "kw-only"])
def test_rule_with_explicit_session_probe_param_receives_callable(env, sig):
    lay, rules, rec = env
    _write(rules, "zz_gap_explicit",
           f"def evaluate({sig}):\n    rec.calls.append((layout, tag, session_probe))\n{RET}")
    got = nxt.decide_next(lay, TAG, session_probe=_probe)
    assert got == RESULT
    assert len(rec.calls) == 1
    layout, tag, sp = rec.calls[0]
    assert tag == TAG and sp is _probe and callable(sp)


# T9 -- kills: VAR_KEYWORD detection dropped (a **kwargs rule would not get the probe).
def test_rule_with_var_keyword_receives_probe_as_keyword(env):
    lay, rules, rec = env
    _write(rules, "zz_gap_kwargs",
           f"def evaluate(layout, tag, **kwargs):\n    rec.calls.append(dict(kwargs))\n{RET}")
    assert nxt.decide_next(lay, TAG, session_probe=_probe) == RESULT
    assert rec.calls == [{"session_probe": _probe}]
    assert rec.calls[0]["session_probe"] is _probe


# T9 -- kills: probe passed unconditionally (TypeError for a plain rule) or positionally.
def test_rule_with_neither_is_called_with_layout_and_tag_only(env):
    lay, rules, rec = env
    _write(rules, "zz_gap_plain",
           f"def evaluate(layout, tag):\n    rec.calls.append((layout, tag))\n{RET}")
    assert nxt.decide_next(lay, TAG, session_probe=_probe) == RESULT
    assert len(rec.calls) == 1 and rec.calls[0][1] == TAG
    assert nxt.decide_next(lay, TAG) == RESULT
    assert len(rec.calls) == 2


# T9 -- kills: `except TypeError` fallback that retries / swallows (EAFP signature probing).
@pytest.mark.parametrize("sig", ["layout, tag", "layout, tag, session_probe=None", "layout, tag, **kw"])
def test_type_error_inside_rule_propagates_and_rule_runs_once(env, sig):
    lay, rules, rec = env
    _write(rules, "zz_gap_raises",
           f"def evaluate({sig}):\n    rec.calls.append(1)\n    raise TypeError('inside-rule-boom')\n")
    with pytest.raises(TypeError, match="inside-rule-boom"):
        nxt.decide_next(lay, TAG, session_probe=_probe)
    assert rec.calls == [1]

def test_next_decide_missing_layout_guards(tmp_path):
    from actl import next, layout
    # Line 21: if not layout.sprint_dir(tag).is_dir() or not layout.state_file(tag).is_file()
    lay = layout.Layout(tmp_path)
    # sprint dir missing
    with pytest.raises(FileNotFoundError):
        next.decide_next(lay, "2026-10-16_nonexistent")
    # sprint dir exists but state.json missing
    (tmp_path / "runs" / "2026-10-16_nostate").mkdir(parents=True)
    with pytest.raises(FileNotFoundError):
        next.decide_next(lay, "2026-10-16_nostate")

def test_next_rule_default_priority_tiebreak(tmp_path, monkeypatch):
    lay = Layout(tmp_path / "root")
    tag = "2026-10-16_demo"
    lay.ensure_sprint_tree(tag)
    lay.state_file(tag).write_text(json.dumps({"status": "draft"}), encoding="utf-8")

    rules_dir = tmp_path / "rules"
    rules_dir.mkdir(parents=True)
    monkeypatch.setattr(nxt, "RULES_DIR", rules_dir)

    # 1. aa_default (no PRIORITY) vs zz_explicit (PRIORITY = 100)
    # Default = 100 -> tie at 100 -> aa_default wins. Mutant > 100 -> zz_explicit wins.
    (rules_dir / "aa_default.py").write_text(
        "def evaluate(layout, tag, **kw):\n    return {'action': 'win_aa', 'command': '', 'reason': 'aa'}\n",
        encoding="utf-8",
    )
    (rules_dir / "zz_explicit.py").write_text(
        "PRIORITY = 100\ndef evaluate(layout, tag, **kw):\n    return {'action': 'win_zz', 'command': '', 'reason': 'zz'}\n",
        encoding="utf-8",
    )
    res = nxt.decide_next(lay, tag)
    assert res["action"] == "win_aa", "aa_default must win tiebreak against zz_explicit at priority 100"

    # 2. aa_explicit (PRIORITY = 100) vs zz_default (no PRIORITY)
    # Default = 100 -> tie at 100 -> aa_explicit wins. Mutant < 100 -> zz_default wins.
    rules_dir_2 = tmp_path / "rules_2"
    rules_dir_2.mkdir(parents=True)
    monkeypatch.setattr(nxt, "RULES_DIR", rules_dir_2)
    (rules_dir_2 / "aa_explicit.py").write_text(
        "PRIORITY = 100\ndef evaluate(layout, tag, **kw):\n    return {'action': 'win_aa_exp', 'command': '', 'reason': 'aa'}\n",
        encoding="utf-8",
    )
    (rules_dir_2 / "zz_default.py").write_text(
        "def evaluate(layout, tag, **kw):\n    return {'action': 'win_zz_def', 'command': '', 'reason': 'zz'}\n",
        encoding="utf-8",
    )
    res2 = nxt.decide_next(lay, tag)
    assert res2["action"] == "win_aa_exp", "aa_explicit must win tiebreak against zz_default at priority 100"


def test_next_rule_supports_match_function(tmp_path, monkeypatch):
    lay = Layout(tmp_path / "root")
    tag = "2026-10-16_demo"
    lay.ensure_sprint_tree(tag)
    lay.state_file(tag).write_text(json.dumps({"status": "draft"}), encoding="utf-8")

    rules_dir = tmp_path / "rules_match"
    rules_dir.mkdir(parents=True)
    monkeypatch.setattr(nxt, "RULES_DIR", rules_dir)

    (rules_dir / "rule_match.py").write_text(
        "def match(layout, tag, **kw):\n    return {'action': 'matched', 'command': 'cmd', 'reason': 'ok'}\n",
        encoding="utf-8",
    )
    res = nxt.decide_next(lay, tag)
    assert res["action"] == "matched"
