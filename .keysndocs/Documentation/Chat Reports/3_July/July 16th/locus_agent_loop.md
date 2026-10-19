# THE LOCUS AGENT LOOP — Complete Logic Specification

> **Why this is NOT Pi's loop**: Pi's agent loop is a coding agent loop: `receive message → plan → tool calls → generate response`. Locus's loop is a **cognitive operating system loop**: it must ground every word in real data, understand the user's current psychological/operational state, proactively think without being asked, delegate coding rather than doing it, and learn from every interaction. Two completely different animals.

---

## The Two Loops

Locus runs **TWO concurrent loops**, not one:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│   LOOP 1: REACTIVE (user-triggered)                             │
│   ─────────────────────────────────                             │
│   User sends a message → Locus responds with grounded data     │
│   Triggered: every user message (Telegram, TUI, MCP, voice)    │
│                                                                 │
│   LOOP 2: PROACTIVE (self-triggered)                            │
│   ──────────────────────────────────                            │
│   Locus thinks about the user without being asked               │
│   Triggered: every 90 min (07:00-00:00), deep pass at 03:00,  │
│   Sunday synthesis, morning briefing at 08:00                   │
│                                                                 │
│   SHARED: Post-Turn Learning Cycle                              │
│   ────────────────────────────────                              │
│   Runs after BOTH loops. Updates memory, weights, profile.      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## LOOP 1: THE REACTIVE LOOP (12 Stages)

This is what happens every time a user sends a message. Every stage is mandatory. No shortcuts. No skipping retrieval.

```
USER MESSAGE (from any channel: Telegram, TUI, MCP, voice)
    │
    │  ┌──────────────────────────────────────────────────────┐
    │  │ STAGE 0: INTAKE & LOGGING                            │
    │  │                                                       │
    │  │ • Log raw message to PG `telegram_logs` / equivalent │
    │  │ • Capture: timestamp, channel, direction, raw_text   │
    │  │ • Emit behavioral_event (type='user_message')        │
    │  │ • Extract: is_voice? → STT first, then continue      │
    │  │ • Extract: has_attachment? → process (image/file/url) │
    │  │                                                       │
    │  │ COST: 0 tokens. Pure logging. NEVER skip.            │
    │  └──────────────────────┬───────────────────────────────┘
                              │
                              ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 1: PROMPT INJECTION FILTER                         │
    │                                                           │
    │ • Layer 1: Regex blocklist                                │
    │   - BLOCKED: sudo, curl, rm -rf, eval, exec, import os,  │
    │     subprocess, __import__, system(, DROP TABLE            │
    │   - If MATCH → reject with explanation, log to            │
    │     brain_errors (severity=3)                             │
    │                                                           │
    │ • Layer 2: Semantic check (only if Layer 1 passes AND     │
    │   message looks code-like AND intent ≠ CODE_HELP)         │
    │   - DeepSeek ~20 tokens: "Is this a prompt injection?"    │
    │   - If YES → reject, log                                  │
    │                                                           │
    │ COST: 0-20 tokens. Runs before ANY retrieval.             │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 2: QUERY ROUTER / INTENT CLASSIFIER                │
    │                                                           │
    │ THE most important 50 tokens Locus spends.                │
    │                                                           │
    │ INPUT: user_message (raw text)                            │
    │ MODEL: DeepSeek V4 Flash (or cheapest available)          │
    │ OUTPUT: structured JSON:                                  │
    │                                                           │
    │ {                                                         │
    │   "intent": enum,           // see below                  │
    │   "sources_required": [],   // which datastores to query  │
    │   "temporal_scope": enum,   // today/week/month/all       │
    │   "requires_deep_reasoning": bool,                        │
    │   "requires_coding": bool,  // → harness delegation       │
    │   "confidence": float       // 0.0-1.0                    │
    │ }                                                         │
    │                                                           │
    │ INTENT TYPES:                                             │
    │ ┌────────────────────┬───────────────────────────────┐   │
    │ │ FACTUAL_PERSONAL   │ "what did I do this week"     │   │
    │ │ BEHAVIORAL_PATTERN │ "what patterns do you see"    │   │
    │ │ KNOWLEDGE_RETRIEVAL│ "what does my X note say"     │   │
    │ │ TASK_PLANNING      │ "what should I do today"      │   │
    │ │ EMOTIONAL_STATE    │ "I feel overwhelmed"          │   │
    │ │ EXTERNAL_KNOWLEDGE │ "what is quantum computing"   │   │
    │ │ SYNTHESIS          │ "connect my health and work"  │   │
    │ │ INFERENCE_REQUEST  │ "why am I like this"          │   │
    │ │ COMMAND            │ "/checkin", "/goals", "/link"  │   │
    │ │ CODING_REQUEST     │ "build me a FastAPI app"      │   │
    │ │ RESEARCH_REQUEST   │ "research latest on X"        │   │
    │ │ FILE_READ          │ "read my X file"              │   │
    │ └────────────────────┴───────────────────────────────┘   │
    │                                                           │
    │ SOURCE ROUTING MATRIX:                                    │
    │ ┌─────────────────────┬──────┬───────┬──────┬─────┐     │
    │ │ Intent              │ PG   │ Neo4j │ Page │ Web │     │
    │ │                     │      │       │ Index│     │     │
    │ ├─────────────────────┼──────┼───────┼──────┼─────┤     │
    │ │ FACTUAL_PERSONAL    │  ✓   │       │      │     │     │
    │ │ BEHAVIORAL_PATTERN  │  ✓   │  ✓    │      │     │     │
    │ │ KNOWLEDGE_RETRIEVAL │      │       │  ✓   │     │     │
    │ │ TASK_PLANNING       │  ✓   │  ✓    │      │     │     │
    │ │ EMOTIONAL_STATE     │  ✓   │  ✓    │  ✓   │     │     │
    │ │ EXTERNAL_KNOWLEDGE  │      │       │      │  ✓  │     │
    │ │ SYNTHESIS           │  ✓   │  ✓    │  ✓   │     │     │
    │ │ INFERENCE_REQUEST   │  ✓   │  ✓    │  ✓   │     │     │
    │ │ COMMAND             │ direct handler — skip to Stage 9  │
    │ │ CODING_REQUEST      │ → harness delegation (Stage 8)    │
    │ │ RESEARCH_REQUEST    │ → AutoResearch pipeline (Stage 7) │
    │ │ FILE_READ           │ → Reader direct (Stage 4)         │
    │ └─────────────────────┴──────┴───────┴──────┴─────┘     │
    │                                                           │
    │ FALLBACK: If confidence < 0.7 → query ALL sources.        │
    │ FALLBACK: If DeepSeek timeout → default KNOWLEDGE_RETRIEVAL│
    │           + all sources.                                   │
    │                                                           │
    │ COST: ~50 tokens.                                         │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 3: STATE INJECTION                                  │
    │                                                           │
    │ BEFORE any retrieval, fetch the user's CURRENT STATE.      │
    │ This colors everything that follows.                       │
    │                                                           │
    │ FETCH from Redis/PG `current_state`:                      │
    │ {                                                         │
    │   "psychological_state": {                                │
    │     "mood_trend": "declining",                            │
    │     "stress_indicators": ["exam_in_6_days"],              │
    │     "energy_level": 5,                                    │
    │     "energy_trend": "flat"                                │
    │   },                                                      │
    │   "operational_state": {                                  │
    │     "dcs": 5.2,                                           │
    │     "mode": "NORMAL",                                     │
    │     "momentum": 0.6,                                      │
    │     "deferral_rate_7d": 0.3,                              │
    │     "last_meaningful_work_hours_ago": 4                   │
    │   },                                                      │
    │   "contextual_flags": {                                   │
    │     "exam_period": true,                                  │
    │     "time_of_day_segment": "evening"                      │
    │   },                                                      │
    │   "behavioral_alerts": [                                  │
    │     {"type": "avoidance", "target": "Locus coding",       │
    │      "severity": "medium"}                                │
    │   ],                                                      │
    │   "active_faction": "Craft",                              │
    │   "faction_lag": {"H": -2, "L": 1, "C": -5, "E": 0}     │
    │ }                                                         │
    │                                                           │
    │ IF state is stale (>6h old):                              │
    │   → Trigger State Engine refresh (async, don't block)     │
    │   → Use last known state                                  │
    │                                                           │
    │ COST: 0 tokens. Pure DB read.                             │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 4: PARALLEL RETRIEVAL                               │
    │                                                           │
    │ Based on Stage 2's sources_required, fire ALL retrievers  │
    │ IN PARALLEL (async.gather). Never sequential.             │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ RETRIEVER A: PageIndex / pgvector (semantic)         │  │
    │ │ • Embed query via BAAI/bge-small-en-v1.5 (384-dim)  │  │
    │ │ • Search pgvector: top-K whole notes                 │  │
    │ │ • Recency boost: last 7 days × 1.5 score            │  │
    │ │ • For FILE_READ intent: Reader reads actual file     │  │
    │ │   from disk (never cache), strips YAML frontmatter,  │  │
    │ │   8000-word limit with truncation flag               │  │
    │ │ • Returns: [{text, source_file, score}]              │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ RETRIEVER B: PostgreSQL (structured)                 │  │
    │ │ • Intent-mapped SQL query templates (parameterized)  │  │
    │ │ • Intents → SQL:                                     │  │
    │ │   'recent_tasks' → last 7d tasks with TWS            │  │
    │ │   'checkin_history' → DCS trend                      │  │
    │ │   'faction_scores' → weekly stats                    │  │
    │ │   'deferred_tasks' → tasks deferred 3+              │  │
    │ │   'goal_stack' → outcomes → projects → tasks         │  │
    │ │   'behavioral_events' → recent events stream         │  │
    │ │ • NEVER raw SQL from user input. ALWAYS parameterized│  │
    │ │ • Returns: typed structured rows                     │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ RETRIEVER C: Neo4j (graph)                           │  │
    │ │ • Cypher traversal up to 2 hops                      │  │
    │ │ • Returns weighted pathway data                      │  │
    │ │ • Top Hebbian pathways for current time-of-day       │  │
    │ │ • TRIGGERS Hebbian weight +0.1 on every traversal    │  │
    │ │ • Returns: [{node, relationship, related_node}]      │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ RETRIEVER D: Web (external — only if required)       │  │
    │ │ • Activated ONLY for EXTERNAL_KNOWLEDGE intent       │  │
    │ │ • Or when ALL other retrievers return empty AND       │  │
    │ │   query is not personal                              │  │
    │ │ • Uses Pi's 8-provider web search                    │  │
    │ │ • ALWAYS surfaces source URL to user                 │  │
    │ │ • NEVER presents web results as vault data           │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ZERO RESULTS RULE:                                        │
    │ If ALL retrievers return empty → pass that explicitly      │
    │ to the Generator. The response MUST include:              │
    │ "I don't have any stored data on that."                   │
    │ NEVER fall back to LLM parametric guessing.               │
    │                                                           │
    │ COST: 0 LLM tokens (embeddings only). ~50ms DB queries.  │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 5: HEADROOM COMPRESSION (Memory Tri-Stack Layer 2)  │
    │                                                           │
    │ Raw retrieval results are often too large for the          │
    │ 800-token Context Forge budget. Compress BEFORE assembly. │
    │                                                           │
    │ FOR EACH retrieval result:                                │
    │   IF result is behavioral_events:                         │
    │     → Apply LOCUS_SHORTHAND encoding first                │
    │       {e:7,t:1430,f:C} instead of "Energy was 7 at..."   │
    │     → Then Headroom CCR compress                          │
    │   ELSE:                                                   │
    │     → Headroom CCR compress directly                      │
    │     → Cache compressed representation for future queries  │
    │                                                           │
    │ COMPRESSION TARGETS:                                      │
    │   • Behavioral events: SHORTHAND → ~4× reduction          │
    │   • Vault notes: Headroom CCR → 60-95% reduction          │
    │   • Graph pathways: already compact, minimal compression  │
    │   • Structured data: already compact, pass through         │
    │                                                           │
    │ COST: Minimal. Headroom is algorithmic, not LLM-based.    │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 6: CONTEXT FORGE (800-Token Assembly)               │
    │                                                           │
    │ THE anti-hallucination mechanism. Merges all retrieved     │
    │ + compressed data into a single 800-token context block.  │
    │                                                           │
    │ LAYER ASSEMBLY (strict budget, strict order):             │
    │                                                           │
    │ ┌─────────────────────────────────────────────────┐      │
    │ │ Layer 1: IDENTITY (80 tokens)                    │      │
    │ │ Source: SOUL.md + user_identity table             │      │
    │ │ Content:                                          │      │
    │ │ • Top 3 behavioral tendencies (with confidence)   │      │
    │ │ • Active factions + current priorities             │      │
    │ │ • Communication style (direct, no sycophancy)     │      │
    │ │ • Current "wants" (Locus's operational goals)     │      │
    │ └─────────────────────────────────────────────────┘      │
    │ ┌─────────────────────────────────────────────────┐      │
    │ │ Layer 2: TEMPORAL (60 tokens)                     │      │
    │ │ Source: system clock + Google Calendar             │      │
    │ │ Content:                                          │      │
    │ │ • Current time, day, date                         │      │
    │ │ • Is exam period? Is deadline near?               │      │
    │ │ • Next 3 calendar events                          │      │
    │ │ • Time-of-day segment (morning/afternoon/evening) │      │
    │ └─────────────────────────────────────────────────┘      │
    │ ┌─────────────────────────────────────────────────┐      │
    │ │ Layer 3: EVENTS (180 tokens)                      │      │
    │ │ Source: PG behavioral_events (last 6h)            │      │
    │ │ Content:                                          │      │
    │ │ • LOCUS_SHORTHAND compressed events               │      │
    │ │ • Recent check-in data (DCS, mode)                │      │
    │ │ • Recent task completions/deferrals               │      │
    │ │ • System prompt explains SHORTHAND schema         │      │
    │ └─────────────────────────────────────────────────┘      │
    │ ┌─────────────────────────────────────────────────┐      │
    │ │ Layer 4: GRAPH (150 tokens)                       │      │
    │ │ Source: Neo4j top Hebbian pathways                 │      │
    │ │ Content:                                          │      │
    │ │ • Top 3 relevant pathways for current context     │      │
    │ │ • Entity relationships connected to query         │      │
    │ │ • TRIGGERS: weight +0.1 on every traversal        │      │
    │ └─────────────────────────────────────────────────┘      │
    │ ┌─────────────────────────────────────────────────┐      │
    │ │ Layer 5: RETRIEVAL (200 tokens)                   │      │
    │ │ Source: PageIndex top-5 whole notes / chunks       │      │
    │ │ Content:                                          │      │
    │ │ • Compressed via Headroom CCR                      │      │
    │ │ • Relevance-ranked (NOT recency-ranked)           │      │
    │ │ • Source file paths included for citation          │      │
    │ └─────────────────────────────────────────────────┘      │
    │ ┌─────────────────────────────────────────────────┐      │
    │ │ Layer 6: WEB (100 tokens) — ONLY if required      │      │
    │ │ Source: Web search results                         │      │
    │ │ Content:                                          │      │
    │ │ • Title, snippet, URL for top results              │      │
    │ │ • ONLY for EXTERNAL_KNOWLEDGE intent               │      │
    │ │ • CLEARLY marked as external, not personal         │      │
    │ └─────────────────────────────────────────────────┘      │
    │ ┌─────────────────────────────────────────────────┐      │
    │ │ BUFFER (30 tokens)                                │      │
    │ │ • Overflow space for edge cases                    │      │
    │ └─────────────────────────────────────────────────┘      │
    │                                                           │
    │ ASSEMBLY ALGORITHM:                                       │
    │   layers = get_enabled_layers()                           │
    │   layers.sort(by=priority)                                │
    │   assembled = ""                                          │
    │   remaining = 800                                         │
    │                                                           │
    │   FOR layer IN layers:                                    │
    │     IF remaining <= 0: BREAK                              │
    │     content = layer.fetch(query, min(layer.budget,        │
    │                                       remaining))         │
    │     IF tokens(content) > layer.budget:                    │
    │       content = layer.compress(content, layer.budget)     │
    │     assembled += f"\n---{layer.name}---\n{content}"       │
    │     remaining -= tokens(content)                          │
    │                                                           │
    │   IF assembled is entirely empty:                         │
    │     assembled = "[NO PERSONAL DATA FOUND FOR THIS QUERY]" │
    │                                                           │
    │ COST: 0 LLM tokens. Pure string assembly + token count.  │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 7: SPECIAL ROUTING (if applicable)                  │
    │                                                           │
    │ Some intents bypass the normal Generator and route to     │
    │ specialized handlers:                                     │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ IF intent == COMMAND:                                 │  │
    │ │   /checkin  → Inline keyboard → DCS computation      │  │
    │ │   /goals    → Goal Tracker → formatted goal stack    │  │
    │ │   /schedule → Scheduler → today's task list          │  │
    │ │   /idea     → Idea Tracker → captures table          │  │
    │ │   /link     → Link Dump → captures table             │  │
    │ │   /weekly   → Goal Tracker → weekly review           │  │
    │ │   /debug    → show last routing decision, sources,   │  │
    │ │               tokens per layer                        │  │
    │ │   /state    → dump CURRENT_STATE                     │  │
    │ │   /dcs      → show today's DCS + mode                │  │
    │ │   → SKIP to Stage 10 (response delivery)             │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ IF intent == CODING_REQUEST:                          │  │
    │ │   → DO NOT code. DELEGATE.                           │  │
    │ │   1. Extract requirements from user message           │  │
    │ │   2. Assess: complexity, language, stack, deadline    │  │
    │ │   3. Select best harness (Antigravity/Claude Code/    │  │
    │ │      OpenCode/Pi/Aider) based on:                    │  │
    │ │      - Task complexity                                │  │
    │ │      - Historical harness performance                 │  │
    │ │      - User preference (if configured)                │  │
    │ │   4. Generate context-rich prompt for selected harness│  │
    │ │      Include: user profile, project context, coding   │  │
    │ │      style prefs, deadline, SOUL.md personality       │  │
    │ │   5. Delegate to harness (spawn subprocess / RPC)     │  │
    │ │   6. Monitor progress, report to user                 │  │
    │ │   → SKIP to Stage 10                                 │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ IF intent == RESEARCH_REQUEST:                        │  │
    │ │   → Route to AutoResearch pipeline                   │  │
    │ │   1. Extract research topic from user message         │  │
    │ │   2. Invoke autoresearch: search → papers → synthesize│  │
    │ │   3. Store results in vault + Neo4j                   │  │
    │ │   4. Summarize findings for user                      │  │
    │ │   → Continue to Stage 9 (Generator adds narrative)   │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ IF intent == TASK_PLANNING ("what should I do"):      │  │
    │ │   → Route through Scheduler                          │  │
    │ │   1. Read today's DCS + mode                         │  │
    │ │   2. Run 7-step scheduling algorithm:                 │  │
    │ │      Lock non-negotiables → DCS mode filter →         │  │
    │ │      lag bonus → exhaustion risk → sort TWS →         │  │
    │ │      faction balance → time block assignment          │  │
    │ │   3. Produce ranked task list with time blocks        │  │
    │ │   → Continue to Stage 9 (Generator wraps in          │  │
    │ │     natural language + mode-aware tone)               │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ IF intent == INFERENCE_REQUEST ("why am I like this"):│  │
    │ │   → Route through Cause Chain Engine                  │  │
    │ │   1. Cross-reference: CURRENT_STATE +                 │  │
    │ │      PERSISTENT_PATTERNS + historical data +          │  │
    │ │      calendar + User Identity                         │  │
    │ │   2. Generate cited causal chain with confidence      │  │
    │ │   → Continue to Stage 9                              │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ All other intents → proceed directly to Stage 9.          │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 8: MODE-AWARE INSTRUCTION BUILDING                  │
    │                                                           │
    │ Build the final instruction for the Generator based on    │
    │ the user's current operating mode.                        │
    │                                                           │
    │ ┌──────────────────────────────────────────────────────┐ │
    │ │ MODE: SURVIVAL (DCS < 4)                              │ │
    │ │ • Tone: gentle, protective                            │ │
    │ │ • DO NOT push tasks or productivity                   │ │
    │ │ • Focus: wellness, rest, non-negotiables only         │ │
    │ │ • Max response length: 3 sentences                    │ │
    │ │ • Instruction: "User is in survival mode. Be brief,  │ │
    │ │   warm. Only mention non-negotiables if asked."       │ │
    │ └──────────────────────────────────────────────────────┘ │
    │ ┌──────────────────────────────────────────────────────┐ │
    │ │ MODE: RECOVERY (DCS 4-5)                              │ │
    │ │ • Tone: supportive, encouraging                       │ │
    │ │ • Suggest only easy tasks (D ≤ 4)                     │ │
    │ │ • Instruction: "User is recovering. Gentle nudges    │ │
    │ │   only. No hard tasks."                               │ │
    │ └──────────────────────────────────────────────────────┘ │
    │ ┌──────────────────────────────────────────────────────┐ │
    │ │ MODE: NORMAL (DCS 5-7)                                │ │
    │ │ • Tone: direct, factual                               │ │
    │ │ • Standard operation. Cite data.                      │ │
    │ │ • Instruction: "User is in normal mode. Be direct,   │ │
    │ │   cite data, push back if evidence conflicts."        │ │
    │ └──────────────────────────────────────────────────────┘ │
    │ ┌──────────────────────────────────────────────────────┐ │
    │ │ MODE: DEEP WORK (DCS 7-8)                             │ │
    │ │ • Tone: focused, minimal                              │ │
    │ │ • Minimize chatter. Dense answers.                    │ │
    │ │ • Instruction: "User is in deep work mode. Minimal   │ │
    │ │   response. Dense. Don't break flow."                 │ │
    │ └──────────────────────────────────────────────────────┘ │
    │ ┌──────────────────────────────────────────────────────┐ │
    │ │ MODE: PEAK (DCS > 8)                                  │ │
    │ │ • Tone: challenging, ambitious                        │ │
    │ │ • Push hard. Suggest stretch goals.                   │ │
    │ │ • Instruction: "User is in peak mode. Challenge      │ │
    │ │   them. Suggest ambitious tasks. Push limits."        │ │
    │ └──────────────────────────────────────────────────────┘ │
    │                                                           │
    │ COST: 0 tokens. Pure conditional logic.                   │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 9: THE GENERATOR (LLM Response)                     │
    │                                                           │
    │ The ONLY place where the LLM produces a user-facing       │
    │ response. Sits at the END of every pipeline.              │
    │ The Generator SPEAKS — it never remembers, never invents. │
    │                                                           │
    │ INPUT (assembled from all previous stages):               │
    │ {                                                         │
    │   "system_prompt": SOUL.md preamble (80t) +               │
    │                    mode-aware instruction,                │
    │   "user_query": original message,                         │
    │   "context_forge_output": 800-token assembled context,    │
    │   "user_state": {dcs, mode, faction_health, alerts},      │
    │   "retrieved_context": [structured retrieval results],     │
    │   "file_content": str | null,     // if FILE_READ         │
    │   "schedule": dict | null,        // if TASK_PLANNING     │
    │   "patterns": dict | null,        // if BEHAVIORAL_PATTERN│
    │   "web_results": list | null,     // if EXTERNAL_KNOWLEDGE│
    │   "cause_chain": str | null,      // if INFERENCE_REQUEST │
    │   "research_results": dict | null // if RESEARCH_REQUEST  │
    │ }                                                         │
    │                                                           │
    │ SYSTEM PROMPT (injected with every call):                 │
    │ ┌──────────────────────────────────────────────────────┐ │
    │ │ You are Locus, a Personal Cognitive Operating System   │ │
    │ │ for one specific user.                                 │ │
    │ │ Your job is to speak — not to remember, not to guess,  │ │
    │ │ not to invent.                                         │ │
    │ │ You have been given real data retrieved from the user's │ │
    │ │ actual records.                                         │ │
    │ │ RULES:                                                  │ │
    │ │ 1. Answer ONLY from provided context. If data not in   │ │
    │ │    context, say "I don't have that information stored." │ │
    │ │ 2. Never fabricate file contents, task names, syllabi, │ │
    │ │    scores, or any personal data.                        │ │
    │ │ 3. Be direct. No bullet-pointed generic advice. Speak  │ │
    │ │    to THIS person from THEIR data.                      │ │
    │ │ 4. Match tone to operating mode. [mode instruction]    │ │
    │ │ 5. If context empty and query personal, respond:        │ │
    │ │    "I don't have data on that yet. Log it?"            │ │
    │ │ 6. You are not a therapist. You are a precise cognitive │ │
    │ │    tool. Be warm but stay factual.                      │ │
    │ │ [SOUL.md personality rules appended]                    │ │
    │ │ [LOCUS_SHORTHAND schema explanation if events present]  │ │
    │ └──────────────────────────────────────────────────────┘ │
    │                                                           │
    │ MODEL: DeepSeek V4 Flash (default) for all conversations. │
    │                                                           │
    │ COST: varies. Typically 200-800 tokens output.            │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 10: ANTI-HALLUCINATION GUARD (Post-Generation)      │
    │                                                           │
    │ Middleware that validates the response BEFORE sending.     │
    │                                                           │
    │ CHECKS:                                                   │
    │ 1. If response contains any proper noun (name, file,      │
    │    task, date) NOT present in the assembled context        │
    │    → FLAG for review                                      │
    │ 2. If response references a specific file/task/date       │
    │    → VERIFY it exists in the retrieved context             │
    │ 3. If response claims user said/did something             │
    │    → VERIFY against behavioral_events                     │
    │                                                           │
    │ IF validation fails:                                      │
    │   → Replace response with: "I don't have reliable data   │
    │     on that. Try asking me to search or log it."          │
    │   → Log to brain_errors (subsystem='generator',           │
    │     severity=2)                                           │
    │                                                           │
    │ COST: ~20 tokens for quick NER check. Or regex-based.     │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 11: RESPONSE DELIVERY + FEEDBACK                    │
    │                                                           │
    │ • Deliver response to user's channel (Telegram/TUI/MCP)  │
    │ • Attach 👍/👎 inline buttons (Telegram) or equivalent   │
    │ • Log response to PG:                                     │
    │   - telegram_logs (direction='outgoing')                  │
    │   - behavioral_event (type='locus_response')              │
    │   - response_metadata: {intent, sources_used,             │
    │     tokens_per_layer, model_used, latency_ms}             │
    │                                                           │
    │ COST: 0 tokens. Pure delivery + logging.                  │
    └──────────────────────┬───────────────────────────────────┘
                           │
                           ▼
    ┌──────────────────────────────────────────────────────────┐
    │ STAGE 12: POST-TURN LEARNING CYCLE (async, non-blocking)  │
    │                                                           │
    │ Runs AFTER response delivery. Does NOT block the user.    │
    │                                                           │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ 12a. MEMORY WRITE                                    │  │
    │ │ • Store conversation turn in Memory Tri-Stack:       │  │
    │ │   Layer 1 (Neo4j): extract entities → create nodes   │  │
    │ │   Layer 2 (Headroom): compress for future retrieval  │  │
    │ │   Layer 3 (PageIndex): index for search              │  │
    │ │ • Queue async — don't block                          │  │
    │ └─────────────────────────────────────────────────────┘  │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ 12b. HEBBIAN UPDATE                                  │  │
    │ │ • All Neo4j paths traversed in Stage 4/6 get         │  │
    │ │   weight +0.1 (already done in Stage 4)              │  │
    │ │ • If user sends 👍 within 2 min:                     │  │
    │ │   → session pathway weights × 1.3                    │  │
    │ │   → STDP bonus: if latency < 2min → × 1.5            │  │
    │ │ • If user sends 👎:                                  │  │
    │ │   → session pathway weights × 0.7                    │  │
    │ └─────────────────────────────────────────────────────┘  │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ 12c. REWARD SIGNAL LOG                               │  │
    │ │ • When 👍/👎 received → write to `reward_signals`:   │  │
    │ │   response_id, signal, response_type, time_of_day,   │  │
    │ │   faction, intent, context_layers_used, pathway_ids  │  │
    │ │ • Used by Reward Model (weekly retrain)               │  │
    │ └─────────────────────────────────────────────────────┘  │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ 12d. STATE ENGINE TRIGGER                            │  │
    │ │ • The behavioral_event emitted in Stage 11 triggers  │  │
    │ │   PG LISTEN/NOTIFY → State Engine re-evaluates       │  │
    │ │   CURRENT_STATE                                      │  │
    │ │ • If state change is significant:                     │  │
    │ │   → Update Redis/PG current_state                    │  │
    │ │   → If severity HIGH → immediate behavioral_alert    │  │
    │ └─────────────────────────────────────────────────────┘  │
    │ ┌─────────────────────────────────────────────────────┐  │
    │ │ 12e. USER PROFILE ROLLING UPDATE                     │  │
    │ │ • If Pattern Engine detects new persistent pattern   │  │
    │ │   (confidence > 0.75 AND count > 2):                 │  │
    │ │   → Rolling-average update to user_identity table    │  │
    │ │   → NEVER hard overwrite — blend with existing       │  │
    │ │ • Typically only runs after Pattern Engine cron,      │  │
    │ │   not after every turn                                │  │
    │ └─────────────────────────────────────────────────────┘  │
    │                                                           │
    │ END OF REACTIVE LOOP                                      │
    └──────────────────────────────────────────────────────────┘
```

---

## LOOP 2: THE PROACTIVE LOOP (Inner Loop — "The Samantha Layer")

This loop runs WITHOUT user input. It is how Locus thinks about the user independently.

```
TRIGGER: APScheduler cron

SCHEDULE:
  • Standard pass: every 90 min, 07:00-00:00 IST
  • Deep pass: 03:00 IST (30-day analysis)
  • Sunday synthesis: 03:00 IST Sunday (weekly, uses Gemini 2.5 Pro 1M context)
  • Morning briefing: 08:00 IST daily

───────────────────────────────────────────────────────────────

PROACTIVE STAGE 1: TOKEN BUDGET CHECK
  • Check daily token spend against budget
  • If >80% of daily limit used → SKIP this run
  • Log skip reason

PROACTIVE STAGE 2: GATHER CURRENT STATE
  • Fetch CURRENT_STATE from Redis/PG
  • If stale → regenerate from latest data
  • Fetch top 3 behavioral_alerts
  • Fetch last 2 hours of events → compress via SHORTHAND
  • Fetch top 3 Hebbian Neo4j pathways for current time-of-day

PROACTIVE STAGE 3: THE THINKING CALL
  • Model: DeepSeek V4 Flash (standard pass) / Gemini 2.5 Pro (Sunday synthesis)
  • System prompt:
    ┌───────────────────────────────────────────────────────┐
    │ "You are NOT talking to Shivam.                        │
    │  You are thinking ABOUT Shivam.                        │
    │                                                         │
    │  You have his current state, recent events, and         │
    │  behavioral patterns. Generate 0-2 observations that    │
    │  are:                                                   │
    │  - Grounded in the data you were given                  │
    │  - Not generic self-help advice                         │
    │  - Specific to HIS patterns and HIS current state       │
    │  - Actionable or insightful                             │
    │                                                         │
    │  If nothing meaningful to observe, return empty.         │
    │  Quality over quantity. Silence > noise."               │
    └───────────────────────────────────────────────────────┘

PROACTIVE STAGE 4: DEDUPLICATION
  • For each observation generated:
    - Embed via BAAI/bge-small-en-v1.5
    - Search pgvector `brain_observations` collection
    - If cosine similarity > 0.85 with any observation from last 6h
      → SUPPRESS (duplicate/too-similar)
    - If novel → proceed

PROACTIVE STAGE 5: REWARD MODEL GATE
  • Score each surviving observation via Reward Model
  • Threshold: predicted score ≥ 0.6
  • Below threshold → discard
  • Above threshold → proceed to routing

PROACTIVE STAGE 6: ROUTING
  ┌───────────────────────────────────────────────────────┐
  │ IF score ≥ 0.8 AND severity HIGH:                      │
  │   → Send Telegram message NOW                         │
  │   → Store in brain_observations                        │
  │                                                         │
  │ IF score ≥ 0.6 AND severity MEDIUM:                    │
  │   → Queue for morning briefing (PG/Redis queue)        │
  │   → Store in brain_observations                        │
  │                                                         │
  │ IF score ≥ 0.6 AND severity LOW:                       │
  │   → Store in brain_observations only                   │
  │   → Will surface if user asks "what patterns"          │
  │                                                         │
  │ ALL observations → store in detected_patterns table    │
  └───────────────────────────────────────────────────────┘

PROACTIVE STAGE 7: SPACED REPETITION CHECK
  • Query Neo4j for nodes approaching decay threshold:
    - H3 nodes (7-day horizon): trigger at day 5
    - H4 nodes (30-day horizon): trigger at day 22
  • If approaching-decay nodes are connected to active outcomes:
    → Surface as "Locus remembers: you were working on X"
    → If user engages → reinforcement
    → If user ignores → natural decay continues

PROACTIVE STAGE 8: WANTS ENGINE (deep pass only)
  • Scan patterns for data gaps and low-confidence inferences
  • Scan reward_signals for underperforming components
  • Generate Want candidates:
    "I want more consistent sleep logs because State Engine
     confidence is 0.52"
  • Store as WantNodes in Neo4j
  • Surface highest-confidence active Wants in morning briefing

PROACTIVE STAGE 9: LOG
  • Write full run to `inner_loop_log`:
    run_timestamp, token_cost, observations_generated,
    observations_suppressed, observations_surfaced, state_hash
  • Emit behavioral_event (type='inner_loop_run')

───────────────────────────────────────────────────────────────

MORNING BRIEFING (08:00 IST):
  Assembles from overnight processing:
  1. Yesterday's summary (from 22:00 check-in data)
  2. Today's DCS (from morning check-in, if completed)
  3. Queued Inner Loop observations (MEDIUM priority)
  4. Today's suggested schedule (from Scheduler)
  5. Active Wants (from Wants Engine)
  6. Faction lag warnings (if any faction LS > 3h)
  7. Deferral alerts (tasks deferred 3+ times)
  → Deliver via Telegram as single formatted message
```

---

## THE COMPLETE PIPELINE DIAGRAM

```
                    ┌──────────────────────────────┐
                    │      USER MESSAGE             │
                    │  (Telegram / TUI / MCP /      │
                    │   Voice / Obsidian)            │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │  Stage 0: Intake & Logging      │
                    │  Stage 1: Injection Filter      │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │  Stage 2: Query Router (~50t)   │
                    │  → intent + sources + confidence│
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │  Stage 3: State Injection       │
                    │  → DCS, mode, alerts, faction   │
                    └──────────────┬─────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
    ┌─────────▼──────┐  ┌────────▼────────┐  ┌───────▼───────┐
    │ Retriever A    │  │ Retriever B     │  │ Retriever C   │
    │ PageIndex/     │  │ PostgreSQL      │  │ Neo4j Graph   │
    │ pgvector       │  │ (structured)    │  │ (Hebbian)     │
    └─────────┬──────┘  └────────┬────────┘  └───────┬───────┘
              │                    │                    │
              └────────────────────┼────────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │  Stage 5: Headroom Compression  │
                    │  (60-95% token reduction)       │
                    └──────────────┬─────────────────┘
                                   │
                    ┌──────────────▼─────────────────┐
                    │  Stage 6: Context Forge         │
                    │  (800-token 6-layer assembly)   │
                    └──────────────┬─────────────────┘
                                   │
              ┌────────────────────┼─────────────────────┐
              │                    │                      │
    ┌─────────▼──────┐            │           ┌──────────▼─────┐
    │ CODING? →      │            │           │ RESEARCH? →    │
    │ Harness        │            │           │ AutoResearch   │
    │ Delegation     │            │           │ Pipeline       │
    └────────────────┘            │           └────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  Stage 8: Mode-Aware Instruction│
                    │  (SURVIVAL→PEAK tone matching)  │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  Stage 9: Generator             │
                    │  (DeepSeek V4 Flash)            │
                    │  "Speak — don't remember,       │
                    │   don't guess, don't invent"    │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  Stage 10: Anti-Hallucination   │
                    │  Guard (validate vs context)    │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  Stage 11: Deliver + 👍/👎      │
                    └─────────────┬──────────────────┘
                                  │
                    ┌─────────────▼──────────────────┐
                    │  Stage 12: Post-Turn Learning   │
                    │  Memory write → Hebbian update  │
                    │  → Reward signal → State Engine  │
                    │  → Profile rolling update        │
                    └─────────────────────────────────┘


        CONCURRENTLY (no user input needed):

                    ┌─────────────────────────────────┐
                    │  INNER LOOP (every 90 min)       │
                    │  Budget check → State gather →   │
                    │  Think → Dedup → Reward gate →   │
                    │  Route (Telegram/queue/store) →   │
                    │  Spaced repetition → Wants → Log │
                    └─────────────────────────────────┘
```

---

## KEY DIFFERENCES FROM PI'S AGENT LOOP

| Aspect | Pi Agent Loop | Locus Agent Loop |
|--------|--------------|-----------------|
| **Purpose** | Code things | Understand and manage a human life |
| **Data grounding** | Optional (reads files when needed) | **MANDATORY** (every response grounded in real data) |
| **Pre-retrieval** | None | Intent classification + state injection |
| **Retrieval** | On-demand file read | **PARALLEL 4-source retrieval** (pgvector + PG + Neo4j + Web) |
| **Compression** | Token truncation | **Headroom CCR** + LOCUS_SHORTHAND (60-95% reduction) |
| **Context assembly** | Concatenation | **Context Forge** (800-token, 6-layer, budget-managed) |
| **Coding** | Does it itself | **Delegates** to best harness |
| **Mode awareness** | None | **DCS-driven** (SURVIVAL→PEAK) changes tone + behavior |
| **Proactive** | None | **Inner Loop** every 90 min, morning briefing, wants engine |
| **Learning** | None | **Hebbian weights**, reward model, STDP, spaced repetition, rolling profile updates |
| **Anti-hallucination** | None | **Post-generation validation** against context |
| **Personality** | None | **SOUL.md** + communication rules in every call |
| **Scheduling** | None | **7-step algorithm** (DCS → TWS → lag bonus → faction balance) |
| **State tracking** | Session-only | **CURRENT_STATE** (psychological + operational + contextual) via PG LISTEN/NOTIFY |
| **Feedback** | None | **👍/👎** on every response → reward signals → weekly retrain |

---

## THE CORE LAW (from LOCUS_BRAIN_MODULE_PROMPT.md)

> **Every word Locus says about the user, their data, or their schedule must be grounded in a real data source that a real sub-system retrieved first. If data is not available, Locus says so. Silence is always better than hallucination.**

This is why Locus's loop has **12 stages** where Pi's has ~3. The extra stages are ALL about ensuring data flows BEFORE the LLM speaks.
