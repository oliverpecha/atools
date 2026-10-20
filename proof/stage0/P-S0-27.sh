#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# P-S0-27 (extra, S0-R11): conformance of proof/run_suite_actl_s0.sh to the run_check pattern of proof/run_suite_engines.sh.
# Static: pattern markers. Dynamic: idempotence, ONLY filter, exit-code mapping 0/1/4 and per-check logs, temporary ACTL_ROOT that is
# removed afterwards and never equals the caller's. NOT listed inside the suite itself (it would recurse): run it separately.
# Exit 0 pass | 1 red | 4 environment.
set -uo pipefail
REPO="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
SUITE="$REPO/proof/run_suite_actl_s0.sh"
for t in bash mktemp diff; do command -v "$t" >/dev/null 2>&1 || { echo "FAIL: $t not installed (environment error)"; exit 4; }; done
rc=0; bad() { echo "FAIL: $*"; rc=1; }
[[ -f "$SUITE" ]] || { echo "FAIL: $SUITE does not exist (S0-R11)"; exit 1; }
bash -n "$SUITE" 2>/dev/null || bad "run_suite_actl_s0.sh has a syntax error"
for pat in 'run_check()' 'proof/out' 'mktemp' 'set -uo pipefail' 'Suite Summary:' 'PASS=' 'FAIL='; do
  grep -qF -- "$pat" "$SUITE" || bad "S0-R11.1: suite lacks the run_check-pattern marker: $pat"
done
grep -Eq 'exit 1' "$SUITE" || bad "S0-R11.1: suite has no non-zero exit on failure"
[[ -x "$SUITE" ]] || bad "suite is not executable"
(( rc == 0 )) || exit 1
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
# idempotence + per-check log (uses the one check that needs no actl code)
o1="$(ACTL_ROOT=/nonexistent-caller-root ONLY=P-S0-10 bash "$SUITE" 2>&1)"; r1=$?
o2="$(ACTL_ROOT=/nonexistent-caller-root ONLY=P-S0-10 bash "$SUITE" 2>&1)"; r2=$?
[[ $r1 -eq 0 && $r2 -eq 0 ]] || bad "S0-R11.2: ONLY=P-S0-10 must exit 0 twice, got $r1 and $r2"
[[ "$o1" == "$o2" ]] || bad "S0-R11.1: two runs give different output (not idempotent)"
grep -q 'Suite Summary: 1 Passed, 0 Failed' <<<"$o1" || bad "S0-R11.1: summary line wrong for one passing check: $(grep 'Suite Summary' <<<"$o1")"
ls "$REPO"/proof/out/P-S0-10*.log >/dev/null 2>&1 && [[ -s "$(ls "$REPO"/proof/out/P-S0-10*.log | head -1)" ]] || bad "S0-R11.1: no non-empty per-check log in proof/out/"
o3="$(ONLY=__no_such_check__ bash "$SUITE" 2>&1)"; r3=$?
[[ $r3 -eq 0 ]] && grep -q '0 Passed, 0 Failed' <<<"$o3" || bad "S0-R11.2: ONLY with no match must exit 0 with 0/0"
# exit-code mapping in a scratch copy with a replaced check
mkdir -p "$T/repo/proof/stage0"; cp "$SUITE" "$T/repo/proof/"; cp -R "$REPO"/proof/stage0/. "$T/repo/proof/stage0/" 2>/dev/null
SC="$T/repo/proof/stage0/P-S0-03.sh"
probe() { printf '#!/usr/bin/env bash\n%s\n' "$1" > "$SC"; chmod +x "$SC"; ACTL_REPO="$T/repo" ACTL_ROOT=/nonexistent-caller-root ONLY=P-S0-03 bash "$T/repo/proof/run_suite_actl_s0.sh" 2>&1; }
out="$(probe 'echo "FAIL: planted"; exit 1')"; r=$?
[[ $r -eq 1 ]] && grep -q '1 Failed' <<<"$out" && grep -q 'FAIL: planted' <<<"$out" || bad "S0-R11.1: a red check must give suite exit 1 and show its FAIL: line (got $r)"
out="$(probe 'exit 4')"; r=$?
[[ $r -eq 4 ]] || bad "S0-R11.2: only an environment result must give suite exit 4 (got $r)"
out="$(probe 'exit 0')"; r=$?
[[ $r -eq 0 ]] && grep -q '1 Passed, 0 Failed' <<<"$out" || bad "S0-R11.1: a green check must give exit 0 (got $r)"
[[ -s "$T/repo/proof/out/P-S0-03_layout.log" || -e "$T/repo/proof/out/P-S0-03_layout.log" ]] || bad "S0-R11.1: log for P-S0-03_layout missing in proof/out/"
out="$(probe 'echo "ROOT=$ACTL_ROOT"; [[ "$ACTL_ROOT" != /nonexistent-caller-root && -d "$ACTL_ROOT" ]] || exit 1; exit 0')"; r=$?
[[ $r -eq 0 ]] || bad "S0-R11.1: the suite must give each check a fresh temporary ACTL_ROOT (not the caller's)"
root="$(sed -n 's/^ROOT=//p' "$T/repo/proof/out/P-S0-03_layout.log" | head -1)"
[[ -n "$root" && ! -e "$root" ]] || bad "S0-R11.1: the temporary ACTL_ROOT was not removed after the run ($root)"
(( rc == 0 )) && echo "OK: P-S0-27 suite conforms"
exit $rc
