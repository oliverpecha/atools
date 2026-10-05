# Install

Sections 1 to 6 are vendor-neutral. Everything specific to one agent runtime lives under **Adapters** (section 7). Commands are carried over from the existing eval-repair guide as a starting point; verify paths, model names and flags on your host. `amaster` and `agate` are planned and have no install steps yet.

## 1. Prerequisites

- Linux or macOS with `git`, `bash`, `python3`, and GNU or compatible `timeout`.
- `~/.local/bin` on `PATH`.
- One runtime adapter from section 7.

## 2. Router and telemetry

```bash
chmod +x ~/.local/bin/agent-router-cursor.py
ln -sf ~/.local/bin/agent-router-cursor.py ~/.local/bin/arouter
ln -sf ~/.local/bin/agent-sessions.py ~/.local/bin/asessions
```

The script names above are the current Cursor-oriented implementations; the command names `arouter` and `asessions` are the stable interface. Map profiles with the CLI rather than editing the config file:

```bash
arouter --set cheap    <model-low>
arouter --set balanced <model-medium>
arouter --set smart    <model-high>
arouter --show
```

`arouter` has no hardcoded defaults; operators choose the models. Profiles are capability tiers, not roles.

## 3. The `arun` contract and tier entry points

`arun` must be a persistent executable on `PATH` (for example `/usr/local/bin/arun`), not a shell function, because exported shell functions do not survive the non-interactive subshells that `timeout` starts. Regardless of runtime, it must:

1. Resolve the model through `arouter --get <profile>`.
2. Apply the runtime-specific invocation flags (defined by the adapter).
3. Append piped stdin as context.
4. Run one fresh, bounded session and never decide acceptance.

Tier entry points are thin delegates and stay vendor-neutral:

```bash
for tier in acheap abalanced asmart; do
cat <<EOF > /usr/local/bin/${tier}
#!/usr/bin/env bash
exec /usr/local/bin/arun "${tier#a}" "\$@"
EOF
chmod +x /usr/local/bin/${tier}
done
```

The body of `arun` is adapter-specific; see section 7.

## 4. Worker instructions

Every runtime needs a worker instruction file in the target repository. The content is the same for all adapters; only its location differs (section 7).

```markdown
# Worker: Implementation

## Objective
Implement the task in the implementation brief, inside the allowed scope, without user intervention.

## Protocol
1. Read the implementation brief.
2. Edit only paths allowed by the scope in the brief.
3. NEVER edit, create or mock oracle files, proofs or test fixtures.
4. Run the oracle command given in the brief.
5. If it fails, read only the failing lines and apply minimal fixes; re-run.
6. If a check looks wrong, paste only the failing line and stop. Do not work around it.
7. Commit progress on a wip/* branch with a (WI-<id>) tag in the message.
8. When the oracle exits 0, ensure the worktree is clean, run `git status`, and conclude.
```

The worker file must not mention outer dispatchers (`arouter`, tier entry points, `asessions`, `arun`, `amaster`), so a worker cannot launch further workers. Operator guidance (`asessions`, `arouter --show`) belongs in a separate operator file.

## 5. Host hardening

### 5.1 Agent rules

Install a machine-wide rules file in the location your adapter reads (section 7). Required content:

```markdown
# Global Agent Operating Guidelines
1. Never commit to main, master or release branches. Verify `git branch --show-current` starts with `wip/` before committing.
2. All experiments and patches occur on an isolated `wip/*` branch.
3. Never run `git push` or modify remote refs.
4. Commit progress with a (WI-<id>) tag. Conclude every run with `git status`.
```

### 5.2 Dual pre-commit hook

```bash
mkdir -p ~/.config/git/hooks
cat <<'EOF' > ~/.config/git/hooks/pre-commit
#!/usr/bin/env bash
set -e
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || true)
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" || ! "$CURRENT_BRANCH" =~ ^wip/ ]]; then
  echo "[BLOCKED] Commits to '$CURRENT_BRANCH' are prohibited. Use a wip/* branch."
  exit 1
fi
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || true)
if [[ -n "$GIT_DIR" && -x "$GIT_DIR/hooks/pre-commit.local" ]]; then
  "$GIT_DIR/hooks/pre-commit.local" "$@"
fi
EOF
chmod +x ~/.config/git/hooks/pre-commit
git config --global core.hooksPath ~/.config/git/hooks
```

The previous version skipped repositories under `/tmp` and `/var/tmp`. That bypass is removed: nothing runs from `/tmp` under this design, and a bypass would exempt any repository placed there.

## 6. Profiles

**Development profile.** Single user. Use a separate git worktree per run, blank credentials for offline proofs, and rely on gate checks after each session. Same-user isolation is not the unattended trust boundary.

**Production profile.** Separate OS users:

| User | Access |
|---|---|
| `owner` | Private `agate` state, credentials, live gate |
| `atools-runner` (optional) | Read-only oracle interface; runs offline proofs with keys blanked |
| `atools-worker` | Its own implementation worktree only; no credentials, no oracle source, no global git config |

Place the hooks path in a root-owned location, set per-user resource and network limits, and verify with `docs/audits` using `--profile prod`.

## 7. Adapters

An adapter binds the vendor-neutral suite to one agent runtime. Choose exactly one per host for the audit (`--cursor` or `--adapter none`; there is no default).

### 7.1 Adapter: Cursor

**Install the CLI**

```bash
curl https://cursor.com/install.sh | bash
which agent || export PATH="$HOME/.local/bin:$PATH"
agent --version
```

**`arun` for Cursor.** Required flags: `--auto-review` and `--trust`.

```bash
cat <<'EOF' > /usr/local/bin/arun
#!/usr/bin/env bash
set -euo pipefail
TIER="${1:-balanced}"; shift || true
MODEL=$(arouter --get "$TIER" 2>/dev/null || echo "auto")
PIPED_INPUT=""
if [[ ! -t 0 ]]; then PIPED_INPUT=$(cat); fi
if [[ -n "$PIPED_INPUT" ]]; then
  exec agent --auto-review --trust --model "$MODEL" "$*

Context / Input:
$PIPED_INPUT"
else
  exec agent --auto-review --trust --model "$MODEL" "$@"
fi
EOF
chmod +x /usr/local/bin/arun
```

**File locations**

| Item | Path |
|---|---|
| Agent rules (section 5.1) | `~/.cursor/rules/git-safety.md` |
| Permission config | `~/.cursor/cli-config.json` |
| Operator instructions | `~/.cursor/skills/atools.md` |
| Worker instructions (section 4) | `<repo>/.cursor/skills/atools-repair/SKILL.md` |

**Permission config.** Use three layers: an allowlist of read and test commands, a hard denylist, and the `--auto-review` classifier for the rest. Set `approvalMode` to `allowlist`. The denylist must contain at least these exact entries, which the audit checks:

```text
Shell(git push*)
Shell(git push)
Shell(rm -rf /)
Shell(git commit *--no-verify*)
Shell(git commit *-n *)
Shell(git commit *-n)
```

Avoid broad allowlist entries such as `Shell(python3 -c *)`. They are capabilities, not conveniences: the audit warns on them, and they are only acceptable with production isolation and gate checks. The full allowlist synchronization script is in `history/atools-eval_repair_guide.md`.

**Audit**

```bash
docs/audits/atools-compliance_audit.sh --cursor
docs/audits/atools-compliance_audit.sh --cursor --profile prod --worker-user <user> --oracle-path <dir>
```

### 7.2 Adding another adapter

An adapter must provide:

1. The runtime binary and how to check its version.
2. The flags `arun` must apply for non-interactive, bounded operation.
3. Locations for agent rules, operator instructions and worker instructions.
4. Its permission or approval mechanism and the deny rules equivalent to those above.
5. How `asessions` reads its session logs.
6. Its environment policy support (keys blanked for offline runs).

Then add the adapter case and `ADP` checks to `atools-compliance_audit.sh`, and list them in `audits/README.md`. Until that is done, run the audit with `--adapter none` and pass `--rules`, `--operator-doc` and `--worker-doc`.

## 8. Planned components

`amaster` and `agate` install steps will be added when those components exist. Until then, follow `operations.md` manually using the `agate` layout in `architecture.md`.
