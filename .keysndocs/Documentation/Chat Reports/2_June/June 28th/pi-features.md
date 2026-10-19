# Pi Agent — Exhaustive Feature Audit

> **Package**: `@earendil-works/pi-coding-agent` + `@earendil-works/pi-agent-core` + `@earendil-works/pi-ai` + `@earendil-works/pi-tui`
> **Language**: TypeScript (Node.js, strip-only)

---

## SUBSYSTEM 1: CODING AGENT CLI

**Entry**: `packages/coding-agent/src/main.ts` | **Args**: `cli/args.ts` | **Help**: `cli/args.ts::printHelp()`

### Run Modes (5)

| Mode | File | Description |
|---|---|---|
| **Interactive** | `modes/interactive/interactive-mode.ts` (5662 lines) | Full TUI: streaming output, inline editor, history, all keybindings |
| **Print (text)** | `modes/print-mode.ts` | Non-interactive, single-turn, prints to stdout |
| **Print (json)** | `modes/print-mode.ts` | Same but JSON output |
| **RPC** | `modes/rpc/rpc-mode.ts` + `rpc-client.ts` | JSONL-based RPC protocol over stdio for programmatic use |
| **SDK** | `core/sdk.ts` | `createAgentSession()` — programmatic API |

### CLI Flags (39 flags)

| Flag | Details |
|---|---|
| `--provider <name>` | Default: google |
| `--model <pattern>` | "provider/id" or just "id", can append `:thinkingLevel` |
| `--api-key <key>` | Override env var |
| `--system-prompt <text>` | Custom system prompt |
| `--append-system-prompt <text>` | Repeatable, appends text or file contents |
| `--mode text\|json\|rpc` | Output mode |
| `--print, -p` | Non-interactive mode |
| `--continue, -c` | Resume last session |
| `--resume, -r` | Pick session to resume |
| `--session <path\|id>` | Use specific session |
| `--session-id <id>` | Exact session ID (create if missing) |
| `--fork <path\|id>` | Fork session into child |
| `--session-dir <dir>` | Override session storage dir |
| `--no-session` | Ephemeral (no persistence) |
| `--name, -n` | Set session display name |
| `--models <patterns>` | Comma-sep model patterns for Ctrl+P cycling (supports globs) |
| `--no-tools, -nt` | Disable ALL tools |
| `--no-builtin-tools, -nbt` | Disable only read/bash/edit/write |
| `--tools, -t <names>` | Tool allowlist |
| `--exclude-tools, -xt <names>` | Tool denylist |
| `--thinking <level>` | off\|minimal\|low\|medium\|high\|xhigh |
| `--extension, -e <path>` | Load extension (repeatable) |
| `--no-extensions, -ne` | Disable extension discovery |
| `--skill <path>` | Load skill (repeatable) |
| `--no-skills, -ns` | Disable skills |
| `--prompt-template <path>` | Load prompt template (repeatable) |
| `--no-prompt-templates, -np` | Disable prompt templates |
| `--theme <path>` | Load theme (repeatable) |
| `--no-themes` | Disable themes |
| `--no-context-files, -nc` | Disable AGENTS.md/CLAUDE.md discovery |
| `--export <file>` | Export session to HTML |
| `--list-models [search]` | List models (optional fuzzy filter) |
| `--verbose` | Force verbose startup |
| `--approve, -a` | Trust project-local files |
| `--no-approve, -na` | Ignore project-local files |
| `--offline` | Skip network operations |
| `--help, -h` | Show help |
| `--version, -v` | Show version |
| `@<file>` | Include file content/images in initial message |
| `<unknown-flags>` | Passed through to extension system |

### CLI Subcommands (6)

| Command | File | Description |
|---|---|---|
| `pi install <source> [-l]` | `main.ts` | Install extension from remote/local |
| `pi remove <source> [-l]` | `main.ts` | Remove extension from settings |
| `pi uninstall <source> [-l]` | `main.ts` | Alias for remove |
| `pi update [source\|self\|pi]` | `main.ts` | Update pi and extensions |
| `pi list` | `main.ts` | List installed extensions |
| `pi config` | `main.ts` | TUI to enable/disable resources |

### Startup Flow Steps

| Step | File | Description |
|---|---|---|
| Arg parsing | `cli/args.ts` | Parse all flags, collect unknown flags for extensions |
| First-time setup | `cli/startup-ui.ts` | `shouldRunFirstTimeSetup()`, `showFirstTimeSetup()` |
| Project trust | `cli/project-trust.ts` | `resolveProjectTrusted()` — AGENTS.md approval gate |
| Session selection | `cli/session-picker.ts` | `selectSession()` — pick/create/resume session |
| Initial message | `cli/initial-message.ts` | Build initial message from args, stdin, `@files` |
| Session manager | `main.ts` | `createSessionManager()` — fork/open/in-memory/new |
| Model resolution | `core/model-resolver.ts` | `resolveCliModel()`, `findInitialModel()` |
| Auth storage | `core/auth-storage.ts` | `AuthStorage.create()` — persists OAuth tokens |
| Settings manager | `core/settings-manager.ts` | User settings read from `~/.pi/agent/settings.json` |
| Model registry | `core/model-registry.ts` | `ModelRegistry.create()` — manages provider/model configs |
| Resource loader | `core/resource-loader.ts` | `DefaultResourceLoader` — discovers skills, extensions, prompts, themes |
| Extension runner | `core/extensions/runner.ts` | Loads and initializes all extensions |
| Agent session | `core/agent-session.ts` (3137 lines) | `AgentSession` — the core abstraction |
| Mode dispatch | `modes/index.ts` | Route to interactive/print/rpc |

---

## SUBSYSTEM 2: AGENT HARNESS

**Package**: `packages/agent/src/`

### Agent Loop (`agent-loop.ts`)

| Feature | Description |
|---|---|
| `agentLoop()` | Full loop: prompt -> LLM stream -> tool execution -> repeat |
| `agentLoopContinue()` | Continue from context (no new prompt) |
| `runAgentLoop()` | Async executor with event emission |
| `runAgentLoopContinue()` | Async continue executor |
| Parallel tool execution | `ToolExecutionMode: "sequential" \| "parallel"` |
| Queue mode | `QueueMode: "all" \| "one-at-a-time"` |
| Auto-retry | Max retries, max delay, exponential backoff |
| Abort signal | Cancellation support |

### Agent State (`agent.ts`)

| Property | Type | Description |
|---|---|---|
| `systemPrompt` | string | System prompt |
| `model` | `Model<any>` | Current LLM model |
| `thinkingLevel` | ThinkingLevel | off/minimal/low/medium/high/xhigh |
| `tools` | `AgentTool[]` | Registered tools |
| `messages` | `AgentMessage[]` | Conversation history |
| `isStreaming` | boolean | Turn in progress |
| `streamingMessage` | `AgentMessage \| undefined` | In-progress message |
| `pendingToolCalls` | `Set<string>` | Unresolved tool call IDs |
| `errorMessage` | `string \| undefined` | Last error |

### Agent Events (13 types)

turn_start, message_start, message_snapshot, message_update, message_end, tool_execution_start, tool_execution_update, tool_execution_end, turn_end, agent_end, queue_update, auto_retry_start, auto_retry_end

### Tool Lifecycle Hooks

| Hook | Description |
|---|---|
| `convertToLlm` | Convert AgentMessage[] to LLM Message[] |
| `beforeToolCall` | Inspect/block/modify tool calls before execution |
| `afterToolCall` | Inspect/override tool results after execution |
| `streamFn` | Custom provider stream function |
| `onPayload` | Inspect/modify provider payload |
| `onResponse` | Inspect provider response |
| `transformContext` | Transform context before LLM call |

---

## SUBSYSTEM 3: AI PROVIDER LAYER

**Package**: `packages/ai/src/`

### Provider APIs (10 API types, 36+ providers)

| API | Provider(s) | File |
|---|---|---|
| `anthropic-messages` | anthropic, ant-ling | `providers/anthropic.ts` |
| `openai-completions` | openai, deepseek, nvidia, groq, cerebras, xai, fireworks, together, openrouter, vercel-ai-gateway, huggingface, zai, zai-coding-cn, opencode, opencode-go, kimi-coding, minimax, minimax-cn, moonshotai, moonshotai-cn, xiaomi, xiaomi-token-plan-*, cloudflare-* | `providers/openai-completions.ts` |
| `openai-responses` | openai (Responses API) | `providers/openai-responses.ts` |
| `azure-openai-responses` | azure-openai-responses | `providers/azure-openai-responses.ts` |
| `openai-codex-responses` | openai-codex | `providers/openai-codex-responses.ts` |
| `mistral-conversations` | mistral | `providers/mistral.ts` |
| `google-generative-ai` | google | `providers/google.ts` |
| `google-vertex` | google-vertex | `providers/google-vertex.ts` |
| `bedrock-converse-stream` | amazon-bedrock | `providers/amazon-bedrock.ts` |
| `openrouter-images` | openrouter (images API) | `providers/images/openrouter.ts` |

### Provider Features

| Feature | File | Description |
|---|---|---|
| Lazy provider loading | `providers/register-builtins.ts` | Providers loaded on first use |
| Proxy support | `utils/node-http-proxy.ts` | HTTP proxy for API calls |
| OAuth (device code) | `utils/oauth/device-code.ts` | Device code flow |
| OAuth (PKCE) | `utils/oauth/pkce.ts` | PKCE auth flow |
| Anthropic OAuth | `utils/oauth/anthropic.ts` | Anthropic-specific |
| GitHub Copilot OAuth | `utils/oauth/github-copilot.ts` | Copilot-specific |
| OpenAI Codex OAuth | `utils/oauth/openai-codex.ts` | Codex-specific |
| OAuth page | `utils/oauth/oauth-page.ts` | Local HTTP callback server |
| Prompt cache headers | `providers/openai-prompt-cache.ts` | Cache retention control |
| GitHub Copilot headers | `providers/github-copilot-headers.ts` | Attribution headers |
| Transport modes | `types.ts` | sse, websocket, websocket-cached, auto |
| ThinkingBudgets | `types.ts` | Per-level token budgets |
| EventStream | `utils/event-stream.ts` | Push-based async stream |

### Core Types

| Type | File | Description |
|---|---|---|
| `Message` | `types.ts` | role, content[], tool_calls |
| `Context` | `types.ts` | Array of Message |
| `AssistantMessage` | `types.ts` | Full response with usage, stopReason, error |
| `ToolCall` | `types.ts` | id, name, arguments |
| `ToolResultMessage` | `types.ts` | role:toolResult |
| `TextContent` / `ImageContent` | `types.ts` | Content blocks |
| `UsageInfo` | `types.ts` | tokens + cost breakdown |
| `Model<T>` | `types.ts` | provider, api, cost, contextWindow, maxTokens |
| `KnownProvider` | `types.ts` | Union of 35+ string constants |

---

## SUBSYSTEM 4: SESSION SYSTEM

**Source**: `packages/coding-agent/src/core/session-manager.ts`

### Persistence Format

| Feature | Detail |
|---|---|
| Format | JSONL — one JSON object per line |
| Header | `SessionHeader` with type, version, id, timestamp, cwd, parentSession |
| Location | `~/.pi/agent/sessions/<cwd-path>/session.jsonl` |
| Global sessions | `~/.pi/agent/sessions-global/` |
| Current version | v3 (migrates from v1 and v2) |

### Entry Types (9)

session, message, compaction, thinking_level_change, model_change, branch_summary, custom (extension data, not in context), custom_message (extension message, in context), label (bookmark), session_info (display name)

### Session Operations (29+)

create, inMemory, open, forkFrom, saveEntry, buildSessionContext, getTree, getBranch, getLeafId, setLeafId, appendMessage, undoAppendLastMessage, appendModelChange, appendThinkingLevelChange, setLabel, deleteLabel, getLabel, getSessionName, setSessionName, getHeader, getSessionId, getSessionFile, list, listAll, delete, rename, getCwd, assertValidSessionId

### Compaction System

**Source**: `core/compaction/`

| Feature | Description |
|---|---|
| `shouldCompact()` | Check threshold/overflow trigger |
| `prepareCompaction()` | Run pre-compaction hooks |
| `compact()` | Summarize older messages, keep recent N |
| `calculateContextTokens()` | Estimate token count |
| `estimateContextTokens()` | Fast token estimation |
| `generateBranchSummary()` | LLM-generated branch summary |
| Auto-compaction | Automatic at thresholds during loop |
| Manual compaction | User-triggered |
| Overflow compaction | On context overflow |
| Extension hooks | `session_before_compact` event |

### Session Events

| Event | Description |
|---|---|
| `compaction_start` | Compaction begins |
| `compaction_end` | Compaction ends |
| `session_info_changed` | Name changed |
| `thinking_level_changed` | Level changed |

### HTML Export

| Feature | File | Description |
|---|---|---|
| Full HTML export | `core/export-html/index.ts` | Export session to standalone HTML |
| ANSI-to-HTML | `core/export-html/ansi-to-html.ts` | Convert ANSI codes |
| Tool renderer | `core/export-html/tool-renderer.ts` | Render tool calls |
| Template CSS/HTML/JS | `core/export-html/template.*` | Export theme |
| Highlight.js | `core/export-html/vendor/highlight.min.js` | Syntax highlighting |
| Marked.js | `core/export-html/vendor/marked.min.js` | Markdown rendering |

---

## SUBSYSTEM 5: BUILT-IN TOOLS

**Source**: `packages/coding-agent/src/core/tools/`

| Tool | File | Description | Read-Only |
|---|---|---|---|
| `read` | `tools/read.ts` | Read file contents (offset, limit) | Yes |
| `bash` | `tools/bash.ts` | Execute shell commands | No |
| `edit` | `tools/edit.ts` | Find/replace file edits | No |
| `write` | `tools/write.ts` | Write/overwrite files | No |
| `grep` | `tools/grep.ts` | Search file contents (regex) | Yes |
| `find` | `tools/find.ts` | Find files by glob pattern | Yes |
| `ls` | `tools/ls.ts` | List directory contents | Yes |

### Tool Features

| Feature | File | Description |
|---|---|---|
| `ToolDef` | `tools/index.ts` | Type-safe tool definition |
| `Tool` (AgentTool) | `tools/index.ts` | Executable tool with operations |
| `withFileMutationQueue` | `tools/file-mutation-queue.ts` | Batch file mutations |
| `createCodingTools()` | `tools/index.ts` | read + bash + edit + write |
| `createReadOnlyTools()` | `tools/index.ts` | read + grep + find + ls |
| `createAllTools()` | `tools/index.ts` | All 7 tools |
| `BashOperations` | `tools/bash.ts` | Configurable bash operations |
| `EditOperations` | `tools/edit.ts` | Configurable edit operations |
| Path utils | `tools/path-utils.ts` | Path resolution helpers |
| Truncation utils | `tools/truncate.ts` | Output truncation (head/tail) |
| Output accumulator | `tools/output-accumulator.ts` | Accumulate tool output |
| Render utils | `tools/render-utils.ts` | Tool output rendering |
| Tool definition wrapper | `tools/tool-definition-wrapper.ts` | Wrap AgentTool -> ToolDef |

### Tool Config Options

| Tool | Option | Description |
|---|---|---|
| Read | `maxBytes`, `maxLines` | Truncation limits |
| Bash | `timeout`, `sandbox`, `allowedCommands`, `blockedCommands` | Execution control |
| Edit | `maxEdits`, `diffContext` | Edit behavior |
| Grep | `maxResults`, `context` | Search limits |
| Find | `maxResults`, `globPattern` | Search limits |
| Ls | `maxEntries` | Directory limit |

---

## SUBSYSTEM 6: INTERACTIVE TUI

**Source**: `packages/tui/src/` + `modes/interactive/`

### TUI Framework Components (`packages/tui/src/`)

| Component | File | Description |
|---|---|---|
| `TUI` class | `tui.ts` | Core TUI: layout, overlays, input, rendering, signals |
| `Terminal` | `terminal.ts` | Raw terminal: raw mode, resize, ANSI, mouse |
| `ProcessTerminal` | `terminal.ts` | PTY-based terminal |
| `EditorComponent` | `editor-component.ts` | Multiline text editor with undo/redo |
| `Input` | `components/input.ts` | Single-line input |
| `Box` | `components/box.ts` | Bordered container |
| `Text` | `components/text.ts` | Styled text |
| `Spacer` | `components/spacer.ts` | Flexible spacing |
| `Markdown` | `components/markdown.ts` | Markdown renderer (with ANSI theme) |
| `Loader` | `components/loader.ts` | Animated spinner |
| `CancellableLoader` | `components/cancellable-loader.ts` | Cancellable spinner |
| `SelectList` | `components/select-list.ts` | Selectable list overlay |
| `SettingsList` | `components/settings-list.ts` | Settings editor overlay |
| `Image` | `components/image.ts` | Terminal image (iTerm/sixel/kitty) |
| `TruncatedText` | `components/truncated-text.ts` | Width-truncated text |

### TUI Features

| Feature | File | Description |
|---|---|---|
| Autocomplete | `autocomplete.ts` | Fuzzy autocomplete for input |
| Fuzzy matching | `fuzzy.ts` | Fuzzy string search |
| Keybindings | `keybindings.ts` | Keybinding config and matching |
| Key parsing | `keys.ts` | Raw key event parsing |
| Kill ring | `kill-ring.ts` | Clipboard kill ring (C-k, C-y) |
| Undo stack | `undo-stack.ts` | Multi-level undo |
| Word navigation | `word-navigation.ts` | Word-based cursor movement |
| Stdin buffer | `stdin-buffer.ts` | Raw stdin reader |
| Terminal image | `terminal-image.ts` | Image display protocols |
| Utils | `utils.ts` | Width, wrapping helpers |
| Native modifiers (macOS) | `native/darwin/` | Native modifier detection (C code) |
| Native console mode (Windows) | `native/win32/` | Console mode setup (C code) |

### Interactive Mode UI Components

**Source**: `modes/interactive/components/`

| Component | Description |
|---|---|
| `user-message.ts` | User message renderer |
| `user-message-selector.ts` | User message selection |
| `assistant-message.ts` | Assistant message renderer |
| `tool-execution.ts` | Tool execution block renderer |
| `bash-execution.ts` | Bash tool specific renderer |
| `diff.ts` | Diff display |
| `compaction-summary-message.ts` | Compaction message renderer |
| `branch-summary-message.ts` | Branch summary renderer |
| `skill-invocation-message.ts` | Skill invocation renderer |
| `custom-message.ts` | Extension message renderer |
| `footer.ts` | Status footer with provider, model, cost |
| `config-selector.ts` | Config overlay |
| `model-selector.ts` | Model selector (Ctrl+P) |
| `scoped-models-selector.ts` | Scoped model selector |
| `session-selector.ts` | Session picker |
| `session-selector-search.ts` | Session search |
| `theme-selector.ts` | Theme picker |
| `thinking-selector.ts` | Thinking level selector |
| `trust-selector.ts` | Project trust selector |
| `settings-selector.ts` | Settings editor |
| `show-images-selector.ts` | Image display toggle |
| `oauth-selector.ts` | OAuth login dialog |
| `login-dialog.ts` | Login dialog |
| `extension-editor.ts` | Extension editor |
| `extension-input.ts` | Extension input hook |
| `extension-selector.ts` | Extension picker |
| `custom-editor.ts` | Custom editor |
| `tree-selector.ts` | Session tree navigation |
| `first-time-setup.ts` | First-run wizard |
| `armin.ts` | ARMin (ARM) status display |
| `earendil-announcement.ts` | Splash/announcement |
| `bordered-loader.ts` | Bordered loading indicator |
| `countdown-timer.ts` | Countdown timer |
| `dynamic-border.ts` | Dynamic border animation |
| `daxnuts.ts` | Decorative element |
| `keybinding-hints.ts` | Keybinding help |
| `index.ts` | Component barrel |

### Interactive Mode Features (`interactive-mode.ts`)

| Feature | Description |
|---|---|
| Streaming output rendering | Real-time assistant message display |
| Inline editor | Full multiline editor with undo/redo |
| Clipboard support | Kill ring, paste buffer, OSC 52 |
| Image display | Terminal images (iTerm2/sixel/kitty) |
| Pipe/stdin input | Accept piped input |
| Session tree navigation | Browse session history tree |
| Branch forking | Fork sessions on the fly |
| Compaction triggers | Manual/auto context compaction |
| Model switching | Ctrl+P model cycling |
| Thinking level switching | Per-conversation think level |
| Theme switching | Dark/light/custom themes |
| Config editing | In-TUI settings editor |
| Extension UI | Extension-provided UI elements |
| Slash commands | /help, /clear, /export, etc. |
| Ctrl+C interrupt | Cancel current response |
| Suspend/resume | Ctrl+Z suspend, resume support |
| Signal handling | SIGINT, SIGTERM cleanup |

### Themes (`modes/interactive/theme/`)

| File | Description |
|---|---|
| `theme.ts` | Theme system with dark/light auto-detect |
| `dark.json` | Default dark theme |
| `light.json` | Default light theme |
| `theme-schema.json` | Theme validation schema |

### Keybindings (`core/keybindings.ts`)

| Keybinding | Default key | Description |
|---|---|---|
| `app.interrupt` | `Ctrl+C` | Interrupt current response |
| `app.clear` | `Ctrl+L` | Clear screen |
| `app.exit` | `Ctrl+D` (empty) | Exit |
| `app.suspend` | `Ctrl+Z` | Suspend process |
| `app.model.cycleForward` | `Ctrl+P` | Next model |
| `app.model.cycleBackward` | `Ctrl+Shift+P` | Previous model |
| `app.model.select` | `Ctrl+Shift+M` | Model selector |
| `app.thinking.cycle` | `Ctrl+Shift+T` | Cycle thinking level |
| `app.thinking.toggle` | `Ctrl+T` | Toggle thinking on/off |
| `app.tools.expand` | `Ctrl+E` | Expand/collapse tools |
| `app.editor.external` | `Ctrl+O` | Open external editor |
| `app.message.followUp` | `Ctrl+Enter` | Send follow-up |
| `tui.input.submit` | `Enter` | Submit input |
| `tui.input.newline` | `Alt+Enter` / `Ctrl+Enter` | New line in editor |
| `tui.input.cancel` | `Escape` | Cancel input |

---

## SUBSYSTEM 7: SKILLS SYSTEM

**Source**: `core/skills.ts`

| Feature | Description |
|---|---|
| Skill discovery | Scan directories for `SKILL.md` files |
| Frontmatter parsing | `name`, `description`, `disable-model-invocation` + custom fields |
| Validation | Name (lowercase, a-z0-9-hyphens, max 64), description (max 1024) |
| Ignore file support | Respects `.gitignore`, `.ignore`, `.fdignore` |
| Collision resolution | Root skills preferred over nested; alphabetic tiebreak |
| Skill block parsing | `<skill name="x" location="y">...</skill>` in user messages |
| Skill invocation | Skills invoked via slash command or `<skill>` block in messages |
| `disable-model-invocation` | Flag to prevent model from auto-invoking the skill |
| Nested skills | Subdirectories under skills/ are discovered |
| Source info | Each skill tracked with file path, base dir, source type |
| Diagnostics | Validation errors reported as `ResourceDiagnostic[]` |

---

## SUBSYSTEM 8: EXTENSION SYSTEM

**Source**: `core/extensions/`

### Extension Lifecycle Events (25+ events)

| Event | Direction | Description |
|---|---|---|
| `before_agent_start` | Hook | Before agent session starts, can add context/tools |
| `session_before_compact` | Hook | Before compaction, can add data to compaction entry |
| `session_shutdown` | Hook | On session end, cleanup |
| `session_before_fork` | Hook | Before session fork |
| `session_before_switch` | Hook | Before session switch |
| `session_before_tree` | Hook | Before tree navigation |
| `resources_discover` | Hook | Extension declares resources (tools, commands, etc.) |
| `before_provider_request` | Hook | Modify provider payload |
| `after_provider_response` | Hook | Inspect provider response |
| `turn_start` / `turn_end` | Hook | Turn lifecycle |
| `message_start` / `message_end` | Hook | Message lifecycle |
| `tool_call` | Hook | Intercept tool calls |
| `tool_result` | Hook | Intercept tool results |
| `user_bash` | Hook | Intercept bash execution |
| `project_trust` | Hook | Project trust checks |
| `context` | Hook | Add/remove messages from context |
| `input` | Hook | Transform/modify user input |

### Extension Capabilities

| Capability | Description |
|---|---|
| Register tools | `registerTool()` — LLM-callable tools |
| Register commands | `registerCommand()` — slash commands |
| Register shortcuts | `registerShortcut()` — keyboard shortcuts |
| Register flags | `registerFlag()` — CLI flags |
| Register renderers | `registerMessageRenderer()` — custom message renderers |
| Register autocomplete | `setAutocompleteProvider()` — custom autocomplete |
| Register editor factory | `setEditorFactory()` — custom editor |
| Open dialogs | `openDialog()` — modal dialogs |
| Open widgets | `openWidget()` — persistent UI elements |
| Toast notifications | `showToast()` — temporary notifications |
| Run tool | `runTool()` — execute a tool from extension |
| Bash execution | `runBash()` — execute shell from extension |
| Set footer data | `footerDataProvider.setData()` |
| OAuth provider | `setOAuthProvider()` |
| Working indicator | `setWorkingIndicator()` — custom streaming loader |
| Terminal input listener | `onTerminalInput()` |

### Extension Config (`types.ts`)

```typescript
interface Extension {
  name: string;
  setup?(ctx: ExtensionContext): Promise<void>;
  // ... event handlers as optional methods
}
```

---

## SUBSYSTEM 9: PROMPT TEMPLATES

**Source**: `core/prompt-templates.ts`

| Feature | Description |
|---|---|
| `expandPromptTemplate()` | Expand template with variable substitution |
| Template discovery | From `--prompt-template` flags and resource loader |
| Frontmatter | YAML frontmatter in `.md` templates |

---

## SUBSYSTEM 10: SYSTEM PROMPT

**Source**: `core/system-prompt.ts`

| Feature | Description |
|---|---|
| `buildSystemPrompt()` | Build system prompt from context files and settings |
| AGENTS.md discovery | Project-local AGENTS.md loaded as system prompt context |
| CLAUDE.md discovery | CLAUDE.md loaded as additional context |
| Settings-based prompt | Default system prompt from provider settings |
| Append system prompt | Additional text from `--append-system-prompt` |

---

## SUBSYSTEM 11: CONFIG & SETTINGS

**Source**: `core/settings-manager.ts`, `config.ts`, `core/model-registry.ts`

| Setting | Description |
|---|---|
| Default provider | Default LLM provider |
| Default model | Default model ID |
| Default thinking level | Default think level |
| Provider retry settings | maxRetries, timeoutMs, maxRetryDelayMs |
| HTTP idle timeout | HTTP connection timeout |
| WebSocket connect timeout | WS connection timeout |
| Block images | Disable image sending to model |
| Steering mode | Queue steering control |
| Follow-up mode | Follow-up message control |
| Transport | SSE/WebSocket/Auto selection |
| Thinking budgets | Per-level token budgets |
| Quiet startup | Suppress version/startup messages |

---

## SUBSYSTEM 12: RPC MODE

**Source**: `modes/rpc/`

| Feature | File | Description |
|---|---|---|
| RPC protocol | `rpc-types.ts` | JSONL request/response format |
| RPC client | `rpc-client.ts` | Client for programmatic use |
| RPC mode | `rpc-mode.ts` | Server side handler |
| JSONL serialization | `jsonl.ts` | JSONL line protocol |

---

## SUBSYSTEM 13: UTILITIES

**Source**: `packages/coding-agent/src/utils/`

| Utility | File | Description |
|---|---|---|
| ANSI processing | `ansi.ts` | ANSI escape code handling |
| Changelog | `changelog.ts` | Changelog rendering |
| Child process | `child-process.ts` | Process spawning utils |
| Clipboard | `clipboard.ts` | Clipboard read/write |
| Clipboard image | `clipboard-image.ts` | Image clipboard (Windows) |
| Clipboard native | `clipboard-native.ts` | Native clipboard (macOS) |
| Deprecation | `deprecation.ts` | Deprecation warnings |
| EXIF orientation | `exif-orientation.ts` | Image orientation fix |
| Frontmatter | `frontmatter.ts` | YAML frontmatter parse |
| FS watch | `fs-watch.ts` | File system watcher |
| Git | `git.ts` | Git operations |
| HTML | `html.ts` | HTML utilities |
| Image convert | `image-convert.ts` | Image format conversion |
| Image resize | `image-resize.ts` | Image resize (worker: `image-resize-worker.ts`) |
| Image resize core | `image-resize-core.ts` | Sharp-based resize core |
| JSON | `json.ts` | JSON utilities |
| MIME | `mime.ts` | MIME type detection |
| Open browser | `open-browser.ts` | Open URL in browser |
| Paths | `paths.ts` | Path resolution utilities |
| Photon | `photon.ts` | Photon image processing |
| Pi user agent | `pi-user-agent.ts` | User agent string for API calls |
| Shell | `shell.ts` | Shell utilities |
| Sleep | `sleep.ts` | Promise-based sleep |
| Syntax highlight | `syntax-highlight.ts` | Code syntax highlighting |
| Tools manager | `tools-manager.ts` | Tool lifecycle manager |
| Version check | `version-check.ts` | Version update check |
| Windows self-update | `windows-self-update.ts` | Windows auto-update |

---

##