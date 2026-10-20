#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# proof/stage0/selfcheck_mutations.sh - checks the checker: golden_selfcheck.sh (P-S0-10) must be GREEN on the pristine fixture (control)
# and RED on every planted fixture defect below. Exit 0 = control green and every mutant detected; 1 otherwise; 4 = tool missing.
# Runs golden_selfcheck.sh with GOLDEN_DIR pointing at a mutated copy; the real fixture is never modified.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GOLD="${GOLDEN_SRC:-$(cd "$HERE/../../fixtures/golden" && pwd)}"
CHECK="${SELFCHECK:-$HERE/golden_selfcheck.sh}"
for t in bash git python3 sed; do command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed (environment error)"; exit 4; }; done
[[ -f "$CHECK" && -d "$GOLD" ]] || { echo "FAIL: golden dir or golden_selfcheck.sh missing"; exit 1; }
W="$(mktemp -d)"; trap 'rm -rf "$W"' EXIT
fresh() { rm -rf "$W/g"; cp -R "$GOLD" "$W/g"; }
fails=0; n=0
run_selfcheck() { GOLDEN_DIR="$W/g" bash "$CHECK" >"$W/out" 2>&1; return $?; }
# control
fresh; run_selfcheck; rc=$?
if (( rc != 0 )); then echo "FAIL: control: golden_selfcheck.sh is not green on the pristine fixture (exit $rc)"; tail -5 "$W/out"; exit 1; fi
echo "ok: control green"
mutant() { # mutant <id> <description> <shell snippet run inside the copy ($W/g)>
  local id="$1" desc="$2" snippet="$3"; n=$((n+1))
  fresh; ( cd "$W/g" && eval "$snippet" ) >/dev/null 2>&1 || { echo "FAIL: $id: mutation could not be applied (harness problem)"; fails=$((fails+1)); return; }
  if cmp -s <(cd "$GOLD" && find . -type f -exec sha256sum {} + | sort -k2) <(cd "$W/g" && find . -type f -exec sha256sum {} + | sort -k2); then
    echo "FAIL: $id: mutation changed nothing (vacuous mutant)"; fails=$((fails+1)); return; fi
  run_selfcheck; rc=$?
  if (( rc == 1 )); then echo "ok: $id detected ($desc)"; grep -m1 '^FAIL:' "$W/out" | sed 's/^/      /'
  else echo "FAIL: $id: golden_selfcheck.sh exited $rc on a planted defect ($desc)"; fails=$((fails+1)); fi
}
mutant M01 "wrong base_sha in expected.d"            "sed -i 's/01d880bc3176cdd8f31d72e67bb3eba54d634378/0000000000000000000000000000000000000000/' expected.d/base.json"
mutant M02 "target-repo content changed (SHA drifts)" "echo '# drift' >> target-repo/api/users.py"
mutant M03 "mutant remapped to a proof that cannot kill it" "sed -i 's#^mutants/contact_leak.patch -> 02_no_email.sh#mutants/contact_leak.patch -> 01_public.sh#' sprint/oracle/coverage.md"
mutant M04 "avatar assertion added: survivor becomes killable" "sed -i 's#^pc = b.get(\"photo_count\")#if b.get(\"avatar\") is None: print(\"FAIL: avatar missing\"); sys.exit(1)\npc = b.get(\"photo_count\")#' sprint/oracle/proofs/01_public.sh"
mutant M05 "02_no_email.sh weakened to always pass"   "printf '#!/usr/bin/env bash\necho OK\n' > sprint/oracle/proofs/02_no_email.sh"
mutant M06 "probe.sh weakened to always pass"         "printf '#!/usr/bin/env bash\necho OK\n' > sprint/oracle/probe.sh"
mutant M07 "03_private_404.sh weakened to always pass" "printf '#!/usr/bin/env bash\necho OK\n' > sprint/oracle/proofs/03_private_404.sh"
mutant M08 "good.patch replaced by a leaking patch"   "cp implementations/bad_proof_o1.patch implementations/good.patch"
mutant M09 "bad_regression_o2 replaced by good.patch" "cp implementations/good.patch implementations/bad_regression_o2.patch"
mutant M10 "bad_secret replaced by good.patch"        "cp implementations/good.patch implementations/bad_secret.patch"
mutant M11 "bad_forbidden replaced by good.patch"     "cp implementations/good.patch implementations/bad_forbidden.patch"
mutant M12 "scope.txt widened: bad_scope no longer denied" "echo 'ALLOW: api/cli.py' >> sprint/oracle/scope.txt"
mutant M13 "scope override removed: bad_testcount stops at G3, not G4" "rm sprint/scope_overrides/bad_testcount.txt"
mutant M14 "declared failing step of bad_scope changed" "sed -i '0,/\"failing_step\": \"G3\"/s//\"failing_step\": \"G4\"/' expected.d/base.json"
mutant M15 "solution key sabotaged: avatar field returns the email" "sed -i 's#+        \"avatar\": user\[\"avatar\"\],#+        \"avatar\": user[\"email\"],#' sprint/solution_key.patch"
mutant M16 "a mutant patch no longer applies"         "echo 'garbage' > sprint/oracle/mutants/private_200.patch"
mutant M17 "second survivor planted (photo_count_off neutralised)" "sed -i 's/len(user\\[\"photos\"\\]) + 1/len(user[\"photos\"])/' sprint/oracle/mutants/photo_count_off.patch"
mutant M18 "proof 01 deleted"                         "rm sprint/oracle/proofs/01_public.sh"
echo "=========================================="
if (( fails == 0 )); then echo "selfcheck_mutations: control green, all $n planted defects detected"; exit 0; fi
echo "selfcheck_mutations: $fails problem(s) over $n mutants"; exit 1
