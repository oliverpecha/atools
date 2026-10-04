import os
import glob
import shutil
from pathlib import Path
from typing import List, Tuple, Optional
from core.config import TRANSCRIPTS_GLOB

def get_unique_session_files() -> List[str]:
    all_files = sorted(glob.glob(TRANSCRIPTS_GLOB), key=os.path.getmtime, reverse=True)
    seen = {}
    for f in all_files:
        uid = Path(f).parent.name
        if uid not in seen or Path(f).name == "transcript.jsonl":
            seen[uid] = f
    return list(seen.values())

def resolve_session_path(target: str) -> Tuple[Optional[str], Optional[str]]:
    files = get_unique_session_files()
    if not files:
        return None, None

    clean = target.strip()
    if clean.isdigit():
        idx = int(clean)
        if 1 <= idx <= len(files):
            fpath = files[idx - 1]
            return fpath, Path(fpath).parent.name

    if clean.lower() in ("latest", "last"):
        fpath = files[0]
        return fpath, Path(fpath).parent.name

    target_lower = clean.lower()
    matches = [f for f in files if target_lower in Path(f).parent.name.lower()]
    if matches:
        return matches[0], Path(matches[0]).parent.name

    return None, None

def delete_sessions(targets: List[str], dry_run: bool = False, force: bool = False) -> int:
    """
    Deletes sessions matched by UUID prefix or row index.
    Removes transcript dirs, chat dirs, and store.db instances.
    """
    files = get_unique_session_files()
    resolved_ids = set()

    for t in targets:
        clean = t.strip()
        if clean.isdigit():
            idx = int(clean)
            if 1 <= idx <= len(files):
                resolved_ids.add(Path(files[idx - 1]).parent.name)
                continue
        matches = [Path(f).parent.name for f in files if clean.lower() in Path(f).parent.name.lower()]
        if matches:
            resolved_ids.add(matches[0])
        else:
            resolved_ids.add(clean)

    all_target_dirs = []
    total_bytes = 0

    for uid in sorted(resolved_ids):
        short = uid[:8]
        t_dirs = glob.glob(f"/root/.cursor/projects/*/agent-transcripts/*{short}*")
        c_dirs = glob.glob(f"/root/.cursor/chats/*/*{short}*")
        found = sorted(set(t_dirs + c_dirs))
        for d in found:
            size = sum(f.stat().st_size for f in Path(d).rglob('*') if f.is_file())
            total_bytes += size
            all_target_dirs.append((short, d, size))

    if not all_target_dirs:
        print("⚠️ No matching session directories found for the specified IDs.")
        return 0

    print(f"\nFound {len(all_target_dirs)} directories across {len(resolved_ids)} session target(s):")
    for short, d, size in all_target_dirs:
        print(f"  [{short}] {d} ({size / 1024:.1f} KB)")
    print(f"\nTotal reclaimable space: {total_bytes / (1024 * 1024):.2f} MB")

    if dry_run:
        print("\n[DRY RUN] No directories were deleted.")
        return 0

    if not force:
        try:
            confirm = input(f"\nPermanently delete {len(all_target_dirs)} session directories? [y/N]: ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted.")
            return 0
        if confirm not in ('y', 'yes'):
            print("Aborted.")
            return 0

    deleted = 0
    for short, d, _ in all_target_dirs:
        try:
            if os.path.isdir(d):
                shutil.rmtree(d, ignore_errors=True)
                print(f"🗑️  Deleted: {d}")
                deleted += 1
        except Exception as e:
            print(f"⚠️ Error deleting {d}: {e}")

    print(f"\n✅ Cleaned {deleted} directories ({total_bytes / (1024 * 1024):.2f} MB freed).")
    return deleted
