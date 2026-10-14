# Global Agent Operating Guidelines

## Git Safety & Branch Hygiene
1. **Branch Protection:** NEVER commit directly to `main`, `master`, or release branches. Always verify that `git branch --show-current` begins with `wip/` before staging or committing.
2. **Feature Isolation:** All experiments, patches, and refactors MUST occur on an isolated `wip/*` branch. If on a protected branch, checkout a wip branch first.
3. **No Upstream Mutations:** NEVER execute `git push` or modify remote refs under any circumstances. Remote synchronization is strictly reserved for human operators.
4. **Assertion-Gated Exit:** Never commit until all project tests/proofs pass. Conclude every completed run with `git status`.
5. **Work Item Tagging:** All commit messages MUST include a work item tag in the form `(WI-<id>)` (e.g., `git commit -m "fix(core): update boundary assertions (WI-101)"`).
