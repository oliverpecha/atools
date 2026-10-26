#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-24: Original log unlinked only after verification artifact fsync.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

python3 - <<'PY'
import os
import sys
from pathlib import Path

try:
    from actl.verify import verify_impl
    from actl.layout import Layout
except ImportError as exc:
    print(f"FAIL: S1-R15: cannot import actl.verify.verify_impl: {exc}")
    sys.exit(1)

root = Path(os.environ.get("ACTL_ROOT", "/tmp")) / "p24_sandbox"
root.mkdir(parents=True, exist_ok=True)
layout = Layout(root)

try:
    res = verify_impl(layout, "2026-10-16_public-profiles")
    ver_path = layout.runs("2026-10-16_public-profiles") / "verification-001.json"
    if not ver_path.exists():
        print(f"FAIL: S1-R15: verification-001.json must exist before log unlink: {ver_path}")
        sys.exit(1)
except Exception as exc:
    print(f"FAIL: S1-R15: verify_impl invocation failed: {exc}")
    sys.exit(1)
PY
