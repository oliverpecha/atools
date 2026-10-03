# Skill: atools Eval-Driven Repair

## Objective
Execute iterative code changes against deterministic test suites without user intervention.

## Operational Protocol
1. Read the provided specification runbook (/tmp/Runbook_<title>.md).
2. Edit target implementation files within scope. Never touch out-of-scope files or immutable directories.
3. Make all test scripts executable (`chmod +x proof/*.sh`).
4. Execute `bash proof/run_suite_<title>.sh`.
5. If failures occur, inspect logs under `proof/out/`, apply minimal surgical fixes, and re-run.
6. Once all checks output PASS, run `git status` and conclude.
