# Authored-by: Vela-OPB (actl build assistant instance), as reported by the Owner, 2026-10-26
"""Hermetic tests for the small pure helpers of actl.doctor and for its _run wrapper."""
import sys
from pathlib import Path

import pytest

_SAVED_PATH = list(sys.path)
_SRC = str(Path(__file__).resolve().parents[2] / "src")
if _SRC not in sys.path:
    sys.path.insert(0, _SRC)

from actl import doctor  # noqa: E402

sys.path[:] = _SAVED_PATH

ZERO = {"pass": 0, "fail": 0, "skip": 0, "warn": 0}


def test_repo_root_is_the_checkout_that_holds_doctor_py():
    here = Path(doctor.__file__).resolve()
    assert (doctor.REPO_ROOT / "src" / "actl" / "doctor.py").resolve() == here


def test_run_captures_text_output_and_gives_the_child_no_stdin():
    code = "import sys; print('out'); sys.stderr.write('err'); print(repr(sys.stdin.read()))"
    r = doctor._run([sys.executable, "-c", code])
    assert isinstance(r.stdout, str)
    assert isinstance(r.stderr, str)
    assert r.stdout == "out\n''\n"
    assert r.stderr == "err"
    assert r.returncode == 0


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("tmux 3.4\n", "tmux 3.4"),
        ("a\nb\nc\n", "a"),
        ("only", "only"),
        ("", ""),
        (None, ""),
        ("  \n\t", ""),
    ],
)
def test_first_line(raw, expected):
    assert doctor._first_line(raw) == expected


def test_tail_keeps_the_last_twenty_lines_by_default():
    text = "\n".join("l%d" % i for i in range(1, 31))
    assert doctor._tail(text) == "\n".join("l%d" % i for i in range(11, 31))


def test_tail_keeps_the_last_two_thousand_characters_by_default():
    assert doctor._tail("x" * 3000) == "x" * 2000
    assert doctor._tail("x" * 2000) == "x" * 2000


def test_tail_honours_explicit_limits():
    assert doctor._tail("a\nb\nc", n=2) == "b\nc"
    assert doctor._tail("abcdef", max_chars=3) == "def"


def test_parse_audit_counts_defaults_to_zero():
    assert doctor._parse_audit_counts("") == ZERO
    assert doctor._parse_audit_counts("nothing relevant here") == ZERO


def test_parse_audit_counts_reads_the_key_first_form():
    text = "pass: 10\nfail=3\nskip : 2\nWARN: 4\n"
    assert doctor._parse_audit_counts(text) == {"pass": 10, "fail": 3, "skip": 2, "warn": 4}


def test_parse_audit_counts_reads_the_count_first_form():
    text = "49 pass, 0 fail, 18 skip, 2 warn"
    assert doctor._parse_audit_counts(text) == {"pass": 49, "fail": 0, "skip": 18, "warn": 2}
