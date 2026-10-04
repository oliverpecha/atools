import sys
import os
import json
from pathlib import Path
from core.terminal import C
from sessions.storage import get_unique_session_files, resolve_session_path, delete_sessions
from sessions.reader import get_session_meta, enrich_meta_from_transcript, format_table_utc, clean_text
from sessions.renderers import render_markdown

def list_sessions() -> None:
    files = get_unique_session_files()
    if not files:
        print("No Cursor Agent sessions found.")
        return
    print("\n" + "=" * 116)
    print(f" {'#':<4} {'SESSION ID':<10} {'DATE / TIME (UTC)':<24} {'MODEL DISPATCHED':<22} {'DURATION':<10} {'QUERY / INTENT'}")
    print("=" * 116)
    for idx, p in enumerate(files, 1):
        uid = Path(p).parent.name[:8]
        meta = get_session_meta(uid)
        meta = enrich_meta_from_transcript(meta, p)
        dt_str = format_table_utc(meta["created_ms"]) if meta["created_ms"] else "N/A"
        query = "N/A"
        try:
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("role") in ("user", "human"):
                        cleaned = clean_text(entry.get("message", entry.get("content", {})))
                        if cleaned:
                            query = (cleaned[:38] + "..") if len(cleaned) > 38 else cleaned
                            break
        except Exception:
            pass
        print(f" {idx:<4} [{uid}]   {dt_str:<24} {meta['model']:<22} {meta['duration']:<10} {query}")
    print("=" * 116)
    print("💡 Run 'asessions <uuid>' to view full execution transcript.")
    print("💡 Run 'asessions rm <uuid...>' to delete test sessions.\n")

def main() -> None:
    args = sys.argv[1:]
    if not args:
        list_sessions()
        sys.exit(0)

    cmd = args[0].lower()
    if cmd in ("rm", "del", "delete"):
        targets = []
        force = False
        dry_run = False
        for a in args[1:]:
            if a in ("-f", "--force"):
                force = True
            elif a in ("-n", "--dry-run"):
                dry_run = True
            else:
                targets.append(a)
        if not targets:
            print("Usage: asessions rm [-f] [-n] <session_id|#_index> [session_id...]")
            sys.exit(1)
        delete_sessions(targets, dry_run=dry_run, force=force)
        sys.exit(0)

    # Transcript / summary lookup fallback
    fpath, full_id = resolve_session_path(args[0])
    if not fpath:
        print(f"Error: Session '{args[0]}' not found.")
        sys.exit(1)
    meta = get_session_meta(full_id)
    meta = enrich_meta_from_transcript(meta, fpath)
    print(f"\nSession {full_id} ({meta['model']}) · Duration: {meta['duration']}")

if __name__ == "__main__":
    main()
