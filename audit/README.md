# atools Compliance Audit

Canonical machine-wide compliance audit testing system dispatchers, tier resolution, runtime adapters, safety guardrails, and Git pre-commit hooks.

## Usage

An adapter flag must be provided explicitly:

```bash
# Audit Cursor environment (dev profile)
audit/atools-compliance_audit.sh --cursor

# Vendor-neutral checks only (skips Cursor-specific configs)
audit/atools-compliance_audit.sh --adapter none

# Strict mode (treats SKIP assertions as failure)
audit/atools-compliance_audit.sh --cursor --strict

# Write detailed audit report to file
audit/atools-compliance_audit.sh --cursor --report /tmp/audit-report.txt

# Run internal fixture self-test
audit/atools-compliance_audit.sh --self-test

```

### Exit Codes

* `0`: All assertions passed.
* `1`: One or more assertions failed (or skipped under `--strict`).
* `2`: Usage / CLI argument syntax error.

---

## Validated Boundaries

1. **INST (Installation & Tiers):** Validates `/usr/local/bin/` wrappers (`acheap`, `abalanced`, `asmart`) delegate to `arouter`, and checks tier model resolution (`cheap`, `balanced`, `smart`).
2. **ADP (Runtime Adapter):** Validates `agent` binary responsiveness, `--auto-review`, `--trust`, and parses `~/.cursor/cli-config.json` permissions (`allowlist`, blocking `git push`, `rm -rf`, `--no-verify`, `-n`).
3. **HARD (Prompt Rules):** Enforces `~/.cursor/rules/git-safety.md` requirements: `wip/` branch isolation, prohibition of `git push`, assertion-gated `git status`, and `(WI-<id>)` commit tags.
4. **HOOK (Git Pre-Commit Boundary):** Confirms global `core.hooksPath` directs commits through `~/.config/git/hooks/pre-commit` and delegates to `pre-commit.local` without `/tmp` bypasses.
5. **SKILL (Instructions & Anti-Recursion):** Confirms operator instructions reference outer tools, and worker instructions strictly exclude outer dispatchers (`arouter`, `acheap`, etc.) and forbid modifying oracle/proof files.
6. **SYNC (Installed vs Repo Synchronization):** Confirms installed system files (`rules/git-safety.md`, `hooks/pre-commit`, and `.cursor/skills/atools-repair/SKILL.md`) strictly match repository source copies to catch uncommitted or uninstalled configuration drift.
7. **PROF (Security Profile):** Dev profile checks same-user boundaries; production profile checks root ownership and user isolation.

---

## Execution Invariants

* **Zero LLM Egress:** All assertions evaluate local POSIX filesystem state, binaries, and JSON configs without sending requests to external LLM providers.
* **Read-Only:** Executes non-destructive assertions without altering repository branches, permissions, or system state.
