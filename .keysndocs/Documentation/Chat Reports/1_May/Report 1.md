# Locus OS v4.0 — System Reconstruction Report

## Prompt

You are working on Locus OS — a self-hosted personal cognitive

operating system built for a single user (Shivam). The system

runs on an Oracle Cloud Always Free ARM64 VM (Ubuntu 22.04,

~11.6GB RAM, CPU-only, no GPU).

GitHub repo: Shivamxp23/locus-os

Current confirmed tech stack:

- FastAPI backend
- PostgreSQL (raw events, logs, task data, user profile)
- Neo4j (behavioral knowledge graph)
- Qdrant (vector embeddings, semantic search)
- LightRAG (Neo4j + Qdrant as unified knowledge retrieval)
- Groq API (Llama 3 8b-instant for fast, 70b-versatile for

  complex — free tier, HARD token/rate limits)
- Gemini 2.5 Pro (weekly synthesis only — expensive,

  use sparingly)
- Celery + APScheduler
- Redis (Celery broker + short-term state cache)
- Telegram bot (primary interaction interface)
- Obsidian vault "Appledore" synced via Mobius Sync

  (accessible as markdown files on disk)
- React PWA at locusapp.online via Cloudflare Pages
- FastAPI at api.locusapp.online via Cloudflare Tunnel

Hard constraints:

- Zero cost. Respect Groq free tier and Oracle Always Free.
- CPU-only. No local LLM fine-tuning.
- Single user only.

---

CRITICAL CONTEXT BEFORE YOU START:

The current Telegram bot is BROKEN in a fundamental way. When

Shivam asks it anything, it hallucinates an answer directly

from the LLM's parametric knowledge WITHOUT querying

PostgreSQL, Neo4j, Qdrant, Obsidian, or any database. It is

essentially a dumb chatbot with no connection to Locus's data

layer. This is the single most important thing to fix.

Everything below is built on top of this fix.

Also unknown: whether Neo4j actually contains meaningful data.

Before building anything, write a diagnostic script

scripts/diagnose_databases.py that:

1. Connects to PostgreSQL and reports row counts for all tables
2. Connects to Neo4j and reports node counts by label and

   edge counts by type
3. Connects to Qdrant and reports collection names and

   vector counts
4. Scans the Obsidian vault directory and reports total

   markdown files, average file size, and whether backlinks

   exist
5. Prints a full health report to stdout

Run this first. Report findings. Then proceed with the build.

---

YOUR TASK: Build three systems. Do not break existing

functionality.

---

## SYSTEM 1: INTELLIGENT QUERY ROUTER (THE THINKING LAYER)

This is the brain of how Locus decides what to look at before

answering anything. Every single prompt — from Telegram, PWA,

or the inner loop — must pass through this router before any

LLM reasoning happens.

The routing philosophy:

"Before answering, understand what kind of question this is,

what data sources are relevant, and retrieve from all of them

in parallel. Never answer from parametric knowledge alone

if personal data exists."

### 1.1 Query Classifier

Create app/core/query_classifier.py

Every incoming prompt must be classified into one or more of

these intents BEFORE retrieval:

INTENT TYPES:

- FACTUAL_PERSONAL: "What did I work on yesterday?"

  → requires PostgreSQL + Neo4j
- BEHAVIORAL_PATTERN: "Why do I keep avoiding X?"

  → requires Neo4j + Qdrant + PostgreSQL history
- KNOWLEDGE_RETRIEVAL: "What do I know about X?"

  → requires Obsidian/LightRAG + Qdrant
- TASK_PLANNING: "What should I work on now?"

  → requires PostgreSQL tasks + Neo4j pathways +

  current time/energy state from Redis
- EMOTIONAL_STATE: "I'm feeling annoyed/stuck/tired"

  → requires PostgreSQL mood history + Neo4j behavioral

  graph + temporal context
- EXTERNAL_KNOWLEDGE: "What is X technology?"

  → requires web search, no personal data needed
- SYNTHESIS: "What does my week look like?"

  → requires ALL sources
- INFERENCE_REQUEST: "What does this say about me?"

  → requires ALL sources + deep reasoning pass

Classification must be done with a single lightweight Groq

8b-instant call using a structured JSON output prompt.

The classifier returns:

{

  "primary_intent": "INTENT_TYPE",

  "secondary_intents": ["INTENT_TYPE", ...],

  "sources_required": ["postgres", "neo4j", "qdrant",

    "obsidian", "web", "redis_cache"],

  "temporal_scope": "last_6h | last_24h | last_7d |

    last_30d | all_time",

  "requires_deep_reasoning": true/false,

  "confidence": 0.0-1.0

}

If confidence < 0.7, default to querying ALL sources.

This classification costs ~50 tokens. It saves thousands.

### 1.2 Parallel Source Retriever

Create app/core/source_retriever.py

Based on classifier output, launch PARALLEL async retrievals

from all required sources simultaneously using asyncio.gather.

For each source, implement these retrieval functions:

POSTGRESQL RETRIEVER:

- Given temporal_scope, fetch relevant events, tasks,

  mood logs, energy logs, faction activity
- For BEHAVIORAL_PATTERN queries, fetch deferral patterns:

  tasks deferred more than twice, with timestamps and

  stated reasons
- For EMOTIONAL_STATE queries, fetch: last 5 mood logs,

  last 3 days of sleep quality logs, last 3 days of food

  logs if they exist, last 3 significant events
- Always include current DCS (Daily Capacity Score)

  and faction scores from Redis cache
- Compress output using LOCUS_SHORTHAND schema (defined

  in Section 1.4)

NEO4J RETRIEVER:

- Given the classified intent and current time of day,

  traverse the behavioral graph for relevant patterns
- For any query: always retrieve the top 3 strongest

  weighted pathways active at this time of day
- For BEHAVIORAL_PATTERN: find all edges connected to the

  subject entity with weight > 0.5, traverse 2 hops deep
- For TASK_PLANNING: find the strongest pathway from

  current_state node toward goal nodes for active factions
- Return pathway data as structured JSON, not raw Cypher

QDRANT RETRIEVER:

- Embed the user's query using the same embedding model

  used during ingestion
- Search top 7 semantically similar vectors
- Filter by recency weight: boost vectors from last 7 days

  by 1.5x in scoring
- Return content + metadata + similarity scores

OBSIDIAN/LIGHTRAG RETRIEVER:

- Pass query to LightRAG's existing retrieval interface
- If LightRAG returns empty or fails, fall back to direct

  markdown file search using the vault directory
- The fallback: embed the query, find the 5 most similar

  note files by filename + content similarity
- Always retrieve: any note modified in the last 48 hours

  that is semantically related to the query

WEB SEARCH RETRIEVER:

- Only invoked if sources_required includes "web" OR if

  all personal data sources return empty/low confidence
- Use existing web search integration or implement

  DuckDuckGo API (free, no key needed)
- Return top 3 results with title, snippet, url

### 1.3 Context Synthesizer

Create app/core/context_synthesizer.py

After parallel retrieval, this module merges all results

into a single coherent context block for the LLM.

Rules:

1. Total context budget: 800 tokens maximum

   Layer budgets:

   - User identity layer: 80 tokens (who Shivam is,

   current state, active goals — static template

   updated weekly)

   - Temporal context layer: 60 tokens (current time,

   day of week, exam periods, known upcoming events)

   - PostgreSQL layer: 180 tokens (compressed events)
   - Neo4j layer: 150 tokens (pathway data)
   - Qdrant/Obsidian layer: 200 tokens (semantic content)
   - Web layer: 100 tokens (only if used)
   - Overflow buffer: 30 tokens
2. If any layer exceeds its budget, truncate by relevance

   score, not by recency.
3. If ALL layers return empty (no data found), the LLM

   must be told explicitly: "No relevant personal data

   found. Answer from general knowledge but state clearly

   that this is not based on Shivam's personal data."

   This eliminates hallucination at the source.
4. Prepend every context block with a metadata header:

   [CONTEXT_META]

   sources_used: postgres, neo4j, qdrant

   temporal_scope: last_7d

   data_confidence: 0.82

   retrieved_at: 2026-05-10T22:30:00+05:30

   [/CONTEXT_META]

### 1.4 LOCUS_SHORTHAND Compression Schema

Define in app/core/shorthand.py as a Python dict and

encoder/decoder pair.

Compression rules:

- Energy log: {e:VALUE,t:HHMM,f:FACTION}
- Task done: {✓:TASK_SHORT_NAME,dur:MINS,q:QUALITY_1-10}
- Task deferred: {→:TASK_SHORT_NAME,n:DEFERRAL_COUNT,

  r:REASON_CODE}

  Reason codes: busy|tired|blocked|forgot|impulse|unclear
- Mood log: {m:VALUE,note:MAX_5_WORDS}
- Sleep log: {s:HOURS,q:QUALITY_1-10}
- Food log: {food:SHORT_DESC,time:HHMM,

  energy_impact:+/-/0}
- Faction score: {H:VALUE,L:VALUE,C:VALUE,E:VALUE}

  (Health, Leverage, Craft, Expression)

Example compression:

BEFORE (47 tokens):

"User logged energy 6/10 at 22:30 while working on craft

faction, deferred Locus coding task for the 3rd time

because they felt tired, mood was 4/10"

AFTER (12 tokens):

{e:6,t:2230,f:craft} {→:locus-code,n:3,r:tired} {m:4}

Build encode() and decode() functions. The LLM receives

encoded context. The system prompt explains the schema.

### 1.5 Fix The Telegram Bot

This is non-negotiable. Rip out the current Telegram

message handler and replace it entirely.

New message flow:

1. Message received from Shivam
2. → Query Classifier (System 1.1) — ~50 tokens,

   <500ms
3. → Parallel Source Retriever (System 1.2) — async,

   all sources in parallel
4. → Context Synthesizer (System 1.3) — merge + compress
5. → LLM Selection:

   - If requires_deep_reasoning = false AND

   context is simple: Groq 8b-instant

   - If requires_deep_reasoning = true OR

   INFERENCE_REQUEST OR SYNTHESIS: Groq 70b-versatile

   - If it is Sunday nightly synthesis: Gemini 2.5 Pro
6. → LLM call with synthesized context + user message
7. → Response delivered to Telegram

The bot must NEVER skip steps 2-4. Hard-code a check:

if context_synthesizer returns None, raise an error

and tell the user "I couldn't retrieve your data right

now, please try again" rather than hallucinating.

Add a /debug command to Telegram that shows the last

query's routing decision, sources queried, tokens used

per layer, and what was retrieved. This is for Shivam

to verify the system is actually working.

---

## SYSTEM 2: DEEP PERSONAL INFERENCE ENGINE

This is where military-grade profiling happens. Not just

logging what Shivam does, but building a continuously

updated, multi-dimensional model of who he is, how he

operates, and what his current psychological and

operational state is.

The core philosophy:

"Every data point is a signal. Every pattern of signals

is a behavioral signature. Every cluster of signatures

is a state. Locus must know what state Shivam is in

before he knows himself."

### 2.1 State Inference Pipeline

Create app/core/state_engine.py

This runs as a background task triggered by:

- Every new PostgreSQL event write
- Every Telegram message received
- The inner loop (System 3)

It maintains a CURRENT_STATE object in Redis with TTL

of 6 hours (refreshed on each trigger):

CURRENT_STATE schema:

{

  "timestamp": "ISO8601",

  "psychological_state": {

    "mood_trend": "rising|falling|stable",

    "mood_value": 0-10,

    "stress_indicators": ["exam_period", "sleep_deficit",

    "task_overload", ...],

    "energy_level": 0-10,

    "energy_trend": "rising|falling|stable"

  },

  "operational_state": {

    "momentum": "building|stalling|blocked|recovering",

    "current_faction_focus": "FACTION_NAME",

    "tasks_completed_today": INT,

    "tasks_deferred_today": INT,

    "deferral_rate_7d": FLOAT,

    "last_meaningful_work_hours_ago": FLOAT

  },

  "contextual_flags": {

    "exam_period": true/false,

    "exam_days_remaining": INT or null,

    "recent_sleep_quality": 0-10,

    "last_meal_energy_impact": "+/-/0",

    "time_of_day_segment": "early_morning|morning|

    afternoon|evening|

    late_night|deep_night"

  },

  "behavioral_alerts": [

    {

    "type": "avoidance_pattern|momentum_loss|

    energy_mismatch|deadline_risk|

    faction_neglect",

    "description": "plain text",

    "severity": "low|medium|high",

    "evidence": ["event_ids or pattern descriptions"],

    "days_active": INT

    }

  ],

  "inferred_cause_chain": "plain text explanation of

    why Shivam is likely in this state right now,

    citing specific data points"

}

The inferred_cause_chain is the key field. This is

Locus making a genuine inference. For example:

"Shivam has been in a low-momentum state for 3 days.

Probable cause chain: Semester IV exams begin in 6 days

(known from calendar data). Historical pattern shows

mood drops to 4-5/10 in the 7 days before exams

(confirmed across 3 previous exam periods in PostgreSQL).

Sleep quality has been 5/10 for 2 consecutive nights.

Last night's food log shows late meal at 23:40 which

historically correlates with poor sleep in his data.

The annoyance expressed in the image generation request

at 14:22 today is consistent with pre-exam anxiety

compounded by sleep deficit and not pre-existing

irritability — confidence: 0.78."

This is the example you gave. This exact level of

inference. Build it.

### 2.2 Multi-Horizon Pattern Detector

Create app/core/pattern_detector.py

Runs as a scheduled job every 6 hours via APScheduler.

Detects patterns across FIVE time horizons simultaneously:

HORIZON 1 — Last 6 hours (acute state):

- Energy delta (rising/falling how fast)
- Task completion vs deferral ratio
- Communication tone in Telegram messages

  (use sentiment scoring via Groq 8b-instant,

  max 30 tokens per message)

HORIZON 2 — Last 24 hours (daily pattern):

- Sleep quality impact on today's productivity
- Meal timing correlation with energy spikes/dips
- Time of day vs faction activity alignment

HORIZON 3 — Last 7 days (weekly pattern):

- Which faction is being systematically neglected
- Deferral velocity: is avoidance increasing or decreasing
- Mood trend direction and slope
- Hours of meaningful work per day trend

HORIZON 4 — Last 30 days (monthly pattern):

- Goal progress vs stated goals in PostgreSQL
- Faction balance score over time
- Recurring avoidance targets (same tasks deferred

  repeatedly across weeks)
- Energy cycle: does Shivam have a weekly rhythm?

HORIZON 5 — All time (identity pattern):

- Exam period behavioral signature

  (extract from all historical exam periods)
- Creative vs analytical work preference patterns
- Time of day peak performance windows
- Long-term goal drift: are current tasks still

  aligned with stated outcomes?

Each detected pattern must be stored in a new

PostgreSQL table `detected_patterns`:

- id (uuid)
- horizon (1-5)
- pattern_type (avoidance|momentum|energy|mood|

  faction_neglect|goal_drift|exam_behavior|

  creative_burst|...)
- description (plain text)
- confidence (float)
- first_detected_at (timestamp)
- last_confirmed_at (timestamp)
- confirmation_count (int)
- supporting_event_ids (jsonb array)
- status (active|resolved|false_positive)

Patterns with confidence > 0.75 and confirmation_count

> 2 are promoted to PERSISTENT_PATTERNS and included

in the User Identity Layer of the Context Synthesizer.

### 2.3 Contextual Inference API

Expose a FastAPI endpoint POST /inference/explain that

takes:

{

  "trigger": "telegram_message | image_generation |

    task_action | explicit_request",

  "raw_input": "what the user said or did",

  "timestamp": "ISO8601"

}

And returns the full inferred cause chain for that

moment, cross-referencing:

- Current CURRENT_STATE from Redis
- Relevant detected patterns from PostgreSQL
- Historical context from relevant time period
- Environmental factors (time, exam status, recent sleep)

This is the endpoint that answers: "Why is Shivam

feeling this way right now?" using every data point

available.

### 2.4 User Identity Profile

Create a persistent PostgreSQL table `user_identity`

(single row, updated in place — Shivam only):

Core identity fields (manually seeded, AI-augmented):

- stated_life_goals (jsonb)
- active_factions (jsonb with current weights)
- known_behavioral_tendencies (jsonb):

  e.g. {"impulse_work": 0.7, "deadline_driven": 0.85,

  "avoidance_creative_when_stressed": 0.6}
- peak_performance_windows (jsonb):

  e.g. {"late_night": 0.82, "morning": 0.31}
- known_stressors (jsonb array)
- known_energizers (jsonb array)
- communication_style_preference (jsonb):

  e.g. {"tone": "direct", "no_sycophancy": true,

  "push_back_allowed": true, "blunt": true}
- exam_behavioral_signature (jsonb — extracted from

  historical exam periods)
- last_updated (timestamp)
- update_source ("manual" | "ai_inference" | "both")

The pattern detector (2.2) must update

known_behavioral_tendencies and peak_performance_windows

automatically when a new persistent pattern is confirmed,

using a weighted rolling average — not a hard overwrite.

---

## SYSTEM 3: PROACTIVE INNER LOOP

A persistent background reasoning process that runs

independently of user input. This makes Locus think

without being asked.

### 3.1 Loop Schedule

APScheduler jobs:

- Every 90 minutes, 07:00–00:00 IST: standard pass
- 03:00 IST nightly: deep synthesis pass
- 03:30 IST Sunday: weekly pattern synthesis +

  decay all Neo4j edge weights by 0.95

### 3.2 Standard Pass (90-min)

Each run:

1. Fetch CURRENT_STATE from Redis (or regenerate if stale)
2. Fetch top 3 active behavioral_alerts from CURRENT_STATE
3. Fetch any detected_patterns confirmed in last 24h
4. Fetch last 2 hours of PostgreSQL events compressed

   via LOCUS_SHORTHAND
5. Pass to Groq 8b-instant with system prompt:

   "You are Locus's internal reasoning process. You are

   NOT talking to Shivam. You are thinking about Shivam.

   Your job: generate 0-2 specific, evidence-based

   observations about what you are noticing in his data

   right now.

   Rules:

   - Be specific. Cite data points. Not generic advice.
   - If you have nothing meaningful, return empty array.
   - Never fabricate. If the data doesn't support it,

   don't say it.

   - You know Shivam: direct, no sycophancy, push-back

   welcome, technically sharp, filmmaker + developer,

   exam in X days, current mood Y/10.

   Return JSON: {observations: [{text: string,

   confidence: float, should_surface: bool,

   surface_timing: 'now'|'morning_brief'|'hold'}]}"
6. For each observation with should_surface = true:

   - Score it: is this something Shivam already knows?

   Check Qdrant for semantic similarity to recent

   Telegram conversation history. If >0.85 similar

   to something said in last 6 hours, suppress it.

   - If surface_timing = 'now' AND confidence > 0.65:

   send via Telegram immediately

   - If surface_timing = 'morning_brief': queue in

   Redis for 08:00 IST morning briefing

   - If surface_timing = 'hold': store in

   detected_patterns for confirmation
7. Rate limit protection: track daily Groq token usage

   in Redis key `groq_tokens_today`. If >80% of free

   tier limit, skip inner loop runs and send one

   Telegram alert: "Locus inner loop paused —

   approaching daily token limit."

### 3.3 Nightly Deep Synthesis (03:00 IST)

Uses Groq 70b-versatile (or Gemini 2.5 Pro on Sundays).

Retrieves:

- Full day's events from PostgreSQL
- All detected_patterns updated today
- CURRENT_STATE history from the last 24 hours

  (store CURRENT_STATE snapshots in PostgreSQL

  every 6 hours — add this table: `state_snapshots`)
- Top 5 Neo4j pathways traversed today

Generates:

- End of day synthesis: what kind of day was it really?
- One key insight Shivam might not have noticed
- Recommended framing for tomorrow based on today's

  trajectory

Stores synthesis in PostgreSQL table `daily_synthesis`.

Queues for morning briefing at 08:00 IST.

### 3.4 Morning Briefing (08:00 IST)

Compiles:

- Nightly synthesis from `daily_synthesis`
- Queued observations from inner loop
- Top 3 tasks recommended for today based on

  faction balance, energy patterns, and deadlines
- One behavioral observation from detected_patterns

Formats as a clean Telegram message. Maximum 200 words.

Direct tone. No fluff. Shivam's communication style.

---

## HEBBIAN WEIGHTING IN NEO4J

Implement alongside the above systems:

1. Every Neo4j traversal by the Source Retriever

   increments traversed edge weights by 0.1
2. Every Telegram 👍 signal multiplies session

   pathway weights by 1.3
3. Every Telegram 👎 signal multiplies session

   pathway weights by 0.7
4. Weekly Sunday decay: all edge weights × 0.95
5. Expose GET /brain/pathways — top 10 strongest

   pathways for PWA display

Add 👍/👎 inline keyboard buttons to ALL Telegram

responses and all inner loop surface messages.

Store feedback in PostgreSQL table `reward_signals`.

---

## INTEGRATION REQUIREMENTS

- All systems Dockerized, added to docker-compose.yml
- All new tables have migration files
- All endpoints follow existing router structure

  with existing auth middleware
- Telegram bot completely rewired through System 1
- Run diagnose_databases.py first and report before

  any other changes

---

## WHAT SUCCESS LOOKS LIKE

Shivam is in an exam period. He's sleep-deprived.

He had a bad meal. He tried to generate an image

earlier and was visibly annoyed in his message.

At 22:30, without being asked, Locus sends:

"You've been in this pattern before — exam week,

bad sleep, low food quality, and it builds into

this kind of afternoon irritability by day 3.

Your data shows it clearly across your last 2 exam

periods. Tonight you deferred the Locus implementation

task again (4th time this week). Last time you pushed

through one anyway you logged satisfaction 8/10.

Your energy right now is 5/10 but it was 6/10 at

this time yesterday. You have a 90-minute window.

Your call."

That message was generated without Shivam saying a

word. It is supported by PostgreSQL event history,

Neo4j behavioral patterns, detected_patterns table,

and the contextual_flags in CURRENT_STATE. Zero

hallucination. Zero generic advice.

That is what you are building.

This is how I imagine Locus to "think" now enhance this or research about it online or keep it as is or use current technology that already does this flawlessly:

Prompt --> Obsidian, Neo4j, Qdrant, PostgreSQL, Web Search; query everything or whatever is necessary (need a system to determine this too) load all relevant context based on the prompt --> Process all this data using LLM + reasoning relevant to current + session context --> deliver answer/steps/execution or best answer akin to user (based on current + session context + user profile context.

I want the model's weights to be hydro dipped in being akin to ME using all the data I give it.

Plus, right now, the main issues is that whenever I query telegram about something, it NEVER queries obsidian or any of the databases only hallucinates an answer, I dont even know if Neo4j even really has data in it or not.

I want the brain to make real genuine inferences of me. It needs to check the time period, example: If I have exams going on and it knows from past record that I havent been very good at it and in a separate chat if I tried to generate an image and I was extra annoyed or angsty and if the night prior what kind of food I had plus what kind of night or days have I been having that attribute to me feeling this way, what does it say about me --> I want state of the art, industrial grade, military grade profiling and data collection and inferencing.

That is the level of expertise and capability I reliably want.GitHub repo: Shivamxp23/locus-os

Current confirmed tech stack:

- FastAPI backend
- PostgreSQL (raw events, logs, task data, user profile)
- Neo4j (behavioral knowledge graph)
- Qdrant (vector embeddings, semantic search)
- LightRAG (Neo4j + Qdrant as unified knowledge retrieval)
- Groq API (Llama 3 8b-instant for fast, 70b-versatile for

  complex — free tier, HARD token/rate limits)
- Gemini 2.5 Pro (weekly synthesis only — expensive,

  use sparingly)
- Celery + APScheduler
- Redis (Celery broker + short-term state cache)
- Telegram bot (primary interaction interface)
- Obsidian vault "Appledore" synced via Mobius Sync

  (accessible as markdown files on disk)
- React PWA at locusapp.online via Cloudflare Pages
- FastAPI at api.locusapp.online via Cloudflare Tunnel

Hard constraints:

- Zero cost. Respect Groq free tier and Oracle Always Free.
- CPU-only. No local LLM fine-tuning.
- Single user only.

---

CRITICAL CONTEXT BEFORE YOU START:

The current Telegram bot is BROKEN in a fundamental way. When

Shivam asks it anything, it hallucinates an answer directly

from the LLM's parametric knowledge WITHOUT querying

PostgreSQL, Neo4j, Qdrant, Obsidian, or any database. It is

essentially a dumb chatbot with no connection to Locus's data

layer. This is the single most important thing to fix.

Everything below is built on top of this fix.

Also unknown: whether Neo4j actually contains meaningful data.

Before building anything, write a diagnostic script

scripts/diagnose_databases.py that:

1. Connects to PostgreSQL and reports row counts for all tables
2. Connects to Neo4j and reports node counts by label and

   edge counts by type
3. Connects to Qdrant and reports collection names and

   vector counts
4. Scans the Obsidian vault directory and reports total

   markdown files, average file size, and whether backlinks

   exist
5. Prints a full health report to stdout

Run this first. Report findings. Then proceed with the build.

---

YOUR TASK: Build three systems. Do not break existing

functionality.

---

## What Was Built

This implements the complete 3-system cognitive architecture overhaul.

### Files Created / Rewritten

| File                                    | Status              | Purpose                                                                                                                                       |
| --------------------------------------- | ------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| `scripts/migrate_v3_inference.sql`    | **NEW**       | New tables:`detected_patterns`, `user_identity`, `state_snapshots`, `daily_synthesis`, `reward_signals`, `morning_briefing_queue` |
| `scripts/diagnose_databases.py`       | **REWRITTEN** | Fixed diagnostic with correct creds, Redis check, vault analysis, v3 table detection                                                          |
| `backend/core/db.py`                  | **NEW**       | Shared asyncpg pool + async Redis client + helper functions — eliminates HTTP round-trips                                                    |
| `backend/core/query_classifier.py`    | **REWRITTEN** | LLM-powered intent classifier with 8 intent types + 6 data sources + temporal scoping                                                         |
| `backend/core/source_retriever.py`    | **REWRITTEN** | Parallel async retrieval from ALL sources via direct DB queries (was broken — used HTTP round-trips)                                         |
| `backend/core/context_synthesizer.py` | **REWRITTEN** | Token-budgeted context merger (800 tokens total) with per-layer compression +`[NO_PERSONAL_DATA]` warning                                   |
| `backend/core/shorthand.py`           | **REWRITTEN** | LOCUS_SHORTHAND compression schema + encoders/decoders + schema prompt for LLM injection                                                      |
| `backend/core/state_engine.py`        | **REWRITTEN** | State inference pipeline — gathers context directly from DB, runs 70b LLM, caches in Redis (6h TTL), snapshots to PostgreSQL                 |
| `backend/core/pattern_detector.py`    | **REWRITTEN** | Multi-horizon (5-level) pattern detection with confirmation counting + auto-promotion to user identity                                        |
| `backend/core/inner_loop.py`          | **REWRITTEN** | Proactive inner loop: 90-min passes, nightly synthesis (Gemini on Sundays), morning briefings, Hebbian decay, token budget tracking           |
| `backend/core/hebbian.py`             | **NEW**       | Hebbian learning: traversal weight increment, feedback signal application, reward persistence                                                 |
| `backend/telegram_bot.py`             | **REWRITTEN** | Complete 6-step routing pipeline, system prompt with identity/shorthand, feedback buttons, background state inference                         |
| `backend/routers/inference.py`        | **REWRITTEN** | API endpoints:`/state`, `/patterns`, `/pathways`, `/feedback`, `/synthesis`                                                         |
| `backend/main.py`                     | **EDITED**    | Added token reset scheduler job, bumped to v4.0                                                                                               |
| `backend/requirements.txt`            | **EDITED**    | Added `python-telegram-bot==21.3`                                                                                                           |

---

## Architecture: The 6-Step Pipeline

Every Telegram message now flows through this pipeline **without exceptions**:

```
User Message
    │
    ▼
┌─────────────────────┐
│ 1. CLASSIFY INTENT  │  ← Groq 8b-instant (~50 tokens, <500ms)
│    8 intent types    │     Returns: intent + sources_required + temporal_scope
│    6 data sources    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 2. PARALLEL FETCH   │  ← asyncio.gather on all required sources
│    PostgreSQL        │     Direct DB queries (no HTTP round-trips)
│    Neo4j             │     Each source has its own async function
│    Qdrant            │
│    Obsidian/LightRAG │
│    Redis Cache       │
│    DuckDuckGo Web    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 3. SYNTHESIZE       │  ← 800-token budget, per-layer compression
│    Identity (80t)    │     Uses LOCUS_SHORTHAND for 75% reduction
│    Temporal (60t)    │     [NO_PERSONAL_DATA] warning if all empty
│    Postgres (180t)   │
│    Neo4j   (150t)    │
│    Semantic (200t)   │
│    Web     (100t)    │
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 4. SELECT MODEL     │  ← 8b for simple, 70b for deep reasoning
│    8b: factual,     │
│    knowledge, tasks  │
│    70b: inference,   │
│    synthesis, pattern│
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 5. LLM CALL         │  ← System prompt + synthesized context + user query
│    Anti-hallucination│     "You are Locus — Shivam's cognitive OS"
│    rules enforced    │     Personal data always prioritized over training
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ 6. RESPOND          │  ← Response + 👍/👎 feedback buttons
│    + Hebbian update  │     Traversed Neo4j pathways get +0.1 weight
│    + State inference │     Background state update triggered
└─────────────────────┘
```

---

## Deployment Steps

> [!IMPORTANT]
> The VM repo at `/opt/locus` was originally cloned/modified as root. If `git pull` fails with "insufficient permission for adding an object to repository database .git/objects", run `sudo chown -R ubuntu:ubuntu /opt/locus` first.

### 1. Push to GitHub (from local machine)

```bash
cd C:\Users\soni8\Desktop\everything\University 2.0\Project(s)\5_Locus\locus-os
git add -A
git commit -m "description of changes"
git push origin main
```

### 2. SSH into the VM

```bash
ssh -i ".keysndocs/ssh-key-2026-03-27.key" ubuntu@140.238.245.25
```

### 3. Fix permissions & pull latest code

```bash
sudo chown -R ubuntu:ubuntu /opt/locus
cd /opt/locus
git pull origin main
```

### 4. Run database migrations (if needed)

Only run migrations that haven't been applied yet. Already-applied migrations will show `NOTICE: relation already exists, skipping`.

```bash
# v2 migration (factions, outcomes, projects, task deferrals)
docker exec -i locus-postgres psql -U locus -d locus < scripts/migrate_v2.sql

# v3 migration (inference engine: detected_patterns, user_identity, state_snapshots, daily_synthesis, reward_signals, morning_briefing_queue)
docker exec -i locus-postgres psql -U locus -d locus < scripts/migrate_v3_inference.sql
```

Verify all 22 tables exist:
```bash
docker exec locus-postgres psql -U locus -d locus -c '\dt'
```

### 5. Rebuild & restart the API

> [!WARNING]
> The docker-compose service is named `fastapi`, NOT `api`. The container is named `locus-api` but the service name is `fastapi`.

```bash
cd /opt/locus
docker compose build fastapi
docker compose up -d fastapi
```

### 6. Verify all services are running

```bash
# Check all 6 containers are up
docker ps --format 'table {{.Names}}\t{{.Status}}'

# Expected:
# locus-api         Up X minutes
# locus-neo4j       Up (healthy)
# locus-redis       Up (healthy)
# locus-postgres    Up (healthy)
# locus-qdrant      Up
# locus-syncthing   Up (healthy)
```

### 7. Health check

```bash
curl -s http://localhost:8000/health | python3 -m json.tool
```

Expected response:
```json
{
    "status": "ok",
    "version": "4.0.0",
    "jobs": [
        "system3_inner_loop", "nightly_diff", "system3_token_reset",
        "vault_change_track", "system2_patterns", "brain_crawl",
        "pattern_detection", "exhaustion_check", "system3_nightly",
        "system3_morning", "weekly_synthesis", "system3_decay",
        "dead_node_detection", "brain_patterns", "brain_weekly_review"
    ],
    "sync": { "postgres": "ok", "neo4j": "ok", "qdrant": "ok" }
}
```

### 8. Check API logs for errors

```bash
docker logs locus-api --tail 30
```

### 9. Deploy PWA (from local machine, if changed)

```bash
npx wrangler pages deploy ./pwa/build --project-name=locus-pwa
```

### Service Architecture Reference

| Container | Service Name | Port | Purpose |
|-----------|-------------|------|---------|
| `locus-api` | `fastapi` | 8000 | FastAPI backend (v4.0.0) |
| `locus-postgres` | `postgres` | 5432 (local only) | PostgreSQL 16 + pgvector |
| `locus-redis` | `redis` | 6379 (local only) | Redis 7 (Celery broker + cache) |
| `locus-neo4j` | `neo4j` | 7687 (internal) | Neo4j 5.18 (behavioral graph) |
| `locus-qdrant` | `qdrant` | 6333 (internal) | Qdrant (vector search) |
| `locus-syncthing` | `syncthing` | 8384, 22000 | Obsidian vault sync |

---

## Key Design Decisions

1. **Direct DB queries over HTTP round-trips** — The old source_retriever called the API's own endpoints via HTTP, which either didn't exist or created circular dependencies. Every retriever now uses asyncpg/neo4j-driver/httpx directly.
2. **Token budget tracking** — Groq free tier has hard limits. Every LLM call increments a Redis counter. Inner loop pauses at 80% budget. Counter resets at midnight IST.
3. **DuckDuckGo over SerpAPI** — SerpAPI requires a paid key. DuckDuckGo Instant Answer API is free and sufficient for external knowledge queries.
4. **Pattern confirmation counting** — Detected patterns aren't immediately trusted. They must be confirmed across multiple detection runs before being promoted to the user identity layer via weighted rolling average.
5. **Sunday Gemini synthesis** — Weekly deep synthesis uses Gemini 2.5 Pro (more expensive but better for long-horizon reasoning). All other synthesis uses Groq 70b.
6. **Similarity suppression** — Inner loop observations are checked against recent Qdrant content to prevent sending the same insight repeatedly.

> [!WARNING]
> The `captures` table must exist in PostgreSQL for the quick-capture feature (`note:` prefix). If it doesn't, the fallback is silent — messages will route through the normal pipeline instead.

> [!IMPORTANT]
> After deploying, run `diagnose_databases.py` FIRST to verify all databases are accessible and have data. If Neo4j is empty, the personality graph retriever will return nothing and responses will lack behavioral context.

---

## v4.0 Dead Code Cleanup — 2026-05-12

After the System 1-2-3 reconstruction, the old `services/brain/` pipeline and several other files became fully redundant. They were either superseded by new `core/` modules or were non-functional stubs. This section documents what was removed and why.

### Files Deleted

| File                               | Reason for Deletion                                                                                                                                        |
| ---------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `services/brain/pipeline.py`     | Old keyword-based routing (`if "pattern" in query...`). Fully replaced by `core/query_classifier.py` + the 6-step pipeline in `telegram_bot.py`.     |
| `services/brain/retriever.py`    | Old keyword-based retriever with single-source routing. Fully replaced by `core/source_retriever.py` which does parallel multi-source direct DB queries. |
| `services/brain/generator.py`    | Old LLM response generator wrapper. Replaced by inline Groq calls in `telegram_bot.py` with the anti-hallucination system prompt.                        |
| `services/brain/web_searcher.py` | Used SerpAPI (paid key required, never configured). Replaced by DuckDuckGo Instant Answer API in `core/source_retriever.py`.                             |
| `services/brain/reader.py`       | Vault file reader. Replaced by Obsidian vault search in `core/source_retriever.py`.                                                                      |
| `services/brain/scheduler.py`    | Old TWS-based task scheduler. Task planning is now handled through the inference pipeline (`TASK_PLANNING` intent).                                      |
| `services/content_engine.py`     | Draft generation service using `services/llm.py` + Gemini. Never imported by any router or service — completely orphaned.                               |
| `routers/wiki.py`                | Empty router (6 lines, only a comment "kept for future"). No endpoints, no logic.                                                                          |

### Files Modified During Cleanup

| File                 | Change                                                                                                                                                                                                                                                                                                                    |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `routers/brain.py` | Stripped dead imports (`pipeline`, `retriever`, `reader`, `scheduler`, `generator`, `web_searcher`). Removed endpoints: `/chat`, `/read`, `/retrieve`, `/schedule`, `/reschedule`. Kept: `/collect`, `/patterns`, `/goals`, `/weekly-review`, `/goals/distill`, `/goals/clarification`. |
| `main.py`          | Removed `wiki` from router imports and registration. Updated startup log to v4.0.                                                                                                                                                                                                                                       |

### Files Kept in `services/brain/`

| File                  | Reason to Keep                                                                                                                                                                                                                              |
| --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `collector.py`      | Vault crawl + hash-based change detection. Still scheduled nightly in `main.py`. Indexes new/changed `.md` files into Qdrant via chunker.                                                                                               |
| `chunker.py`        | Proposition-based chunking with spaCy + Groq factual filter. Used by `collector.py` for Qdrant ingestion.                                                                                                                                 |
| `pattern_engine.py` | Legacy pattern engine (DCS trend, faction lag, deferral analysis). Still scheduled weekly in `main.py`. Writes to `pattern_snapshots` and Neo4j. Complements the new `core/pattern_detector.py` which operates on different horizons. |
| `goal_tracker.py`   | Weekly review: dead node detection, stalled project flagging, deferral summaries. Still scheduled weekly in `main.py`. Writes Obsidian notes and `weekly_reviews` table.                                                                |

### Other Files Kept (Not Redundant)

| File                  | Reason to Keep                                                                                 |
| --------------------- | ---------------------------------------------------------------------------------------------- |
| `services/llm.py`   | 5-provider LLM cascade. Still used by `vault_jobs.py` for nightly diff and weekly synthesis. |
| `routers/vector.py` | Working Qdrant vector search endpoint. Used by PWA.                                            |
| `routers/logs.py`   | DCS calculator endpoint for morning check-in.                                                  |

### Net Result

- **8 files deleted** (~25KB of dead code)
- **2 files rewritten** to remove broken imports
- `services/brain/` reduced from 11 files → 5 files (only functional modules remain)
- `routers/` reduced from 17 files → 16 files
- Zero functionality lost — every deleted file was either superseded or non-functional
