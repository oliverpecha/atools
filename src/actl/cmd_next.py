"""actl next subcommand."""
from __future__ import annotations

import argparse
import json

from actl.errors import UsageError
from actl.layout import Layout
from actl.next import decide_next


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("next", help="Decide next sprint action")
    p.add_argument("--sprint", required=True)
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=handler)


def handler(args: argparse.Namespace, layout: Layout) -> int:
    try:
        result = decide_next(layout, args.sprint)
    except (ValueError, FileNotFoundError) as e:
        raise UsageError(str(e)) from e
    if args.json:
        print(json.dumps(result))
    else:
        print(f"{result['action']}: {result['reason']}")
        if result.get("command"):
            print(result["command"])
    return 0
