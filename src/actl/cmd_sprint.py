"""actl sprint subcommand."""
from __future__ import annotations

import argparse
import json

from actl.errors import StateIntegrityError, UsageError
from actl.layout import Layout
from actl.sprint import create_sprint


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("sprint", help="Sprint management")
    sp = p.add_subparsers(dest="sprint_cmd", required=True)
    new_p = sp.add_parser("new", help="Create a new sprint")
    new_p.add_argument("slug")
    new_p.add_argument("--spec")
    new_p.add_argument("--json", action="store_true")
    new_p.set_defaults(func=handler_new)


def handler_new(args: argparse.Namespace, layout: Layout) -> int:
    try:
        result = create_sprint(layout, args.slug, spec_path=args.spec)
    except (ValueError, FileNotFoundError) as e:
        raise UsageError(str(e)) from e
    except OSError as e:
        raise StateIntegrityError(str(e)) from e
    if args.json:
        print(json.dumps(result))
    else:
        print(f"created sprint {result['sprint_tag']}")
    return 0
