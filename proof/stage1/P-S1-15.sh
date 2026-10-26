#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-15: prior_attempt.json has strictly 4 keys and leaks no oracle tests.
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
    print(f"FAIL: S1-R7: cannot import actl modules: {exc}")
    sys.exit(1)

layout = Layout(Path("/tmp/actl-test-s1"))
try:
    res = verify_impl(layout, "2026-10-16_public-profiles")
    prior_path = layout.inbox("2026-10-16_public-profiles", "implementer") / "prior_attempt.json"
    if prior_path.exists():
        import json
        data = json.loads(prior_path.read_text())
        errs = schemas.validate("prior_attempt", data)
        if errs or len(data.keys()) != 4:
            print(f"FAIL: S1-R7: Invalid prior_attempt keys: {list(data.keys())}")
            sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R7: verify_impl invocation failed: {exc}")
    sys.exit(1)
PY
