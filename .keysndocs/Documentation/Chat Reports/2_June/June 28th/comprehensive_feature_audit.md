# Comprehensive Feature Audit — Pi · Hermes Agent · OpenHuman · Locus OS

> **Audit date**: 2026-06-28
> **Scope**: Every feature, every flag, every tool, every module at atomic granularity
> **Method**: Full codebase reads + targeted deep-dives across ~11,000 source files

---

## Table of Contents

1. [Pi Agent — Feature Inventory](#1-pi-agent-earendil-works)
2. [Hermes Agent — Feature Inventory](#2-hermes-agent-nous-research)
3. [OpenHuman — Feature Inventory](#3-openhuman-tinyhumansai)
4. [Locus OS — Feature Inventory](#4-locus-os)
5. [Cross-Codebase Comparison Matrix](#5-cross-codebase-comparison-matrix)
6. [Feature Overlap Analysis](#6-feature-overlap-analysis)
7. [Gaps &amp; Missing Features](#7-gaps--missing-features)

---

AC52-38E5

# 1. Pi Agent (earendil-works)

**Stack**: TypeScript / Node.js monorepo | 3 packages (ai, agent, coding-agent) + TUI
**Size**: ~844 source files | `packages/` dir

## 1.1 Coding Agent CLI (`packages/coding-agent/src/cli.ts` + `cli/args.ts`)

### Command-line Flags (all 30+ flags)

| Flag                         | Type                                   | Description                          |
| ---------------------------- | -------------------------------------- | ------------------------------------ |
| `--provider`               | string                                 | AI provider to use                   |
| `--model`                  | string                                 | Model name override                  |
| `--api-key`                | string                                 | API key for provider                 |
| `--system-prompt`          | string                                 | System prompt path or inline         |
| `--append-system-prompt`   | string[]                               | Additional system prompts to append  |
| `--thinking`               | off\|minimal\|low\|medium\|high\|xhigh | Thinking level                       |
| `--continue`               | boolean                                | Continue from last session           |
| `--resume`                 | boolean                                | Resume a specific session            |
| `--mode`                   | text\|json\|rpc                        | Output mode                          |
| `--name`                   | string                                 | Session name                         |
| `--no-session`             | boolean                                | Don't persist session                |
| `--session`                | string                                 | Session ID for resume                |
| `--session-id`             | string                                 | Explicit session ID                  |
| `--fork`                   | string                                 | Fork from session ID                 |
| `--session-dir`            | string                                 | Custom session dir                   |
| `--models`                 | string[]                               | Model constraints                    |
| `--tools`                  | string[]                               | Allowlisted tools                    |
| `--exclude-tools`          | string[]                               | Blocklisted tools                    |
| `--no-tools`               | boolean                                | Disable all tools                    |
| `--no-builtin-tools`       | boolean                                | Disable built-in tools only          |
| `--extensions`             | string[]                               | Extension paths/names                |
| `--no-extensions`          | boolean                                | Disable extensions                   |
| `--print`                  | boolean                                | Print response and exit (batch mode) |
| `--export`                 | string                                 | Export session (html\|json\|md)      |
| `--no-skills`              | boolean                                | Disable skills                       |
| `--skills`                 | string[]                               | Skills to load                       |
| `--prompt-templates`       | string[]                               | Prompt template files                |
| `--no-prompt-templates`    | boolean                                | Disable prompt templates             |
| `--no-themes`              | boolean                                | Disable themes                       |
| `--no-context-files`       | boolean                                | Disable context file loading         |
| `--list-models`            | string\|true                           | List available models                |
| `--offline`                | boolean                                | Offline mode                         |
| `--verbose`                | boolean                                | Verbose logging                      |
| `--project-trust-override` | boolean                                | Override project trust               |
| `--help`                   | boolean                                | Show help                            |
| `--version`                | boolean                                | Show version                         |

### Run Modes (`packages/coding-agent/src/modes/`)

| Mode              | File                                      | Description                                     |
| ----------------- | ----------------------------------------- | ----------------------------------------------- |
| Interactive (TUI) | `modes/interactive/interactive-mode.ts` | Full terminal UI with streaming                 |
| Print (batch)     | `modes/print-mode.ts`                   | One-shot query → print response → exit        |
| RPC (daemon)      | `modes/rpc/rpc-mode.ts`                 | JSON-RPC protocol for IDE/extension integration |
| JSON              | (via`--mode json`)                      | Structured JSON output                          |

## 1.2 Agent Harness (`packages/agent/src/`)

### Agent Loop

| Component            | File                         | Description                                 |
| -------------------- | ---------------------------- | ------------------------------------------- |
| `runAgentLoop()`   | `agent-loop.ts`            | Two-entry system: tooled loop + simple loop |
| `agent-harness.ts` | `harness/agent-harness.ts` | Full agent runtime with state management    |
| `Agent` class      | `agent.ts`                 | Stateful agent wrapper with tool execution  |

### Tool Execution

| Tool                        | File                                      | Description                         |
| --------------------------- | ----------------------------------------- | ----------------------------------- |
| `read`                    | `core/tools/read.ts`                    | Read file contents                  |
| `write`                   | `core/tools/write.ts`                   | Write/create files                  |
| `edit`                    | `core/tools/edit.ts`                    | Edit files with precise replacement |
| `edit-diff`               | `core/tools/edit-diff.ts`               | Diff-based file editing             |
| `bash`                    | `core/tools/bash.ts`                    | Execute shell commands              |
| `grep`                    | `core/tools/grep.ts`                    | Search file contents                |
| `ls`                      | `core/tools/ls.ts`                      | List directory contents             |
| `find`                    | `core/tools/find.ts`                    | Find files by pattern               |
| `tool-definition-wrapper` | `core/tools/tool-definition-wrapper.ts` | Tool call validation                |
| `output-accumulator`      | `core/tools/output-accumulator.ts`      | Accumulate tool output              |
| `file-mutation-queue`     | `core/tools/file-mutation-queue.ts`     | Queue file operations               |

### Session System (`packages/agent/src/harness/session/`)

| Feature                | File                  | Description                            |
| ---------------------- | --------------------- | -------------------------------------- |
| Tree-based persistence | `session.ts`        | Session stored as tree of entries      |
| JSONL storage          | `jsonl-storage.ts`  | Append-only JSONL log format           |
| JSONL repo             | `jsonl-repo.ts`     | Session JSONL repository with ID index |
| Memory storage         | `memory-storage.ts` | In-memory session backend              |
| Memory repo            | `memory-repo.ts`    | In-memory session repository           |
| UUID generation        | `uuid.ts`           | Session/entry ID generation            |
| Repo utils             | `repo-utils.ts`     | Repository helpers                     |

### Compaction (`packages/coding-agent/src/core/compaction/`)

| Feature              | File                        | Description                                 |
| -------------------- | --------------------------- | ------------------------------------------- |
| Compaction engine    | `compaction.ts`           | Summarize older turns to fit context window |
| Branch summarization | `branch-summarization.ts` | Summarize forked branches                   |
| Compaction utils     | `utils.ts`                | Shared compaction utilities                 |

### Hooks (`packages/agent/docs/hooks.md`)

| Hook               | Description             |
| ------------------ | ----------------------- |
| `beforeResponse` | Before LLM response     |
| `afterResponse`  | After LLM response      |
| `beforeToolCall` | Before tool execution   |
| `afterToolCall`  | After tool execution    |
| `onSessionStart` | Session lifecycle start |
| `onSessionEnd`   | Session lifecycle end   |

### System Prompt

| Feature               | File                            | Description                               |
| --------------------- | ------------------------------- | ----------------------------------------- |
| System prompt builder | `harness/system-prompt.ts`    | Builds dynamic system prompt              |
| Prompt templates      | `harness/prompt-templates.ts` | Template-based prompts                    |
| Skills system         | `harness/skills.ts`           | Load and inject skills into system prompt |

### Types & Messages

| Feature       | File                    | Description             |
| ------------- | ----------------------- | ----------------------- |
| Message types | `harness/messages.ts` | Message data structures |
| Harness types | `harness/types.ts`    | Core type definitions   |

## 1.3 AI Provider Layer (`packages/ai/src/`)

### Provider Backends (9+)

| Provider                | File                                     | Description                    |
| ----------------------- | ---------------------------------------- | ------------------------------ |
| OpenAI Responses        | `providers/openai-responses.ts`        | OpenAI chat completions API    |
| OpenAI Completions      | `providers/openai-completions.ts`      | Legacy completions API         |
| OpenAI Responses Shared | `providers/openai-responses-shared.ts` | Shared OpenAI logic            |
| OpenAI Codex Responses  | `providers/openai-codex-responses.ts`  | Codex-specific adapter         |
| OpenAI Prompt Cache     | `providers/openai-prompt-cache.ts`     | Prompt caching support         |
| Anthropic               | `providers/anthropic.ts`               | Anthropic Claude API           |
| Google                  | `providers/google.ts`                  | Google Gemini API              |
| Google Vertex           | `providers/google-vertex.ts`           | GCP Vertex AI                  |
| Google Shared           | `providers/google-shared.ts`           | Shared Google provider logic   |
| Amazon Bedrock          | `providers/amazon-bedrock.ts`          | AWS Bedrock                    |
| Azure OpenAI Responses  | `providers/azure-openai-responses.ts`  | Azure OpenAI                   |
| Cloudflare              | `providers/cloudflare.ts`              | Cloudflare Workers AI          |
| Mistral                 | `providers/mistral.ts`                 | Mistral AI                     |
| GitHub Copilot Headers  | `providers/github-copilot-headers.ts`  | GitHub Copilot auth            |
| Faux (testing)          | `providers/faux.ts`                    | Mock provider for tests        |
| Azure OpenAI Responses  | `providers/azure-openai-responses.ts`  | Azure OpenAI Responses API     |
| Simple Options          | `providers/simple-options.ts`          | Simplified provider config     |
| Message Transform       | `providers/transform-messages.ts`      | Message format transformations |

### Provider Registry

| Feature              | File                               | Description                   |
| -------------------- | ---------------------------------- | ----------------------------- |
| API registry         | `api-registry.ts`                | Central provider registry     |
| Builtin registration | `providers/register-builtins.ts` | Auto-register all providers   |
| Model types          | `models.ts`                      | Model definitions             |
| Generated models     | `models.generated.ts`            | Auto-generated model metadata |
| Model utilities      | `models.ts`                      | Model lookups                 |
| Image models         | `image-models.ts`                | Image generation models       |

### Streaming & Types

| Feature           | File                     | Description                      |
| ----------------- | ------------------------ | -------------------------------- |
| Stream protocol   | `stream.ts`            | SSE streaming support            |
| Core types        | `types.ts`             | Request/response types           |
| CLI               | `cli.ts`               | Provider CLI utilities           |
| Env API keys      | `env-api-keys.ts`      | Environment-based key management |
| OAuth             | `oauth.ts`             | OAuth flow support               |
| Session resources | `session-resources.ts` | Session-scoped resources         |

### Image Generation

| Feature            | File                       | Description             |
| ------------------ | -------------------------- | ----------------------- |
| Image API          | `images.ts`              | Image generation        |
| Image API registry | `images-api-registry.ts` | Image provider registry |

### Utility Layer

| Feature          | File                          | Description             |
| ---------------- | ----------------------------- | ----------------------- |
| Abort signals    | `utils/abort-signals.ts`    | Cancellation support    |
| Diagnostics      | `utils/diagnostics.ts`      | Provider diagnostics    |
| Event stream     | `utils/event-stream.ts`     | SSE event parser        |
| Hash             | `utils/hash.ts`             | Request caching hash    |
| Headers          | `utils/headers.ts`          | HTTP header utilities   |
| JSON parse       | `utils/json-parse.ts`       | Safe JSON parsing       |
| Node HTTP proxy  | `utils/node-http-proxy.ts`  | HTTP proxy support      |
| Overflow         | `utils/overflow.ts`         | Token overflow handling |
| Sanitize unicode | `utils/sanitize-unicode.ts` | Unicode sanitization    |
| TypeBox helpers  | `utils/typebox-helpers.ts`  | Schema validation       |
| Validation       | `utils/validation.ts`       | Input validation        |

## 1.4 TUI (`packages/coding-agent/src/core/` + TUI widgets)

| Feature                | File                               | Description                          |
| ---------------------- | ---------------------------------- | ------------------------------------ |
| Event bus              | `core/event-bus.ts`              | Internal event system for UI updates |
| Keybindings            | `core/keybindings.ts`            | Keyboard shortcut system             |
| Slash commands         | `core/slash-commands.ts`         | `/command` parsing                 |
| Startup UI             | `cli/startup-ui.ts`              | Initial terminal UI on launch        |
| Session picker         | `cli/session-picker.ts`          | Interactive session selection        |
| Config selector        | `cli/config-selector.ts`         | Config UI picker                     |
| Project trust          | `cli/project-trust.ts`           | Trust prompt for projects            |
| Footer data provider   | `core/footer-data-provider.ts`   | Status bar data                      |
| Provider attribution   | `core/provider-attribution.ts`   | Show current provider                |
| Provider display names | `core/provider-display-names.ts` | Human-readable provider names        |
| Diagnostics UI         | `core/diagnostics.ts`            | Diagnostic display                   |
| Timings                | `core/timings.ts`                | Response timing display              |
| Source info            | `core/source-info.ts`            | Source file display                  |
| Screen output guard    | `core/output-guard.ts`           | Prevent output overflow              |
| ANSI utils             | `utils/ansi.ts`                  | ANSI escape code handling            |
| Shell integration      | `utils/shell.ts`                 | Shell integration                    |
| Session CWD            | `core/session-cwd.ts`            | Working directory tracking           |

## 1.5 Extensions System (`packages/coding-agent/src/core/extensions/`)

| Feature           | File           | Description                    |
| ----------------- | -------------- | ------------------------------ |
| Extension loader  | `loader.ts`  | Load extensions from paths     |
| Extension runner  | `runner.ts`  | Execute extension lifecycle    |
| Extension types   | `types.ts`   | Extension API types            |
| Extension wrapper | `wrapper.ts` | Sandbox wrapper for extensions |
| Extension index   | `index.ts`   | Extension registry             |

## 1.6 Config & Settings

| Feature              | File                             | Description                      |
| -------------------- | -------------------------------- | -------------------------------- |
| Config loader        | `config.ts`                    | YAML/JSON config loading         |
| Settings manager     | `core/settings-manager.ts`     | User settings read/write         |
| Resolve config value | `core/resolve-config-value.ts` | Resolve config with env fallback |
| Migrations           | `migrations.ts`                | Config schema migration          |
| Defaults             | `core/defaults.ts`             | Default configuration            |
| Package manager      | `core/package-manager.ts`      | Pi package management            |
| Package manager CLI  | `package-manager-cli.ts`       | CLI for package management       |

## 1.7 HTTP Dispatcher

| Feature         | File                        | Description                           |
| --------------- | --------------------------- | ------------------------------------- |
| HTTP dispatcher | `core/http-dispatcher.ts` | HTTP server for external integrations |

## 1.8 Export

| Feature       | File                                  | Description                |
| ------------- | ------------------------------------- | -------------------------- |
| HTML export   | `core/export-html/index.ts`         | Export session to HTML     |
| ANSI to HTML  | `core/export-html/ansi-to-html.ts`  | Convert ANSI to HTML       |
| Tool renderer | `core/export-html/tool-renderer.ts` | Tool output HTML rendering |

## 1.9 Utilities (`packages/coding-agent/src/utils/`)

| Feature             | File                            | Description                  |
| ------------------- | ------------------------------- | ---------------------------- |
| Clipboard           | `clipboard.ts`                | System clipboard read/write  |
| Clipboard native    | `clipboard-native.ts`         | Native clipboard integration |
| Clipboard image     | `clipboard-image.ts`          | Image clipboard support      |
| Child process       | `child-process.ts`            | Process spawning             |
| Changelog           | `changelog.ts`                | Release notes viewer         |
| Deprecation         | `deprecation.ts`              | Deprecation warnings         |
| Exif orientation    | `exif-orientation.ts`         | Image orientation detection  |
| Frontmatter         | `frontmatter.ts`              | YAML frontmatter parser      |
| FS watch            | `fs-watch.ts`                 | File system watcher          |
| Git                 | `git.ts`                      | Git integration              |
| Highlight.js types  | `highlight-js-lib-index.d.ts` | Syntax highlighting types    |
| HTML utils          | `html.ts`                     | HTML processing              |
| Image convert       | `image-convert.ts`            | Image format conversion      |
| Image resize        | `image-resize.ts`             | Image resizing               |
| JSON utils          | `json.ts`                     | JSON helpers                 |
| MIME types          | `mime.ts`                     | MIME type detection          |
| Open browser        | `open-browser.ts`             | Open URL in browser          |
| Paths               | `paths.ts`                    | Path resolution              |
| Photon              | `photon.ts`                   | Image library bindings       |
| Pi user agent       | `pi-user-agent.ts`            | User agent string            |
| Sleep               | `sleep.ts`                    | Async sleep                  |
| Syntax highlight    | `syntax-highlight.ts`         | Code syntax highlighting     |
| Tools manager       | `tools-manager.ts`            | Tool management              |
| Version check       | `version-check.ts`            | Update checking              |
| Windows self-update | `windows-self-update.ts`      | Windows auto-update          |

## 1.10 Agent Mode Features

| Feature                | File                               | Description                  |
| ---------------------- | ---------------------------------- | ---------------------------- |
| Mode index             | `modes/index.ts`                 | Mode registry                |
| Agent session runtime  | `core/agent-session-runtime.ts`  | Session lifecycle runtime    |
| Agent session services | `core/agent-session-services.ts` | Session services             |
| Agent session          | `core/agent-session.ts`          | Main agent session           |
| Session manager        | `core/session-manager.ts`        | Session lifecycle management |
| Auth storage           | `core/auth-storage.ts`           | Auth credential storage      |
| Auth guidance          | `core/auth-guidance.ts`          | Auth setup guidance          |
| Experimental           | `core/experimental.ts`           | Experimental features        |
| Telemetry              | `core/telemetry.ts`              | Usage telemetry              |
| Resource loader        | `core/resource-loader.ts`        | File resource loading        |
| Trust manager          | `core/trust-manager.ts`          | Project trust management     |

---

# 2. Hermes Agent (Nous Research)

**Stack**: Python 3.11-3.13 | 90 agent modules + CLI (650K) + gateway + apps
**Size**: ~5,048 source files | core agent: 90 .py files

## 2.1 Agent Loop & Runtime

| Feature           | File                           | Description          |
| ----------------- | ------------------------------ | -------------------- |
| Conversation loop | `agent/conversation_loop.py` | Main agent turn loop |

# 2. Hermes Agent (Nous Research)

**Stack**: Python 3.11-3.13 | 90 agent modules + CLI (650K lines) + gateway + apps
**Size**: ~5,048 source files | core agent: 90 .py files

## 2.1 Agent Loop & Runtime

| Feature                     | File                                     | Description                        |
| --------------------------- | ---------------------------------------- | ---------------------------------- |
| Conversation loop           | `agent/conversation_loop.py`           | Main agent turn loop               |
| Agent init                  | `agent/agent_init.py`                  | Agent initialization and bootstrap |
| Agent runtime helpers       | `agent/agent_runtime_helpers.py`       | Runtime utility functions          |
| Turn context                | `agent/turn_context.py`                | Per-turn context management        |
| Turn finalizer              | `agent/turn_finalizer.py`              | End-of-turn processing             |
| Turn retry state            | `agent/turn_retry_state.py`            | Retry logic for failed turns       |
| System prompt               | `agent/system_prompt.py`               | Dynamic system prompt assembly     |
| Prompt builder              | `agent/prompt_builder.py`              | Prompt construction utilities      |
| Prompt caching              | `agent/prompt_caching.py`              | LLM prompt caching support         |
| Context engine              | `agent/context_engine.py`              | Context window management          |
| Context compressor          | `agent/context_compressor.py`          | Compress oversized context         |
| Context references          | `agent/context_references.py`          | Reference tracking in context      |
| Coding context              | `agent/coding_context.py`              | Code-specific context              |
| Conversation compression    | `agent/conversation_compression.py`    | Compress conversation history      |
| Background review           | `agent/background_review.py`           | Async post-turn review             |
| Manual compression feedback | `agent/manual_compression_feedback.py` | User-driven compression tuning     |
| Stream diagnostics          | `agent/stream_diag.py`                 | Stream health monitoring           |
| Iteration budget            | `agent/iteration_budget.py`            | Max turn iteration control         |
| Async utils                 | `agent/async_utils.py`                 | Async concurrency utilities        |
| Retry utils                 | `agent/retry_utils.py`                 | Retry/backoff utilities            |
| Title generator             | `agent/title_generator.py`             | Auto-generate session titles       |
| Onboarding                  | `agent/onboarding.py`                  | First-run setup flow               |
| Rate limit tracker          | `agent/rate_limit_tracker.py`          | API rate limit tracking            |
| Usage pricing               | `agent/usage_pricing.py`               | Token cost calculation             |
| Credits tracker             | `agent/credits_tracker.py`             | Usage credits management           |
| Account usage               | `agent/account_usage.py`               | User account usage stats           |

## 2.2 TUI Terminal Interface (`cli.py` — 650K)

| Feature                    | Description                                             |
| -------------------------- | ------------------------------------------------------- |
| Multiline editing          | Full editor with multi-line input                       |
| Slash-command autocomplete | `/command` autocompletion                             |
| Conversation history       | Up/down arrow history navigation                        |
| Interrupt-and-redirect     | Cancel mid-generation and redirect                      |
| Streaming tool output      | Real-time streaming of tool results                     |
| Keyboard shortcuts         | Ctrl+C, Ctrl+D, Ctrl+Q, Ctrl+Z, Ctrl+L, Alt+Enter, etc. |
| Voice recording            | Inline voice recording via Ctrl+R                       |
| Paste support              | System clipboard paste                                  |
| Editor integration         | `$EDITOR` integration for long input                  |
| Tab completion             | Smart tab completion                                    |
| Open-in-editor             | Edit message in external editor                         |
| Escape modal               | Escape key for modal dialogs                            |

## 2.3 Multi-Platform Gateway (`gateway/`)

| Feature              | File                              | Description                       |
| -------------------- | --------------------------------- | --------------------------------- |
| Gateway runner       | `gateway/run.py`                | Main gateway runtime loop         |
| Platform registry    | `gateway/platform_registry.py`  | Channel registration and dispatch |
| Session management   | `gateway/session.py`            | Cross-platform session state      |
| Session context      | `gateway/session_context.py`    | Session-scoped context            |
| Message delivery     | `gateway/delivery.py`           | Message dispatch to channels      |
| Stream consumer      | `gateway/stream_consumer.py`    | SSE stream consumer               |
| Stream dispatch      | `gateway/stream_dispatch.py`    | Stream event routing              |
| Stream events        | `gateway/stream_events.py`      | Stream event types                |
| Auth middleware      | `gateway/authz_mixin.py`        | Authorization mixin               |
| Slash access control | `gateway/slash_access.py`       | Per-command access control        |
| Slash commands       | `gateway/slash_commands.py`     | Command routing                   |
| Hooks                | `gateway/hooks.py`              | Gateway lifecycle hooks           |
| Channel directory    | `gateway/channel_directory.py`  | Channel discovery                 |
| Kanban watchers      | `gateway/kanban_watchers.py`    | Kanban task monitoring            |
| Memory monitor       | `gateway/memory_monitor.py`     | Memory usage monitoring           |
| Mirror               | `gateway/mirror.py`             | Cross-platform message mirroring  |
| Pairing              | `gateway/pairing.py`            | Device pairing flow               |
| Restart              | `gateway/restart.py`            | Graceful daemon restart           |
| Runtime footer       | `gateway/runtime_footer.py`     | Status bar display                |
| Shutdown forensics   | `gateway/shutdown_forensics.py` | Crash logging                     |
| Status               | `gateway/status.py`             | Health/status reporting           |
| Sticker cache        | `gateway/sticker_cache.py`      | Sticker/media caching             |
| Config               | `gateway/config.py`             | Gateway configuration             |
| Display config       | `gateway/display_config.py`     | Per-channel display settings      |
| WhatsApp identity    | `gateway/whatsapp_identity.py`  | WhatsApp identity verification    |

**Supported Platforms** (via `apps/`):

| Platform           | Channel File                                               |
| ------------------ | ---------------------------------------------------------- |
| Telegram           | (via`apps/shared` + gateway adapter)                     |
| Discord            | (via`apps/shared` + gateway adapter)                     |
| Slack              | (via`apps/shared` + gateway adapter)                     |
| WhatsApp           | `gateway/whatsapp_identity.py`                           |
| Signal             | (via`apps/shared`)                                       |
| CLI/Terminal       | Built into`cli.py`                                       |
| Desktop (Electron) | `apps/desktop/electron/*.cjs` — full Electron app with: |

- Backend env management (`backend-env.cjs`)
- Backend probes (`backend-probes.cjs`)
- Platform bootstrap (`bootstrap-platform.cjs`)
- Runner bootstrap (`bootstrap-runner.cjs`)
- Connection config (`connection-config.cjs`)
- Dashboard token (`dashboard-token.cjs`)
- Desktop uninstall (`desktop-uninstall.cjs`)
- Entitlements (macOS `entitlements.mac.plist`)
- FS read dir (`fs-read-dir.cjs`)
- Gateway WS probe (`gateway-ws-probe.cjs`)
- Git root detection (`git-root.cjs`)
- Hardening (`hardening.cjs`)
- Main process (`main.cjs`)
- OAuth net request (`oauth-net-request.cjs`)
- Port pool (`port-pool.cjs`)
- Preload (`preload.cjs`)
- Session windows (`session-windows.cjs`)
- Update remote (`update-remote.cjs`)
- VSCode marketplace (`vscode-marketplace.cjs`)
- Workspace CWD (`workspace-cwd.cjs`)

## 2.4 Learning Loop

| Feature           | File                           | Description                                              |
| ----------------- | ------------------------------ | -------------------------------------------------------- |
| Curator           | `agent/curator.py`           | Main learning curator — extracts insights from sessions |
| Curator backup    | `agent/curator_backup.py`    | Backup curator as fallback                               |
| Insights          | `agent/insights.py`          | Insight generation from session patterns                 |
| Background review | `agent/background_review.py` | Async post-turn analysis                                 |

**Learning Loop Flow**:

1. Per-turn review → extract facts/patterns/mistakes
2. Curator → organize into structured insights
3. Memory nudge → periodic persistence to long-term store
4. Session search → FTS5 full-text search across sessions
5. LLM summarization → cross-session recall

## 2.5 Skills System (`skills/`)

| Feature             | File                             | Description                            |
| ------------------- | -------------------------------- | -------------------------------------- |
| Skill bundles       | `agent/skill_bundles.py`       | Skill grouping and activation          |
| Skill commands      | `agent/skill_commands.py`      | Skill-specific CLI commands            |
| Skill preprocessing | `agent/skill_preprocessing.py` | Pre-process skill inputs               |
| Skill utils         | `agent/skill_utils.py`         | Skill utility functions                |
| Index cache         | `skills/index-cache/`          | Cached skill indexes from marketplaces |

**Built-in Skill Categories**:

| Category                         | Description               |
| -------------------------------- | ------------------------- |
| `skills/apple/`                | Apple ecosystem skills    |
| `skills/autonomous-ai-agents/` | Autonomous agent patterns |
| `skills/creative/`             | Creative/design skills    |
| `skills/data-science/`         | Data science + ML         |
| `skills/dogfood/`              | Internal dogfooding skill |
| `skills/email/`                | Email automation          |
| `skills/github/`               | GitHub workflow skills    |
| `skills/media/`                | Media processing          |
| `skills/mlops/`                | MLOps skills              |
| `skills/note-taking/`          | Note-taking integration   |
| `skills/productivity/`         | Productivity tools        |
| `skills/research/`             | Research skills           |
| `skills/smart-home/`           | Smart home control        |
| `skills/social-media/`         | Social media automation   |
| `skills/yuanbao/`              | Yuanbao integration       |

**Marketplace Indexes**:

- `skills/index-cache/anthropics_skills_skills_.json`
- `skills/index-cache/claude_marketplace_anthropics_skills.json`
- `skills/index-cache/lobehub_index.json`
- `skills/index-cache/openai_skills_skills_.json`

## 2.6 Subagent Delegation

| Feature           | File                            | Description                        |
| ----------------- | ------------------------------- | ---------------------------------- |
| Subagent spawning | `agent/agent_init.py`         | Spawn isolated subagents           |
| RPC subagent      | `agent/codex_runtime.py`      | RPC-based subagent execution       |
| ACP client        | `agent/copilot_acp_client.py` | ACP protocol client                |
| Process bootstrap | `agent/process_bootstrap.py`  | Subprocess bootstrap for subagents |

## 2.7 Scheduler / Cron (`agent/`)

| Feature                 | File                    | Description                                   |
| ----------------------- | ----------------------- | --------------------------------------------- |
| Cron scheduling         | (built into`cli.py`)  | Natural language cron scheduling              |
| Scheduled automations   | (built into`cli.py`)  | Daily reports, nightly backups, weekly audits |
| Multi-platform delivery | `gateway/delivery.py` | Deliver to any connected platform             |

## 2.8 Terminal Backends (`agent/`)

| Backend     | Description                                       |
| ----------- | ------------------------------------------------- |
| Local       | Run on local machine                              |
| Docker      | Run inside Docker container                       |
| SSH         | Run on remote SSH server                          |
| Singularity | Run via Singularity containers                    |
| Modal       | Serverless cloud execution (hibernates when idle) |
| Daytona     | Serverless VM (hibernates when idle)              |

## 2.9 ACP Adapter (`acp_adapter/`)

| Feature       | File                 | Description                         |
| ------------- | -------------------- | ----------------------------------- |
| ACP server    | `server.py`        | Agent Communication Protocol server |
| ACP session   | `session.py`       | Session management for ACP          |
| Auth          | `auth.py`          | ACP authentication                  |
| Edit approval | `edit_approval.py` | Approval workflow for edits         |
| Entry point   | `entry.py`         | ACP adapter entry point             |
| Events        | `events.py`        | ACP event streaming                 |
| Permissions   | `permissions.py`   | Permission management               |
| Provenance    | `provenance.py`    | Action provenance tracking          |
| Tools         | `tools.py`         | ACP tool exposure                   |
| Main          | `__main__.py`      | ACP adapter CLI                     |

## 2.10 CLI (`cli.py` — 650,647 bytes)

| Command                     | Description                    |
| --------------------------- | ------------------------------ |
| `hermes`                  | Main entry point               |
| `hermes model`            | Switch provider/model          |
| `hermes gateway`          | Gateway management subcommands |
| `hermes gateway run`      | Start gateway daemon           |
| `hermes install`          | Installation commands          |
| `hermes update`           | Self-update                    |
| `hermes doctor`           | Diagnostics                    |
| (All 13+ keyboard handlers) | TUI keybindings                |

**Built-in Shell Features**:

- `handle_enter` — Submit message
- `handle_alt_enter` — Newline without submit
- `handle_ctrl_enter_newline` — Ctrl+Enter = newline
- `handle_open_in_editor` — Edit in $EDITOR
- `handle_tab` — Tab completion
- `handle_ctrl_l` — Clear screen
- `handle_ctrl_c` — Cancel/interrupt
- `handle_ctrl_q` — Quit
- `handle_ctrl_d` — EOF/exit
- `handle_escape_modal` — Escape modal dialogs
- `handle_ctrl_z` — Suspend
- `handle_voice_record` — Voice recording
- `handle_paste` — Paste text
- `handle_ctrl_v` — Verbose paste
- `handle_alt_v` — Alternative paste

## 2.11 Memory & User Modeling

| Feature             | File                                    | Description                      |
| ------------------- | --------------------------------------- | -------------------------------- |
| Memory manager      | `agent/memory_manager.py`             | Long-term memory orchestration   |
| Memory provider     | `agent/memory_provider.py`            | Memory backend abstraction       |
| Honcho integration  | (via plugins)                           | Dialectic user modeling          |
| FTS5 session search | (sqlite via`agent/memory_manager.py`) | Full-text search across sessions |
| LLM summarization   | `agent/background_review.py`          | Cross-session recall via LLM     |

## 2.12 Model Providers

| Provider           | File                                  | Description               |
| ------------------ | ------------------------------------- | ------------------------- |
| OpenAI             | (via generic adapter)                 | OpenAI chat completions   |
| Anthropic          | `agent/anthropic_adapter.py`        | Claude-specific adapter   |
| Google Gemini      | `agent/gemini_native_adapter.py`    | Gemini native API         |
| Google Cloud Code  | `agent/gemini_cloudcode_adapter.py` | Cloud Code adapter        |
| Google Code Assist | `agent/google_code_assist.py`       | Code Assist integration   |
| AWS Bedrock        | `agent/bedrock_adapter.py`          | Bedrock API adapter       |
| Azure              | `agent/azure_identity_adapter.py`   | Azure identity + API      |
| Codex              | `agent/codex_responses_adapter.py`  | OpenAI Codex adapter      |
| Moonshot           | `agent/moonshot_schema.py`          | Moonshot/Kimi API         |
| LM Studio          | `agent/lmstudio_reasoning.py`       | Local LM Studio           |
| Plugin LLM         | `agent/plugin_llm.py`               | Plugin-based provider     |
| Model metadata     | `agent/model_metadata.py`           | Model capability metadata |
| Model dev          | `agent/models_dev.py`               | Development model configs |

## 2.13 Additional Agent Capabilities

| Feature                    | File                                    | Description                  |
| -------------------------- | --------------------------------------- | ---------------------------- |
| Tool executor              | `agent/tool_executor.py`              | Execute tool calls safely    |
| Tool dispatch helpers      | `agent/tool_dispatch_helpers.py`      | Tool routing                 |
| Tool guardrails            | `agent/tool_guardrails.py`            | Safety guardrails for tools  |
| Tool result classification | `agent/tool_result_classification.py` | Classify tool output         |
| File safety                | `agent/file_safety.py`                | Safe file operations         |
| Redaction                  | `agent/redact.py`                     | Sensitive data redaction     |
| Error classifier           | `agent/error_classifier.py`           | Classify and handle errors   |
| Think scrubber             | `agent/think_scrubber.py`             | Clean thinking tokens        |
| Trajectory                 | `agent/trajectory.py`                 | Session trajectory recording |
| Message sanitization       | `agent/message_sanitization.py`       | Sanitize messages            |
| Auxiliary client           | `agent/auxiliary_client.py`           | Secondary LLM client         |

---

# 3. OpenHuman (TinyHumansAI)

**Stack**: Rust (2021, tokio async) + Tauri v2 desktop + React/TypeScript frontend
**Size**: ~4,725 source files | ~100 Rust modules under `src/openhuman/`
**Version**: 0.57.39

## 3.1 Agent Engine

**Unified Turn Engine** (`engine/core.rs`): 5 pluggable seams (ToolSource, ProgressReporter, TurnObserver, CheckpointStrategy, ResponseParser). 3 ToolDispatchers: Native (structured), Xml (`<tool_call>`), PFormat (compact).

**Subsystems**: fork_context, memory_context, sandbox_context, worktree_context, spawn_depth_context, payload_summarizer, self_healing (ToolMaker polyfill, circuit breakers), tool_filter, token_budget

## 3.2 Multi-Provider LLM Routing

**Providers**: OpenHumanBackend (JWT), OpenAiCompatible (BYOK), ClaudeAgentSdk (subprocess), IntelligentRouting (local+cloud fallback), RouterProvider (hint-based)

**Routing**: classify()→TaskCategory, cached health probes (30s TTL), Aho-Corasick DFA refusal detection

## 3.3 Memory (10+ modules)

memory_store (SQLite), memory_tree (bucket-seal cascade), memory_archivist (Chat→tree), memory_entities, memory_graph, memory_conversations (JSONL), memory_search, memory_sync, memory_queue, memory_diff, memory_tools

## 3.4 MCP (4 modules)

mcp_client (HTTP+stdio, protocol 2024-2025), mcp_server (Axum HTTP+SSE), mcp_registry (dynamic install, Smithery.ai, 60s reconnect), mcp_audit

## 3.5 Subagents

3-Tier: chat→reasoning→worker, MAX_SPAWN_DEPTH=3. 15 built-in archetypes (orchestrator, planner, researcher, code_executor, critic, summarizer, etc.)

## 3.6 Learning

Post-turn hooks: ArchivistHook, ReflectionHook, ToolTrackerHook, UserProfileHook. Ambient profile facets, stability detector (30min), PROFILE.md injection

## 3.7 Security

Autonomy tiers (readonly/supervised/full), sandboxes (bubblewrap, docker, firejail, landlock), approval gate (10-min TTL), policy engine (command classification, path checks)

## 3.8 Context

Layered pipeline, guard (0.90/0.95), microcompact, summarizer, 16 KiB tool result budget

## 3.9 Config (~70 schema files)

agent, autonomy, channels, cloud_providers, context, dashboard, dictation, heartbeat, learning, local_ai, MCP, observability, proxy, routes, runtime, sandbox, scheduler, search, tools (browser, HTTP, integrations, MCP, multimodal, search), update, voice

## 3.10 Remaining ~80 Modules

app_state, billing, channels, cron, dashboard, doctor, embeddings, health, heartbeat, http_host, integrations (Composio, webhooks), notifications, search, service, session_db, skill_registry, skill_runtime, socket, startup, subconscious, task_sources, tools, tool_registry, tool_timeout, voice, webhooks, workflows, workspace, accessibility, autocomplete, text_input, devices, connectivity, desktop_companion, encryption, keyring, tls, codegraph, javascript, runtime_node, runtime_python, council_registry, model_council, cwd_jail, file_state, image, prompt_injection, referral, team, people, x402, wallet, tokenjuice, cost, web3, meet, meet_agent, agent_meetings, agent_experience, agent_memory, agent_tool_policy, overlay, screen_intelligence, update, migration, migrations, provider_surfaces, redirect_links, scheduler_gate, sandbox, about_app, test_support

---

# 4. Locus OS

**Stack**: Python 3.10+ | ~100 .py files | SETTINGS.md (56KB, 28 sections)

## 4.1 CLI

| Command                                                                      | Description       |
| ---------------------------------------------------------------------------- | ----------------- |
| `locus setup`                                                              | Full setup wizard |
| `locus setup gateway`                                                      | Messaging setup   |
| `locus config show/set/path/env-path/check/migrate`                        | Config management |
| `locus gateway run/start/stop/restart/status/install/uninstall/list/setup` | Gateway lifecycle |
| `locus version`                                                            | Print version     |

**Setup Categories**: agent_settings, channels, integrations, llm_providers, memory, observability, proxy, scheduling, security, tools_search, voice

**Extra**: TUI mode (curses_ui.py), colors.py, cli_output.py, secret_prompt.py, slash_commands.py

## 4.2 Core Agent Engine

`core/agent.py`: Message/ToolDef/ToolResult dataclasses, ToolRegistry, LlmProvider (OpenAI-compatible HTTP), resolve_provider()

**Tools** (`core/tools.py`): read, write, edit, edit_file, run_shell (sandboxed), web_search, web_fetch, system_info, list_directory, git_status, git_diff, git_commit

## 4.3 Gateway

Telegram bot (PTB long-polling, auth allowlist, slash command handlers), agent dispatcher, platform registry, status/health

## 4.4 Memory

**Backends**: SQLite (WAL, conversations/documents/sessions tables), Neo4j (graph), Holographic HRR (SHA-256 deterministic vectors, bind/unbind/bundle/similarity)

**Orchestration**: memory_manager.py, session_manager.py, approval_store.py

## 4.5 Channels (13)

Telegram, Discord, Slack, Signal, WhatsApp, IRC, Matrix, Mattermost, Teams, Lark, DingTalk, Google Chat, Email, iMessage

## 4.6 Voice

**STT**: Whisper (local), Azure STT, Groq STT, OpenAI STT
**TTS**: Edge TTS, ElevenLabs, OpenAI TTS, Piper (local)
**Dictation**: dictation.py

## 4.7 Search (5 providers)

Brave, Exa, Firecrawl, SearXNG, Tavily

## 4.8 Browser

Playwright automation (browserbase.py, playwright_backend.py), screenshot.py

## 4.9 Screen

Capture (capture.py), vision (vision.py)

## 4.10 Computer Use

Native (native.py), VNC (vnc.py)

## 4.11 Context

Token counter (token_counter.py), compression (compression.py), compactor (compactor.py)

## 4.12 Display

Progress (progress.py), streaming TUI (streaming_tui.py), themes (themes.py)

## 4.13 Learning

Reflector (reflector.py — LLM post-session reflection), tool tracker (tool_tracker.py), user profile (user_profile.py)

## 4.14 Heartbeat

Notification (notification.py), subconscious background (subconscious.py)

## 4.15 Delegation

Subagent (delegation/subagent.py), coding agent (delegation/coding_agent.py)

## 4.16 Integrations (3)

Composio (composio.py), Polymarket (polymarket.py), Webhooks (webhooks.py)

## 4.17 MCP Client

mcp_client.py — MCP protocol client

## 4.18 Cron/Scheduler

cron_runner.py, scheduler/task_sources.py

## 4.19 Security

Sandbox (shell_exec.py blocklists), approval_store.py, proxy.py

## 4.20 Coding Subsystem

file_ops.py, git_ops.py, shell_exec.py (BLOCKED_PATTERNS, configurable sandbox)

## 4.21 Config (SETTINGS.md — 56KB, 28 sections)

All 28 sections: Core Identity, LLM Providers, Local AI, Agent Behaviour, Memory, Channels, Web Search, Browser, Voice, Terminal, MCP, Security, Cost, Cron, Heartbeat, Integrations, Proxy, Observability, Context, Skills, Subagent, Display, Sessions, Updates, Runtimes, OpenHuman Overrides, Hermes Settings, Env Var Index

## 4.22 Life OS Core — Behavioral Metrics & Life Domains

> **Source**: `LOCUS_SYSTEM_v1.md`, `LOCUS_MASTER_DOCUMENT.md`, `locus_features_decomposed.md`, design documents in `.keysndocs/Documentation/Ideas and System/`
>
> These features are **not present in any of the three reference codebases** (Pi, Hermes, OpenHuman). They make Locus a Personal Cognitive Operating System rather than a general coding agent.

| #  | Feature                                     | Description                                                                                                                                                                            |
| -- | ------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1  | **Four Factions Framework**           | Life-domain model: Health/Stability (🟢), Leverage/Money (🔵), Craft/Skills (🟠), Expression/Exploration (🟣). Weekly hour targets (~17.5/17.5/21/14h). Crisis hierarchy. Color-codes. |
| 2  | **Daily Capacity Score (DCS)**        | `((E+M+S)/3) × (1−ST/20)` — computed metric from Energy, Mood, Sleep, Stress. GENERATED ALWAYS AS column.                                                                         |
| 3  | **Five Operating Modes**              | DCS → SURVIVAL / RECOVERY / NORMAL / DEEP_WORK / PEAK. Each mode gates task difficulty ceiling and expected output.                                                                   |
| 4  | **Task Weight Score (TWS)**           | `(P×0.4)+(U×0.4)+(D×0.2)` — Priority, Urgency, Difficulty mapped to a single sorting key. Computed column.                                                                       |
| 5  | **Three-Layer Goal Stack**            | Outcomes (WHY, max 7) → Projects (WHAT, max 3 active/faction) → Tasks (HOW). Max-cap enforcement, dead node detection, hierarchy traversal.                                          |
| 6  | **Action Gap Tracking**               | AG = declared_priority − (actual_hrs / target_hrs × 10). AG > 5 → behavioral honesty alert.                                                                                         |
| 7  | **Deferral Detection (3/5/8+ rule)**  | Progressive alerts: 3× → flag, 5× → Telegram alert, 8+ → escalate to Inner Loop. Tracks reasons for deferral.                                                                     |
| 8  | **Lag Score + TWS Lag Bonus**         | Lagging faction (>3h behind) gets TWS +2; crisis (>6h) gets TWS +4. Ahead faction gets TWS −1. Scheduling-level rebalancing.                                                          |
| 9  | **Emergency Task Injection Protocol** | New urgent task → compute TWS → compare to scheduled → replace if higher → deferred task gets U+2.`is_locked` flag for non-negotiables.                                          |
| 10 | **Exhaustion Predictor**              | IF avg_task_difficulty(5d) > 7 AND avg_DCS(5d) < 5 → reduce next-day load 30%.                                                                                                        |
| 11 | **Weekly Faction Rebalance**          | Starving faction gets automatic priority boost for the coming week.                                                                                                                    |
| 12 | **Cross-Faction Efficiency**          | Tasks serving multiple factions get TWS +1 per extra faction. Time splits proportionally. "3-birds-1-stone" principle.                                                                 |
| 13 | **Review Cadence System**             | Daily (7min) → Weekly (30-45min) → Monthly (60min) → Quarterly (2-3hrs). Each with AI-generated content and structured templates.                                                   |
| 14 | **Goal Stack Enforcement**            | Max 7 outcomes, max 3 active projects per faction, dead node detection at 60 days, stalled project detection (CR < 20% at age > 30 days).                                              |

**Scheduling Algorithm**: 6-step decision tree: non-negotiables → DCS filter → lag bonus → sort by TWS → faction balance check → time block assignment.

**Emergency Protocol**: 4-level disruption classification, golden rule of 2-week recovery.

## 4.23 Brain Engine — Proactive Reasoning ("Samantha Layer")

> Features that model, think about, and infer about the user **without being asked**.

| #  | Feature                                          | Description                                                                                                                                                                                                                                                                                       |
| -- | ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 15 | **Inner Loop (Proactive Thinker)**         | APScheduler every 90 min (07:00-00:00). Prompt: "You are NOT talking to the user. You are thinking about the user." Generates 0-2 unprompted observations. Deduplicates against last 6h. Scores via Reward Model (≥ 0.6). Routes: HIGH → Telegram now, MEDIUM → morning brief, LOW → discard. |
| 16 | **State Engine with Inferred Cause Chain** | CURRENT_STATE includes: psychological_state (mood_trend, energy_trend), operational_state (momentum, deferral_rate_7d, last_meaningful_work), contextual_flags (exam_period), alerts. Plus a cause chain — DeepSeek generates "why you're in this state" citing specific historical data.        |
| 17 | **Multi-Horizon Pattern Engine**           | 5 time horizons: H1 (6h acute), H2 (24h daily rhythm), H3 (7d faction neglect), H4 (30d via SQL+DeepSeek), H5 (all-time via DeepSeek). Patterns promoted to PERSISTENT when confidence > 0.75 AND count > 2. Auto-updates user identity.                                                          |
| 18 | **User Identity Profile**                  | Single-row PG table. Never hard-overwritten — rolling average updates. Tracks: behavioral tendencies (with confidence floats), peak windows, stressors, energizers, communication style, exam behavioral signature.                                                                              |
| 19 | **Personal Reward Model**                  | sklearn LogisticRegression trained on 👍/👎 from every response. Weekly retrain. Used as gate for Inner Loop (predicted ≥ 0.6 to surface). Weights stored in PG bytea.                                                                                                                           |
| 20 | **Hebbian Pathway Weighting + STDP**       | Neo4j edge weights: traversal +0.1. 👍 → ×1.3. 👎 → ×0.7. Weekly decay ×0.95. STDP (Spike-Timing Dependent Plasticity): response latency < 2 min = ×1.5 reinforcement. Project completion → connected edges × 0.5. Biological learning rule applied to an agent.                          |
| 21 | **Inferred Cause Chain Engine**            | Dedicated engine that cross-references CURRENT_STATE + PERSISTENT patterns + historical events + calendar + User Identity → plain English causal explanation with confidence scores and data source tracking.                                                                                    |
| 22 | **Personality + "Wants" Engine**           | SOUL.md defines rules: "never flatter, never say 'great question', cite data, push back when evidence conflicts." Operational preferences surfaced without being asked — WantNodes in Neo4j with confidence + evidence.                                                                          |
| 23 | **Context Forge (800-Token Assembler)**    | 6 hard-budget layers: user_identity (80t), temporal (60t), pg_events (180t via SHORTHAND), neo4j_pathways (150t), pgvector_semantic (200t), web (100t). Truncation by relevance score not recency. Anti-hallucination guard: if ALL empty → explicit signal to LLM.                              |
| 24 | **Query Router / Intent Classifier**       | 8 intent types: FACTUAL_PERSONAL, BEHAVIORAL_PATTERN, KNOWLEDGE_RETRIEVAL, TASK_PLANNING, EMOTIONAL_STATE, EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST, COMMAND. Source routing matrix. Confidence < 0.7 → query ALL sources.                                                               |
| 25 | **Spaced Repetition Memory Reinforcement** | Nodes approaching decay threshold AND connected to active outcomes → Inner Loop surfaces as deliberate reminders. Engagement = reinforcement. No engagement = natural decay.                                                                                                                     |
| 26 | **Project-Specific Memory Decay**          | Completed/inactive project → Cypher:`SET r.weight = r.weight * 0.5`. Combined with weekly global decay.                                                                                                                                                                                        |
| 27 | **Self-Evolving + Architect Bot**          | Scans reward_signals for underperforming components. Generates code patches with tests. LOW risk → auto-deploy. HIGH risk → Telegram approval.                                                                                                                                                  |

## 4.24 Data Philosophy — Personal Vault as Brain

| #  | Feature                                    | Description                                                                                                                                                                                                                                                  |
| -- | ------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 28 | **PageIndex + Direct Retrieval**     | Whole-note embedding (200-800 words) combined with direct pgvector + Neo4j queries. No middleware (LightRAG removed). Short notes embed whole, long AI chats chunk at sentence boundaries.                                                                   |
| 29 | **Nightly Vault Ingestion Pipeline** | Multi-account Playwright scraping of ChatGPT (×3 accounts), Claude, Gemini, Perplexity. Each chat gets unique ID → tagged .md with YAML → embedding → DeepSeek entity extraction → Neo4j.                                                               |
| 30 | **Weekly Full Vault Synthesis**      | Sunday 02:00 — behavioral_events (7d) + faction_weekly_stats + detected_patterns + CURRENT_STATE + top 10 Hebbian pathways → DeepSeek generates personality drift report, faction narrative, top 3 observations.                                           |
| 31 | **LOCUS_SHORTHAND**                  | `{e:N,t:HHMM,f:FACTION}` / `{✓:NAME,dur:MINS,q:QUALITY}` / `{→:NAME,n:COUNT,r:REASON}` — ~4× token compression with zero information loss. Dedicated encode/decode functions.                                                                      |
| 32 | **Obsidian as Primary Dashboard**    | Backend pushes stats JSON → Dataview/Charts render. 8 panels: Today's Schedule, Faction Health, Active Patterns, Goal Stack, Hebbian Pathways, Brain Observations, DCS Trend, Morning Briefing. No separate web app — PWA explicitly removed and replaced. |
| 33 | **Obsidian MCP**                     | vault_read, vault_write (append-only), vault_search (grep + pgvector), vault_tag, vault_stats. Localhost only, .md only, path traversal blocked.                                                                                                             |
| 34 | **3-Level Tag Hierarchy**            | faction/domain/specific enforced on every vault file. Tag registry in PG with auto-suggestion.                                                                                                                                                               |
| 35 | **Rough Note Parser / Idea Tracker** | Telegram /idea →`captures` table → DeepSeek expansion + web research → [Promote to Task] [Research] [Archive] flow.                                                                                                                                     |
| 36 | **Link Dump / Resource Logger**      | Telegram /link → captures table (type='link', url, tags) → vault note.                                                                                                                                                                                     |
| 37 | **Daily AI Chat Archiver**           | Nightly 23:45 — ALL Telegram messages exported to /vault/03-AI-Chats/telegram/YYYY-MM-DD.md → git commit + push.                                                                                                                                           |
| 38 | **Excalidraw MCP Skill**             | Autonomous Excalidraw diagram generation via MCP tools, integrated into vault context.                                                                                                                                                                       |

## 4.25 Interface Philosophy — Deliberate Non-Builds

| #  | Feature                                                | Description                                                                                                                                                                                                                                                                       |
| -- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 39 | **No TUI (explicitly rejected)**                 | "A TUI is a third interface that does a worse version of both Telegram and Obsidian. Desktop-only, can't receive proactive messages, adds maintenance surface. Don't build it." Pi and Hermes both have elaborate TUIs — Locus's absence of one is a design decision, not a gap. |
| 40 | **Telegram as Primary Conversational Interface** | Not as a gateway/platform — as the**primary** interface with /commands and structured inline keyboards. Hermes has a Telegram gateway adapter; Locus is Telegram-native.                                                                                                   |
| 41 | **4 Daily Structured Check-ins**                 | Morning/Afternoon/Evening/Night with inline keyboard taps. DCS auto-computed. Evening includes AI 3-sentence summary. Data pushed to vault JSON.                                                                                                                                  |
| 42 | **Voice Call Interface**                         | Audio → Groq Whisper STT → full pipeline → Kokoro TTS. Post-call transcript to vault. Not a voice gateway — a voice interaction modality for the life OS.                                                                                                                     |
| 43 | **Structured Check-in Reminders**                | APScheduler 07:30/13:00/18:00/22:00 IST → Telegram inline keyboard. No VAPID/web push needed — Telegram IS the push channel.                                                                                                                                                    |
| 44 | **Obsidian Dashboard replaces PWA**              | Hermes has its own dashboard (port 9119). Pi has its TUI. Locus uses Obsidian. PWA explicitly removed from architecture.                                                                                                                                                          |

## 4.26 Infrastructure Decisions — Deeper Philosophy

| #  | Feature                                                                                                                                                                                   | Description                                                                                                                                                                        |
| -- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 45 | **Git for vault sync (replacing Syncthing)**                                                                                                                                        | Directory partitioning (backend writes to 00/03/06/07, user writes to 01/02/04/05) prevents merge conflicts. Version history free. No extra service.                               |
| 46 | **Manual Google OAuth (replacing Composio)**                                                                                                                                        | "50 lines of code. No external dependency. Full control."                                                                                                                          |
| 47 | **pgvector replaces Qdrant + ChromaDB**                                                                                                                                             | <50K vectors → one fewer container. Three containers total (PG, Neo4j, Redis optional).                                                                                           |
| 48 | **Redis optional**                                                                                                                                                                  | "At single-user scale, PG + in-memory dict covers all Redis use cases."                                                                                                            |
| 49 | **DeepSeek V4 Flash only (~$0.012/day)** | No multi-provider cascade. One model, one behavior, ~$4/year. Not a limitation — an architectural decision shaping every design choice. |                                                                                                                                                                                    |
| 50 | **Minimum AI in Every Harness Layer**                                                                                                                                               | Everywhere deterministic logic works, use it. LLM only for: classification, reasoning, generation, synthesis. Not for control flow, not for data routing, not for scheduling math. |
| 51 | **Zero-cost constraint as 1st-class requirement**                                                                                                                                   | $5 credit lasts ~416 days. Not a limitation — an architectural decision.                                                                                                          |

## 4.27 Headless Setup Wizard (Designed, In-Chat)

Since Locus is headless, the full post-bot-token setup happens inside the messaging app via conversation flow:

```
/setup
  ├── /setup provider     → DeepSeek/Groq/OpenRouter API key capture + test
  ├── /setup db            → PostgreSQL/Neo4j/pgvector health check, migration, reset
  ├── /setup vault         → GitHub repo link, directory structure, PageIndex indexing
  ├── /setup skills        → Skill registry download, default install, sync
  ├── /setup integration   → Google/Calendar/Gmail/Calendly OAuth device-code flow
  ├── /setup cron          → Check-in times, review cadence, night crawl schedule
  ├── /setup personality   → SOUL.md calibration conversation (tone, pushback threshold)
  ├── /setup subconscious  → Inner Loop frequency, depth pass configuration
  ├── /setup voice         → STT/TTS provider selection
  ├── /setup notifications → Alert preferences, quiet hours
  ├── /setup import        → Telegram IDB scan, existing vault import
  └── /setup credentials   → Encrypted API key management
```

## 4.28 Sub-Agent Architecture (Designed)

4 faction-specific sub-agents planned:

- **Faction Planner** — schedules tasks by faction balance
- **Vault Curator** — manages vault ingestion, tagging, synthesis
- **Brain Analyst** — runs pattern detection, Hebbian analysis
- **Schedule Builder** — DCS-aware daily schedule construction

Plus optional Pi-style sub-agents via subprocess (Scout, Researcher, Worker) for coding tasks.

## 4.29 Architectural Position: Why Not Build on Pi

Explicitly decided against building Locus on Pi Agent framework:

1. **Language mismatch** — Locus's differentiating stack is Python (FastAPI, sklearn, Neo4j driver, APScheduler, fastembed, spaCy). Pi is TypeScript. Every call crosses a serialization boundary.
2. **Architectural mismatch** — Pi is turn-based (user speaks → agent responds). Locus is always-on (Inner Loop fires every 90 min without user input).
3. **TUI irrelevance** — Pi's most sophisticated component is its TUI. Locus explicitly rejected TUI.
4. **Extension system limitations** — Pi extensions can't own databases, run background cron, or train ML models.
5. **Borrow, don't couple** — Provider routing, session tree, skill format, compaction prompts borrowed as Python reimplementations. Pi-subagents installable as standalone tool via subprocess.

---

# 5. Cross-Codebase Comparison Matrix

| Feature Area                  | Pi                                             | Hermes Agent                                                               | OpenHuman                                                      | Locus OS                                                                                                                         |
| ----------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------- | -------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Language**            | TypeScript (Node)                              | Python 3.11-3.13                                                           | Rust (tokio async)                                             | Python 3.10+                                                                                                                     |
| **Source files**        | ~844                                           | ~5,048                                                                     | ~4,725                                                         | ~100                                                                                                                             |
| **Agent loop**          | Two-entry (tooled+simple)                      | Conversation loop + background review                                      | Unified engine, 5 seams, 3 dispatchers                         | ToolRegistry + LlmProvider + Context Forge + Query Router + Inner Loop                                                           |
| **TUI**                 | Full TUI (keybindings, themes, modes)          | CLI.py (650K, 15+ keyboard handlers)                                       | Tauri desktop + web (React/TS)                                 | None (deliberately rejected — Telegram-native headless)                                                                         |
| **CLI flags**           | 30+ flags                                      | 13+ keyboard handlers                                                      | JSON-RPC + CLI                                                 | 18 CLI commands                                                                                                                  |
| **Providers**           | 10+ (OpenAI, Anthropic, Google, Bedrock, etc.) | 15+ (OpenAI, Anthropic, Gemini, Bedrock, Codex, Moonshot, LM Studio, etc.) | 5 (Backend, BYOK, Claude SDK, Intelligent, Router)             | 1 (DeepSeek V4 Flash — intentional single-provider, ~$4/year)                                                                   |
| **Tool count**          | 8 built-in tools                               | 90+ agent modules                                                          | ~80 tool modules                                               | 12 built-in tools                                                                                                                |
| **Memory**              | JSONL + in-memory                              | FTS5 + Honcho + SQLite                                                     | 10+ modules (bucket-seal tree, graph, entities, SQLite)        | SQLite + Neo4j (Hebbian/STDP) + HRR + pgvector + PG (behavioral events)                                                          |
| **Session**             | Tree-based JSONL persistence + compaction      | SQLite sessions + compression                                              | JSONL + bucket-seal cascade                                    | SQLite (conversations, sessions, documents)                                                                                      |
| **Subagents**           | Builtin subagent tool                          | spawn_subagent + RPC                                                       | 3-tier hierarchy, 15 archetypes                                | 4 faction sub-agents (Planner, Curator, Analyst, Builder) + optional Pi subprocess                                               |
| **Learning**            | Skills + prompt templates                      | Curator + insights + memory nudge + session search                         | Post-turn hooks + ambient profile facets + stability detector  | Hebbian+STDP weights, Personal Reward Model (sklearn), 5-horizon Pattern Engine, Architect Bot, Reflector, User Identity Profile |
| **Channels**            | CLI/TUI only                                   | Telegram, Discord, Slack, WhatsApp, Signal + CLI + Electron desktop        | Tauri desktop, web, CLI, MCP                                   | 13 channels (Telegram primary, Discord, Slack, Signal, IRC, Matrix, etc.)                                                        |
| **MCP**                 | Extensions system                              | Plugin system (ACP)                                                        | Full client + server + registry                                | Basic MCP client + Obsidian MCP                                                                                                  |
| **Voice**               | —                                             | STT + TTS (via plugins)                                                    | Voice inference module                                         | STT: 4 backends, TTS: 4 backends, Voice Call Interface                                                                           |
| **Search**              | —                                             | Web search (via plugins)                                                   | Web search tools                                               | 5 providers (Brave, Exa, Firecrawl, SearXNG, Tavily)                                                                             |
| **Browser**             | —                                             | Browser provider                                                           | Screen intelligence                                            | Playwright automation + screenshot + vision                                                                                      |
| **Security**            | Project trust                                  | File safety + redaction + guardrails                                       | Autonomy tiers + sandboxes (4) + approval gate + policy engine | Shell blocklists + approval_store + proxy                                                                                        |
| **Scheduler**           | —                                             | Cron (natural language)                                                    | Cron module                                                    | cron_runner + task_sources + Inner Loop (90min) + 4× daily check-ins                                                            |
| **CICD**                | GitHub Actions CI                              | Full CI (lint, test, typecheck, docker, nix, security)                     | Full CI (build, test, deploy, e2e, smoke)                      | None visible                                                                                                                     |
| **Extensions**          | Extensions system (loader, runner, wrapper)    | ACP adapter + skills marketplace                                           | MCP registry + skill_registry                                  | —                                                                                                                               |
| **Export**              | HTML, JSON, MD session export                  | Trajectory recording                                                       | —                                                             | —                                                                                                                               |
| **Computer use**        | —                                             | —                                                                         | Desktop companion + overlay + screen_intelligence              | Native + VNC                                                                                                                     |
| **Config size**         | YAML/JSON config                               | cli-config.yaml.example                                                    | ~70 schema files                                               | SETTINGS.md (56KB, 28 sections)                                                                                                  |
| **Life OS metrics**     | —                                             | —                                                                         | —                                                             | DCS, TWS, Factions, Goal Stack, Action Gap, Lag Score, Deferral Detection, Exhaustion Predictor (14 features)                    |
| **Proactive reasoning** | —                                             | —                                                                         | —                                                             | Inner Loop, State Engine, Pattern Engine (5 horizons), Inferred Cause Chain, Reward Model, Architect Bot (13 features)           |
| **User modeling**       | —                                             | Honcho dialectic                                                           | Ambient profile facets                                         | User Identity Profile (PG), Hebbian+STDP weighting, Personal Reward Model, SOUL.md personality rules                             |
| **Vault intelligence**  | —                                             | —                                                                         | —                                                             | PageIndex, Nightly multi-account ingestion, Weekly Vault Synthesis, LOCUS_SHORTHAND, Obsidian Dashboard, Chat Archiver           |
| **Primary interface**   | TUI (terminal)                                 | TUI + Telegram/Discord/Slack gateway                                       | Tauri desktop + web                                            | Telegram (headless-first, no TUI by design)                                                                                      |

# 6. Feature Overlap Analysis

## Features in ALL 4 systems

- Agent conversation loop
- Multi-provider LLM support
- Tool execution framework
- Session persistence
- Subagent/spawn delegation

## Features in Pi + Hermes + OpenHuman but NOT in Locus

- Full TUI with keybindings and themes
- Rich provider ecosystem (10+ providers)
- MCP full client-server-registry (Locus has basic MCP only)
- Compaction/context management (Locus has token counter only)
- Skills system with marketplace support
- Built-in testing/CI infrastructure

## Features in Hermes + OpenHuman but NOT in Pi or Locus

- Multi-platform messaging gateway (Telegram, Discord, Slack, etc.)
- Voice STT/TTS
- Web search providers
- Browser automation
- Cron/scheduling
- Security sandboxing (autonomy tiers, approval gates)
- Learning/reflection loop
- Computer use (screen control, VNC)
- Background/heartbeat processing

## Features unique to Pi

- HTML/JSON/MD session export
- Extensions system (loader/runner/wrapper)
- 30+ CLI flags with granular control
- RPC mode for IDE integration
- Session compaction + branch summarization
- Theme system

## Features unique to Hermes Agent

- Curator-based learning loop with FTS5 session search
- Honcho dialectic user modeling
- Skills marketplace indexes (Anthropic, Claude, LobeHub, OpenAI)
- 6 terminal backends (local, Docker, SSH, Singularity, Modal, Daytona)
- ACP protocol adapter with edit approval + provenance
- Voice recording inline in TUI
- Batch trajectory runner (1321 lines)
- Image/video generation provider
- Electron desktop app with 38+ modules

## Features unique to OpenHuman

- Intelligent LLM routing with health probes + quality gate (Aho-Corasick DFA)
- Bucket-seal memory tree cascade
- 5 pluggable engine seams + 3 tool dispatchers
- Ambient profile facets with stability detector
- 15 built-in subagent archetypes with strict 3-tier enforcement
- ~80 domain modules (billing, wallet, web3, model council, meet, etc.)
- MCP registry with dynamic install from Smithery.ai
- Tauri v2 desktop + web + CLI tri-modal interface

## Features unique to Locus OS

### Infrastructure-level (code exists)

- Holographic Reduced Representations (HRR) for concept binding
- 13 messaging channels (most of any system)
- 5 search providers
- 4 STT + 4 TTS voice backends
- Computer use (Native + VNC)
- Locus-specific SETTINGS.md (28-section master config)
- Secret_prompt.py (prompt encryption)
- Neo4j graph memory + SQLite + HRR triple memory backend
- Deployment module (SSH-based remote deploy)

### Life OS layer (14 features — no equivalent in any reference codebase)

- Four Factions Framework (Health/Leverage/Craft/Expression with weekly hour targets)
- Daily Capacity Score (DCS) — computed human capacity metric
- Five Operating Modes (SURVIVAL → PEAK) gating task difficulty
- Task Weight Score (TWS) — computed priority sorting key
- Three-Layer Goal Stack (Outcomes → Projects → Tasks, max caps)
- Action Gap Tracking (behavioral honesty metric)
- Deferral Detection (3/5/8+ progressive alerts)
- Lag Score + TWS Lag Bonus (faction rebalancing at scheduling level)
- Emergency Task Injection Protocol
- Exhaustion Predictor (5-day difficulty vs DCS)
- Weekly Faction Rebalance
- Cross-Faction Efficiency ("3-birds-1-stone")
- Review Cadence System (Daily/Weekly/Monthly/Quarterly AI-generated)
- Goal Stack Enforcement (dead node detection, stall detection)

### Brain Engine / "Samantha Layer" (13 features — no equivalent in any reference codebase)

- Inner Loop (APScheduler 90min proactive reasoning, not turn-based)
- State Engine with Inferred Cause Chain (psychological + operational state)
- Multi-Horizon Pattern Engine (H1–H5 across 6h to all-time)
- User Identity Profile (PG table, rolling-average updates, never overwritten)
- Personal Reward Model (sklearn, 👍/👎 trained, weekly retrain)
- Hebbian Pathway Weighting + STDP (biological decay rules on Neo4j)
- Inferred Cause Chain Engine (cross-referencing state + patterns + history)
- Personality + "Wants" Engine (SOUL.md rules + WantNodes in Neo4j)
- Context Forge (800-token 6-layer assembler with relevance-based truncation)
- Query Router / Intent Classifier (8 intent types, source routing matrix)
- Spaced Repetition Memory Reinforcement
- Project-Specific Memory Decay (Cypher-based weight reduction)
- Self-Evolving Architect Bot (auto-generates code patches, risk-gated deployment)

### Data & Vault Philosophy (11 features — no equivalent in any reference codebase)

- PageIndex + Direct Retrieval (whole-note embedding, no middleware)
- Nightly Vault Ingestion Pipeline (multi-account Playwright scraping of ChatGPT×3, Claude, Gemini, Perplexity)
- Weekly Full Vault Synthesis (personality drift report, faction narrative)
- LOCUS_SHORTHAND (~4× token compression)
- Obsidian as Primary Dashboard (8 panels, replaces PWA)
- Obsidian MCP (vault_read/write/search/tag/stats)
- 3-Level Tag Hierarchy (faction/domain/specific)
- Rough Note Parser / Idea Tracker (/idea → expand → promote/research/archive)
- Link Dump / Resource Logger (/link → vault note)
- Daily AI Chat Archiver (nightly Telegram → vault → git)
- Excalidraw MCP Skill

### Interface Philosophy (6 features — deliberate non-builds)

- No TUI (explicitly rejected as design decision)
- Telegram as primary interface (not a gateway — the native interface)
- 4 Daily Structured Check-ins (Morning/Afternoon/Evening/Night)
- Voice Call Interface (Groq Whisper → Kokoro TTS → vault transcript)
- Structured Check-in Reminders (APScheduler → Telegram inline keyboards)
- Obsidian Dashboard replaces PWA

### Infrastructure Decisions (7 features — philosophical choices)

- Git for vault sync (replacing Syncthing, directory partitioning)
- Manual Google OAuth (replacing Composio, 50 lines)
- pgvector replaces Qdrant + ChromaDB
- Redis optional (PG + in-memory dict at single-user scale)
- DeepSeek V4 Flash only (~$0.012/day, ~$4/year)
- Minimum AI in Every Harness Layer (LLM only for reasoning/generation)
- Zero-cost constraint as 1st-class architectural requirement

# 7. Gaps & Missing Features

## Locus OS gaps vs others

### Genuine infrastructure gaps

| Missing Feature                         | Present in                                                            | Impact                                                                                                            |
| --------------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| No compaction/context management (code) | Pi, Hermes, OpenHuman                                                 | Locus will hit context limits on long sessions. (Note: Context Forge is designed but not yet implemented as code) |
| No skills system                        | Pi (skills), Hermes (skills), OpenHuman (skill_registry)              | No reusable agent skill ecosystem                                                                                 |
| No full MCP server/registry             | OpenHuman (full), Hermes (ACP)                                        | Can't expose tools to external clients                                                                            |
| No automated testing                    | Pi (vitest), Hermes (pytest), OpenHuman (cargo test)                  | No regression safety net                                                                                          |
| No CI/CD                                | All three                                                             | No automated quality gates                                                                                        |
| No approval gate UX                     | Hermes (ACP), OpenHuman (approval)                                    | No user approval flow for dangerous actions                                                                       |
| No sandbox beyond shell blocklists      | Hermes (file_safety), OpenHuman (bubblewrap/docker/firejail/landlock) | Limited security isolation                                                                                        |

### Intentional non-builds (not gaps)

| "Missing" Feature                | Locus's Design Decision | Rationale                                                                                                                |
| -------------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| No TUI keybindings/themes        | Deliberately rejected   | "A TUI is a third interface that does a worse version of both Telegram and Obsidian." Telegram is the primary interface. |
| Single LLM provider (no routing) | DeepSeek V4 Flash only  | Architectural decision: one model, one behavior, ~$4/year. Zero-cost constraint shapes design.                           |
| No multi-provider cascade        | By design               | Minimum AI in harness — deterministic logic where possible, LLM only for reasoning/generation.                          |

### Learning: not a gap (design is ahead of code)

The original audit listed "No learning loop (beyond basic reflector)" as a gap. This is **incorrect at the design level**. Locus's designed learning system includes: Hebbian+STDP weighting, Personal Reward Model (sklearn), 5-horizon Pattern Engine, User Identity Profile, Architect Bot, Spaced Repetition Memory Reinforcement, and Project-Specific Memory Decay. This is architecturally more sophisticated than Hermes's curator or OpenHuman's post-turn hooks — but exists primarily in design docs, not yet fully in code.

## Pi gaps vs others

| Missing Feature            | Present in                                    | Impact                                  |
| -------------------------- | --------------------------------------------- | --------------------------------------- |
| No multi-channel messaging | Hermes, OpenHuman, Locus                      | CLI/TUI only, no Telegram/Discord/Slack |
| No voice                   | Hermes, OpenHuman, Locus                      | No voice input/output                   |
| No search providers        | Hermes, OpenHuman, Locus                      | No web search capability                |
| No browser automation      | Hermes, OpenHuman, Locus                      | No web interaction                      |
| No learning loop           | Hermes (curator), OpenHuman (post-turn hooks) | No agent self-improvement               |
| No cron/scheduling         | Hermes, OpenHuman, Locus                      | No scheduled tasks                      |
| No security sandboxing     | Hermes, OpenHuman, Locus                      | Limited safety for dangerous operations |

## Hermes gaps vs others

| Missing Feature           | Present in       | Impact                                     |
| ------------------------- | ---------------- | ------------------------------------------ |
| No Holographic HRR memory | Locus only       | No VSA-based concept binding               |
| No full MCP server        | OpenHuman only   | No MCP tool exposure                       |
| No intelligent routing    | OpenHuman only   | No health/quality-based provider selection |
| No Neo4j graph memory     | OpenHuman, Locus | No knowledge graph                         |
| No computer use (VNC)     | Locus only       | No remote desktop control                  |

## OpenHuman gaps vs others

| Missing Feature               | Present in  | Impact                         |
| ----------------------------- | ----------- | ------------------------------ |
| No session export (HTML/JSON) | Pi only     | No shareable session artifacts |
| No 13-channel messaging       | Locus only  | Fewer platform integrations    |
| No Holographic HRR            | Locus only  | No VSA encoding                |
| No batch trajectory runner    | Hermes only | No large-scale agent runs      |
| No ACP protocol               | Hermes only | No ACP compatibility           |
