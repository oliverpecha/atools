#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-12: G5 clean/exempted positive, secret negative, [[allow]] exemption,
# and redaction (S1-R3.5).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p12_ok" "good.patch")"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p12_bad" "bad_secret.patch")"
IFS='|' read -r SDIR_CL WT_CL <<< "$(create_stage1_sandbox "p12_cl" "good.patch")"

python3 - "$SDIR_OK" "$WT_OK" "$SDIR_BAD" "$WT_BAD" "$SDIR_CL" "$WT_CL" "$REPO_DIR" <<'PY'
import hashlib
import json
import os
import sys
from pathlib import Path

sdir_ok, wt_ok, sdir_bad, wt_bad, sdir_cl, wt_cl, repo_dir = [Path(x) for x in sys.argv[1:8]]

try:
    from actl.verify import check_guards, verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3.5: cannot import actl.verify: {exc}")
    sys.exit(1)

tag = "2026-10-16_public-profiles"
raw_secret = "AKIAIOSFODNN7EXAMPLE"

# 1. Clean positive: good.patch has no secrets -> G5 exit 0
res_ok = check_guards(Layout(sdir_ok), tag, wt_ok)
g5_ok = next((r for r in res_ok if r.id == "G5"), None)
if g5_ok is None or g5_ok.exit_code != 0:
    print(f"FAIL: S1-R3.5: Expected G5 exit 0 on clean good.patch, got {g5_ok}")
    sys.exit(1)

# 2. Diff secret caught and scrubbed
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

# 3. Closure backlog secret on an otherwise clean worktree
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

# 4. [[allow]] SHA-256 exemption via a scratch config (implementation must honor it)
import shutil
import subprocess
allowed_line = 'api_key = "0123456789abcdef"'
line_sha = hashlib.sha256(allowed_line.strip().encode("utf-8")).hexdigest()
scratch = sdir_ok / "allow_repo"
if scratch.exists():
    shutil.rmtree(scratch)
src_root = repo_dir / "src"
if not (src_root / "actl" / "verify.py").is_file():
    print("FAIL: S1-R3.5: actl.verify missing; [[allow]] scratch cannot run")
    sys.exit(1)
shutil.copytree(src_root, scratch / "src")
if (repo_dir / "schemas").is_dir():
    shutil.copytree(repo_dir / "schemas", scratch / "schemas")
(scratch / "config").mkdir(parents=True, exist_ok=True)
secrets_body = (
    "[[rules]]\n"
    'id = "S007"\n'
    'pattern = "(?i)(secret|token|passwd|password|api[_-]?key)\\s*[:=]\\s*[\'\\"][^\'\\"\\s]{16,}[\'\\"]"\n'
    'description = "generic"\n'
    "[[allow]]\n"
    'rule = "S007"\n'
    f'line_sha256 = "{line_sha}"\n'
)
(scratch / "config" / "secrets.toml").write_text(secrets_body, encoding="utf-8")
(scratch / "config" / "forbidden.toml").write_text("[[rules]]\nid='F001'\nkind='regex'\npattern='^$'\nmessage='x'\n", encoding="utf-8")
closure_allow = sdir_ok / "closure_allow.json"
closure_allow.write_text(json.dumps({
    "reason": "done",
    "blocking_step": None,
    "notes": [allowed_line],
    "backlog": [],
    "solution_key_divergence": None,
}), encoding="utf-8")
probe = r'''
import sys
from pathlib import Path
from actl.verify import check_guards
from actl.layout import Layout
layout = Layout(Path(sys.argv[1]))
tag = sys.argv[2]
wt = Path(sys.argv[3])
cl = Path(sys.argv[4])
res = check_guards(layout, tag, wt, closure_path=cl)
g5 = next((r for r in res if r.id == "G5"), None)
if g5 is None or g5.exit_code != 0:
    print(f"FAIL: S1-R3.5: [[allow]] exemption must pass G5, got {g5}")
    raise SystemExit(1)
'''
st = subprocess.run(
    [sys.executable, "-c", probe, str(sdir_ok), tag, str(wt_ok), str(closure_allow)],
    env={**dict(**{k: v for k, v in __import__("os").environ.items()}), "PYTHONPATH": __import__("os").environ.get("PYTHONPATH", "") + ":" + str(scratch / "src")},
    capture_output=True, text=True,
)
if st.returncode != 0:
    print(st.stdout + st.stderr)
    sys.exit(1)
PY
