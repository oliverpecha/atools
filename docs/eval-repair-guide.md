# Engineering Guide: Eval-Driven Repair Loops, Autonomous Patching & Safety Architecture with `atools`

* **Objective:** Provide a repeatable, production-grade guide for installing the `atools` suite, configuring tiered model routing via CLI, hardening execution permissions, and establishing deterministic pre-commit branch boundaries.

---

## 1. Overview & Operational Tenets

Manual patch application via web chat interfaces is error-prone, hallucination-heavy, and unmetered. This infrastructure automates code repairs using three coupled components:

1. **Orchestrator (`atools` suite):** A lightweight CLI toolkit (`arouter`, `asessions`, `arun`, and tier entrypoints `acheap`, `abalanced`, `asmart`) managing model routing, token economics, session auditing, and unattended execution.
2. **Agent Runtime (Cursor Agent CLI):** Headless agent running directly against local repository files and system binaries under strict OS-level supervision.
3. **Deterministic Objective Function (Proof Suite):** Standalone bash test harnesses (`proof/run_suite_<title>.sh`) returning binary exit codes (`0` = PASS, `1` = FAIL) that serve as the agent's sole termination criteria.

### The Four Operational Tenets

1. **Decoupled Model Tiering:** Model selection (`cheap`, `balanced`, `smart`) must remain independent of prompt templates and scripts. Operators map semantic tiers to concrete models via CLI configuration based on speed, cost, and context requirements.
2. **Deterministic Exit Codes as Objective Functions:** Natural language instructions like *"make sure it works"* invite hallucinated completion. The agent's only valid completion signal is `Exit 0` from an unmocked shell script.
3. **Executable Runbook Grounding:** Ambiguous task descriptions lead to model wandering and token exhaustion. Supplying pre-verified code structures and unambiguous assertions in `/tmp/Runbook_<title>.md` focuses model attention strictly on file integration and boundary repairs.
4. **Hard Blast-Radius Envelopes:** No prompt instruction can replace filesystem and OS boundaries. Designating explicit component directories (e.g., `backend/`, `frontend/`) as strictly immutable, enforcing isolated working trees, setting hard wall-clock process timeouts (`timeout -k`), restricting tool permissions, and maintaining pre-commit branch guards ensures that agent errors remain strictly localized and non-destructive.

### Taxonomy of Loop-Driven Workflows

Teams frequently conflate "TDD" with autonomous agent loops. In automated code repair, these concepts form four nested concentric layers:

```
┌──────────────────────────────────────────────────────────┐
│ Eval-Driven Repair (Outermost System)                    │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │ Red-Green Harness (Test Infrastructure)            │  │
│  │                                                    │  │
│  │   ┌──────────────────────────────────────────────┐ │  │
│  │   │ Test-Driven Red-Green (Testing Methodology)  │ │  │
│  │   │                                              │ │  │
│  │   │   ┌────────────────────────────────────────┐ │ │  │
│  │   │   │ Assertion-Gated (Innermost Core)       │ │ │  │
│  │   │   └────────────────────────────────────────┘ │ │  │
│  │   └──────────────────────────────────────────────┘ │  │  
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘

```

| Workflow Concept | Specific Engineering Role |
| --- | --- |
| **Assertion-Gated** | The underlying validation primitive: discrete assertions returning Boolean `True` or process Exit `0` that strictly gate progression and prevent false-positive completion. |
| **Test-Driven Red-Green** | The operational methodology: proving that assertions reliably fail against the baseline (**Red**) before verifying they pass against the modified codebase (**Green**). |
| **Red-Green Harness** | The tooling infrastructure (`proof/run_suite_<title>.sh`, `verify_fails_on_base.sh`) that sets up temporary execution environments, runs suites, captures timestamped error logs in `proof/out/`, and reports verdicts. |
| **Eval-Driven Repair** | The complete autonomous feedback loop: the agent parses runtime failures, inspects diffs, reasons through error logs, patches code, and re-executes tests iteratively until zero defects remain. |

---

## 2. Architecture & Runtime Mechanics

### A. Security Boundaries & Process Supervison

```
                     ┌──────────────────────────────────────────────┐
                     │          Global Agent System Prompt          │
                     │         (~/.cursor/rules/git-safety.md)      │
                     └──────────────────────┬───────────────────────┘
                                            │
                                            ▼
┌──────────────────────┐      ┌───────────────────────────┐      ┌────────────────────────────────┐
│      atools Tier     │ ───► │   Dispatcher (/usr/local/ │ ───► │     Tool Permission Engine     │
│ (acheap / abalanced /│      │         bin/arun)         │      │  (~/.cursor/cli-config.json)   │
│        asmart)       │      │ (--auto-review + --trust) │      │  [Allow / Deny / Classifier]   │
└──────────────────────┘      └───────────────────────────┘      └──────────────┬─────────────────┘
                                                                                │
                                                                                ▼
┌────────────────────────────────────────────────────────┐       ┌────────────────────────────────┐
│                Git Pre-Commit Boundary                 │ ◄──── │     OS Process Supervisor      │
│  Global Hook (~/.config/git/hooks/pre-commit)          │       │   (timeout -k 15s <duration>)  │
│  Local Hook Delegation (.git/hooks/pre-commit.local)   │       └────────────────────────────────┘
└────────────────────────────────────────────────────────┘

```

### B. The Runtime Feedback Cycle

```
┌────────────────────────────────────────────────────────────────────────┐
│                        DEVELOPER WORKSPACE                             │
│  Runbook Specification (/tmp/Runbook_<title>.md)  +  Proof Suite (proof/run_suite_<title>.sh) │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                       ORCHESTRATION LAYER (atools)                     │
│  arouter CLI  ──►  agent-router-cursor.py  ──►  _dispatch_agent / arun │
│    (cheap)                   (balanced)                       (smart)  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      HEADLESS AGENT EXECUTION (Cursor)                 │
│   Tool Allowlist + --auto-review Classifier + Watchdog (timeout -k)    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      EVAL-DRIVEN VERIFICATION LOOP                     │
│   [Write Code] ──► [Run proof/run_suite_<title>.sh] ──► [Parse Log] ──► [Patch]  │
│                            ▲                       │                   │
│                            └─────── Exit 0 ────────┘                   │
└────────────────────────────────────────────────────────────────────────┘

```

The feedback cycle progresses deterministically across five stages:

1. **Extraction & Seeding:** The agent parses the runbook specification (`/tmp/Runbook_<title>.md`), extracting target implementation files and corresponding test scripts.
2. **First-Pass Execution:** The agent validates syntax (e.g., via `python3 -m compileall`) and triggers `bash proof/run_suite_<title>.sh`.
3. **Log Ingestion & Diagnosis:** If an assertion returns non-zero, the harness writes stdout/stderr to `proof/out/<test>.log`. The agent inspects only the failing log file, conserving context window tokens.
4. **Surgical Patching:** The agent modifies only the necessary lines within the designated files, avoiding full file regeneration.
5. **Clean Termination:** When all test scripts exit `0`, the agent runs `git status` and concludes execution.

---

## 3. Component Installation & Environment Setup

### A. Cursor Agent CLI Installation

Install the agent CLI and verify system path availability:

```bash
# Install Cursor Agent CLI
curl https://cursor.com/install.sh | bash

# Ensure binary is in PATH and verify installation
which agent || export PATH="$HOME/.local/bin:$PATH"
agent --version

```

### B. `atools` Suite Installation & Tool Overview

The `atools` suite consists of Python management scripts and bash wrappers deployed to `~/.local/bin` and `/usr/local/bin`:

* **`arouter`:** Manages model routing across three tier identifiers:
* `cheap`: Routine refactoring, lint fixes, single-line adjustments.
* `balanced`: Primary autonomous driver for multi-file repairs and test debugging.
* `smart`: Complex or ambiguous architectural modifications.
*(Note: `arouter` does not hardcode default models for these tiers. Operators explicitly map tiers to their model of choice via CLI commands).*


* **`asessions`:** Post-mortem session log inspector. Dumps execution history, tool calls, model decisions, and token consumption without consuming additional tokens.
* **`arun`:** The underlying headless execution engine applying non-interactive flags (`--auto-review --trust`) and handling piped stdin.

Ensure `~/.local/bin` is in your environment and configure the `arouter` CLI symlink:

```bash
# Add local bin to PATH if not already present
export PATH="$HOME/.local/bin:$PATH"

# Ensure agent-router-cursor.py is executable and linked as 'arouter'
chmod +x ~/.local/bin/agent-router-cursor.py
ln -sf ~/.local/bin/agent-router-cursor.py ~/.local/bin/arouter
ln -sf ~/.local/bin/agent-sessions.py ~/.local/bin/asessions

```

### C. Configuring Model Tiers via `arouter` CLI

**Do not manually modify `~/.cursor/arouter-config.json`.** Use the `arouter` CLI to configure model mappings:

```bash
# Configure chosen model mappings for each tier
arouter --set cheap gemini-3.8-flash-low
arouter --set balanced gemini-3.8-flash-medium
arouter --set smart gemini-3.8-flash-high

# Verify active mappings
arouter --show

```

### D. System-Wide Dispatcher & Tier Binaries

In-memory Bash functions (`export -f`) do not survive subshell boundaries or non-interactive shells invoked by Linux `timeout`. Deploy the dispatcher and tier entrypoints as persistent executables in `/usr/local/bin`:

```bash
# 1. Install central execution dispatcher
cat <<'EOF' > /usr/local/bin/arun
#!/usr/bin/env bash
set -euo pipefail

TIER="${1:-balanced}"
shift || true

# Resolve model via router CLI
MODEL=$(arouter --get "$TIER" 2>/dev/null || echo "auto")

# Capture stdin input if piped
PIPED_INPUT=""
if [[ ! -t 0 ]]; then
    PIPED_INPUT=$(cat)
fi

# Execute agent with auto-review and workspace trust enabled
if [[ -n "$PIPED_INPUT" ]]; then
    exec agent --auto-review --trust --model "$MODEL" "$*

Context / Input:
$PIPED_INPUT"
else
    exec agent --auto-review --trust --model "$MODEL" "$@"
fi
EOF

chmod +x /usr/local/bin/arun

# 2. Deploy tier executables into /usr/local/bin
for tier in acheap abalanced asmart; do
    cat <<EOF > /usr/local/bin/${tier}
#!/usr/bin/env bash
exec /usr/local/bin/arun "${tier#a}" "\$@"
EOF
    chmod +x /usr/local/bin/${tier}
done

```

### E. Agent Execution Skill Architecture (`atools-repair`)

> **Anti-Recursion Boundary:** The autonomous repair loop operates strictly under a single worker skill: `.cursor/skills/atools-repair/SKILL.md`. This subordinate agent executes within the target repository, parsing runbooks and verifying assertions. It intentionally excludes outer dispatchers (`arouter`, `abalanced`, `asessions`) to prevent recursive execution loops. Auditing tools for human operators (`asessions`, `arouter --show`) reside separately in `~/.cursor/skills/atools.md` as an auxiliary manual reference cheatsheet.

#### Autonomous Worker Skill (`.cursor/skills/atools-repair/SKILL.md`)
Standardizes the headless repair protocol within target repositories:

```markdown
# Skill: atools Eval-Driven Repair

## Objective
Execute iterative code changes against deterministic test suites without user intervention.

## Operational Protocol
1. Read the provided specification runbook (/tmp/Runbook_<title>.md).
2. Edit target implementation files within scope. Never touch out-of-scope files or immutable directories.
3. Make all test scripts executable (`chmod +x proof/*.sh`).
4. Execute `bash proof/run_suite_<title>.sh`.
5. If failures occur, inspect logs under `proof/out/`, apply minimal surgical fixes, and re-run.
6. Once all checks output PASS, run `git status` and conclude.
```
---

## 4. Execution Pattern & Session Auditing

### A. Supervised Loop Invocation

Launch the autonomous repair loop under an OS wall-clock watchdog. By referencing the repository skill (`atools-repair`), the prompt remains minimal and focused:

```bash
timeout -k 15s 12m abalanced "Follow the 'atools-repair' skill protocol using /tmp/Runbook_<title>.md as your specification."

```

*(Note: For complex, architectural refactors, substitute `abalanced` with `asmart`).*

### B. Session Auditing & Diagnostics

Inspect runs post-mortem without burning additional tokens:

```bash
# List recent session runs, durations, and token usage
asessions

# Inspect deep execution trace, tool invocations, and LLM reasoning for a specific run
asessions <session-uuid>

```

---

## 5. Machine-Wide Safety & Guardrail Configuration

### A. Global Agent System Prompt (`~/.cursor/rules/`)

Machine-wide prompt rules in `~/.cursor/rules/` are injected into the agent context across **all** repositories, preventing circumvention via per-repo `AGENT.md` manipulation:

```bash
mkdir -p ~/.cursor/rules

cat <<'EOF' > ~/.cursor/rules/git-safety.md
# Global Agent Operating Guidelines

## Git Safety & Branch Hygiene
1. **Branch Protection:** NEVER commit directly to `main`, `master`, or release branches. Always verify that `git branch --show-current` begins with `wip/` before staging or committing.
2. **Feature Isolation:** All experiments, patches, and refactors MUST occur on an isolated `wip/*` branch. If on a protected branch, checkout a wip branch first.
3. **No Upstream Mutations:** NEVER execute `git push` or modify remote refs under any circumstances. Remote synchronization is strictly reserved for human operators.
4. **Assertion-Gated Exit:** Never commit until all project tests/proofs pass. Conclude every completed run with `git status`.
EOF

```

### B. Tool Authorization & Permissions (`~/.cursor/cli-config.json`)

To enable unattended runs without disabling safety checks, configure three defensive layers:

1. **Deterministic Allowlist:** 32 pre-approved read and test commands that execute without terminal approval prompts.
2. **Hard Denylist:** Unconditionally blocked destructive commands (`rm -rf /`), remote operations (`git push --force`), and pre-commit bypass flags (`-n`, `--no-verify`).
3. **`--auto-review` Classifier:** Any shell command outside both lists is evaluated by Cursor's server-side classifier before execution.

Synchronize this configuration:

```bash
python3 - <<'PY'
import json, os

path = os.path.expanduser("~/.cursor/cli-config.json")
try:
    with open(path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {"version": 1}

cfg["approvalMode"] = "allowlist"
cfg.setdefault("permissions", {})

cfg["permissions"]["allow"] = sorted(list(set(cfg["permissions"].get("allow", []) + [
    # Navigation & File Reading
    "Shell(ls)", "Shell(ls *)", "Shell(dir)",
    "Shell(cat *)", "Shell(head *)", "Shell(tail *)",
    "Shell(grep *)", "Shell(find *)", "Shell(wc *)",
    "Shell(diff *)", "Shell(sha256sum *)",

    # Git Inspection, Branching & Staging
    "Shell(git status)", "Shell(git status *)",
    "Shell(git diff)", "Shell(git diff *)",
    "Shell(git log)", "Shell(git log *)",
    "Shell(git show)", "Shell(git show *)",
    "Shell(git rev-parse *)",
    "Shell(git branch)", "Shell(git branch *)",
    "Shell(git checkout *)", "Shell(git checkout -b *)",
    "Shell(git switch *)", "Shell(git switch -c *)",
    "Shell(git add *)", "Shell(git commit -m *)",

    # Safe Utilities & Execution
    "Shell(mkdir -p *)", "Shell(chmod +x proof/*.sh)",
    "Shell(python3 -m compileall *)",
    "Shell(python3 -m py_compile *)",
    "Shell(python3 -c *)",
    "Shell(pytest)", "Shell(pytest *)",
    "Shell(bash proof/*.sh)", "Shell(bash proof/run_suite_*.sh)"
])))

cfg["permissions"]["deny"] = sorted(list(set(cfg["permissions"].get("deny", []) + [
    # Destructive System Commands
    "Shell(rm -rf /)", "Shell(rm -rf /*)", "Shell(rm -rf ~*)",
    "Shell(git push*)", "Shell(git push)",
    "Shell(git clean -fdx)",
    "Shell(reboot)", "Shell(shutdown*)", "Shell(init 0)",
    "Shell(mkfs*)", "Shell(dd if=*)",
    "Shell(iptables*)", "Shell(ufw*)",
    "Shell(passwd*)", "Shell(visudo*)",

    # Hook Bypasses (Blocked for agent executions)
    "Shell(git commit *--no-verify*)",
    "Shell(git commit *-n *)",
    "Shell(git commit *-n)"
])))

with open(path, "w", encoding="utf-8") as f:
    json.dump(cfg, f, indent=2)

print("✅ ~/.cursor/cli-config.json permissions successfully synchronized.")
PY

```

### C. Dual Git Pre-Commit Hook Architecture

Configuring Git's `core.hooksPath` globally normally bypasses repository-local `.git/hooks/`. A dual-hook architecture enforces machine-wide branch policies while delegating to local checks:

```bash
# 1. Create global hooks directory
mkdir -p ~/.config/git/hooks

# 2. Deploy global dispatcher hook
cat <<'EOF' > ~/.config/git/hooks/pre-commit
#!/usr/bin/env bash
set -e

# 1. TEST FIXTURE BYPASS: Ignore temporary / sandboxed test repositories
REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || true)
if [[ "$REPO_ROOT" =~ ^/tmp/ || "$REPO_ROOT" =~ ^/var/tmp/ ]]; then
  exit 0
fi

# 2. GLOBAL POLICY: Enforce isolated wip/* branches
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || true)
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" || ! "$CURRENT_BRANCH" =~ ^wip/ ]]; then
  echo "🚨 [BLOCKED] Commits to '$CURRENT_BRANCH' are prohibited by global policy."
  echo "   All agent work must occur on a branch prefixed with 'wip/' (e.g., git checkout -b wip/<task>)."
  echo "   Humans may override with: git commit --no-verify -m '...'"
  exit 1
fi

# 3. LOCAL DELEGATION: Execute repo-specific hook if present
GIT_DIR=$(git rev-parse --git-dir 2>/dev/null || true)
if [[ -n "$GIT_DIR" && -x "$GIT_DIR/hooks/pre-commit.local" ]]; then
  "$GIT_DIR/hooks/pre-commit.local" "$@"
fi
EOF

chmod +x ~/.config/git/hooks/pre-commit
git config --global core.hooksPath ~/.config/git/hooks

```

#### Repository-Specific Hook Pattern (`pre-commit.local`)

Repositories requiring local build validation or asset tracking place logic in `.git/hooks/pre-commit.local`:

```bash
cat <<'EOF' > .git/hooks/pre-commit.local
#!/usr/bin/env bash
set -e

if [[ -f "sync_version.py" ]]; then
  python3 sync_version.py
  if [[ -d "frontend" ]]; then
    git add -u frontend/ 2>/dev/null || true
  fi
fi
EOF

chmod +x .git/hooks/pre-commit.local

```

---

## 6. Infrastructure Replication Reference

| Component | Location / Command | Primary Function |
| --- | --- | --- |
| **Agent CLI** | `/usr/local/bin/agent` | Base Cursor Agent binary. |
| **Tier Router** | `arouter` (`~/.local/bin/arouter`) | CLI tool to set/get model tiers (`arouter --set <tier> <model>`). |
| **Session Auditing** | `asessions` (`~/.local/bin/asessions`) | Displays past session UUIDs, tool histories, and token spend. |
| **Dispatcher** | `/usr/local/bin/arun` | Central execution engine with `--auto-review --trust` and stdin handling. |
| **Tier Executables** | `/usr/local/bin/{acheap,abalanced,asmart}` | Standalone disk binaries callable by `timeout` and subshells. |
| **Global Agent Rules** | `~/.cursor/rules/git-safety.md` | Machine-wide prompt policy enforcing `wip/*` branches and blocking `git push`. |
| **Tool Guardrails** | `~/.cursor/cli-config.json` | 32 pre-approved tools; denylist blocking destructive commands and hook bypasses. |
| **Global Git Hook** | `~/.config/git/hooks/pre-commit` | Bypasses `/tmp` test fixtures, blocks non-`wip/*` commits machine-wide, and delegates to local hooks. |
| **Global Hook Path** | `git config --global core.hooksPath` | Points Git to `~/.config/git/hooks`. |
| **Repo Local Hook** | `<repo>/.git/hooks/pre-commit.local` | Project-specific pre-commit hook (e.g., version synchronization). |
| **Worker Skill** | `.cursor/skills/atools-repair/SKILL.md` | In-repo agent skill defining the headless Red-Green repair loop protocol. |
| **Operator Cheatsheet** | `.cursor/skills/atools.md` | Auxiliary manual reference for session inspection (`asessions`) and routing tiers. |


## 7. Verification

Run `./atools-compliance_audit.sh` to verify all 36 architectural guardrails.
