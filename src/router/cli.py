import sys
import os
from router.config import load_tier_config, TIER_MAP
from router.menu import display_interactive_menu
from router.process import (
    print_sessions,
    attach_session,
    tail_logs,
    kill_session,
)

def print_help() -> None:
    help_text = """
CURSOR AGENT ROUTER (arouter) - Help & Reference
======================================================================
The agent router manages dynamic model tiers for Cursor CLI on your VPS,
routing prompts to appropriate models without requiring manual flags.

AVAILABLE TIERS:
  acheap    : Fast, high-efficiency model for quick queries & inspection.
              Invoked via: acheap "your prompt"
  abalanced : Standard workhorse for daily coding, testing, and debugging.
              Invoked via: abalanced "your prompt"
  asmart    : Frontier reasoning for multi-file refactoring and architecture.
              Invoked via: asmart "your prompt"

PROCESS MANAGEMENT & PERSISTENCE:
  arouter ps | list       List running background agent sessions
  arouter attach <sess>   Attach interactively to running session (PTY)
  arouter logs <sess> [-f] View or follow session log output
  arouter kill <sess>     Terminate an active session and clean process tree

EXECUTION OPTIONS:
  -d, --detach            Launch run inside headless tmux session
  -n, --name <tag>        Custom session name (default: arun-<tier>-<ts>)
  -t, --timeout <dur>     Watchdog timeout limit (e.g. 5s, 15m, 1h)

COMMAND USAGE:
  arouter                 Launch interactive TUI to reassign model tiers
  arouter --show          Display all active tier assignments
  arouter --show <tier>   Display single tier (e.g. 'arouter --show cheap')
  arouter --help          Display this help overview

SHELL WRAPPERS & STDIN PIPING:
  All tier commands accept direct arguments or piped content via stdin:
    cat file.py | acheap "Explain this module"
    cat requirements.txt | abalanced "What dependencies are missing?"
    git diff | asmart "Review staged changes for regressions"
======================================================================
"""
    print(help_text.strip())

def print_active_tiers(tier_filter: str = None, raw: bool = False) -> None:
    cfg = load_tier_config()
    if tier_filter:
        norm = TIER_MAP.get(tier_filter.lower())
        if not norm:
            print(f"⚠️ Invalid tier '{tier_filter}'. Available: cheap, balanced, smart")
            sys.exit(1)
        model = cfg.get(norm, 'auto')
        if raw:
            print(model)
            return
        print(f"  [a{norm:<8}] -> {model:<28}")
        return

    print()
    print("======================================================================")
    print("  CURRENT ACTIVE CURSOR TIERS")
    print("======================================================================")
    for t in ('cheap', 'balanced', 'smart'):
        model = cfg.get(t, 'auto')
        print(f"  [a{t:<8}] -> {model:<28}")
    print("======================================================================")
    print()

def main() -> None:
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ('--help', '-h', 'help'):
            print_help()
            sys.exit(0)
        elif arg in ('ps', 'list'):
            sys.exit(print_sessions())
        elif arg == 'attach':
            session = sys.argv[2] if len(sys.argv) > 2 else ""
            if not session:
                print("Usage: arouter attach <session>", file=sys.stderr)
                sys.exit(1)
            sys.exit(attach_session(session))
        elif arg == 'logs':
            if len(sys.argv) < 3:
                print("Usage: arouter logs <session> [-f]", file=sys.stderr)
                sys.exit(1)
            session = sys.argv[2]
            follow = '-f' in sys.argv[3:] or '--follow' in sys.argv[3:]
            sys.exit(tail_logs(session, follow=follow))
        elif arg == 'kill':
            session = sys.argv[2] if len(sys.argv) > 2 else ""
            if not session:
                print("Usage: arouter kill <session>", file=sys.stderr)
                sys.exit(1)
            sys.exit(kill_session(session))
        elif arg in ('--show', '-s', 'show'):
            tier_target = None
            is_raw = '--raw' in sys.argv
            for token in sys.argv[2:]:
                if token != '--raw':
                    tier_target = token
                    break
            print_active_tiers(tier_target, raw=is_raw)
            sys.exit(0)
        elif arg == '--get' and len(sys.argv) > 2:
            print_active_tiers(sys.argv[2].lower(), raw=True)
            sys.exit(0)

    display_interactive_menu()

if __name__ == "__main__":
    main()
