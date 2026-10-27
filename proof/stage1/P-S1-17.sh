#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-17: scan_tripwires detects oracle/proofs access in dirty_ansi.log and
# dirty_oracle.jsonl, returns [] on clean.log and clean.jsonl, and enforces
# provenance-safe exclusions (GD-01 / GD-04 fix).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${REPO_DIR}/src"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p17" "good.patch")"

python3 - "$SDIR" "$WT" "$REPO_DIR" <<'PY'
import os
import shutil
import sys
from pathlib import Path

sdir, wt, repo_dir = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])

try:
    from actl.session import scan_tripwires
    from actl.verify import verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R10: cannot import actl modules: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

clean_log = repo_dir / "fixtures" / "golden" / "logs" / "clean.log"
dirty_log = repo_dir / "fixtures" / "golden" / "logs" / "dirty_ansi.log"
clean_jsonl = repo_dir / "fixtures" / "golden" / "transcripts" / "clean.jsonl"
dirty_jsonl = repo_dir / "fixtures" / "golden" / "transcripts" / "dirty_oracle.jsonl"

# 1. Clean log + clean transcript -> []
cursor_home = sdir / "cursor_home_clean"
cursor_home.mkdir(parents=True, exist_ok=True)
shutil.copy2(clean_jsonl, cursor_home / "clean.jsonl")
os.environ["ATOOLS_CURSOR_HOME"] = str(cursor_home)

hits_clean = scan_tripwires(layout, tag, 6, log_path=clean_log)
if hits_clean != []:
    print(f"FAIL: S1-R10.1: Expected [] on clean.log + clean.jsonl, got {hits_clean}")
    sys.exit(1)

# 2. Dirty ANSI log -> detects log tripwire with ANSI stripped
hits_dirty_log = scan_tripwires(layout, tag, 6, log_path=dirty_log)
if not hits_dirty_log or not any(h.get("source") == "log" for h in hits_dirty_log):
    print(f"FAIL: S1-R10.1: Failed to detect tripwire in dirty_ansi.log: {hits_dirty_log}")
    sys.exit(1)

# 3. Dirty JSONL transcript -> detects transcript tripwire while ignoring SKILL.md line
cursor_home_dirty = sdir / "cursor_home_dirty"
cursor_home_dirty.mkdir(parents=True, exist_ok=True)
shutil.copy2(dirty_jsonl, cursor_home_dirty / "dirty_oracle.jsonl")
os.environ["ATOOLS_CURSOR_HOME"] = str(cursor_home_dirty)

hits_dirty_tr = scan_tripwires(layout, tag, 6, log_path=clean_log)
tr_hits = [h for h in hits_dirty_tr if h.get("source") == "transcript"]
if len(tr_hits) < 2:
    print(f"FAIL: S1-R10.1: Expected >= 2 transcript hits from dirty_oracle.jsonl (records/ and proofs/01_public.sh), got {tr_hits}")
    sys.exit(1)

# 4. Provenance-safe exclusion test: line mentioning SKILL.md AND reading oracle proof MUST NOT be excluded
mixed_log = sdir / "mixed_evasion.log"
mixed_log.write_text(
    "Following skills/actl-implementer/SKILL.md; now running cat records/target-repo/oracle-003/proofs/01_public.sh\n",
    encoding="utf-8",
)
os.environ["ATOOLS_CURSOR_HOME"] = str(cursor_home)
hits_mixed = scan_tripwires(layout, tag, 6, log_path=mixed_log)
if not hits_mixed:
    print("FAIL: S1-R10.3: Provenance bypass! Line combining SKILL.md mention with oracle path access was erroneously excluded")
    sys.exit(1)

# 5. strict_tripwire=True on a green tree forces exit_code=1 and failing_step='tripwire'
os.environ["ATOOLS_CURSOR_HOME"] = str(cursor_home_dirty)
ver_strict = verify_impl(layout, tag, worktree=wt, strict_tripwire=True)
if ver_strict.get("exit_code") != 1 or ver_strict.get("failing_step") != "tripwire":
    print(f"FAIL: S1-R10.3: Expected strict_tripwire=True to force exit_code=1 and failing_step='tripwire', got {ver_strict}")
    sys.exit(1)

# 6. After an earlier fail-fast failure, tripwires are still populated
from actl.verify import check_guards  # noqa: F401
ver_ff = verify_impl(layout, tag, worktree=wt, fail_fast=True, strict_tripwire=True)
if not ver_ff.get("tripwires"):
    print("FAIL: S1-R1.5: scan_tripwires must still run after fail-fast; tripwires empty")
    sys.exit(1)
PY
