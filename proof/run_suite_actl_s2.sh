#!/usr/bin/env bash

# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini

# proof/run_suite_actl_s2.sh - Stage 2 gating suite runner.

set -uo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_DIR" || exit 4
mkdir -p proof/out
PASS=0; FAIL=0; ENVERR=0

for t in bash python3 git; do
command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed (environment error)"; exit 4; }
done
python3 -c "import pytest" >/dev/null 2>&1 || { echo "FAIL: pytest not installed (environment error)"; exit 4; }

export ACTL_REPO="$REPO_DIR" PYTHONDONTWRITEBYTECODE=1
ACTL_ROOT="$(mktemp -d /tmp/actl-s2.XXXXXX)"; export ACTL_ROOT
trap 'rm -rf "$ACTL_ROOT"' EXIT

# Ensure dynamic large fixture (bad_size.txt > 1 MiB) is synthesized on disk before running checks (D-S2-09)

BAD_SIZE_FILE="$REPO_DIR/fixtures/golden/responses/bad_size.txt"
if [[ -f "$REPO_DIR/fixtures/golden/make_responses.sh" ]]; then
if [[ ! -f "$BAD_SIZE_FILE" ]] || (( $(wc -c < "$BAD_SIZE_FILE") < 1048576 )); then
bash "$REPO_DIR/fixtures/golden/make_responses.sh" >/dev/null 2>&1 || true
fi
fi

selected() {
[[ -z "${ONLY:-}" ]] && return 0
local s; IFS=, read -ra _o <<<"$ONLY"
for s in "${_o[@]}"; do
[[ "$1" == *"$s"* ]] && return 0
done
return 1
}

run_check() {
local name="$1"; shift
selected "$name" || return 0
local log="proof/out/${name}.log" rc
echo -n "Running ${name}... "
"$@" > "$log" 2>&1; rc=$?
if (( rc == 0 )); then
echo "[PASS]"
PASS=$((PASS+1))
elif (( rc == 4 )); then
echo "[ENV] (see $log)"
ENVERR=$((ENVERR+1))
sed -n '1,2p' "$log" | sed 's/^/    /'
else
echo "[FAIL] (see $log)"
FAIL=$((FAIL+1))
grep -m2 '^FAIL:' "$log" | sed 's/^/    /'
fi
}

P=proof/stage2
run_check "P-S2-01_intake_unpack_and_turns"  bash $P/P-S2-01.sh
run_check "P-S2-02_challenger_unpack"        bash $P/P-S2-02.sh
run_check "P-S2-03_bad_responses_matrix"     bash $P/P-S2-03.sh
run_check "P-S2-04_truncation_property"      bash $P/P-S2-04.sh
run_check "P-S2-05_path_attacks_and_safety"  bash $P/P-S2-05.sh
run_check "P-S2-06_patchsynth_and_multihunk" bash $P/P-S2-06.sh
run_check "P-S2-07_normalization_variants"   bash $P/P-S2-07.sh
run_check "P-S2-08_amend_and_atomic_swap"    bash $P/P-S2-08.sh
run_check "P-S2-09_turn_replay"              bash $P/P-S2-09.sh
run_check "P-S2-10_bundle_assembly_limits"   bash $P/P-S2-10.sh
run_check "P-S2-11_sentinel_verification"    bash $P/P-S2-11.sh
run_check "P-S2-12_role_promotion"           bash $P/P-S2-12.sh
run_check "P-S2-13_repair_and_nonexec"       bash $P/P-S2-13.sh
run_check "P-S2-14_next_rules_phase12"       bash $P/P-S2-14.sh
run_check "P-S2-15_postparse_validation"     bash $P/P-S2-15.sh
run_check "P-S2-16_stage0_reuse"             bash $P/P-S2-16.sh
run_check "P-S2-17_prompts_checklist"        bash $P/P-S2-17.sh
run_check "P-S2-18_stage2_additions_gate"    bash $P/P-S2-18.sh

echo "=="
echo "Suite Summary: $PASS Passed, $FAIL Failed, $ENVERR Environment"
echo "=="
(( FAIL == 0 )) || exit 1
(( ENVERR == 0 )) || exit 4
exit 0
