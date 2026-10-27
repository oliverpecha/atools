#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-02: Additive-change rule, PB-2 immutability, NUL-safe parser, required
# deliverable inventory, and adversarial self-tests (S1-R16, D-41).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR"

BASE_SHA="${ACTL_S1_BASE_SHA:-4e16cc3}"
if ! git rev-parse -q --verify "${BASE_SHA}^{commit}" >/dev/null 2>&1; then
  echo "FAIL: S1-R16: Base commit $BASE_SHA missing (environment error)"
  exit 4
fi

python3 - "$REPO_DIR" "$BASE_SHA" <<'PY'
import subprocess
import sys
from pathlib import Path

repo_dir = Path(sys.argv[1])
base_sha = sys.argv[2]

REQUIRED_AUTHORING_FILES = frozenset({
    "docs/plan/spec-S1.md",
    "fixtures/golden/expected.d/s1.json",
    "fixtures/golden/transcripts/clean.jsonl",
    "fixtures/golden/transcripts/dirty_oracle.jsonl",
    "proof/run_suite_actl_s1.sh",
    "proof/stage1/fixture_s1.sh",
    *[f"proof/stage1/P-S1-{i:02d}.sh" for i in range(1, 30)],
    "test/actl/test_guards_s1.py",
    "test/actl/test_next_phase3.py",
    "test/actl/test_session_s1.py",
    "test/actl/test_verify_s1.py",
})

FROZEN_STAGE0_PREFIXES = (
    "proof/stage0/",
    "proof/run_suite_actl_s0.sh",
    "proof/run_suite_exit_code.sh",
    "fixtures/golden/expected.d/base.json",
    "tools/",
    "src/actl/INTERFACES.md",
    "schemas/",
)

ALLOWED_IMPL_FILES = frozenset({
    "src/actl/verify.py",
    "src/actl/stage.py",
    "src/actl/session.py",
    "src/actl/cmd_verify_impl.py",
    "src/actl/cmd_dispatch_impl.py",
    "src/actl/cmd_wait.py",
    "src/actl/cmd_selftest.py",
    "src/actl/next_rules/phase3.py",
    "config/forbidden.toml",
    "config/secrets.toml",
    "skills/actl-implementer/SKILL.md",
    "src/core/config.py",
    "src/sessions/storage.py",
})


def parse_name_status_z(raw: bytes) -> list[tuple[str, str, str | None]]:
    """Parse `git diff --name-status -z` output into (status, path, new_path)."""
    if not raw:
        return []
    tokens = [t.decode("utf-8", errors="surrogateescape") for t in raw.split(b"\x00") if t]
    records: list[tuple[str, str, str | None]] = []
    i = 0
    while i < len(tokens):
        st = tokens[i]
        code = st[0]
        if code in ("R", "C"):
            old_p = tokens[i + 1]
            new_p = tokens[i + 2]
            records.append((st, old_p, new_p))
            i += 3
        else:
            p = tokens[i + 1]
            records.append((st, p, None))
            i += 2
    return records


def validate_diff_records(
    records: list[tuple[str, str, str | None]], mode: str = "authoring"
) -> list[str]:
    errors: list[str] = []
    if not records:
        errors.append("Branch has zero changes relative to baseline")
        return errors

    seen_paths: set[str] = set()
    for st, path, new_path in records:
        code = st[0]
        paths_to_check = [p for p in (path, new_path) if p is not None]
        for p in paths_to_check:
            if any(p == fp or p.startswith(fp) for fp in FROZEN_STAGE0_PREFIXES):
                errors.append(f"PB-2 frozen path touched: {p} ({st})")

        if code in ("D", "R", "C"):
            errors.append(f"Disallowed git status {st} on {path} -> {new_path}")
            continue

        if mode == "authoring":
            if code != "A":
                errors.append(f"Authoring branch only permits 'A' (Added), got {st} on {path}")
            if path not in REQUIRED_AUTHORING_FILES:
                errors.append(f"Path not in exact Stage 1 authoring allowlist: {path}")
            seen_paths.add(path)
        else:
            # Implementation mode: allow authoring deliverables + Stage 1 implementation paths
            is_guard_mod = (
                path.startswith("src/actl/guards/")
                and path.endswith(".py")
                and "/" not in path[len("src/actl/guards/"):]
            )
            if (
                path not in REQUIRED_AUTHORING_FILES
                and path not in ALLOWED_IMPL_FILES
                and not is_guard_mod
            ):
                errors.append(f"Unauthorized path in Stage 1 branch: {path} ({st})")
            seen_paths.add(path)

    missing = REQUIRED_AUTHORING_FILES - seen_paths
    if missing:
        errors.append(f"Missing required Stage 1 authoring deliverables: {sorted(missing)[:5]}")
    return errors


# 1. Self-test the validator against adversarial cases (GD-01 / PB-2 review requirement)
base_valid = [("A", p, None) for p in sorted(REQUIRED_AUTHORING_FILES)]
assert validate_diff_records(base_valid, "authoring") == [], "Self-test failed on valid set"
assert validate_diff_records([], "authoring"), "Self-test failed to reject empty diff"
assert validate_diff_records(
    base_valid + [("A", "docs/plan/spec-S1.md.extra", None)], "authoring"
), "Self-test failed to reject prefix lookalike docs/plan/spec-S1.md.extra"
assert validate_diff_records(
    base_valid + [("A", "proof/stage1/malicious.py", None)], "authoring"
), "Self-test failed to reject non-allowlisted file under proof/stage1/"
assert validate_diff_records(
    base_valid + [("A", "fixtures/golden/transcripts/note.txt", None)], "authoring"
), "Self-test failed to reject non-.jsonl file under transcripts/"
assert validate_diff_records(
    [("D", "docs/plan/spec-S1.md", None)] + base_valid[1:], "authoring"
), "Self-test failed to reject deletion"
assert validate_diff_records(
    [("R100", "docs/plan/spec-S1.md", "docs/plan/spec-S1-renamed.md")] + base_valid[1:],
    "authoring",
), "Self-test failed to reject rename"
assert validate_diff_records(
    base_valid + [("M", "src/actl/INTERFACES.md", None)], "authoring"
), "Self-test failed to reject frozen path modification"
assert validate_diff_records(
    base_valid + [("A", "src/actl/verify.py", None)], "authoring"
), "Self-test failed to reject implementation smuggling on authoring branch"

# 2. Check clean working tree (ignoring proof/out/)
st_proc = subprocess.run(
    ["git", "status", "--porcelain", "-z"],
    cwd=repo_dir,
    capture_output=True,
    check=True,
)
for entry in st_proc.stdout.split(b"\x00"):
    if not entry:
        continue
    line = entry.decode("utf-8", errors="replace")
    rel_path = line[3:]
    if not rel_path.startswith("proof/out"):
        print(f"FAIL: S1-R16.2: Working tree has uncommitted/untracked changes: {line}")
        sys.exit(1)

# 3. Inspect real git diff against BASE_SHA
diff_proc = subprocess.run(
    ["git", "diff", "--name-status", "-z", f"{base_sha}..HEAD"],
    cwd=repo_dir,
    capture_output=True,
    check=True,
)
records = parse_name_status_z(diff_proc.stdout)

branch_proc = subprocess.run(
    ["git", "branch", "--show-current"],
    cwd=repo_dir,
    capture_output=True,
    text=True,
    check=True,
)
branch = branch_proc.stdout.strip()
mode = "authoring" if branch == "wip/author-s1" else "implementation"

errs = validate_diff_records(records, mode=mode)
if errs:
    for e in errs:
        print(f"FAIL: S1-R16.2: {e}")
    sys.exit(1)

for req_file in sorted(REQUIRED_AUTHORING_FILES):
    if not (repo_dir / req_file).is_file():
        print(f"FAIL: S1-R16.2: Deliverable missing on disk: {req_file}")
        sys.exit(1)

print(f"OK: S1-R16.2 verified ({len(records)} records, mode={mode}).")
PY
