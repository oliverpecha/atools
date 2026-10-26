#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-02: Additive-change rule, PB-2 immutability, and deliverable allowlist.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR"

BASE_SHA="4e16cc3"
if ! git rev-parse -q --verify "$BASE_SHA" >/dev/null; then
  echo "FAIL: S1-R16: Base commit $BASE_SHA missing (environment error)"
  exit 4
fi

# 1. Reject empty diff on authoring branch
TOTAL_CHANGES=$(git diff --name-only "$BASE_SHA"..HEAD | wc -l)
if [[ "$TOTAL_CHANGES" -eq 0 ]]; then
  echo "FAIL: S1-R16: Branch has zero changes relative to $BASE_SHA"
  exit 1
fi

# 2. Assert zero diff on PB-2 frozen paths relative to baseline 4e16cc3 across all statuses
FROZEN_DIFF=$(git diff --name-only "$BASE_SHA"..HEAD -- proof/stage0 fixtures/golden/expected.d/base.json tools src/actl/INTERFACES.md)
if [[ -n "$FROZEN_DIFF" ]]; then
  echo "FAIL: S1-R16: PB-2 frozen files modified relative to $BASE_SHA: $FROZEN_DIFF"
  exit 1
fi

# 3. Reject any implementation smuggling under src/actl/ or skills/
IMPL_DIFF=$(git diff --name-only "$BASE_SHA"..HEAD -- src/actl skills)
if [[ -n "$IMPL_DIFF" ]]; then
  echo "FAIL: S1-R16: Implementation smuggling detected in authoring branch: $IMPL_DIFF"
  exit 1
fi

# 4. Strict deliverable allowlist across all change statuses (A, M, D, R, C)
python3 - "$BASE_SHA" <<'PY'
import sys
import subprocess
from pathlib import Path

base_sha = sys.argv[1]
res = subprocess.run(["git", "diff", "--name-status", f"{base_sha}..HEAD"], capture_output=True, text=True, check=True)

allowed_prefixes = (
    "docs/plan/spec-S1.md",
    "proof/run_suite_actl_s1.sh",
    "proof/stage1/",
    "test/actl/test_verify_s1.py",
    "test/actl/test_guards_s1.py",
    "test/actl/test_session_s1.py",
    "test/actl/test_next_phase3.py",
    "fixtures/golden/expected.d/s1.json",
    "fixtures/golden/transcripts/",
)

for line in res.stdout.strip().splitlines():
    if not line:
        continue
    parts = line.split(maxsplit=1)
    status = parts[0]
    path = parts[1] if len(parts) > 1 else ""
    if not any(path == prefix or path.startswith(prefix) for prefix in allowed_prefixes):
        print(f"FAIL: S1-R16: File {path} (status {status}) not in Stage 1 authoring deliverable allowlist")
        sys.exit(1)

print("OK: S1-R16 deliverable check passed.")
PY
