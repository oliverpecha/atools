"""actl CLI entrypoint."""
from __future__ import annotations

import argparse
import importlib
import json
import sys
from pathlib import Path

from actl.errors import EnvError, StateIntegrityError, UsageError
from actl.layout import Layout


def discover_commands(subparsers: argparse._SubParsersAction) -> list[str]:
    pkg_dir = Path(__file__).resolve().parent
    stems: list[str] = []
    for name in list(sys.modules):
        if name.startswith("actl.cmd_"):
            mod = sys.modules[name]
            f = getattr(mod, "__file__", None)
            if f and not Path(f).is_file():
                del sys.modules[name]
    for p in sorted(pkg_dir.glob("cmd_*.py"), key=lambda x: x.stem):
        mod_name = f"actl.{p.stem}"
        if mod_name in sys.modules:
            mod = importlib.reload(sys.modules[mod_name])
        else:
            mod = importlib.import_module(mod_name)
        if not hasattr(mod, "register") or not callable(mod.register):
            raise AttributeError(f"{mod.__name__} lacks register(subparsers)")
        mod.register(subparsers)
        stems.append(p.stem)
    return stems


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    want_json = "--json" in argv
    parser = argparse.ArgumentParser(prog="actl")
    subparsers = parser.add_subparsers(dest="command", required=True)
    discover_commands(subparsers)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            return 0
        if want_json:
            print(json.dumps({"ok": False, "exit_code": 2, "error": "usage error"}))
        return 2

    layout = Layout()
    try:
        rc = args.func(args, layout)
        return 0 if rc is None else int(rc)
    except UsageError as e:
        code, msg = 2, str(e)
    except StateIntegrityError as e:
        code, msg = 3, str(e)
    except EnvError as e:
        code, msg = 4, str(e)
    except SystemExit as e:
        c = e.code
        if c in (0, 1, 2, 3, 4):
            return 0 if c is None else int(c)
        code, msg = 2, str(e)
    except Exception as e:
        code, msg = 3, f"{type(e).__name__}: {e}"

    use_json = want_json or bool(getattr(args, "json", False))
    if use_json:
        print(json.dumps({"ok": False, "exit_code": code, "error": msg}))
    else:
        print(f"ERROR: {msg}", file=sys.stderr)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
