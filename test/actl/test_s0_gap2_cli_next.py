# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2, proof text only; not executed.
import argparse
import importlib
import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for _p in (REPO / "src", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import actl  # noqa: E402
from actl import seq  # noqa: E402
from actl.layout import Layout  # noqa: E402

cli = importlib.import_module("actl.cli")
nxt = importlib.import_module("actl.next")
TAG = "2026-10-16_gap2-cli"
NOOP = {"action": "noop", "command": "", "reason": "No matching rule for current sprint state"}


def subparsers():
    return argparse.ArgumentParser(prog="t").add_subparsers(dest="command")


@pytest.fixture
def pkg(tmp_path, monkeypatch):
    d = tmp_path / "pkg"
    d.mkdir()
    monkeypatch.setattr(cli, "__file__", str(d / "cli.py"))
    monkeypatch.setattr(actl, "__path__", list(actl.__path__) + [str(d)])
    importlib.invalidate_caches()
    yield d
    for k in [k for k in sys.modules if k.startswith("actl.cmd_zz")]:
        del sys.modules[k]


def test_non_callable_register_raises_attribute_error(pkg):
    (pkg / "cmd_zz_bad.py").write_text("register = 5\n")
    with pytest.raises(AttributeError):  # cli.py:29 'or' -> 'and' would give TypeError
        cli.discover_commands(subparsers())


def test_missing_register_raises_attribute_error(pkg):
    (pkg / "cmd_zz_bad.py").write_text("x = 1\n")
    with pytest.raises(AttributeError):
        cli.discover_commands(subparsers())


def test_good_module_is_discovered(pkg):
    (pkg / "cmd_zz_ok.py").write_text("def register(sp):\n    sp.add_parser('zz-ok')\n")
    assert cli.discover_commands(subparsers()) == ["cmd_zz_ok"]


def test_stale_cmd_module_purged_and_live_ones_kept():
    # cli.py:21 is reachable: it purges sys.modules entries whose file vanished.
    stale = types.ModuleType("actl.cmd_zz_stale")
    stale.__file__ = "/nonexistent/dir/cmd_zz_stale.py"
    sys.modules["actl.cmd_zz_stale"] = stale
    try:
        stems = cli.discover_commands(subparsers())
        assert "actl.cmd_zz_stale" not in sys.modules
        for s in stems:
            assert f"actl.{s}" in sys.modules
    finally:
        sys.modules.pop("actl.cmd_zz_stale", None)


def mk(tmp_path):
    lay = Layout(tmp_path / "root")
    lay.ensure_sprint_tree(TAG)
    seq.reconstruct(lay, TAG)
    return lay


def test_next_missing_sprint_or_state_is_file_not_found(tmp_path):
    # next.py:23 'or' -> 'and' is equivalent for the exception type: read_state raises FileNotFoundError.
    lay = Layout(tmp_path / "root")
    with pytest.raises(FileNotFoundError):
        nxt.decide_next(lay, TAG)
    lay.ensure_sprint_tree(TAG)
    assert not lay.state_file(TAG).exists()
    with pytest.raises(FileNotFoundError):
        nxt.decide_next(lay, TAG)


def test_next_rule_with_no_spec_is_skipped(tmp_path, monkeypatch):
    lay = mk(tmp_path)
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "a.py").write_text("def evaluate(layout, tag, session_probe=None):\n    return None\n")
    monkeypatch.setattr(nxt, "RULES_DIR", rules)
    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **k: None)
    assert nxt.decide_next(lay, TAG) == NOOP  # next.py:47 'or' -> 'and' would raise AttributeError


def test_next_rule_with_spec_without_loader_is_skipped(tmp_path, monkeypatch):
    lay = mk(tmp_path)
    rules = tmp_path / "rules"
    rules.mkdir()
    (rules / "a.py").write_text("def evaluate(layout, tag, session_probe=None):\n    return None\n")
    monkeypatch.setattr(nxt, "RULES_DIR", rules)
    monkeypatch.setattr(importlib.util, "spec_from_file_location",
                        lambda *a, **k: types.SimpleNamespace(loader=None))
    assert nxt.decide_next(lay, TAG) == NOOP


def test_decide_next_raises_when_only_one_path_exists(tmp_path):
    lay = Layout(tmp_path / "root")
    tag = "2026-10-16_partial"
    # Case 1: directory exists, state file missing
    lay.sprint_dir(tag).mkdir(parents=True, exist_ok=True)
    with pytest.raises(FileNotFoundError, match="Sprint not found"):
        nxt.decide_next(lay, tag)
    
    # Case 2: state file exists, directory missing (parent deleted)
    # create both then remove directory contents/dir
    lay.ensure_sprint_tree(tag)
    import shutil
    shutil.rmtree(lay.sprint_dir(tag))
    with pytest.raises(FileNotFoundError, match="Sprint not found"):
        nxt.decide_next(lay, tag)
