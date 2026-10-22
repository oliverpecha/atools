#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# P-S0-02 (S0-R2): additive-change rule. Env: ACTL_FORK_POINT (default: pin commit or git merge-base HEAD main),
# ACTL_WORKSTREAM=0A|0B|integration, ACTL_REPO (repo under test). Exit 0 pass, 1 red, 4 environment.
set -uo pipefail
THIS_SCRIPT="$(realpath "${BASH_SOURCE[0]}")"
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
CH="$( { git diff --name-status -M -C "$FORK"; git ls-files -o --exclude-standard | sed 's/^/A\t/'; } )"
rc=0; bad() { echo "FAIL: $*"; rc=1; }
added=(); modified=(); deleted=()
while IFS=$'\t' read -r st a b; do
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
  if git rev-parse -q --verify HEAD^2 >/dev/null 2>&1 || git merge-base --is-ancestor 6811e0d HEAD 2>/dev/null || { printf '%s\n' "${added[@]:-}" | grep -qx 'bin/actl' && printf '%s\n' "${modified[@]:-}" | grep -qx 'src/router/process.py'; }; then
    WS="integration"
  else
    WS="0A"
  fi
fi

is_allowed_addition() {
  local f="$1"
  [[ "$f" == "src/actl/INTERFACES.md" ]] && return 1
  case "$f" in
    src/actl/*|schemas/*|proof/stage0/*|test/actl/*|fixtures/*) return 0 ;;
    config/graph.toml|bin/actl|install.sh|README.md|proof/run_suite_actl_s0.sh|proof/run_suite_gate_d.sh|docs/plan/spec-S0.md) return 0 ;;
    *) return 1 ;;
  esac
}

is_allowed_modification() {
  local f="$1"
  if [[ "$f" == "src/actl/INTERFACES.md" ]]; then
    # PB-2/PB-4: Allowed only if matching the Owner-approved PB-4 contract (81465b0)
    if git hash-object "$REPO/src/actl/INTERFACES.md" 2>/dev/null | grep -q '^81465b0' &&        grep -q 'approved by Owner (PB-4)' "$REPO/src/actl/INTERFACES.md" 2>/dev/null; then
      return 0
    fi
    return 1
  fi
  if is_allowed_addition "$f"; then
    return 0
  fi
  case "$f" in
    src/router/process.py|proof/run_suite_exit_code.sh|install.sh|README.md|VERSION|hooks/commit-msg|proof/run_suite_commit_msg.sh) return 0 ;;
    *) return 1 ;;
  esac
}

is_allowed_deletion() {
  local f="$1"
  [[ "$f" == "docs/plan/spec-S0-rulings.md" ]]
}

if [[ "$WS" == "integration" ]]; then
  printf '%s\n' "${added[@]:-}" | grep -qx 'bin/actl' || bad "S0-R2.5: no workstream-0A work found (bin/actl not added)"
  printf '%s\n' "${added[@]:-}" | grep -qx 'src/actl/cli.py' || bad "S0-R2.5: no workstream-0A work found (src/actl/cli.py not added)"
  printf '%s\n' "${modified[@]:-}" | grep -qx 'src/router/process.py' || bad "S0-R2.2: no workstream-0B work found (src/router/process.py not modified)"
  for a in "${added[@]:-}"; do [[ -z "$a" ]] && continue
    is_allowed_addition "$a" || bad "S0-R2.1: unauthorized file change: $a"
  done
  for m in "${modified[@]:-}"; do [[ -z "$m" ]] && continue
    is_allowed_modification "$m" || bad "S0-R2.1: unauthorized file change: $m"
  done
  for d in "${deleted[@]:-}"; do [[ -z "$d" ]] && continue
    is_allowed_deletion "$d" || bad "S0-R2.1: unexpected deleted file: $d"
  done
elif [[ "$WS" == "0A" ]]; then
  (( ${#deleted[@]} == 0 )) || bad "S0-R2.1: 0A may not delete files: ${deleted[*]}"
  for f in "${modified[@]:-}"; do [[ -z "$f" ]] && continue
    [[ "$f" == install.sh || "$f" == README.md ]] || bad "S0-R2.1: 0A modified $f (only install.sh and README.md may be patched)"
  done
  printf '%s\n' "${added[@]:-}" | grep -qx 'bin/actl' || bad "S0-R2.5: no workstream-0A work found (bin/actl not added)"
  printf '%s\n' "${added[@]:-}" | grep -qx 'src/actl/cli.py' || bad "S0-R2.5: no workstream-0A work found (src/actl/cli.py not added)"
else
  (( ${#deleted[@]} == 0 )) || bad "S0-R2.2: 0B may not delete files: ${deleted[*]}"
  (( ${#added[@]} == 0 )) || bad "S0-R2.2: 0B may not add files, found: ${added[*]}"
  [[ "${#modified[@]}" -eq 1 && "${modified[0]:-}" == src/router/process.py ]] || bad "S0-R2.2: 0B must change exactly src/router/process.py, changed: ${modified[*]:-none}"
fi

# PB-2: frozen-path check across all modes
PB2_BASE="$(git diff --name-only "$FORK" -- fixtures/golden/expected.d/base.json)"
[[ -z "$PB2_BASE" ]] || bad "S0-R2.3 (PB-2): immutable fixtures/golden/expected.d/base.json changed: $PB2_BASE"

if git diff --name-only "$FORK" -- src/actl/INTERFACES.md | grep -q .; then
  if ! git hash-object "$REPO/src/actl/INTERFACES.md" 2>/dev/null | grep -q '^81465b0' ||      ! grep -q 'approved by Owner (PB-4)' "$REPO/src/actl/INTERFACES.md" 2>/dev/null; then
    bad "S0-R2.3 (PB-2): immutable src/actl/INTERFACES.md changed without Owner approval (PB-4)"
  fi
fi

if [[ "$WS" == "0A" || "$WS" == "0B" ]]; then
  PB2="$( { git diff --name-only "$FORK" -- proof fixtures test/actl src/actl/INTERFACES.md; git ls-files -o --exclude-standard -- proof fixtures test/actl src/actl/INTERFACES.md; } | grep -v '^proof/out/' || true)"
  [[ -z "$PB2" ]] || bad "S0-R2.3 (PB-2): immutable paths changed: $(echo $PB2)"
fi

# Negative self-checks (executed once when not in a self-test run)
if [[ -z "${ACTL_P02_SELFTEST:-}" ]]; then
  ST_DIR="$(mktemp -d /tmp/p02_selftest.XXXXXX)"
  cleanup_selftest() {
    git worktree remove --force "$ST_DIR" >/dev/null 2>&1 || true
    rm -rf "$ST_DIR"
  }
  trap cleanup_selftest EXIT INT TERM
  if git worktree add --detach "$ST_DIR" HEAD >/dev/null 2>&1; then
    # 1. Negative self-check: unauthorized file outside whitelist
    touch "$ST_DIR/unauthorized.txt"
    if ACTL_REPO="$ST_DIR" ACTL_FORK_POINT="$FORK" ACTL_WORKSTREAM="integration" ACTL_P02_SELFTEST=1 bash "$THIS_SCRIPT" >/dev/null 2>&1; then
      bad "S0-R2.1: selftest failed: unauthorized file was not rejected"
    fi
    rm -f "$ST_DIR/unauthorized.txt"

    # 2. Negative self-check: modification to fixtures/golden/expected.d/base.json
    echo '{"tampered": true}' > "$ST_DIR/fixtures/golden/expected.d/base.json"
    if ACTL_REPO="$ST_DIR" ACTL_FORK_POINT="$FORK" ACTL_WORKSTREAM="integration" ACTL_P02_SELFTEST=1 bash "$THIS_SCRIPT" >/dev/null 2>&1; then
      bad "S0-R2.3: selftest failed: tampered fixtures/golden/expected.d/base.json was not rejected"
    fi

    # 3. Negative self-check: tampering with src/actl/INTERFACES.md
    echo "tampered" > "$ST_DIR/src/actl/INTERFACES.md"
    if ACTL_REPO="$ST_DIR" ACTL_FORK_POINT="$FORK" ACTL_WORKSTREAM="integration" ACTL_P02_SELFTEST=1 bash "$THIS_SCRIPT" >/dev/null 2>&1; then
      bad "S0-R2.3: selftest failed: tampered src/actl/INTERFACES.md was not rejected"
    fi
  else
    bad "S0-R2: could not create git worktree for selftests"
  fi
  cleanup_selftest
  trap - EXIT INT TERM
fi

if [[ -z "${ACTL_P02_SELFTEST:-}" ]]; then
  if [[ -x proof/run_suite_engines.sh ]]; then bash proof/run_suite_engines.sh >/tmp/p02_engines.$$ 2>&1 || bad "S0-R2.4: proof/run_suite_engines.sh is red (see /tmp/p02_engines.$$)"; fi
  if [[ -f audit/atools-compliance_audit.sh ]]; then
    bash audit/atools-compliance_audit.sh --cursor >/dev/null 2>&1 || bad "S0-R2.4: compliance audit --cursor is red"
    bash audit/atools-compliance_audit.sh --self-test >/dev/null 2>&1 || bad "S0-R2.4: compliance audit --self-test is red"
  else echo "FAIL: audit script not found (environment error, D-9)"; exit 4; fi
fi

(( rc == 0 )) && echo "OK: P-S0-02 ($WS)"
exit $rc
