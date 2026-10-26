# LT-A3 Report: test and proof rename residue

* Workstream: LT-A3 / branch `wip/layout-amend-a` / worktree `~/atools-lt-a`
* Base: `117d7e3`
* Head: `bf5ceaf`
* Scratch: `/tmp/lt-a3-scratch`
* Date (UTC): 2026-10-25

## Commits (`117d7e3..HEAD`)

```
bf5ceaf test(proof): refresh P-S0-02 pins after L-5 test rename (WI-S0-PROOF)
d17aacb test(actl): rename gating ev/qual kinds to L-5 names (WI-S0-PROOF)
```

## R1 Inventory (before)

```
fixtures/golden/artifacts/invalid/contract/budgets_forbidden.json:15:  "qual": {
fixtures/golden/artifacts/invalid/contract/epoch_zero.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/id_pattern.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/kind_const.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/short_base_sha.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/spec_missing_sha256.json:12:  "qual": {
fixtures/golden/artifacts/valid/contract/contract_base.json:12:  "qual": {
fixtures/golden/build_golden.sh:83:{"base_sha":"$base_sha","epoch":1,"id":"contract-005","kind":"contract","oracle":{"id":"oracle-003","manifest_sha256":"$msha","seq":3},"parent":null,"qual":{"id":"qualification-004","seq":4,"sha256":"$qual_sha"},"scope":{"path":"oracle-003/scope.txt","sha256":"$scope_sha"},"seq":5,"spec":{"id":"spec-001","seq":1,"sha256":"$spec_sha"},"sprint_sha256":"$sprint_sha"}
proof/stage0/SURVIVOR_ANALYSIS.md:90:S11-51 schemas/ev.json:28 seq minimum 1 to 0: killed-by test_pinned_bounds[ev:seq:minimum] and the lint.
proof/stage0/SURVIVOR_ANALYSIS.md:91:S11-52 schemas/ev.json:75 additionalProperties false to true: same as S11-47.
proof/stage0/SURVIVOR_ANALYSIS.md:92:S11-53 schemas/qual.json:63 additionalProperties false to true: same as S11-47.
proof/stage0/diff_equiv_seed11.py:42:        if isinstance(d, dict) and d.get("kind") == "qual" and not schemas.validate("qual", d):
proof/stage0/diff_equiv_seed11.py:55:        k = rnd.choice(["spec", "sk", "od", "o", "contract", "closure", "ev", "esc", "live", "qual"])
proof/stage0/diff_equiv_seed11.py:68:        elif k == "ev":
proof/stage0/diff_equiv_seed11.py:69:            (rd / f"ev-{n:03d}.json").write_text(json.dumps({"stage": rnd.choice(["guards", "live", None]), "hard_cap": rnd.random() < .4}))
proof/stage0/diff_equiv_seed11.py:78:            d["seq"], d["id"] = n, f"qual-{n:03d}"
proof/stage0/diff_equiv_seed11.py:79:            (rd / f"qual-{n:03d}.json").write_text(json.dumps(d))
test/actl/test_p05_seq.py:21:    print(seq.reserve(lay, %r, "ev"), flush=True)
test/actl/test_p05_seq.py:40:    n = seq.reserve(lay, TAG, "qual")
test/actl/test_p05_seq.py:47:    with pytest.raises(ValueError): seq.reserve(lay, "../x", "ev")
test/actl/test_p05_seq.py:48:    with pytest.raises(FileNotFoundError): seq.reserve(lay, "2026-10-17_absent", "ev")
test/actl/test_p05_seq.py:57:    if seq.reserve(lay, TAG, "ev") != 41: fail("reserve must use max(state.seq, highwater) + 1 (highwater=40, state=5)")
test/actl/test_s0_gap2_reconstruct.py:148:        doc = {"kind": "ev", "seq": i + 1, "parent": None}
test/actl/test_s0_gap2_reconstruct.py:151:        put(lay, f"ev-{i + 1:03d}.json", doc, "runs")
test/actl/test_s0_gap2_reconstruct.py:166:            put(lay, f"ev-{seqn:03d}.json", {"hard_cap": True}, "runs")
test/actl/test_s0_gap2_reconstruct.py:168:            put(lay, f"ev-{seqn:03d}.json", {"session": {"hard_cap": True}}, "runs")
test/actl/test_s0_gap2_reconstruct.py:170:    put(lay, f"ev-{seqn:03d}.json", {"hard_cap": True, "session": {"hard_cap": True}}, "runs")
test/actl/test_s0_gap2_reconstruct.py:173:        put(lay, f"ev-{seqn:03d}.json", extra, "runs")
test/actl/test_s0_gap2_schemas.py:182:    for k in ("state", "sprint", "sprint-proposal", "closure", "ev", "qual", "contract"):
test/actl/test_s0_gap2_schemas.py:254:    ("closure", ["seq"], "minimum", 1), ("ev", ["seq"], "minimum", 1), ("qual", ["seq"], "minimum", 1),
test/actl/test_s0_gap2_schemas.py:257:    ("ev", ["exit_code"], "minimum", 0), ("ev", ["exit_code"], "maximum", 255),
test/actl/test_s0_gap2_seed23.py:75:    assert seq.reserve(l, TAG, "ev") == 1
test/actl/test_s0_gap_conformance.py:128:    ("ev", "stage", {"guards", "offline", "live", "blockedcheck"}),
test/actl/test_s0_gap_conformance.py:129:    ("ev", "halt.reason",
test/actl/test_s0_gap_conformance.py:131:    ("qual", "diagnostic_case", {"none", "pureoraclefailure", "solutionkeyconflict"}),
test/actl/test_s0_gap_conformance.py:162:    ("ev", "exit_code", 0, 255),
test/actl/test_s0_gap_conformance.py:189:    types = {t for ts in _collect(_prop("ev", "exit_code"), "type") for t in (ts if isinstance(ts, list) else [ts])}
test/actl/test_s0_gap_conformance.py:191:        isinstance(n, dict) and n.get("type") == "null" for n, _, _ in _subs(_prop("ev", "exit_code")))
test/actl/test_s0_gap_conformance.py:196:    ("ev", "head", 40), ("qual", "base_sha", 40), ("contract", "base_sha", 40), ("sprint", "base_sha", 40),
test/actl/test_s0_gap_conformance.py:197:    ("qual", "manifest_sha256", 64), ("meta", "sha256", 64),
test/actl/test_s0_gap_ids.py:20:    "spec", "solution_key", "oracle", "oracle-draft", "qual", "contract",
test/actl/test_s0_gap_ids.py:21:    "closure", "ev", "escalation", "live-decision", "implementer",
test/actl/test_s0_gap_ids.py:36:        fn("ev", seq)
test/actl/test_s0_gap_ids.py:65:    for k in ("qual", "contract", "closure", "ev", "escalation", "live-decision"):
test/actl/test_s0_gap_schemas_oneof.py:109:    errors = schemas.validate_schema_direct(schema, {}) if hasattr(schemas, "validate_schema_direct") else schemas.validate("qual", {})
test/actl/test_s0_gap_seq_reconstruct_order.py:178:        "qual": {"seq": 4, "sha256": "c" * 64},
test/actl/test_s0_gap_seq_reconstruct_order.py:218:        "qual": {"seq": 4, "sha256": "c" * 64},
```

## R1 Inventory (after)

```
fixtures/golden/artifacts/invalid/contract/budgets_forbidden.json:15:  "qual": {
fixtures/golden/artifacts/invalid/contract/epoch_zero.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/id_pattern.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/kind_const.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/short_base_sha.json:12:  "qual": {
fixtures/golden/artifacts/invalid/contract/spec_missing_sha256.json:12:  "qual": {
fixtures/golden/artifacts/valid/contract/contract_base.json:12:  "qual": {
fixtures/golden/build_golden.sh:83:{"base_sha":"$base_sha","epoch":1,"id":"contract-005","kind":"contract","oracle":{"id":"oracle-003","manifest_sha256":"$msha","seq":3},"parent":null,"qual":{"id":"qualification-004","seq":4,"sha256":"$qual_sha"},"scope":{"path":"oracle-003/scope.txt","sha256":"$scope_sha"},"seq":5,"spec":{"id":"spec-001","seq":1,"sha256":"$spec_sha"},"sprint_sha256":"$sprint_sha"}
proof/stage0/SURVIVOR_ANALYSIS.md:90:S11-51 schemas/ev.json:28 seq minimum 1 to 0: killed-by test_pinned_bounds[ev:seq:minimum] and the lint.
proof/stage0/SURVIVOR_ANALYSIS.md:91:S11-52 schemas/ev.json:75 additionalProperties false to true: same as S11-47.
proof/stage0/SURVIVOR_ANALYSIS.md:92:S11-53 schemas/qual.json:63 additionalProperties false to true: same as S11-47.
proof/stage0/diff_equiv_seed11.py:42:        if isinstance(d, dict) and d.get("kind") == "qual" and not schemas.validate("qual", d):
proof/stage0/diff_equiv_seed11.py:55:        k = rnd.choice(["spec", "sk", "od", "o", "contract", "closure", "ev", "esc", "live", "qual"])
proof/stage0/diff_equiv_seed11.py:68:        elif k == "ev":
proof/stage0/diff_equiv_seed11.py:69:            (rd / f"ev-{n:03d}.json").write_text(json.dumps({"stage": rnd.choice(["guards", "live", None]), "hard_cap": rnd.random() < .4}))
proof/stage0/diff_equiv_seed11.py:78:            d["seq"], d["id"] = n, f"qual-{n:03d}"
proof/stage0/diff_equiv_seed11.py:79:            (rd / f"qual-{n:03d}.json").write_text(json.dumps(d))
test/actl/test_p05_seq.py:47:    with pytest.raises(ValueError): seq.reserve(lay, TAG, "ev")
test/actl/test_p05_seq.py:48:    with pytest.raises(ValueError): seq.reserve(lay, TAG, "qual")
test/actl/test_p08_schemas.py:57:@pytest.mark.parametrize("kind", ["no-such-kind", "ev", "qual"])
test/actl/test_s0_gap2_schemas.py:277:@pytest.mark.parametrize("kind", ["ev", "qual"])
test/actl/test_s0_gap_ids.py:24:BAD_KINDS = ["bogus", "", "EV", "ev ", None, "spec-001", "ev", "qual"]
test/actl/test_s0_gap_seq_reconstruct_order.py:178:        "qual": {"seq": 4, "sha256": "c" * 64},
test/actl/test_s0_gap_seq_reconstruct_order.py:218:        "qual": {"seq": 4, "sha256": "c" * 64},
```

### Remaining-hit justifications (zero positive uses)

| Hit | Class | Justification |
|---|---|---|
| fixtures/.../contract/*.json `"qual":` | contract field | Ratified: contract object field `qual` stays |
| fixtures/golden/build_golden.sh `"qual":{...\}` | contract field | Same; `` is a shell var |
| test_s0_gap_seq_reconstruct_order.py `"qual":` | contract field | Contract fixture objects |
| test_p05_seq.py `reserve(..., "ev"/"qual")` | explicit negative | Old kinds must raise ValueError |
| test_p08_schemas.py parametrize `ev`, `qual` | explicit negative | Unknown schema kinds |
| test_s0_gap2_schemas.py parametrize `ev`, `qual` | explicit negative | `validate` must refuse old names |
| test_s0_gap_ids.py BAD_KINDS `ev`, `qual` | explicit negative | `format_artifact_*` must refuse |
| proof/stage0/diff_equiv_seed11.py | non-gating (R4) | Historical differential; no gate runs it; **must not be run after Part B** |
| proof/stage0/SURVIVOR_ANALYSIS.md `schemas/ev.json` / `qual.json` | historical prose | Seed11 mutant kill record; not executed |

## Per-file change list

### d17aacb test(actl): rename gating ev/qual kinds to L-5 names (WI-S0-PROOF)

| File | Change |
|---|---|
| test/actl/test_p05_seq.py | Positive `reserve` → `verification`/`qualification`; add `ev`/`qual` reject; tag-error paths use `verification` |
| test/actl/test_p08_schemas.py | `test_unknown_kind` parametrizes `ev`, `qual` |
| test/actl/test_s0_gap2_reconstruct.py | Plant `verification-NNN.json` / kind `verification` |
| test/actl/test_s0_gap2_schemas.py | Inventory + PINNED → new kinds (exit_code 0..255, seq min 1 retained); refuse `ev`/`qual` |
| test/actl/test_s0_gap2_seed23.py | `reserve(..., "verification")` |
| test/actl/test_s0_gap_conformance.py | Schema names `verification`/`qualification` |
| test/actl/test_s0_gap_ids.py | KINDS renamed; BAD_KINDS += `ev`, `qual` |
| test/actl/test_s0_gap_schemas_oneof.py | Fallback `validate("qualification", ...)` |

### bf5ceaf test(proof): refresh P-S0-02 pins after L-5 test rename (WI-S0-PROOF)

| File | Change |
|---|---|
| proof/stage0/P-S0-02.sh | Re-pin 8 test blobs; `# LT-A3 pin refresh applied`; INTERFACES pin SKIPPED |

## R4 Legacy script

`proof/stage0/diff_equiv_seed11.py` is non-gating (historical differential; no gate runs it) and **must not be run after Part B**.

## Touched-test pytest failures → memo

Exception lines from `python3 -m pytest` on the eight edited test files (plus p08). All map to **L-5** (kinds/schemas/files renamed in tests; implementation still old) unless noted.

| Exception / assertion | Memo |
|---|---|
| `ValueError: Invalid artifact kind/seq: 'verification', …` / `'qualification'` | L-5: `ARTIFACT_KINDS` still `ev`/`qual` |
| `ValueError: Unknown schema kind: verification` / `qualification` | L-5: `VALID_KINDS` / schema files still old |
| `FileNotFoundError: .../schemas/verification.json` / `qualification.json` | L-5: schema rename pending Part B |
| `FAIL: schemas/verification.json missing` | L-5 |
| `DID NOT RAISE ValueError` for kind `ev`/`qual` (ids, schemas.validate, reserve) | L-5: old names still accepted until Part B |
| `no valid fixture for verification` / `doc_of` fails | L-5: validate cannot bind new kinds yet |
| reconstruct asserts `0 == n` / hard_caps / hold (verification-NNN ignored) | L-5: `seq.reconstruct` still matches `ev-`/`qual-` |
| `FAIL: worker exited 1` / `too few numbers (0)` | L-5: worker `reserve(..., "verification")` rejected |
| `FAIL: installed golden state.json ... repo` | L-10 (pre-existing; state schema lacks `repo`) |

Full log: `/tmp/lt-a3-scratch/touched_pytest.log` (80 failed, 205 passed).

## Delivery gates

### 1. Ancestry / commits / tags

```
ancestor_rc=0
bf5ceaf test(proof): refresh P-S0-02 pins after L-5 test rename (WI-S0-PROOF)
d17aacb test(actl): rename gating ev/qual kinds to L-5 names (WI-S0-PROOF)
tags: (WI-S0-PROOF) (WI-S0-PROOF) 
```

New commits only; each has exactly one `WI-S0-PROOF` tag; hook accepted both.

### 2. Diff paths / forbidden

```
proof/stage0/P-S0-02.sh
test/actl/test_p05_seq.py
test/actl/test_p08_schemas.py
test/actl/test_s0_gap2_reconstruct.py
test/actl/test_s0_gap2_schemas.py
test/actl/test_s0_gap2_seed23.py
test/actl/test_s0_gap_conformance.py
test/actl/test_s0_gap_ids.py
test/actl/test_s0_gap_schemas_oneof.py
forbidden_count=0
```

Only `test/actl/` and `proof/`; forbidden-path count 0.

### 3. R1 after → zero positives

See remaining-hit table above.

### 4. `bash proof/run_suite_actl_s0.sh` → exit 1, 0 Environment

```
Running P-S0-10_golden_selfcheck... [PASS]
Running P-S0-01_doctor... [PASS]
Running P-S0-02_additive_change... [PASS]
    FAIL: pytest reported failures without a FAIL: line
    FAIL: worker produced too few numbers (0) to test a kill
    FAIL: pytest reported failures without a FAIL: line
Running P-S0-07_hashing... [PASS]
    FAIL: schemas/verification.json missing
    FAIL: installed golden state.json invalid: [{'path': '/repo', 'message': 'Additional property not allowed: repo'}]
    FAIL: pytest reported failures without a FAIL: line
Running P-S0-11_cli_exit_codes... [PASS]
Running P-S0-12_scope... [PASS]
Running P-S0-13_global_hook_immunity... [PASS]
    FAIL: decide_next crashed: Traceback (most recent call last):
    FAIL: decide_next crashed: Traceback (most recent call last):
Running P-S0-15_expected_fragments... [PASS]
    FAIL: 5 interface problem(s):
Running P-S0-28_doctor_uninitialised... [PASS]
    FAIL: decide_next crashed: Traceback (most recent call last):
    FAIL: decide_next crashed: Traceback (most recent call last):
    FAIL: pytest reported failures without a FAIL: line
Suite Summary: 9 Passed, 10 Failed, 0 Environment
```

Stored: `EXIT_RC=1` (suite exit 1).

Red set (same 10 as A2): P-S0-03, -04, -05, -06, -08, -09, -14, -26, -29, -30.
Growth inside already-red proofs: P-S0-05 kill worker now fails immediately on `verification` reserve; P-S0-30 gap proofs add DID NOT RAISE for old-name negatives — memo **L-5**.

### 5. Green suites

```
run_suite_exit_code: EXIT_RC=0
==========================================
Suite Summary: 10 Passed, 0 Failed
==========================================
P-S0-27: P27_RC=0
golden_selfcheck: GOLDEN_RC=0
==========================================
golden_selfcheck: ALL CHECKS PASSED
selfcheck_mutations: MUT_RC=0
==========================================
selfcheck_mutations: control green, all 23 planted defects detected
```

Mutants still 23.

### 6. Compliance audit

```
Audit Verdict: 49 passed, 0 failed, 18 skipped, 2 warnings (profile=dev, adapter=cursor)
========================================================
```

### 7. P-S0-02 + clean tree

```
P02: P02_RC=0
OK: P-S0-02 (integration)
git status --short: 0 lines (empty)
```

## Stop

LT-A3 authoring complete. No push, no Part B, no amend/rebase/merge.
