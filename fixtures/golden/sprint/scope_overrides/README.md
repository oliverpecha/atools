# scope_overrides
Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
If `scope_overrides/<case>.txt` exists, the G3/G4 evaluation of that case uses it instead of `oracle/scope.txt`
(only `bad_testcount` needs it: G4 applies only when a `test/` file is thawed by a literal ALLOW). See spec-S0.md SA-6.
