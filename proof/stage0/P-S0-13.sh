#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# P-S0-13 (S0-R9, D-12): with the repo's real pre-commit hook installed as the GLOBAL hook, building the golden repo in a mktemp dir succeeds
# and gives the pinned base_sha. A counter-check proves the hook is really active (otherwise the proof would be vacuous).
set -uo pipefail
REPO="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
command -v git >/dev/null 2>&1 || { echo "FAIL: git not installed (environment error)"; exit 4; }
[[ -f "$REPO/hooks/pre-commit" ]] || { echo "FAIL: $REPO/hooks/pre-commit not found (environment error)"; exit 4; }
[[ -f "$REPO/fixtures/golden/build_golden.sh" ]] || { echo "FAIL: fixtures/golden/build_golden.sh missing"; exit 1; }
T="$(mktemp -d)"; trap 'rm -rf "$T"' EXIT
H="$T/home"; mkdir -p "$H/.config/git/hooks"
cp "$REPO/hooks/pre-commit" "$H/.config/git/hooks/pre-commit"; chmod +x "$H/.config/git/hooks/pre-commit"
printf '[core]\n\thooksPath = %s\n' "$H/.config/git/hooks" > "$H/.gitconfig"
GENV=(env HOME="$H" GIT_CONFIG_GLOBAL="$H/.gitconfig" GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t)
"${GENV[@]}" git init -q -b main "$T/ctl" && "${GENV[@]}" git -C "$T/ctl" commit -q --allow-empty -m "counter-check" >/dev/null 2>&1
if [[ $? -eq 0 ]]; then echo "FAIL: the installed global hook did not block a commit on main; test setup is vacuous (environment error)"; exit 4; fi
sha="$("${GENV[@]}" bash "$REPO/fixtures/golden/build_golden.sh" "$T/golden" 2>"$T/err")" || { echo "FAIL: build_golden.sh failed under the global hook: $(tail -c 300 "$T/err")"; exit 1; }
want="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["base_sha"])' "$REPO/fixtures/golden/expected.d/base.json")"
[[ "$sha" == "$want" ]] || { echo "FAIL: base_sha $sha != expected $want under the global hook"; exit 1; }
echo "OK: golden build is immune to the global hook"
