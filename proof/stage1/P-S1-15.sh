#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-15: prior_attempt.json has strictly 4 keys and leaks no oracle tests.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import os
import sys
import json
from pathlib import Path

try:
    from actl.verify import verify_impl
    from actl.layout import Layout
    import actl.schemas as schemas
except ImportError as exc:
    print(f"FAIL: S1-R7: cannot import actl modules: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p15_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)

try:
    res = verify_impl(layout, "2026-10-16_public-profiles")
    prior_path = layout.inbox("2026-10-16_public-profiles", "implementer") / "prior_attempt.json"
    if not prior_path.exists():
        print(f"FAIL: S1-R7: verify_impl failed to write prior_attempt.json on exit_code {res.get('exit_code')}")
        sys.exit(1)
    data = json.loads(prior_path.read_text())
    expected_keys = {"diff", "failing_step", "failing_line", "closures_submitted"}
    if set(data.keys()) != expected_keys:
        print(f"FAIL: S1-R7: prior_attempt.json keys {set(data.keys())} != {expected_keys}")
        sys.exit(1)
    errs = schemas.validate("prior_attempt", data)
    if errs:
        print(f"FAIL: S1-R7: prior_attempt schema invalid: {errs}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R7: verify_impl invocation failed: {exc}")
    sys.exit(1)
PY
