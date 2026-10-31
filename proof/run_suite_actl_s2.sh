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

# R4-03: wrappers must preserve pytest exit 4 so run_check can classify ENV.
# Static: reject `if ! python3 -m pytest` and reject rc!=0-before-rc==4 ordering.
# Functional: execute EACH real pytest wrapper under a python3 shim that exits 4;
# synthetic good/bad/wrong-order patterns prove the scanner distinctions.
_r403_wrapper_env_selftest() {
local w base tmp grc brc orc wrc rc4_line rcnz_line
for w in "$REPO_DIR"/proof/stage2/P-S2-*.sh; do
base=$(basename "$w")
[[ "$base" == "P-S2-18.sh" ]] && continue
grep -q 'python3 -m pytest' "$w" || continue
if grep -Eq 'if ![[:space:]]+python3 -m pytest' "$w"; then
echo "FAIL: R4-03: $base collapses pytest statuses via 'if !'; ENV (rc 4) unreachable"
exit 1
fi
if ! grep -Eq '\(\([[:space:]]*rc == 4[[:space:]]*\)\)' "$w"; then
echo "FAIL: R4-03: $base does not propagate pytest exit 4 as exit 4"
exit 1
fi
# Counterexample ordering: rc!=0 exit 1 BEFORE rc==4 still contains the rc==4 token.
rc4_line=$(grep -nE '\(\([[:space:]]*rc == 4[[:space:]]*\)\)' "$w" | head -1 | cut -d: -f1)
rcnz_line=$(grep -nE '\(\([[:space:]]*rc != 0[[:space:]]*\)\)' "$w" | head -1 | cut -d: -f1 || true)
if [[ -n "${rcnz_line:-}" && -n "${rc4_line:-}" ]] && (( rcnz_line < rc4_line )); then
echo "FAIL: R4-03: $base checks rc!=0 (line $rcnz_line) before rc==4 (line $rc4_line); ENV collapsed to FAIL"
exit 1
fi
done
tmp=$(mktemp -d /tmp/actl-r403.XXXXXX)
printf '#!/bin/sh\nexit 4\n' > "$tmp/python3"
chmod +x "$tmp/python3"
cat > "$tmp/good.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
rc=0
python3 -m pytest /dev/null -q || rc=$?
if (( rc == 4 )); then exit 4
elif (( rc != 0 )); then exit 1
fi
EOS
cat > "$tmp/bad.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
if ! python3 -m pytest /dev/null -q; then
echo "FAIL: collapsed"
exit 1
fi
EOS
# Wrong order: has rc==4 token and no `if !`, but collapses ENV to 1 (R4-03 counterexample).
cat > "$tmp/wrong_order.sh" <<'EOS'
#!/usr/bin/env bash
set -euo pipefail
rc=0
python3 -m pytest /dev/null -q || rc=$?
if (( rc != 0 )); then exit 1; fi
if (( rc == 4 )); then exit 4; fi
EOS
chmod +x "$tmp/good.sh" "$tmp/bad.sh" "$tmp/wrong_order.sh"
grc=0; PATH="$tmp:$PATH" bash "$tmp/good.sh" >/dev/null 2>&1 || grc=$?
brc=0; PATH="$tmp:$PATH" bash "$tmp/bad.sh" >/dev/null 2>&1 || brc=$?
orc=0; PATH="$tmp:$PATH" bash "$tmp/wrong_order.sh" >/dev/null 2>&1 || orc=$?
if (( grc != 4 )); then
echo "FAIL: R4-03 self-test: good wrapper pattern returned $grc, want 4"
rm -rf "$tmp"; exit 1
fi
if (( brc != 1 )); then
echo "FAIL: R4-03 self-test: bad (old) wrapper pattern returned $brc, want 1"
rm -rf "$tmp"; exit 1
fi
if (( orc != 1 )); then
echo "FAIL: R4-03 self-test: wrong-order pattern returned $orc, want 1 (ENV collapsed)"
rm -rf "$tmp"; exit 1
fi
# Execute every real pytest-backed proof wrapper under the exit-4 shim.
for w in "$REPO_DIR"/proof/stage2/P-S2-*.sh; do
base=$(basename "$w")
[[ "$base" == "P-S2-18.sh" ]] && continue
grep -q 'python3 -m pytest' "$w" || continue
wrc=0
PATH="$tmp:$PATH" ACTL_REPO="$REPO_DIR" bash "$w" >/dev/null 2>&1 || wrc=$?
if (( wrc != 4 )); then
echo "FAIL: R4-03: real wrapper $base returned $wrc under python3-exit-4 shim, want 4 (ENV)"
rm -rf "$tmp"; exit 1
fi
done
rm -rf "$tmp"
}
_r403_wrapper_env_selftest

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
# N7-02: rc 0 with a FAIL: line is INCONSISTENT (do not count as PASS)
if grep -q '^FAIL:' "$log"; then
local last_fail
last_fail="$(grep '^FAIL:' "$log" | tail -n1)"
echo "[INCONSISTENT] (see $log)"
echo "    $last_fail"
FAIL=$((FAIL+1))
else
echo "[PASS]"
PASS=$((PASS+1))
fi
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
