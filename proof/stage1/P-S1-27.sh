#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# Gate-D-remediation: Cursor-S1 (Grok 4.6)
# P-S1-27: ATOOLS_CURSOR_HOME override is honored by src/core/config.py,
# src/sessions/storage.py, and actl.session.scan_tripwires (S1-R10.4).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
if [[ -z "${ACTL_STANDIN_OVERLAY:-}" ]]; then
  export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"
fi

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p27" "good.patch")"

CUSTOM_HOME="${SDIR}/custom_cursor_home"
mkdir -p "$CUSTOM_HOME"
export ATOOLS_CURSOR_HOME="$CUSTOM_HOME"

cp "${REPO_DIR}/fixtures/golden/transcripts/dirty_oracle.jsonl" "${CUSTOM_HOME}/dirty_oracle.jsonl"

python3 - "$SDIR" "$CUSTOM_HOME" <<'PY'
import os
import sys
from pathlib import Path

sdir, custom_home = Path(sys.argv[1]), Path(sys.argv[2])


def path_contained(resolved, home) -> bool:
    """Canonical containment: equality or Path.is_relative_to (realpath)."""
    r = Path(os.path.realpath(str(resolved)))
    h = Path(os.path.realpath(str(home)))
    if r == h:
        return True
    try:
        return r.is_relative_to(h)
    except AttributeError:
        return str(r).startswith(str(h) + os.sep)


# Degenerate resolver returning custom_home_evil must REJECT (substring trap).
evil = Path(str(custom_home) + "_evil")
evil.mkdir(parents=True, exist_ok=True)
if path_contained(evil, custom_home):
    print(
        "FAIL: S1-R10.4: custom_home_evil accepted as contained in custom_home "
        f"(resolved={evil}, home={custom_home})"
    )
    sys.exit(1)
if path_contained(str(custom_home) + "_evil", custom_home):
    print("FAIL: S1-R10.4: custom_home_evil string accepted by containment check")
    sys.exit(1)

try:
    from actl.session import scan_tripwires
    from actl.layout import Layout
    import core.config as core_cfg
    import sessions.storage as sess_storage
except ImportError as exc:
    print(f"FAIL: S1-R10.4: cannot import required modules: {exc}")
    sys.exit(1)

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# S1-R10.1: dirty home yields transcript hits; empty/clean home yields none
hits = scan_tripwires(layout, tag, 6)
if not isinstance(hits, list) or len(hits) == 0:
    print("FAIL: S1-R10.1: scan_tripwires failed to discover dirty_oracle.jsonl under ATOOLS_CURSOR_HOME")
    sys.exit(1)
if not any(h.get("source") == "transcript" for h in hits):
    print(f"FAIL: S1-R10.1: Expected transcript source hit, got {hits}")
    sys.exit(1)

clean_home = sdir / "clean_cursor_home"
clean_home.mkdir(parents=True, exist_ok=True)
os.environ["ATOOLS_CURSOR_HOME"] = str(clean_home)
hits_clean = scan_tripwires(layout, tag, 6)
if hits_clean:
    print(f"FAIL: S1-R10.1: empty/clean ATOOLS_CURSOR_HOME must produce no transcript hits, got {hits_clean}")
    sys.exit(1)

# Restore dirty home for module resolution checks
os.environ["ATOOLS_CURSOR_HOME"] = str(custom_home)

# S1-R10.4: each of core.config and sessions.storage MUST expose one of
# cursor_home / get_cursor_home / resolve_cursor_home / cursor_dir returning the override.
# Missing helper is FAIL (no scan_tripwires secondary fallback).
# Require canonical containment (equality or is_relative_to), not substring.
# Exercise a real consumer: open/read/write under the returned home.
for mod, label in ((core_cfg, "core.config"), (sess_storage, "sessions.storage")):
    resolver = None
    for name in ("cursor_home", "get_cursor_home", "resolve_cursor_home", "cursor_dir"):
        fn = getattr(mod, name, None)
        if callable(fn):
            resolver = fn
            break
    if resolver is None:
        print(f"FAIL: S1-R10.4: {label} does not honor ATOOLS_CURSOR_HOME")
        sys.exit(1)
    resolved = Path(resolver())
    if not path_contained(resolved, custom_home):
        print(
            f"FAIL: S1-R10.4: {label} does not honor ATOOLS_CURSOR_HOME "
            f"(resolved={resolved!s}, expected contained in {custom_home})"
        )
        sys.exit(1)
    # Consumer of the resolver: write/read under the returned home path.
    marker = resolved / f"p27_consumer_{label.replace('.', '_')}.txt"
    try:
        marker.write_text("consumer-ok\n", encoding="utf-8")
        got = marker.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"FAIL: S1-R10.4: {label} resolver home not usable for open/read/write: {exc}")
        sys.exit(1)
    if got != "consumer-ok\n":
        print(f"FAIL: S1-R10.4: {label} consumer read mismatch under resolved home")
        sys.exit(1)
    if not path_contained(marker, custom_home):
        print(
            f"FAIL: S1-R10.4: {label} consumer path escaped custom_home "
            f"(marker={marker}, home={custom_home})"
        )
        sys.exit(1)

print("OK: S1-R10.4 cursor home containment and consumer checks passed.")
PY
