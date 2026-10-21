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

import pytest

from actl import cli
from actl.errors import EnvError, StateIntegrityError, UsageError


@pytest.fixture
def fake_cli(monkeypatch, tmp_path):
    monkeypatch.setenv("ACTL_ROOT", str(tmp_path / "root"))
    monkeypatch.delenv("NO_COLOR", raising=False)

    def discover(subparsers):
        # Register --json on the main parser parent so flag_pos="before" parses
        if hasattr(subparsers, "_parser_class"):
            pass
        parser = getattr(subparsers, "_parser", None)
        if parser and not any(a.dest == "json" for a in parser._actions):
            parser.add_argument("--json", action="store_true", help="JSON output")
        p = subparsers.add_parser("zz-gap", help="test-only")
        p.add_argument("mode")
        p.add_argument("--json", action="store_true")

        def handler(args, layout):
            m = args.mode
            if m == "usage":
                raise UsageError("usage-msg-1")
            if m == "integrity":
                raise StateIntegrityError("integrity-msg-1")
            if m == "env":
                raise EnvError("env-msg-1")
            if m == "boom":
                raise ValueError("boom-msg-1")
            if m == "red":
                return 1
            if m == "none":
                return None
            return 0

        p.set_defaults(func=handler)
        return ["cmd_zz_gap"]

    monkeypatch.setattr(cli, "discover_commands", discover)


HANDLER_CASES = [
    ("usage", 2, "usage-msg-1"),
    ("integrity", 3, "integrity-msg-1"),
    ("env", 4, "env-msg-1"),
    ("boom", 3, "ValueError: boom-msg-1"),
]


def _doc(out):
    doc = json.loads(out)
    assert isinstance(doc, dict)
    return doc


# T8 -- kills: wrong code in any except-arm (UsageError 2 / StateIntegrityError 3 / EnvError 4 /
# generic Exception 3), exit_code in the JSON differing from the return code, "ok" true/missing,
# `--json` ignored or emitted only when the flag is after the subcommand, error text dropped.
@pytest.mark.parametrize("mode,code,msg", HANDLER_CASES)
@pytest.mark.parametrize("flag_pos", ["after", "before"])
def test_handler_errors_with_json(fake_cli, capsys, mode, code, msg, flag_pos):
    argv = ["zz-gap", mode, "--json"] if flag_pos == "after" else ["zz-gap", "--json", mode]
    rc = cli.main(argv)
    out, err = capsys.readouterr()
    assert rc == code
    doc = _doc(out)
    assert doc["ok"] is False
    assert doc["exit_code"] == code and type(doc["exit_code"]) is int
    assert isinstance(doc["error"], str) and msg in doc["error"]


@pytest.mark.parametrize("mode,code,msg", HANDLER_CASES)
def test_handler_errors_without_json_use_stderr_only(fake_cli, capsys, mode, code, msg):
    rc = cli.main(["zz-gap", mode])
    out, err = capsys.readouterr()
    assert rc == code
    assert out.strip() == ""
    assert msg in err


USAGE_ARGVS = [
    ["--json"],
    ["--json", "no-such-command"],
    ["zz-gap", "--json"],
    ["zz-gap", "ok", "--json", "--no-such-flag"],
]


@pytest.mark.parametrize("argv", USAGE_ARGVS, ids=lambda a: " ".join(a))
def test_usage_errors_with_json_print_ok_false_exit_2(fake_cli, capsys, argv):
    rc = cli.main(argv)
    out, err = capsys.readouterr()
    assert rc == 2
    doc = _doc(out)
    assert doc["ok"] is False
    assert doc["exit_code"] == 2 and type(doc["exit_code"]) is int
    assert isinstance(doc["error"], str) and doc["error"]


@pytest.mark.parametrize("argv", [[], ["no-such-command"], ["zz-gap"]], ids=repr)
def test_usage_errors_without_json_print_nothing_on_stdout(fake_cli, capsys, argv):
    rc = cli.main(argv)
    out, err = capsys.readouterr()
    assert rc == 2
    assert out.strip() == ""


def test_success_and_red_are_not_reported_as_errors(fake_cli, capsys):
    assert cli.main(["zz-gap", "ok", "--json"]) == 0
    assert capsys.readouterr().out.strip() == ""
    assert cli.main(["zz-gap", "none"]) == 0
    assert cli.main(["zz-gap", "red", "--json"]) == 1
    assert capsys.readouterr().out.strip() == ""


def test_help_exits_zero_with_plain_text_even_with_json(fake_cli, capsys):
    rc = cli.main(["--json", "--help"])
    out, _ = capsys.readouterr()
    assert rc == 0
    assert not out.lstrip().startswith("{")
