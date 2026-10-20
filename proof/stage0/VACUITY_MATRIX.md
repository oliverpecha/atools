# VACUITY_MATRIX.md - D-20 three-stand-in review of the Stage 0 proofs
Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity

## How to read this
Stand-ins (addendum section 10, item 5): (a) empty module / missing symbols, (b) always-succeed stub (functions return success, empty or permissive values), (c) always-fail stub (functions raise or return failure). A proof passes the review when it is RED against every stand-in it should reject. A green result is correct only for the cells marked "by design".

Evidence labels: **ran** = executed in the authoring environment; **traced** = derived by reading the delivered proof code (no stand-in run yet); **pending** = the proof file is not part of Part 1.
Nothing in the "traced" columns has been executed against a generated stand-in tree. The generator and runner (`vacuity_matrix.sh`, stand-ins built from the 71-entry manifest) belong to Part 2; this table is the expected result they must reproduce.

## Matrix (pytest proofs; all `actl` imports happen inside tests, so an empty tree gives FAIL, not a collection error)
| Proof | (a) Empty / missing symbols | (b) Always-succeed stub | (c) Always-fail stub | Anti-vacuity mechanism |
|---|---|---|---|---|
| P-S0-01 doctor | RED: `FAIL: bin/actl is missing` (traced) | RED: stub prints `{}` / exit 0 -> key-set check; missing-`tmux` and missing-audit tests expect exit 4 (traced) | RED: exit 1 -> `doctor exited 1` (traced) | exact key sets, value checks against `git`, sentinel test for write-once, PATH without tmux |
| P-S0-02 additive | pending: red when no `src/actl/cli.py`/`bin/actl` (S0-R2.5) | pending: a diff-only script cannot be fooled by code stubs; it is red unless files exist and only allowed files changed | pending | positive-work assertion plus allow-list |
| P-S0-03 layout | RED: `module actl.layout cannot be imported` (traced) | RED: constant paths fail equality; no `ValueError` -> 10 traversal/role/name tests `DID NOT RAISE`; modes unset (traced) | RED for positive tests (paths, modes); the pure "must raise" tests pass by design because raising is what they ask for (traced) | `S_IMODE` under `umask 077`, full path table |
| P-S0-04 sprint | RED: `bin/actl is missing` (traced) | RED: `{}` JSON -> key check; bad slugs return 0 not 2 (traced) | RED: `init` fixture fails (traced) | byte-exact files, header, nothing created for bad slugs, duplicate untouched |
| P-S0-05 seq | RED: import failure (traced; a reference implementation passed 6 of these tests: **ran**) | RED: constant or per-process counter -> 50-process test finds duplicates; SIGKILL test needs persisted highwater (traced) | RED: first `reserve` raises (traced) | real processes, SIGKILL, highwater-vs-state |
| P-S0-06 reconstruct | RED: import failure (traced) | RED: hard-coded `7` fails the workspace (9), highwater (12) and handoff (11) tests (traced) | RED (traced) | three different expected maxima defeat a constant |
| P-S0-07 hashing | RED: import failure (traced) | RED: `"0"*64` or `b"{}"` mismatches 11 vectors; no `ValueError` for symlink/FIFO (traced) | positive vectors RED; error tests pass by design (traced) | independent vectors, `sha256sum` cross-check, exec-bit twin |
| P-S0-08 schemas | RED: import failure (traced) | RED: `validate -> []` is accepted by 0 of 54 invalid cases (traced) | RED: constant `[{"path":"/"}]` makes every valid case fail and no invalid case hit its expected pointer, because no expected pointer is `"/"` (traced) | exact pointer sets, `jsonschema` blocked, schema-file shape |
| P-S0-09 defaults | RED: `config/graph.toml missing` (traced) | RED: a hard-coded template fails the edited-`graph.toml` test (traced) | RED (traced) | scratch copy with `max_epochs = 7` |
| P-S0-10 golden self-check | n/a: no actl code involved | n/a | n/a | **ran**: exit 0 on the delivered fixture. Fixture-level mutation (changing `coverage.md`, killing the survivor, altering `expected.d`) is planned in Part 2 (`selfcheck_mutations.sh`) and not yet run |
| P-S0-11 cli | RED: `bin/actl is missing` (traced) | RED: `main -> 0` fails 1/2/3/4 rows and usage rows (traced) | RED: `main -> 1` fails the `0` and `2` rows (traced) | one dummy command per exit code in a scratch copy |
| P-S0-12 scope | RED: import failure (traced; reference passed 80+ of these cases: **ran**) | RED: `match -> "allowed"`, `validate -> []`, `parse` never raises (traced) | RED for match/validate tests; the `parse` rejection rows pass by design (traced) | 23 match rows, 10 invalid rulesets, 19 parse errors, order-independence |
| P-S0-13 hook immunity | pending | pending: green only if the build is hermetic | pending | counter-check that the hook really blocks a plain commit |
| P-S0-14 registries | RED: import failure (traced) | RED: constant `noop` or constant `early` fails priority, tie and terminal rows (traced) | RED (traced) | five-step priority scenario, `_private.py` ignored, purity digest |
| P-S0-15 loader | RED: import failure (traced; reference passed: **ran**) | RED: constant dict fails merge, duplicate and error rows (traced) | RED: `real_expected` row (traced) | lexical-order assertion, duplicate key and malformed JSON |
| P-S0-16..25 (E1..E10) | **ran** against the behavioural model, base variant: exit 1, all 10 red with `FAIL: <name>.exit was not written` | traced: a `0`-always writer is red at E2, E3, E8, E9, E10; a missing-file writer is red everywhere | traced: constant non-zero writer fails E1 and E2 | per-check sessions, E10 requires 129/130/143, E7 positive half; fixed variant: **ran**, exit 0, 10 green |
| P-S0-26 interfaces | RED: modules missing (traced) | RED: stubs with `*args, **kwargs` or no return annotation (traced); a stub generated with correct names, order and annotations is GREEN by design | GREEN by design: raising bodies with correct signatures conform - behaviour is covered by the other proofs | checker self-test rejects swapped params, missing annotation, missing name |
| P-S0-27 suite conformance | pending | pending | pending | double run with `ONLY=P-S0-10` must give identical summaries |

## Findings from the review
1. The reference `E10` and `E7` of the addendum passed on the fork point (a missing file satisfied them). Both were tightened (SA-9, SA-11); against the base model all ten checks are now red.
2. Four rows pass against the always-fail stand-in for "must reject" tests (P-S0-03, -07, -12, and P-S0-26 by design). This is expected; the same proofs also contain positive tests that fail, so the proof as a whole is red.
3. P-S0-26 is green for a signature-correct stub. It is an interface proof, not a behaviour proof; do not count it as evidence that the modules work.
4. Structural weakness not yet covered: P-S0-02, P-S0-13 and P-S0-27 and the gating suite `run_suite_actl_s0.sh` are not delivered yet, so their rows cannot be confirmed.
5. Real `tmux` and the real `arouter` were unavailable where the proofs were authored; E1..E10 were validated against a fake `tmux`/`arouter` model only. The first run on the VPS is the real test (SA-12).

## Part 2 deliverables needed to close this review
`proof/stage0/lib.sh`, `P-S0-01..15.sh`, `P-S0-26.sh`, `P-S0-27.sh`, `proof/run_suite_actl_s0.sh`, `vacuity_matrix.sh` with the stand-in generator, `selfcheck_mutations.sh`, and the planned `Authored-by` header on `.patch` files.
