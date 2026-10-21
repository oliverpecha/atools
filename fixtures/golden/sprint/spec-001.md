# spec-001: public profiles
Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude

## Requirements
- R1: Guests see name, bio, avatar and photo count of public profiles.
- R2: Never expose email (in any key, in any form).
- R3: Private profiles return 404.

Behaviour contract: `python3 -m api.cli profile <id>` prints one JSON line `{"status": <int>, "body": {...}}` and exits 0.
Public body keys: `name`, `bio`, `avatar`, `photo_count`. A private or unknown id yields status 404 and body `{"error": "not_found"}`.
Visibility is held in `api.users.PUBLIC_USER_IDS` (ids 1 and 2 are public, 3 is private).

## Locked
- The users schema (the key set of each record in `api.users.USERS`) is unchanged.

## Deferred
- Search engine indexing of public profiles.
