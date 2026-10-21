#!/usr/bin/env bash
# proof/run_suite_commit_msg.sh - Verification suite for mechanical commit enforcement (WI-RULES-1)
set -uo pipefail

REPO_DIR="${REPO_DIR:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
OUT_DIR="$REPO_DIR/proof/out"
mkdir -p "$OUT_DIR"
PASS=0; FAIL=0

HOOK="$REPO_DIR/hooks/commit-msg"

check() {
  local n="$1"; shift
  if "$@" > "$OUT_DIR/$n.log" 2>&1; then
    echo "Running $n... [PASS]"
    PASS=$((PASS+1))
  else
    echo "Running $n... [FAIL] (see $OUT_DIR/$n.log)"
    sed -n '1,5p' "$OUT_DIR/$n.log" | sed 's/^/    /'
    FAIL=$((FAIL+1))
  fi
}

# Gate 1: Artifact existence and executable bit
check_hook_exists() { [[ -f "$HOOK" && -x "$HOOK" ]]; }
check "T1_hook_executable" check_hook_exists

# Gate 2: Hook catches malformed header syntax (E_HEADER)
check_bad_header() {
  local f=$(mktemp) rc=0
  printf "bad: header\n\nWhy:\nValid context.\n\nWhat changed:\n- file.py: change\n\nResult:\n1 passed, 0 failed.\n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_HEADER"
}
check "T2_reject_bad_header" check_bad_header

# Gate 3: Hook catches synonym types and suggests canonical root (E_SYNONYM)
check_synonym_type() {
  local f=$(mktemp) rc=0
  printf "performance(router): speed up polling (WI-RULES-1)\n\nWhy:\nValid context.\n\nWhat changed:\n- file.py: change\n\nResult:\n1 passed, 0 failed.\n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_SYNONYM.*perf"
}
check "T3_reject_synonym_type" check_synonym_type

# Gate 4: Hook rejects stage/version pseudonyms in scope (E_SCOPE)
check_stage_scope() {
  local f=$(mktemp) rc=0
  printf "chore(s0): pin baseline fixtures (WI-RULES-1)\n\nWhy:\nValid context.\n\nWhat changed:\n- file.py: change\n\nResult:\n1 passed, 0 failed.\n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_SCOPE"
}
check "T4_reject_stage_scope" check_stage_scope

# Gate 5: Hook rejects lazy verbs in summary (E_LAZY_VERB)
check_lazy_verb() {
  local f=$(mktemp) rc=0
  printf "feat(actl): update the configuration parser (WI-RULES-1)\n\nWhy:\nValid context.\n\nWhat changed:\n- file.py: change\n\nResult:\n1 passed, 0 failed.\n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_LAZY_VERB"
}
check "T5_reject_lazy_verb" check_lazy_verb

# Gate 6: Hook rejects missing or empty sections (E_SECTION_RESULT)
check_missing_section() {
  local f=$(mktemp) rc=0
  printf "feat(router): isolate flag parsing (WI-RULES-1)\n\nWhy:\nValid context.\n\nWhat changed:\n- file.py: change\n\nResult:\n# only a comment\n   \n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_SECTION_RESULT"
}
check "T6_reject_missing_or_empty_section" check_missing_section

# Gate 7: Hook rejects 'What changed:' lacking bullet points (E_BULLETS)
check_bullets() {
  local f=$(mktemp) rc=0
  printf "feat(router): isolate flag parsing (WI-RULES-1)\n\nWhy:\nValid context.\n\nWhat changed:\nNo bullets here\n\nResult:\n1 passed, 0 failed.\n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_BULLETS"
}
check "T7_reject_missing_bullets" check_bullets

# Gate 8: Hook rejects non-bare SHA references in Why: (E_BARE_SHA)
check_bare_sha() {
  local f=$(mktemp) rc=0
  printf "fix(router): guard auto tier (WI-RULES-1)\n\nWhy:\nRegression introduced in commit 85523a0 during refactor.\n\nWhat changed:\n- bin/arouter: guard prefix.\n\nResult:\n6 passed, 0 failed.\n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_BARE_SHA"
}
check "T8_reject_non_bare_sha" check_bare_sha

# Gate 9: Multi-error accumulation in a single pass
check_multi_error() {
  local f=$(mktemp)
  printf "bad_header\n\nWhy:\nValid context.\n" > "$f"
  local out=$("$HOOK" "$f" 2>&1 || true)
  rm -f "$f"
  echo "$out" | grep -q "E_HEADER" && echo "$out" | grep -q "E_SECTION_WHAT" && echo "$out" | grep -q "E_SECTION_RESULT"
}
check "T9_multi_error_accumulation" check_multi_error

# Gate 10: Clean pass on fully conforming commit message
check_valid_commit() {
  local f=$(mktemp)
  cat << 'MSG' > "$f"
feat(router): isolate prompt tiers from flag parsing (WI-TOOLS-2)

Why: Fixes positional argument truncation on 2acaf3c.

What changed:
- src/router/cli.py: Guard positional arguments.

Result: 11 passed, 0 failed in engine proof suite.
MSG
  "$HOOK" "$f" >/dev/null 2>&1
  local res=$?
  rm -f "$f"
  return $res
}
check "T10_accept_valid_message" check_valid_commit

# Gate 11: Merge and Revert exemption on line 1
check_merge_exemption() {
  local f=$(mktemp)
  printf "Merge branch 'wip/s0b-exit-code' into wip/stage0-integration\n" > "$f"
  "$HOOK" "$f" >/dev/null 2>&1 || { rm -f "$f"; return 1; }
  printf 'Revert "feat(router): isolate prompt tiers (WI-TOOLS-2)"\n' > "$f"
  "$HOOK" "$f" >/dev/null 2>&1 || { rm -f "$f"; return 1; }
  rm -f "$f"
  return 0
}
check "T11_exempt_merge_and_revert" check_merge_exemption

# Gate 12: Installation script syncs commit-msg hook and audit passes
check_install_and_audit() {
  grep -q 'cp "$ROOT_DIR/hooks/commit-msg" "$HOME/.config/git/hooks/commit-msg"' "$REPO_DIR/install.sh" || return 1
  diff -q "$REPO_DIR/hooks/commit-msg" "$HOME/.config/git/hooks/commit-msg" >/dev/null 2>&1 || return 1
  bash "$REPO_DIR/audit/atools-compliance_audit.sh" --cursor >/dev/null 2>&1
}
check "T12_install_sync_and_audit_clean" check_install_and_audit

# Gate 13: Safety rules and worker skill enforce no-verify and worktree isolation
check_governance_texts() {
  grep -q '\--no-verify' "$REPO_DIR/rules/git-safety.md" || return 1
  grep -q '\--no-verify' "$REPO_DIR/.cursor/skills/atools-repair/SKILL.md" || return 1
  grep -q 'worktree' "$REPO_DIR/.cursor/skills/atools-repair/SKILL.md" || return 1
}
check "T13_governance_contracts_present" check_governance_texts

# Gate 14: Hook rejects 'fix' commits missing a prior commit SHA in Why: (E_FIX_NO_SHA)
check_fix_without_sha() {
  local f=$(mktemp) rc=0
  printf "fix(router): guard auto tier (WI-RULES-1)\n\nWhy:\nRegression fixed but omitted prior sha.\n\nWhat changed:\n- bin/arouter: guard prefix.\n\nResult:\n6 passed, 0 failed.\n" > "$f"
  local out; out=$("$HOOK" "$f" 2>&1) || rc=$?
  rm -f "$f"
  [[ $rc -ne 0 ]] && echo "$out" | grep -q "E_FIX_NO_SHA"
}
check "T14_reject_fix_without_sha" check_fix_without_sha

# Gate 15: Hook accepts 'feat' commit without prior SHA
check_feat_without_sha() {
  local f=$(mktemp)
  cat << 'MSG' > "$f"
feat(router): add new telemetry filter option (WI-TOOLS-2)

Why: Introduces optional log verbosity flag requested by operator.

What changed:
- src/router/cli.py: Add --verbose flag.

Result: 11 passed, 0 failed in engine proof suite.
MSG
  "$HOOK" "$f" >/dev/null 2>&1
  local res=$?
  rm -f "$f"
  return $res
}
check "T15_accept_feat_without_sha" check_feat_without_sha

# Gate 16: Hook accepts 'fix' commit with prior SHA in Why:
check_fix_with_sha() {
  local f=$(mktemp)
  cat << 'MSG' > "$f"
fix(router): isolate prompt tiers from flag parsing (WI-TOOLS-2)

Why: Fixes argument truncation introduced in 2acaf3c.

What changed:
- src/router/cli.py: Guard positional arguments.

Result: 11 passed, 0 failed in engine proof suite.
MSG
  "$HOOK" "$f" >/dev/null 2>&1
  local res=$?
  rm -f "$f"
  return $res
}
check "T16_accept_fix_with_sha" check_fix_with_sha

echo "--- Suite Results: $PASS passed, $FAIL failed ---"
[[ $FAIL -eq 0 ]]
