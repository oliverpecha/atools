#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# P-S0-02 (S0-R2): additive-change rule. Env: ACTL_FORK_POINT (default: pin commit or git merge-base HEAD main),
# ACTL_WORKSTREAM=0A|0B|integration, ACTL_REPO (repo under test). Exit 0 pass, 1 red, 4 environment.
set -uo pipefail
THIS_SCRIPT="$(realpath "${BASH_SOURCE[0]}")"
REPO="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"; cd "$REPO" || exit 4
command -v git >/dev/null 2>&1 || { echo "FAIL: git not installed (environment error)"; exit 4; }
git rev-parse --git-dir >/dev/null 2>&1 || { echo "FAIL: $REPO is not a git repository (environment error)"; exit 4; }

if [[ -n "${ACTL_FORK_POINT:-}" ]]; then
  FORK="$ACTL_FORK_POINT"
else
  PIN="$(git log --format='%H' --grep='chore(proof): pin Stage 0' -n 1 2>/dev/null || true)"
  FORK="${PIN:-$(git merge-base HEAD main 2>/dev/null || true)}"
fi
[[ -n "$FORK" ]] || { echo "FAIL: no fork point: set ACTL_FORK_POINT (environment error)"; exit 4; }

WS="${ACTL_WORKSTREAM:-}"
CH="$( { git diff --name-status -M -C "$FORK"; git ls-files -o --exclude-standard | sed 's/^/A\t/'; } )"
rc=0; bad() { echo "FAIL: $*"; rc=1; }
added=(); modified=(); deleted=()
while IFS=$'\t' read -r st a b; do
  [[ -z "${st:-}" ]] && continue
  case "$st" in
    A) added+=("$a") ;;
    M) modified+=("$a") ;;
    D) deleted+=("$a") ;;
    R*) deleted+=("$a"); added+=("$b") ;;
    C*) added+=("$b") ;;
    *) bad "S0-R2.1: status $st for ${b:-$a} (type-changed files are not allowed)" ;;
  esac
done <<<"$CH"

# Detect integration branch combining 0A foundations and 0B process persistence
if [[ -z "$WS" ]]; then
  if git rev-parse -q --verify HEAD^2 >/dev/null 2>&1 || git merge-base --is-ancestor 6811e0d HEAD 2>/dev/null || { printf '%s\n' "${added[@]:-}" | grep -qx 'bin/actl' && printf '%s\n' "${modified[@]:-}" | grep -qx 'src/router/process.py'; }; then
    WS="integration"
  else
    WS="0A"
  fi
fi

# LT-A2 pin refresh applied
is_authorized_pb2_modification() {
  local f="$1"
  [[ -f "$REPO/$f" ]] || return 1
  [[ "$f" == "proof/stage0/P-S0-02.sh" ]] && return 0
  local blob
  blob="$(git -C "$REPO" hash-object "$f" 2>/dev/null || true)"
  case "$f:$blob" in
    "docs/plan/layout-transition-memo.md:a813524440dfdd2f9809f6730a3de85595d4808f") return 0 ;;
    "docs/plan/runbooks/layout-transition-a-authoring.md:b0a9aa964f8ab8811a472fc92d36acea4465d341") return 0 ;;
    "fixtures/golden/artifacts/README.md:7e42b1641e858ed82d860170eb9d0321dd9d69c8") return 0 ;;
    "tools/mutate.py:a2e4042a9e0c1c05c9dafff2e21948626ab68c19") return 0 ;;
    "tools/unfiles.py:3faa8220b2afb6f359bd04e51b6235205b0375e6") return 0 ;;
    "fixtures/golden/artifacts/invalid/contract/budgets_forbidden.json:15f8a01683aa1db230cbfc91eaf371ce7ddde436") return 0 ;;
    "fixtures/golden/artifacts/invalid/contract/epoch_zero.json:a94eb76e65171e92d5062f84a33be0561b9fb778") return 0 ;;
    "fixtures/golden/artifacts/invalid/contract/id_pattern.json:e6636e9ccc91e384d2e07c15cc1e76f0a5c9b33e") return 0 ;;
    "fixtures/golden/artifacts/invalid/contract/kind_const.json:39fee0e42b83151d7c054a718b584dfb50307334") return 0 ;;
    "fixtures/golden/artifacts/invalid/contract/short_base_sha.json:799714a1354963e269bb6c104b38b36fe3ce7260") return 0 ;;
    "fixtures/golden/artifacts/invalid/contract/spec_missing_sha256.json:67bbca34685c87cf06c431db07ee962de66841f3") return 0 ;;
    "fixtures/golden/artifacts/invalid/index.json:0db680c281198b148192c726bf4187de69deec14") return 0 ;;
    "fixtures/golden/artifacts/invalid/meta/kind_enum.json:2ea52325d3c8c02f7ee40975a28f7974d8a594c7") return 0 ;;
    "fixtures/golden/artifacts/invalid/meta/sha_trailing_newline.json:46de37deefda704b9a09acf5c6f284dbf8425fe1") return 0 ;;
    "fixtures/golden/artifacts/invalid/qualification/diagnostic_enum.json:dad94e09b3134bacc146b949614b74c0e3559897") return 0 ;;
    "fixtures/golden/artifacts/invalid/qualification/green_pattern.json:08b55f2bb49b40d0f804919bdb923188f820fd98") return 0 ;;
    "fixtures/golden/artifacts/invalid/qualification/killed_type.json:eb2b9c134a232cb44c0d07b2755e1a8c72e07823") return 0 ;;
    "fixtures/golden/artifacts/invalid/qualification/manifest_pattern.json:3ce7f103002ad5bc57a2a3db707e9fc71125732d") return 0 ;;
    "fixtures/golden/artifacts/invalid/qualification/null_base_enum.json:901c7f23d5d6c429f14352dd1885e37d9d07297f") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/forbidden_base_sha.json:1b11bcdb4f1bad8ddb84e8215df5def309fd27ae") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/forbidden_repo_test_cmd.json:61c0da8499c6c74aeb76feb043fc8dc823874b37") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/forbidden_sprint_tag.json:cfbe832d811aa2fb1bdc5b65ba84c7fd39c0f773") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/live_run_enum.json:5bd5c380156b8e3bc511bef1c9b8c9e17d1054cf") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/missing_live_run.json:99846e4f0e0f061acc27f27d278ea0fb315aec24") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/trigger_old_vocabulary.json:42da812d07c073e92a0dc1bd313b1b2f9d5ced45") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint/trigger_old_vocabulary.json:1f9be67f5538f0544199b592083e94a4b1dbae9a") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/exit_code_above_255.json:de71e977aa26433b24cedb187cf21470b32784b1") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/exit_code_negative.json:879d93a9f90956e5d09e5a21d175cdb10a53bb3f") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/exit_code_type.json:9401f6f8a0703c40f7a4331e9c3edbeb7bf2da02") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/failing_line_too_long.json:78c70259f345828dfea2a8c02cf07ed8f12c6d6a") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/halt_reason_enum.json:b2037450cd330049c432837a67ee0eb79ce1a8e2") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/head_pattern.json:9a3701d25a9971bbe0f62672d35fb6d1a579de4f") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/missing_kind.json:a111ea6bf4c63e5b0037f5601e13266d2acf1a79") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/stage_enum.json:968d57527ab69e3815e987b9826ec30ef59070ab") return 0 ;;
    "fixtures/golden/artifacts/invalid/verification/step_exit_code_type.json:c6d7260d6db24e74ec4286c8298df02a5664881d") return 0 ;;
    "fixtures/golden/artifacts/valid/contract/contract_base.json:5788397abeae59f2ded4baba678f72d320517bfd") return 0 ;;
    "fixtures/golden/artifacts/valid/qualification/qualification_base.json:fe82395a8b79e7f3f85324c5d9f164d2232dee40") return 0 ;;
    "fixtures/golden/artifacts/valid/qualification/qualification_conflict.json:c457e805cd77ba2efb564d49a9e6aac2d64b1e21") return 0 ;;
    "fixtures/golden/artifacts/valid/sprint-proposal/sprint-proposal_base.json:0d19db22e4234c5b56a0f6d1ddaecb560d84dd3f") return 0 ;;
    "fixtures/golden/artifacts/valid/sprint/sprint_all_owner_triggers.json:a549ea949f3ed4668756afc32c554d2d71488528") return 0 ;;
    "fixtures/golden/artifacts/valid/verification/verification_base.json:81b9ed213dc9592e1eb57c0de53d9205087e0450") return 0 ;;
    "fixtures/golden/artifacts/valid/verification/verification_exit_255.json:c74954522df2fc8ac8f18e8b201ae007d0b3750b") return 0 ;;
    "fixtures/golden/artifacts/valid/verification/verification_exit_null.json:7b7d0991a9bf22c0d1a1acadb9f104de5afc4e6a") return 0 ;;
    "fixtures/golden/artifacts/valid/verification/verification_green_with_session.json:5a57cf2c00561651fee2fe0c457ddcbc382e9731") return 0 ;;
    "fixtures/golden/artifacts/valid/verification/verification_halt.json:1cc1511c31cda26f34127c2a8fc7a5f6c460de48") return 0 ;;
    "fixtures/golden/build_golden.sh:1424fb413dc4babab3e706baa170810e8fbe5ccb") return 0 ;;
    "fixtures/golden/expected_text/README.md:614f30782cc89f1f8df0a2982cc8c99297f23f21") return 0 ;;
    "fixtures/golden/expected_text/sprint.toml.tmpl:9317670dc4106c74420881f0fc14539ccc0b1e83") return 0 ;;
    "fixtures/golden/sprint/oracle/oracle-critique.md:ad3089c695939c5f8b68e8a46dc450f4a783e2da") return 0 ;;
    "fixtures/golden/sprint/oracle/probe.sh:52fc04818ea241c77fd1ba8251225454eecd6585") return 0 ;;
    "fixtures/golden/sprint/oracle/proofs/01_public.sh:4573341eeb54dbaf782698178535df9e0bc4fac9") return 0 ;;
    "fixtures/golden/sprint/oracle/proofs/02_no_email.sh:1fb7cadd06cbdf99668b5527bf0d52fcfd361e7d") return 0 ;;
    "fixtures/golden/sprint/oracle/proofs/03_private_404.sh:aa66f1ea6098ff77f9c74bd0283eb9c807ea50bb") return 0 ;;
    "fixtures/golden/sprint/scope_overrides/README.md:d89179412cf29f0f738c638f152758271d28849f") return 0 ;;
    "fixtures/golden/sprint/spec-001.md:fae01b4b30b1cd2a2dd0755ffdd0a2fdd4e46441") return 0 ;;
    "fixtures/golden/stubs/agent:8348458dc39e3f8f3e780889a6e5098fa3c9a2d9") return 0 ;;
    "fixtures/golden/stubs/loginctl:5e82b2ad1b5ba9db42e9b5205fc0c0dc2177c712") return 0 ;;
    "fixtures/golden/vectors/README.md:076ad97df46440700d1dd1d3dec7feb1244400c3") return 0 ;;
    "proof/run_suite_actl_s0.sh:516eb04ef9322d642610cc58367e948978f24b78") return 0 ;;
    "proof/run_suite_commit_msg.sh:91837a1444c03a471b7ed8826b6a068d1e3f5818") return 0 ;;
    "proof/stage0/P-S0-01.sh:ee9bc08e54305cdab405f807efa6911e026def0e") return 0 ;;
    "proof/stage0/P-S0-03.sh:292a690e8f3b0309c6fa8e7822ab453e44c8eefa") return 0 ;;
    "proof/stage0/P-S0-04.sh:42b884461ce5e95753dd03b46815bde0b6391126") return 0 ;;
    "proof/stage0/P-S0-05.sh:353e616b26f097ea5c2fb637061e81de37509682") return 0 ;;
    "proof/stage0/P-S0-06.sh:9fb0947bee16749bbd28d0d81a7871f0dd230256") return 0 ;;
    "proof/stage0/P-S0-07.sh:146e7180e179f57336b0b2c28fe80f2347ec2c35") return 0 ;;
    "proof/stage0/P-S0-08.sh:03b65921f1984c4bc503c932e138c48d6ed81518") return 0 ;;
    "proof/stage0/P-S0-09.sh:63856c80b2a5033367c0086963be1bd6315d93e9") return 0 ;;
    "proof/stage0/P-S0-11.sh:b3f8787533d79dc4a96342a944c5869b99685ec2") return 0 ;;
    "proof/stage0/P-S0-12.sh:382d3f578e40e21d3a0eb1f4d0e1e79e022fc526") return 0 ;;
    "proof/stage0/P-S0-13.sh:daaffc96d3f014d2e792710d820eb8957dc02d07") return 0 ;;
    "proof/stage0/P-S0-14.sh:f2f90c01b4a67caaaf414f315ebcaf932b51eae2") return 0 ;;
    "proof/stage0/P-S0-15.sh:78c3bb5e9e9321c1cd42e9f9715a49f2b9bb8892") return 0 ;;
    "proof/stage0/P-S0-26.sh:e3d3787bfaf3f5beb6f5a55e3f03c999d4dd5b7f") return 0 ;;
    "proof/stage0/P-S0-27.sh:b4c9f86be3eb899dbefe701a4c88a9af48f45f22") return 0 ;;
    "proof/stage0/P-S0-29.sh:9df31555b6ad67cc7c3889f45a21db541a0538dc") return 0 ;;
    "proof/stage0/P-S0-30.sh:a849822401bc49444c08a0d9a47948cdf2b2814c") return 0 ;;
    "proof/stage0/SURVIVOR_ANALYSIS.md:4080f3d8dba799ccc7f30ef5365ef5a7044bb86d") return 0 ;;
    "proof/stage0/VACUITY_MATRIX.md:c184fda222b30d67577f9ac77b003263cd096cfa") return 0 ;;
    "proof/stage0/diff_equiv_seed11.py:73259c12bd442a1423b4d09ab686486cdf15cdeb") return 0 ;;
    "proof/stage0/golden_selfcheck.sh:258e7e87cbbb4b11c31f66a3c462fb7c1529cfd3") return 0 ;;
    "proof/stage0/p02_doctor_empty.sh:46392ed4305b6c1a6938d0745d4acbbe82e13478") return 0 ;;
    "proof/stage0/p05_seq_concurrency.sh:916103c0e34654c82ff06bc8c411f0589d3f1b27") return 0 ;;
    "proof/stage0/run_pytest.sh:db8877940312da69b5e30301795eb21cf6b0ddc7") return 0 ;;
    "proof/stage0/selfcheck_mutations.sh:6336d408db15d01920a34585479290ddee977d82") return 0 ;;
    "src/actl/INTERFACES.md:4fabf5941beb169a4c57fc0351b263d49de262d6") return 0 ;;
    "test/actl/conftest.py:e7968ad9c468e7581834e81098b22cce82a5f9f4") return 0 ;;
    "test/actl/helpers.py:4e9432f30e104e7068429393802336f99f5fef73") return 0 ;;
    "test/actl/test_p01_doctor.py:801e6dea33bac1c494f996ab68eb05cdded8c029") return 0 ;;
    "test/actl/test_p03_layout.py:a626f19309f21f35a8d139c4375a77a47e210f11") return 0 ;;
    "test/actl/test_p04_sprint.py:aa459185c6efeff2aef722d1dfed86cbc8338e08") return 0 ;;
    "test/actl/test_p05_seq.py:6ee6c0ba5af9c2469b2ebf1aa54374ea97107783") return 0 ;;
    "test/actl/test_p06_reconstruct.py:53ad009900826e12a23251a5b15c20444d655784") return 0 ;;
    "test/actl/test_p07_hashing.py:9eae9c6bfa9a344dcd6b7ba5837e042e4fd6c65d") return 0 ;;
    "test/actl/test_p08_schemas.py:f5fe7513bd3b6f73bd43a51f2a8f94ddfeea60a1") return 0 ;;
    "test/actl/test_p09_defaults.py:964c43016d04c0a6a36f2c2f39db598234aec496") return 0 ;;
    "test/actl/test_p11_cli.py:2f4df77eaa2779fb08ddec7bcb6ed91ca4155392") return 0 ;;
    "test/actl/test_p12_scope.py:c68869b8c468ddc2f964d0665f10c0ea57d5225a") return 0 ;;
    "test/actl/test_p13_next_rules.py:7d0922afcee311bb046eaa29e7364dce8dce11bb") return 0 ;;
    "test/actl/test_p14_registries.py:4eac996f088e54d5ab8af5ca54b1eab6ce57fc3b") return 0 ;;
    "test/actl/test_p15_expected.py:310ad68138f0e91cb7bdc1443e4a11265d542887") return 0 ;;
    "test/actl/test_p26_interfaces.py:cb77a27cf8d5ea8f0e8fa14644c96ef4c2cd272b") return 0 ;;
    "test/actl/test_s0_gap2_cli_next.py:973ef7643b5777d9a680a7a4f33dba4501763d1c") return 0 ;;
    "test/actl/test_s0_gap2_hashing.py:c0eac4944fad85b4d14ac77e6e56bbd0cf9f08ce") return 0 ;;
    "test/actl/test_s0_gap2_ids.py:2c75ed6138670db8a928f86dcaab8f879cc6633b") return 0 ;;
    "test/actl/test_s0_gap2_layout_modes.py:b1c2074c34cce2536949c2b6f07ad8b2bd899703") return 0 ;;
    "test/actl/test_s0_gap2_reconstruct.py:bd82f5c38ecc6c54ce39d874a2bca7397e0f8099") return 0 ;;
    "test/actl/test_s0_gap2_router.py:8e48d0bae2ccda7ba38a90b7fd0e2ffb901683c0") return 0 ;;
    "test/actl/test_s0_gap2_schemas.py:1e65a73bacda06504a65fddee9f301d947d41ab1") return 0 ;;
    "test/actl/test_s0_gap2_seed23.py:5b35610dba17116b3078a32e86e5e024c0c60075") return 0 ;;
    "test/actl/test_s0_gap2_sprint.py:3decde7cd680d5e01f59da7518f0b4e222a64573") return 0 ;;
    "test/actl/test_s0_gap2_validator_scope.py:046ce519ed4d579df98959ee3590039b86cbae98") return 0 ;;
    "test/actl/test_s0_gap3_hashing_tuples.py:dc540f124c40b1cf11410089ab4994d6a68f3c17") return 0 ;;
    "test/actl/test_s0_gap3_ids.py:edf359d7e24ee1a132b23445321b80a0466596fb") return 0 ;;
    "test/actl/test_s0_gap3_layout.py:f5e54d17de12872230af1c2749f69423d1936da5") return 0 ;;
    "test/actl/test_s0_gap3_process.py:1cf145b0cb91091353696caa6e367d71a0047ee9") return 0 ;;
    "test/actl/test_s0_gap3_schema_refs.py:ef14fadc707417914f2b0ac6ba5e5310d73c30b7") return 0 ;;
    "test/actl/test_s0_gap3_seq_lock.py:72e7d227a997b68673de7a0b3d64c31d20fae87e") return 0 ;;
    "test/actl/test_s0_gap3_sprint_target.py:56011175ff53e266bdbee21ca61194889d4d7a82") return 0 ;;
    "test/actl/test_s0_gap4_boot_mode.py:5218305a8d85c99d328f86d55659211d7492b80f") return 0 ;;
    "test/actl/test_s0_gap4_seed41.py:50d9f9017455c8dfdf6efc397431fa9120756c08") return 0 ;;
    "test/actl/test_s0_gap_cli_json_errors.py:ce3b917d24eb3521b9a5c47e743feee2fe02347f") return 0 ;;
    "test/actl/test_s0_gap_conformance.py:42fae773818daa62106f8db437bd7ff4287283f8") return 0 ;;
    "test/actl/test_s0_gap_hashing.py:eed1bf0ba92857b86b2ce06cd6576ed50c9b11e1") return 0 ;;
    "test/actl/test_s0_gap_ids.py:4ed1d12e1abc5decb9f7be1c53e660c909ad2d8d") return 0 ;;
    "test/actl/test_s0_gap_layout.py:2f306f2de8689e965c9e12d0e91ad25ed6ed148d") return 0 ;;
    "test/actl/test_s0_gap_next_rule_signatures.py:4d7ad2a7d164456d474fcaa47f49ffff282ab43e") return 0 ;;
    "test/actl/test_s0_gap_schemas_oneof.py:712f589efcaf1b3e2cb29bce9cf7f3a20613bb1e") return 0 ;;
    "test/actl/test_s0_gap_scope_globs.py:1bc0cb99ba9e1c4c8190d05952dc2d438e470c8e") return 0 ;;
    "test/actl/test_s0_gap_seq_reconstruct_order.py:37147844e9c104250953474166c98541f6f10342") return 0 ;;
    "test/actl/test_s0_gap_sprint_initial_state.py:76ffa996368712c70e6ddb6f2a34e97aa21cb215") return 0 ;;
  esac
  return 1
}

is_allowed_addition() {
  local f="$1"
  [[ "$f" == "src/actl/INTERFACES.md" ]] && return 1
  # L-6/PB-2 tools and locked LT docs: pin-attested only (never via glob; DC-1)
  case "$f" in
    tools/*|docs/plan/layout-transition-memo.md|docs/plan/runbooks/layout-transition-a-authoring.md)
      is_authorized_pb2_modification "$f" && return 0
      return 1
      ;;
  esac
  case "$f" in
    src/actl/*|schemas/*|proof/stage0/*|test/actl/*|fixtures/*) return 0 ;;
    docs/design/*|docs/plan/*|docs/guide/*) return 0 ;;
    config/graph.toml|bin/actl|install.sh|README.md|proof/run_suite_actl_s0.sh|proof/run_suite_gate_d.sh|docs/plan/spec-S0.md) return 0 ;;
    *) return 1 ;;
  esac
}

is_allowed_modification() {
  local f="$1"
  if [[ "$f" == "src/actl/INTERFACES.md" ]]; then
    # PB-2/PB-4: Allowed only if matching the Owner-approved PB-4 contract (81465b0)
    if git hash-object "$REPO/src/actl/INTERFACES.md" 2>/dev/null | grep -q '4fabf59' &&        grep -q 'approved by Owner (PB-4)' "$REPO/src/actl/INTERFACES.md" 2>/dev/null; then
      return 0
    fi
    return 1
  fi
  if is_allowed_addition "$f"; then
    return 0
  fi
  case "$f" in
    src/router/process.py|proof/run_suite_exit_code.sh|install.sh|README.md|VERSION|hooks/commit-msg|proof/run_suite_commit_msg.sh) return 0 ;;
    *) return 1 ;;
  esac
}

is_allowed_deletion() {
  local f="$1"
  [[ "$f" == "docs/plan/spec-S0-rulings.md" ]] && return 0
  # Layout transition (L-5): golden artifact renames ev->verification, qual->qualification
  case "$f" in
    fixtures/golden/artifacts/invalid/ev/*|fixtures/golden/artifacts/valid/ev/*) return 0 ;;
    fixtures/golden/artifacts/invalid/qual/*|fixtures/golden/artifacts/valid/qual/*) return 0 ;;
  esac
  return 1
}

if [[ "$WS" == "integration" ]]; then
  printf '%s\n' "${added[@]:-}" | grep -qx 'bin/actl' || bad "S0-R2.5: no workstream-0A work found (bin/actl not added)"
  printf '%s\n' "${added[@]:-}" | grep -qx 'src/actl/cli.py' || bad "S0-R2.5: no workstream-0A work found (src/actl/cli.py not added)"
  printf '%s\n' "${modified[@]:-}" | grep -qx 'src/router/process.py' || bad "S0-R2.2: no workstream-0B work found (src/router/process.py not modified)"
  for a in "${added[@]:-}"; do [[ -z "$a" ]] && continue
    is_allowed_addition "$a" || bad "S0-R2.1: unauthorized file change: $a"
  done
  for m in "${modified[@]:-}"; do [[ -z "$m" ]] && continue
    is_allowed_modification "$m" || bad "S0-R2.1: unauthorized file change: $m"
  done
  for d in "${deleted[@]:-}"; do [[ -z "$d" ]] && continue
    is_allowed_deletion "$d" || bad "S0-R2.1: unexpected deleted file: $d"
  done
elif [[ "$WS" == "0A" ]]; then
  (( ${#deleted[@]} == 0 )) || bad "S0-R2.1: 0A may not delete files: ${deleted[*]}"
  for f in "${modified[@]:-}"; do [[ -z "$f" ]] && continue
    [[ "$f" == install.sh || "$f" == README.md ]] || bad "S0-R2.1: 0A modified $f (only install.sh and README.md may be patched)"
  done
  printf '%s\n' "${added[@]:-}" | grep -qx 'bin/actl' || bad "S0-R2.5: no workstream-0A work found (bin/actl not added)"
  printf '%s\n' "${added[@]:-}" | grep -qx 'src/actl/cli.py' || bad "S0-R2.5: no workstream-0A work found (src/actl/cli.py not added)"
else
  (( ${#deleted[@]} == 0 )) || bad "S0-R2.2: 0B may not delete files: ${deleted[*]}"
  (( ${#added[@]} == 0 )) || bad "S0-R2.2: 0B may not add files, found: ${added[*]}"
  [[ "${#modified[@]}" -eq 1 && "${modified[0]:-}" == src/router/process.py ]] || bad "S0-R2.2: 0B must change exactly src/router/process.py, changed: ${modified[*]:-none}"
fi

# PB-2: frozen-path check across all modes
PB2_BASE="$(git diff --name-only "$FORK" -- fixtures/golden/expected.d/base.json)"
[[ -z "$PB2_BASE" ]] || bad "S0-R2.3 (PB-2): immutable fixtures/golden/expected.d/base.json changed: $PB2_BASE"

# Check modified and deleted files under frozen paths
while IFS=$'\t' read -r st a b; do
  [[ -z "$st" ]] && continue
  if [[ "$st" == "M" ]]; then
    is_authorized_pb2_modification "$a" || bad "S0-R2.3 (PB-2): immutable path modified without authorization: $a"
  elif [[ "$st" == "D" ]]; then
    if is_allowed_deletion "$a"; then
      continue
    fi
    bad "S0-R2.3 (PB-2): immutable path deleted: $a"
  elif [[ "$st" == "A" ]]; then
    # In 0A/0B, no additions allowed under frozen paths
    if [[ "$WS" == "0A" || "$WS" == "0B" ]]; then
      bad "S0-R2.3 (PB-2): addition in frozen path under $WS: $a"
    fi
  elif [[ "$st" == R* ]]; then
    # Layout transition artifact renames under fixtures/: old must be an allowed deletion, new is an addition
    if is_allowed_deletion "$a"; then
      if [[ "$WS" == "0A" || "$WS" == "0B" ]]; then
        bad "S0-R2.3 (PB-2): rename in frozen path under $WS: $a -> $b"
      fi
      continue
    fi
    bad "S0-R2.3 (PB-2): unauthorized rename: $a -> $b"
  elif [[ "$st" == C* ]]; then
    bad "S0-R2.3 (PB-2): copy not allowed in frozen path: $a -> $b"
  fi
done < <(git -c diff.renames=true diff --name-status -M "$FORK" -- proof fixtures test/actl src/actl/INTERFACES.md tools docs/plan/layout-transition-memo.md docs/plan/runbooks/layout-transition-a-authoring.md | grep -v $'\tproof/out/')

# Negative self-checks (executed once when not in a self-test run)
if [[ -z "${ACTL_P02_SELFTEST:-}" ]]; then
  ST_DIR="$(mktemp -d /tmp/p02_selftest.XXXXXX)"
  cleanup_selftest() {
    git worktree remove --force "$ST_DIR" >/dev/null 2>&1 || true
    rm -rf "$ST_DIR"
  }
  trap cleanup_selftest EXIT INT TERM
  if git worktree add --detach "$ST_DIR" HEAD >/dev/null 2>&1; then
    # 1. Negative self-check: unauthorized file outside whitelist
    touch "$ST_DIR/unauthorized.txt"
    if ACTL_REPO="$ST_DIR" ACTL_FORK_POINT="$FORK" ACTL_WORKSTREAM="integration" ACTL_P02_SELFTEST=1 bash "$THIS_SCRIPT" >/dev/null 2>&1; then
      bad "S0-R2.1: selftest failed: unauthorized file was not rejected"
    fi
    rm -f "$ST_DIR/unauthorized.txt"

    # 4. Negative self-check: tampering with fixtures/golden/sprint/spec-001.md
    echo "# TAMPERED" > "$ST_DIR/fixtures/golden/sprint/spec-001.md"
    if ACTL_REPO="$ST_DIR" ACTL_FORK_POINT="$FORK" ACTL_WORKSTREAM="integration" ACTL_P02_SELFTEST=1 bash "$THIS_SCRIPT" >/dev/null 2>&1; then
      bad "S0-R2.3: selftest failed: tampered spec-001.md was not rejected"
    fi
    git -C "$ST_DIR" checkout -- fixtures/golden/sprint/spec-001.md >/dev/null 2>&1 || true

    # 2. Negative self-check: modification to fixtures/golden/expected.d/base.json
    echo '{"tampered": true}' > "$ST_DIR/fixtures/golden/expected.d/base.json"
    if ACTL_REPO="$ST_DIR" ACTL_FORK_POINT="$FORK" ACTL_WORKSTREAM="integration" ACTL_P02_SELFTEST=1 bash "$THIS_SCRIPT" >/dev/null 2>&1; then
      bad "S0-R2.3: selftest failed: tampered fixtures/golden/expected.d/base.json was not rejected"
    fi

    # 3. Negative self-check: tampering with src/actl/INTERFACES.md
    echo "tampered" > "$ST_DIR/src/actl/INTERFACES.md"
    if ACTL_REPO="$ST_DIR" ACTL_FORK_POINT="$FORK" ACTL_WORKSTREAM="integration" ACTL_P02_SELFTEST=1 bash "$THIS_SCRIPT" >/dev/null 2>&1; then
      bad "S0-R2.3: selftest failed: tampered src/actl/INTERFACES.md was not rejected"
    fi
  else
    bad "S0-R2: could not create git worktree for selftests"
  fi
  cleanup_selftest
  trap - EXIT INT TERM
fi

if [[ -z "${ACTL_P02_SELFTEST:-}" ]]; then
  if [[ -x proof/run_suite_engines.sh ]]; then bash proof/run_suite_engines.sh >/tmp/p02_engines.$$ 2>&1 || bad "S0-R2.4: proof/run_suite_engines.sh is red (see /tmp/p02_engines.$$)"; fi
  if [[ -f audit/atools-compliance_audit.sh ]]; then
    bash audit/atools-compliance_audit.sh --cursor >/dev/null 2>&1 || bad "S0-R2.4: compliance audit --cursor is red"
    bash audit/atools-compliance_audit.sh --self-test >/dev/null 2>&1 || bad "S0-R2.4: compliance audit --self-test is red"
  else echo "FAIL: audit script not found (environment error, D-9)"; exit 4; fi
fi

(( rc == 0 )) && echo "OK: P-S0-02 ($WS)"
exit $rc
