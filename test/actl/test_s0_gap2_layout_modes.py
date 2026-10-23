# Authored-by: Perplexity (underlying model undisclosed). Stage 0 gap round 2, proof text only; not executed.
import os
import stat
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REPO = Path(os.environ.get("ACTL_REPO") or HERE.parents[1]).resolve()
for _p in (REPO / "src", HERE):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from actl import seq  # noqa: E402
from actl.layout import Layout  # noqa: E402

TAG = "2026-10-16_gap2-layout"
ROLES = ("architect", "challenger", "implementer", "curator")


@pytest.fixture(params=[0o000, 0o022, 0o077], ids=["umask000", "umask022", "umask077"])
def umask(request):
    old = os.umask(request.param)
    yield request.param
    os.umask(old)


def mode(p):
    return stat.S_IMODE(os.lstat(p).st_mode)


def expected(lay, sprint):
    r = lay.root
    m = {r: 0o755, r / "actl-repo": 0o700, r / "actl-repo" / "specs": 0o755}
    for d in ("handoff", "workspaces", "repos", "homes"):
        m[r / d] = 0o755
    for role in ROLES:
        m[r / "homes" / role] = 0o755
    if sprint:
        sd = r / "actl-repo" / "specs" / TAG
        for p in (sd, sd / "runs", sd / "runs" / "logs", sd / "runs" / "turns", r / "handoff" / TAG):
            m[p] = 0o755
        for role in ROLES:
            m[r / "handoff" / TAG / f"{role}-inputs"] = 0o750
            m[r / "handoff" / TAG / f"{role}-outputs"] = 0o770
    return m


def found_dirs(root):
    out = {root}
    for dp, dns, _ in os.walk(root):
        for d in dns:
            out.add(Path(dp) / d)
    return out


def test_paths_agree_with_layout_accessors(tmp_path):
    lay = Layout(tmp_path / "root")
    r = lay.root
    assert lay.actl_repo == r / "actl-repo"
    assert lay.homes("curator") == r / "homes" / "curator"
    assert lay.inbox(TAG, "architect") == r / "handoff" / TAG / "architect-inputs"
    assert lay.outbox(TAG, "architect") == r / "handoff" / TAG / "architect-outputs"
    assert lay.logs_dir(TAG) == r / "actl-repo" / "specs" / TAG / "runs" / "logs"
    assert lay.turns_dir(TAG) == r / "actl-repo" / "specs" / TAG / "runs" / "turns"


def test_base_tree_exact_modes_and_exact_dir_set(tmp_path, umask):
    lay = Layout(tmp_path / "root")
    lay.ensure_base_tree()
    exp = expected(lay, False)
    for p, m in exp.items():
        assert mode(p) == m, f"{p}: {oct(mode(p))} != {oct(m)}"
    assert found_dirs(lay.root) == set(exp)
    assert not (lay.root / "repos" / "target-repo").exists()


def test_sprint_tree_exact_modes_and_exact_dir_set(tmp_path, umask):
    lay = Layout(tmp_path / "root")
    lay.ensure_sprint_tree(TAG)
    exp = expected(lay, True)
    for p, m in exp.items():
        assert mode(p) == m, f"{p}: {oct(mode(p))} != {oct(m)}"
    assert found_dirs(lay.root) == set(exp)


def test_modes_restored_on_second_call(tmp_path, umask):
    lay = Layout(tmp_path / "root")
    lay.ensure_sprint_tree(TAG)
    exp = expected(lay, True)
    for p in exp:
        os.chmod(p, 0o777)
    lay.ensure_sprint_tree(TAG)
    lay.ensure_base_tree()
    for p, m in exp.items():
        assert mode(p) == m, f"{p}: {oct(mode(p))} != {oct(m)}"


def test_lock_file_is_0600(tmp_path, umask):
    lay = Layout(tmp_path / "root")
    lay.ensure_sprint_tree(TAG)
    with seq.state_lock(lay, TAG):
        pass
    lock = lay.state_lock(TAG)
    assert lock.is_file()
    assert mode(lock) == 0o600
