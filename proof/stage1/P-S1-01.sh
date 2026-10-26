#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-01: Golden good.patch green, exit 0, verification record schema-valid.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import sys
from pathlib import Path
try:
    from actl.verify import verify_impl
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R1: cannot import actl.verify: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
try:
    res = verify_impl(layout, "2026-10-16_public-profiles")
    errs = schemas.validate("verification", res)
    if errs:
        print(f"FAIL: S1-R1.3: Verification schema validation failed: {errs}")
        sys.exit(1)
    if res.get("exit_code") != 0:
        print(f"FAIL: S1-R1: Expected exit_code 0 for good run, got {res.get('exit_code')}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R1: verify_impl invocation failed: {exc}")
    sys.exit(1)
PY
