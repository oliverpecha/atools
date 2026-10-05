#!/usr/bin/env bash
set -uo pipefail

echo "========================================================"
echo "    atools Architecture & Compliance Audit"
echo "    Specification: atools-evals_repair_guide.md"
echo "========================================================"
PASS=0; FAIL=0

check() {
  local desc="$1"; shift
  if "$@" >/dev/null 2>&1; then
    echo "  [PASS] $desc"; ((PASS++))
  else
    echo "  [FAIL] $desc"; ((FAIL++))
  fi
}

check_content() {
  local desc="$1"; local file="$2"; local pattern="$3"
  if [[ -f "$file" ]] && grep -Eq -e "$pattern" "$file" 2>/dev/null; then
    echo "  [PASS] $desc"; ((PASS++))
  else
    echo "  [FAIL] $desc"; ((FAIL++))
  fi
}

# 1. Agent Runtime CLI
echo ""
echo "--- 1. Agent Runtime CLI ---"
check "Binary 'agent' reachable in PATH" which agent
check "Agent CLI version responsive" agent --version

# 2. Router Scripts, Symlinks & Operations
echo ""
echo "--- 2. Router Configuration, Tiers & Auditing ---"
check "Script ~/.local/bin/arouter executable" test -x "$HOME/.local/bin/arouter"
check "CLI command 'arouter --show' functional" arouter --show
check "Tier 'cheap' query returns model" bash -c '[[ -n "$(arouter --get cheap 2>/dev/null)" ]]'
check "Tier 'balanced' query returns model" bash -c '[[ -n "$(arouter --get balanced 2>/dev/null)" ]]'
check "Tier 'smart' query returns model" bash -c '[[ -n "$(arouter --get smart 2>/dev/null)" ]]'
check "Session audit tool ~/.local/bin/asessions executable" test -x "$HOME/.local/bin/asessions"
check "Session audit CLI 'asessions' reachable in PATH" which asessions

# 3. System Dispatchers & Tier Entrypoints
echo ""
echo "--- 3. System Dispatchers & Execution Mechanics ---"
check "Dispatcher /usr/local/bin/arouter executable" test -x /usr/local/bin/arouter
check_content "Dispatcher enforces '--auto-review'" /usr/local/bin/arouter "--auto-review"
check_content "Dispatcher enforces '--trust'" /usr/local/bin/arouter "--trust"
for tier in acheap abalanced asmart; do
  check "Tier entrypoint /usr/local/bin/$tier executable" test -x "/usr/local/bin/$tier"
  check_content "Tier wrapper $tier delegates to arouter" "/usr/local/bin/$tier" "exec.*arouter"
done

# 4. Global Prompt & Permission Guardrails
echo ""
echo "--- 4. Machine-Wide Safety Guardrails & Permissions ---"
check "Global prompt rules (~/.cursor/rules/git-safety.md)" test -f "$HOME/.cursor/rules/git-safety.md"
check_content "Git safety prompt enforces 'wip/' branches" "$HOME/.cursor/rules/git-safety.md" "wip/"
check_content "Git safety prompt prohibits 'git push'" "$HOME/.cursor/rules/git-safety.md" "git push"
check_content "Git safety prompt mandates assertion-gated 'git status'" "$HOME/.cursor/rules/git-safety.md" "git status"
check "CLI config exists (~/.cursor/cli-config.json)" test -f "$HOME/.cursor/cli-config.json"
check "cli-config.json enforces allowlist mode and blocks dangerous bypasses" python3 -c '
import json, os
path = os.path.expanduser("~/.cursor/cli-config.json")
with open(path, "r", encoding="utf-8") as f:
    cfg = json.load(f)
assert cfg.get("approvalMode") == "allowlist", "approvalMode is not allowlist"
perms = cfg.get("permissions", {})
denies = perms.get("deny", [])
allows = perms.get("allow", [])
assert any("--no-verify" in d for d in denies), "Missing --no-verify hook bypass block"
assert any("-n" in d for d in denies), "Missing -n commit bypass block"
assert any("git push" in d for d in denies), "Missing git push denylist rule"
assert any("rm -rf" in d for d in denies), "Missing rm -rf denylist rule"
assert any("proof" in a for a in allows), "Missing proof execution tools in allowlist"
'

# 5. Dual Pre-Commit Hook Architecture
echo ""
echo "--- 5. Git Pre-Commit Hook Boundary ---"
check "Global Git core.hooksPath set to ~/.config/git/hooks" bash -c '[[ "$(git config --global core.hooksPath)" =~ \.config/git/hooks$ ]]'
check "Global pre-commit dispatcher executable" test -x "$HOME/.config/git/hooks/pre-commit"
check_content "Global hook enforces wip branch isolation" "$HOME/.config/git/hooks/pre-commit" "wip/"
check_content "Global hook delegates to local pre-commit.local" "$HOME/.config/git/hooks/pre-commit" "pre-commit\.local"

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  GIT_DIR=$(git rev-parse --git-dir)
  if [[ -f "$GIT_DIR/hooks/pre-commit.local" ]]; then
    check "Repo local pre-commit hook is executable" test -x "$GIT_DIR/hooks/pre-commit.local"
  fi
else
  echo "  [INFO] Not inside a Git repository; skipped repo-level hook checks."
fi

# 6. Decoupled Skill Architecture (Operator vs Worker)
echo ""
echo "--- 6. Decoupled Skill Architecture & Anti-Recursion ---"
check "Global Operator Skill present (~/.cursor/skills/atools.md)" test -f "$HOME/.cursor/skills/atools.md"
check_content "Operator skill references 'asessions'" "$HOME/.cursor/skills/atools.md" "asessions"
check_content "Operator skill references 'arouter'" "$HOME/.cursor/skills/atools.md" "arouter"
check "Global Worker Skill present (~/.cursor/skills/atools-repair/SKILL.md)" test -f "$HOME/.cursor/skills/atools-repair/SKILL.md"
check_content "Worker skill references 'Runbook_'" "$HOME/.cursor/skills/atools-repair/SKILL.md" "Runbook_"
check "Global Worker Skill excludes outer dispatchers (anti-recursion)" bash -c '! grep -Eq "(arouter|acheap|abalanced|asmart|asessions)" "$HOME/.cursor/skills/atools-repair/SKILL.md" 2>/dev/null'

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  REPO_ROOT=$(git rev-parse --show-toplevel)
  check "Repo Worker Skill present (.cursor/skills/atools-repair/SKILL.md)" test -f "$REPO_ROOT/.cursor/skills/atools-repair/SKILL.md"
  if [[ -f "$REPO_ROOT/.cursor/skills/atools-repair/SKILL.md" ]]; then
    check "Repo Worker Skill excludes outer dispatchers (anti-recursion)" bash -c '! grep -Eq "(arouter|acheap|abalanced|asmart|asessions)" "'"$REPO_ROOT"'/.cursor/skills/atools-repair/SKILL.md" 2>/dev/null'
  fi
else
  echo "  [INFO] Not inside a Git repository; skipped repo-level skill checks."
fi

echo ""
echo "========================================================"
echo "Audit Verdict: $PASS Passed, $FAIL Failed"
echo "========================================================"

if [[ $FAIL -gt 0 ]]; then
  exit 1
fi
