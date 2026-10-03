# atools

Modular orchestration, process supervision, and deterministic safety guardrails for headless coding agent loops.

## Architecture & Layout

```text
atools/
├── install.sh                  # Non-destructive system installer & hook setup
├── VERSION                     # Release version indicator
├── bin/
│   └── arouter                 # Universal tier router & compliance dispatcher
├── engines/
│   ├── cursor-agent.sh         # Hardened headless Cursor Agent runtime
│   ├── openai-codex.sh         # OpenAI Codex adapter
│   ├── claude-code.sh          # Anthropic Claude Code adapter
│   ├── google-agy.sh           # Google Antigravity adapter
│   ├── aider.sh                # Aider CLI adapter
│   └── mistral-vibe.sh         # Mistral Vibe adapter
├── rules/
│   └── git-safety.md           # Machine-wide wip/* branch enforcement rules
├── hooks/
│   └── pre-commit              # Dual pre-commit isolation hook
├── proof/
│   └── run_suite_engines.sh    # Deterministic test harness
└── audit/
    └── atools-compliance_audit.sh # 36-point compliance validator

```

## Quickstart for Colleagues

```bash
# 1. Clone repository
git clone git@github.com:<org>/atools.git ~/.atools
cd ~/.atools

# 2. Run automated installer
./install.sh

# 3. Configure tier mappings
arouter --set cheap gemini-3.8-flash-low
arouter --set balanced gemini-3.8-flash-medium
arouter --set smart gemini-3.8-flash-high

# 4. Verify installation
arouter --show
bash proof/run_suite_engines.sh

```

## Execution Tiers

* `acheap "<prompt>"`: Fast routine refactoring, lint fixes, single-line adjustments.
* `abalanced "<prompt>"`: Primary autonomous driver for multi-file repairs and test debugging.
* `asmart "<prompt>"`: Complex, architectural, or ambiguous changes.

## Engine Switching

Select runtime engine via flag or environment variable:

```bash
# Via flag
arouter --engine claude-code smart "Refactor core loop"
arouter --engine openai-codex cheap "Lint files"

# Via environment variable
export ATOOLS_ENGINE=cursor
abalanced "Run repair loop"

```
