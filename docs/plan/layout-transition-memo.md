# Memo v3: actl directory upgrades (layout, names, courier, profiles)

Date: 2026-10-25. Audience: the amendment agents and the cross-family reviewer. Approval route: Owner, PB-4 and D-28 (approved by the Owner on 2026-10-25, to be logged when the whole transition is pushed to main).
Status: every item is LOCKED unless marked PROPOSAL. The Owner confirmed the `closeout.md` contents on 2026-10-25. This memo covers names, lifetimes and policy. Code and scripts are for the amendment agents to resolve.
Verified 2026-10-25: the Stage 0 implementation is merged on `main` (`src/actl/` contains `layout.py`, `ids.py`, `seq.py`, `sprint.py`, `schemas.py`, `doctor.py` and the rest) and the compliance audit is green (49 passed, 0 failed, 18 skipped, 2 warnings). Commit 2bb1307 folded `spec-S0-rulings.md` into `spec-S0.md`, so the amendment edits `spec-S0.md`. The Stage 1 and Stage 2 specs and proofs are not authored yet, so they will be written against the new names. The amendment therefore has an authoring part (part A) and an implementation part (part B), see section 7.

## 1. Locked decisions

| ID | Decision |
|---|---|
| L-1 | Layout H1: one `ACTL_ROOT` with three lifetimes. `records/` is STORAGE (git, actl only). `sprints/` is TRANSIENT working memory, deleted after closeout. `profiles/` is PERSISTENT per-persona CLI state. `repos/` holds the target repositories. |
| L-2 | Names: `repos`, `records`, `sprints`, `mailboxes` (with `inbox`/`outbox`), `workspaces`, `profiles`, `tools`, `signoffs`. "Hand-off" stays the name of the act; `mailboxes/` is where it happens. |
| L-3 | Sprint closeout is "archive, then delete". Keep in `records/<repo>/<tag>/closeout/`: `sessions.tsv`, the final green verification receipt, the qualification receipt, and `closeout.md` (section 5). Toss logs, workspaces, mailboxes and raw turns. `closeout.md` lives in `records`, not in the target repo: the target repo is exported read-only to the persona accounts, and `closeout.md` names oracle-derived items (waived mutants, proof ids, tripwire hits), which Invariant P keeps inside the 700 `records` repo. |
| L-4 | Courier: Sync is a transport, not storage. One copy, moved not copied, every name UTC-stamped, one drawer per turn (section 4). |
| L-5 | Artifact renames: `ev-NNN.json` becomes `verification-NNN.json`; `qual-NNN.json` becomes `qualification-NNN.json`. The kinds are produced by `verify.py` and read by replay, reconstruct, escalation and `actl next`. |
| L-6 | `tools/` at the repo top level holds process scripts: `tools/mutate.py` (mutation harness, D-29) and `tools/unfiles.py` (retired when Stage 2 `actl unpack` lands). `tools/` joins the PB-2 immutable list. |
| L-7 | `docs/plan/signoffs/` holds records of judgment-based acceptances (independent challenge verdicts, Owner approvals). Mechanical acceptances leave only receipts. |
| L-8 | `profiles/<persona>` is the account's persistent state directory, and the account's `HOME` points to it. It holds login, CLI config, transcripts, installed copies of skills and rules, and the Architect's persistent thread. It does NOT hold persona instructions: prompts, skills and rules are versioned in the atools repo and delivered by `actl` each turn or installed at account creation. Verified on the VPS: a fresh empty `HOME` reports "Not logged in", so profiles must persist. `actl init` writes `profiles/README.md`. |
| L-9 | `ACTL_ROOT` is the only root name. The Design's `/srv/agent-graph` becomes an example value. Sprint tags keep the Design format `YYYY-MM-DD-slug` (hyphen). |
| L-10 | `Layout(root, repo="target-repo")`: one Layout per repository, so existing method signatures stay unchanged and the golden fixture works through the default. A `repo` field is recorded in `sprint.toml` and `state.json`. Every function that loads state checks it equals `layout.repo` and raises the existing integrity error (exit 3). One proof: "wrong-repo Layout rejected". The earlier narrower `Layout.target_repo(name)` amendment is superseded. |
| L-11 | Addendum open item O-16 (section 9.2) and the Stage 4 summary line (section 8.1): revisit `Layout(root, repo)` against an explicit `repo` argument at Stage 4, with the learnings gathered by then. Measured at decision time: 37 files under `test/actl`, `proof` and `fixtures` and 34 lines of `INTERFACES.md` mention tag-scoped functions. |

## 2. Example tree (three repositories)

```text
~/actl-graph/                              ACTL_ROOT
├── README.md
├── baseline.json
├── repos/                                 target repositories, written only by actl
│   ├── cat_app/   dog_app/   bird_app/
├── records/                               STORAGE: one git repo, actl only, chmod 700
│   └── cat_app/2026-10-25-add-whiskers/
│       ├── sprint.toml  spec-001.md  oracle-003/  contract-005.json  checklist.md
│       ├── architect_thread.jsonl  architect-notes.md      vault copy, recovery only
│       └── closeout/                      sessions.tsv, verification-NNN.json, qualification-NNN.json, closeout.md
├── sprints/                               TRANSIENT, deleted after closeout
│   └── cat_app/2026-10-25-add-whiskers/
│       ├── runs/                          state.json, sessions.tsv, receipts, turns/, logs/
│       ├── mailboxes/{architect,challenger,implementer,curator}/{inbox,outbox}
│       └── workspaces/                    implementer-006, architect-worktree, verify-* ...
└── profiles/                              PERSISTENT per persona
    ├── architect/  challenger/  curator/  implementer/
    └── README.md
```

Permissions model is unchanged: `records` is 700 actl:actl, mailboxes stay account-partitioned, workspaces stay 2770 per account. From Stage 4 the persona accounts need to reach `profiles/<persona>` through the parent directories of `ACTL_ROOT` (a shared group such as `cloners`).

## 3. Old to new

| Design / addendum / code today | New |
|---|---|
| `actl-repo/` | `records/` |
| `actl-repo/specs/<tag>/` (hashed artifacts) | `records/<repo>/<tag>/` |
| `actl-repo/specs/<tag>/runs/` | `sprints/<repo>/<tag>/runs/` |
| `handoff/<tag>/` | `sprints/<repo>/<tag>/mailboxes/` |
| `workspaces/` | `sprints/<repo>/<tag>/workspaces/` |
| `repos/target-repo` | `repos/<repo>` (default name `target-repo` kept for the golden fixture) |
| `homes/<role>`, `Layout.homes` | `profiles/<role>`, `Layout.profile` |
| `ev-NNN.json`, `schemas/ev.json` | `verification-NNN.json`, `schemas/verification.json` |
| `qual-NNN.json`, `schemas/qual.json` | `qualification-NNN.json`, `schemas/qualification.json` |

## 4. Courier specification

- `ACTL_COURIER_DIR` points at the courier root (VPS: `/home/syncer/Sync/courier`). If unset, `actl` writes only the ledger copy.
- Drawer name: `{stamp}__{repo}__{tag}__{role}-{n}__{purpose}`. `stamp` is UTC `YYYYMMDDTHHMMZ` taken from the bundle's creation time. `__` separates fields and is forbidden inside them. `role` is one of the four roles, `n` is the turn number, `purpose` comes from the fixed vocabulary (`architect-intake`, `challenger`, `architect-review`, `curator`).
- Drawer contents mirror the ledger turn folder `runs/turns/<role>-<n>/`: `bundle.txt` (written by `actl bundle`), `response.txt` (dropped by the Owner), optional `amend-N.txt`, `repair.txt`.
- Identity comes from the sentinel `ENDRESPONSE bundle=<hex8>` inside the response, not from file names. A reply in the wrong drawer fails with `EBUNDLEMISMATCH`.
- `actl unpack --drawer <path>` reads `response.txt`; if it is missing and exactly one other file besides `bundle.txt` exists, it uses that one. After success it moves the response into the ledger after a hash check and removes the empty drawer. After failure it adds `repair.txt` and keeps the drawer.
- Agents with file access put Owner-bound files only in the courier root, UTC-stamped, with no second copy. This paragraph goes into the COMMON BLOCK of the Handoff Prompts.
- Courier names are for the Owner's convenience only. Nothing in the parser depends on them.

## 5. `closeout.md` contents (LOCKED)

Generated deterministically by `actl` from state and receipts, not written by an LLM, so it can be regenerated. Markdown with a small machine-readable header. At most one page. The Owner may append a Notes paragraph.

1. Identity: repo, sprint tag, `base_sha`, contract hash and tag, final head SHA, merge ref, opened and closed dates, spec source.
2. Outcome: done, aborted or escalated; the final verification receipt id and result; whether a Live Run happened.
3. Effort: attempts used against budget per stage, epochs, `closures_submitted`, `hardcap_stripped`, token and cost totals from `sessions.tsv`, wall-clock.
4. Models: model and family per persona, and the same-family pairs disclosed under Invariant F.
5. Decisions and exceptions: escalations (id, trigger, action), waived mutants with the Owner countersignature, modified legacy tests, tripwire hits, halts.
6. Backlog items the Owner accepted from `backlog-proposal.md`.
7. Artifact index: hashes of the kept files, the contract and oracle manifest hashes, and counts of what was discarded.
8. Pointers to the related sign-off records.

Deferred by the Owner on 2026-10-25: a generated index `records/<repo>/closeouts.tsv`, one line per closed sprint. It is derivable from the `closeout.md` files, so it can be added later without migration.

## 6. `profiles/README.md` text

```markdown
# profiles/

One folder per persona account: architect, challenger, implementer, curator.
Each folder holds that persona's CLI state. The account's HOME points here.

Lives here: login and config, session store and transcripts, installed copies of
skills and rules, and the Architect's persistent thread.

Does not live here: the persona's instructions. System prompts, skills and rules are
versioned in the atools repo and delivered by actl on every turn, or installed into
the profile when the account is created. Nothing in a profile is authoritative:
deleting one loses memory, never policy.

Durable results are copied into records/ by actl. A profile is working memory, not an archive.
Empty until Stage 4, when real accounts exist.
```

## 7. Impact and process

Touched: Design section 1.5, section 4 naming and glossary; addendum S0-R3, S0-R4, S0-R5, S0-R7, S2-R1, S2-R2, S2-R4, S2-R9, plus O-16 and the Stage 4 summary; `spec-S0.md`; `INTERFACES.md` (Layout, artifact kinds, schema list, registry); tests such as `test_p03_layout.py`, `test_p05_seq.py`, `test_p06_reconstruct.py`, `test_p08_schemas.py`, `test_p15_expected.py`; proofs P-S0-03, P-S0-08, P-S0-26, P-S0-27; the golden fixtures; the implemented modules (`layout.py`, `ids.py`, `seq.py`, `sprint.py`, `schemas.py`, `doctor.py`, `cmd_init.py`, `cmd_sprint.py`) and `schemas/*.json`; the Handoff Prompts and the Guide; the PB-2 list (add `tools`); the pinned blob hashes in P-S0-02.

Because Stage 0 is already implemented, the amendment runs as a miniature stage:
1. Owner approval of this memo (PB-4, D-28), logged in the transition push.
2. Part A, authoring, one `wip` branch (runbook `docs/plan/runbooks/layout-transition-a-authoring.md`), tagged `WI-IFACE`, `WI-S0-SPEC` or `WI-S0-PROOF`: amend the Design, addendum, `spec-S0.md`, `INTERFACES.md`, tests, proofs and fixtures. Re-verify PB-1: the amended suites are red against the current code, the golden and mutation self-checks stay green, and nothing outside the amendment's scope turns red.
3. Cross-family delta review of that diff (D-28); the verdict is saved under `docs/plan/signoffs/`.
4. Part B, implementation, tagged `WI-S0-Rk` for the requirements touched: update the modules and schemas until the suites are green, with the pinned paths untouched (PB-2). Its runbook is written after the delta review.
5. Merge through PB-5 in one push, with the approval record `docs/plan/signoffs/layout-transition-owner-approval.md` and an Owner Amendment Note in `INTERFACES.md`.
6. Then author the Stage 1 and Stage 2 specs and proofs against the new layout, and dispatch their implementers.

## 8. Out of scope here

The closeout archiving command (Stage 4 `actl gc` and Stage 5), persona account creation and path permissions (Stage 4), disposable profiles for the leaf personas (shelved: it needs a Cursor API key), the arouter research notes (they stay in Sync as preliminary research), and deleting the two Sync reorg memos, which happens after the transition lands.

## 9. Open items

None. The `repo` guard in L-10 is confirmed by the Owner (2026-10-25). The `closeouts.tsv` index is deferred (section 5).
