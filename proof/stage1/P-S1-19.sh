#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-19: Implementer skill governance verification (S1-R8) + semantic check
# that prohibitory clauses are allowed while imperative leaks are rejected.
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"

SKILL="${REPO_DIR}/skills/actl-implementer/SKILL.md"
if [[ ! -f "$SKILL" ]]; then
  echo "FAIL: S1-R8.1: skills/actl-implementer/SKILL.md missing"
  exit 1
fi

python3 - "$SKILL" <<'PY'
import re
import sys
from pathlib import Path

skill_path = Path(sys.argv[1])
text = skill_path.read_text(encoding="utf-8")

required_tokens = [
    "mailboxes/implementer/inbox",
    "attempt.json",
    "mailboxes/implementer/outbox/closure.json",
    "wip/",
    "git status",
]
for tok in required_tokens:
    if tok not in text:
        print(f"FAIL: S1-R8.2: Required token {tok!r} missing from {skill_path}")
        sys.exit(1)

# Must explicitly state the Invariant P prohibition (never read records/ or oracle proofs)
lower = text.lower()
if not any(w in lower for w in ("never", "must not", "do not", "prohibited", "forbidden")):
    print("FAIL: S1-R8.3: SKILL.md lacks explicit prohibition language for Invariant P")
    sys.exit(1)

# No non-prohibitory line may instruct running proof suites or reading oracle/records
prohibition_re = re.compile(r"\b(never|must\s+not|do\s+not|don't|prohibited|forbidden|not\s+allowed|excluding)\b", re.I)
leak_re = re.compile(r"(bash\s+proof/|cat\s+.*records/|cat\s+.*oracle-|cat\s+.*proofs/)")

for line_no, raw_line in enumerate(text.splitlines(), start=1):
    line = raw_line.strip()
    if not line:
        continue
    if leak_re.search(line) and not prohibition_re.search(line):
        print(f"FAIL: S1-R8.3: Imperative oracle/proof access instruction at line {line_no}: {line}")
        sys.exit(1)
PY
