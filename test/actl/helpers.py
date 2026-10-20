# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
"""Shared helpers for the Stage 0 proofs. No actl code is imported at module level (Red-on-Base: a missing module is a test FAILURE)."""
import importlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(os.environ.get("ACTL_REPO") or Path(__file__).resolve().parents[2]).resolve()
SRC = REPO / "src"
GOLDEN = Path(__file__).resolve().parents[2] / "fixtures" / "golden"
TAG = "2026-10-16_public-profiles"
ROLES = ("architect", "challenger", "implementer", "curator")
BASE_SHA = json.loads((GOLDEN / "expected.d" / "base.json").read_text())["base_sha"]


def fail(msg):
    pytest.fail("FAIL: " + msg, pytrace=False)


def envfail(msg):
    pytest.fail("ENVFAIL: " + msg, pytrace=False)


def need_tool(name):
    if shutil.which(name) is None:
        envfail("required tool not installed: " + name)


def need(modname):
    """Import an actl/router module or FAIL (never skip, never error)."""
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))
    try:
        return importlib.import_module(modname)
    except ImportError as exc:
        fail("module %s cannot be imported (%s)" % (modname, exc))


def need_attr(mod, name):
    obj = mod
    for part in name.split("."):
        if not hasattr(obj, part):
            fail("%s.%s is missing" % (mod.__name__, name))
        obj = getattr(obj, part)
    return obj


def run(cmd, env=None, cwd=None, timeout=240):
    e = os.environ.copy()
    e.update(env or {})
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True, env=e, cwd=cwd, timeout=timeout)


def run_actl(args, root=None, env=None, cwd=None, repo=None, timeout=240):
    repo = Path(repo) if repo else REPO
    exe = repo / "bin" / "actl"
    if not exe.exists():
        fail("bin/actl is missing (D-2)")
    e = {"ACTL_TODAY": "2026-10-16", "PYTHONDONTWRITEBYTECODE": "1"}
    e.update(env or {})
    if root is not None:
        e["ACTL_ROOT"] = str(root)
    return run([exe] + list(args), env=e, cwd=cwd, timeout=timeout)


def build_golden(dest):
    need_tool("git")
    r = run(["bash", GOLDEN / "build_golden.sh", dest])
    if r.returncode != 0:
        envfail("build_golden.sh failed: " + r.stderr)
    return r.stdout.strip()


def install_golden(root, tag=TAG):
    need_tool("git")
    r = run(["bash", GOLDEN / "build_golden.sh", "--install-sprint", root, "--tag", tag])
    if r.returncode != 0:
        envfail("build_golden.sh --install-sprint failed: " + r.stderr)
    return r.stdout.strip()


def scratch_repo(tmp_path, name="repo"):
    """A writable copy of the repo under test (for tests that must add/remove files)."""
    dst = Path(tmp_path) / name
    shutil.copytree(REPO, dst, symlinks=True, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", "out"))
    return dst


def sha256_file(p):
    import hashlib
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def tree_digest(root):
    """Independent digest of a directory tree (relative path, mode, content) for purity checks."""
    import hashlib
    h = hashlib.sha256()
    for d, dirs, files in os.walk(root):
        dirs.sort()
        for f in sorted(files):
            p = os.path.join(d, f)
            h.update(os.path.relpath(p, root).encode() + b"\0" + str(os.lstat(p).st_mode).encode() + b"\0")
            if os.path.isfile(p) and not os.path.islink(p):
                h.update(open(p, "rb").read())
    return h.hexdigest()


def jsonout(r):
    try:
        return json.loads(r.stdout)
    except Exception:
        fail("stdout is not a single JSON document (rc=%s): %r" % (r.returncode, r.stdout[:300]))
