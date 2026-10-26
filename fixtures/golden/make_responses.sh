#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
# fixtures/golden/make_responses.sh - builds golden turns, responses, and expected.d/s2.json
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SPRINT="$HERE/sprint"

python3 - "$HERE" "$SPRINT" <<'PY_INNER'
import hashlib
import json
import os
import sys
from pathlib import Path

golden_dir = Path(sys.argv[1])
sprint_dir = Path(sys.argv[2])
base_sha = "01d880bc3176cdd8f31d72e67bb3eba54d634378"

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().lower()

def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())

turns_dir = golden_dir / "turns"
responses_dir = golden_dir / "responses"
turns_dir.mkdir(parents=True, exist_ok=True)
responses_dir.mkdir(parents=True, exist_ok=True)

# 1. Build turns: architect-1, challenger-1, architect-2
turns_data = [
    ("architect-1", "architect", "architect-intake", None),
    ("challenger-1", "challenger", "challenger", sha256_file(sprint_dir / "solution_key.patch")),
    ("architect-2", "architect", "architect-review", sha256_file(sprint_dir / "solution_key.patch")),
]

sentinels = {}

for turn_id, role, purpose, sol_key_sha in turns_data:
    tdir = turns_dir / turn_id
    tdir.mkdir(parents=True, exist_ok=True)
    body_text = (
        f"# Turn {turn_id} prompt bundle\n"
        f"role: {role}\n"
        f"purpose: {purpose}\n"
        f"base_sha: {base_sha}\n"
        f"sprint_tag: 2026-10-16_public-profiles\n"
    )
    bundle_bytes = body_text.encode("utf-8")
    b_sha = sha256_bytes(bundle_bytes)
    prefix8 = b_sha[:8]
    sentinels[turn_id] = prefix8

    full_bundle = bundle_bytes + f'<<<END_RESPONSE bundle="{prefix8}">>>\n'.encode("utf-8")
    (tdir / "bundle.txt").write_bytes(full_bundle)

    meta = {
        "turn_id": turn_id,
        "role": role,
        "purpose": purpose,
        "base_sha": base_sha,
        "solution_key_sha256": sol_key_sha,
        "files": [],
        "bundle_sha256": b_sha,
        "created": "2026-10-16T00:00:00+00:00",
        "model_hint": "auto",
    }
    (tdir / "bundle.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

# 2. Build Good Responses
sprint_toml_content = (
    'live_run = "none"\n'
    'approval_live_run = "architect"\n'
    'solution_key_exposure = "full"\n'
    'min_attempts_before_block = 2\n'
    'max_epochs = 3\n'
    'repo_test_cmd = "python3 -m pytest test -q -rf"\n\n'
    '[max_attempts]\n'
    'oracle = 3\n'
    'implementer = 2\n'
    'live = 2\n'
    'curator = 2\n\n'
    '[hard_cap.implementer]\n'
    'wall_clock = "45m"\n'
    'turns = 60\n'
)
sol_key_content = (sprint_dir / "solution_key.patch").read_text(encoding="utf-8")

resp_intake = (
    f'<<<FILE path="sprint.toml">>>\n{sprint_toml_content}<<<END_FILE>>>\n'
    f'<<<FILE path="solution_key.patch">>>\n{sol_key_content}<<<END_FILE>>>\n'
    f'<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n'
)
(responses_dir / "good_architect_intake.txt").write_text(resp_intake, encoding="utf-8")

challenger_blocks = []
challenger_outputs = {}

scope_text = (sprint_dir / "oracle" / "scope.txt").read_text(encoding="utf-8")
challenger_blocks.append(f'<<<FILE path="oracle-draft/scope.txt">>>\n{scope_text}<<<END_FILE>>>\n')
challenger_outputs["oracle-draft/scope.txt"] = sha256_bytes(scope_text.encode("utf-8"))

cov_text = (sprint_dir / "oracle" / "coverage.md").read_text(encoding="utf-8")
challenger_blocks.append(f'<<<FILE path="oracle-draft/coverage.md">>>\n{cov_text}<<<END_FILE>>>\n')
challenger_outputs["oracle-draft/coverage.md"] = sha256_bytes(cov_text.encode("utf-8"))

crit_text = (sprint_dir / "oracle" / "oracle-critique.md").read_text(encoding="utf-8")
challenger_blocks.append(f'<<<FILE path="oracle-draft/oracle-critique.md">>>\n{crit_text}<<<END_FILE>>>\n')
challenger_outputs["oracle-draft/oracle-critique.md"] = sha256_bytes(crit_text.encode("utf-8"))

probe_text = (sprint_dir / "oracle" / "probe.sh").read_text(encoding="utf-8")
challenger_blocks.append(f'<<<FILE path="oracle-draft/probe.sh" mode="exec">>>\n{probe_text}<<<END_FILE>>>\n')
challenger_outputs["oracle-draft/probe.sh"] = sha256_bytes(probe_text.encode("utf-8"))

for pf in sorted((sprint_dir / "oracle" / "proofs").glob("*.sh")):
    p_text = pf.read_text(encoding="utf-8")
    rel = f"oracle-draft/proofs/{pf.name}"
    challenger_blocks.append(f'<<<FILE path="{rel}" mode="exec">>>\n{p_text}<<<END_FILE>>>\n')
    challenger_outputs[rel] = sha256_bytes(p_text.encode("utf-8"))

for mf in sorted((sprint_dir / "oracle" / "mutants").glob("*.patch")):
    m_text = mf.read_text(encoding="utf-8")
    rel = f"oracle-draft/mutants/{mf.name}"
    challenger_blocks.append(f'<<<FILE path="{rel}">>>\n{m_text}<<<END_FILE>>>\n')
    challenger_outputs[rel] = sha256_bytes(m_text.encode("utf-8"))

resp_challenger = "".join(challenger_blocks) + f'<<<END_RESPONSE bundle="{sentinels["challenger-1"]}">>>\n'
(responses_dir / "good_challenger.txt").write_text(resp_challenger, encoding="utf-8")

dec_lock = '{\n  "decision": "lock_oracle",\n  "feedback": "All requirements verified."\n}\n'
resp_rev_lock = (
    f'<<<FILE path="oracle-decision.json">>>\n{dec_lock}<<<END_FILE>>>\n'
    f'<<<END_RESPONSE bundle="{sentinels["architect-2"]}">>>\n'
)
(responses_dir / "good_architect_review_lock.txt").write_text(resp_rev_lock, encoding="utf-8")

dec_revise = '{\n  "decision": "revise_oracle",\n  "feedback": "Avatar check needs tightening."\n}\n'
resp_rev_revise = (
    f'<<<FILE path="oracle-decision.json">>>\n{dec_revise}<<<END_FILE>>>\n'
    f'<<<END_RESPONSE bundle="{sentinels["architect-2"]}">>>\n'
)
(responses_dir / "good_architect_review_revise.txt").write_text(resp_rev_revise, encoding="utf-8")

# 3. Variants
(responses_dir / "variant_fenced.txt").write_text(f"```markdown\n{resp_intake}```\n", encoding="utf-8")
(responses_dir / "variant_crlf_bom.txt").write_bytes(b"\xef\xbb\xbf" + resp_rev_lock.replace("\n", "\r\n").encode("utf-8"))

# 4. Bad Responses (Static)
bad_cases = {
    "bad_truncated": (resp_intake[: len(resp_intake) // 2], "architect-intake", "architect-1", "E_TRUNCATED"),
    "bad_no_sentinel": (resp_intake.replace(f'<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', ""), "architect-intake", "architect-1", "E_TRUNCATED"),
    "bad_wrong_bundle": (resp_intake.replace(f'bundle="{sentinels["architect-1"]}"', 'bundle="00000000"'), "architect-intake", "architect-1", "E_BUNDLE_MISMATCH"),
    "bad_syntax_marker": (resp_intake.replace(f'bundle="{sentinels["architect-1"]}"', f'bundle={sentinels["architect-1"]}'), "architect-intake", "architect-1", "E_SYNTAX_MARKER"),
    "bad_path_traversal": (f'<<<FILE path="../escape.txt">>>\ndata\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_PATH"),
    "bad_dup_path": (f'<<<FILE path="sprint.toml">>>\na\n<<<END_FILE>>>\n<<<FILE path="sprint.toml">>>\nb\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_DUPLICATE"),
    "bad_search_nomatch": (f'<<<PATCH path="api/users.py">>>\n<<<<<<< SEARCH\nNON_EXISTENT_FUNCTION_XYZ()\n=======\nREPLACEMENT\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_SEARCH_NOMATCH"),
    "bad_search_multi": (f'<<<PATCH path="api/users.py">>>\n<<<<<<< SEARCH\ndef \n=======\ndef replaced_\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_SEARCH_MULTI"),
    "bad_patch_apply": (f'<<<PATCH path="api/users.py">>>\n<<<<<<< SEARCH\nUSERS = {{}}\n<<<END_PATCH>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_PATCH_APPLY"),
    "bad_json": (f'<<<FILE path="oracle-decision.json">>>\n{{"decision": invalid_json\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="{sentinels["architect-2"]}">>>\n', "architect-review", "architect-2", "E_JSON"),
    "bad_toml": (f'<<<FILE path="sprint.toml">>>\nlive_run = = "none"\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_TOML"),
    "bad_schema": (f'<<<FILE path="oracle-decision.json">>>\n{{"decision": "unknown_decision", "feedback": null}}\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="{sentinels["architect-2"]}">>>\n', "architect-review", "architect-2", "E_SCHEMA"),
    "bad_shell_syntax": (resp_challenger.replace('python3 -m api.cli', 'if [[ then'), "challenger", "challenger-1", "E_SHELL_SYNTAX"),
    "bad_scope": (resp_challenger.replace('ALLOW: api/profile.py', 'ALLOW: **'), "challenger", "challenger-1", "E_SCOPE"),
    "bad_coverage": (resp_challenger.replace('R3 -> 03_private_404.sh\n', ''), "challenger", "challenger-1", "E_COVERAGE"),
    "bad_missing_required": (f'<<<FILE path="solution_key.patch">>>\n{sol_key_content}<<<END_FILE>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_MISSING_REQUIRED"),
    "bad_exists": (f'<<<PATCH path="api/users.py" new="true">>>\n<<<<<<< SEARCH\n=======\nnew_content\n>>>>>>> REPLACE\n<<<END_PATCH>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n', "architect-intake", "architect-1", "E_EXISTS"),
}

for name, (body, purpose, turn, err_code) in bad_cases.items():
    (responses_dir / f"{name}.txt").write_text(body, encoding="utf-8")

# 5. Dynamic generation of bad_size.txt (1.05 MB on disk, excluded from git & bundle)
bad_size_content = f'<<<FILE path="sprint.toml">>>\n{"A" * 1050000}\n<<<END_FILE>>>\n<<<END_RESPONSE bundle="{sentinels["architect-1"]}">>>\n'
(responses_dir / "bad_size.txt").write_text(bad_size_content, encoding="utf-8")

# 6. Build expected.d/s2.json
intake_outputs = {
    "sprint.toml": sha256_bytes(sprint_toml_content.encode("utf-8")),
    "solution_key.patch": sha256_bytes(sol_key_content.encode("utf-8")),
}
lock_outputs = {
    "oracle-decision.json": sha256_bytes(dec_lock.encode("utf-8")),
}
revise_outputs = {
    "oracle-decision.json": sha256_bytes(dec_revise.encode("utf-8")),
}

expected_responses = {
    "good_architect_intake": {"purpose": "architect-intake", "turn": "architect-1", "expect": {"exit": 0, "error_code": None, "output_hashes": intake_outputs}},
    "good_challenger": {"purpose": "challenger", "turn": "challenger-1", "expect": {"exit": 0, "error_code": None, "output_hashes": challenger_outputs}},
    "good_architect_review_lock": {"purpose": "architect-review", "turn": "architect-2", "expect": {"exit": 0, "error_code": None, "output_hashes": lock_outputs}},
    "good_architect_review_revise": {"purpose": "architect-review", "turn": "architect-2", "expect": {"exit": 0, "error_code": None, "output_hashes": revise_outputs}},
    "variant_fenced": {"purpose": "architect-intake", "turn": "architect-1", "expect": {"exit": 0, "error_code": None, "output_hashes": intake_outputs}},
    "variant_crlf_bom": {"purpose": "architect-review", "turn": "architect-2", "expect": {"exit": 0, "error_code": None, "output_hashes": lock_outputs}},
}

for name, (body, purpose, turn, err_code) in bad_cases.items():
    expected_responses[name] = {"purpose": purpose, "turn": turn, "expect": {"exit": 2, "error_code": err_code, "output_hashes": {}}}

expected_responses["bad_size"] = {"purpose": "architect-intake", "turn": "architect-1", "expect": {"exit": 2, "error_code": "E_SIZE", "output_hashes": {}}}

expected_doc = {"responses": expected_responses}
(golden_dir / "expected.d" / "s2.json").write_text(json.dumps(expected_doc, indent=2) + "\n", encoding="utf-8")
print("SUCCESS: make_responses.sh generated all turns, responses, and expected.d/s2.json")
PY_INNER
