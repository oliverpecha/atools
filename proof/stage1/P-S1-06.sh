#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-06: bad_forbidden.patch fails G6 with expected substring; good.patch passes G6 (S1-R3.6).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p06_ok" "good.patch")"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p06_bad" "bad_forbidden.patch")"

python3 - "$SDIR_OK" "$WT_OK" "$SDIR_BAD" "$WT_BAD" <<'PY'
import sys
from pathlib import Path

sdir_ok, wt_ok, sdir_bad, wt_bad = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.verify import check_guards
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R3.6: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

exp = schemas.load_expected()["cases"]["bad_forbidden"]["expect"]
tag = "2026-10-16_public-profiles"

# 1. Positive control: good.patch passes G6
res_ok = check_guards(Layout(sdir_ok), tag, wt_ok)
g6_ok = next((r for r in res_ok if r.id == "G6"), None)
if g6_ok is None or g6_ok.exit_code != 0:
    print(f"FAIL: S1-R3.6: Expected G6 exit_code 0 on good.patch, got {g6_ok}")
    sys.exit(1)

# 2. Negative control: bad_forbidden.patch fails G6
res_bad = check_guards(Layout(sdir_bad), tag, wt_bad)
g6_bad = next((r for r in res_bad if r.id == "G6"), None)
if g6_bad is None or g6_bad.exit_code != exp["exit"]:
    print(f"FAIL: S1-R3.6: Expected G6 exit_code {exp['exit']} on bad_forbidden.patch, got {g6_bad}")
    sys.exit(1)
if exp["failing_line_contains"] not in (g6_bad.failing_line or ""):
    print(f"FAIL: S1-R3.6: G6 failing_line missing {exp['failing_line_contains']!r}: {g6_bad.failing_line!r}")
    sys.exit(1)

# 3. Aliased os.system on an otherwise-green tree must fail G6 (AST)
import subprocess
layout_alias = Layout(sdir_ok)
profile_py = wt_ok / "api" / "profile.py"
orig_profile = profile_py.read_text(encoding="utf-8")
profile_py.write_text(orig_profile + "\nimport os as _o\n_o.system('echo hi')\n", encoding="utf-8")
env = {
    "PATH": "/usr/bin:/bin",
    "GIT_CONFIG_GLOBAL": "/dev/null",
    "GIT_CONFIG_SYSTEM": "/dev/null",
    "GIT_AUTHOR_NAME": "Cand",
    "GIT_AUTHOR_EMAIL": "c@example.test",
    "GIT_COMMITTER_NAME": "Cand",
    "GIT_COMMITTER_EMAIL": "c@example.test",
}
subprocess.run(["git", "-C", str(wt_ok), "-c", "core.hooksPath=/dev/null", "commit", "-q", "-a", "-m", "alias"], env=env, check=True)
res_alias = check_guards(layout_alias, tag, wt_ok)
g6_alias = next((r for r in res_alias if r.id == "G6"), None)
if g6_alias is None or g6_alias.exit_code != 1:
    print(f"FAIL: S1-R3.6: Expected G6 to reject aliased os.system, got {g6_alias}")
    sys.exit(1)

# 4. Syntax-invalid added Python still fails G6 via regex fallback
profile_py.write_text(orig_profile + "\neval(  # broken(\n", encoding="utf-8")
subprocess.run(["git", "-C", str(wt_ok), "-c", "core.hooksPath=/dev/null", "commit", "-q", "-a", "-m", "syntax"], env=env, check=True)
res_rx = check_guards(layout_alias, tag, wt_ok)
g6_rx = next((r for r in res_rx if r.id == "G6"), None)
if g6_rx is None or g6_rx.exit_code != 1:
    print(f"FAIL: S1-R3.6: Expected G6 regex fallback on syntax-invalid file, got {g6_rx}")
    sys.exit(1)
PY
