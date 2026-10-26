# Runbook: Layout transition, part A4 (oracle defects found by part B) - workstream `LT-A4`

- **Branch / worktree:** create `wip/layout-a4` in `~/atools-lt-a4` from `wip/layout-int` at `68e2e96`. Work only there. No push, no merge, no `--no-verify`, no `rm` of tracked files. Part B code is NOT in this branch; do not look for it.
- **Why:** part B (`wip/layout-b`) is green except four oracle defects and two stale INTERFACES statements, all introduced or missed in part A. Evidence is the Owner-pasted code and `/tmp/lt-b-report.md` (TD-1 to TD-4).
- **Boundary:** allowed `test/actl/`, `proof/`, `docs/plan/spec-S0.md`, `src/actl/INTERFACES.md`. Forbidden: `src/actl/*.py`, `schemas/`, `fixtures/`, `tools/`, `hooks/`, `rules/`, `audit/`, `engines/`, `bin/`, `src/router`, `src/sessions`, `src/core`, all other docs. Tests/proofs: `(WI-S0-PROOF)`; spec-S0.md: `(WI-S0-SPEC)`; INTERFACES.md: `(WI-IFACE)`. One tag and one area per commit. Hook format: `type(scope): summary (WI-tag)`, `Why:` (bare SHAs), `What changed:` with `- <file>: <change>` bullets, `Result:` with metrics. Run every command with `</dev/null`.
- **Rule:** every fix keeps the assertion at least as strong. No skip, xfail, loosened match or deleted case.

## Tasks (verify each defect first with `sed -n`/`git show main:<file>` and keep the raw output)

**D1 (TD-1)** `test/actl/test_p03_layout.py`, test `test_paths_match_design_section_1_5`, the no-tag line: the test on `main` expected the no-tag workspace at `workspaces/<name>` (no tag). Part A wrongly inserted `TAG`. Layout cannot know a tag it was not given. Required expectation, per INTERFACES 1.1: `r / "sprints" / "target-repo" / "workspaces" / "verify-implementer"`. Keep the tagged assertion unchanged. Align the S0-R3.2 text in `docs/plan/spec-S0.md` (and nothing else) so that it states both forms: with tag `sprints/{repo}/{tag}/workspaces/{name}`, without tag `sprints/{repo}/workspaces/{name}`.

**D2 (TD-2)** same file, `test_wrong_repo_guard_rejects_mismatch`: a `dog_app` Layout reads `sprints/dog_app/...`, so it never sees a state file written under `cat_app`. Fix: build `lay_dog`, call `lay_dog.ensure_sprint_tree(TAG)`, write the state dict with `"repo": "cat_app"` into `lay_dog.state_file(TAG)`, then `seq.read_state(lay_dog, TAG)` must raise `StateIntegrityError`. Add a positive control in the same test: the same dict with `"repo": "dog_app"` written to the same path reads without error.

**D3 (TD-3)** `test/actl/test_s0_gap_layout.py::test_layout_rejects_symlink_traversal`: the test plants the symlink under the old `$ACTL_ROOT/workspaces/`. Plant it at `<root>/sprints/<lay.repo>/workspaces/escape` instead (create parents), keep `lay.workspace("escape")` and the `pytest.raises(ValueError, match=...)` unchanged. Then grep `test/actl proof` for any other test that creates a bare `workspaces`, `actl-repo`, `handoff`, `homes` directory under a Layout root (pattern `/ ?['"]?(workspaces|handoff|homes|actl-repo)['"]?`) and report each hit: fix or justify.

**D4 (TD-4)** `test/actl/test_s0_gap_sprint_initial_state.py::test_create_sprint_exact_initial_state`: the `expected` dict must include `"repo": lay.repo` (L-10: `state.json` records the repo). Keep `st == expected` and the key-set assertion.

**D5 INTERFACES stale statements** (`src/actl/INTERFACES.md`, `WI-IFACE`): (a) the `ensure_base_tree` side-effects text must not say it writes `profiles/README.md`; state that `actl init` writes it (ratified decision 3, L-8). (b) Find the sentence in the `sprint-proposal` description that says it forbids `repo` (`git grep -n -i 'repo' src/actl/INTERFACES.md` around the sprint-proposal section and the `interfaces.json` block) and make it say `repo` is optional and not rejected (ratified decision 4). Keep the fenced `interfaces.json` block consistent with the prose.

**D6 Re-pin (last commit, `WI-S0-PROOF`).** `proof/stage0/P-S0-02.sh` pins the changed test blobs and INTERFACES.md in two places for INTERFACES: the case line in `is_authorized_pb2_modification` AND the `grep -q '<prefix>'` substring in `is_allowed_modification`. Update both from the new `git hash-object` values, with an idempotent python script printing `ok`/`SKIPPED` per edit and the marker `# LT-A4 pin refresh applied`.

## Delivery gate (paste raw output into `/tmp/lt-a4-report.md`, not committed)

1. `git merge-base --is-ancestor 68e2e96 HEAD` exits 0; new commits only; one valid tag each; hook accepted them.
2. `git diff --name-only 68e2e96..HEAD` lists only `test/actl/*`, `proof/stage0/P-S0-02.sh`, `docs/plan/spec-S0.md`, `src/actl/INTERFACES.md`; forbidden-path count 0.
3. Weakening check: per touched test file, counts of removed vs added lines containing `assert`, `pytest.raises`, `parametrize`, `skip`, `xfail` (no `skip`/`xfail` added; no `assert` or `raises` net loss).
4. `bash proof/run_suite_actl_s0.sh`: exit 1, 0 Environment, the same 10 reds as before (P-S0-03, -04, -05, -06, -08, -09, -14, -26, -29, -30); P-S0-02 passes.
5. `bash proof/run_suite_exit_code.sh`, `bash proof/stage0/P-S0-27.sh`, `proof/stage0/golden_selfcheck.sh`, `proof/stage0/selfcheck_mutations.sh` exit 0 (mutants still 23 or more). Audit `--cursor` shows 0 failed.
6. The D3 grep output with a justification for every hit; `git status --short` empty. Then stop.
