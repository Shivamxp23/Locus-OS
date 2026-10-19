# PI AGENT — COMPLETE ATOMIC FEATURE SPECIFICATION (v2 — CORRECTED)

Source-of-truth dump for comprehension, clone, and reimplementation.
Covers: core runtime, tools, extensions, skills, providers, models, TUI, sessions, CLI, SDK, compaction, keybindings, themes, packages, settings, and more.

---

## 1. CORE RUNTIME & ARCHITECTURE

### Tech Stack
- **TypeScript monorepo** — Node.js runtime, npm workspaces
- **4 packages**: `pi-coding-agent` (CLI + SDK), `pi-agent-core` (agent runtime), `pi-ai` (LLM API), `pi-tui` (terminal UI)
- Lazy imports for cold-start optimization
- Diff-based terminal rendering with full Unicode support
- Supply-chain: exact version pins, shrinkwrap, `--ignore-scripts`, npm audit

### Agent Loop (`packages/agent/`)
- `AIAgent` core agent class with tool-calling loop
- `agent-loop.ts` — main conversation loop with iteration budget
- Streaming and non-streaming response paths
- Tool-call dispatch via function name matching
- Token tracking per turn (input/output/cache)
- Grace-turn after budget exhaustion
- Automatic agent-level retry on transient errors (max 3 retries, 2s base delay, exponential backoff)
- Provider-level retry config (timeout, maxRetries, maxRetryDelayMs)

### Agent Harness (`packages/agent/src/harness/`)
- `agent-harness.ts` — AgentHarness wrapping AIAgent with session, skills, compaction
- `system-prompt.ts` — system prompt assembly from templates + skills + context
- `skills.ts` — skill discovery, loading, progressive disclosure (Agent Skills standard)
- `prompt-templates.ts` — prompt template expansion
- `messages.ts` — session message types
- `env/nodejs.ts` — Node.js environment adapter
- `session/` — JSONL repo, memory repo, UUID generation
- `compaction/` — auto-compaction and branch summarization
- `utils/` — shell output capture, truncation helpers

---

## 2. CLI & EXECUTION MODES

### Interactive Mode (default)
- Full TUI with editor, message history, tool rendering
- Four visual areas: startup header, messages, editor, footer
- File reference: `@` fuzzy-search, Tab path completion, Shift+Enter multi-line
- Image paste: Ctrl+V (Alt+V on Windows), drag into terminal
- Shell: `!command` sends to model, `!!command` silent
- External editor: Ctrl+G opens `$VISUAL` or `$EDITOR`
- Message queue: Enter=steer, Alt+Enter=follow-up, Escape=abort, Alt+Up=restore

### Print Mode (`-p`, `--print`)
- Non-interactive: send prompt, print response, exit
- Reads piped stdin: `cat README.md | pi -p "Summarize"`

### JSON Event Stream Mode (`--mode json`)
- All session events as JSON lines to stdout
- Events: agent_start/end, turn_start/end, message_start/update/end, tool_execution_start/update/end
- queue_update, compaction_start/end, auto_retry_start/end

### RPC Mode (`--mode rpc`)
- JSON protocol over stdin/stdout (strict JSONL, LF-only)
- Commands: prompt, cancel, set-model, set-thinking, fork, compact, session-info, etc.
- `streamingBehavior`: queue, steer, queueHead, block
- Optional `id` for request/response correlation

### CLI Subcommands
- `pi install <source> [-l]` — install package (npm/git/path), `-l` for project-local
- `pi remove`/`uninstall <source> [-l]` — remove
- `pi update [source|self|pi]` — update pi + packages + reconcile pinned git refs
- `pi update --extensions` — packages only
- `pi update --self` — pi only (platform-specific)
- `pi update --self --force` — reinstall even if current
- `pi list` — list installed packages
- `pi config` — enable/disable package resources

---

## 3. PROVIDER & MODEL SYSTEM

### Provider Architecture (`packages/ai/src/providers/`)
- Multi-provider unified API over OpenAI-compatible interface
- 30+ providers implemented: `anthropic.ts`, `openai-completions.ts`, `openai-responses.ts`, `openai-codex-responses.ts`, `google.ts`, `google-vertex.ts`, `cloudflare.ts`, `azure-openai-responses.ts`, `mistral.ts`, `amazon-bedrock.ts`, `faux.ts`, `openai-prompt-cache.ts`, etc.
- `simple-options.ts` — simplified config for custom providers
- `transform-messages.ts` — format conversion between provider APIs
- `register-builtins.ts` — built-in provider registration
- Image providers: `openrouter.ts`, `register-builtins.ts`

### 3 OAuth Subscription Providers
- **ChatGPT Plus/Pro (Codex)** — OpenAI subscription, officially OSS-endorsed
- **Claude Pro/Max** — Anthropic subscription, extra usage billing
- **GitHub Copilot** — Enterprise Server domain support

### 28 API Key Providers
Anthropic, OpenAI, Google Gemini, Google Vertex AI, DeepSeek, NVIDIA NIM, Mistral, Groq, Cerebras, xAI, OpenRouter, Vercel AI Gateway, Together AI, Fireworks, Hugging Face, Cloudflare AI Gateway, Cloudflare Workers AI, Azure OpenAI Responses, Ant Ling, ZAI, ZAI Coding Plan (CN), OpenCode Zen, OpenCode Go, Kimi For Coding, MiniMax, MiniMax (CN), Xiaomi MiMo, Xiaomi MiMo Token Plan (CN/AMS/SGP)

### Custom Providers (`~/.pi/agent/models.json`)
- Ollama, vLLM, LM Studio, any OpenAI-compatible server
- `api`: `openai-completions`, `openai-responses`, `anthropic-messages`, `google-generative-language`
- `compat` flags: `supportsDeveloperRole`, `supportsReasoningEffort`
- Provider-level `baseUrl`, `apiKey`, `headers`, `query`
- Model-level `reasoning: true/false`
- Extension-based custom providers (Anthropic passthrough, GitLab Duo)

### OAuth System (`packages/ai/src/utils/oauth/`)
- `device-code.ts` — device code flow
- `pkce.ts` — PKCE authorization code flow
- `anthropic.ts`, `openai-codex.ts`, `oauth-page.ts`

### Model Selection & Thinking
- `/login`, `/logout`, `/model`, `/scoped-models`
- `--provider`, `--model`, `--thinking` CLI flags
- 6 thinking levels: off, minimal, low, medium, high, xhigh
- Custom token budgets per level (`thinkingBudgets` setting)
- `hideThinkingBlock`, `enabledModels` for Ctrl+P cycling
- Model registry: `models.ts`, `models.generated.ts`, `api-registry.ts`
- Image models: `image-models.ts`, `images-api-registry.ts`

---

## 4. BUILT-IN TOOLS (8)

### `read` — Read files with line numbers, image attachment support, pagination (2000 lines / 50KB cap)
### `bash` — Execute shell commands, stdout/stderr/exit code capture, timeout, temp file on truncation
### `edit` — Precise find-and-replace, multi-edit in one call, exact-text matching, non-overlapping enforcement
### `write` — Create/overwrite files, auto-creates parent directories
### `grep` — Ripgrep-backed search, context lines, output modes (content/files_with_matches/count)
### `find` / `ls` — Directory listing, recursive walk, pattern matching, max-depth
### `web_search` — 8 providers (OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini), multi-query, recency filter, domain filter, full content fetch
### `fetch_content` — URL→markdown, YouTube transcripts with frames, GitHub repos, local video frames, Gemini fallback
### `get_search_content` — Retrieve stored content from prior searches

Tools can be configured: `--tools` (allowlist), `--exclude-tools`, `--no-builtin-tools`, `--no-tools`

---

## 5. EXTENSIONS SYSTEM

### Extension Architecture
- TypeScript modules, auto-discovered: `~/.pi/agent/extensions/` (global), `.pi/extensions/` (project, trust-gated)
- CLI: `-e <source>` (path/npm/git), repeatable
- Hot-reload: `/reload`
- Dependencies via `package.json` in extension directory

### Extension API (`ExtensionAPI`)
- `pi.registerTool()` — custom LLM-callable tools
- `pi.registerCommand()` — slash commands
- `pi.on(event, handler)` — 15+ lifecycle events
- `pi.appendEntry()` — session persistence
- `pi.registerCustomModel()` — custom providers
- `pi.setCustomHeader()` / `pi.setCustomFooter()` — UI customization
- `pi.setToolRenderer()` / `pi.setMessageRenderer()` — custom rendering

### Lifecycle Events
- **Resource**: `resource_changed`
- **Session**: `session_start`, `session_end`
- **Agent**: `agent_start`, `agent_end`
- **Model**: `pre_llm_call`, `post_llm_call`
- **Tool**: `tool_call`, `tool_result` (can block/modify)
- **Compaction**: `pre_compact`, `post_compact`, `pre_branch_summary`, `post_branch_summary`
- **UI**: `project_trust`
- **Message**: `user_message`

### Custom UI Components
- Full TUI via `ctx.ui.custom(component)`
- Component interface: `render(width)`, `handleInput(data)`, `wantsKeyRelease`, `invalidate()`
- `Focusable` for IME: `CURSOR_MARKER` zero-width escape, `focused` propagation
- `ctx.ui.select()`, `ctx.ui.confirm()`, `ctx.ui.input()`, `ctx.ui.notify()`

### 75+ Example Extensions (shipped in `examples/extensions/`)

**Security/Permissions:** `confirm-destructive.ts`, `permission-gate.ts`, `protected-paths.ts`, `dirty-repo-guard.ts`, `project-trust.ts`

**Git Workflows:** `git-checkpoint.ts`, `git-merge-and-resolve.ts`, `auto-commit-on-exit.ts`

**Custom Providers:** `custom-provider-anthropic/`, `custom-provider-gitlab-duo/`

**Tool Extensions:** `tools.ts`, `dynamic-tools.ts`, `tool-override.ts`, `bash-spawn-hook.ts`, `inline-bash.ts`, `truncated-tool.ts`, `built-in-tool-renderer.ts`

**UI Customization:** `border-status-editor.ts`, `custom-footer.ts`, `custom-header.ts`, `titlebar-spinner.ts`, `working-indicator.ts`, `status-line.ts`, `model-status.ts`, `mac-system-theme.ts`, `hidden-thinking-label.ts`, `minimal-mode.ts`

**Input/Message:** `input-transform.ts`, `input-transform-streaming.ts`, `message-renderer.ts`, `send-user-message.ts`

**Games (yes, in terminal):** `snake.ts`, `space-invaders.ts`, `tic-tac-toe.ts`, `doom-overlay/` (DOOM in terminal overlay!)

**Sub-agents & Planning:** `subagent/`, `handoff.ts`, `plan-mode/`

**Compaction & Editors:** `custom-compaction.ts`, `trigger-compact.ts`, `rainbow-editor.ts`, `modal-editor.ts`

**Integration & Infrastructure:** `github-issue-autocomplete.ts`, `ssh.ts`, `gondolin/` (tools→micro-VM), `sandbox/`

**State Management:** `bookmark.ts`, `todo.ts`, `preset.ts`, `session-name.ts`

**Other:** `claude-rules.ts`, `event-bus.ts`, `file-trigger.ts`, `notify.ts`, `pirate.ts`, `prompt-customizer.ts`, `provider-payload.ts`, `qna.ts`, `question.ts`, `questionnaire.ts`, `reload-runtime.ts`, `shutdown-command.ts`, `structured-output.ts`, `summarize.ts`, `system-prompt-header.ts`, `timed-confirm.ts`, `widget-placement.ts`, `working-message-test.ts`, `overlay-test.ts`, `overlay-qa-tests.ts`, `hello.ts`, `commands.ts`, `dynamic-resources/`, `interactive-shell.ts`, `with-deps/`, `rpc-demo.ts`, `rpc-extension-ui.ts`

---

## 6. SKILLS SYSTEM

### Standards Compliance
- Implements [Agent Skills standard](https://agentskills.io/specification)
- **Cross-harness compatible** — can load skills from Claude Code, OpenAI Codex, etc.
- Progressive disclosure: only descriptions in context, full SKILL.md loaded on-demand
- Skills exposed as `/skill:name` commands with arguments

### Bundled Skills
- Pi ships with exactly **1** bundled skill: `.pi/skills/add-llm-provider.md` — guides agent on adding new LLM providers
- This is intentional minimalism — the extension system (75+ examples) is Pi's primary extension mechanism
- Skills are installed by users from the ecosystem or created by the agent itself

### Skill Locations
- Global: `~/.pi/agent/skills/`, `~/.agents/skills/`
- Project (trust-gated): `.pi/skills/`, `.agents/skills/`
- Packages: `skills/` dir or `pi.skills` in `package.json`
- Settings: `skills` array with glob patterns
- CLI: `--skill <path>` (repeatable)
- Cross-harness: load `~/.claude/skills`, `~/.codex/skills` via settings

### Discovery Rules
- Direct root `.md` files = individual skills (in `~/.pi/agent/skills/` and `.pi/skills/`)
- Directories with `SKILL.md` discovered recursively (all locations)
- `~/.agents/skills/` and `.agents/skills/`: root `.md` files ignored (dirs only)
- `--no-skills` disables discovery; explicit `--skill` paths still load

### No Bundled MCP
- Pi does **not** ship with a built-in MCP client or server
- MCP servers can be connected via extension or external tools
- The `pi-chat` companion repo handles Slack/chat automation separately

---

## 7. SESSIONS & PERSISTENCE

### Session Storage
- JSONL tree format in `~/.pi/agent/sessions/--<path>--/<timestamp>_<uuid>.jsonl`
- Tree structure via `id`/`parentId` — in-place branching without new files
- Versioned: v1 (linear) → v2 (tree) → v3 (renamed custom role), auto-migrated
- Custom dir via `--session-dir`, `PI_CODING_AGENT_SESSION_DIR`, or `sessionDir` setting

### Session Commands
- `pi -c`/`--continue`, `pi -r`/`--resume`, `pi --no-session` (ephemeral)
- `pi --name`, `pi --session <path|id>`, `pi --fork <path|id>`
- `/resume` — interactive picker (search, sort, filter, rename, delete via `trash` CLI)
- `/tree` — navigate tree (↑↓, Ctrl+O filter, Shift+L label, branch summary on switch)
- `/fork`, `/clone`, `/new`, `/name`, `/session`
- `/export [file]` — HTML export with ANSI→HTML + tool rendering
- `/share` — private GitHub gist with shareable HTML link
- `badlogic/pi-share-hf` — publish to Hugging Face datasets

### Entry Types
`user`, `assistant`, `tool_call`, `tool_result`, `compaction`, `branch_summary`, `custom` (extensions), `model_change`, `thinking_change`, `label`

---

## 8. CONTEXT & COMPACTION

### Context Files
- `AGENTS.md` / `CLAUDE.md`: `~/.pi/agent/AGENTS.md`, parent dirs walking up to git root, cwd
- `--no-context-files` / `-nc` to disable
- `.pi/SYSTEM.md` / `~/.pi/agent/SYSTEM.md` — replace default system prompt
- `APPEND_SYSTEM.md` — append without replacing
- `--system-prompt`, `--append-system-prompt` CLI overrides

### Auto-Compaction
- Triggers: `contextTokens > contextWindow - reserveTokens` (default reserve: 16384)
- Process: find cut point (keepRecentTokens: 20000) → LLM summarize → append CompactionEntry → reload
- Iterative: passes previous summary as context
- Structured format: files read/modified/created, learned conventions, key decisions, tasks
- `/compact [instructions]` for manual trigger
- Extension hooks: `pre_compact`, `post_compact`

### Branch Summarization
- On `/tree` switch away from branch: no summary / default / custom instructions
- Preserves abandoned-branch context at new position
- Extension hooks: `pre_branch_summary`, `post_branch_summary`

### Overflow Handling
- Fallback compaction at hard limits
- Large results saved to temp files
- Output guard (`output-guard.ts`)

---

## 9. TUI — TERMINAL UI

### TUI Library (`packages/tui/`)
- Differential rendering — only changed lines redrawn
- Component system: `render(width)`, `handleInput(data)`, `invalidate()`
- `Focusable` IME support: `CURSOR_MARKER` APC escape, `focused` propagation
- Hardware cursor: `showHardwareCursor` / `PI_HARDWARE_CURSOR=1`
- Built-in components: `Input`, `Editor`, `Select`, `Container`, `Dialog`

### 30+ TUI Components (`modes/interactive/components/`)
- Message rendering: `assistant-message`, `armin` (thinking blocks), `user-message`, `custom-message`, `skill-invocation-message`
- Tool display: `tool-execution`, `bash-execution`, `diff` (syntax-highlighted)
- Compaction: `compaction-summary-message`, `branch-summary-message`
- Selectors: `model-selector`, `session-selector`, `theme-selector`, `thinking-selector`, `oauth-selector`, `extension-selector`, `config-selector`, `settings-selector`, `tree-selector`, `scoped-models-selector`, `show-images-selector`, `user-message-selector`, `trust-selector`
- UI: `footer` (cwd, session, tokens, cost, model), `bordered-loader`, `countdown-timer`, `keybinding-hints`, `login-dialog`, `first-time-setup`, `earendil-announcement`, `dynamic-border`, `visual-truncate`
- Editors: `extension-editor`, `custom-editor`

### Editor Features
- Syntax highlighting (highlight.js), file reference autocomplete (`@`), path autocomplete (Tab)
- Image paste, shell command dispatch (`!`/`!!`), external editor (Ctrl+G)
- Prompt template expansion (`/template`), slash command autocomplete
- Message queue, `editorPaddingX` setting (0-3)

---

## 10. KEYBINDINGS

### Fully Customizable
- `~/.pi/agent/keybindings.json` — namespaced IDs (`tui.editor.cursorUp`)
- Legacy auto-migration from pre-namespaced configs
- `/reload` to apply, `/hotkeys` to display
- Key format: `modifier+key` (ctrl, shift, alt combinable)
- All keyboard chars, function keys, special keys supported, multiple bindings per action

### Categories
- **Editor Cursor**: up/down/left/right, word jump, line start/end, page up/down, jump-to-char
- **Editor Deletion**: char/word forward/backward, to line start/end
- **Input**: submit (Enter), newline (Shift+Enter), tab/autocomplete
- **Navigation**: scroll, page, tree nav, fork, clone
- **UI**: settings, model, session picker
- **Extensions**: custom via `keyHint()` and injected `keybindings` manager

---

## 11. THEMES

- Built-in: `dark`, `light` — auto-detect terminal background on first run
- Custom: `~/.pi/agent/themes/*.json`, `.pi/themes/*.json` (trust-gated), packages, settings
- JSON format with `$schema`, `name`, `vars` (hex/ANSI/named colors)
- Color tokens: primary, secondary, background, foreground, borders, syntax, diffs
- Schema validation, `/settings` → theme selection, `--theme` CLI, `--no-themes`

---

## 12. PROMPT TEMPLATES

- Markdown files with YAML frontmatter, expanded via `/name` in editor
- Frontmatter: `description`, `argument-hint` (`<required>` / `[optional]`)
- Locations: `~/.pi/agent/prompts/`, `.pi/prompts/`, packages, settings
- CLI: `--prompt-template`, `--no-prompt-templates`
- **5 bundled templates**: `cl.md` (changelog), `is.md` (issues), `pr.md` (PR review), `sa.md` (summary), `wr.md` (work review)

---

## 13. PI PACKAGES

### Package System
- Bundle extensions, skills, prompts, themes for npm/git/path distribution
- `pi install <source> [-l]`, `pi remove`, `pi update`, `pi list`, `pi config`
- Sources: npm (`npm:@scope/pkg@1.2.3`), git (`git:github.com/user/repo@v1`), path, URL
- `-l` for project-local (`.pi/settings.json`), default user (`~/.pi/agent/settings.json`)
- `-e` for one-time use without install
- Auto-install missing project packages after trust
- Resource filtering: select specific skills/extensions, exclude by type

---

## 14. SETTINGS SYSTEM

### Architecture
- JSON: `~/.pi/agent/settings.json` (global), `.pi/settings.json` (project, trust-gated)
- Project overrides global — nested objects merged
- Edit directly or use `/settings`

### All Settings by Category

**Model & Thinking:** `defaultProvider`, `defaultModel`, `defaultThinkingLevel`, `hideThinkingBlock`, `thinkingBudgets`, `enabledModels`

**UI & Display:** `theme`, `quietStartup`, `collapseChangelog`, `doubleEscapeAction`, `treeFilterMode`, `editorPaddingX`, `autocompleteMaxVisible`, `showHardwareCursor`

**Trust:** `defaultProjectTrust` (ask/always/never)

**Compaction:** `compaction.enabled`, `compaction.reserveTokens` (16384), `compaction.keepRecentTokens` (20000)

**Branch Summary:** `branchSummary.reserveTokens` (16384), `branchSummary.skipPrompt`

**Retry:** `retry.enabled`, `retry.maxRetries` (3), `retry.baseDelayMs` (2000), `retry.provider.timeoutMs`, `retry.provider.maxRetries` (0), `retry.provider.maxRetryDelayMs` (60000)

**Message Delivery:** `steeringMode`, `followUpMode`, `transport` (auto/sse/websocket/websocket-cached), `httpIdleTimeoutMs` (300000), `websocketConnectTimeoutMs` (15000)

**Terminal & Images:** `terminal.showImages`, `terminal.imageWidthCells` (60), `terminal.clearOnShrink`, `images.autoResize`, `images.blockImages`

**Shell:** `shellPath`, `shellCommandPrefix`, `npmCommand`

**Sessions:** `sessionDir`

**Resources:** `packages`, `extensions`, `skills`, `prompts`, `themes`, `enableSkillCommands`

**Telemetry:** `enableInstallTelemetry` (true), `enableAnalytics` (false)

**Other:** `markdown.codeBlockIndent`, `warnings.anthropicExtraUsage`

---

## 15. SDK — PROGRAMMATIC API

### Core API
- `createAgentSession(options)` — main factory for `AgentSession`
- `SessionManager.inMemory()` / `SessionManager.file()` — persistence backends
- `AuthStorage.create()` — credential management
- `ModelRegistry.create(authStorage)` — provider/model registry
- `ResourceLoader` / `DefaultResourceLoader` — extensions, skills, prompts, themes, context
- Custom `ResourceLoader` for programmatic control

### AgentSession API
- `session.prompt(message, options?)`, `session.subscribe(callback)`, `session.cancel()`
- `session.setModel(model)`, `session.setThinking(level)`, `session.fork()`, `session.compact()`
- Events: message_update, tool_execution_start/end, compaction_start/end, etc.

### 13 SDK Examples
`01-minimal.ts` through `13-session-runtime.ts` covering: basic session, custom model, custom prompt, skills, tools, extensions, context files, prompt templates, auth, settings, sessions, full control, runtime integration

---

## 16. SECURITY & TRUST

### Project Trust
- Interactive prompt on startup for new projects with trust-gated inputs
- Trust saved in `~/.pi/agent/trust.json` (per-folder, inherited from parents)
- `/trust` to save, `--approve`/`-a` to override, `--no-approve`/`-na` to ignore
- Non-interactive: `defaultProjectTrust` fallback (ask/always/never)
- Before trust: only context files + user/global extensions + CLI `-e`
- After trust: project extensions, packages, settings loaded

### Supply-Chain Hardening
- Direct deps pinned to exact versions, `save-exact=true`, `min-release-age=2`
- `package-lock.json` is ground truth; pre-commit blocks accidental changes
- Published CLI includes `npm-shrinkwrap.json` for transitive pinning
- Release smoke tests: isolated npm/Bun installs outside repo
- `--ignore-scripts` on all install paths
- CI: `npm ci --ignore-scripts`, scheduled `npm audit --omit=dev`

### Containerization
- **OpenShell**: policy-controlled sandbox (NVIDIA)
- **Gondolin extension**: tools into local micro-VM while auth stays on host
- **Plain Docker**: full process in container
- No built-in permission system — relies on OS/containerization

---

## 17. SHELL, IMAGES & UTILITIES

### Shell Integration
- `!command` sends to model, `!!command` silent
- Non-interactive `bash -c`, optional timeout
- `shellCommandPrefix` for alias expansion, `shellPath` for custom shell
- `npmCommand` for npm wrappers (e.g., mise exec)

### Image System
- Paste: Ctrl+V / Alt+V, drag into terminal
- Resize: max 2000×2000 (`images.autoResize`), `images.blockImages` to disable
- Kitty/iTerm2 inline protocols (`terminal.showImages`, `terminal.imageWidthCells`)
- Pipeline: `image-convert.ts`, `image-resize.ts`, `image-resize-worker.ts`, `exif-orientation.ts`
- Photon WASM-based processing (`photon.ts`), MIME detection (`mime.ts`)
- Native + image clipboard (`clipboard-native.ts`, `clipboard-image.ts`)

### 30+ Utility Modules
- Core: `event-bus.ts`, `exec.ts`, `bash-executor.ts`, `http-dispatcher.ts`, `footer-data-provider.ts`, `provider-attribution.ts`, `diagnostics.ts`, `timings.ts`, `telemetry.ts`, `experimental.ts`, `defaults.ts`, `resource-loader.ts`, `package-manager.ts`, `project-trust.ts`, `trust-manager.ts`, `session-cwd.ts`, `config.ts`
- Frontend: `ansi.ts`, `syntax-highlight.ts`, `html.ts`, `git.ts`, `shell.ts`, `paths.ts`, `json.ts`, `mime.ts`, `sleep.ts`, `fs-watch.ts`, `frontmatter.ts`, `pi-user-agent.ts`, `open-browser.ts`, `child-process.ts`, `tools-manager.ts`, `deprecation.ts`

---

## 18. SLASH COMMANDS (FULL LIST)

### Session: `/resume`, `/new`, `/name`, `/session`, `/tree`, `/fork`, `/clone`, `/compact`, `/export`, `/share`

### Config: `/login`, `/logout`, `/model`, `/scoped-models`, `/settings`, `/trust`

### Info: `/reload`, `/hotkeys`, `/changelog`, `/quit`

### Skills: `/skill:<name>` + custom extension commands

---

## 19. CLI FLAGS (FULL REFERENCE)

### Mode: (default), `-p`/`--print`, `--mode json`, `--mode rpc`, `--export <in> [out]`

### Model: `--provider`, `--model`, `--api-key`, `--thinking`, `--models`, `--list-models`

### Session: `-c`/`--continue`, `-r`/`--resume`, `--session`, `--fork`, `--session-dir`, `--no-session`, `--name`/`-n`

### Tools: `--tools`/`-t`, `--exclude-tools`/`-xt`, `--no-builtin-tools`/`-nbt`, `--no-tools`/`-nt`

### Resources: `-e`/`--extension`, `--no-extensions`, `--skill`, `--no-skills`, `--prompt-template`, `--no-prompt-templates`, `--theme`, `--no-themes`, `--no-context-files`/`-nc`

### Other: `--system-prompt`, `--append-system-prompt`, `--verbose`, `-a`/`--approve`, `-na`/`--no-approve`, `-h`/`--help`, `-v`/`--version`

### File Args: `@file.md`, `@image.png`, multiple files

---

## 20. TELEMETRY & PLATFORM SUPPORT

### Telemetry
- `enableInstallTelemetry` (default: true) — anonymous version ping
- `PI_SKIP_VERSION_CHECK=1`, `PI_OFFLINE=1` to disable all startup network
- `enableAnalytics` (default: false, opt-in via `PI_EXPERIMENTAL=1`)

### Platforms
- Windows (full TUI, ConPTY, Windows Terminal, `windows-self-update.ts`)
- macOS (full TUI, system theme detection)
- Linux (full TUI, various terminals)
- Termux for Android, Tmux compatibility
- Kitty/iTerm2 image protocols, cursor/IME support

---

## 21. KEY PATHS & ENV VARS

### Paths
| Path | Purpose |
|------|---------|
| `~/.pi/agent/settings.json` | Global settings |
| `~/.pi/agent/auth.json` | OAuth + API keys |
| `~/.pi/agent/trust.json` | Trust decisions |
| `~/.pi/agent/keybindings.json` | Custom keybindings |
| `~/.pi/agent/models.json` | Custom providers |
| `~/.pi/agent/sessions/` | Sessions |
| `~/.pi/agent/extensions/` | Global extensions |
| `~/.pi/agent/skills/` | Global skills |
| `~/.pi/agent/prompts/` | Global templates |
| `~/.pi/agent/themes/` | Global themes |
| `~/.pi/agent/AGENTS.md` | Global context |
| `~/.pi/agent/npm/` | User packages |
| `~/.agents/skills/` | Cross-harness skills |
| `.pi/settings.json` | Project settings |
| `.pi/extensions/` | Project extensions |
| `.pi/skills/` | Project skills |
| `.pi/prompts/` | Project templates |
| `.pi/themes/` | Project themes |
| `.pi/npm/` | Project packages |

### Env Vars
`PI_SKIP_VERSION_CHECK`, `PI_OFFLINE`, `PI_CODING_AGENT_SESSION_DIR`, `PI_HARDWARE_CURSOR`, `PI_ALLOW_LOCKFILE_CHANGE`, `PI_EXPERIMENTAL`

---

## 22. DEVELOPMENT & TESTING

- TypeScript composite project references, `tsconfig.base.json`
- `npm run build`, `npm run check` (lint+format+typecheck+dep checks)
- `./test.sh` (skips LLM tests without API keys), `./pi-test.sh` (run from sources)
- Vitest for all packages, E2E tests with LLM-dependent suites
- CI: `ci.yml`, `build-binaries.yml`, `npm-audit.yml`, `pr-gate.yml`, `issue-gate.yml`, `approve-contributor.yml`

---

## 23. CORRECTED COMPARISON TABLE

| Feature | Hermes | OpenHuman | Pi |
|---------|--------|-----------|-----|
| **Bundled Skills** | **73** (17 categories) | **1** (marketplace) | **1** (`add-llm-provider`) |
| **Optional Skills** | **97** (10 categories) | 0 | 0 (user installs) |
| **Managed Integrations** | 0 | **118+** (Composio) | 0 |
| **Native MCP Client** | ✅ (catalog/picker/circuit-breaker) | ✅ (stdio+HTTP, registry) | ❌ |
| **Native MCP Server** | ✅ (serve/add/remove/test) | ✅ (stdio+HTTP+SSE) | ❌ |
| **MCP OAuth 2.1 PKCE** | ✅ | ❌ | ❌ |
| **MCP Audit/Registry** | ❌ | ✅ (audit+registry) | ❌ |
| **Agent Skills Standard** | ❌ (custom format) | ❌ (metadata-only now) | ✅ (spec-compliant) |
| **Extension System** | Plugins (20+ types) | None | Extensions (75+ examples) |
| **Package Ecosystem** | Skills hub | None | npm/git packages |
| **Memory System** | 8 providers | Memory Tree + 16 domains | None |
| **Voice/STT/TTS** | ✅ | ✅ | ❌ |
| **Desktop Mascot** | ❌ | ✅ (Rive-animated) | ❌ |
| **Messaging Gateway** | 25 platforms | 17 platforms | None (pi-chat repo) |
| **Wallet/Web3** | ❌ | ✅ (BTC/ETH/SOL/TRON) | ❌ |
| **Subconscious/Background** | ❌ | ✅ (subconscious + dreaming) | ❌ |
| **Cron/Scheduling** | ✅ | ✅ | ❌ |
| **Browser/Computer Use** | ✅ (CDP + macOS CUA) | ✅ (CEF + mouse/kb) | ❌ |
| **Model Providers** | 30+ | Hint-routed (managed) | **31** (3 OAuth + 28 API) |
| **Custom Providers** | Plugin-based | Config TOML | **JSON config** (Ollama/vLLM) |
| **SDK** | ❌ | ❌ | ✅ `AgentSession` |
| **Supply-Chain** | ❌ | ❌ | ✅ shrinkwrap + audit |
| **Total Skills (bundled+opt)** | **170** | **1** (+118 integrations) | **1** (+ecosystem) |

---

End of atomic specification (v2, corrected).