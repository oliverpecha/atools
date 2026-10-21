#!/usr/bin/env bash
# Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude
# P-S0-05 (S0-R5): 50 parallel reserves (10 processes x 5), 8 threads, SIGKILL mid-reserve; asserts contiguous distinct
# monotonic numbers, state.json parseable after the kill, highwater >= every returned number, no duplicate after restart.
exec bash "$(dirname "${BASH_SOURCE[0]}")/run_pytest.sh" test/actl/test_p05_seq.py
