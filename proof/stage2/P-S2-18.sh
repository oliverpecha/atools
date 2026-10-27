#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
# proof/stage2/P-S2-18.sh - Stage 2 per-stage git diff additions & PB-2 immutability gate (S2-R13, D-41, D-S2-03).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
cd "$REPO_DIR"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
    echo "FAIL: S2-R13: $REPO_DIR is not a git repository"
    exit 1
fi

FORK_POINT="${ACTL_FORK_POINT:-}"
if [[ -z "$FORK_POINT" ]]; then
    FORK_POINT="$(git merge-base HEAD main 2>/dev/null || git rev-parse HEAD~1 2>/dev/null || true)"
fi
if [[ -z "$FORK_POINT" ]] || ! git rev-parse --verify "${FORK_POINT}^{commit}" >/dev/null 2>&1; then
    echo "FAIL: S2-R13: Invalid or unresolvable ACTL_FORK_POINT='${FORK_POINT}'"
    exit 1
fi

REQUIRED_IMPL=(
    "src/actl/turns.py"
    "src/actl/bundle.py"
    "src/actl/envelope.py"
    "src/actl/unpack.py"
    "src/actl/patchsynth.py"
    "src/actl/repair.py"
    "src/actl/replay.py"
    "src/actl/promote.py"
    "src/actl/cmd_bundle.py"
    "src/actl/cmd_unpack.py"
    "src/actl/cmd_replay.py"
    "src/actl/cmd_promote.py"
    "src/actl/next_rules/phase12.py"
    "prompts/architect-intake.md"
    "prompts/architect-review.md"
    "prompts/challenger.md"
    "prompts/curator.md"
    "prompts/_output_contract.md"
)
for mod in "${REQUIRED_IMPL[@]}"; do
    if [[ ! -f "$mod" ]]; then
        echo "FAIL: S2-R13: Stage 2 implementation file missing on base: $mod"
        exit 1
    fi
done

FROZEN_PATHS=(
    "src/actl/INTERFACES.md"
    "src/actl/__init__.py"
    "src/actl/cli.py"
    "src/actl/next.py"
    "src/actl/layout.py"
    "src/actl/ids.py"
    "src/actl/seq.py"
    "src/actl/hashing.py"
    "src/actl/schemas.py"
    "src/actl/scope.py"
    "src/actl/sprint.py"
    "src/actl/doctor.py"
    "src/actl/errors.py"
    "src/actl/cmd_doctor.py"
    "src/actl/cmd_init.py"
    "src/actl/cmd_next.py"
    "src/actl/cmd_sprint.py"
    "schemas"
    "config/graph.toml"
    "proof/stage0"
    "proof/run_suite_actl_s0.sh"
    "proof/run_suite_exit_code.sh"
    "fixtures/golden/expected.d/base.json"
    "fixtures/golden/build_golden.sh"
)
for fp in "${FROZEN_PATHS[@]}"; do
    if [[ -e "$fp" ]]; then
        diff_out="$(git diff --name-only "$FORK_POINT" -- "$fp")"
        if [[ -n "$diff_out" ]]; then
            echo "FAIL: S2-R13: PB-2 frozen path modified since $FORK_POINT: $diff_out"
            exit 1
        fi
    fi
done

is_allowed_stage2_path() {
    local p="$1"
    case "$p" in
        src/actl/turns.py|\
        src/actl/bundle.py|\
        src/actl/envelope.py|\
        src/actl/unpack.py|\
        src/actl/patchsynth.py|\
        src/actl/repair.py|\
        src/actl/replay.py|\
        src/actl/promote.py|\
        src/actl/cmd_bundle.py|\
        src/actl/cmd_unpack.py|\
        src/actl/cmd_replay.py|\
        src/actl/cmd_promote.py|\
        src/actl/next_rules/phase12.py|\
        prompts/architect-intake.md|\
        prompts/architect-review.md|\
        prompts/challenger.md|\
        prompts/curator.md|\
        prompts/_output_contract.md|\
        docs/plan/spec-S2.md|\
        proof/run_suite_actl_s2.sh|\
        proof/stage2/*|\
        test/actl/test_s2_*.py|\
        fixtures/golden/make_responses.sh|\
        fixtures/golden/expected.d/s2.json|\
        fixtures/golden/responses/*|\
        fixtures/golden/turns/*|\
        install.sh|README.md)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

if is_allowed_stage2_path "src/actl/scope.py"; then
    echo "FAIL: S2-R13: Regression self-test failed: src/actl/scope.py unexpectedly passed allowlist"
    exit 1
fi
if is_allowed_stage2_path "src/actl/arbitrary.py"; then
    echo "FAIL: S2-R13: Regression self-test failed: src/actl/arbitrary.py unexpectedly passed allowlist"
    exit 1
fi

while IFS=$'\t' read -r status path1 path2; do
    [[ -z "$status" ]] && continue
    case "$status" in
        D*|R*)
            echo "FAIL: S2-R13: Forbidden file deletion or rename ($status): $path1 ${path2:-}"
            exit 1
            ;;
        A|M)
            if ! is_allowed_stage2_path "$path1"; then
                echo "FAIL: S2-R13: Disallowed path touched ($status): $path1"
                exit 1
            fi
            ;;
        *)
            echo "FAIL: S2-R13: Unexpected git status '$status' on $path1"
            exit 1
            ;;
    esac
done < <(git diff --name-status "$FORK_POINT")

echo "OK: P-S2-18"
