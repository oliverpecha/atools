# scope_overrides
Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
If `scope_overrides/<case>.txt` exists, the G3/G4 evaluation of that case uses it instead of `oracle/scope.txt`
(only `bad_testcount` needs it: G4 applies only when a `test/` file is thawed by a literal ALLOW). See spec-S0.md SA-6.
