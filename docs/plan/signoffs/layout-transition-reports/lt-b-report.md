# LT-B Report — Layout transition part B (implementation)

Branch: `wip/layout-b` in `~/atools-lt-b`
Base: `68e2e96` (WI-DOCS-18 integration merge of part A)
Memo: `docs/plan/layout-transition-memo.md`
Model: Composer via Cursor auto (preferred family: Grok through Cursor auto; this session ran as Composer/Auto)

Stopped after this report per runbook. Did not run mutation harness beyond `selfcheck_mutations.sh`, end-to-end demo, or doctor refresh.

---

## Delivery gates (raw)

### 1. Ancestor + commits

```
$ git merge-base --is-ancestor 68e2e96 HEAD; echo $?
0

$ git log --format='%h %s' 68e2e96..HEAD
118d695 fix(actl): chmod intermediate repo sprint path segments (WI-S0-R3)
d383790 fix(actl): record repo in sprint/state and write profiles README (WI-S0-R4)
b20ff27 fix(actl): reconstruct verification/qualification and mailboxes paths (WI-S0-R5)
81456cc fix(actl): adopt records/sprints/mailboxes/profiles layout (WI-S0-R3)
a62ae52 fix(actl): rename verification/qualification schemas and kinds (WI-S0-R7)
```

Each commit has exactly one WI tag: R7, R3, R5, R4, R3. Only new commits on top of 68e2e96.

### 2. PB-2 immutability

```
$ git diff --name-only 68e2e96..HEAD -- proof fixtures test/actl src/actl/INTERFACES.md tools
(empty)

$ git diff --name-only 68e2e96..HEAD
schemas/qualification.json
schemas/sprint-proposal.json
schemas/sprint.json
schemas/state.json
schemas/verification.json
src/actl/cmd_init.py
src/actl/ids.py
src/actl/layout.py
src/actl/schemas.py
src/actl/seq.py
src/actl/sprint.py
```

(Also schema renames: `ev.json`→`verification.json`, `qual.json`→`qualification.json` via `git mv`.)

### 3. pytest

```
4 failed, 813 passed in 121.79s
FAILED test/actl/test_p03_layout.py::test_paths_match_design_section_1_5
FAILED test/actl/test_p03_layout.py::test_wrong_repo_guard_rejects_mismatch
FAILED test/actl/test_s0_gap_layout.py::test_layout_rejects_symlink_traversal
FAILED test/actl/test_s0_gap_sprint_initial_state.py::test_create_sprint_exact_initial_state
```

**Not fully green.** Blocked by four test defects (below). Per runbook: do not edit tests, skip them, or work around them in code.

### 4. proof/run_suite_actl_s0.sh

```
Suite Summary: 17 Passed, 2 Failed, 0 Environment
```

Fails: P-S0-03_layout (`workspace(name) wrong`), P-S0-30_gap_proofs (same four pytest failures). Exit non-zero.

### 5. Other gate suites

```
proof/run_suite_exit_code.sh              Suite Summary: 10 Passed, 0 Failed   EXIT=0
proof/run_suite_commit_msg.sh             --- Suite Results: 16 passed, 0 failed --- EXIT=0
proof/run_suite_engines.sh                Suite Summary: 5 Passed, 0 Failed    EXIT=0
proof/run_suite_session_persistence.sh    Suite Summary: 6 Passed,0 Failed     EXIT=0
bash proof/stage0/P-S0-27.sh              OK: P-S0-27 suite conforms           EXIT=0
bash proof/stage0/golden_selfcheck.sh     golden_selfcheck: ALL CHECKS PASSED  EXIT=0
bash proof/stage0/selfcheck_mutations.sh  selfcheck_mutations: control green, all 23 planted defects detected  EXIT=0
```

### 6. Audit

```
$ bash audit/atools-compliance_audit.sh --cursor | tail -2
Audit Verdict: 49 passed, 0 failed, 18 skipped, 2 warnings (profile=dev, adapter=cursor)
```

### 7. git status

```
$ git status --short
(empty)
```

---

## B0 Baseline

Saved under `/tmp/lt-b-baseline/`.

- `python3 -m pytest test/actl -q --tb=line` → **157 failed, 660 passed**
- `bash proof/run_suite_actl_s0.sh` → **9 Passed, 10 Failed**

Matches runbook expectation.

---

## B1 Inventory

### Old names (`actl-repo|handoff|homes|target_repo|"ev"|"qual"|ev-|qual-|ev.json|qual.json`)

65 hits saved to `/tmp/lt-b-inventory/b1-old-names.txt` (pre-edit). Covered `src/actl`, `schemas`, `config`, `bin`, `install.sh`.

Notable pre-edit clusters: `schemas/ev.json`, `schemas/qual.json`, `layout.py` (`actl_repo`, `handoff`, `homes`), `ids.py`/`schemas.py` kinds `ev`/`qual`, `sprint.py` `handoff_dir`, `seq.py` `qual-`/`ev-`/`handoff`.

### PB-2 spelling hits in hooks / rules / audit / engines

12 hits in `/tmp/lt-b-inventory/b1-pb2.txt` (not edited):

```
audit/README.md:41: ... forbid modifying oracle/proof files.
audit/atools-compliance_audit.sh:26:  --self-test ... fixtures
audit/atools-compliance_audit.sh:94:2. NEVER edit, create or mock oracle files, proofs or test fixtures.
audit/atools-compliance_audit.sh:155:  mut_proof_chmod() { echo 'chmod +x proof/*.sh' ...
audit/atools-compliance_audit.sh:166:  expect_fail SKILL-10 "worker doc chmods proof files" ...
audit/atools-compliance_audit.sh:310:  check_content SKILL-06 "Worker instructions forbid editing oracle/proofs" ...
audit/atools-compliance_audit.sh:314:  check_absent SKILL-10 "Worker instructions do not chmod proof files" ...
hooks/commit-msg:64-65: allowed types include `proof`
hooks/commit-msg:70: Scope example includes `proof`
hooks/commit-msg:155: Result: ... proof suite
rules/git-safety.md:7: Never commit until all project tests/proofs pass
```

No hits under `engines/`. Owner/Vela decide any PB-2 list updates separately.

### B7 post-edit sweep (`src/actl schemas`)

Remaining hits are allowed:

- `schemas/contract.json` `qual` property (Owner: keep contract field name `qual`)
- `INTERFACES.md` historical note about `handoff_dir` → `mailboxes_dir`
- False positives on `git rev-parse` matching `ev-`/`qual-` pattern fragments

---

## Commits

| SHA | Tag | Summary |
|-----|-----|---------|
| a62ae52 | WI-S0-R7 | Rename verification/qualification schemas and kinds |
| 81456cc | WI-S0-R3 | Layout records/sprints/mailboxes/profiles |
| b20ff27 | WI-S0-R5 | Reconstruct new artifact names and mailbox/workspace paths |
| d383790 | WI-S0-R4 | repo in state/sprint.toml, mailboxes_dir, init --name + profiles README |
| 118d695 | WI-S0-R3 | chmod intermediate records/<repo> and sprints/<repo> segments |

---

## Test defects (stopped; did not edit oracles)

Per runbook: if a test contradicts the memo, stop and report; do not edit the test or work around it.

### TD-1 — `test_p03_layout.py::test_paths_match_design_section_1_5`

- **Line:** expects `lay.workspace("verify-implementer")` (no tag) == `.../sprints/target-repo/{TAG}/workspaces/verify-implementer`
- **Memo:** section 2 tree places `workspaces/` under `sprints/<repo>/<tag>/` only when a tag exists; no rule that a no-tag call invents `TAG`
- **INTERFACES.md §1.1:** no-tag form is `$ACTL_ROOT/sprints/{repo}/workspaces/{name}` (no tag segment)
- **Implementation:** follows INTERFACES (no-tag → `sprints/<repo>/workspaces/<name>`)
- **Why unfixable without editing the oracle:** Layout cannot know the test helper's `TAG` when `tag` is omitted

### TD-2 — `test_p03_layout.py::test_wrong_repo_guard_rejects_mismatch`

- **Lines:** writes state under `Layout(repo="cat_app").state_file(TAG)`, then `read_state(Layout(repo="dog_app"), TAG)`
- **Memo L-10 / section 2–3:** paths are repo-scoped (`sprints/<repo>/<tag>/runs/state.json`)
- **Observed:** `FileNotFoundError` (dog_app state file was never created), not `StateIntegrityError`
- **Why unfixable without editing the oracle:** a wrong-repo guard can only fire on a state file that exists for that Layout; the test never writes into `dog_app`'s tree. Correct shape would write mismatched `repo` into `lay_dog.state_file(TAG)` then read with `lay_dog`

### TD-3 — `test_s0_gap_layout.py::test_layout_rejects_symlink_traversal`

- **Lines:** plants symlink at `$ACTL_ROOT/workspaces/escape` (old tree) and calls `lay.workspace("escape")`
- **Memo section 3:** `workspaces/` → `sprints/<repo>/<tag>/workspaces/` (and no-tag → `sprints/<repo>/workspaces/`)
- **Observed:** no ValueError; new path does not traverse the planted symlink
- **Why unfixable without editing the oracle:** test still uses the pre-transition workspace root

### TD-4 — `test_s0_gap_sprint_initial_state.py::test_create_sprint_exact_initial_state`

- **Lines:** `assert st == expected` where `expected` omits `repo`
- **Memo L-10 / S0-R4.5:** `state.json` must record `repo = layout.repo`
- **Observed:** left contains `'repo': 'target-repo'`
- **Why unfixable without editing the oracle:** omitting `repo` from create_sprint would violate the locked memo

---

## Ambiguity notes (non-blocking except via TD-1)

- INTERFACES §1.1 `ensure_base_tree` still mentions writing `profiles/README.md`; Owner ratification + memo L-8 + tests require init-only. Implementation follows L-8 / tests.
- INTERFACES §3.2 still says sprint-proposal forbids `repo`; Owner ratification requires it does not reject. Schema adds optional `repo`.
- S0-R3.2 formula writes `workspace(name, tag=None)=sprints/{repo}/{tag}/workspaces/{name}` which conflicts with INTERFACES no-tag branch and with TD-1.

---

## Verdict

Implementation of L-1–L-11 / S0-R3/R4/R5/R7 is on `wip/layout-b` in allowed paths only, with one WI tag per commit. PB-2 clean. Audit 0 failed. Mutations still 23. **Delivery gate 3 (pytest fully green) and gate 4 (S0 suite 19 passed) are blocked by four part-A test defects listed above.** Stopped here for Owner/Vela to fix the oracles; no further code workarounds.
