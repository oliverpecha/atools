# oracle-critique.md
Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude

Audit of spec-001 and solution_key.patch (golden fixture; hand-written, not a model output).

## Findings
- R1 lists "avatar" but `01_public.sh` deliberately does not assert the avatar value. `mutants/avatar_drop.patch`
  (sets avatar to null) therefore SURVIVES. This is intentional: the fixture needs one known survivor so Stage 3 can
  exercise `diagnostic_case = pure_oracle_failure` and the `waive_mutant` path. coverage.md maps it to `01_public.sh`
  (where a strong oracle would kill it), so the mapping is well-formed while the kill does not happen.
- `photo_count` exactness is checked only by `probe.sh` (recomputed from raw data); `photo_count_off.patch` is killed by the probe alone.
- R2 uses a raw-payload sentinel scan, so renamed keys (`contact`) are caught.
- R3 also asserts that no owner name or bio leaks in the 404 body.

## Residual risk
Avatar correctness is unverified by the oracle. Accepting this risk requires a `waive_mutant` resolution.
