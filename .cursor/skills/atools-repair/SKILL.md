# Skill: atools Eval-Driven Repair

## Objective
Execute iterative code changes against deterministic test suites without user intervention.

## Operational Protocol
1. Read the provided specification and implementation requirements.
2. NEVER edit, create, modify or mock oracle files, proofs or test fixtures.
3. All progress must be staged and committed on an isolated wip/* branch.
4. Commit messages must be tagged with a valid (WI-<id>) work item identifier.
5. Execute the designated test suite directly via bash or python runner without modifying file permissions.
6. If failures occur, inspect test logs, apply minimal surgical fixes, and re-run.
7. Once all checks output PASS, verify branch isolation with git status and conclude.
