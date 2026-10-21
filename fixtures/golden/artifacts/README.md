# artifacts
Authored-by: Claude Sonnet 5.5 (Anthropic; accessed via the Perplexity web UI; Owner-attested 2026-10-20), model family: Claude

`valid/<kind>/*.json` must give `[]` from `schemas.validate(kind, obj)`. `invalid/<kind>/*.json` must give errors whose set of `path`
values equals `expect_paths` in `invalid/index.json` exactly (messages are not asserted). JSON files carry no Authored-by field because the
schemas use `additionalProperties: false` (SA-14). `sprint` documents are the TOML->JSON form of `sprint.toml`.
Owner rulings (2026-10-20) are reflected: 40-hex SHAs only, `owner_review_triggers` vocabulary `plan_deviation|budget_exceeded|critical_tripwire|manual_flag`
(old action names are invalid), `ev.exit_code` is an integer 0..255 or null.
