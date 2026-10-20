# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""P-S0-05 / S0-R5: seq.reserve under concurrency and SIGKILL (reconstruct lives in test_p06_reconstruct.py)."""
import json
import signal
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from helpers import *  # noqa

WORKER = """
import sys
sys.path.insert(0, %r)
from actl.layout import Layout
from actl import seq
lay = Layout(%r)
for _ in range(int(sys.argv[1])):
    print(seq.reserve(lay, %r, "ev"), flush=True)
"""


def _setup(tmp_path):
    root = tmp_path / "root"; install_golden(root)
    need("actl.seq"); need("actl.layout")
    return root


def _spawn(root, n):
    return subprocess.Popen([sys.executable, "-c", WORKER % (str(SRC), str(root), TAG), str(n)], stdout=subprocess.PIPE, text=True)


def test_single_reserve_semantics(tmp_path):
    root = _setup(tmp_path)
    from actl.layout import Layout
    from actl import seq
    lay = Layout(root)
    n = seq.reserve(lay, TAG, "qual")
    if n != 6: fail("first reserve after the golden state (seq=5) must return 6, got %r" % n)
    st = json.loads(lay.state_file(TAG).read_text())
    if st["seq"] != 6: fail("state.json seq must equal the reserved number")
    if (lay.runs_dir(TAG) / "seq.highwater").read_text() != "6\n": fail("seq.highwater must hold '6' + newline")
    if seq.reserve(lay, TAG, "implementer") != 7: fail("kind 'implementer' must be accepted and monotonic")
    with pytest.raises(ValueError): seq.reserve(lay, TAG, "bogus-kind")
    with pytest.raises(ValueError): seq.reserve(lay, "../x", "ev")
    with pytest.raises(FileNotFoundError): seq.reserve(lay, "2026-10-17_absent", "ev")


def test_highwater_wins_over_lower_state_seq(tmp_path):
    root = _setup(tmp_path)
    from actl.layout import Layout
    from actl import seq
    lay = Layout(root)
    (lay.runs_dir(TAG) / "seq.highwater").write_text("40\n")
    if seq.reserve(lay, TAG, "ev") != 41: fail("reserve must use max(state.seq, highwater) + 1 (highwater=40, state=5)")


def test_fifty_parallel_processes_get_distinct_monotonic_numbers(tmp_path):
    root = _setup(tmp_path)
    procs = [_spawn(root, 5) for _ in range(10)]
    per = []
    for p in procs:
        out, _ = p.communicate(timeout=120)
        if p.returncode != 0: fail("worker exited %s" % p.returncode)
        per.append([int(x) for x in out.split()])
    flat = [x for l in per for x in l]
    if len(flat) != 50 or len(set(flat)) != 50: fail("expected 50 distinct numbers, got %d distinct of %d" % (len(set(flat)), len(flat)))
    if sorted(flat) != list(range(6, 56)): fail("numbers must be the contiguous range 6..55, got %s" % sorted(flat))
    for l in per:
        if l != sorted(l) or len(set(l)) != len(l): fail("per-process numbers must be strictly increasing: %s" % l)
    st = json.loads((root / "actl-repo" / "specs" / TAG / "runs" / "state.json").read_text())
    if st["seq"] != 55: fail("final state.seq must be 55, got %s" % st["seq"])


def test_threads_in_one_process_are_distinct(tmp_path):
    root = _setup(tmp_path)
    from actl.layout import Layout
    from actl import seq
    lay = Layout(root)
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda _: seq.reserve(lay, TAG, "ev"), range(40)))
    if len(set(res)) != 40: fail("threads obtained duplicate numbers")
    if sorted(res) != list(range(6, 46)): fail("thread numbers not contiguous")


def test_sigkill_mid_reserve_leaves_no_duplicate_and_valid_state(tmp_path):
    root = _setup(tmp_path)
    p = _spawn(root, 100000)
    seen = []
    deadline = time.time() + 60
    while len(seen) < 40 and time.time() < deadline:
        line = p.stdout.readline()
        if not line: break
        seen.append(int(line))
    p.send_signal(signal.SIGKILL); p.wait(timeout=30)
    seen += [int(x) for x in p.stdout.read().split()]
    if len(seen) < 10: fail("worker produced too few numbers (%d) to test a kill" % len(seen))
    if len(set(seen)) != len(seen): fail("duplicate numbers before the kill")
    runs = root / "actl-repo" / "specs" / TAG / "runs"
    try:
        json.loads((runs / "state.json").read_text())
    except Exception as e:
        fail("state.json unreadable after SIGKILL (non-atomic write?): %s" % e)
    hw = int((runs / "seq.highwater").read_text())
    if hw < max(seen): fail("highwater %d is below an already-returned number %d" % (hw, max(seen)))
    from actl.layout import Layout
    from actl import seq
    n = seq.reserve(Layout(root), TAG, "ev")
    if n <= max(seen) or n in seen: fail("post-kill reserve returned %d, not above every returned number (max %d)" % (n, max(seen)))
