# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
"""P-S0-01 / S0-R1: actl doctor."""
import getpass
import json
import re
import shutil

from helpers import *  # noqa

TOP = {"version", "head_sha", "git_dirty", "git_status_porcelain", "ancestors", "tool_versions", "python_packages",
       "engine_clis", "timeout_available", "effective_user", "actl_root", "log_dir", "metadata_dir", "linger_state",
       "router_has_read_exit_code", "suites", "audit", "installed_sync_diffs", "warnings"}
SUITE_KEYS = {"present", "exit_code", "tail"}
AUDIT_KEYS = {"present", "exit_code", "pass", "fail", "skip", "warn", "self_test_exit_code", "tail"}


def _env(tmp_path):
    return {"ATOOLS_LOG_DIR": str(tmp_path / "logs"), "ATOOLS_SESSION_DIR": str(tmp_path / "sess")}


def _prepare(tmp_path):
    need_tool("tmux"); need_tool("git")
    repo = scratch_repo(tmp_path)
    if not (repo / "audit" / "atools-compliance_audit.sh").exists():
        envfail("audit/atools-compliance_audit.sh not present in the repo under test (D-9: Owner guarantees it)")
    return repo


def test_doctor_reports_every_field_with_correct_values(tmp_path):
    repo = _prepare(tmp_path)
    root = tmp_path / "root"
    porcelain_before = run(["git", "status", "--porcelain"], cwd=repo).stdout
    head = run(["git", "rev-parse", "HEAD"], cwd=repo).stdout.strip()
    r = run_actl(["doctor", "--json"], root=root, env=_env(tmp_path), repo=repo)
    if r.returncode != 0:
        fail("doctor exited %s: %s" % (r.returncode, r.stderr[-300:]))
    d = jsonout(r)
    if set(d) != TOP:
        fail("doctor JSON keys differ: missing %s extra %s" % (sorted(TOP - set(d)), sorted(set(d) - TOP)))
    if d["head_sha"] != head: fail("head_sha != git rev-parse HEAD")
    if not re.fullmatch(r"v[0-9]+\.[0-9]+\.[0-9]+.*", str(d["version"])): fail("version not like v0.1.x: %r" % d["version"])
    if set(d["ancestors"]) != {"5cb7f30", "759a0ca", "a9b3a4e", "4da9394"}: fail("ancestors keys wrong")
    if not all(isinstance(v, bool) for v in d["ancestors"].values()): fail("ancestors values must be bool")
    if set(d["tool_versions"]) != {"python3", "git", "tmux", "bash"}: fail("tool_versions keys wrong")
    if not str(d["tool_versions"]["tmux"]).startswith("tmux"): fail("tool_versions.tmux must come from `tmux -V`")
    if set(d["python_packages"]) != {"pytest", "jsonschema"}: fail("python_packages keys wrong")
    if set(d["engine_clis"]) != {"agent", "codex", "claude", "agy", "aider", "vibe"}: fail("engine_clis keys wrong")
    if d["effective_user"] != getpass.getuser(): fail("effective_user wrong")
    if d["actl_root"] not in (str(root.resolve()), str(root)): fail("actl_root wrong: %r" % d["actl_root"])
    if d["log_dir"] != str(tmp_path / "logs"): fail("log_dir must honour ATOOLS_LOG_DIR (F4)")
    if d["metadata_dir"] != str(tmp_path / "sess"): fail("metadata_dir must honour ATOOLS_SESSION_DIR (F4)")
    if not isinstance(d["timeout_available"], bool): fail("timeout_available must be bool")
    has = "def read_exit_code" in (repo / "src" / "router" / "process.py").read_text()
    if d["router_has_read_exit_code"] is not has: fail("router_has_read_exit_code probe wrong (expected %s)" % has)
    for s in ("engines", "session_persistence", "exit_code"):
        if set(d["suites"][s]) != SUITE_KEYS: fail("suites.%s keys wrong" % s)
    if set(d["audit"]) != AUDIT_KEYS: fail("audit keys wrong")
    if d["audit"]["present"] is not True: fail("audit.present must be true")
    if set(d["installed_sync_diffs"]) != {"hooks/pre-commit", "rules/git-safety.md", ".cursor/skills/atools-repair/SKILL.md"}:
        fail("installed_sync_diffs keys wrong")
    if not isinstance(d["warnings"], list): fail("warnings must be a list")
    if run(["git", "status", "--porcelain"], cwd=repo).stdout != porcelain_before:
        fail("doctor modified the repository (git status --porcelain changed)")
    base = root / "baseline.json"
    if not base.exists(): fail("baseline.json not written to ACTL_ROOT")
    if json.loads(base.read_text()) != d: fail("baseline.json differs from the --json report")


def test_baseline_written_once_and_refresh_overwrites(tmp_path):
    repo = _prepare(tmp_path)
    root = tmp_path / "root"; env = _env(tmp_path)
    r1 = run_actl(["doctor", "--json"], root=root, env=env, repo=repo)
    if r1.returncode != 0: fail("first doctor run exit %s" % r1.returncode)
    base = root / "baseline.json"
    if not base.exists(): fail("baseline.json not written on the first run")
    doc = json.loads(base.read_text()); doc["warnings"] = ["SENTINEL"]
    base.write_text(json.dumps(doc, indent=2))
    tampered = base.read_bytes()
    r2 = run_actl(["doctor", "--json"], root=root, env=env, repo=repo)
    if r2.returncode != 0: fail("second doctor run exit %s" % r2.returncode)
    if base.read_bytes() != tampered: fail("baseline.json was rewritten without --refresh (must be written first run only)")
    r3 = run_actl(["doctor", "--refresh", "--json"], root=root, env=env, repo=repo)
    if r3.returncode != 0: fail("--refresh run exit %s" % r3.returncode)
    if "SENTINEL" in base.read_text(): fail("--refresh did not overwrite baseline.json")


def test_missing_tmux_exits_4(tmp_path):
    repo = _prepare(tmp_path)
    bindir = tmp_path / "nobin"; bindir.mkdir()
    for n in ("python3", "git", "bash", "sh", "env", "cat", "grep", "sed", "awk", "head", "tail", "timeout", "diff", "mktemp",
              "rm", "cp", "mv", "mkdir", "sort", "ls", "dirname", "basename", "readlink", "date", "uname", "id", "whoami",
              "find", "xargs", "tr", "cut", "wc", "pgrep", "pkill", "sleep", "true", "false", "chmod", "touch", "tee", "stat", "realpath"):
        p = shutil.which(n)
        if p: (bindir / n).symlink_to(p)
    r = run_actl(["doctor", "--json"], root=tmp_path / "root", env={**_env(tmp_path), "PATH": str(bindir)}, repo=repo)
    if r.returncode != 4: fail("doctor without tmux must exit 4, got %s" % r.returncode)


def test_missing_audit_script_exits_4_and_records_not_found(tmp_path):
    repo = _prepare(tmp_path)
    shutil.rmtree(repo / "audit")
    r = run_actl(["doctor", "--json"], root=tmp_path / "root", env=_env(tmp_path), repo=repo)
    if r.returncode != 4: fail("doctor without the audit script must exit 4, got %s" % r.returncode)
    try:
        d = json.loads(r.stdout)
    except Exception:
        return
    if d.get("audit", {}).get("present") is not False: fail("audit.present must be false when the script is missing")
