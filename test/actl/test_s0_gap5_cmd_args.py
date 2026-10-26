# Authored-by: Gemini Flash 3.8 High (Google), as reported by the Owner, 2026-10-26
# Revised-by: Vela-OPB, 2026-10-26, applying the GPT 6.1 Sol review conditions (sys.path restore, Layout guard, direct rc asserts, narrow patches, hermetic doctor)
"""Required command arguments and subcommands: argparse message on stderr plus exit code 2."""
import argparse
import sys
from pathlib import Path

import pytest

_SAVED_PATH = list(sys.path)
_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from actl import cli, cmd_init, cmd_next, cmd_sprint  # noqa: E402

sys.path[:] = _SAVED_PATH

PHRASE = "the following arguments are required"


def _no_layout(*args, **kwargs):
    raise AssertionError("argument parsing unexpectedly succeeded: Layout() was reached")


@pytest.fixture
def guard_layout(monkeypatch, tmp_path):
    monkeypatch.setenv("ACTL_ROOT", str(tmp_path / "root"))
    monkeypatch.setattr(cli, "Layout", _no_layout)


def _parse_direct(register, argv, capsys):
    parser = argparse.ArgumentParser(prog="actl")
    sp = parser.add_subparsers(dest="cmd")
    register(sp)
    with pytest.raises(SystemExit) as exc_info:
        parser.parse_args(argv)
    assert exc_info.value.code == 2
    return capsys.readouterr().err


def test_cmd_init_target_required(capsys):
    err = _parse_direct(cmd_init.register, ["init"], capsys)
    assert PHRASE in err
    assert "--target" in err


def test_cmd_init_target_required_via_main(capsys, guard_layout):
    assert cli.main(["init"]) == 2
    err = capsys.readouterr().err
    assert PHRASE in err
    assert "--target" in err


def test_cmd_sprint_subcommand_required(capsys):
    err = _parse_direct(cmd_sprint.register, ["sprint"], capsys)
    assert PHRASE in err
    assert "sprint_cmd" in err


def test_cmd_sprint_subcommand_required_via_main(capsys, guard_layout):
    assert cli.main(["sprint"]) == 2
    err = capsys.readouterr().err
    assert PHRASE in err
    assert "sprint_cmd" in err


def test_cmd_next_sprint_required(capsys):
    err = _parse_direct(cmd_next.register, ["next"], capsys)
    assert PHRASE in err
    assert "--sprint" in err


def test_cmd_next_sprint_required_via_main(capsys, guard_layout):
    assert cli.main(["next"]) == 2
    err = capsys.readouterr().err
    assert PHRASE in err
    assert "--sprint" in err
