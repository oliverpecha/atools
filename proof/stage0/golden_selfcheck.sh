#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# proof/stage0/golden_selfcheck.sh - P-S0-10 (S0-R9). Plain bash + git + python3 stdlib. ZERO actl code.
# Verifies fixtures/golden against fixtures/golden/expected.d/base.json:
#   deterministic base_sha; base red; key green 3x + repo tests; each mutant killed exactly by its coverage.md proofs
#   (avatar_drop survives); good.patch green; every bad_* fails at its declared step.
# Exit 0 = fixture consistent, 1 = inconsistent, 4 = tool missing. GOLDEN_DIR may point at a mutated copy (self-tests).
set -uo pipefail
export PYTHONDONTWRITEBYTECODE=1
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOLDEN="${GOLDEN_DIR:-$(cd "$HERE/../../fixtures/golden" && pwd)}"
for t in git python3 bash; do command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed"; exit 4; }; done
[[ -d "$GOLDEN" ]] || { echo "FAIL: golden dir not found: $GOLDEN"; exit 1; }
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
FAILS=0
bad() { echo "FAIL: $*"; FAILS=$((FAILS+1)); }
ok()  { echo "ok: $*"; }
EXPECTED="$GOLDEN/expected.d/base.json"
[[ -f "$EXPECTED" ]] || { echo "FAIL: missing $EXPECTED"; exit 1; }
exp() { python3 - "$EXPECTED" "$1" "$2" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); k = sys.argv[2]
if k == "base_sha": print(d["base_sha"]); sys.exit()
v = d["cases"][k]["expect"].get(sys.argv[3]); print("" if v is None else v)
PY
}
ggit() { GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null git -c core.hooksPath=/dev/null -c core.autocrlf=false "$@"; }

# 1. deterministic build
BASE="$(bash "$GOLDEN/build_golden.sh" "$W/base1" 2>/dev/null)" || { echo "FAIL: build_golden.sh failed"; exit 1; }
BASE2="$(bash "$GOLDEN/build_golden.sh" "$W/base2" 2>/dev/null)" || { echo "FAIL: second build failed"; exit 1; }
[[ "$BASE" == "$BASE2" ]] && ok "build is deterministic ($BASE)" || bad "two builds gave different SHAs ($BASE vs $BASE2)"
[[ "$BASE" == "$(exp base_sha x)" ]] && ok "base_sha matches expected.d" || bad "base_sha $BASE != expected.d $(exp base_sha x)"

# 2. independent mini-guards (NOT actl code)
glob_match() { local p="$1" g="${2//\*\*/*}"; [[ "$p" == $g ]]; }
SECRET_RE='AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----'
FORBID_RE='(^|[^A-Za-z0-9_.])(eval|exec)\(|os\.system\(|subprocess|urllib\.request|import socket|requests\.'
g3() { # g3 <repo> <scope-file>
  local repo="$1" scope="$2" p rc=0 rule kind pat lit_allowed frozen glob_allowed
  while IFS= read -r p; do
    lit_allowed=0; frozen=0; glob_allowed=0
    while IFS= read -r rule; do
      rule="${rule%%[[:space:]]}"; [[ -z "$rule" || "$rule" == \#* ]] && continue
      kind="${rule%%:*}"; pat="${rule#*: }"
      if [[ "$kind" == ALLOW ]]; then
        if [[ "$pat" != *'*'* ]]; then [[ "$p" == "$pat" ]] && lit_allowed=1; else glob_match "$p" "$pat" && glob_allowed=1; fi
      elif [[ "$kind" == FROZEN ]]; then glob_match "$p" "$pat" && frozen=1; fi
    done < "$scope"
    if (( lit_allowed )); then continue
    elif (( frozen )); then echo "FAIL: G3 path $p is frozen by scope"; rc=1
    elif (( glob_allowed )); then continue
    else echo "FAIL: G3 path $p is denied by scope (not in ALLOW)"; rc=1; fi
  done < <(cd "$repo" && ggit diff --cached --name-only)
  return $rc
}
g4() { # g4 <repo> <scope-file> <base-repo>
  local repo="$1" scope="$2" baserepo="$3" b a
  grep -Eq '^ALLOW: test/[^*]+$' "$scope" || return 0
  b="$(grep -h '^[[:space:]]*def test_' "$baserepo"/test/*.py | wc -l)"; a="$(grep -h '^[[:space:]]*def test_' "$repo"/test/*.py | wc -l)"
  if (( a < b )); then echo "FAIL: G4 test function count decreased ($b -> $a)"; return 1; fi
  return 0
}
added() { (cd "$1" && ggit diff --cached -U0 | grep -E '^\+[^+]' | sed 's/^+//'); }
g5() { local hit; hit="$(added "$1" | grep -E "$SECRET_RE" | head -1)"; [[ -z "$hit" ]] || { echo "FAIL: G5 secret pattern matched in added line"; return 1; }; }
g6() { local hit; hit="$(added "$1" | grep -E "$FORBID_RE" | head -1)"; [[ -z "$hit" ]] || { echo "FAIL: G6 forbidden call in added line: $hit"; return 1; }; }

printf 'x = "AKIAIOSFODNN7EXAMPLE"\n' | grep -Eq "$SECRET_RE" && ok "G5 self-test catches synthetic secret" || bad "G5 self-test failed"
printf 'y = eval("1")\n' | grep -Eq "$FORBID_RE" && ok "G6 self-test catches synthetic eval" || bad "G6 self-test failed"
printf 'retrieval = 1\n' | grep -Eq "$FORBID_RE" && bad "G6 self-test false positive on 'retrieval'" || ok "G6 self-test no false positive"

# F006 tripwire pattern (spec O-5): anchored to records/ — bare word "records" must not match (DC-9)
F006_RE='records/|/etc/actl|probe\.sh|/proofs/|/mutants/'
printf 'open("$ACTL_ROOT/records/x")\n' | grep -Eq "$F006_RE" && ok "F006 self-test catches records/ path" || bad "F006 self-test missed records/ path"
printf 'n_records = len(items)\n' | grep -Eq "$F006_RE" && bad "F006 self-test false positive on bare word records" || ok "F006 self-test no false positive on bare word records"

# Layout transition fixture invariants (L-5, L-10): renamed kinds and repo-scoped install path
[[ -d "$GOLDEN/artifacts/valid/verification" && -d "$GOLDEN/artifacts/valid/qualification" ]] \
  && [[ ! -d "$GOLDEN/artifacts/valid/ev" && ! -d "$GOLDEN/artifacts/valid/qual" ]] \
  && ok "golden artifact dirs use verification/qualification (not ev/qual)" \
  || bad "golden artifact dirs missing verification/qualification or still have ev/qual"
grep -q '"kind": "verification"' "$GOLDEN/artifacts/valid/verification/verification_base.json" \
  && ok "verification_base kind is verification" \
  || bad "verification_base kind is not verification"
grep -q '"kind": "qualification"' "$GOLDEN/artifacts/valid/qualification/qualification_base.json" \
  && ok "qualification_base kind is qualification" \
  || bad "qualification_base kind is not qualification"
grep -q 'records/target-repo' "$GOLDEN/build_golden.sh" \
  && ok "build_golden install path is repo-scoped under records/" \
  || bad "build_golden.sh missing records/target-repo install path"
grep -q '"repo":"target-repo"' "$GOLDEN/build_golden.sh" \
  && ok "build_golden state template records repo field" \
  || bad "build_golden.sh state template missing repo field"

# 3. oracle + repo-test runner
run_tests() { # on failure prints "STEP ..." and "LINE ..."
  local repo="$1" out rc fl stem name
  if python3 -c 'import pytest' 2>/dev/null; then out="$(cd "$repo" && python3 -m pytest test -q -rf --color=no -p no:cacheprovider 2>&1)"; rc=$?
  else out="$(cd "$repo" && python3 -m unittest discover -s test -t . 2>&1)"; rc=$?; fi
  (( rc == 0 )) && return 0
  fl="$(printf '%s\n' "$out" | grep -E '^(FAILED|FAIL:|ERROR:)' | head -1)"
  case "$fl" in
    FAILED*) name="$(printf '%s' "$fl" | sed -E 's/^FAILED [^ ]*::([A-Za-z0-9_]+)( .*)?$/\1/')"
             stem="$(printf '%s' "$fl" | sed -E 's#^FAILED (.*/)?(test_[A-Za-z0-9]+)\.py.*#\2#')" ;;
    *)       name="$(printf '%s' "$fl" | awk '{print $2}')"; stem="$(printf '%s' "$fl" | sed -E 's/.*\(test\.(test_[a-z0-9]+)\..*/\1/')" ;;
  esac
  echo "STEP O2:${stem:-test_users}::${name:-unknown}"
  echo "LINE FAIL: repo test failed: ${name:-unknown}"
  return 1
}
run_oracle() { # run_oracle <repo> <oracle-dir>; sets FAILSET FIRST_STEP FIRST_LINE
  local repo="$1" orc="$2" f out rc names=""
  FIRST_STEP=""; FIRST_LINE=""
  for f in "$orc"/proofs/*.sh "$orc"/probe.sh; do
    out="$(cd "$repo" && bash "$f" 2>&1)"; rc=$?
    if (( rc != 0 )); then
      names="$names $(basename "$f")"
      if [[ -z "$FIRST_STEP" ]]; then FIRST_STEP="O1:$(basename "$f")"; FIRST_LINE="$(printf '%s\n' "$out" | grep -m1 '^FAIL:' || echo "$out")"; fi
    fi
  done
  FAILSET="${names# }"
  if [[ -z "$FIRST_STEP" ]]; then
    local t; t="$(run_tests "$repo")" || { FIRST_STEP="$(printf '%s\n' "$t" | sed -n 's/^STEP //p')"; FIRST_LINE="$(printf '%s\n' "$t" | sed -n 's/^LINE //p')"; }
  fi
}
checkout() { local dest="$1"; shift; rm -rf "$dest"; cp -R "$W/base1" "$dest"; (cd "$dest" && ggit update-index -q --refresh)
  local p; for p in "$@"; do (cd "$dest" && ggit apply --index "$p") || return 1; done; }
ORC="$GOLDEN/sprint/oracle"; KEY="$GOLDEN/sprint/solution_key.patch"

# 4. null base red
checkout "$W/r_base" || bad "cannot checkout base"
run_oracle "$W/r_base" "$ORC"
N_PROOFS=$(ls "$ORC"/proofs/*.sh | wc -l)
[[ "$(wc -w <<<"$FAILSET")" -eq $((N_PROOFS+1)) ]] && ok "base: every proof and probe is red" || bad "base: expected all $((N_PROOFS+1)) proofs red, red set = [$FAILSET]"
[[ "$FIRST_STEP" == "$(exp null_base failing_step)" ]] && ok "base: first failing step $FIRST_STEP" || bad "base: first failing step '$FIRST_STEP' != '$(exp null_base failing_step)'"
[[ "$FIRST_LINE" == *"$(exp null_base failing_line_contains)"* ]] && ok "base: failing line has FAIL:" || bad "base: failing line '$FIRST_LINE'"
run_tests "$W/r_base" >/dev/null && ok "base: repo tests green" || bad "base: repo tests are not green"

# 5. key green 3x
checkout "$W/r_key" "$KEY" || bad "solution_key.patch does not apply on base"
for i in 1 2 3; do
  run_oracle "$W/r_key" "$ORC"
  [[ -z "$FIRST_STEP" ]] && ok "key run $i/3 green (O1+O2)" || bad "key run $i/3 red at $FIRST_STEP: $FIRST_LINE"
done
g3 "$W/r_key" "$ORC/scope.txt" >/dev/null && g5 "$W/r_key" >/dev/null && g6 "$W/r_key" >/dev/null && ok "key passes G3/G5/G6" || bad "key fails a guard"

# 6. mutants
mapped() { python3 - "$ORC/coverage.md" "mutants/$1" <<'PY'
import re, sys
for l in open(sys.argv[1]):
    m = re.match(r'^((?:mutants/)?[A-Za-z0-9_.-]+\.patch)\s*(?:->|→|:)\s*(.+)$', l.strip())
    if m and m.group(1) == sys.argv[2]:
        print(" ".join(sorted(x.strip() for x in m.group(2).split(","))))
PY
}
SURVIVORS=0
for mp in "$ORC"/mutants/*.patch; do
  mn="$(basename "$mp" .patch)"
  checkout "$W/r_m" "$KEY" "$mp" || { bad "mutant $mn does not apply on base+key"; continue; }
  run_oracle "$W/r_m" "$ORC"; want="$(mapped "$mn.patch")"
  if [[ "$mn" == "avatar_drop" ]]; then
    [[ -z "$FAILSET" && -z "$FIRST_STEP" ]] && { ok "mutant $mn survives (deliberate)"; SURVIVORS=$((SURVIVORS+1)); } || bad "mutant $mn must survive but failed [$FAILSET]"
  else
    [[ "$FAILSET" == "$want" ]] && ok "mutant $mn killed exactly by [$FAILSET]" || bad "mutant $mn killed by [$FAILSET], coverage.md says [$want]"
  fi
  [[ "$FIRST_STEP" == "$(exp "mutant_$mn" failing_step)" ]] && ok "mutant $mn first failing step '${FIRST_STEP:-none}' as declared" || bad "mutant $mn failing step '$FIRST_STEP' != declared '$(exp "mutant_$mn" failing_step)'"
done
(( SURVIVORS == 1 )) && ok "exactly one deliberate survivor" || bad "expected exactly 1 surviving mutant, got $SURVIVORS"

# 7/8. candidates: guards G3,G4,G5,G6 then O1,O2
evaluate() {
  local c="$1" patch="$GOLDEN/implementations/$c.patch" scope="$ORC/scope.txt" line
  [[ -f "$GOLDEN/sprint/scope_overrides/$c.txt" ]] && scope="$GOLDEN/sprint/scope_overrides/$c.txt"
  checkout "$W/r_c" "$patch" || { echo "APPLY|1|apply|patch does not apply"; return; }
  line="$(g3 "$W/r_c" "$scope")" || { echo "G3|1|G3|$line"; return; }
  line="$(g4 "$W/r_c" "$scope" "$W/base1")" || { echo "G4|1|G4|$line"; return; }
  line="$(g5 "$W/r_c")" || { echo "G5|1|G5|$line"; return; }
  line="$(g6 "$W/r_c")" || { echo "G6|1|G6|$line"; return; }
  run_oracle "$W/r_c" "$ORC"
  if [[ -z "$FIRST_STEP" ]]; then echo "O2|0||"; else echo "${FIRST_STEP%%:*}|1|$FIRST_STEP|$FIRST_LINE"; fi
}
for c in good bad_scope bad_testcount bad_secret bad_forbidden bad_proof_o1 bad_regression_o2; do
  IFS='|' read -r st ex fs ln <<<"$(evaluate "$c")"
  w_st="$(exp "$c" step)"; w_ex="$(exp "$c" exit)"; w_fs="$(exp "$c" failing_step)"; w_ln="$(exp "$c" failing_line_contains)"
  if [[ "$st" == "$w_st" && "$ex" == "$w_ex" && "$fs" == "$w_fs" && ( -z "$w_ln" || "$ln" == *"$w_ln"* || "$w_ln" == "secret pattern" && "$ln" == *"secret pattern"* ) ]]; then ok "$c -> step=$st exit=$ex failing=${fs:-none}"
  else bad "$c: got step=$st exit=$ex failing='$fs' line='$ln' ; want step=$w_st exit=$w_ex failing='$w_fs' contains='$w_ln'"; fi
done
checkout "$W/r_c" "$GOLDEN/implementations/bad_testcount.patch"
G3OUT="$(g3 "$W/r_c" "$ORC/scope.txt" 2>&1)"; [[ "$G3OUT" == *frozen* ]] && ok "bad_testcount under default scope fails G3 (frozen)" || bad "bad_testcount under default scope not stopped by G3"
checkout "$W/r_c" "$KEY"; run_oracle "$W/r_c" "$ORC"
if [[ -z "$FIRST_STEP" ]]; then st=O2; ex=0; else st="${FIRST_STEP%%:*}"; ex=1; fi
[[ "$st|$ex" == "$(exp solution_key step)|$(exp solution_key exit)" ]] && ok "solution_key case matches expected.d" || bad "solution_key case mismatch ($st|$ex)"

echo "=========================================="
if (( FAILS == 0 )); then echo "golden_selfcheck: ALL CHECKS PASSED"; exit 0; fi
echo "golden_selfcheck: $FAILS check(s) FAILED"; exit 1
