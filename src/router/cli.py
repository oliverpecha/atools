import sys
from router.config import load_tier_config, TIER_MAP
from router.menu import display_interactive_menu

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
