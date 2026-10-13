#!/usr/bin/env bash
# atools compliance audit
# Spec: DESIGN.md and docs/. Check IDs are stable; docs/audits/README.md lists them.
# Core checks are vendor-neutral. Runtime-specific checks live in the ADP section.
# An adapter must be chosen explicitly: --cursor (or --adapter cursor), or --adapter none. There is no default.
# Exit: 0 = no FAIL (and no SKIP under --strict); 1 = failures; 2 = usage error.
set -uo pipefail

ADAPTER=""; CURSOR_FLAG=0; RULES_O=""; OPS_O=""; WORKER_O=""
PROFILE="dev"; REPORT=""; STRICT=0; REPO=""; WORKER_USER=""; ORACLE_PATH=""; SELFTEST=0

usage() {
cat <<'EOF'
Usage: atools-compliance_audit.sh (--cursor | --adapter NAME) [options]
  --adapter NAME         runtime adapter: cursor or none (vendor-neutral checks only). Required unless --cursor is given
  --cursor               shorthand for --adapter cursor
  --rules FILE           agent rules file (overrides the adapter default)
  --operator-doc FILE    operator instructions file (overrides the adapter default)
  --worker-doc FILE      worker instructions file (overrides the adapter default; relative to --repo if not absolute)
  --profile dev|prod     security profile to audit (default: dev)
  --repo PATH            target repo for repo-level checks (default: cwd if inside git)
  --worker-user NAME     prod: implementer OS user (needs passwordless sudo -u NAME)
  --oracle-path PATH     prod: private oracle directory
  --report FILE          also write results to FILE
  --strict               treat SKIP as failure
  --self-test            run the audit against good and deliberately broken fixtures
  -h, --help
Env overrides (for tests): ATOOLS_AUDIT_HOME, ATOOLS_SYS_BIN, ATOOLS_USER_BIN
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --adapter) ADAPTER="${2:-}"; shift 2 ;;
    --cursor) CURSOR_FLAG=1; shift ;;
    --rules) RULES_O="${2:-}"; shift 2 ;;
    --operator-doc) OPS_O="${2:-}"; shift 2 ;;
    --worker-doc) WORKER_O="${2:-}"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --repo) REPO="${2:-}"; shift 2 ;;
    --worker-user) WORKER_USER="${2:-}"; shift 2 ;;
    --oracle-path) ORACLE_PATH="${2:-}"; shift 2 ;;
    --report) REPORT="${2:-}"; shift 2 ;;
    --strict) STRICT=1; shift ;;
    --self-test) SELFTEST=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done
if [[ $CURSOR_FLAG -eq 1 ]]; then
  if [[ -n "$ADAPTER" && "$ADAPTER" != "cursor" ]]; then echo "--cursor conflicts with --adapter $ADAPTER" >&2; exit 2; fi
  ADAPTER="cursor"
fi
if [[ $SELFTEST -eq 0 && -z "$ADAPTER" ]]; then
  echo "no adapter chosen: use --cursor, --adapter cursor, or --adapter none" >&2; usage >&2; exit 2
fi
[[ "$PROFILE" == "dev" || "$PROFILE" == "prod" ]] || { echo "profile must be dev or prod" >&2; exit 2; }

SELF="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"

# ---------------------------------------------------------------- self-test
selftest() {
  local T; T="$(mktemp -d)"; trap 'rm -rf "$T"' RETURN
  local fails=0

  build() {
    rm -rf "$T/f"; local F="$T/f"
    mkdir -p "$F/home/.local/bin" "$F/sys" "$F/home/.cursor/rules" "$F/home/.cursor/skills" \
             "$F/home/.config/git/hooks" "$F/repo/.cursor/skills/atools-repair"
    printf '#!/usr/bin/env bash\ncase "$1" in --show) echo ok;; --get) echo "model-$2";; esac\n' > "$F/home/.local/bin/arouter"
    printf '#!/usr/bin/env bash\necho sessions\n' > "$F/home/.local/bin/asessions"
    printf '#!/usr/bin/env bash\n[[ "${1:-}" == "--version" ]] && echo 1.0\n' > "$F/sys/agent"
    printf '#!/usr/bin/env bash\nMODEL=$(arouter --get "${1:-balanced}")\nexec agent --auto-review --trust --model "$MODEL" "$@"\n' > "$F/sys/arouter"
    for t in acheap abalanced asmart; do
      printf '#!/usr/bin/env bash\nexec /usr/local/bin/arouter "%s" "$@"\n' "${t#a}" > "$F/sys/$t"
    done
    chmod +x "$F"/home/.local/bin/* "$F"/sys/*
    printf 'Work only on wip/* branches.\nNever run git push.\nTag commits with (WI-<id>). Finish with git status.\n' > "$F/home/.cursor/rules/git-safety.md"
    python3 - "$F/home/.cursor/cli-config.json" <<'PY'
import json, sys
cfg = {"version": 1, "approvalMode": "allowlist", "permissions": {
  "allow": ["Shell(ls)", "Shell(git status)"],
  "deny": ["Shell(git push*)", "Shell(git push)", "Shell(rm -rf /)",
           "Shell(git commit *--no-verify*)", "Shell(git commit *-n *)", "Shell(git commit *-n)"]}}
json.dump(cfg, open(sys.argv[1], "w"))
PY
    printf '#!/usr/bin/env bash\nset -e\nB=$(git branch --show-current)\n[[ "$B" =~ ^wip/ ]] || { echo blocked; exit 1; }\nL="$(git rev-parse --git-dir)/hooks/pre-commit.local"\n[[ -x "$L" ]] && "$L" "$@"\nexit 0\n# pre-commit.local delegation\n' > "$F/home/.config/git/hooks/pre-commit"
    chmod +x "$F/home/.config/git/hooks/pre-commit"
    printf '[core]\n\thooksPath = %s/home/.config/git/hooks\n' "$F" > "$F/gitconfig"
    printf 'Operator cheatsheet: asessions, arouter --show\n' > "$F/home/.cursor/skills/atools.md"
    cat > "$F/repo/.cursor/skills/atools-repair/SKILL.md" <<'MD'
# Skill: atools Implementation
1. Read the implementation brief.
2. NEVER edit, create or mock oracle files, proofs or test fixtures.
3. Commit progress on a wip/* branch with a (WI-<id>) tag.
MD
    git init -q "$F/repo" >/dev/null 2>&1
  }

  run_audit() {
    local F="$T/f"; local extra=("$@"); [[ ${#extra[@]} -eq 0 ]] && extra=(--cursor)
    env ATOOLS_AUDIT_HOME="$F/home" ATOOLS_SYS_BIN="$F/sys" ATOOLS_USER_BIN="$F/home/.local/bin" \
        PATH="$F/home/.local/bin:$F/sys:$PATH" GIT_CONFIG_GLOBAL="$F/gitconfig" \
        bash "$SELF" --repo "$F/repo" --report "$T/report.txt" "${extra[@]}" >/dev/null 2>&1
  }

  expect_pass() {
    build; run_audit; local rc=$?
    if [[ $rc -eq 0 ]] && ! grep -q '\[FAIL\]' "$T/report.txt"; then echo " [PASS] self-test: baseline fixture (--cursor) is clean"
    else echo " [FAIL] self-test: baseline fixture should pass (rc=$rc)"; grep '\[FAIL\]' "$T/report.txt"; fails=$((fails+1)); fi
  }

  expect_pass_neutral() {
    build; local F="$T/f"; mkdir -p "$F/neutral"
    cp "$F/home/.cursor/rules/git-safety.md" "$F/neutral/rules.md"
    cp "$F/home/.cursor/skills/atools.md" "$F/neutral/ops.md"
    cp "$F/repo/.cursor/skills/atools-repair/SKILL.md" "$F/neutral/worker.md"
    rm -rf "$F/home/.cursor" "$F/repo/.cursor"
    run_audit --adapter none --rules "$F/neutral/rules.md" --operator-doc "$F/neutral/ops.md" --worker-doc "$F/neutral/worker.md"; local rc=$?
    if [[ $rc -eq 0 ]] && ! grep -q '\[FAIL\]' "$T/report.txt" && grep -q '\[SKIP\] ADP-01' "$T/report.txt"; then
      echo " [PASS] self-test: vendor-neutral run (--adapter none, no .cursor paths) is clean"
    else echo " [FAIL] self-test: vendor-neutral run should pass (rc=$rc)"; grep '\[FAIL\]' "$T/report.txt"; fails=$((fails+1)); fi
  }

  expect_usage_error() {
    bash "$SELF" >/dev/null 2>&1; local rc=$?
    if [[ $rc -eq 2 ]]; then echo " [PASS] self-test: no adapter chosen -> usage error (exit 2)"
    else echo " [FAIL] self-test: running without an adapter should exit 2 (rc=$rc)"; fails=$((fails+1)); fi
    bash "$SELF" --cursor --adapter none >/dev/null 2>&1; rc=$?
    if [[ $rc -eq 2 ]]; then echo " [PASS] self-test: --cursor with --adapter none -> usage error (exit 2)"
    else echo " [FAIL] self-test: conflicting adapter flags should exit 2 (rc=$rc)"; fails=$((fails+1)); fi
  }

  expect_fail() {
    local id="$1" desc="$2"; shift 2
    build; "$@"; run_audit; local rc=$?
    if [[ $rc -ne 0 ]] && grep -q "\[FAIL\] $id " "$T/report.txt"; then echo " [PASS] self-test: $desc -> $id fails"
    else echo " [FAIL] self-test: $desc did not trigger $id (rc=$rc)"; fails=$((fails+1)); fi
  }

  mut_no_n_deny() { python3 - "$T/f/home/.cursor/cli-config.json" <<'PY'
import json, sys
p = sys.argv[1]; c = json.load(open(p))
c["permissions"]["deny"].remove("Shell(git commit *-n)")
json.dump(c, open(p, "w"))
PY
  }
  mut_no_trust() { sed -i.bak 's/ --trust//' "$T/f/sys/arouter"; }
  mut_tmp_bypass() { printf '[[ "$(git rev-parse --show-toplevel)" =~ ^/tmp/ ]] && exit 0\n' >> "$T/f/home/.config/git/hooks/pre-commit"; }
  mut_proof_chmod() { echo 'chmod +x proof/*.sh' >> "$T/f/repo/.cursor/skills/atools-repair/SKILL.md"; }
  mut_recursion() { echo 'run abalanced for helpers' >> "$T/f/repo/.cursor/skills/atools-repair/SKILL.md"; }
  mut_wrapper() { printf '#!/usr/bin/env bash\necho nothing\n' > "$T/f/sys/acheap"; chmod +x "$T/f/sys/acheap"; }

  echo "--- self-test ---"
  expect_pass
  expect_pass_neutral
  expect_usage_error
  expect_fail ADP-PERM-08 "cli-config missing '-n' deny entry" mut_no_n_deny
  expect_fail ADP-FLAG-trust "arouter missing --trust" mut_no_trust
  expect_fail HOOK-05 "hook contains /tmp bypass" mut_tmp_bypass
  expect_fail SKILL-10 "worker doc chmods proof files" mut_proof_chmod
  expect_fail SKILL-05 "worker doc references an outer dispatcher" mut_recursion
  expect_fail INST-WRAPD-acheap "tier entry point does not delegate to arouter" mut_wrapper
  [[ $fails -eq 0 ]] && { echo "Self-test OK"; return 0; } || { echo "Self-test: $fails failure(s)"; return 1; }
}

if [[ $SELFTEST -eq 1 ]]; then selftest; exit $?; fi

# ---------------------------------------------------------------- core
AH="${ATOOLS_AUDIT_HOME:-$HOME}"
SYS_BIN="${ATOOLS_SYS_BIN:-/usr/local/bin}"
USER_BIN="${ATOOLS_USER_BIN:-$AH/.local/bin}"
PASS=0; FAIL=0; SKIP=0; WARN=0

# Runtime adapters supply default paths and runtime-specific checks. Core checks never name a vendor.
AD_BIN=""; AD_RULES=""; AD_OPS=""; AD_WORKER=""; AD_PERMS=""; AD_FLAGS=""
case "$ADAPTER" in
  cursor)
    AD_BIN="agent"; AD_RULES="$AH/.cursor/rules/git-safety.md"; AD_OPS="$AH/.cursor/skills/atools.md"
    AD_WORKER=".cursor/skills/atools-repair/SKILL.md"; AD_PERMS="$AH/.cursor/cli-config.json"
    AD_FLAGS="--auto-review --trust" ;;
  none) ;;
  *) echo "unknown adapter: $ADAPTER (use cursor or none)" >&2; exit 2 ;;
esac
RULES="${RULES_O:-$AD_RULES}"; OPS="${OPS_O:-$AD_OPS}"; WORKER_REL="${WORKER_O:-$AD_WORKER}"

if [[ -z "$REPO" ]] && git rev-parse --is-inside-work-tree >/dev/null 2>&1; then REPO="$(git rev-parse --show-toplevel)"; fi
[[ -n "$REPORT" ]] && : > "$REPORT"

emit() { printf '%s\n' "$*"; [[ -n "$REPORT" ]] && printf '%s\n' "$*" >> "$REPORT"; return 0; }
section() { emit ""; emit "--- $* ---"; }
ok()   { PASS=$((PASS+1)); emit " [PASS] $1 $2"; }
bad()  { FAIL=$((FAIL+1)); emit " [FAIL] $1 $2"; }
skip() { SKIP=$((SKIP+1)); emit " [SKIP] $1 $2 (reason: $3)"; }
warn() { WARN=$((WARN+1)); emit " [WARN] $1 $2"; }

check() { local id="$1" desc="$2"; shift 2; if "$@" >/dev/null 2>&1; then ok "$id" "$desc"; else bad "$id" "$desc"; fi; }
check_content() { local id="$1" desc="$2" file="$3" pat="$4"
  if [[ -f "$file" ]] && grep -Eiq -e "$pat" "$file" 2>/dev/null; then ok "$id" "$desc"; else bad "$id" "$desc"; fi; }
check_absent() { local id="$1" desc="$2" file="$3" pat="$4"
  if [[ ! -f "$file" ]]; then bad "$id" "$desc (file missing)"
  elif grep -Eiq -e "$pat" "$file" 2>/dev/null; then bad "$id" "$desc"; else ok "$id" "$desc"; fi; }

cfg_has() { # file, mode, entry
  python3 - "$1" "$2" "${3:-}" <<'PY'
import json, sys
path, mode, entry = sys.argv[1:4]
cfg = json.load(open(path, encoding="utf-8"))
perms = cfg.get("permissions", {})
if mode == "approval":
    sys.exit(0 if cfg.get("approvalMode") == "allowlist" else 1)
if mode == "deny":
    sys.exit(0 if entry in perms.get("deny", []) else 1)
if mode == "allow":
    sys.exit(0 if entry in perms.get("allow", []) else 1)
sys.exit(2)
PY
}

emit "========================================================"
emit " atools Compliance Audit   (profile: $PROFILE, adapter: $ADAPTER)"
emit " Specification: DESIGN.md, docs/"
emit "========================================================"

# ---------------------------------------------------------------- INST
section "INST  Suite installation (vendor-neutral)"
check INST-01 "arouter executable in user bin" test -x "$USER_BIN/arouter"
check INST-02 "asessions executable in user bin" test -x "$USER_BIN/asessions"
check INST-03 "'arouter --show' functional" arouter --show
for t in cheap balanced smart; do
  check "INST-TIER-$t" "Profile '$t' resolves to a model" bash -c '[[ -n "$(arouter --get '"$t"' 2>/dev/null)" ]]'
done
check INST-04 "arouter is a persistent executable (not a shell function)" test -x "$SYS_BIN/arouter"
check_content INST-05 "arouter resolves the model via arouter" "$SYS_BIN/arouter" 'arouter --get'
for t in acheap abalanced asmart; do
  check "INST-WRAP-$t" "Entry point $t is executable" test -x "$SYS_BIN/$t"
  check_content "INST-WRAPD-$t" "Entry point $t delegates to arouter" "$SYS_BIN/$t" 'exec .*arouter'
done

# ---------------------------------------------------------------- ADP
section "ADP  Runtime adapter: $ADAPTER"
if [[ -z "$AD_BIN" ]]; then
  skip ADP-01 "Runtime binary reachable" "adapter 'none'"
  skip ADP-02 "Runtime version responsive" "adapter 'none'"
  skip ADP-FLAGS "arouter applies the adapter's required flags" "adapter 'none'"
  skip ADP-PERM "Runtime permission configuration" "adapter 'none'"
else
  check ADP-01 "Runtime binary '$AD_BIN' reachable in PATH" which "$AD_BIN"
  check ADP-02 "Runtime '$AD_BIN' version responsive" "$AD_BIN" --version
  for f in $AD_FLAGS; do check_content "ADP-FLAG-${f#--}" "arouter applies $f" "$SYS_BIN/arouter" "$f"; done
  CFG="$AD_PERMS"
  check ADP-PERM-01 "Permission config exists" test -f "$CFG"
  check ADP-PERM-02 "approvalMode is allowlist" cfg_has "$CFG" approval
  check ADP-PERM-03 "Denies 'git push*'" cfg_has "$CFG" deny 'Shell(git push*)'
  check ADP-PERM-04 "Denies 'git push'" cfg_has "$CFG" deny 'Shell(git push)'
  check ADP-PERM-05 "Denies 'rm -rf /'" cfg_has "$CFG" deny 'Shell(rm -rf /)'
  check ADP-PERM-06 "Denies commit --no-verify" cfg_has "$CFG" deny 'Shell(git commit *--no-verify*)'
  check ADP-PERM-07 "Denies commit -n (with arguments)" cfg_has "$CFG" deny 'Shell(git commit *-n *)'
  check ADP-PERM-08 "Denies commit -n (bare)" cfg_has "$CFG" deny 'Shell(git commit *-n)'
  if cfg_has "$CFG" allow 'Shell(python3 -c *)'; then
    warn ADP-PERM-09 "Allowlist contains broad capability 'python3 -c *' (safe only with prod isolation and gate checks)"
  else ok ADP-PERM-09 "Allowlist has no 'python3 -c *' capability"; fi
fi

# ---------------------------------------------------------------- HARD
section "HARD  Agent rules (content is vendor-neutral; path from adapter or --rules)"
if [[ -z "$RULES" ]]; then
  for i in 01 02 03 04 05; do skip "HARD-$i" "Agent rules check" "no rules file (use --rules)"; done
else
  check HARD-01 "Agent rules file exists" test -f "$RULES"
  check_content HARD-02 "Rules require wip/ branches" "$RULES" 'wip/'
  check_content HARD-03 "Rules prohibit git push" "$RULES" 'git push'
  check_content HARD-04 "Rules require git status at exit" "$RULES" 'git status'
  check_content HARD-05 "Rules require (WI-<id>) commit tags" "$RULES" 'WI-'
fi

# ---------------------------------------------------------------- HOOK
section "HOOK  Git pre-commit boundary (git-level, vendor-neutral)"
HP="$(git config --global core.hooksPath 2>/dev/null || true)"; HOOK="$AH/.config/git/hooks/pre-commit"
check HOOK-01 "Global core.hooksPath points to ~/.config/git/hooks" bash -c '[[ "'"$HP"'" =~ \.config/git/hooks/?$ ]]'
check HOOK-02 "Global pre-commit hook executable" test -x "$HOOK"
check_content HOOK-03 "Hook enforces wip/ isolation" "$HOOK" 'wip/'
check_content HOOK-04 "Hook delegates to pre-commit.local" "$HOOK" 'pre-commit\.local'
check_absent HOOK-05 "Hook has no /tmp bypass" "$HOOK" '(\^|[ "])/(var/)?tmp'
if [[ -n "$REPO" && -d "$REPO/.git" && -f "$REPO/.git/hooks/pre-commit.local" ]]; then
  check HOOK-06 "Repo pre-commit.local is executable" test -x "$REPO/.git/hooks/pre-commit.local"
else skip HOOK-06 "Repo pre-commit.local executable" "no repo-local hook present"; fi

# ---------------------------------------------------------------- SKILL
section "SKILL  Operator and worker instructions (content is vendor-neutral)"
if [[ -z "$OPS" ]]; then
  for i in 01 02 03; do skip "SKILL-$i" "Operator instructions check" "no operator doc (use --operator-doc)"; done
else
  check SKILL-01 "Operator instructions present" test -f "$OPS"
  check_content SKILL-02 "Operator instructions reference asessions" "$OPS" 'asessions'
  check_content SKILL-03 "Operator instructions reference arouter" "$OPS" 'arouter'
fi
if [[ -n "$REPO" && -n "$WORKER_REL" ]]; then
  case "$WORKER_REL" in /*) WS="$WORKER_REL" ;; *) WS="$REPO/$WORKER_REL" ;; esac
  check SKILL-04 "Worker instructions present" test -f "$WS"
  check_absent SKILL-05 "Worker instructions exclude outer dispatchers (anti-recursion)" "$WS" '(arouter|acheap|abalanced|asmart|asessions|arun|amaster)'
  check_content SKILL-06 "Worker instructions forbid editing oracle/proofs" "$WS" 'NEVER[^.]*(edit|create|modify|mock)[^.]*(oracle|proof)'
  check_content SKILL-07 "Worker instructions require wip/ branch" "$WS" 'wip/'
  check_content SKILL-08 "Worker instructions require (WI-<id>) tags" "$WS" 'WI-'
  check_absent SKILL-09 "Worker instructions have no /tmp runbook contract" "$WS" 'Runbook_'
  check_absent SKILL-10 "Worker instructions do not chmod proof files" "$WS" 'chmod \+x proof'
else
  for i in 04 05 06 07 08 09 10; do skip "SKILL-$i" "Worker instructions check" "need a target repo and a worker doc (use --repo, --worker-doc)"; done
fi

# ---------------------------------------------------------------- PROF
section "PROF  Security profile ($PROFILE)"
if [[ "$PROFILE" == "dev" ]]; then
  warn PROF-00 "Development profile: same-user isolation; not the unattended trust boundary"
  skip PROF-01 "Hooks path root-owned, not group/world writable" "production profile only"
  for i in 02 03 04 05; do skip "PROF-$i" "Worker-identity isolation check" "production profile only"; done
else
  HD="${HP:-$AH/.config/git/hooks}"
  check PROF-01 "Hooks path owned by root" bash -c 'find "'"$HD"'" -maxdepth 0 -user root | grep -q .'
  check PROF-01b "Hooks path not group/world writable" bash -c '! find "'"$HD"'" -maxdepth 0 \( -perm -g+w -o -perm -o+w \) | grep -q .'
  if [[ -z "$WORKER_USER" || -z "$ORACLE_PATH" ]]; then
    for i in 02 03 04 05; do skip "PROF-$i" "Worker-identity isolation check" "need --worker-user and --oracle-path"; done
  elif ! sudo -n -u "$WORKER_USER" true >/dev/null 2>&1; then
    for i in 02 03 04 05; do skip "PROF-$i" "Worker-identity isolation check" "cannot sudo -n -u $WORKER_USER"; done
  else
    check PROF-02 "Worker cannot read the oracle" bash -c '! sudo -n -u "'"$WORKER_USER"'" test -r "'"$ORACLE_PATH"'"'
    check PROF-03 "Worker cannot write the oracle" bash -c '! sudo -n -u "'"$WORKER_USER"'" test -w "'"$ORACLE_PATH"'"'
    check PROF-04 "Worker environment has no credentials" bash -c '! sudo -n -u "'"$WORKER_USER"'" env | grep -Eq "(API_KEY|TOKEN|SECRET)="'
    check PROF-05 "Worker has no global git config" bash -c 'sudo -n -u "'"$WORKER_USER"'" sh -c '"'"'test ! -e "$HOME/.gitconfig"'"'"
  fi
fi

# ---------------------------------------------------------------- planned
section "ORC / SCP / EVD  Gate checks (planned)"
R="agate not implemented"
skip ORC-01 "Null implementation is red" "$R"
skip ORC-02 "Each re-injected defect is red" "$R"
skip ORC-03 "Reference commit is green" "$R"
skip ORC-04 "Oracle manifest hash matches pinned version tag" "$R"
skip ORC-05 "Oracle lints pass (including echo|grep -q self-test)" "$R"
skip ORC-06 "Repeated runs (3+) agree" "$R"
skip SCP-01 "BASE..HEAD paths match ALLOW and avoid FROZEN" "$R"
skip SCP-02 "Every commit has a registered (WI-<id>) tag; every item has a commit" "$R"
skip SCP-03 "Worktree is clean" "$R"
skip EVD-01 "Accepted ledger lines cite a report commit" "$R"
skip EVD-02 "sessions.tsv has a row per session" "$R"
skip EVD-03 "Leak scan finds no key patterns" "$R"

emit ""
emit "========================================================"
emit "Audit Verdict: $PASS passed, $FAIL failed, $SKIP skipped, $WARN warnings (profile=$PROFILE, adapter=$ADAPTER)"
emit "========================================================"

[[ $FAIL -gt 0 ]] && exit 1
[[ $STRICT -eq 1 && $SKIP -gt 0 ]] && exit 1
exit 0
