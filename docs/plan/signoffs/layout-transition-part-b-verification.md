# Layout transition: part B verification record

Trust tags: [V] seen in raw terminal output pasted by the Owner, [R] reported by the Owner or by an agent report, [P] from the plan documents.
Date (UTC): 2026-10-26. Integration head before this record: 01827a2 (merge of part B 4bf1639 onto 2d65404).

## Gates [V]
- `python3 -m pytest test/actl -q`: 817 passed.
- `bash proof/run_suite_actl_s0.sh`: 19 passed, 0 failed, 0 environment (P-S0-02 included, default fork mode).
- `run_suite_exit_code`, `run_suite_commit_msg`, `run_suite_engines`, `run_suite_session_persistence`: exit 0. `P-S0-27`, `golden_selfcheck`: exit 0. `selfcheck_mutations`: all 23 planted defects detected.
- `audit/atools-compliance_audit.sh --cursor`: 49 passed, 0 failed, 18 skipped, 2 warnings.
- PB-2: `git diff --name-only 2d65404..HEAD -- proof fixtures test/actl src/actl/INTERFACES.md tools` was empty on the part B branch; part B changed only `src/actl/*.py` and `schemas/*.json`.

## Mutation re-run, D-29 [V]
- Seed 53 (used seeds: 7, 11, 23, 37, 41, 53), `python3 tools/mutate.py --seed 53 --only ids layout seq schemas sprint` on a clean committed tree at 4bf1639: total 58, killed 45, survived 3, invalid 10.
- `src/actl/ids.py:68` `split("_", 1)` to `2`: equivalent (EQ-B, S41-03): a valid tag has one underscore.
- `src/actl/seq.py:184` default `0` to `1` in `state.get("seq", 0)`: unreachable default, `read_state` validates against a schema that requires `seq`.
- `src/actl/sprint.py:227` `text=True` to `False`: only the return code and the truthiness of stdout are used.
- All three lines were last changed in Stage 0 commits (30b6ec6, 099244a), not in part B. Judgment by Vela from code excerpts.

## End-to-end demo [V]
- Scratch `ACTL_ROOT`, default repo name: `actl init` created `repos/target-repo` with `base_sha` set; `actl sprint new demo --json` returned `mailboxes_dir`, created `records/target-repo/2026-10-26_demo/sprint.toml` and `sprints/target-repo/2026-10-26_demo/{mailboxes/<4 roles>,runs/{logs,turns,sessions.tsv,state.json},workspaces}`.
- `profiles/{architect,challenger,curator,implementer}` and `profiles/README.md` exist. Modes: `records` 700, `sprints`, `repos`, `profiles` 755, README 644.
- `actl next --sprint` returned noop (exit 0). `actl doctor --refresh --json` exit 0 (version v0.1.8).
- Wrong-repo guard at library level: `StateIntegrityError: state.repo 'target-repo' != layout.repo 'dog_app'`. The CLI maps `StateIntegrityError` in `cli.py` (handler at line 58, `test_p11_cli.py` integrity mode); the literal exit value 3 was not read directly.

## Known limitations
- Only `actl init` takes `--name`. Other commands build `Layout()` with the default repo `target-repo` (`cli.py:52`), so `sprint new` after a named init exits 2 ("Target repo not initialized"). This is the repo-selection question deferred to Stage 4 by L-11 and O-16. [V]
- `proof/stage0/diff_equiv_seed11.py` still uses the legacy `ev` and `qual` names. No gate runs it and it must not be run after this transition. [V]
- `proof/stage0/SURVIVOR_ANALYSIS.md` keeps the pre-transition names as a historical record. [V]

## Models [R]
- Part A authoring: Gemini Flash 3.8 High until credits ran out, then Cursor auto (Owner: Grok); the audit header showed "default". Corrections A2, A3, A4: Cursor auto, family not recorded per session.
- Part B: Cursor auto; the agent report says "Composer".
- Delta reviewer: Claude Sonnet 5.5 High (Owner-reported), web chat, saw excerpts of the 356 KB bundle. No author, implementer or reviewer pair is known to share a family; the A2 to A4 models are unrecorded.
