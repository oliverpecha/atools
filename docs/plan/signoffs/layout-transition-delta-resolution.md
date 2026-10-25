# Layout transition delta resolution (LT-A2)

* Branch: `wip/layout-amend-a`
* Base reviewed: `738cd6b`
* Resolution head: see table (commits `738cd6b..HEAD`)
* Date (UTC): 2026-10-25
* Owner approval draft status: delta review verdict still **pending** (this record does not change that)

## DC-1 .. DC-14

| ID | Status | Commit(s) | Notes |
|---|---|---|---|
| DC-1 | FIXED | `b05757d`, `e3d0498` | Memo and LT-A runbook pin-attested; `tools/` pin-only (not glob-allowlisted); pins refreshed after later edits. |
| DC-2 | FIXED | `e3519e1` | INTERFACES prose and `interfaces.json`: `verification-*`, mailboxes inbox/outbox paths; `ev.*` identifiers renamed. |
| DC-3 | FIXED | `e3519e1` | Removed `O-17`; Layout property names listed under Proposed decisions only. |
| DC-4 | FIXED | `8f2ceda`, `da79a07` | `~architect` → `profiles/architect`; remaining Design file-name residues to L-5 names. |
| DC-5 | FIXED | `8f2ceda`, `da79a07` | Bare `qual`/`ev` receipt wording fixed in Design; remaining hits justified (schema keys, rename maps, Stage-1 shorthand, mutants). |
| DC-6 | PROPOSED-DECISION | `8f2ceda`, `4776395` | Default applied: JSON key `handoff_dir` → `mailboxes_dir` (spec, INTERFACES note, tests). Awaiting Owner ratification. |
| DC-7 | FIXED | `8f2ceda` | Profiles HOME restated (persistent, non-authoritative); mode aligned to 0755; outbox lock is the verification read-only surface. |
| DC-8 | FIXED | `8f2ceda` | Design `closeout.md` list matches memo §5 verbatim (`hardcap_stripped`). |
| DC-9 | FIXED | `4776395` | F006 pattern anchored to `records/`; negative bare-word self-test in `golden_selfcheck.sh`. |
| DC-10 | FIXED | `3b5af34` | COMMON BLOCK courier cut to memo §4 one-liner; mailboxes vs Sync drawers distinguished. |
| DC-11 | FIXED | `defd33c`, `3b5af34` | `tools/` added to every PB-2 immutable spelling in scope; hooks/rules/audit deferred to Part B. |
| DC-12 | FIXED | `4776395` | Mutants M19–M23 (kinds, dirs, records path, repo field); count 18 → 23. Unimplemented-rule mutants deferred to Part B (`tools/mutate.py`, D-29). |
| DC-13 | FIXED | (report) | Crash exception lines and new-rule test map recorded in `/tmp/lt-a2-report.md` (not committed). |
| DC-14 | PROPOSED-DECISION | `8f2ceda` | (a) `profiles/README.md` by `actl init` only (L-8). (b) `sprint-proposal` `repo` reject removed (memo does not support it). Mixed-area historical commits left as-is. |

## Proposed decisions (awaiting Owner ratification)

1. Rename JSON key `handoff_dir` → `mailboxes_dir`.
2. Profile directory mode 0755 (Design aligned to spec/tests; memo silent on mode).
3. `profiles/README.md` written by `actl init` only (not `ensure_base_tree`).
4. Do not make `sprint-proposal` reject `repo` unless the memo later says so.
5. Proposed Layout property names: `records`, `profile`, `mailboxes` (replacing `actl_repo` / handoff / homes accessors in Part B).
6. New mutants that require implementation code deferred to Part B gate (`tools/mutate.py`).
