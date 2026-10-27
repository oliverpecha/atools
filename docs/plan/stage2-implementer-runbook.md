# Stage 2 Implementer Runbook (Paste Bridge & Promotion)

## 1. Goal
Implement the 13 Stage 2 modules specified in `src/actl/INTERFACES.md`
to transition the Stage 2 gate suite (`proof/run_suite_actl_s2.sh`)
from Red (0 Passed, 18 Failed) to clean Green (18 Passed, 0 Failed, 0 Env).

## 2. Implementer
Cursor Auto executed through `arouter`.

## 3. Files in Scope
Implementation is strictly restricted to the 13 Stage 2 modules:
- `src/actl/turns.py`
- `src/actl/bundle.py`
- `src/actl/envelope.py`
- `src/actl/unpack.py`
- `src/actl/patchsynth.py`
- `src/actl/repair.py`
- `src/actl/replay.py`
- `src/actl/promote.py`
- `src/actl/cmd_bundle.py`
- `src/actl/cmd_unpack.py`
- `src/actl/cmd_replay.py`
- `src/actl/cmd_promote.py`
- `src/actl/next_rules/phase12.py`

## 4. Immutable Paths (PB-2)
The following paths are permanently frozen and must not be touched:
- `proof/`
- `fixtures/`
- `test/actl/`
- `src/actl/INTERFACES.md`
- `tools/`

Verification check:
`git diff --name-only <start>..HEAD -- proof fixtures test/actl src/actl/INTERFACES.md tools`
must remain completely empty.

## 5. Designated Suite
Run under lock:
`flock -w 3600 /tmp/atools-heavy.lock bash proof/run_suite_actl_s2.sh`

## 6. Branching & Commit Protocol
1. Branch `wip/s2-bridge` is created from `wip/author-s2` plus `main`
   after Owner amendments land.
2. Commits use message files: `printf "..." > /tmp/msg && git commit -F /tmp/msg`.
3. Work items follow `WI-S2-R<k>` tags per requirement group.
4. Working branch only; no push to remote.

### Commit Message Format
Every commit must use a message file (`git commit -F <file>`) following this structure:

<type>(<scope>): <summary> (WI-S2-R<k>)

Why: <rationale referencing bare commit SHAs, e.g. 49ebef9>

What changed:
- <file>: <description of changes>

Result: <test and proof outcome metrics>
Scope Stop Rule
If an implementation change OUTSIDE the 13 files listed in Section 3 appears needed, work MUST STOP immediately and be reported to the Owner.

Model Tracking
The implementer's model identifier and family are recorded per session in the session ledger.

## 7. Test Defect Stop Rule
If an implementer identifies an apparent contradiction between
`docs/plan/spec-S2.md` and the test suite, work MUST STOP immediately.
Report the issue to the Owner. Under no circumstances may an implementer
edit tests, proofs, or fixtures.
