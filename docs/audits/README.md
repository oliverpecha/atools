# Audits

`atools-compliance_audit.sh` is the executable audit for the suite described in `../../DESIGN.md`. This file is its specification: every check has a stable ID, and the script and this table change together.

## Principles

- A check is mechanical. A rule with no check is not part of the audit (premise 2).
- Output is generated. A check that did not run is **SKIP**, never PASS (premise 3).
- The audit must be able to fail. `--self-test` runs it against a clean fixture and deliberately broken fixtures and expects each break to fail the intended check (premise 4).
- Core checks are vendor-neutral. Anything specific to one agent runtime lives in the `ADP` section.

## Usage

An adapter must be chosen explicitly. There is no default; running without one exits with code 2.

```bash
./atools-compliance_audit.sh --cursor                           # Cursor adapter, dev profile, repo = cwd
./atools-compliance_audit.sh --adapter cursor                   # same as --cursor
./atools-compliance_audit.sh --adapter none \
    --rules <file> --operator-doc <file> --worker-doc <file>    # vendor-neutral checks only
./atools-compliance_audit.sh --cursor --profile prod \
    --worker-user <user> --oracle-path <dir>                    # production isolation checks
./atools-compliance_audit.sh --cursor --report runs/audit.txt   # also write results to a file
./atools-compliance_audit.sh --cursor --strict                  # SKIP counts as failure
./atools-compliance_audit.sh --self-test
```

Exit codes: 0 when nothing failed (and nothing was skipped under `--strict`), 1 when a check failed, 2 for a usage error (no adapter, conflicting adapter flags, unknown option). `--cursor` combined with `--adapter none` is a usage error. The last output line reports passed, failed, skipped and warning counts.

## Adapters

| Selection | Supplies |
|---|---|
| `--cursor` or `--adapter cursor` | Runtime binary, required `arun` flags, permission config, default paths for rules, operator doc and worker doc |
| `--adapter none` | Nothing. `ADP` checks are SKIP. Rules, operator doc and worker doc must be passed explicitly or their checks are SKIP |

To support another runtime, add an adapter case to the script (binary, flags, default paths, permission checks), add its ADP rows below, and document it in `docs/install.md` section 7. The vendor-neutral sections need no change, because they read file content that the adapter or the `--rules`, `--operator-doc` and `--worker-doc` options point to.

## Check index

Status: **active** runs today; **planned** is a SKIP placeholder until the component exists.

### INST: suite installation (vendor-neutral)

| ID | Check | Status |
|---|---|---|
| INST-01 | `arouter` executable in user bin | active |
| INST-02 | `asessions` executable in user bin | active |
| INST-03 | `arouter --show` works | active |
| INST-TIER-cheap, -balanced, -smart | Each profile resolves to a model | active |
| INST-04 | `arun` is a persistent executable, not a shell function | active |
| INST-05 | `arun` resolves the model through `arouter` | active |
| INST-WRAP-`<entry>` | `acheap`, `abalanced`, `asmart` are executable | active |
| INST-WRAPD-`<entry>` | Each entry point delegates to `arun` | active |

### ADP: runtime adapter (Cursor)

| ID | Check | Status |
|---|---|---|
| ADP-01 | Runtime binary reachable in `PATH` | active |
| ADP-02 | Runtime reports a version | active |
| ADP-FLAG-`<flag>` | `arun` applies each required flag (`auto-review`, `trust`) | active |
| ADP-PERM-01 | Permission config exists | active |
| ADP-PERM-02 | Approval mode is allowlist | active |
| ADP-PERM-03, -04 | Denies `git push*` and `git push` | active |
| ADP-PERM-05 | Denies `rm -rf /` | active |
| ADP-PERM-06 | Denies commit `--no-verify` | active |
| ADP-PERM-07, -08 | Denies commit `-n` with and without arguments | active |
| ADP-PERM-09 | WARN if the allowlist contains `python3 -c *` | active |

### HARD: agent rules

| ID | Check | Status |
|---|---|---|
| HARD-01 | Rules file exists | active |
| HARD-02 | Requires `wip/` branches | active |
| HARD-03 | Prohibits `git push` | active |
| HARD-04 | Requires `git status` at exit | active |
| HARD-05 | Requires `(WI-<id>)` commit tags | active |

### HOOK: git pre-commit boundary

| ID | Check | Status |
|---|---|---|
| HOOK-01 | Global `core.hooksPath` is `~/.config/git/hooks` | active |
| HOOK-02 | Global pre-commit hook is executable | active |
| HOOK-03 | Hook enforces `wip/` isolation | active |
| HOOK-04 | Hook delegates to `pre-commit.local` | active |
| HOOK-05 | Hook has no `/tmp` bypass | active |
| HOOK-06 | Repo-local `pre-commit.local` is executable | active (SKIP if absent) |

### SKILL: operator and worker instructions

| ID | Check | Status |
|---|---|---|
| SKILL-01 to -03 | Operator doc exists and references `asessions` and `arouter` | active |
| SKILL-04 | Worker doc exists in the target repo | active |
| SKILL-05 | Worker doc excludes outer dispatchers (`arouter`, tier entry points, `asessions`, `arun`, `amaster`) | active |
| SKILL-06 | Worker doc forbids editing oracle files and proofs | active |
| SKILL-07, -08 | Worker doc requires `wip/` and `(WI-<id>)` | active |
| SKILL-09 | No `/tmp` runbook contract (`Runbook_`) | active |
| SKILL-10 | No `chmod +x proof` | active |

### PROF: security profile

| ID | Check | Profile | Status |
|---|---|---|---|
| PROF-00 | WARN: same-user isolation in effect | dev | active |
| PROF-01, -01b | Hooks path root-owned and not group or world writable | prod | active |
| PROF-02 | Worker user cannot read the oracle | prod | active (needs `--worker-user`, `--oracle-path`, passwordless `sudo -u`) |
| PROF-03 | Worker user cannot write the oracle | prod | same |
| PROF-04 | Worker environment has no credentials | prod | same |
| PROF-05 | Worker has no global git config | prod | same |

### ORC, SCP, EVD: gate checks

| ID | Check | Status |
|---|---|---|
| ORC-01 | Null implementation is red | planned |
| ORC-02 | Each re-injected defect is red | planned |
| ORC-03 | Reference commit is green | planned |
| ORC-04 | Oracle manifest hash matches the pinned version tag | planned |
| ORC-05 | Oracle lints pass, including the `echo \| grep -q` lint self-test | planned |
| ORC-06 | Repeated runs (3 or more) agree | planned |
| SCP-01 | `BASE..HEAD` paths match `ALLOW` and avoid `FROZEN` | planned |
| SCP-02 | Every commit has a registered `(WI-<id>)` tag; every declared item has a commit | planned |
| SCP-03 | Worktree is clean | planned |
| EVD-01 | Accepted ledger lines cite a report commit | planned |
| EVD-02 | `sessions.tsv` has a row per session | planned |
| EVD-03 | Leak scan finds no key patterns | planned |

## Evolving the audit

1. When a component lands, replace its SKIP stubs with real checks under the same IDs, and mark them active here.
2. When a guard is added to the design, add its check and a matching broken fixture to `--self-test` in the same commit.
3. The commit message states which failure the check prevents and where it was seen.
4. Never change a check ID's meaning. Retire an ID and add a new one.

## Superseded

`history/atools-compliance_audit.sh` audited the previous guide's layout. It checked `/usr/local/bin/arouter` as the dispatcher, used a substring test for the `-n` deny rule, required the string `Runbook_` in the worker skill, and had no SKIP state. It is kept for reference and should not be run as the current audit.
