#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-11: G4 AST analysis on thawed test/test_users.py via scope_overrides
# (oracle left intact). Positive class/async tests; hollow and syntax negatives.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p11" "good.patch")"
apply_scope_override "$SDIR" "bad_testcount.txt"

python3 - "$SDIR" "$WT" <<'PY'
import subprocess
import sys
from pathlib import Path

sdir, wt = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.verify import check_guards
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3.4: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"
test_file = wt / "test" / "test_users.py"
orig_content = test_file.read_text(encoding="utf-8")
oracle_scope = layout.sprint_dir(tag) / "oracle-003" / "scope.txt"
oracle_before = oracle_scope.read_bytes() if oracle_scope.is_file() else b""


def commit_test_content(new_text: str, msg: str) -> None:
    test_file.write_text(new_text, encoding="utf-8")
    env = {
        "PATH": "/usr/bin:/bin",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_CONFIG_SYSTEM": "/dev/null",
        "GIT_AUTHOR_NAME": "Cand",
        "GIT_AUTHOR_EMAIL": "c@example.test",
        "GIT_AUTHOR_DATE": "2026-01-02T00:00:00+0000",
        "GIT_COMMITTER_NAME": "Cand",
        "GIT_COMMITTER_EMAIL": "c@example.test",
        "GIT_COMMITTER_DATE": "2026-01-02T00:00:00+0000",
    }
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "add", "test/test_users.py"],
        cwd=wt, env=env, check=True,
    )
    subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false", "commit", "-q", "-m", msg],
        cwd=wt, env=env, check=True,
    )


# 0. G1 green on the thawed-via-override fixture
res_base = check_guards(layout, tag, wt)
g1 = next((r for r in res_base if r.id == "G1"), None)
if g1 is None or g1.exit_code != 0:
    print(f"FAIL: S1-R3.1: G1 must be green before G4 hollow-test cases, got {g1}")
    sys.exit(1)

# 1. Positive control: adding a real async test and a real class method test passes G4
valid_addition = orig_content + """

class TestExtraSuite:
    def test_class_method_real(self):
        val = 2 + 2
        assert val == 4

async def test_async_real():
    res = "ok"
    assert res == "ok"
"""
commit_test_content(valid_addition, "feat(actl): add valid class and async tests (WI-S1-TEST)")
res_ok = check_guards(layout, tag, wt)
g1_ok = next((r for r in res_ok if r.id == "G1"), None)
if g1_ok is None or g1_ok.exit_code != 0:
    print(f"FAIL: S1-R3.1: G1 turned red after valid test addition, got {g1_ok}")
    sys.exit(1)
g4_ok = next((r for r in res_ok if r.id == "G4"), None)
if g4_ok is None or g4_ok.exit_code != 0:
    print(f"FAIL: S1-R3.4: Valid class/async test additions should pass G4, got {g4_ok}")
    sys.exit(1)

# 2. Negative controls: each hollow variant and syntax error must fail G4
bad_variants = [
    ("pass_body", orig_content + "\ndef test_hollow_pass():\n    pass\n"),
    ("ellipsis_body", orig_content + "\ndef test_hollow_ellipsis():\n    ...\n"),
    ("docstring_only", orig_content + '\ndef test_hollow_doc():\n    """only doc"""\n'),
    ("assert_true", orig_content + "\ndef test_hollow_assert_true():\n    assert True\n"),
    ("syntax_error", orig_content + "\ndef test_broken(:\n"),
]

for label, body in bad_variants:
    commit_test_content(body, f"feat(actl): test variant {label} (WI-S1-TEST)")
    res = check_guards(layout, tag, wt)
    g1_i = next((r for r in res if r.id == "G1"), None)
    if g1_i is None or g1_i.exit_code != 0:
        print(f"FAIL: S1-R3.1: G1 must stay green on {label}, got {g1_i}")
        sys.exit(1)
    g4 = next((r for r in res if r.id == "G4"), None)
    if g4 is None or g4.exit_code != 1:
        print(f"FAIL: S1-R3.4: G4 failed to reject {label}: {g4}")
        sys.exit(1)

if oracle_scope.is_file() and oracle_scope.read_bytes() != oracle_before:
    print("FAIL: S1-R3.4: oracle-003/scope.txt was mutated; G4 thaw must use scope_overrides")
    sys.exit(1)
PY
