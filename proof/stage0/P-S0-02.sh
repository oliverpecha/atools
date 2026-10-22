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
    *) bad "S0-R2.1: status $st for ${b:-$a} (renamed, copied or type-changed files are not allowed)" ;;
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

is_authorized_pb2_modification() {
  local f="$1"
  [[ -f "$REPO/$f" ]] || return 1
  [[ "$f" == "proof/stage0/P-S0-02.sh" ]] && return 0
  local blob
  blob="$(git -C "$REPO" hash-object "$f" 2>/dev/null || true)"
  case "$f:$blob" in
    "fixtures/golden/artifacts/README.md:7e42b1641e858ed82d860170eb9d0321dd9d69c8") return 0 ;;
    "fixtures/golden/artifacts/invalid/meta/sha_trailing_newline.json:46de37deefda704b9a09acf5c6f284dbf8425fe1") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/forbidden_base_sha.json:1b11bcdb4f1bad8ddb84e8215df5def309fd27ae") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/forbidden_repo_test_cmd.json:61c0da8499c6c74aeb76feb043fc8dc823874b37") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/forbidden_sprint_tag.json:cfbe832d811aa2fb1bdc5b65ba84c7fd39c0f773") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/live_run_enum.json:5bd5c380156b8e3bc511bef1c9b8c9e17d1054cf") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/missing_live_run.json:99846e4f0e0f061acc27f27d278ea0fb315aec24") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint-proposal/trigger_old_vocabulary.json:42da812d07c073e92a0dc1bd313b1b2f9d5ced45") return 0 ;;
    "fixtures/golden/artifacts/invalid/sprint/trigger_old_vocabulary.json:1f9be67f5538f0544199b592083e94a4b1dbae9a") return 0 ;;
    "fixtures/golden/artifacts/valid/sprint-proposal/sprint-proposal_base.json:0d19db22e4234c5b56a0f6d1ddaecb560d84dd3f") return 0 ;;
    "fixtures/golden/artifacts/valid/sprint/sprint_all_owner_triggers.json:a549ea949f3ed4668756afc32c554d2d71488528") return 0 ;;
    "fixtures/golden/build_golden.sh:6e62699099515388843226117d19ef731713cb14") return 0 ;;
    "fixtures/golden/expected_text/README.md:614f30782cc89f1f8df0a2982cc8c99297f23f21") return 0 ;;
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
    "proof/stage0/SURVIVOR_ANALYSIS.md:2c88090f53c872eb0ee5e271e662cf30c00f4600") return 0 ;;
    "proof/stage0/VACUITY_MATRIX.md:c184fda222b30d67577f9ac77b003263cd096cfa") return 0 ;;
    "proof/stage0/golden_selfcheck.sh:bc2da5970922a75dbfaed5b3a20c8a9f9b47d559") return 0 ;;
    "proof/stage0/p02_doctor_empty.sh:46392ed4305b6c1a6938d0745d4acbbe82e13478") return 0 ;;
    "proof/stage0/p05_seq_concurrency.sh:916103c0e34654c82ff06bc8c411f0589d3f1b27") return 0 ;;
    "proof/stage0/run_pytest.sh:db8877940312da69b5e30301795eb21cf6b0ddc7") return 0 ;;
    "proof/stage0/selfcheck_mutations.sh:4b5a564db03ddb0dc85e89504c561108ec238b1b") return 0 ;;
    "src/actl/INTERFACES.md:81465b0bd35c2f2e4559f53a5388cc6bfc000680") return 0 ;;
    "test/actl/conftest.py:e7968ad9c468e7581834e81098b22cce82a5f9f4") return 0 ;;
    "test/actl/helpers.py:4e9432f30e104e7068429393802336f99f5fef73") return 0 ;;
    "test/actl/test_p01_doctor.py:801e6dea33bac1c494f996ab68eb05cdded8c029") return 0 ;;
    "test/actl/test_p03_layout.py:f95bfc7bfd56b7507936046cfbe155a9bbcca6d3") return 0 ;;
    "test/actl/test_p04_sprint.py:aa7fa626e8ce593aed1b5cb345c6f848dc612e5b") return 0 ;;
    "test/actl/test_p05_seq.py:fd0797e19cb33cbd7e76bb8f23375611a3f1ce9c") return 0 ;;
    "test/actl/test_p06_reconstruct.py:8323b06256828f56928d05e02100a746480a78d3") return 0 ;;
    "test/actl/test_p07_hashing.py:9eae9c6bfa9a344dcd6b7ba5837e042e4fd6c65d") return 0 ;;
    "test/actl/test_p08_schemas.py:0f6ce146a3a6666e8a52a169461e60d13b4583f5") return 0 ;;
    "test/actl/test_p09_defaults.py:74ae1d3c2e07f104adf46461b7c50a901d3cdf18") return 0 ;;
    "test/actl/test_p11_cli.py:2f4df77eaa2779fb08ddec7bcb6ed91ca4155392") return 0 ;;
    "test/actl/test_p12_scope.py:c68869b8c468ddc2f964d0665f10c0ea57d5225a") return 0 ;;
    "test/actl/test_p13_next_rules.py:fa200227ac6d083d7c046e909c8911d87dbe1fd8") return 0 ;;
    "test/actl/test_p14_registries.py:7888a2f091332916cb27b7735481a2fe444e447f") return 0 ;;
    "test/actl/test_p15_expected.py:310ad68138f0e91cb7bdc1443e4a11265d542887") return 0 ;;
    "test/actl/test_p26_interfaces.py:cb77a27cf8d5ea8f0e8fa14644c96ef4c2cd272b") return 0 ;;
    "test/actl/test_s0_gap_cli_json_errors.py:ce3b917d24eb3521b9a5c47e743feee2fe02347f") return 0 ;;
    "test/actl/test_s0_gap_conformance.py:42fae773818daa62106f8db437bd7ff4287283f8") return 0 ;;
    "test/actl/test_s0_gap_hashing.py:eed1bf0ba92857b86b2ce06cd6576ed50c9b11e1") return 0 ;;
    "test/actl/test_s0_gap_ids.py:4ed1d12e1abc5decb9f7be1c53e660c909ad2d8d") return 0 ;;
    "test/actl/test_s0_gap_layout.py:2f306f2de8689e965c9e12d0e91ad25ed6ed148d") return 0 ;;
    "test/actl/test_s0_gap_next_rule_signatures.py:4d7ad2a7d164456d474fcaa47f49ffff282ab43e") return 0 ;;
    "test/actl/test_s0_gap_schemas_oneof.py:712f589efcaf1b3e2cb29bce9cf7f3a20613bb1e") return 0 ;;
    "test/actl/test_s0_gap_scope_globs.py:1bc0cb99ba9e1c4c8190d05952dc2d438e470c8e") return 0 ;;
    "test/actl/test_s0_gap_seq_reconstruct_order.py:c499407d61e045cf9cc8c6b53addc0ee40b84b05") return 0 ;;
    "test/actl/test_s0_gap_sprint_initial_state.py:711fe6562783454672db44ab5cfbcdbf1e68b49c") return 0 ;;
  esac
  return 1
}

is_allowed_addition() {
  local f="$1"
  [[ "$f" == "src/actl/INTERFACES.md" ]] && return 1
  case "$f" in
    src/actl/*|schemas/*|proof/stage0/*|test/actl/*|fixtures/*) return 0 ;;
    config/graph.toml|bin/actl|install.sh|README.md|proof/run_suite_actl_s0.sh|proof/run_suite_gate_d.sh|docs/plan/spec-S0.md) return 0 ;;
    *) return 1 ;;
  esac
}

is_allowed_modification() {
  local f="$1"
  if [[ "$f" == "src/actl/INTERFACES.md" ]]; then
    # PB-2/PB-4: Allowed only if matching the Owner-approved PB-4 contract (81465b0)
    if git hash-object "$REPO/src/actl/INTERFACES.md" 2>/dev/null | grep -q '^81465b0' &&        grep -q 'approved by Owner (PB-4)' "$REPO/src/actl/INTERFACES.md" 2>/dev/null; then
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
  [[ "$f" == "docs/plan/spec-S0-rulings.md" ]]
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
while IFS=$'	' read -r st f; do
  [[ -z "$st" ]] && continue
  if [[ "$st" == "M" ]]; then
    is_authorized_pb2_modification "$f" || bad "S0-R2.3 (PB-2): immutable path modified without authorization: $f"
  elif [[ "$st" == "D" ]]; then
    bad "S0-R2.3 (PB-2): immutable path deleted: $f"
  elif [[ "$st" == "A" ]]; then
    # In 0A/0B, no additions allowed under frozen paths
    if [[ "$WS" == "0A" || "$WS" == "0B" ]]; then
      bad "S0-R2.3 (PB-2): addition in frozen path under $WS: $f"
    fi
  fi
done < <(git diff --name-status "$FORK" -- proof fixtures test/actl src/actl/INTERFACES.md | grep -v $'	proof/out/')

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
