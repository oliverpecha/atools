#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-21), model family: Claude
# P-S0-30: gap proofs T1-T10 covering hashing, IDs, seq ordering, scope globs, schemas, CLI errors, and sprint state
exec bash "$(dirname "${BASH_SOURCE[0]}")/run_pytest.sh" test/actl/test_s0_gap_*.py
