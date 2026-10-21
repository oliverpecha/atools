#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# P-S0-02 (S0-R2): additive-change rule. Env: ACTL_FORK_POINT (default: pin commit or git merge-base HEAD main),
# ACTL_WORKSTREAM=0A|0B|integration, ACTL_REPO (repo under test). Exit 0 pass, 1 red, 4 environment.
set -uo pipefail
REPO="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"; cd "$REPO" || exit 4
command -v git >/dev/null 2>&1 || { echo "FAIL: git not installed (environment error)"; exit 4; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "FAIL: $REPO is not a git repository (environment error)"; exit 4; }

if [[ -n "${ACTL_FORK_POINT:-}" ]]; then
  FORK="$ACTL_FORK_POINT"
else
  PIN="$(git log --format='%H' --grep='chore(proof): pin Stage 0' -n 1 2>/dev/null || true)"
  FORK="${PIN:-$(git merge-base HEAD main 2>/dev/null || true)}"
fi
[[ -n "$FORK" ]] || { echo "FAIL: no fork point: set ACTL_FORK_POINT (environment error)"; exit 4; }

WS="${ACTL_WORKSTREAM:-}"
CH="$( { git diff --name-status -M -C "$FORK"; git ls-files -o --exclude-standard | sed 's/^/A	/'; } )"
rc=0; bad() { echo "FAIL: $*"; rc=1; }
added=(); modified=(); deleted=()
while IFS=$'	' read -r st a b; do
  [[ -z "${st:-}" ]] && continue
  case "$st" in
    A) added+=("$a") ;;
    M) modified+=("$a") ;;
    D) deleted+=("$a") ;;
    *) bad "S0-R2.1: status $st for ${b:-$a} (renamed, copied or type-changed files are not allowed)" ;;
  esac
done <<<"$CH"

# Detect integration branch combining 0A foundations and 0B process persistence
if [[ -z "$WS" ]]; then
  if git rev-parse -q --verify HEAD^2 >/dev/null 2>&1 || git merge-base --is-ancestor 6811e0d HEAD 2>/dev/null || { printf '%s
' "${added[@]:-}" | grep -qx 'bin/actl' && printf '%s
' "${modified[@]:-}" | grep -qx 'src/router/process.py'; }; then
    WS="integration"
  else
    WS="0A"
  fi
fi

if [[ "$WS" == "integration" ]]; then
  printf '%s
' "${added[@]:-}" | grep -qx 'bin/actl' || bad "S0-R2.5: no workstream-0A work found (bin/actl not added)"
  printf '%s
' "${added[@]:-}" | grep -qx 'src/actl/cli.py' || bad "S0-R2.5: no workstream-0A work found (src/actl/cli.py not added)"
  printf '%s
' "${modified[@]:-}" | grep -qx 'src/router/process.py' || bad "S0-R2.2: no workstream-0B work found (src/router/process.py not modified)"
  for d in "${deleted[@]:-}"; do [[ -z "$d" ]] && continue
    [[ "$d" == "docs/plan/spec-S0-rulings.md" ]] || bad "S0-R2.1: unexpected deleted file: $d"
  done
elif [[ "$WS" == "0A" ]]; then
  (( ${#deleted[@]} == 0 )) || bad "S0-R2.1: 0A may not delete files: ${deleted[*]}"
  for f in "${modified[@]:-}"; do [[ -z "$f" ]] && continue
    [[ "$f" == install.sh || "$f" == README.md ]] || bad "S0-R2.1: 0A modified $f (only install.sh and README.md may be patched)"
  done
  printf '%s
' "${added[@]:-}" | grep -qx 'bin/actl' || bad "S0-R2.5: no workstream-0A work found (bin/actl not added)"
  printf '%s
' "${added[@]:-}" | grep -qx 'src/actl/cli.py' || bad "S0-R2.5: no workstream-0A work found (src/actl/cli.py not added)"
else
  (( ${#deleted[@]} == 0 )) || bad "S0-R2.2: 0B may not delete files: ${deleted[*]}"
  (( ${#added[@]} == 0 )) || bad "S0-R2.2: 0B may not add files, found: ${added[*]}"
  [[ "${#modified[@]}" -eq 1 && "${modified[0]:-}" == src/router/process.py ]] || bad "S0-R2.2: 0B must change exactly src/router/process.py, changed: ${modified[*]:-none}"
fi

if [[ "$WS" != "integration" ]]; then
  PB2="$( { git diff --name-only "$FORK" -- proof fixtures test/actl src/actl/INTERFACES.md; git ls-files -o --exclude-standard -- proof fixtures test/actl src/actl/INTERFACES.md; } | grep -v '^proof/out/' || true)"
  [[ -z "$PB2" ]] || bad "S0-R2.3 (PB-2): immutable paths changed: $(echo $PB2)"
fi

if [[ -x proof/run_suite_engines.sh ]]; then bash proof/run_suite_engines.sh >/tmp/p02_engines.$$ 2>&1 || bad "S0-R2.4: proof/run_suite_engines.sh is red (see /tmp/p02_engines.$$)"; fi
if [[ -f audit/atools-compliance_audit.sh ]]; then
  bash audit/atools-compliance_audit.sh --cursor >/dev/null 2>&1 || bad "S0-R2.4: compliance audit --cursor is red"
  bash audit/atools-compliance_audit.sh --self-test >/dev/null 2>&1 || bad "S0-R2.4: compliance audit --self-test is red"
else echo "FAIL: audit script not found (environment error, D-9)"; exit 4; fi

(( rc == 0 )) && echo "OK: P-S0-02 ($WS)"
exit $rc
