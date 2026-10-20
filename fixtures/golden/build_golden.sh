#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# build_golden.sh - deterministic golden target repo + optional sprint install (S0-R9).
#   build_golden.sh <dest-dir>                       build git repo at <dest-dir>, print base_sha
#   build_golden.sh --install-sprint <ACTL_ROOT> [--tag <TAG>]   populate spec-001.md, solution_key-002.patch,
#        oracle-003/, qual-004.json, contract-005.json, runs/state.json (+ frozen sprint.toml, repos/target-repo)
# Uses no actl code, no network, no LLM. Hermetic git: no global/system config, no hooks, fixed identity and dates.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEFAULT_TAG="2026-10-16_public-profiles"
GIT_DATE="2026-01-01T00:00:00+0000"

ggit() {
  GIT_CONFIG_GLOBAL=/dev/null GIT_CONFIG_SYSTEM=/dev/null GIT_CONFIG_NOSYSTEM=1 \
  GIT_AUTHOR_NAME="Golden Fixture" GIT_AUTHOR_EMAIL="golden@example.test" GIT_AUTHOR_DATE="$GIT_DATE" \
  GIT_COMMITTER_NAME="Golden Fixture" GIT_COMMITTER_EMAIL="golden@example.test" GIT_COMMITTER_DATE="$GIT_DATE" \
  git -c core.hooksPath=/dev/null -c core.autocrlf=false -c core.fileMode=true -c init.defaultBranch=main \
      -c commit.gpgsign=false "$@"
}

build_repo() {
  local dest="$1"
  [[ -n "$dest" ]] || { echo "usage: build_golden.sh <dest>" >&2; exit 2; }
  if [[ -e "$dest" ]] && [[ -n "$(ls -A "$dest" 2>/dev/null)" ]]; then
    echo "FAIL: destination $dest exists and is not empty" >&2; exit 2
  fi
  mkdir -p "$dest"
  ( cd "$HERE/target-repo" && find . -type f ! -path '*/__pycache__/*' ! -name '*.pyc' | LC_ALL=C sort ) |
  while IFS= read -r f; do
    mkdir -p "$dest/$(dirname "$f")"; cp "$HERE/target-repo/$f" "$dest/$f"; chmod 644 "$dest/$f"
  done
  ( cd "$dest"
    ggit init -q .
    ggit add -A
    ggit commit -q -m "golden: base (public-profiles target)"
    ggit rev-parse HEAD )
}

sha() { sha256sum "$1" | cut -d' ' -f1; }

manifest_sha() {  # S0-R6 / INTERFACES A-1, reimplemented here without actl code
  python3 - "$1" <<'PY'
import hashlib, os, sys
root = sys.argv[1]; rows = []
for d, _, fs in os.walk(root):
    for f in fs:
        p = os.path.join(d, f)
        assert not os.path.islink(p), p
        rel = os.path.relpath(p, root).replace(os.sep, "/")
        x = "x" if os.stat(p).st_mode & 0o111 else "-"
        rows.append((rel.encode("utf-8"), x, hashlib.sha256(open(p, "rb").read()).hexdigest()))
rows.sort()
m = b"".join(r[0] + b"\0" + r[1].encode() + b"\0" + r[2].encode() + b"\n" for r in rows)
print(hashlib.sha256(m).hexdigest())
PY
}

install_sprint() {
  local root="$1" tag="$2"
  [[ -n "$root" ]] || { echo "usage: --install-sprint <ACTL_ROOT>" >&2; exit 2; }
  local sd="$root/actl-repo/specs/$tag" runs="$root/actl-repo/specs/$tag/runs"
  mkdir -p "$sd" "$runs/logs" "$runs/turns" "$root/repos"
  local base_sha
  if [[ ! -d "$root/repos/target-repo/.git" ]]; then base_sha="$(build_repo "$root/repos/target-repo")"
  else base_sha="$(ggit -C "$root/repos/target-repo" rev-parse HEAD)"; fi
  cp "$HERE/sprint/spec-001.md" "$sd/spec-001.md"
  cp "$HERE/sprint/solution_key.patch" "$sd/solution_key-002.patch"
  rm -rf "$sd/oracle-003"; cp -R "$HERE/sprint/oracle" "$sd/oracle-003"
  cp "$HERE/sprint/solution_key.patch" "$sd/oracle-003/solution_key.patch"
  find "$sd/oracle-003" -type f -name '*.sh' -exec chmod 755 {} +
  find "$sd/oracle-003" -type f ! -name '*.sh' -exec chmod 644 {} +
  local msha; msha="$(manifest_sha "$sd/oracle-003")"
  sed -e "s/{{sprint_tag}}/$tag/" -e "s/{{base_sha}}/$base_sha/" -e 's/{{status}}/frozen/' \
      -e 's/{{spec_source}}/imported/' -e 's/{{live_run_line}}/live_run = "none"\n/' \
      "$HERE/expected_text/sprint.toml.tmpl" > "$sd/sprint.toml"
  local spec_sha sprint_sha scope_sha
  spec_sha="$(sha "$sd/spec-001.md")"; sprint_sha="$(sha "$sd/sprint.toml")"; scope_sha="$(sha "$sd/oracle-003/scope.txt")"
  cat > "$sd/qual-004.json" <<EOF
{"base_sha":"$base_sha","diagnostic_case":"pure_oracle_failure","id":"qual-004","kind":"qual","manifest_sha256":"$msha","mutants":[{"apply_error":false,"killed":true,"name":"contact_leak.patch"},{"apply_error":false,"killed":true,"name":"private_200.patch"},{"apply_error":false,"killed":true,"name":"photo_count_off.patch"},{"apply_error":false,"killed":false,"name":"avatar_drop.patch"}],"null_base":"red","oracle":"oracle-003","parent":null,"seq":4,"solution_key_guards":"green","solution_key_green":"3/3","solution_key_repo_test":"green","spec":"spec-001"}
EOF
  local qual_sha; qual_sha="$(sha "$sd/qual-004.json")"
  cat > "$sd/contract-005.json" <<EOF
{"base_sha":"$base_sha","epoch":1,"id":"contract-005","kind":"contract","oracle":{"id":"oracle-003","manifest_sha256":"$msha","seq":3},"parent":null,"qual":{"id":"qual-004","seq":4,"sha256":"$qual_sha"},"scope":{"path":"oracle-003/scope.txt","sha256":"$scope_sha"},"seq":5,"spec":{"id":"spec-001","seq":1,"sha256":"$spec_sha"},"sprint_sha256":"$sprint_sha"}
EOF
  local rid; rid="run-$(printf '%s' "$tag" | sha256sum | cut -c1-12)"
  cat > "$runs/state.json" <<EOF
{"active_contract":"contract-005.json","active_oracle":"oracle-003","active_oracle_draft":null,"active_solution_key":"solution_key-002.patch","active_spec":"spec-001.md","active_stage":"implementer","attempts":{"curator":0,"implementer":0,"live":0,"oracle":1},"closures_submitted":0,"epoch":1,"grants":{"curator":0,"implementer":0,"live":0,"oracle":0},"hard_caps_tripped":0,"run_id":"$rid","seq":5,"sprint_tag":"$tag","status":"running","tmux_sessions":[]}
EOF
  printf 'seq\tsession\trole\tengine\tmodel\tmodel_family\tturns\ttool_calls\ttokens\tcost_usd\texit_code\taccepted_items\tescalation_alerts_sent\n' > "$runs/sessions.tsv"
  echo "$base_sha"
}

case "${1:-}" in
  --install-sprint)
    root="${2:-}"; tag="$DEFAULT_TAG"
    if [[ "${3:-}" == "--tag" ]]; then tag="${4:?--tag needs a value}"; fi
    install_sprint "$root" "$tag" ;;
  ""|-h|--help) echo "usage: build_golden.sh <dest> | --install-sprint <ACTL_ROOT> [--tag <TAG>]" >&2; exit 2 ;;
  *) build_repo "$1" ;;
esac
