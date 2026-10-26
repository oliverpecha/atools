# Stage 2 Vacuity and Mutation Plan (Seed 79)
Authored-by: Gemini 3.1 Pro (Google), model family: Gemini
Date: 2026-10-26. Reserved Seed: 79.

## 1. Vacuity Protocol
Each Stage 2 proof P-S2-01..P-S2-17 is verified against three standard stand-in configurations:
- Configuration (a): Empty module (pure stub raising NotImplementedError or missing module).
- Configuration (b): Always-succeed stub (pure stub returning exit code 0 or empty ok status).
- Configuration (c): Always-fail stub (pure stub raising SystemExit(1) or unhandled RuntimeError).

A proof is deemed non-vacuous if and only if it fails against stand-in configurations that violate the requirement contract.

## 2. Mutation Testing Strategy (Seed 79)
Mutations are evaluated using tools/mutate.py with reserved seed 79 across all Stage 2 modules:
- actl/turns.py: sequence allocation, directory mode checks, path bounds.
- actl/cmd_bundle.py: header assembly, include validation, sentinel suffix computation.
- actl/envelope.py: delimiter scaling, path safety, unquoted sentinel rejection.
- actl/cmd_unpack.py: Step 3 normalization, BOM stripping, CRLF handling, atomic swap.
- actl/patchsynth.py: difflib candidate calculation, multi-hunk sequencing, new-file creation.
- actl/promote.py: 7-key dictionary return, staged_to path resolution, deduplication tuple.
- actl/next_rules/phase12.py: priority ordering (PRIORITY = 10) and 10-state decision tree.

Target mutation score: 100% kill rate of all non-equivalent mutants.
