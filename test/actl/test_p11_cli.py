# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-11 / S0-R10: exit-code table, --json and NO_COLOR. A test-only dummy command is dropped into a SCRATCH copy of the repo."""
import json

import pytest

from helpers import *  # noqa

DUMMY = """import json

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


@pytest.fixture
def scratch(tmp_path):
    repo = scratch_repo(tmp_path)
    if not (repo / "src" / "actl").is_dir(): fail("src/actl package missing")
    (repo / "src" / "actl" / "cmd_zz_dummy.py").write_text(DUMMY)
    return repo, tmp_path / "root"


@pytest.mark.parametrize("mode,code", [("ok", 0), ("red", 1), ("usage", 2), ("integrity", 3), ("env", 4), ("sysexit3", 3)])
def test_handler_outcomes_map_to_exit_codes(scratch, mode, code):
    repo, root = scratch
    r = run_actl(["zzdummy", mode], root=root, repo=repo)
    if r.returncode != code: fail("zzdummy %s exited %s, expected %s (stderr: %s)" % (mode, r.returncode, code, r.stderr[-200:]))


@pytest.mark.parametrize("argv", [[], ["no-such-command"], ["sprint", "new"], ["sprint", "new", "Bad Slug"], ["zzdummy"], ["--no-such-flag"]])
def test_usage_errors_exit_2(scratch, argv):
    repo, root = scratch
    r = run_actl(argv, root=root, repo=repo)
    if r.returncode != 2: fail("argv %r exited %s, expected 2" % (argv, r.returncode))


def test_help_exits_0_as_plain_text(scratch):
    repo, root = scratch
    r = run_actl(["--help"], root=root, repo=repo, env={"NO_COLOR": "1"})
    if r.returncode != 0: fail("--help exited %s" % r.returncode)
    if "zzdummy" not in r.stdout: fail("--help must list discovered commands (registry)")
    for c in ("doctor", "init", "sprint", "next"):
        if c not in r.stdout: fail("--help lacks core command %s" % c)


def test_json_flag_yields_single_json_document(scratch):
    repo, root = scratch
    r = run_actl(["zzdummy", "ok", "--json"], root=root, repo=repo)
    if r.returncode != 0 or r.stdout.strip() == "" or json.loads(r.stdout) != {"ok": True}: fail("--json output wrong: rc=%s out=%r" % (r.returncode, r.stdout))
    r = run_actl(["zzdummy", "usage", "--json"], root=root, repo=repo)
    if r.returncode != 2: fail("usage error with --json must still exit 2, got %s" % r.returncode)
    if r.stdout.strip():
        try:
            doc = json.loads(r.stdout)
        except Exception:
            fail("with --json an error must print a single JSON document or nothing on stdout, got %r" % r.stdout[:200])
        if not isinstance(doc, dict): fail("error JSON must be an object")


@pytest.mark.parametrize("argv", [["--help"], ["zzdummy", "ok"], ["zzdummy", "usage"], ["sprint", "new", "BAD SLUG"]])
def test_no_color_means_no_ansi(scratch, argv):
    repo, root = scratch
    r = run_actl(argv, root=root, repo=repo, env={"NO_COLOR": "1", "FORCE_COLOR": "1", "TERM": "xterm-256color"})
    if r.returncode in (126, 127): fail("command could not be executed (rc=%s)" % r.returncode)
    if "\x1b[" in r.stdout + r.stderr: fail("NO_COLOR=1 output contains ANSI escapes for %r" % argv)
