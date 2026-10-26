#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# proof/run_suite_actl_s1.sh - Stage 1 gating verification suite.
set -uo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
cd "$REPO_DIR" || exit 4
mkdir -p proof/out
PASS=0; FAIL=0; ENVERR=0

for t in bash python3 git pytest; do
  command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed (environment error)"; exit 4; }
done

export ACTL_REPO="$REPO_DIR" PYTHONDONTWRITEBYTECODE=1
ACTL_ROOT="$(mktemp -d /tmp/actl-s1.XXXXXX)"; export ACTL_ROOT
trap 'rm -rf "$ACTL_ROOT"' EXIT

selected() {
  [[ -z "${ONLY:-}" ]] && return 0
  local s
  IFS=, read -ra _o <<<"$ONLY"
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
    grep -m2 '^FAIL:' "$log" | sed 's/^/    /' || head -n 2 "$log" | sed 's/^/    /'
  fi
}

# 1. Execute Stage 1 pytest suites (GD-02, GD-03)
run_pytest() {
  local name="$1"
  local test_file="$2"
  selected "$name" || return 0
  local log="proof/out/${name}.log" rc
  echo -n "Running ${name}... "
  pytest "$test_file" -q -rf > "$log" 2>&1; rc=$?
  if (( rc == 0 )); then
    echo "[PASS]"
    PASS=$((PASS+1))
  else
    echo "[FAIL] (see $log)"
    FAIL=$((FAIL+1))
    grep -m2 -E '(FAILED|ERROR|FAIL:)' "$log" | sed 's/^/    /' || head -n 2 "$log" | sed 's/^/    /'
  fi
}

run_pytest "pytest_verify_s1"      "test/actl/test_verify_s1.py"
run_pytest "pytest_guards_s1"      "test/actl/test_guards_s1.py"
run_pytest "pytest_session_s1"     "test/actl/test_session_s1.py"
run_pytest "pytest_next_phase3"    "test/actl/test_next_phase3.py"

# 2. Execute Stage 1 behavioral proof scripts
P=proof/stage1
run_check "P-S1-01_good_patch"             bash $P/P-S1-01.sh
run_check "P-S1-02_additive_change"        bash $P/P-S1-02.sh
run_check "P-S1-03_bad_scope"              bash $P/P-S1-03.sh
run_check "P-S1-04_bad_testcount"          bash $P/P-S1-04.sh
run_check "P-S1-05_bad_secret"             bash $P/P-S1-05.sh
run_check "P-S1-06_bad_forbidden"          bash $P/P-S1-06.sh
run_check "P-S1-07_bad_proof_o1"           bash $P/P-S1-07.sh
run_check "P-S1-08_guard_selftests"        bash $P/P-S1-08.sh
run_check "P-S1-09_oracle_tamper"          bash $P/P-S1-09.sh
run_check "P-S1-10_scope_matcher"          bash $P/P-S1-10.sh
run_check "P-S1-11_g4_hollow_tests"        bash $P/P-S1-11.sh
run_check "P-S1-12_secret_scrubbing"       bash $P/P-S1-12.sh
run_check "P-S1-13_staging_cleanup"        bash $P/P-S1-13.sh
run_check "P-S1-14_env_allowlist"          bash $P/P-S1-14.sh
run_check "P-S1-15_prior_attempt_keys"     bash $P/P-S1-15.sh
run_check "P-S1-16_dispatch_no_run"        bash $P/P-S1-16.sh
run_check "P-S1-17_tripwires"              bash $P/P-S1-17.sh
run_check "P-S1-18_phase3_rules"           bash $P/P-S1-18.sh
run_check "P-S1-19_implementer_skill"      bash $P/P-S1-19.sh
run_check "P-S1-20_detached_dispatch"      bash $P/P-S1-20.sh
run_check "P-S1-21_hard_cap_overrun"       bash $P/P-S1-21.sh
run_check "P-S1-22_session_lost"           bash $P/P-S1-22.sh
run_check "P-S1-23_archive_log"            bash $P/P-S1-23.sh
run_check "P-S1-24_log_unlink_order"       bash $P/P-S1-24.sh
run_check "P-S1-25_session_collision"      bash $P/P-S1-25.sh
run_check "P-S1-26_prompt_size_ceiling"    bash $P/P-S1-26.sh
run_check "P-S1-27_cursor_home_override"   bash $P/P-S1-27.sh
run_check "P-S1-28_verify_cli_codes"       bash $P/P-S1-28.sh
run_check "P-S1-29_bad_regression_o2"      bash $P/P-S1-29.sh

echo "=========================================="
echo "Suite Summary: $PASS Passed, $FAIL Failed, $ENVERR Environment"
echo "=========================================="
(( FAIL == 0 )) || exit 1
(( ENVERR == 0 )) || exit 4
exit 0
