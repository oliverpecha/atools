# Global Agent Operating Guidelines

## Git Safety & Branch Hygiene
1. **Branch Protection:** NEVER commit directly to `main`, `master`, or release branches. Always verify that `git branch --show-current` begins with `wip/` before staging or committing.
2. **Feature Isolation:** All experiments, patches, and refactors MUST occur on an isolated `wip/*` branch. If on a protected branch, checkout a wip branch first.
3. **No Upstream Mutations:** NEVER execute `git push` or modify remote refs under any circumstances. Remote synchronization is strictly reserved for human operators.
4. **Assertion-Gated Exit:** Never commit until all project tests/proofs pass. Conclude every completed run with `git status`.
5. **Commit Protocol & Work Item Tagging:** All commit messages MUST end the subject line with `(WI-<id>)` and pass the mechanical `commit-msg` hook (`<type>(<scope>): <summary> (WI-<id>)` with `Why:`, `What changed:`, and `Result:` sections). NEVER bypass hooks with `--no-verify` or `-n`, and NEVER modify `.git/hooks` or `core.hooksPath`.
6. **Multi-Worktree Isolation:** NEVER checkout, rebase, or mutate a branch checked out in another linked worktree. Cross-worktree integration is performed exclusively via `--no-ff` merge gates on the integration branch.
