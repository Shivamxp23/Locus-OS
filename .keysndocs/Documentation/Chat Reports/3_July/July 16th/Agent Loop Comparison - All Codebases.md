# Agent Loop Comparison — Atomic Detail

> **Methodology**: Every claim below is grounded in actual source code. Pi Agent from `agent-loop.ts`/`agent.ts`, Hermes from `conversation_loop.py`/`turn_context.py`/`turn_finalizer.py`/`background_review.py`/`memory_manager.py`, OpenHuman from `tool_loop.rs`/`engine/core.rs`/`subconscious/engine.rs`, and Locus from the designed spec.

---

## 1. LOOP ARCHITECTURE

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Language** | TypeScript | Python | Rust | Python/TypeScript hybrid |
| **Loop type** | Double loop (outer: follow-ups, inner: tool calls + steers) | Single while loop with retry sub-loop | `for iteration in 0..max_iterations` | Double loop (Reactive 12-stage + Proactive Inner) |
| **Entry point** | `runAgentLoop()` → `runLoop()` | `run_conversation()` | `run_turn_engine()` | `reactive_loop()` + `proactive_loop()` |
| **Concurrency model** | `async/await`, single-threaded event loop | Threading + `ThreadPoolExecutor` for background work | `tokio` async runtime, multi-threaded | `async.gather` for parallel retrieval, `APScheduler` for cron |
| **Lines of core loop** | ~270 lines (`agent-loop.ts`) | ~4,246 lines (`conversation_loop.py`) | ~784 lines (`core.rs`) + ~384 lines (`tool_loop.rs`) | ~12 stages, ~600 lines designed |
| **Stateful?** | Yes — `Agent` class holds `_state`, queues | Yes — `AIAgent` instance, heavy mutation | Yes — `EngineState`, `RepeatFailureGuard`, `TurnCost` | Yes — `CURRENT_STATE`, memory tri-stack, user_identity |
| **User-triggered loop** | ✅ | ✅ | ✅ | ✅ (Reactive Loop) |
| **Self-triggered loop** | ❌ | ❌ | ✅ (`SubconsciousEngine`) | ✅ (Proactive Inner Loop every 90 min) |

---

## 2. PRE-TURN SETUP (What happens before the first LLM call)

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Setup function** | `createContextSnapshot()` inline | `build_turn_context()` (~470 lines) | `observer.before_dispatch()` | Stages 0-3 (Intake → Injection Filter → Query Router → State Injection) |
| **Message sanitization** | `convertToLlm()` filter (user/assistant/toolResult) | Surrogate stripping, non-ASCII cleanup, tool-call argument repair, message-alternation repair | Image placeholder rehydration, multimodal preparation | Prompt injection filter (regex + optional semantic) |
| **System prompt** | Static `systemPrompt` string from options | Restored from SQLite session DB (prefix-cache aware) or rebuilt; persisted back | Not explicitly shown in loop (set at agent init) | SOUL.md preamble + mode-aware instruction, rebuilt per turn |
| **Memory prefetch** | ❌ None | ✅ `MemoryManager.prefetch_all()` → injected into user message via `<memory-context>` fence | ✅ Memory retrieval via `MemoryClientRef` (30 chunks max) | ✅ Parallel 4-source retrieval (PageIndex + PG + Neo4j + Web) |
| **Plugin hooks** | ❌ None | ✅ `pre_llm_call` plugin hook, `on_session_start` hook | ❌ Not at this layer | ❌ Not plugin-based, but Extension API hooks planned |
| **Context compression** | ❌ Not at this layer | ✅ Preflight compression (`context_compressor`) when history too large | ✅ `trim_chat_messages_to_budget()` token budget trimming | ✅ Headroom CCR compression (60-95% reduction) |
| **Intent classification** | ❌ None | ❌ None (all messages treated as coding/general) | ❌ None | ✅ DeepSeek V4 Flash classifier → 12 intent types |
| **User state injection** | ❌ None | ❌ None | ❌ None | ✅ CURRENT_STATE fetch (DCS, mode, faction health, alerts) |
| **Credits/billing check** | ❌ Not at this layer | ✅ `seed_credits_at_session_start()`, Nous rate guard | ❌ Not at this layer | ❌ Token budget check (but in proactive loop) |

---

## 3. THE CORE LOOP (Per-iteration flow)

### 3a. Iteration Control

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Max iterations** | No explicit cap (loops until no tool calls or follow-ups) | `max_iterations` (configurable) + `IterationBudget` with grace call | `max_tool_iterations` (default 10, extended 50) | No iteration cap (single-pass pipeline, not iterative) |
| **Budget system** | No budget | `IterationBudget` with `consume()`, `refund()`, grace call mechanism | Default 10, Extended 50, hard caps | Token budget per day for proactive loop |
| **Interrupt handling** | `AbortSignal` propagated through `signal` parameter | `_interrupt_requested` flag checked each iteration | Stop hooks (`StopDecision::Continue/Stop`) checked before each LLM call | Not iteration-based; single-pass |
| **Loop termination** | When no tool calls + no steering + no follow-up messages | When budget exhausted, interrupted, or final response produced | When no tool calls (final text), circuit breaker trips, or cap hit | After Stage 12 (single pass) |

### 3b. LLM Call

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Streaming** | `streamAssistantResponse()` via configurable `streamFn` | Always streaming (with fallback to non-streaming for mocks/ACP) | Streaming via `delta_tx` channel + `ProgressReporter` | Streaming for Generator output only |
| **Model selection** | Single model per agent, configurable | Single model + automatic failover to fallback provider | Single model per turn, provider abstraction with `reliable.rs` failover | DeepSeek V4 Flash for most calls; Gemini 2.5 Pro for Sunday synthesis |
| **Context transform** | Optional `transformContext` callback before LLM | Inline: Anthropic cache control, thinking-only turn dropping, whitespace normalization | `ContextGuard` check + `trim_chat_messages_to_budget` | Context Forge 800-token 6-layer assembly |
| **API key resolution** | Optional `getApiKey` callback per-provider | Inline credential management, Nous portal refresh | `AuthService` + `APP_SESSION_PROVIDER` | Provider-level config |
| **Error handling** | `stopReason === "error"` → emit events, return | 3-retry loop with jittered backoff, error classification (`classify_api_error`), fallback activation | `Result<>` propagation, transient vs permanent error classification | Single-call, errors logged to `brain_errors` |
| **Cache optimization** | ❌ None | ✅ Anthropic prompt caching (`cache_control` breakpoints), prefix-cache-aware system prompt persistence | ❌ Not at this layer | ❌ Not at this layer (Headroom CCR caches compressed representations) |

### 3c. Tool Execution

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Execution mode** | Parallel by default, sequential if any tool has `executionMode: "sequential"` | Sequential within single API call (tools processed one at a time in the response) | Sequential within iteration, parallel in `spawn_parallel_agents` for subagents | No tool calls in reactive loop (Locus delegates coding, uses structured retrieval) |
| **Tool preparation** | `prepareToolCall()` → `beforeToolCall` hook → validation | `handle_function_call()` with approval gates | `ToolSource.execute()` with `ToolPolicy` check | N/A — special routing replaces tool calls |
| **Tool result handling** | `afterToolCall` hook → `FinalizedToolCallOutcome` | Tool result appended to messages, steer drain injected into tool results | Tool result appended to history | N/A |
| **Approval/Safety** | `beforeToolCall` can intercept and reject | Inline approval flow (CLI/TUI prompts) | `ApprovalGate` (process-global), `ToolPolicy` (whitelist/filter per agent) | N/A |
| **Tool visibility** | All tools visible unless filtered by config | All registered tools visible | `visible_tool_names` whitelist + `extra_tools` per-turn splice | N/A |

---

## 4. CIRCUIT BREAKERS & SAFETY

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Repeat failure detection** | `shouldStopAfterTurn()` callback (configurable) | ❌ No repeat-failure guard | ✅ `RepeatFailureGuard`: same (tool, args) fails 3× → halt with root cause | ❌ Not needed (single-pass) |
| **No-progress detection** | ❌ None | ❌ None | ✅ `NO_PROGRESS_FAILURE_THRESHOLD` (6 back-to-back failures) → halt | ❌ Not needed (single-pass) |
| **Repeat output detection** | ❌ None | ❌ None | ✅ `RepeatOutputGuard`: identical output 4× → halt | ❌ Not needed (single-pass) |
| **Hard policy rejection** | ❌ None | ❌ None | ✅ `HardReject::Blocked/Denied`: halt on first verbatim repeat of security-blocked call | ✅ Prompt injection filter (Stage 1) |
| **Anti-hallucination** | ❌ None | ❌ None | ❌ None | ✅ Post-generation validation: verify proper nouns against context (Stage 10) |
| **Context exhaustion** | ❌ None | ✅ Context compressor triggers when too large | ✅ `ContextGuard::ContextExhausted` when >threshold% full | ✅ Context Forge 800-token hard cap |
| **Cost tracking** | `EMPTY_USAGE` placeholder | Usage tracking via `normalize_usage` + `estimate_usage_cost` | `TurnCost` tracker with per-call and cumulative USD | Token budget with daily caps |

---

## 5. STEERING & MESSAGE INJECTION

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Mid-turn steering** | ✅ `steeringQueue` with drain modes ("one-at-a-time" / "all") | ✅ `_drain_pending_steer()` — injected into last tool message pre-API-call | ✅ `RunQueue` with steer + collect injection at pre-dispatch boundary | ❌ Single-pass, no mid-turn injection |
| **Follow-up messages** | ✅ `followUpQueue` — drained after agent would stop, re-enters outer loop | ❌ Single-turn only (new `run_conversation` call per user message) | ❌ New `run_turn_engine` call per turn | ❌ Single-pass per message |
| **Queue modes** | "one-at-a-time" (default) or "all" | N/A (single pending steer string) | N/A (all pending steers drained at once) | N/A |

---

## 6. POST-TURN FINALIZATION

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Finalization function** | `emit({ type: "agent_end" })` events | `finalize_turn()` (~429 lines) | `TurnEngineOutcome` return + `TurnObserver::after_dispatch` | Stage 12: Post-Turn Learning Cycle (async, non-blocking) |
| **Session persistence** | ❌ Not at this layer | ✅ `_persist_session()` → SQLite | ✅ Via session layer | ✅ Behavioral event emitted → PG LISTEN/NOTIFY |
| **Trajectory save** | ❌ Not at this layer | ✅ `_save_trajectory()` → JSONL file | ❌ Not shown | ✅ Conversation turn stored in Memory Tri-Stack |
| **Response transform** | ❌ None | ✅ `transform_llm_output` plugin hook | ❌ None | ✅ Anti-hallucination guard (Stage 10) |
| **Memory sync** | ❌ None | ✅ `MemoryManager.sync_all()` + background memory prefetch for next turn | ❌ Not at this layer | ✅ Neo4j entity extraction, Headroom compression, PageIndex indexing |
| **Background review** | ❌ None | ✅ `spawn_background_review()` → daemon thread with forked agent, reviews conversation for memory + skill updates | ❌ Not at this layer | ✅ Hebbian weight update, reward signal logging, state engine trigger |
| **Budget summary** | ❌ None | ✅ On exhaustion: strips tools, asks model for summary | ✅ `CheckpointStrategy` produces tool-call digest summary | ❌ Not needed (single-pass) |
| **User feedback** | ❌ None | ❌ None (skill review is background only) | ❌ None | ✅ 👍/👎 inline buttons → reward signals → STDP bonus |

---

## 7. MEMORY & LEARNING

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Memory system** | ❌ None (stateless per-session) | ✅ `MemoryManager` with pluggable `MemoryProvider`s (single external + optional built-in) | ✅ `MemoryClientRef` with memory tree, sync, chunks | ✅ Memory Tri-Stack: Neo4j + Headroom CCR + PageIndex |
| **Memory injection** | N/A | `<memory-context>` fence tags injected into user message, with `StreamingContextScrubber` for display | Memory chunks retrieved before subconscious tick | Context Forge Layer 4 (Graph) + Layer 5 (Retrieval) |
| **Background learning** | ❌ None | ✅ Memory review + skill review in daemon thread after each turn | ✅ Subconscious engine (periodic tick with scratchpad) | ✅ Hebbian weight updates, rolling profile updates, reward model training |
| **Skill system** | ❌ None (extensions are static) | ✅ Dynamic skill library with class-level skills, SKILL.md, references, templates, scripts | ❌ Not at this layer | ✅ Locus-SKILL (.md + optional scripts), extensible |
| **Self-improvement** | ❌ None | ✅ Skill review creates/updates skills based on conversation learnings | ✅ Subconscious scratchpad maintained by agent | ✅ Pattern Engine → rolling user_identity updates, Wants Engine |

---

## 8. PROACTIVE / BACKGROUND LOOPS

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Background loop exists?** | ❌ | ✅ (daemon thread for memory/skill review per turn) | ✅ `SubconsciousEngine` (periodic, configurable interval) | ✅ Inner Loop (every 90 min, deep at 03:00, Sunday synthesis) |
| **Trigger** | N/A | Post-turn (automatic) | Timer-based (configurable minutes) | APScheduler cron |
| **Scope** | N/A | Review just-completed conversation for memory + skill updates | Full agent turn with tool access + scratchpad + memory context | Thinks ABOUT the user (not TO the user) |
| **Tools available** | N/A | Memory + skill management only (whitelist) | Full tool access with `SubconsciousTainted` security origin | No tools — observation generation only |
| **Safety** | N/A | Forked agent, no main conversation mutation | `tick_lock` prevents overlapping, 30-min hard timeout, tainted origin for external content | Budget check, deduplication, reward model gate |
| **Output** | N/A | Memory writes + skill updates (silent) | Scratchpad updates | Observations → routed to Telegram/queue/store based on severity |
| **Deduplication** | N/A | ❌ No dedup | ❌ Not shown | ✅ Cosine similarity > 0.85 → suppress |

---

## 9. CONTEXT MANAGEMENT

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Context strategy** | Full message history, optional `transformContext` callback | Full history + preflight compression + per-call Anthropic cache control | Token budget trimming per iteration + context guard utilization check | 800-token Context Forge with 6 fixed layers |
| **Compression** | External (via `transformContext` callback) | `context_compressor` (preflight), message-sequence repair | `trim_chat_messages_to_budget()` — removes oldest messages | Headroom CCR (algorithmic, not LLM-based) + LOCUS_SHORTHAND encoding |
| **Cache awareness** | ❌ None | ✅ Anthropic prompt caching (prefix-stable system prompt, cache_control breakpoints) | ❌ None | ✅ Compressed representations cached for future queries |
| **Budget** | Unlimited (relies on model's context window) | `estimate_request_tokens_rough()` monitoring + compression trigger | Hard context window from `effective_context_window` | Hard 800-token cap for context assembly |
| **Mode-awareness** | ❌ None | ❌ None | ❌ None | ✅ DCS-driven mode (SURVIVAL → PEAK) changes tone, response length, task suggestions |

---

## 10. STREAMING & EVENT SYSTEM

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Event model** | `AgentEvent` tagged union (agent_start, turn_start, message_start, message_update, message_end, tool_execution_start/end, turn_end, agent_end) | `step_callback` + `emit_status` + `stream_callback` for TTS | `ProgressReporter` trait (TurnStarted, IterationStarted, CostUpdated, Delta forwarding) | No event stream (pipeline, not iterative) |
| **Streaming** | `EventStream<AgentEvent>` with async iterator | Chunk-based streaming to consumers (TUI, TTS, gateway) | `tokio::sync::mpsc::Sender<String>` delta channel | Direct response delivery |
| **Consumer model** | Subscribe listeners via `agent.subscribe()` | Direct callbacks + consumer list (`_has_stream_consumers()`) | `on_delta` sender + `ProgressReporter::make_stream_sink` | Telegram/TUI/MCP delivery |

---

## 11. SUBAGENT / DELEGATION

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **Subagent support** | ❌ Not in agent loop (handled at harness level) | ✅ `delegate_tool` spawns forked agent in daemon thread | ✅ `spawn_parallel_agents` (up to N concurrent subagents with `subagent_runner`) | ✅ Harness delegation (coding → external agent) |
| **Subagent isolation** | N/A | Forked `AIAgent` with tool whitelist | Separate `run_inner_loop` with own `RepeatFailureGuard`, `VirtualTodo` tracking | Process-level: spawns Antigravity/Claude Code/OpenCode subprocess |
| **Spawn depth** | N/A | Configurable nesting | `SpawnDepthGuard` context (max depth enforcement) | Single delegation (no nesting) |

---

## 12. ERROR HANDLING DETAIL

| Dimension | Pi Agent | Hermes Agent | OpenHuman | Locus |
|-----------|----------|-------------|-----------|-------|
| **API errors** | `stopReason === "error"` → emit, return | `classify_api_error()` → `FailoverReason` enum, 3 retries with jittered backoff, fallback activation, rate limit guard | `Result<>` propagation, transient (rate-limited/upstream-unhealthy) vs permanent classification | Log to `brain_errors`, severity-based |
| **Empty responses** | Handled by event system | Truncation detection, continuation prompt, partial stream stub handling | Empty-text-no-tools → degenerate response detection | Anti-hallucination guard catches empty context |
| **Tool failures** | Via `afterToolCall` callback | Tool result appended as error, retried by model | `RepeatFailureGuard` + `RepeatOutputGuard` → root-cause halt | N/A (no tool calls in main loop) |
| **Provider failover** | ❌ None | ✅ `_try_activate_fallback()` → switches provider mid-turn | ✅ `reliable.rs` multi-provider failover with retry chain | ❌ Single provider per call |

---

## 13. FUNDAMENTAL PARADIGM COMPARISON

```
┌─────────────────────────────────────────────────────────────────────────┐
│                                                                         │
│  Pi Agent:     TOOL CALLING LOOP                                        │
│  ─────────                                                              │
│  User msg → [LLM → tools → LLM → tools → ... → final text]            │
│  Simple, clean, extensible. No memory, no learning, no state.           │
│  Designed for: coding agents, general-purpose tool use.                 │
│                                                                         │
│  Hermes Agent: ENTERPRISE CODING AGENT LOOP                             │
│  ─────────────                                                          │
│  User msg → [setup (470 lines) → retry(LLM → tools) → finalize]       │
│  Heavy: session persistence, prompt caching, memory, skill review,      │
│  failover, compression, TTS, kanban, credits, plugins.                  │
│  Designed for: production coding assistant with memory and learning.     │
│                                                                         │
│  OpenHuman:    AGENT TURN ENGINE                                        │
│  ──────────                                                             │
│  User msg → [stop hooks → context guard → LLM → parse → tools →       │
│              circuit breakers → checkpoint] + SubconsciousEngine        │
│  Safety-first: circuit breakers, policy gates, approval flow,           │
│  cost tracking, spawn-depth limits, tainted-origin isolation.           │
│  Designed for: autonomous agent with safety rails and background mind.  │
│                                                                         │
│  Locus:        COGNITIVE PIPELINE                                       │
│  ──────                                                                 │
│  User msg → [filter → classify → state → retrieve → compress →         │
│              forge → route → generate → validate → deliver → learn]    │
│  + Inner Loop (proactive, every 90 min)                                 │
│  Data-first: every response grounded in real data. Never iterates on    │
│  tool calls. Delegates coding. Learns from every interaction.           │
│  Designed for: personal cognitive operating system for one human.        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 14. WHAT LOCUS STEALS FROM EACH

### From Pi Agent (TypeScript, clean architecture)
| Feature | Pi Source | Locus Application |
|---------|----------|-------------------|
| Event stream model | `EventStream<AgentEvent>` in `agent-loop.ts` | Adopt for lifecycle events (turn_start, response_delivered, etc.) |
| Queue-based steering | `steeringQueue` / `followUpQueue` | Adapt for queued Inner Loop observations |
| Configurable `transformContext` | `config.transformContext` callback | Locus equivalent: Context Forge as a composable pipeline |
| Clean tool execution | `executeToolCalls()` with prepare/execute/finalize | Adapt for harness delegation (prepare → select → delegate → monitor) |
| `prepareNextTurn` hook | Allows context/model swap between turns | Use for mode-aware model selection between turns |
| `shouldStopAfterTurn` hook | Configurable termination logic | Use for anti-hallucination gate as stop condition |

### From Hermes Agent (Python, production-hardened)
| Feature | Hermes Source | Locus Application |
|---------|--------------|-------------------|
| `MemoryManager` architecture | Pluggable `MemoryProvider`s with single-external-provider rule | Direct steal: Locus memory interface pattern with swappable providers (mem0, supermemory, etc.) |
| Background skill review | `spawn_background_review()` + review prompts | Adapt for post-turn learning cycle (Stage 12) |
| `<memory-context>` fencing | `StreamingContextScrubber` for clean display | Adapt for Context Forge layer fencing |
| System prompt persistence | SQLite session DB → prefix-cache reuse | Adapt for SOUL.md persistence across sessions |
| `build_turn_context()` pattern | 470-line prologue extracted to dedicated module | Locus equivalent: Stages 0-3 as separate functions |
| `finalize_turn()` pattern | Post-loop finalization extracted to module | Locus equivalent: Stage 12 as separate async module |
| `TurnRetryState` | Retry state tracking within a turn | Adapt for API call retries to DeepSeek/providers |
| Prompt caching | Anthropic `cache_control` breakpoints | Adapt for KV cache stability with local providers |
| Plugin hook system | `pre_llm_call`, `pre_api_request`, `on_session_start` | Adapt for Extension API hooks in Locus |

### From OpenHuman (Rust, safety-first)
| Feature | OpenHuman Source | Locus Application |
|---------|-----------------|-------------------|
| `RepeatFailureGuard` | Per-(tool, args) failure counting with thresholds | Adapt for harness delegation failure detection |
| `RepeatOutputGuard` | Hash-based identical-output detection | Adapt for Inner Loop observation deduplication |
| `SubconsciousEngine` | Periodic background agent with scratchpad + memory | **Direct architectural steal** for Locus Inner Loop |
| `tick_origin_source()` taint tracking | `SubconsciousTainted` origin for external content | Adapt for data-source provenance in Context Forge |
| `ContextGuard` | Utilization-based context window management | Inform Context Forge budget enforcement |
| `TurnCost` tracking | Per-call and cumulative USD cost | Direct steal for token budget management |
| `ToolPolicy` trait | Per-agent tool filtering interface | Adapt for harness capability filtering |
| Stop hooks | `StopDecision::Continue/Stop` per-iteration check | Adapt for anti-hallucination gate |
| Spawn depth context | `SpawnDepthGuard` prevents infinite nesting | Adapt for harness delegation depth limits |
| `ProgressReporter` trait | Lifecycle events + streaming progress | Adapt for Locus stage-level progress reporting |

---

## 15. KEY ARCHITECTURAL INNOVATIONS UNIQUE TO EACH

### Pi Only
- **Double-loop with follow-ups**: Outer loop re-enters when follow-up messages arrive after the agent would otherwise stop. Neither Hermes nor OpenHuman has this.
- **Queue drain modes**: "one-at-a-time" vs "all" for steering messages. Elegant control over how injected messages are processed.

### Hermes Only
- **Prompt caching awareness**: Entire system designed around Anthropic prefix caching — system prompt persisted to SQLite, rebuilt identically across turns.
- **Skill review as learning**: After every turn, a forked agent reviews the conversation for skill creation/updates. No other codebase has an active self-improvement loop at the skill level.
- **Plugin architecture**: Hooks at multiple points (session_start, pre_llm_call, pre_api_request, transform_llm_output). Most extensible for third-party integrations.

### OpenHuman Only
- **Triple circuit breaker**: RepeatFailureGuard + RepeatOutputGuard + hard policy reject detection. The most robust runaway prevention of any codebase.
- **Subconscious engine**: True background cognition with scratchpad maintenance, memory retrieval, situation reports. Only codebase with an independent thinking loop.
- **Taint tracking**: `SubconsciousTainted` origin means the subconscious agent's tool access is restricted when processing third-party content. Security-by-design.

### Locus Only
- **Intent classification pre-routing**: 12 intent types with source routing matrix. No other codebase classifies intent before retrieval.
- **Mode-aware generation**: DCS-driven tone (SURVIVAL → PEAK). Response style changes based on user's psychological state.
- **Context Forge**: Fixed 800-token 6-layer assembly with budget enforcement. Other codebases have unbounded context growth.
- **Anti-hallucination guard**: Post-generation validation against retrieved context. No other codebase validates LLM output before delivery.
- **Memory Tri-Stack**: Three-layer memory (Neo4j + Headroom CCR + PageIndex) with Hebbian learning. No other codebase has reinforcement learning on memory pathways.
- **Reward model**: 👍/👎 feedback → reward signals → weekly retrain. No other codebase has user feedback driving system behavior.

---

## 16. FLOW COMPARISON (Pseudocode)

### Pi Agent
```
prompt(messages):
  context.messages += messages
  emit(agent_start, turn_start)
  
  OUTER while true:
    INNER while hasToolCalls OR pendingMessages:
      drain pending steers → inject
      response = streamAssistantResponse(context)
      if error → emit, return
      toolCalls = response.filter(toolCall)
      if toolCalls:
        results = executeToolCalls(parallel or sequential)
        context.messages += results
      emit(turn_end)
      if shouldStopAfterTurn → emit(agent_end), return
      pendingMessages = getSteeringMessages()
    
    followUps = getFollowUpMessages()
    if followUps → pendingMessages = followUps, continue
    break
  
  emit(agent_end)
```

### Hermes Agent
```
run_conversation(user_message):
  ctx = build_turn_context(agent, user_message)  # 470 lines of setup
  
  while api_call_count < max_iterations AND budget.remaining > 0:
    if interrupted → break
    budget.consume()
    drain_pending_steer() → inject into last tool message
    
    api_messages = build_api_messages(messages, ctx)
    apply_anthropic_cache_control(api_messages)
    sanitize_surrogates(api_messages)
    
    while retry_count < max_retries:
      try:
        response = interruptible_streaming_api_call(api_kwargs)
        break
      except → classify_error → retry/fallback/fail
    
    (assistant_text, tool_calls) = normalize_response(response)
    messages.append(assistant_message)
    
    if tool_calls:
      for tool in tool_calls:
        result = handle_function_call(tool)
        messages.append(tool_result)
    else:
      final_response = assistant_text
      break
  
  finalize_turn(agent, final_response, messages, ...)
  spawn_background_review(memory_review + skill_review)  # daemon thread
  return result_dict
```

### OpenHuman
```
run_turn_engine(provider, history, tools, max_iterations):
  turn_cost = TurnCost::new()
  failure_guard = RepeatFailureGuard::new()
  repeat_guard = RepeatOutputGuard::new()
  context_guard = ContextGuard::with_context_window(...)
  
  progress.turn_started()
  
  for iteration in 0..max_iterations:
    progress.iteration_started(iteration)
    
    # Stop hooks
    for hook in stop_hooks:
      if hook.check() == Stop → bail
    
    # Context guard
    if context_guard.check() == ContextExhausted → bail
    trim_chat_messages_to_budget(history)
    
    # Pre-dispatch
    observer.before_dispatch(history, tools)
    run_queue.drain_steers() → inject
    
    # Image/multimodal prep
    prepared = prepare_messages_for_provider(history)
    
    # LLM call
    (response_text, tool_calls) = provider.chat(prepared)
    context_guard.update_usage(usage)
    turn_cost.add_call(usage)
    
    if tool_calls.is_empty():
      return TurnEngineOutcome { text: response_text }
    
    # Tool execution
    for (name, args) in tool_calls:
      result = tools.execute(name, args)
      
      # Circuit breakers
      if failure_guard.record(name, args, success) → halt
      if repeat_guard.record(signature) → halt
      
      history.push(tool_result)
    
    observer.after_dispatch(history)
  
  # Iteration cap hit
  summary = checkpoint.produce_summary(tool_digest)
  return TurnEngineOutcome { text: summary, hit_cap: true }
```

### Locus (Designed)
```
reactive_loop(user_message):
  # Stage 0: Intake
  log(user_message, timestamp, channel)
  emit(behavioral_event('user_message'))
  
  # Stage 1: Injection filter
  if regex_blocklist.match(message) → reject, log
  if looks_code_like → semantic_check(message) → reject if injection
  
  # Stage 2: Query Router
  {intent, sources, confidence} = deepseek_classify(message)  # ~50 tokens
  
  # Stage 3: State Injection
  state = fetch_current_state()  # DCS, mode, faction, alerts
  
  # Stage 4: Parallel Retrieval (async.gather)
  results = await gather(
    retriever_pageindex(query),   # pgvector semantic search
    retriever_postgres(intent),    # structured SQL templates
    retriever_neo4j(query),        # graph traversal + Hebbian +0.1
    retriever_web(query) if intent == EXTERNAL_KNOWLEDGE
  )
  if ALL_EMPTY → context = "[NO PERSONAL DATA FOUND]"
  
  # Stage 5: Headroom Compression
  for result in results:
    if is_behavioral → shorthand_encode → CCR_compress
    else → CCR_compress
  
  # Stage 6: Context Forge (800 tokens max)
  context = assemble_layers([
    IDENTITY(80t), TEMPORAL(60t), EVENTS(180t),
    GRAPH(150t), RETRIEVAL(200t), WEB(100t), BUFFER(30t)
  ])
  
  # Stage 7: Special Routing
  if COMMAND → direct handler → skip to delivery
  if CODING → select_harness → delegate → monitor
  if RESEARCH → autoresearch_pipeline → continue
  if TASK_PLANNING → scheduler_algorithm → continue
  
  # Stage 8: Mode-Aware Instruction
  instruction = build_mode_instruction(state.mode)  # SURVIVAL→PEAK
  
  # Stage 9: Generator
  response = deepseek_generate(SOUL.md + instruction + context + query)
  
  # Stage 10: Anti-Hallucination Guard
  if response contains proper_nouns NOT in context → replace with safe msg
  
  # Stage 11: Deliver + Feedback
  deliver(response, channel)
  attach(thumbs_up_down_buttons)
  log(response_metadata)
  
  # Stage 12: Post-Turn Learning (async, non-blocking)
  async:
    memory_write(conversation_turn)     # Neo4j + Headroom + PageIndex
    hebbian_update(traversed_paths)     # +0.1 per traversal
    if thumbs_up → pathway_weights × 1.3  # STDP bonus if < 2min
    if thumbs_down → pathway_weights × 0.7
    state_engine.trigger()              # re-evaluate CURRENT_STATE
    pattern_engine.check()              # rolling profile update


# CONCURRENT — no user input needed
proactive_loop():  # every 90 min, 07:00-00:00
  if daily_token_spend > 80% → skip
  state = fetch_current_state()
  events = compress_recent_events(last_2h)
  pathways = neo4j.top_hebbian(time_of_day)
  
  observations = deepseek_think(ABOUT user, NOT TO user, state, events)
  
  for obs in observations:
    if cosine_similarity(obs, recent_observations) > 0.85 → suppress
    score = reward_model.predict(obs)
    if score < 0.6 → discard
    if score >= 0.8 AND severity HIGH → telegram_send_now(obs)
    elif score >= 0.6 → queue_for_morning_briefing(obs)
    else → store_only(obs)
  
  check_spaced_repetition(approaching_decay_nodes)
  if deep_pass → wants_engine.scan(data_gaps, low_confidence)
```
