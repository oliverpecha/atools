# Stage 0 Gate D Independent Review Handoff

## 1. Primary Goal
Execute the **Gate D Independent Audit & Sign-Off** for Stage 0 on repository `atools`. The objective is to verify that the integrated Stage 0 foundation (`wip/stage0-integration`) satisfies all design contracts, interface freezes, deterministic fixture requirements, and proof suites before merging into `main` and beginning Stage 1.

- **Repository Root:** `/root/atools`
- **Target Branch:** `wip/stage0-integration`
- **Pinned HEAD Commit:** `7e92d09` (`fix(proof): restore golden target-repo and patches to preserve base_sha (WI-S0-PROOF)`)
- **Working Tree State:** Clean (0 unstaged, 0 untracked).

---

## 2. Review Bundle & Files Saved in `/home/syncer/Sync/`

All review materials and proof artifacts have been compiled to `/home/syncer/Sync/gate_d/`:

| Artifact Path | Size / Lines | Purpose |
| :--- | :--- | :--- |
| `/home/syncer/Sync/gate_d/in_D_stage0.txt` | ~678 KB | **Primary Gate D Package:** Consolidated specification, design, interface definitions, vacuity matrix, schemas, and full source code. |
| `/home/syncer/Sync/gate_d/mutation_report.json` | 27 mutants | Results from `mutate_fast.py` (14 killed, 13 survived). |
| `/home/syncer/Sync/gate_d/d_stat.txt` | Diffstat | Cumulative diffstat between baseline `e413125` and HEAD `7e92d09`. |
| `/home/syncer/Sync/gate_d/d_pinned_changes.diff` | Diff | Changes to pinned proof suites, golden fixtures, and `INTERFACES.md`. |
| `/home/syncer/Sync/gate_d/d_process.diff` | Diff | Router process persistence and `.boot.sh` cleanup changes (`src/router/process.py`). |
| `/home/syncer/Sync/gate_d/SURVIVOR_ANALYSIS.md` | Audit Notes | Line-by-line semantic justification for why the 13 mutation survivors are benign. |

---

## 3. Core Files to Review in Repository

1. **Interface Boundaries & Invariants:**
   - `src/actl/INTERFACES.md` — Frozen contracts for Stage 0-2 (exit codes 0..255, `owner_review_triggers` aligned with Design 6.3).
   - `docs/plan/spec-S0.md` — Consolidated single source of truth (folded rulings C-1..C-3, F-11..F-27).
   - `proof/stage0/VACUITY_MATRIX.md` — Mapping of specifications to test coverage and vacuity proofs.

2. **Core Implementation Modules:**
   - `src/actl/schemas.py` & `schemas/*.json` — Schema validation with `\Z` string anchors and trigger constraints.
   - `src/actl/cli.py` — CLI dispatch mapping `SystemExit(None)` to exit code 0.
   - `src/actl/next.py` — Dynamic rule signature inspection and `session_probe` parameter handling.
   - `src/router/process.py` — Background runner metadata lifecycle and `.boot.sh` unlink operations.

3. **Deterministic Fixture Baseline:**
   - `fixtures/golden/expected.d/base.json` — Verified against target repository `base_sha`: `01d880bc3176cdd8f31d72e67bb3eba54d634378`.
   - `hooks/commit-msg` — Live hook reading `$STRIPPED` directly to avoid `fix(...)` deadlocks.

---

## 4. Verification Commands for the Incoming Agent

Run these commands inside `/root/atools` to verify repository integrity independently:

```bash
cd /root/atools

# 1. Verify working directory is pristine and at commit 7e92d09
git status --short
git rev-parse HEAD

# 2. Run full pytest suite (289 tests)
export PYTHONPATH=src
python3 -m pytest test/actl/ -q

# 3. Run Stage 0 Gate Proofs (18 passed, 0 failed)
bash proof/run_suite_actl_s0.sh

# 4. Run Router Process & Exit Code Proofs (10 passed, 0 failed)
bash proof/run_suite_exit_code.sh

# 5. Run Commit Message Governance Suite (16 passed, 0 failed)
bash proof/run_suite_commit_msg.sh
5. Exit Criteria to Close Milestone
[x] All 289 unit tests pass in test/actl/.

[x] 18/18 Stage 0 proof gates pass (proof/run_suite_actl_s0.sh).

[x] 10/10 Router exit code proofs pass (proof/run_suite_exit_code.sh).

[x] 16/16 Commit-msg policy checks pass (proof/run_suite_commit_msg.sh).

[x] Gate D package assembled at /home/syncer/Sync/gate_d/in_D_stage0.txt.

[ ] Incoming reviewer conducts independent audit of in_D_stage0.txt.

[ ] Merge wip/stage0-integration into main or cut tag stage-0-verified.
