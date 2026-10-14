# actl_Handoff_Prompts — Authoring and challenge prompts for Stages 0–2

**Purpose:** ready-to-paste prompts for the spec-and-proof authoring pass and the pre-implementation challenge. **Not part of the lock.** Operational file; replace freely. The locked package is: `actl_Design.md`, `actl_Build_Plan-Stages0to2.md` (core), `actl_Build_Plan-Stages0to2_addendum.md` (addendum) and `actl_Guide.md`.

## 0. How to use

**Order**
1. Commit the lock under `docs/` on a `wip/*` branch and merge it yourself (the hook blocks direct commits to `main`).
2. Optional five-minute measurements that the addendum still lists as open (F16 group case, O-15); snippets below.
3. Generate the repo dump (snippet below) and keep `paste.txt` (the `git log -p -3` diffs).
4. Run **A1** (interfaces). Review and accept `src/actl/INTERFACES.md`; commit it.
5. Run **A2**, **B** and **C** in parallel. They share only the accepted interface file.
6. Integrate: merge the three outputs; run every gating suite (each must exit `1`); run the golden self-check (must exit `0`).
7. Run **D** (cross-family challenge) on the integrated result. Fix findings by re-running the relevant author prompt with the findings attached.
8. Owner gate on the OPEN items the specs propose answers for; commit specs, proofs and fixtures to `main`; start implementation with the guide.

**Where to run.** Preferred: Cursor CLI inside a dedicated worktree (the agent writes files directly), for example
`git worktree add ../atools-author-s0 -b wip/author-s0 && cd ../atools-author-s0`, write the prompt to `/tmp/Runbook_author_s0.md`, then
`arouter -d -n author-s0 -t 90m smart "Follow /tmp/Runbook_author_s0.md" < /dev/null`
(map the `smart` tier to the model family you want with `arouter --set smart <model>`). Alternative: a web chat with the files attached; then use the delimited output format of the common block and paste results into the worktree by hand.

**Model families** (fill in; authors differ from the implementer, the challenger differs from the authors)

| Role | Family | Model |
|---|---|---|
| Authors A1, A2 | X | |
| Authors B, C | X or Y (never the implementer's) | |
| Challenger D | Z (not X or Y) | |
| Implementer (Cursor workhorse) | | |

**Attachments per prompt**

| Prompt | Always attach | Also attach |
|---|---|---|
| A1 | `actl_Design.md`, core, addendum | repo dump (below) |
| A2 | same three | `INTERFACES.md` (accepted A1 output), repo dump, `paste.txt`, `actl_Guide.md` |
| B | same three | `INTERFACES.md`, repo dump, `paste.txt`, `actl_Guide.md` |
| C | same three | `INTERFACES.md`, repo dump |
| D | same three | every author output (specs, proofs, tests, fixtures), `INTERFACES.md`, `actl_Guide.md`, repo dump, `paste.txt` |

If the agent works inside the worktree, the first three files are already under `docs/`.

**Repo dump (baseline commit)**
```bash
cd ~/atools && git rev-parse HEAD
{ find . -type d \( -name '.git' -o -name 'audit' -o -name 'docs' -o -name 'out' -o -name '_*' \) -prune \
    -o -type f ! -name '.*' ! -name '_*' ! -name '*.pyc' ! -name '*.log' -size +0c -print0 \
  | sort -z | while IFS= read -r -d '' f; do printf '\n==== FILE: %s ====\n\n' "$f"; cat "$f"; done
  printf '\n==== FILE: audit/atools-compliance_audit.sh ====\n\n'; cat audit/atools-compliance_audit.sh
} > /tmp/atools_dump.txt
```

**Optional measurements still open** (record the output next to the addendum facts)
```bash
# F16: SIGTERM followed at once by SIGHUP to the whole process group (what tmux kill-session does)
python3 - <<'EOF'
import subprocess, time, os, signal
open('/tmp/t3.sh','w').write("#!/usr/bin/env bash\ncleanup() { local ec=$?; echo \"$ec\" > /tmp/t3_out; }\ntrap cleanup EXIT\ntrap 'exit 143' TERM\nsleep 4\nexit $?\n")
if os.path.exists('/tmp/t3_out'): os.remove('/tmp/t3_out')
p = subprocess.Popen(['bash','/tmp/t3.sh'], start_new_session=True)
time.sleep(0.5); p.send_signal(signal.SIGTERM); os.killpg(p.pid, signal.SIGHUP); p.wait()
print('returncode', p.returncode, 'file:', open('/tmp/t3_out').read().strip() if os.path.exists('/tmp/t3_out') else None)
EOF
# O-15: do non-PATH variables reach a pane on an already-running tmux server? (subshell: does not touch your shell)
( T=$(mktemp -d); export TMUX_TMPDIR=$T; tmux -V
  tmux new-session -d -s keep 'sleep 60'
  FOO=bar tmux new-session -d -s p3 "echo FOO=\$FOO > $T/foo"; sleep 1; cat $T/foo
  tmux kill-server; rm -rf $T )
```

---

## 1. COMMON BLOCK (paste at the top of every author prompt)

```text
ROLE
You are an independent specification-and-proof author for the "actl" incremental build plan. You do not implement actl. You write specifications, proofs (executable checks), tests, fixtures and stubs that a later, different agent will implement against. State your model name and family in a header line "Authored-by:" in every file you produce.

INPUTS (read all of them completely before writing)
- actl_Design.md  (long-term design; normative when in doubt)
- actl_Build_Plan-Stages0to2_addendum.md  (Stage specifications, numbered requirements, proof obligations, measured facts F1-F16, branch rules)
- actl_Build_Plan-Stages0to2.md  (core: strategy, ground truth, stage map)
Authority order: Design > Addendum > Core. If two sources conflict, follow the higher one and record the conflict under "Proposed decisions".

RULES
1. Keep every requirement ID (S0-R1 ...). You may add requirements; you must not delete or weaken one. Add new IDs with the next free number and say why.
2. Do not write implementation code for src/actl/*.py or src/router/*.py. Allowed: spec documents, INTERFACES text, proofs (bash), pytest tests, fixtures, stubs, expected-results files.
3. Proof conventions: a proof is a script that exits 0 on pass and 1 on fail and prints a line starting "FAIL:" with the requirement id and the reason. Gating proofs use no network and no LLM; anything needing a live model is named smoke_* and is excluded from the gating suite. Use "mktemp -d" scratch directories; every git repository you create or commit in must use "-c core.hooksPath=/dev/null".
4. RED ON BASE: every gating suite you write must exit 1 on a checkout that contains none of the implementation, and must fail for the right reason (a missing module, command or file reported with a FAIL: line), not because of a harness error. A missing tool (tmux, git) is a different condition: exit 4 with a message.
5. VACUITY REVIEW (addendum §10 item 5, first phase): for each proof, state in the traceability table how it behaves against (a) an empty module, (b) an always-succeed stub, (c) an always-fail stub, and make sure it fails against each stand-in it should reject. A proof that would pass against a stand-in it should reject is vacuous: fix it. (Planting mutants in real code is the second phase, after implementation, done by a reviewer.)
6. Ambiguities: do not ask questions unless you are blocked. For each ambiguity write a row in an "Ambiguity register" (what is unclear, the readings, the one you chose, why). Answer every OPEN item assigned to you under "Proposed decisions" with a concrete proposal.
7. Traceability: every requirement ID maps to at least one proof ID; every proof ID maps back to a requirement.
8. Be concrete: exact commands, exact file paths, exact expected exit codes and substrings. No placeholders such as "TBD" or "etc.".
9. Stay in scope: produce only the deliverables listed for your prompt.

OUTPUT FORMAT
- If you have a filesystem: write the files in place and finish by printing the tree of what you created plus the self-check below.
- If you do not: output every file as
    === FILE: path/relative/to/repo ===
    <verbatim content>
    === END FILE ===
  If the answer is too long, stop at a file boundary and end with "=== CONTINUE (part n of m) ===". Never truncate a file. Finish with a list of paths that need the executable bit.

SELF-CHECK (end your answer with this list, each item "done" or "not done: why")
[ ] all IDs preserved   [ ] traceability complete   [ ] every gating suite is Red on base for the right reason
[ ] vacuity review in the traceability table   [ ] Proposed decisions answer every assigned OPEN item
[ ] ambiguity register present   [ ] no implementation code written   [ ] all git use passes core.hooksPath=/dev/null
```

---

## 2. Prompt A1 — Interfaces (small, first)

Attach: see matrix (A1). Paste COMMON BLOCK, then:

```text
TASK A1: write src/actl/INTERFACES.md, the interface freeze of addendum S0-R15 (including its machine-readable block).

It must contain:
1. For every public function/class that Stages 0, 1 and 2 share or call across Stage boundaries: Layout, ids, seq (reserve, reconstruct), hashing (file_sha256, manifest_sha256, canonical_json, json_sha256), schemas.validate, scope (parse, validate, match), decide_next and the registry entry points (cmd_*.py register(subparsers); next_rules/*.py rule signature and evaluation order), StepResult and the ev document shape, session helpers that Stage 1 will use (names only, behaviour in S1-R14), the turn-ledger layout of Stage 2, and the CLI synopsis of every command in Stages 0-2 (flags, exit codes per S0-R10, --json output keys).
2. For each item: Python signature with types, preconditions, return value, errors raised or error codes returned, side effects (files touched), idempotence, and which Stage owns it.
3. File formats: state.json keys, sprint.toml keys, baseline.json keys, ev/StepResult/session record, prior_attempt.json, turn ledger files, expected.d fragment schema, the envelope sentinel reference (grammar stays in addendum §7.5).
4. A fenced ```json block named interfaces.json: a machine-readable list {module, name, kind, params:[{name,type}], returns} for every public name, so that proof P-S0-26 can check conformance.
5. A "Dependency map": for each Stage 1 and Stage 2 requirement, which Stage 0 names it uses.
6. "Proposed decisions" for O-1 (jsonschema or vendored validator), O-2 (solution_key name before freeze) and anything that changes an interface.
No proofs, no code bodies. Maximum about 700 lines. This file becomes immutable once accepted (PB-2), so be precise and minimal: do not expose anything a Stage does not need to share.
```

---

## 3. Prompt A2 — Stage 0 specification, proofs and golden fixture

Attach: see matrix (A2). Paste COMMON BLOCK, then:

```text
TASK A2: author Stage 0 (workstreams 0A and 0B) against the accepted INTERFACES.md.

Deliverables
1. spec-S0.md: every requirement S0-R1..R16 expanded into testable text; traceability table (requirement -> proof ids, with the vacuity-review columns); Ambiguity register; Proposed decisions (O-1, O-2 if not settled, anything you recommend changing).
2. Proofs and tests for 0A: proof/stage0/*.sh, proof/run_suite_actl_s0.sh (run_check pattern of proof/run_suite_engines.sh; log per check in proof/out/), test/actl/*.py (pytest, stdlib only). Cover P-S0-01..15 and P-S0-26 as written in the addendum (add more if you find gaps). They must be Red on base.
3. Proofs for 0B: proof/run_suite_exit_code.sh (checks E1..E10 = P-S0-16..25), starting from the reference in addendum §5.9, which already includes the signal traps and the unconditional kill-path overwrite. The suite is normative, the reference code is a starting point. Run the suite against the current repo and paste the output, showing that it fails only because the exit-code file is missing (and, for E10, not because of a harness error).
4. The golden sprint under fixtures/golden/ exactly as addendum §5.8 lists it: target-repo/ (stdlib-only Python), build_golden.sh (fixed author/date so the commit SHA is stable; uses -c core.hooksPath=/dev/null), sprint/ (spec-001.md, solution_key.patch, oracle/ with proofs, probe.sh, scope.txt, coverage.md, oracle-critique.md, four mutants including avatar_drop.patch which must survive), implementations/ (good.patch and the six bad_*.patch, each failing at exactly the step named), stubs/ (agent, loginctl with the behaviours EXIT7, SLEEP, WRITE_CLOSURE keyed on words in the prompt), closures/ (good, schema-invalid, blocked-too-early, done), artifacts/valid and artifacts/invalid (>= 3 invalid per schema, each with the expected error path), expected.d/base.json, and the expected resolved sprint.toml text for P-S0-09.
5. proof/stage0/golden_selfcheck.sh (P-S0-10): a plain-shell script, using no actl code, that proves the fixture is internally true: base fails the proofs; base+key passes proofs three times and the repo tests; each mutant applied to base+key is killed by exactly the mapped proof(s) except avatar_drop.patch which survives; good.patch passes everything; every bad_*.patch applies cleanly and fails at the declared step. Exit 0 only if all of that holds.
6. The scope.txt / glob table for P-S0-12 (>= 15 cases) as data (fixtures/golden/scope_cases.tsv).
Do not write src/actl/*.py. Do not write schemas/*.json (the implementer does, and must satisfy your artifacts/ examples).
```

---

## 4. Prompt B — Stage 1 specification and proofs

Attach: see matrix (B). Paste COMMON BLOCK, then:

```text
TASK B: author Stage 1 (verifier and Implementer loop) against the accepted INTERFACES.md. The golden fixture is written by another author; refer to its files by the names in addendum §5.8 and define your expectations in fixtures/golden/expected.d/s1.json. Do not create implementations/*.patch or the golden sprint.

Deliverables
1. spec-S1.md: S1-R1..R15 expanded; traceability table with vacuity columns; Ambiguity register; Proposed decisions (O-4 G4 for non-Python, O-5 initial config/forbidden.toml rule list, O-6 initial config/secrets.toml patterns, O-8 failing_line sanitising). The argument-size ceiling is already measured (addendum F3: 131071 bytes accepted, 131072 refused); use it. Include the proposed contents of config/forbidden.toml and config/secrets.toml as spec appendices (the implementer will create the files).
2. Proofs and tests: proof/stage1/*.sh, proof/run_suite_actl_s1.sh, test/actl/test_verify_*.py, test_guards_*.py, test_next_phase3.py, covering P-S1-01..28 of the addendum (add more if you find gaps). Detached proofs use the private-environment recipe of addendum §6.6 (private TMUX_TMPDIR, private ATOOLS_LOG_DIR and ATOOLS_SESSION_DIR, stub agent and loginctl first in PATH, behaviour chosen by words in the prompt); without tmux they exit 4 and say so.
3. Synthetic inputs for the tripwire proofs: fixtures/golden/transcripts/ (Cursor-style JSONL transcripts, one clean, one mentioning proofs/ and probe.sh) and fixtures/golden/logs/ (ANSI-laden console logs, one clean, one with an oracle path).
4. A proof that skills/actl-implementer/SKILL.md (to be written by the implementer) satisfies S1-R8: required instructions present, forbidden instructions (running proof suites, reading oracle paths) absent; grep-based, with the checklist stated in the spec.
5. expected.d/s1.json mapping each golden case to the expected step, exit code, failing_step and failing_line substring.
Do not write src/actl/*.py, skills/*, config/*.toml.
```

---

## 5. Prompt C — Stage 2 specification and proofs

Attach: see matrix (C). Paste COMMON BLOCK, then:

```text
TASK C: author Stage 2 (paste bridge and promotion) against the accepted INTERFACES.md and addendum §7.9. The golden sprint is written by another author; derive everything that depends on its content programmatically.

Deliverables
1. spec-S2.md: S2-R1..R12 expanded, including the envelope grammar (addendum §7.5) as a normative section with at least 10 worked examples (good and bad); traceability table with vacuity columns; Ambiguity register; Proposed decisions (O-2, O-3 envelope escape, O-9, and the exact normalisation rules of S2-R4 step 3).
2. Proofs and tests: proof/stage2/*.sh, proof/run_suite_actl_s2.sh, test/actl/test_envelope*.py etc., covering P-S2-01..16 (add more if needed). Include the truncation property test with a fixed seed.
3. fixtures/golden/make_responses.sh: builds the good_* responses from the golden spec/key/oracle files, the bad_* and variant_* ones from the good_* ones, and fixtures/golden/turns/<role>-1/ (bundle.json, bundle.txt) whose hash supplies each sentinel; plus fixtures/golden/expected.d/s2.json with the expected single error code, exit code and output hashes for each response.
4. A proof that the repair prompt (S2-R7) for each bad_* response contains the error code, the path and the nearest candidate where applicable, and no text that the response did not contain.
5. prompts/*.md requirements as a checklist test (S2-R11): required statements present per persona; the output contract is appended from a single file.
Do not write src/actl/*.py or prompts/*.md themselves.
```

---

## 6. Prompt D — Cross-family challenge (before implementation)

Attach: see matrix (D). Paste this (no common block):

```text
ROLE
You are an adversarial reviewer from a model family different from the authors. State your model and family. You do not rewrite the work; you find defects and prove them where possible.

INPUTS
The Design, the core document, the addendum, INTERFACES.md, spec-S0/S1/S2.md, all proofs, tests, fixtures, stubs and expected.d files, the guide, the repo dump and the diffs.

CHECKS (do all; report evidence for each)
1. Traceability: every requirement ID has >= 1 proof; every proof has a requirement; list orphans and gaps. Check specs preserve all IDs and did not weaken any requirement versus the addendum.
2. Red on base: run every gating suite on a checkout without implementation. Each must exit 1 with FAIL: lines naming missing features, never harness errors. Report outputs.
3. Vacuity (addendum §10 item 5, first phase): for each suite, build or simulate (a) an empty package, (b) an always-succeed stub, (c) an always-fail stub of the modules it tests, and run it. List every proof that passes where it should fail. If you can, deliver the stand-ins as a small kit (proof/degenerate/ or scripts) so the check can be repeated.
4. Fixture truth: run proof/stage0/golden_selfcheck.sh and the 0B suite's stub recipe; confirm base red, key green, mutants as declared (avatar_drop survives), bad_* fail exactly where declared.
5. Conflicts and ambiguity: contradictions between specs, addendum and Design; requirements with two plausible readings that would let an implementation pass the proofs while violating the intent; list each with a concrete counter-example implementation.
6. Security and robustness: path handling, command execution from model output, secret leakage, environment allowlists, race conditions in seq allocation and in the exit-code file, signal handling in the runner, hook independence of scratch repos.
7. Design alignment: places where a Stage spec departs from the Design without a recorded reason.
8. Over-engineering and omissions: things the specs demand that no Stage 0-2 goal needs; and goals with no requirement.
9. Interface check: INTERFACES.md versus what the Stage 1 and Stage 2 specs assume; missing or unusable signatures.

OUTPUT
A table of findings: id, severity (blocker/major/minor), location (file and line or requirement id), evidence (command and output, or counter-example), suggested fix. Then one verdict per Stage: ready / ready after fixes / not ready, with the blockers listed. Then a log of every command you ran. Do not edit the authors' files.
```
