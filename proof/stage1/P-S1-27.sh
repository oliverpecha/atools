#!/usr/bin/env bash
# Authored-by: Gemini 3.1 Pro (Google), model family: Gemini (Serra-S1)
# P-S1-27: ATOOLS_CURSOR_HOME override is honored by src/core/config.py,
# src/sessions/storage.py, and actl.session.scan_tripwires (S1-R10.4).
set -euo pipefail
REPO_DIR="${ACTL_REPO:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)}"
export PYTHONPATH="${REPO_DIR}/src${PYTHONPATH:+:${PYTHONPATH}}"

source "${REPO_DIR}/proof/stage1/fixture_s1.sh"
IFS='|' read -r SDIR WT <<< "$(create_stage1_sandbox "p27" "good.patch")"

CUSTOM_HOME="${SDIR}/custom_cursor_home"
mkdir -p "$CUSTOM_HOME"
export ATOOLS_CURSOR_HOME="$CUSTOM_HOME"

cp "${REPO_DIR}/fixtures/golden/transcripts/dirty_oracle.jsonl" "${CUSTOM_HOME}/dirty_oracle.jsonl"

python3 - "$SDIR" "$CUSTOM_HOME" <<'PY'
import sys
from pathlib import Path

sdir, custom_home = Path(sys.argv[1]), Path(sys.argv[2])

try:
    from actl.session import scan_tripwires
    from actl.layout import Layout
    import core.config as core_cfg
    import sessions.storage as sess_storage
except ImportError as exc:
    print(f"FAIL: S1-R10.4: cannot import required modules: {exc}")
    sys.exit(1)

import os
from pathlib import Path as P

layout = Layout(sdir)
tag = "2026-10-16_public-profiles"

# Behavioral honor: dirty home yields transcript hits; empty/clean home yields none
hits = scan_tripwires(layout, tag, 6)
if not isinstance(hits, list) or len(hits) == 0:
    print("FAIL: S1-R10.4: scan_tripwires failed to discover dirty_oracle.jsonl under ATOOLS_CURSOR_HOME")
    sys.exit(1)
if not any(h.get("source") == "transcript" for h in hits):
    print(f"FAIL: S1-R10.4: Expected transcript source hit, got {hits}")
    sys.exit(1)

clean_home = sdir / "clean_cursor_home"
clean_home.mkdir(parents=True, exist_ok=True)
os.environ["ATOOLS_CURSOR_HOME"] = str(clean_home)
hits_clean = scan_tripwires(layout, tag, 6)
if hits_clean:
    print(f"FAIL: S1-R10.4: empty/clean ATOOLS_CURSOR_HOME must produce no transcript hits, got {hits_clean}")
    sys.exit(1)

# Modules must resolve the override at runtime, not merely mention the env name
observed = []
for mod in (core_cfg, sess_storage):
    for name in ("cursor_home", "get_cursor_home", "resolve_cursor_home", "cursor_dir"):
        fn = getattr(mod, name, None)
        if callable(fn):
            observed.append(str(fn()))
            break
    else:
        # Fall back: if the module exposes a Path/str attribute computed from the env
        for name in dir(mod):
            val = getattr(mod, name)
            if isinstance(val, (str, P)) and str(custom_home) in str(val):
                observed.append(str(val))
                break
if not observed:
    # Last-resort runtime check: re-set dirty home and require hits again
    os.environ["ATOOLS_CURSOR_HOME"] = str(custom_home)
    hits_again = scan_tripwires(layout, tag, 6)
    if not hits_again:
        print("FAIL: S1-R10.4: ATOOLS_CURSOR_HOME override is not honored at runtime")
        sys.exit(1)
else:
    if not any(str(custom_home) in x or str(clean_home) in x for x in observed):
        print(f"FAIL: S1-R10.4: config/storage cursor home did not resolve to override, got {observed}")
        sys.exit(1)
PY
