#!/usr/bin/env bash
# Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity
# P-S0-05 (S0-R5): 50 parallel reserves (10 processes x 5), 8 threads, SIGKILL mid-reserve; asserts contiguous distinct
# monotonic numbers, state.json parseable after the kill, highwater >= every returned number, no duplicate after restart.
exec bash "$(dirname "${BASH_SOURCE[0]}")/run_pytest.sh" test/actl/test_p05_seq.py
