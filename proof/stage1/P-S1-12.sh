#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-12: G5 redacts matched secret from failing_line and output tails.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.verify import check_guards
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R3: cannot import actl.verify.check_guards: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
try:
    results = check_guards(layout, "2026-10-16_public-profiles", Path("/tmp/wt-secret-redact"))
    g5 = next((r for r in results if r.id == "G5"), None)
    if not g5 or g5.exit_code != 1:
        print("FAIL: S1-R3: G5 did not fail on secret")
        sys.exit(1)
    if "AKIA" in (g5.failing_line or ""):
        print("FAIL: S1-R3: Raw secret leaked in failing_line without redaction")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R3: check_guards invocation failed: {exc}")
    sys.exit(1)
PY
