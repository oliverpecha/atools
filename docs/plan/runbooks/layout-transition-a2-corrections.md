# Runbook: Layout transition, part A2 (corrections from the delta review) - workstream `LT-A2`

- **Branch / worktree:** `wip/layout-amend-a` in `~/atools-lt-a`. Continue on top of head `738cd6b`. Never rewrite or amend existing commits.
- **Input:** the delta challenge verdict (`DC-1` to `DC-14`), saved by the Owner as `/tmp/lt-a-delta-verdict-raw.md`. Spec: `docs/plan/layout-transition-memo.md` (L-1 to L-11 are locked; the memo wins over the Design and the addendum).
- **Boundary:** same as `docs/plan/runbooks/layout-transition-a-authoring.md` (read its sections 1 and 2 first). Allowed: `docs/design/`, `docs/plan/` (not historical records), `docs/guide/`, `src/actl/INTERFACES.md`, `test/actl/`, `proof/`, `fixtures/`. Forbidden: `src/actl/*.py`, `schemas/*.json`, `bin/`, `install.sh`, `src/router`, `src/sessions`, `src/core`, `engines`, `hooks`, `rules`, `audit/`, `tools/`. No push, no merge, no `--no-verify`, no `rm` of tracked files (`git mv`). Part B is not started.
- **Commit tags:** one tag per commit, one area per commit: `(WI-S0-SPEC)` Design/addendum/spec-S0, `(WI-IFACE)` INTERFACES.md, `(WI-S0-PROOF)` tests/proofs/fixtures, `(WI-DOCS-n)` Handoff Prompts, Guide, signoffs. `n` = next free from `git log --format=%s | grep -o 'WI-DOCS-[0-9]*' | sort -V | tail -1` run on the branch. Format `type(scope): summary (WI-tag)` plus `Why:`, `What changed:`, `Result:`. A change to the gate logic of P-S0-02 gets its own `WI-S0-PROOF` commit.

## 0. Rules for this run

1. The reviewer saw only excerpts of the bundle. Before changing anything for a finding, verify it against the repo with a command and keep the raw output. If a finding is wrong, change nothing for it and record `DISPUTED` with the evidence in the report.
2. Never resolve a conflict silently. Decisions listed in section 2 have a default; apply the default and list it under "Proposed decisions" for the Owner to ratify. Do not invent new open-item numbers (no `O-17`).
3. Do not weaken any proof to get a gate green. The amended suites stay RED for memo reasons only.
4. Scratch space is `mktemp -d`. Unique names (PB-6).

## 1. Tasks, in order

**C1 (DC-1, blocker) P-S0-02.** Run `git diff main..HEAD -- proof/stage0/P-S0-02.sh` and `git show 2d8be0d -- proof/stage0/P-S0-02.sh`. For every path whose handling changed, produce a table in the report: path | method (pinned blob hash with `git hash-object` at the current HEAD / fork-point handled / allowlisted). Required end state: the memo and the LT-A runbooks are handled by pin or fork point, never by a glob; `tools/` is NOT allowlisted (L-6, PB-2); docs allowlists must not cover INTERFACES.md, `test/actl`, `proof`, `fixtures`, `tools`. Fix anything else in a separate commit. Re-pin all hashes last, after every other change in this run, with an idempotent script printing `ok`/`SKIPPED` (the replacement contains the already-applied marker literally).

**C2 (DC-2, blocker) INTERFACES.md residue.** Rewrite every stale name in prose and in the fenced `interfaces.json` block: `runs/ev-{seq:03d}.json` to `runs/verification-{seq:03d}.json`, `ev.parent`/`ev.tripwires` to `verification.*`, `handoff/{tag}/implementer-inputs/...` to `sprints/<repo>/<tag>/mailboxes/implementer/inbox/...` (and the outbox equivalents). Update P-S0-26 expectations if they reference these. Keep the three proposed Layout property names (`records`, `profile`, `mailboxes`) in "Proposed decisions" only.

**C3 (DC-3) O-17.** Remove "O-17" everywhere. Replace by a numbered "Proposed decision" list in the report and in the Owner Amendment Note draft, limited to the three Layout names plus the decisions in section 2.

**C4 (DC-4, DC-5) sweeps.** Fix `~architect` and its siblings (Design.md around line 599) to `profiles/<role>`. Fix bare `qual receipt` and similar to `qualification receipt`. Run, over `docs test/actl proof fixtures src/actl/INTERFACES.md` excluding the memo map, `docs/proposals`, `docs/plan/signoffs`, `docs/plan/runbooks`, `docs/design/actl_Design_collisions.md` and `proof/stage0/SURVIVOR_ANALYSIS.md`:
`git grep -nE '~(architect|challenger|implementer|curator)|\bqual\b|\bev\b|to_ev_|actl_repo|\.handoff\(|\.homes\(|/srv/agent-graph|handoff_dir|actl-repo|ev-[0-9]|qual-[0-9]'`
Every remaining hit is fixed or has a one-line justification in the report.

**C5 (DC-6) `handoff_dir` JSON key.** Default: rename to `mailboxes_dir` in spec-S0 S0-R4.7, INTERFACES.md, the tests (`test_p04_sprint.py` and any fixture or expected fragment) and the Handoff Prompts. Record as a proposed decision.

**C6 (DC-7) Design invariant on profiles.** Restate: `profiles/<role>` is the persistent HOME (login, transcripts, installed skills), non-authoritative; no persistent path is trusted for verification; the outbox lock is what is read-only during verification. Reconcile the profile directory mode between the Design (0750) and spec/tests (0755): follow the memo if it states a mode; otherwise align the Design to the spec and tests and record it as a proposed decision.

**C7 (DC-8) closeout.md contents.** Make the Design list match memo section 5 verbatim, including `hardcap_stripped`. Check all eight items character by character and paste the comparison in the report.

**C8 (DC-9) F006 tripwire pattern.** Anchor the renamed pattern (`records/` or `$ACTL_ROOT/records`) and add a negative test: the word "records" in ordinary code is not flagged. The test must go red or green consistent with the current code; report which.

**C9 (DC-10) Courier paragraph.** In the COMMON BLOCK of `docs/plan/actl_Handoff_Prompts.md`, cut it back to the memo section 4 one-line agent rule; state that mailboxes are IPC inside the sprint and courier drawers are the Sync folder.

**C10 (DC-11) PB-2 list.** Grep every spelling of the immutable list (Handoff Prompts, Guide, Design, addendum, spec) and add `tools` wherever it is missing. Do not touch hooks, rules or audit (Part B item; Vela adds it to the Part B runbook).

**C11 (DC-12) Mutants for the new rules.** Add at least one planted defect to `proof/stage0/selfcheck_mutations.sh` for each new rule where it can be planted at schema, fixture or golden level (renamed kinds, `repo` field, profiles README expectation, repo-scoped paths). For any rule that can only be mutated once the implementation exists, list it in the report under "Deferred to Part B (D-29, tools/mutate.py)". Report the new mutant count (baseline 18).

**C12 (DC-13, DC-14) Evidence and notes.** Report: the exception line of each crashing red (P-S0-05, -14, -29) and the name of the test that covers each new rule and which suite turns red for it. Decide DC-14 (a) (`profiles/README.md` written by `init` only, per L-8, unless the memo says otherwise) and (b) (`sprint-proposal` rejecting `repo`: remove it unless the memo supports it); both go under "Proposed decisions". Split nothing that is already committed; just avoid mixed areas from now on.

**C13 Verdict records (last commit, `WI-DOCS-n`).** Copy the verdict into `docs/plan/signoffs/layout-transition-delta-challenge-verdict.md` with this header: reviewer "Perplexity chat (underlying model not disclosed; PB-9 family unconfirmed)", subject, commit reviewed `738cd6b`, date. Remove only the pasted signed-URL citation artifacts (`[[ppl-ai-file-upload...]]`); change no other word. Add `docs/plan/signoffs/layout-transition-delta-resolution.md`: table DC-1..DC-14 with status FIXED / DISPUTED / DEFERRED-PART-B / PROPOSED-DECISION and the commit hash. Leave "delta review verdict" in the approval draft as pending.

## 2. Defaults awaiting Owner ratification

| Item | Default applied |
|---|---|
| `handoff_dir` key | rename to `mailboxes_dir` |
| Profile dir mode | memo if stated, else Design aligned to spec/tests |
| README written by | `actl init` only |
| `sprint-proposal` rejecting `repo` | removed unless memo supports it |
| New mutants for unimplemented rules | deferred to Part B gate |

## 3. Delivery gate (run last; paste the raw output into the report)

1. `git merge-base --is-ancestor 738cd6b HEAD; echo $?` is 0, and `git log --format='%h %s' 738cd6b..HEAD` lists only new commits, each with exactly one valid WI tag.
2. `git diff --name-only main..HEAD` has zero forbidden-path hits and nothing outside the allowed paths.
3. `bash proof/run_suite_actl_s0.sh` exits 1 with `0 Environment`. Every FAIL maps to a memo item. The red set may equal the previous 10 (P-S0-03, -04, -05, -06, -08, -09, -14, -26, -29, -30) or add reds only with a stated memo reason.
4. `bash proof/run_suite_exit_code.sh`, `bash proof/stage0/P-S0-27.sh`, `proof/stage0/golden_selfcheck.sh` and `proof/stage0/selfcheck_mutations.sh` exit 0.
5. `bash audit/atools-compliance_audit.sh --cursor | tail -2` shows 0 failed.
6. P-S0-02 passes, and its table (C1) shows no `tools/` allowlist and no glob over the memo or runbooks.
7. The C4 sweep command is run again and every hit is justified.
8. `git status --short` is empty. Write `/tmp/lt-a2-report.md` (not committed): C1 table, DC status table, Proposed decisions, deferrals, gate outputs. Run every command with `</dev/null`. Then stop.
