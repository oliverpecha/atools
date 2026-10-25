#!/usr/bin/env python3
import argparse, re, stat, sys
from pathlib import Path

# Matches standard lines, table cells (| === ... === |), blockquotes (> === ... ===), and indents
START = re.compile(
    r"^(?:\|\s*|>\s*|\s*)?=== FILE:\s*(.+?)\s*===(?:\s*\|.*)?\s*$",
    re.IGNORECASE
)
END = re.compile(
    r"^(?:\|\s*|>\s*|\s*)?=== END FILE(?::\s*.*?)?\s*===(?:\s*\|.*)?\s*$",
    re.IGNORECASE
)
CONT = re.compile(
    r"^(?:\|\s*|>\s*|\s*)?=== CONTINUE \(part \d+ of \d+\) ===(?:\s*\|.*)?\s*$",
    re.IGNORECASE
)
DEFAULT_ALLOW = ["src/actl/", "proof/", "test/", "fixtures/", "docs/", "schemas/", "config/", "skills/", "prompts/"]

def unwrap(lines):
    idx = [i for i, l in enumerate(lines) if l.lstrip().startswith("```")]
    nonempty = [i for i, l in enumerate(lines) if l.strip()]
    if len(idx) >= 2 and idx[0] == nonempty[0] and idx[-1] == nonempty[-1]:
        depth = 0
        for i in idx[:-1]:
            depth += 1 if depth == 0 else -1
            if depth == 0:
                return lines
        return lines[idx[0] + 1 : idx[-1]]
    return lines

def valid_path(p, allow):
    # Strip any residual markdown cell escapes or whitespace
    p = p.strip().strip("|").strip()
    if not p or p.startswith("/") or "\\" in p or "\0" in p or p.endswith("/"):
        return "absolute, empty, backslash or directory path"
    if ".." in p.split("/"):
        return "path traversal"
    if allow and not any(p.startswith(a) for a in allow):
        return f"outside allowed prefixes {allow}"
    return None

def parse(text):
    blocks, errors, cur, path = [], [], None, None
    for n, raw_line in enumerate(text.split("\n"), 1):
        line = raw_line.strip()
        if cur is None:
            m = START.match(line)
            if m:
                path = m.group(1).strip().strip("|").strip()
                cur = []
            continue
        if END.match(line):
            blocks.append((path, unwrap(cur)))
            cur = None
        elif START.match(line):
            errors.append(f"line {n}: new FILE block before END FILE of {path}")
            path = START.match(line).group(1).strip().strip("|").strip()
            cur = []
        elif not CONT.match(line):
            cur.append(raw_line)
    if cur is not None:
        errors.append(f"unterminated block: {path} (response truncated?)")
    return blocks, errors

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--root", default=".")
    ap.add_argument("--allow", nargs="*", default=DEFAULT_ALLOW)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("-n", "--dry-run", action="store_true")
    a = ap.parse_args()

    text = "\n".join(Path(f).read_text(encoding="utf-8") for f in a.files)
    blocks, errors = parse(text)
    seen, root = set(), Path(a.root)

    if not blocks:
        errors.append("no '=== FILE: ... ===' blocks found")

    for path, _ in blocks:
        bad = valid_path(path, a.allow)
        if bad:
            errors.append(f"{path}: {bad}")
        if path in seen:
            errors.append(f"{path}: duplicate block")
        seen.add(path)
        if (root / path).exists() and not a.force:
            errors.append(f"{path}: exists (use --force)")

    if errors:
        print("REFUSED, nothing written:")
        for e in errors:
            print("  -", e)
        sys.exit(2)

    for path, lines in blocks:
        body = "\n".join(lines).rstrip("\n") + "\n"
        target = root / path
        print(("would write " if a.dry_run else "write       ") + f"{path}  ({len(body.splitlines())} lines)")
        if a.dry_run:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        if path.endswith(".sh"):
            target.chmod(target.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print(f"{len(blocks)} file(s) {'checked' if a.dry_run else 'written'} under {root.resolve()}")

if __name__ == "__main__":
    main()