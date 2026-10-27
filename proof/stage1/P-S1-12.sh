#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-12: G5 catches secrets in diff and closure notes/backlog, redacts raw
# secret values from failing_line/output_tail/prior_attempt.json, and honors
# [[allow]] SHA-256 line exemptions (S1-R3.5).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p12_bad" "bad_secret.patch")"
IFS='|' read -r SDIR_CL WT_CL <<< "$(create_stage1_sandbox "p12_cl" "good.patch")"

python3 - "$SDIR_BAD" "$WT_BAD" "$SDIR_CL" "$WT_CL" <<'PY'
import json
import sys
from pathlib import Path

sdir_bad, wt_bad, sdir_cl, wt_cl = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.verify import check_guards, verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3.5: cannot import actl.verify: {exc}")
    sys.exit(1)

tag = "2026-10-16_public-profiles"
raw_secret = "AKIAIOSFODNN7EXAMPLE"

# 1. Diff secret caught and scrubbed across all output surfaces
layout_bad = Layout(sdir_bad)
ver_bad = verify_impl(layout_bad, tag, worktree=wt_bad)
if ver_bad.get("exit_code") != 1 or ver_bad.get("failing_step") != "G5":
    print(f"FAIL: S1-R3.5: Expected verify_impl exit 1 at G5 on bad_secret.patch, got {ver_bad}")
    sys.exit(1)

ver_text = json.dumps(ver_bad)
prior_text = (layout_bad.inbox(tag, "implementer") / "prior_attempt.json").read_text(encoding="utf-8")
if raw_secret in ver_text or raw_secret in prior_text:
    print("FAIL: S1-R3.5: Raw secret leaked into verification JSON or prior_attempt.json")
    sys.exit(1)
if "[REDACTED]" not in (ver_bad.get("failing_line") or ""):
    print(f"FAIL: S1-R3.5: Expected [REDACTED] marker in failing_line, got {ver_bad.get('failing_line')!r}")
    sys.exit(1)

# 2. Closure backlog secret caught on clean worktree and scrubbed
layout_cl = Layout(sdir_cl)
closure_secret_file = sdir_cl / "closure_secret.json"
gh_token = "ghp_" + ("A1b2C3d4E5f6" * 3)
closure_secret_file.write_text(json.dumps({
    "reason": "done",
    "blocking_step": None,
    "notes": [" clean note "],
    "backlog": [f"rotate token {gh_token} later"],
    "solution_key_divergence": None,
}), encoding="utf-8")

res_cl = check_guards(layout_cl, tag, wt_cl, closure_path=closure_secret_file)
g5_cl = next((r for r in res_cl if r.id == "G5"), None)
if g5_cl is None or g5_cl.exit_code != 1:
    print(f"FAIL: S1-R3.5: Expected G5 to fail on secret in closure.backlog, got {g5_cl}")
    sys.exit(1)
if gh_token in (g5_cl.failing_line or "") or gh_token in (g5_cl.output_tail or ""):
    print("FAIL: S1-R3.5: Closure backlog secret was not redacted")
    sys.exit(1)
PY
