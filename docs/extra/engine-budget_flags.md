This analysis evaluates the current per-session budget controls across **Anthropic Claude Code**, **Cursor Agent CLI**, and **OpenAI Codex CLI** based on official documentation, configuration references, and CLI specifications.

---

### Comparative Evaluation Table

| Tool & Control Type | Exact Flag / Config Key | Docs Link | Works in Headless / Non-Interactive? | Behavior on Hit (Exit Code, Partial Output) | Verification Status |
| --- | --- | --- | --- | --- | --- |
| **Anthropic Claude Code** |  |  |  |  |  |
| • *Max turns / tool calls* | `--max-turns <N>` | [CLI Reference](https://code.claude.com/docs/en/cli-reference) | **Yes** (required with `-p` / non-interactive print mode) | Exits with a nonzero exit code (`1`). Yields final result message with error subtype `error_max_turns` (`Reached maximum number of turns`). | **Verified in docs** |
| • *Max cost in currency* | `--max-budget-usd <amount>` (or `max_budget_usd` in options) | [CLI Reference](https://code.claude.com/docs/en/cli-reference) | **Yes** (intended for `-p` print mode) | Exits with a nonzero code. Emits error subtype `error_max_budget_usd`. The in-flight turn finishes and is counted; subagents are halted. | **Verified in docs** |
| • *Max tokens (session ceiling)* | `MAX_THINKING_TOKENS` *(thinking tokens only; overall session token cap absent)* | [Env Vars](https://code.claude.com/docs/en/env-vars) | **Yes** (env var applies globally) | For thinking tokens: clamps reasoning length. For total session tokens: **Not found** (only auto-compaction trigger `autoCompactWindow` exists). | **Verified in docs** *(Partial: thinking only)* |
| • *Wall-clock timeout* | `BASH_MAX_TIMEOUT_MS` *(per tool execution)*; overall run timeout absent in CLI flags | [Env Vars](https://code.claude.com/docs/en/env-vars) | **Yes** (for tool executions) | Per-command bash call aborts when exceeded. For entire session wall-clock timeout: **Not found** (must be handled by external wrappers like `timeout` or workflow runners). | **Not found** *(Session level)* / **Verified in docs** *(Tool call level)* |
| • *Model / Reasoning effort* | `--model <ID>`, `/effort <level>`, `alwaysThinkingEnabled` | [CLI Reference](https://code.claude.com/docs/en/cli-reference) / [Settings](https://code.claude.com/docs/en/settings-reference) | **Yes** (`--model` works in `-p`) | Enforces fixed model tier and thinking constraints during the run. Does not terminate with error. | **Verified in docs** |
| **Cursor Agent CLI** |  |  |  |  |  |
| • *Max turns / tool calls* | *None* | [CLI Parameters](https://cursor.com/docs/cli/reference/parameters) | N/A | **Not found**. Cursor Agent documentation explicitly notes there is no limit on tool calls per task. | **Not found** |
| • *Max cost in currency* | *None* (CLI flag absent; account-wide monthly spend limit only) | [CLI Parameters](https://cursor.com/docs/cli/reference/parameters) / [Spend Limits](https://cursor.com/help/account-and-billing/spend-limits) | N/A | **Not found** at CLI/session level. Monthly account caps stop agent requests across the account with an out-of-budget API error. | **Not found** |
| • *Max tokens* | *None* | [CLI Parameters](https://cursor.com/docs/cli/reference/parameters) | N/A | **Not found**. No per-session token budget flag exists. | **Not found** |
| • *Wall-clock timeout* | *None* (Shell tool execution hardcoded to 30s) | [Shell Mode](https://cursor.com/docs/cli/shell-mode) | N/A | **Not found** for session. Bash/shell commands timeout after 30 seconds (non-configurable). | **Not found** *(Session level)* |
| • *Model / Reasoning effort* | `--model <model>` | [CLI Parameters](https://cursor.com/docs/cli/reference/parameters) | **Yes** (supported with `-p` / `--print`) | Pins model variant; Max Mode context variants are passed when specified in headless runs. | **Verified in docs** |
| **OpenAI Codex CLI** |  |  |  |  |  |
| • *Max turns / tool calls* | *None* | [GitHub openai/codex](https://github.com/openai/codex) | N/A | **Not found**. Feature request #12336 specifically requests adding `--max-turns` to the CLI. | **Not found** |
| • *Max cost in currency* | *None* | [Codex Config Docs](https://github.com/openai/codex/blob/main/docs/config.md) | N/A | **Not found**. Rate/credit caps are enforced only by account-level ChatGPT/API quotas. | **Not found** |
| • *Max tokens* | *None* | [GitHub openai/codex](https://github.com/openai/codex) | N/A | **Not found**. Only internal sub-budgets exist (e.g., hardcoded 2% context ceiling for skill listings). | **Not found** |
| • *Wall-clock timeout* | *None* | [GitHub openai/codex](https://github.com/openai/codex) | N/A | **Not found** at CLI session level. External timeouts required. | **Not found** |
| • *Model / Reasoning effort* | `--model` / `-m`, and `-c model_reasoning_effort="<low|medium|high>"` (or in `config.toml`) | [Codex Reference](https://github.com/openai/codex) | **Yes** (works with both interactive `codex` and headless `codex exec`) | Caps or fixes reasoning effort tokens per request. Run completes without failure. | **Verified in docs** |
| **Google Antigravity CLI (`agy`)** |  |  |  |  |  |
| • *Max turns / tool calls* | *None* *(Outputs `num_turns` in session metadata, but provides no hard stop ceiling)* | [Headless Mode](https://antigravity.google/docs/cli/headless/) | N/A | **Not found**. There is no `--max-turns` flag to halt execution. Stdin stream terminates only upon EOF or manual interrupt (`SIGINT`). | **Not found** |
| • *Max cost in currency* | *None* (Monitored interactively via `/credits` and `/usage`) | [CLI Reference](https://antigravity.google/docs/cli/reference/) | N/A | **Not found** at CLI session level. Only upstream Google Cloud / AI Studio / account credit quotas are enforced. | **Not found** |
| • *Max tokens* | *None* (Context visualizer available via `/context`, but no limit flag exists) | [CLI Reference](https://antigravity.google/docs/cli/reference/) | N/A | **Not found**. No per-session token budget exists; tracked in open feature requests. | **Not found** |
| • *Wall-clock timeout* | *None* (Only `--mcp-timeout` / MCP handshake timeout exists) | [Changelog](https://antigravity.google/docs/changelog/) | N/A | **Not found** for overall session run. Execution depends on process lifecycle or external shell `timeout`. | **Not found** *(Session level)* / **Verified in docs** *(MCP server handshake only)* |
| • *Model / Reasoning effort* | `--model <name>`, `--effort <low|medium|high>` (or `/effort`, `/model`) | [Headless Mode](https://antigravity.google/docs/cli/headless/) / [CLI Reference](https://antigravity.google/docs/cli/reference/) | **Yes** (supported with `-p` / `--print`) | Pins the model variant and controls reasoning depth (Flash/Pro thinking budget). Does not exit with error unless an unrecognized model name is supplied (exits non-zero `ERROR`). | **Verified in docs** |

---

### Detailed Findings by Agent

#### 1. Anthropic Claude Code

* **Turn Limits:** Supported via `--max-turns <N>` in non-interactive/print mode (`-p`). When the turn counter hits the threshold, the session terminates with exit code `1` and emits an `error_max_turns` result message.
* **Currency Budget:** Supported via `--max-budget-usd <float>`. Tracks client-side estimated API costs across the agent loop (including spawned subagents). When breached, ongoing background subagents are halted, the final response finishes execution and is counted, and the process exits with a nonzero exit code (`error_max_budget_usd`).
* **Timeouts & Token Ceilings:** An overall session wall-clock flag is not present; Anthropic advises wrapping invocation commands in CI/workflow-level timeouts (such as the standard coreutils `timeout` command). A dedicated reasoning token ceiling can be configured via `MAX_THINKING_TOKENS`.

#### 2. Cursor Agent CLI

* **Per-Session Budgeting:** Cursor Agent CLI does not provide session-scoped flags for turns, token consumption, or cost. Cursor relies on account-level credit quotas and monthly spend limits managed via the web dashboard.
* **Turn Limits:** Official documentation notes there is no ceiling on agentic tool roundtrips.
* **Tool Constraints:** Command executions inside the CLI shell sandbox are hard-capped to a 30-second timeout that cannot be adjusted.
* **Model Pinning:** Flags like `--model <name>` are supported in both headless (`-p` / `--print`) and interactive modes.

#### 3. OpenAI Codex CLI

* **Per-Session Budgeting:** Codex CLI (`codex` and `codex exec`) does not offer built-in `--max-turns`, `--max-budget`, `--timeout`, or session token limit parameters. Requests for CLI-level turn limits remain open enhancement issues.
* **Reasoning Configuration:** Model ceilings and reasoning constraints can be set via `-m <model>` or inline configuration overrides (`-c model_reasoning_effort="low|medium|high"`), as well as in `~/.codex/config.toml`. These control per-turn inference depth rather than acting as a cumulative circuit breaker.



### 4. Google Antigravity CLI (`agy`)

* **Headless Architecture:** Antigravity CLI offers robust headless and streaming execution via `-p` / `--print` and `--output-format stream-json`. It surfaces post-run execution telemetry (including `duration_seconds` and cumulative `num_turns`) inside JSON output envelopes, but does not provide input flags to constrain or cap them before launch.
* **Budget & Turns Deficit:** Like Cursor and Codex, Antigravity CLI lacks native `--max-turns` and `--max-budget` flags. It relies on upstream platform quotas (Google AI Studio credits or Gemini API keys).
* **Reasoning Configuration:** Both model pinning (`--model`) and thinking constraints (`--effort low|medium|high`) are directly configurable as CLI overrides during headless invocations (`agy -p "..." --effort high`).
