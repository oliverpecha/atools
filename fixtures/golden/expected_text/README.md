# expected_text
Authored-by: Perplexity (AI assistant developed by Perplexity AI; underlying model name not disclosed to this agent), model family: Perplexity

`sprint.toml.tmpl` is the normative byte-exact text of a resolved `sprint.toml` (S0-R4/S0-R8, P-S0-09). Placeholders: `{{sprint_tag}}`, `{{base_sha}}`,
`{{status}}` (`draft`|`frozen`), `{{spec_source}}` (`architect_qna`|`imported`), `{{live_run_line}}` (empty for a draft, `live_run = "none"` + newline for the frozen golden sprint).
The file ends with exactly one newline. Location is `fixtures/golden/expected_text/` (not under `sprint/`): `build_golden.sh` and `test_p09_defaults.py` read it there.
