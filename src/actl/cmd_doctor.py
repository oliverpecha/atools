"""actl doctor subcommand."""
from __future__ import annotations

import argparse
import json

from actl.doctor import run_doctor
from actl.layout import Layout


def register(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("doctor", help="Report environment baseline")
    p.add_argument("--refresh", action="store_true")
    p.add_argument("--json", action="store_true")
    p.set_defaults(func=handler)


def handler(args: argparse.Namespace, layout: Layout) -> int:
    report = run_doctor(layout, refresh=bool(args.refresh))
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"actl doctor {report.get('version')} @ {report.get('head_sha', '')[:12]}")
        print(f"actl_root={report.get('actl_root')}")
        tv = report.get("tool_versions") or {}
        print(f"tmux={tv.get('tmux')}")
        audit = report.get("audit") or {}
        print(f"audit.present={audit.get('present')}")
        for w in report.get("warnings") or []:
            print(f"warning: {w}")
    if report.get("tool_versions", {}).get("tmux") is None or not report.get("audit", {}).get(
        "present"
    ):
        return 4
    return 0
