# Stage 0 interface challenge verdict

Reviewer: Claude Sonnet 5.5 (Anthropic), as stated in the saved text
Subject: src/actl/INTERFACES.md, authoring-pass draft (the commit reviewed is not recorded in the saved text)
Verdict: accept after fixes (1 blocker, 13 major, 14 minor); all fixes are text edits to INTERFACES.md
Finding IDs F-01 to F-28 are defined in the text below

---

Claude Sonnet 5.5, Anthropic, Claude family (not Gemini). The INTERFACES.md header lists "Claude Sonnet 5.5" among earlier challengers. I have no record of that round, so treat this as a fresh review and judge PB-9 independence yourself.

## 1. Verdict and findings (Task 1)

**Verdict: accept after fixes** (1 blocker, 13 major, 14 minor). All fixes are text edits to INTERFACES.md, and nothing needs a redesign. Several of your checks are already resolved in this revision:
- Check 5: `main` says "`0` preserved for `--help`".
- Check 6: `run_doctor` no longer raises.
- Check 9: `active_solution_key` and `active_oracle_draft` exist.
- Check 1: the `fence="N"` text matches addendum 7.5.
- Check 16: the `run_o1` out-of-tree staging matches S1-R4.

| id | sev | section | evidence | suggested fix |
|---|---|---|---|---|
| F-01 | blocker | §1.10 `archive_session_log`, `wait_session`, `verify_impl` | archive: "unlinks original log and `.exit` only after `runs/log` copy verification"; wait: "(which unlinks `.exit`)"; verify_impl: "and only then unlinks original"; S1-R15: "unlinked **only after** `runs/ev-{seq:03d}.json` is durably written" | Three owners of the unlink, two of them before `ev` exists, and `ev.session.log_sha256` needs the hash first. Make `archive_session_log` copy, verify and return the hash, and never unlink. One named step (a `release_session_files(...)` or `verify_impl` only) unlinks after the `ev` fsync. Fix the `wait_session` note. |
| F-02 | major | §3.4, §1.5 `validate` kinds, §7 A-4 | "`schemas/closure-draft.json`, `schemas/closure.json`"; A-4 reading (b) puts `closure` among required-meta kinds; S0-R7: "In `closure`, `kind`, `seq`, and `parent` are optional so agent-authored drafts validate before promotion" | Contradicts S0-R7. It also adds `closure-draft`, `meta`, `attempt` and `sprint-proposal`, which are absent from the addendum 5.3 schema tree. S2-R6 itself cites `sprint-proposal.json`, so the tree is the stale side for that one. Drop `closure-draft` and make closure meta optional per S0-R7, with stamping asserted in `verify_impl` and a proof. List the other three in §6 as additions needing Owner approval. |
| F-03 | major | §7 A-1, A-3, A-4 | A-1 quotes S0-R6 as "`{relpath}\0{file_sha256}\n` extended with an x/- flag", but current S0-R6 prints the full `f"{relpath}\0{exec_flag}\0{file_sha256}\n"`. A-3 says S2-R8 lacks `--sprint`, but its header is "`actl replay <role>-<n> [--sprint TAG]`". A-4 quotes an older S0-R7. | The register was written against earlier addendum text (probably pre WI-DOCS-3; unverified). Rewrite A-1..A-4 against current text. Keep A-3 only as "rule when `--sprint` is omitted". |
| F-04 | major | §1.8 `main`; §1.7, §1.10 errors | "`EnvironmentError -> 4`"; "integrity/state/storage `OSError` or `RuntimeError` → `3`"; "input `FileNotFoundError` → `2`"; `wait_session`: "`RuntimeError` if `shutil.which("tmux")` is `None` (mapped to exit code `4`)" | In Python 3 `EnvironmentError` is `OSError`. The same exception types get three exit codes. `UsageError` and `StateIntegrityError` are undeclared. Add `actl.errors` (UsageError, HaltError, EnvError) to §1 and interfaces.json. Handlers raise only those, `main` maps only those, and there is one documented fallback. |
| F-05 | major | §1.8 `decide_next`, registry entry 2 | `decide_next(..., session_probe: Callable...)` but rules are `evaluate(layout: Layout, tag: str)` | The probe cannot reach the rules. S1-R12 needs running/finished/lost state, so phase3 would call tmux directly and P-S1-18 (table-tested) loses purity. Use `evaluate(layout, tag, session_probe=None)`. |
| F-06 | major | §3.4 `ev.halt` | enum has "`selftest_failed`" and "`internal_error`"; Design §4.3/§6.3: "`integrity_mismatch` \| `wrapper_rejected` \| `unsupported_cap` \| `architect_unavailable`" | The Design set is closed. S1-R2 introduces `selftest_failed`, and the Design wins. `internal_error` has no source. Restrict the enum to `integrity_mismatch` and `selftest_failed`. Log `selftest_failed` in §6 as a proposed Design amendment (or map it to `integrity_mismatch`). Drop `internal_error`. |
| F-07 | major | §1.9 | "`get_log_path` similarly resolves `ATOOLS_LOG_DIR` dynamically"; S0-R16 item 6: "No other behaviour changes (log handling…)" | Code at HEAD resolves `LOG_DIR` and `METADATA_DIR` once at import. Addendum 5.9 changes only the exit helpers and defines an unused `_resolve_log_dir`. Delete the clause. Only `get_exit_path` uses `_resolve_metadata_dir()`. |
| F-08 | major | §1.6 `parse`, `validate` | parse: "fails `^(ALLOW\|FROZEN):\s*(\S.*)$` or has a leading `/`, `\`, NUL, or `..` segment"; validate: "rejects inline `#` comments"; S0-R12 has inline `#`, `.`, `..` and empty segments "rejected with `ValueError`" | `.` and `//` are missing from parse. Inline `#` moved into `validate`, which returns strings instead of raising. Proofs written to S0-R12 (P-S0-12) will disagree. Restore the S0-R12 split. |
| F-09 | major | §3.6 `repair.txt` | bundle.txt: `<<<END_RESPONSE bundle="{bundle_sha256[:8]}">>>`; repair.txt: "close with `<<<END_RESPONSE bundle={bundle_sha256[:8]}>>>`"; S2-R4 paste terminator regex needs `bundle="[0-9a-f]{8}"` | The quote-less sentinel is accepted by the 7.5 grammar but not by the `--paste` regex, so paste mode never terminates. Use the quoted form everywhere in INTERFACES. The Owner must reconcile 7.5 (optional quotes) with the S2-R4 regex (required); that is an addendum matter and is not patched. |
| F-10 | major | §1.5 `validate` | "`path` is "/" for root type errors and "/<prop>" … for missing `required` … and rejected `additionalProperties`" | Nothing covers wrong type, enum or pattern at a property, or array items (`steps[0].exit_code`). The immutable `artifacts/invalid` fixtures must encode "expected error path". Pin RFC 6901 pointers for every keyword, array indices, and the missing-required rule. |
| F-11 | major | §3 (all) | "All JSON Schemas in `schemas/*.json` use Draft 2020-12…" followed by field lists with types but no required/optional marks | Two sources of truth: §3 is immutable under PB-2, `schemas/` is implementer-authored, so drift is undetectable. Keep §3 only for non-schema files (`bundle.json`, `unpack.json`, `baseline.json`, turn files, `coverage.md`) plus pointers. Or add a machine-checkable `schemas` block to §4, checked by P-S0-26. |
| F-12 | major | §1.3 `state_lock` | "process-local re-entrancy depth keyed on `layout.state_lock(tag)` … Re-entrant within a process" | A per-process counter lets a second thread, or a forked child inheriting counter and fd, skip the `flock`. Across processes it is safe, because the kernel drops `flock` on `kill -9` (P-S0-05). Use `threading.local()` depth, reset after fork, and forbid holding the lock across subprocess or LLM waits. |
| F-13 | major | §1.3 `reserve`, `reconstruct`; §3.1 | reserve: "increments `state["seq"]`" (no highwater, no `max`); reconstruct: highwater "(written by `reserve` before returning)"; `run_id`: "non-empty unique identifier" | S0-R5 is `max(state["seq"], highwater)+1` plus a highwater fsync. With `state.json` deleted, `run_id` cannot be rebuilt from artifacts, so the rebuilt state may fail `validate("state")`. Restate S0-R5 in `reserve`. Define a deterministic `run_id` rule or make it optional on rebuild. Define the depth of "`handoff(tag)/*`". |
| F-14 | major | §1.10 `verify_impl`; §2 `verify-impl` | side effects omit `prior_attempt.json` (S1-R7: "On red it writes `implementer-inputs/prior_attempt.json`"), the `closures_submitted` update, and the tripwire merge. Function has `closure_path: Path \| None = None` while the CLI requires `--closure`. | `closures_submitted` is needed by the S1-R3 G2 precondition and by `prior_attempt.closures_submitted`. Add the three effects or name their owner. Define `None` for `closure_path` (Stage 3 Q2 runs G3/G5/G6 without a closure) and for `worktree`. |
| F-15 | minor | §1.10 `wait_session` | default `timeout_s=2700`; S1-R14: "wall_clock + kill grace + 30 s" | With a 45m watchdog plus 3 s grace, `wait` gives up inside the grace and kills a session that would record 124, which becomes 143. Default to `None`, derived from `hard_cap` + grace + 30. Also `wait_session` and `archive_session_log` both return `log_sha256`; keep one producer. |
| F-16 | minor | §1.7 `run_doctor`; §3.3 | "recorded as `not_found`" but §3.3 uses `tmux: str \| null` and `audit.present: bool`; "snapshotting and restoring `proof/out/`" | Pin how `not_found` is represented and that exit 4 derives from it. The snapshot trick has no addendum source. Whether `proof/out` is git-ignored is unknown (S0-R1: "never modifies the repo"). |
| F-17 | minor | §1.2 | `reserve` accepts "`implementer`" and `parse_seq_from_name` parses `implementer-NNN`, but `format_artifact_id` rejects it | Stage 1 will hand-format `implementer-{seq:03d}` and `wip/{seq:03d}`. Accept `implementer` in `format_artifact_id` and document the branch name. Define `slug_trimmed` length and the hash encoding in `format_session_name`. |
| F-18 | minor | §1.8 `main` | "On any error exit emits `{"ok": false, …}`" | argparse prints and exits itself, so `error` text is only available through an `ArgumentParser.error` override. State that. |
| F-19 | minor | §4, §1.8, §1.10 | Registry entry points, `PRIORITY` and the `actl.verify.StepResult` re-export are prose only. `actl.stage` appears in the §1.10 title with no entries. `params` have no `default`. | S0-R15 puts "the registry entry points" in the block, and P-S0-26 checks only what is listed. Add `entry_point`/`constant` entries and a `default` field. Declare `actl.stage` or drop it from the title. |
| F-20 | minor | §1.8 | "Phase 1–3 rules live in `docs/plan/INTERFACES_S1_S2.md`" | The file is not in the attachment and contradicts the one-file freeze. Delete and point to S1-R12 and S2-R10. |
| F-21 | minor | §2 table | the `actl bundle` row has a bare pipe in `--out <FILE…->`; other rows escape theirs | Write `<FILE\|->`. |
| F-22 | minor | §3.1, §3.2 | `sprint_tag` pattern ends `$` while others use `\Z`. `seq` is "only field mutated in Stage 0" though `create_sprint` sets `active_spec`. | Use `\Z` throughout and state the patterns are Python `re` (ECMA treats `\Z` as a literal Z). Fix the wording. |
| F-23 | minor | §3.2, §1.7, §1.10 | `repo_test_cmd = "python3 -m pytest test -q -rf"` (S0-R8 names the key but gives no value). `spec_source` with no `--spec` is unstated. `run_o2(repo_test_cmd=None)` has no source. | Record these in §6/§7, or take them from `graph.toml`. |
| F-24 | minor | §1.11, §2 | `promote_role` returns 5 keys but the CLI lists 7 (`active_solution_key`, `active_oracle_draft` missing). The Challenger's "next role" is undefined. `oracle-decision.json` and `sprint-proposal.toml` have no promotion rule. | Align the keys. State `staged_to` for the Challenger. State what promote does with non-artifact outputs. |
| F-25 | minor | §2 exit codes; §3.4 `qual` | `unpack` and `promote` list `3`, `wait` lists `1`, with no cause in S2-R4 or S1-R14. `qual` cannot express "Q5 skipped". | Define each or drop it. |
| F-26 | minor | §4 rule 2 | `ACTL_CHECK_STAGES` env protocol and the `hasattr(router.process, "read_exit_code")` fallback | Not in S0-R15 or the P-S0-26 row. Technically fine. Log in §6 as proposed (PB-4). |
| F-27 | minor | §1.1, §1.3 | `Layout.state_lock(tag)` is a path; `seq.state_lock(layout, tag)` is a context manager | Rename one (for example `state_lock_path`). |
| F-28 | minor | §7 | The register has A-1..A-4 only, and there is no self-check list. | Add the items above (F-13, F-14, F-17, F-23..F-25) and a short self-check list. |

**Check coverage.**
- Check 1 → F-09.
- Check 2 → F-17.
- Check 3 → F-02. The `notes` and `backlog` types as `string[]` are correct.
- Check 4 → F-08.
- Check 5 → fixed; residual F-18.
- Check 6 → fixed; residual F-16.
- Check 7 → F-06.
- Check 8 → `EXIT_OK`, `EXIT_RED` and `EXIT_HALT` do not occur in the attached INTERFACES.md. I read it; I did not grep it. The same defect class remains in F-04.
- Check 9 → fixed.
- Check 10 → fine. `run_id` is in Design §4.1, and extra `sprint_tag` is harmless. Residual F-13 and F-22.
- Check 11 → F-05, F-19, F-20. Flat `next_rules/*.py` matches the addendum.
- Check 12 → F-11.
- Check 13 → F-10, F-05.
- Check 14 → F-12, F-13.
- Check 15 → F-24. The idempotence key matches S2-R9. The proposal forbid-list matches S0-R7, but the allowlist is only implied by `additionalProperties:false`.
- Check 16 → F-01, F-15.
- Check 17 → F-14.
- Check 18 → F-21.
- Check 19 → F-19. I counted 68 entries, each with the six keys. Apart from the items in F-19, prose names equal JSON names.
- Check 20 → F-28.

## 2. Anchor table (Task 3)

| Anchor (addendum S0-R16 / 5.9) | Present at HEAD? | Unique? | process.py evidence | Patch? |
|---|---|---|---|---|
| `create_runner_script`, "after `meta_path = get_metadata_path(session_name)`" | yes | The statement occurs 3×: `load_session_metadata`, `cleanup_session_metadata` and `create_runner_script`. Unique only by the function scope the addendum names. | `meta_path = get_metadata_path(session_name)` directly after `runner_path = METADATA_DIR / f"{session_name}.run.sh"` | No. The anchor is correct by scope. An implementer must not blind-replace the one-line statement. |
| runner template: `cleanup()` body and `trap cleanup EXIT` | yes | yes | `rm -f {shlex.quote(str(runner_path))} {shlex.quote(str(meta_path))}` then `trap cleanup EXIT` | No |
| `spawn_detached_session`, "next to the existing log unlink" | yes | yes | `log_file.unlink()` | No |
| `spawn_detached_session`, tmux-failure branch | yes | yes | `Failed to start tmux session: {res.stderr}` followed by `runner_path.unlink(missing_ok=True)` | No |
| `kill_session`, "after the final kill -9 loop" | yes | yes. Only one `-9` loop; the `-15` loop comes earlier. | `subprocess.run(["kill", "-9", pid], check=False, …)`, followed by `cleanup_session_metadata(session_name)`, `print(msg_term)`, `return 0` | No |

The new helper names (`get_exit_path`, `read_exit_code`, `_record_exit`, `_wait_pids_gone`, `_resolve_*`) do not collide with anything in process.py. `re`, `time`, `os` and `Optional` are already imported. No addendum edit is needed.

**Item 6 and E1–E10.** These hold by reading only; I did not run them.
- Commit 2acaf3c changed only the `stream_session` and `attach_session` region (key forwarding), which is outside every anchor.
- Item 6 holds for the reference as written, provided `get_log_path` stays untouched (see F-07).
- All E checks start through `run_detached`, which calls `arouter cheap -d -n NAME -t DUR PROMPT < /dev/null`. The tier parsing sees first argument `cheap`, and `${…#a}` leaves it unchanged. The prompts `OK`, `EXIT7` and `SLEEP` are not tier words.
- `-d` means no auto-stream. `arouter kill` is handled before tier parsing.
- The F1, F2 and F11 statements still match bin/arouter.

**Other observations, not anchors and not patched.**
- Addendum 5.9 prose says `kill_session` "unconditionally overwrites `.exit` with `143`" (S0-R16 item 4, D-14). The reference snippet calls `_record_exit(session_name, 143, overwrite=False)`. The one-line fix is `overwrite=True`.
- `_resolve_log_dir` is defined but never used.

**Read-only side check: `TARGET="${FILTERED_ARGS[0]#a}"` for `auto`.** It yields `uto`, because `#a` strips the leading `a` of `auto`.
- `aauto` correctly becomes `auto`, `acheap`, `abalanced` and `asmart` are correct, and `cheap`, `balanced` and `smart` are unchanged.
- No tier argument at all hits the `*)` branch and correctly gives `auto`.
- Downstream, `arouter --get uto` falls back to the key itself, so `MODEL=uto` and the engine gets `--model uto`.
- The default session name becomes `arun-uto-<ts>`, and the metadata tier, the `ps` TIER column and the banner all show `uto`.

## 3. `patch_baseline.py`

```python
#!/usr/bin/env python3
"""patch_baseline.py - move the atools CODE baseline statements to 2acaf3c / v0.1.7.

Run from the repository root (~/atools). Idempotent. Touches only:
  docs/plan/actl_Build_Plan-Stages0to2_addendum.md
  src/actl/INTERFACES.md
"""
import sys
from pathlib import Path

COMMIT = "2acaf3c"
VERSION = "v0.1.7"  # ctx_baseline.txt: "2acaf3c VERSION=v0.1.7"
TODAY = "2026-10-19"

ADDENDUM = "docs/plan/actl_Build_Plan-Stages0to2_addendum.md"
INTERFACES = "src/actl/INTERFACES.md"

NEW_BASELINE_LINE = f"Baseline: `atools` commit `{COMMIT}`, `VERSION` `{VERSION}`"
REVISION = (
    f"Revision note: {TODAY} baseline header moved to {COMMIT} / {VERSION}; "
    "no interface changed; Owner approval required (PB-4)."
)

EDITS = [
    {
        "id": "A1",
        "path": ADDENDUM,
        "old": "**Baseline:** `atools` `main` at `4221952`, `VERSION` v0.1.4 (audit runner `4da9394`;",
        "new": f"**Baseline:** `atools` `main` at `{COMMIT}`, `VERSION` {VERSION} (audit runner `4da9394`;",
        "grep": f"grep -n '4221952' {ADDENDUM}",
    },
    {
        "id": "A2",
        "path": ADDENDUM,
        "old": "Baseline is `4221952`, `VERSION` v0.1.4 (modular audit runner adopted in `4da9394`,",
        "new": f"Baseline is `{COMMIT}`, `VERSION` {VERSION} (modular audit runner adopted in `4da9394`,",
        "grep": f"grep -n 'Baseline is' {ADDENDUM}",
    },
    {
        "id": "B1",
        "path": INTERFACES,
        "old": "Baseline: `atools` commit `64d0980`, `VERSION` `v0.1.4`",
        "new": NEW_BASELINE_LINE,
        "grep": f"grep -n 'Baseline:' {INTERFACES}",
    },
    {
        "id": "B2",
        "path": INTERFACES,
        "old": NEW_BASELINE_LINE,
        "new": NEW_BASELINE_LINE + "\n" + REVISION,
        "marker": REVISION,
        "grep": f"grep -n 'Baseline:\\|Revision note' {INTERFACES}",
    },
]


def main() -> int:
    if not Path(".git").exists():
        print("ERROR: run from the repository root (no .git in the current directory)", file=sys.stderr)
        return 2

    state = {}  # path -> [original_text, current_text], or None when the file is missing
    skipped = 0

    for e in EDITS:
        label = f"[{e['id']}] {e['path']}"
        if e["path"] not in state:
            p = Path(e["path"])
            if p.is_file():
                text = p.read_bytes().decode("utf-8")
                state[e["path"]] = [text, text]
            else:
                state[e["path"]] = None
        entry = state[e["path"]]
        if entry is None:
            print(f"{label}: SKIPPED (file not found) -> run: {e['grep']}")
            skipped += 1
            continue

        cur = entry[1]
        nl = "\r\n" if "\r\n" in cur else "\n"
        old = e["old"].replace("\n", nl)
        new = e["new"].replace("\n", nl)
        marker = e.get("marker", e["new"]).replace("\n", nl)

        if marker in cur:
            print(f"{label}: ok (already applied)")
        elif cur.count(old) == 1:
            entry[1] = cur.replace(old, new, 1)
            print(f"{label}: ok")
        else:
            print(f"{label}: SKIPPED (anchor found {cur.count(old)} times, expected 1) -> run: {e['grep']}")
            skipped += 1

    written = []
    for path, entry in state.items():
        if entry is not None and entry[1] != entry[0]:
            Path(path).write_bytes(entry[1].encode("utf-8"))
            written.append(path)
    print("files written: " + (", ".join(written) if written else "none"))

    print("Not patched (schedule/other WI): docs/guide/actl_Guide.md, docs/plan/actl_Build_Plan-Stages0to2.md, Handoff Prompts.")
    print(r"  check: grep -nE '4221952|64d0980|v0\.1\.[0-9]+' docs/guide/*.md docs/plan/*.md")
    return 1 if skipped else 0


if __name__ == "__main__":
    sys.exit(main())
```

**Not patched (schedule/other WI).**
- **Guide.** `docs/guide/actl_Guide.md` header: "**Baseline:** `atools` `main` at `4221952` (`VERSION` v0.1.4), which adds…". It is updated on the guide §12 schedule.
- **Core document.** The audit counts "at `4221952`: 49 checks pass, 18 are planned SKIPs, 2 warn" are a measurement at that commit, so they are historical. The "Existing item (v0.1.0)" header is also historical.
- **Addendum S0-R1.** "`VERSION` (expected `v0.1.4` or later)" is a floor, so I left it. The addendum's "Revision: Wednesday, October 14, 2026" date is also unchanged, since you did not ask for it.
- **Handoff Prompts.** Not in the attachment or in ctx_baseline's grep, so I cannot list its lines. The script prints the grep command.

## 4. Not verified / not run

I ran nothing: no tools, no git, no grep, and not the script (checked by reading only). No suite (E1–E10, engines, persistence, audit) was executed. I did not verify any of the following:
- `schemas/*.json`, the fixtures and the guide, which are not in the attachment.
- Whether `docs/plan/INTERFACES_S1_S2.md` exists.
- Whether `proof/out` is git-ignored.
- My guess that INTERFACES was drafted against pre-WI-DOCS-3 addendum text (F-03).
- That the code at 558b23e equals 2acaf3c. I am relying on the two "docs(...)" subjects only.
- `proof/run_suite_session_persistence.sh` in atools_code_facts.txt shows literal `\vert{}` where a pipe belongs. This is probably an export artifact, since you reported 11/11 passing.

Please run these (max 5):
1. `git diff --stat 2acaf3c 558b23e -- . ':!docs' ':!src/actl'` (expect empty) and `git show 2acaf3c:VERSION` (expect `v0.1.7`)
2. `grep -n 'EXIT_OK\|EXIT_RED\|EXIT_HALT\|INTERFACES_S1_S2' src/actl/INTERFACES.md; ls docs/plan`
3. `grep -nE '4221952|64d0980|v0\.1\.[0-9]+' docs/guide/*.md docs/plan/*Handoff* 2>/dev/null`
4. `grep -n 'vert' proof/run_suite_session_persistence.sh; git check-ignore -v proof/out`
5. `git diff dff10d3~1 dff10d3 -- docs/plan/actl_Build_Plan-Stages0to2_addendum.md | grep -n 'S0-R6\|S0-R7\|S2-R8'` (does the pre-tightening text match INTERFACES' A-1/A-3/A-4?)

## 5. Self-check

| Item | Status | Why |
|---|---|---|
| Model and family on the first line | done | |
| Task 1: verdict, table, all 20 checks addressed | done | Check 8 not found in the attachment (stated). |
| Evidence by section plus quote, no line numbers | done | |
| Not-verified list stated | done | |
| Patch anchors copied verbatim; VERSION taken from ctx_baseline | done | `v0.1.7` for 2acaf3c. |
| Historical, ancestor, audit-runner (`4da9394`) and D-n text untouched | done | |
| Idempotence, write-only-on-change, no other files | done | By construction only; not executed. |
| Guide, core and Handoff Prompts untouched, lines listed | done | Handoff lines need command 3. |
| Task 3 per-anchor table; addendum patched only if wrong | done | No anchor was wrong, so no addendum edit. |
| `arouter` `auto` side check | done | Read-only, as requested. |
| E1–E10 and S0-R16 item 6 confirmed | done by reading | Not run. |
| Mechanical verification (grep, JSON key check, script run) | not done | No execution environment used. |
| 68-entry count | done manually | No mechanical check. |
