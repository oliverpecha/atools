"""actl init subcommand."""
from __future__ import annotations

import argparse
import json
import subprocess

from actl.errors import UsageError
from actl.layout import PROFILES_README, Layout
from actl.sprint import init_target


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("init", help="Initialize target repository clone")
    p.add_argument("--target", required=True)
    p.add_argument("--name", default=None, help="Target repository name under repos/")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=handler)


def handler(args: argparse.Namespace, layout: Layout) -> int:
    if args.name is not None:
        layout = Layout(layout.root, repo=args.name)
    existed = (layout.target_repo / ".git").exists()
    try:
        target_repo = init_target(layout, args.target)
    except (ValueError, RuntimeError) as e:
        raise UsageError(str(e)) from e
    created = not existed
    readme = layout.root / "profiles" / "README.md"
    if not readme.is_file():
        layout.ensure_base_tree()
        readme.write_text(PROFILES_README, encoding="utf-8")
    r = subprocess.run(
        ["git", "-C", str(target_repo), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    base_sha = r.stdout.strip() if r.returncode == 0 else ""
    doc = {
        "actl_root": str(layout.root),
        "target_repo": str(target_repo),
        "base_sha": base_sha,
        "created": created,
    }
    if args.json:
        print(json.dumps(doc))
    else:
        print(f"initialized target_repo={target_repo} base_sha={base_sha} created={created}")
    return 0
