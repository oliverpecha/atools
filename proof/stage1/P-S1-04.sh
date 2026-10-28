#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-04: bad_testcount.patch fails G4 when test/test_users.py is thawed via
# sprint_dir/scope_overrides (oracle left intact so G1 stays green) (S1-R3.4).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR_BAD WT_BAD <<< "$(create_stage1_sandbox "p04_bad" "bad_testcount.patch")"
IFS='|' read -r SDIR_OK WT_OK <<< "$(create_stage1_sandbox "p04_ok" "good.patch")"

apply_scope_override "$SDIR_BAD" "bad_testcount.txt"
apply_scope_override "$SDIR_OK" "bad_testcount.txt"

python3 - "$SDIR_OK" "$WT_OK" "$SDIR_BAD" "$WT_BAD" <<'PY'
import hashlib
import sys
from pathlib import Path

sdir_ok, wt_ok, sdir_bad, wt_bad = [Path(x) for x in sys.argv[1:5]]

try:
    from actl.verify import check_guards
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R3.4: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

exp = schemas.load_expected()["cases"]["bad_testcount"]["expect"]
tag = "2026-10-16_public-profiles"


def oracle_digest(layout) -> str:
    oracle = layout.sprint_dir(tag) / "oracle-003"
    h = hashlib.sha256()
    for p in sorted(oracle.rglob("*")):
        if p.is_file() and not p.is_symlink():
            h.update(p.relative_to(oracle).as_posix().encode("utf-8"))
            h.update(b"\0")
            h.update(p.read_bytes())
    return h.hexdigest()


layout_ok = Layout(sdir_ok)
digest_before = oracle_digest(layout_ok)

# 1. G1 must be green before G4 is interpreted (override lives outside the oracle)
res_ok = check_guards(layout_ok, tag, wt_ok)
g1_ok = next((r for r in res_ok if r.id == "G1"), None)
if g1_ok is None or g1_ok.exit_code != 0:
    print(f"FAIL: S1-R3.1: G1 must be green after scope override, got {g1_ok}")
    sys.exit(1)
g4_ok = next((r for r in res_ok if r.id == "G4"), None)
if g4_ok is None or g4_ok.exit_code != 0:
    print(f"FAIL: S1-R3.4: Expected G4 exit_code 0 when test count preserved, got {g4_ok}")
    sys.exit(1)

if oracle_digest(layout_ok) != digest_before:
    print("FAIL: S1-R3.4: Locked oracle directory was mutated by the G4 thaw")
    sys.exit(1)

# 2. Negative control: bad_testcount.patch drops a test -> G4 fails
layout_bad = Layout(sdir_bad)
res_bad = check_guards(layout_bad, tag, wt_bad)
g1_bad = next((r for r in res_bad if r.id == "G1"), None)
if g1_bad is None or g1_bad.exit_code != 0:
    print(f"FAIL: S1-R3.1: G1 must be green on bad_testcount fixture, got {g1_bad}")
    sys.exit(1)
g4_bad = next((r for r in res_bad if r.id == "G4"), None)
if g4_bad is None or g4_bad.exit_code != exp["exit"]:
    print(f"FAIL: S1-R3.4: Expected G4 exit_code {exp['exit']} on bad_testcount.patch, got {g4_bad}")
    sys.exit(1)
if exp["failing_line_contains"] not in (g4_bad.failing_line or ""):
    print(f"FAIL: S1-R3.4: G4 failing_line missing {exp['failing_line_contains']!r}: {g4_bad.failing_line!r}")
    sys.exit(1)
PY
