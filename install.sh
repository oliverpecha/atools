#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "=== Installing atools Framework ==="

# 1. Symlink local binaries
mkdir -p "$HOME/.local/bin"
ln -sf "$ROOT_DIR/bin/arouter" "$HOME/.local/bin/arouter"
chmod +x "$ROOT_DIR/bin/arouter" "$ROOT_DIR"/engines/*.sh "$ROOT_DIR"/proof/*.sh "$ROOT_DIR"/audit/*.sh

# 2. System Dispatchers in /usr/local/bin
SUDO=""
if [[ $(id -u) -ne 0 ]] && command -v sudo >/dev/null 2>&1; then
    SUDO="sudo"
fi

echo "Deploying system dispatchers to /usr/local/bin..."
$SUDO ln -sf "$ROOT_DIR/bin/arouter" /usr/local/bin/arouter
for tier in acheap abalanced asmart; do
    $SUDO tee "/usr/local/bin/$tier" >/dev/null <<EOF
#!/usr/bin/env bash
for arg in "\$@"; do
    if [[ "\$arg" == "--help" || "\$arg" == "-h" || "\$arg" == "help" ]]; then
        echo "CURSOR TIER WRAPPER: $tier"
        echo "======================================================================"
        echo "Default Tier : ${tier#a}"
        echo "Usage        : $tier [options] [\"prompt...\"]"
        echo ""
        echo "Examples:"
        echo "  $tier \"Explain this module\""
        echo "  $tier -d -n my-task -t 30m \"Run test suites and fix regressions\""
        echo "  git diff | $tier \"Review staged changes\""
        echo "======================================================================"
        echo ""
        exec /usr/local/bin/arouter --help
    fi
done
exec /usr/local/bin/arouter "${tier#a}" "\$@"
EOF
    $SUDO chmod +x "/usr/local/bin/$tier"
done

# 3. Synchronize Global Rules & Hooks
mkdir -p "$HOME/.cursor/rules" "$HOME/.config/git/hooks"
cp "$ROOT_DIR/rules/git-safety.md" "$HOME/.cursor/rules/git-safety.md"
cp "$ROOT_DIR/hooks/pre-commit" "$HOME/.config/git/hooks/pre-commit"
chmod +x "$HOME/.config/git/hooks/pre-commit"
cp "$ROOT_DIR/hooks/commit-msg" "$HOME/.config/git/hooks/commit-msg"
chmod +x "$HOME/.config/git/hooks/commit-msg"
git config --global core.hooksPath "$HOME/.config/git/hooks"

# 4. Synchronize In-Repo Worker Skill to global Cursor store
mkdir -p "$HOME/.cursor/skills/atools-repair"
cp "$ROOT_DIR/.cursor/skills/atools-repair/SKILL.md" "$HOME/.cursor/skills/atools-repair/SKILL.md"

# 5. Non-destructively merge permissions into ~/.cursor/cli-config.json
python3 - <<'PY_INNER'
import json, os
path = os.path.expanduser("~/.cursor/cli-config.json")
os.makedirs(os.path.dirname(path), exist_ok=True)
try:
    with open(path, "r", encoding="utf-8") as f: cfg = json.load(f)
except Exception: cfg = {"version": 1}

cfg["approvalMode"] = "allowlist"
perms = cfg.setdefault("permissions", {})

allow_rules = [
    "Shell(ls)", "Shell(ls *)", "Shell(dir)", "Shell(cat *)", "Shell(head *)", "Shell(tail *)",
    "Shell(grep *)", "Shell(find *)", "Shell(wc *)", "Shell(diff *)", "Shell(sha256sum *)",
    "Shell(git status)", "Shell(git status *)", "Shell(git diff)", "Shell(git diff *)",
    "Shell(git log)", "Shell(git log *)", "Shell(git show)", "Shell(git show *)",
    "Shell(git rev-parse *)", "Shell(git branch)", "Shell(git branch *)",
    "Shell(git checkout *)", "Shell(git checkout -b *)", "Shell(git switch *)", "Shell(git switch -c *)",
    "Shell(git add *)", "Shell(git commit -m *)",
    "Shell(mkdir -p *)", "Shell(chmod +x proof/*.sh)",
    "Shell(python3 -m compileall *)", "Shell(python3 -m py_compile *)", "Shell(python3 -c *)",
    "Shell(pytest)", "Shell(pytest *)",
    "Shell(bash proof/*.sh)", "Shell(bash proof/run_suite_*.sh)"
]
deny_rules = [
    "Shell(rm -rf /)", "Shell(rm -rf /*)", "Shell(rm -rf ~*)",
    "Shell(git push*)", "Shell(git push)", "Shell(git clean -fdx)",
    "Shell(reboot)", "Shell(shutdown*)", "Shell(init 0)",
    "Shell(mkfs*)", "Shell(dd if=*)", "Shell(iptables*)", "Shell(ufw*)",
    "Shell(passwd*)", "Shell(visudo*)",
    "Shell(git commit *--no-verify*)", "Shell(git commit *-n *)", "Shell(git commit *-n)"
]

perms["allow"] = sorted(list(set(perms.get("allow", []) + allow_rules)))
perms["deny"] = sorted(list(set(perms.get("deny", []) + deny_rules)))

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)
print("✅ Permissive rules merged into ~/.cursor/cli-config.json")
PY_INNER

echo ""
echo "=== Installation complete. Running verification suite ==="
bash "$ROOT_DIR/proof/run_suite_engines.sh"
