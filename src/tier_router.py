#!/usr/bin/env python3
"""
Cursor Agent Tier Router & Interactive Selector
- Discovers live models from 'agent models' / 'agent --list-models'
- Groups models cleanly by vendor
- Hardcodes 'auto' as default across all tiers
- Renders available models first, followed by active tiers at the bottom
- Provides headless lookup for shell integration via --get <tier>
- Supports --show for active tier inspection and --help for full documentation
"""

import os
import sys
import json
import subprocess
from pathlib import Path
from typing import List, Dict

CONFIG_PATH = Path(os.environ.get('ATOOLS_CONFIG', os.path.expanduser('~/.cursor/arouter-config.json')))

DEFAULT_TIERS = {
    'cheap': 'auto',
    'balanced': 'auto',
    'smart': 'auto',
}

VENDOR_ORDER = [
    ('ANTHROPIC', ['claude', 'sonnet', 'opus', 'haiku', 'fable']),
    ('OPENAI', ['gpt', 'o1', 'o3', 'o4']),
    ('GOOGLE', ['gemini', 'flash']),
    ('CURSOR & XAI', ['grok', 'composer', 'astra', 'auto']),
    ('OTHER', []),
]


def load_tier_config() -> Dict[str, str]:
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            for k, v in DEFAULT_TIERS.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception:
            return DEFAULT_TIERS.copy()
    return DEFAULT_TIERS.copy()


def save_tier_config(config: Dict[str, str]) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(config, indent=2) + '\n')


def fetch_available_models() -> List[str]:
    raw_output = ''
    for cmd in (['agent', 'models'], ['agent', '--list-models']):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0 and res.stdout.strip():
                raw_output = res.stdout
                break
        except Exception:
            continue

    discovered = []
    for line in raw_output.splitlines():
        line = line.strip()
        if not line or line.startswith('#') or 'available' in line.lower() or 'filter' in line.lower():
            continue
        parts = line.split()
        candidate = parts[0].lstrip('-*• ')
        if not candidate:
            continue
        discovered.append(candidate)

    discovered = list(dict.fromkeys(discovered))
    if not discovered:
        discovered = [
            'auto',
            'claude-opus-5-thinking-high',
            'claude-fable-5-thinking-high',
            'claude-sonnet-5-thinking-high',
            'claude-3.7-sonnet',
            'claude-3.5-sonnet',
            'gpt-4o',
            'o3-mini',
            'gemini-2.5-flash',
            'gemini-2.5-pro',
            'grok-4.7',
            'composer-2.5',
        ]
    return discovered


def categorize_model(name: str) -> str:
    low = name.lower()
    for vendor, keys in VENDOR_ORDER[:-1]:
        if any(k in low for k in keys):
            return vendor
    return 'OTHER'


TIER_HINTS = {
    'cheap': 'acheap',
    'balanced': 'abalanced',
    'smart': 'asmart',
}

TIER_MAP = {
    'c': 'cheap',
    'ac': 'cheap',
    'cheap': 'cheap',
    'acheap': 'cheap',
    'b': 'balanced',
    'ab': 'balanced',
    'balanced': 'balanced',
    'abalanced': 'balanced',
    's': 'smart',
    'as': 'smart',
    'smart': 'smart',
    'asmart': 'smart',
}


def print_help() -> None:
    help_text = """
CURSOR AGENT ROUTER (arouter) - Help & Reference
======================================================================
The agent router manages dynamic model tiers for Cursor CLI on your VPS,
routing prompts to appropriate models without requiring manual flags.

AVAILABLE TIERS:
  cheap 
    : Fast, high-efficiency model for quick queries & inspection.
                Invoked via: acheap "your prompt"
  balanced
  : Standard workhorse for daily coding, testing, and debugging.
                Invoked via: abalanced "your prompt"
  smart 
    : Frontier reasoning for multi-file refactoring and architecture.
                Invoked via: asmart "your prompt"

COMMAND USAGE:
  arouter                 Launch interactive TUI to reassign model tiers
  arouter --show          Display all active tier assignments with usage notes
  arouter --show <tier>   Display single tier (e.g. 'arouter --show cheap')
  arouter --help          Display this help overview

SHELL WRAPPERS & STDIN PIPING:
  All tier commands accept direct arguments or piped content via stdin:
    cat file.py | acheap "Explain this module"
    cat requirements.txt | abalanced "What dependencies are missing?"
    git diff | asmart "Review staged changes for regressions"

TIER CONFIGURATION:
  Tier preferences persist in ~/.cursor/arouter-config.json.
  In the interactive menu, tier names can be abbreviated as:
    'c' (cheap), 'b' (balanced), or 's' (smart).
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
        cmd = TIER_HINTS.get(norm, f"a{norm}")
        print(f"  [a{norm:<8}] -> {model:<28}")
        return

    print()
    print("======================================================================")
    print("  CURRENT ACTIVE CURSOR TIERS")
    print("======================================================================")
    for t in ('cheap', 'balanced', 'smart'):
        model = cfg.get(t, 'auto')
        cmd = TIER_HINTS.get(t, f"a{t}")
        print(f"  [a{t:<8}] -> {model:<28}")
    print("======================================================================")
    print()


def display_interactive_menu() -> None:
    tier_config = load_tier_config()
    models = fetch_available_models()
    grouped = {vendor: [] for vendor, _ in VENDOR_ORDER}
    for m in models:
        fam = categorize_model(m)
        grouped[fam].append(m)

    number_to_model = {}
    current_idx = 1

    while True:
        print()
        print("======================================================================")
        print("  AVAILABLE CURSOR MODELS (GROUPED BY VENDOR)")
        print("======================================================================")
        number_to_model.clear()
        current_idx = 1

        for vendor, _ in VENDOR_ORDER:
            members = grouped.get(vendor, [])
            if not members:
                continue
            print()
            print(f"--- {vendor} ---")
            for m in members:
                num_str = str(current_idx)
                number_to_model[num_str] = m
                print(f"  [{current_idx:2d}] {m}")
                current_idx += 1

        print()
        print("----------------------------------------------------------------------")
        print("Current Active Tiers:")
        for t in ('cheap', 'balanced', 'smart'):
            model = tier_config.get(t, 'auto')
            cmd = TIER_HINTS.get(t, f"a{t}")
            print(f"  [a{t:<8}] -> {model:<28}")
        print("======================================================================")

        try:
            tier_raw = input("👉 Enter tier to edit (a[c]heap / a[b]alanced / a[s]mart, or 'q' to exit): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if tier_raw in ('q', 'quit', 'exit', ''):
            print("Configuration saved.")
            sys.exit(0)

        if tier_raw not in TIER_MAP:
            print("⚠ Invalid tier. Choose 'c' (acheap), 'b' (abalanced), or 's' (asmart).")
            continue

        tier_choice = TIER_MAP[tier_raw]

        try:
            model_pick = input(f"👉 Enter model number for 'a{tier_choice}' [1..{len(number_to_model)}]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            sys.exit(0)

        if model_pick in number_to_model:
            selected_model = number_to_model[model_pick]
            tier_config[tier_choice] = selected_model
            save_tier_config(tier_config)
            print(f"✓ Tier 'a{tier_choice}' updated to -> {selected_model}")
        else:
            print(f"⚠️ Invalid model selection: '{model_pick}'")


if __name__ == '__main__':
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
