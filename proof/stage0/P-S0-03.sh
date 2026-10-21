#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# P-S0-03: test_p03_layout.py
exec bash "$(dirname "${BASH_SOURCE[0]}")/run_pytest.sh" test/actl/test_p03_layout.py
