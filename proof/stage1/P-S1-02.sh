#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-02: Additive-change rule, PB-2 immutability, NUL-safe porcelain parser,
# bounded proof/out/ exemption, explicit mode selection, authoring pin (S1-R16, D-41).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR"

BASE_SHA="${ACTL_S1_BASE_SHA:-4e16cc3}"

python3 - "$REPO_DIR" "$BASE_SHA" <<'PY'
import os
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
    "proof/stage1/run_standins.sh",
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


def is_proof_out(path: str) -> bool:
    return path == "proof/out" or path.startswith("proof/out/")


def is_frozen(path: str) -> bool:
    for fp in FROZEN_STAGE0_PREFIXES:
        if fp.endswith("/"):
            if path.startswith(fp):
                return True
        elif path == fp:
            return True
    return False


def parse_name_status_z(raw: bytes) -> list[tuple[str, str, str | None]]:
    """Parse `git diff --name-status -z` into (status, path, new_path)."""
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


def parse_porcelain_z(raw: bytes) -> list[tuple[str, str, str | None]]:
    """Parse `git status --porcelain -z` consuming rename/copy companion paths."""
    records: list[tuple[str, str, str | None]] = []
    parts = raw.split(b"\x00")
    i = 0
    while i < len(parts) and parts[i]:
        entry = parts[i].decode("utf-8", errors="surrogateescape")
        if len(entry) < 3:
            i += 1
            continue
        xy = entry[:2]
        path = entry[3:]
        if ("R" in xy) or ("C" in xy):
            new_path = parts[i + 1].decode("utf-8", errors="surrogateescape")
            records.append((xy, path, new_path))
            i += 2
        else:
            records.append((xy, path, None))
            i += 1
    return records


def select_mode(branch: str, env_mode: str) -> str:
    env_mode = env_mode.strip()
    if env_mode:
        if env_mode not in ("authoring", "implementation"):
            raise ValueError(
                f"ACTL_S1_VALIDATE_MODE must be authoring or implementation, got {env_mode!r}"
            )
        return env_mode
    if branch == "wip/author-s1":
        return "authoring"
    if branch == "wip/s1-verifier":
        return "implementation"
    raise ValueError(
        f"Unknown branch {branch!r}; set ACTL_S1_VALIDATE_MODE=authoring|implementation"
    )


def pin_drift_errors(changed_authoring: set[str]) -> list[str]:
    errors: list[str] = []
    drifted = sorted(changed_authoring & REQUIRED_AUTHORING_FILES)
    if drifted:
        errors.append(
            "Implementation mode authoring pin drift: " + ", ".join(drifted[:8])
        )
    return errors


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
            if is_frozen(p):
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

    if mode == "authoring":
        missing = REQUIRED_AUTHORING_FILES - seen_paths
        if missing:
            errors.append(f"Missing required Stage 1 authoring deliverables: {sorted(missing)[:5]}")
    return errors


# 1. Self-tests (no git baseline required)
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

# Porcelain rename companion consumption
porc = parse_porcelain_z(b"R  old-name\x00new-name\x00?? proof/out/foo.log\x00?? proof/outside\x00")
assert porc[0] == ("R ", "old-name", "new-name"), porc[0]
assert porc[1] == ("??", "proof/out/foo.log", None), porc[1]
assert porc[2] == ("??", "proof/outside", None), porc[2]
assert is_proof_out("proof/out/foo.log") and is_proof_out("proof/out")
assert not is_proof_out("proof/outside")
assert not is_proof_out("proof/out_extra")

assert select_mode("wip/author-s1", "") == "authoring"
assert select_mode("wip/s1-verifier", "") == "implementation"
assert select_mode("main", "authoring") == "authoring"
try:
    select_mode("main", "")
    print("FAIL: S1-R16.2: Unknown branch must fail closed without ACTL_S1_VALIDATE_MODE")
    sys.exit(1)
except ValueError:
    pass

assert pin_drift_errors({"docs/plan/spec-S1.md", "src/actl/verify.py"})
assert not pin_drift_errors({"src/actl/verify.py"})

# D-41 pin is the annotated tag name only (never a commit SHA in this proof;
# never read ACTL_S1_AUTHORING_PIN -- env HEAD/SHA bypass stays closed).
AUTHORING_PIN_TAG = "stage-1-authoring-verified"
assert AUTHORING_PIN_TAG == "stage-1-authoring-verified"
assert "ACTL_S1_AUTHORING_PIN" not in AUTHORING_PIN_TAG

print("OK: P-S1-02 validator self-tests passed.")

# 2. Baseline commit must exist for the live inventory check
probe = subprocess.run(
    ["git", "rev-parse", "-q", "--verify", f"{base_sha}^{{commit}}"],
    cwd=repo_dir,
    capture_output=True,
)
if probe.returncode != 0:
    print(f"FAIL: S1-R16: Base commit {base_sha} missing (environment error)")
    sys.exit(4)

# 3. Clean working tree, ignoring only proof/out/
st_proc = subprocess.run(
    ["git", "status", "--porcelain", "-z"],
    cwd=repo_dir,
    capture_output=True,
    check=True,
)
for xy, path, new_path in parse_porcelain_z(st_proc.stdout):
    for p in (path, new_path):
        if p and not is_proof_out(p):
            print(f"FAIL: S1-R16.2: Working tree has uncommitted/untracked changes: {xy} {path} -> {new_path}")
            sys.exit(1)

# 4. Inspect real git diff against BASE_SHA
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
try:
    mode = select_mode(branch, os.environ.get("ACTL_S1_VALIDATE_MODE", ""))
except ValueError as exc:
    print(f"FAIL: S1-R16.2: {exc}")
    sys.exit(1)

errs = validate_diff_records(records, mode=mode)
if mode == "implementation":
    # Pin object: annotated tag stage-1-authoring-verified (D-41).
    # Never read ACTL_S1_AUTHORING_PIN (bypass stays closed even if set to HEAD/SHA).
    tag = AUTHORING_PIN_TAG
    tag_probe = subprocess.run(
        ["git", "rev-parse", "-q", "--verify", f"refs/tags/{tag}^{{commit}}"],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    if tag_probe.returncode != 0:
        print(
            f"FAIL: S1-R16.2: annotated tag {tag} missing "
            "(no env SHA fallback, no HEAD fallback)"
        )
        sys.exit(1)
    pin = tag_probe.stdout.strip()
    anc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", pin, "HEAD"],
        cwd=repo_dir,
        capture_output=True,
    )
    if anc.returncode != 0:
        print(
            f"FAIL: S1-R16.2: HEAD is not a descendant of {tag}^{{commit}} ({pin})"
        )
        sys.exit(1)
    changed_authoring: set[str] = set()
    for req in REQUIRED_AUTHORING_FILES:
        drift = subprocess.run(
            ["git", "diff", "--name-only", pin, "HEAD", "--", req],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        )
        if drift.stdout.strip():
            changed_authoring.add(req)
    errs.extend(pin_drift_errors(changed_authoring))

if errs:
    for e in errs:
        print(f"FAIL: S1-R16.2: {e}")
    sys.exit(1)

for req_file in sorted(REQUIRED_AUTHORING_FILES):
    if not (repo_dir / req_file).is_file():
        print(f"FAIL: S1-R16.2: Deliverable missing on disk: {req_file}")
        sys.exit(1)

print(f"OK: S1-R16.2 verified ({len(records)} records, mode={mode}, files={len(REQUIRED_AUTHORING_FILES)}).")
PY
