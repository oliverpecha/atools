#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# proof/run_suite_actl_s0.sh - Workstream 0A gating suite (S0-R11). run_check pattern of proof/run_suite_engines.sh:
# log per check in proof/out/<name>.log, PASS/FAIL counters, Suite Summary, non-zero exit on failure. Idempotent; temp ACTL_ROOT.
# Exit: 0 all green | 1 at least one red (always the case on the fork point, PB-1) | 4 only environment problems, no red check.
# ONLY=<substring>[,<substring>] runs just the matching checks (used by P-S0-27).
set -uo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_DIR" || exit 4
mkdir -p proof/out
PASS=0; FAIL=0; ENVERR=0
for t in bash python3 git; do command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed (environment error)"; exit 4; }; done
export ACTL_REPO="$REPO_DIR" PYTHONDONTWRITEBYTECODE=1
ACTL_ROOT="$(mktemp -d /tmp/actl-s0.XXXXXX)"; export ACTL_ROOT
trap 'rm -rf "$ACTL_ROOT"' EXIT

selected() { [[ -z "${ONLY:-}" ]] && return 0; local s; IFS=, read -ra _o <<<"$ONLY"; for s in "${_o[@]}"; do [[ "$1" == *"$s"* ]] && return 0; done; return 1; }
run_check() {
    local name="$1"; shift
    selected "$name" || return 0
    local log="proof/out/${name}.log" rc
    echo -n "Running ${name}... "
    "$@" > "$log" 2>&1; rc=$?
    if (( rc == 0 )); then echo "[PASS]"; PASS=$((PASS+1))
    elif (( rc == 4 )); then echo "[ENV] (see $log)"; ENVERR=$((ENVERR+1)); sed -n '1,2p' "$log" | sed 's/^/    /'
    else echo "[FAIL] (see $log)"; FAIL=$((FAIL+1)); grep -m2 '^FAIL:' "$log" | sed 's/^/    /'; fi
}
P=proof/stage0
run_check "P-S0-10_golden_selfcheck"        bash $P/golden_selfcheck.sh
run_check "P-S0-01_doctor"                  bash $P/P-S0-01.sh
run_check "P-S0-02_additive_change"         bash $P/P-S0-02.sh
run_check "P-S0-03_layout"                  bash $P/P-S0-03.sh
run_check "P-S0-04_sprint_new"              bash $P/P-S0-04.sh
run_check "P-S0-05_seq_concurrency"         bash $P/p05_seq_concurrency.sh
run_check "P-S0-06_seq_reconstruct"         bash $P/P-S0-06.sh
run_check "P-S0-07_hashing"                 bash $P/P-S0-07.sh
run_check "P-S0-08_schemas"                 bash $P/P-S0-08.sh
run_check "P-S0-09_defaults"                bash $P/P-S0-09.sh
run_check "P-S0-11_cli_exit_codes"          bash $P/P-S0-11.sh
run_check "P-S0-12_scope"                   bash $P/P-S0-12.sh
run_check "P-S0-13_global_hook_immunity"    bash $P/P-S0-13.sh
run_check "P-S0-14_registries"              bash $P/P-S0-14.sh
run_check "P-S0-15_expected_fragments"      bash $P/P-S0-15.sh
run_check "P-S0-26_interfaces_conformance"  bash $P/P-S0-26.sh
run_check "P-S0-28_doctor_uninitialised"    bash $P/p02_doctor_empty.sh
run_check "P-S0-29_next_rules_table"        bash $P/P-S0-29.sh
run_check "P-S0-30_gap_proofs"             bash $P/P-S0-30.sh

echo "=========================================="
echo "Suite Summary: $PASS Passed, $FAIL Failed, $ENVERR Environment"
echo "=========================================="
(( FAIL == 0 )) || exit 1
(( ENVERR == 0 )) || exit 4
exit 0
