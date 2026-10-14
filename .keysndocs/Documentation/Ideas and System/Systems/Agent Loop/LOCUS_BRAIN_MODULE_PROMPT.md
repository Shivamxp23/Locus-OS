# LOCUS BRAIN MODULE — IMPLEMENTATION PROMPT
## For use in an AI code editor (Claude Code / Cursor / Windsurf)

---

## CONTEXT: WHO YOU ARE BUILDING FOR

You are building the Brain Module for **Locus** — a Personal Cognitive Operating System (PCOS) built for one specific user. Locus is not a generic productivity app. It is a system that builds a deep, data-driven model of one person over time and uses that model to help them make better decisions about how they spend their time, energy, and attention.

The user's life is organized into **four factions**:
- **Faction 1 — Health/Stability** (color: `#22C55E`): fitness, sleep, nutrition, academics, CS fundamentals
- **Faction 2 — Leverage/Money** (color: `#3B82F6`): freelance, startups, networking, career visibility
- **Faction 3 — Craft/Skills** (color: `#F97316`): cinematography, software engineering, passion projects
- **Faction 4 — Expression/Exploration** (color: `#A855F7`): identity, hobbies, reading, unstructured time

Every action, task, goal, and log entry belongs to exactly one faction. The system is entirely metric-driven. No vague sentiment — only numbers.

---

## EXISTING TECH STACK

Do not change the stack. Build within it.

- **Backend**: FastAPI (Python), running in Docker on Oracle ARM VM (`140.238.245.25`)
- **Database**: PostgreSQL — all relational data, behavioral events, task/goal records
- **Graph DB**: Neo4j — knowledge graph, entity relationships, personality model, Person node
- **Vector DB**: Qdrant — semantic search, embeddings, vault chunks
- **Embeddings**: `fastembed` with model `BAAI/bge-small-en-v1.5` (384 dims)
- **Scheduler**: APScheduler — nightly and periodic jobs
- **Vault**: Obsidian vault synced via Syncthing to VM at path defined by `VAULT_PATH` env var
- **Interface**: Telegram bot (`@mylocusbot`) as primary conversational interface
- **PWA**: React/Vite hosted on Cloudflare Pages
- **Tunnel**: Cloudflare Tunnel routing external traffic to VM
- **LLM Gateway**: OpenClaw (configured with Groq — `llama-3.1-8b-instant` or `gemma2-9b-it`)
- **NLP**: `spacy` with `en_core_web_sm`

**Repo root**: OpenClaw  
**Locus skill path**: `skills/locus/`  
**All business logic**: FastAPI owns it  
**API version at time of writing**: v3.0.0  

---

## WHAT YOU ARE BUILDING

The Brain Module is a collection of **9 specialized sub-systems**. Each sub-system has exactly one responsibility. They do not overlap. They are wired together in a strict pipeline: data is always collected and retrieved **before** any LLM is invoked. The LLM only speaks — it never remembers, never invents.

**The Core Law**: Every word Locus says about the user, their data, or their schedule must be grounded in a real data source that a real sub-system retrieved first. If data is not available, Locus says so. Silence is always better than hallucination.

---

## THE 9 SUB-SYSTEMS — DETAILED SPECIFICATIONS

---

### SUB-SYSTEM 1: THE COLLECTOR
**File**: `brain/collector.py`  
**Trigger**: APScheduler nightly job (default: 2:00 AM VM time) + on-demand via API  
**Responsibility**: Ingest all user data sources into the tri-store (Postgres + Neo4j + Qdrant)

**Data Sources to Collect From** (in priority order):
1. Obsidian vault — all `.md` files under `VAULT_SCAN_DIRS` (read from env, currently: `01-Journal`, `03-AI-Chats`, `04-Resources`, `05-Content`)
2. Telegram captured messages (already in Postgres `captures` table — just needs indexing trigger)
3. Morning/evening check-in logs (Postgres `checkins` table)
4. Task completion events (Postgres `tasks` table)
5. Google Calendar events (via existing OAuth integration)

**Incremental Logic** (critical — do not re-process unchanged files):
```python
# For each file:
file_hash = md5(file_content)
# Check against stored hash in postgres table: vault_index_state(file_path, file_hash, last_indexed_at)
# If hash unchanged: SKIP
# If hash changed or new: pass to Chunker, update hash record
```

**On collection, write to**:
- Postgres: `behavioral_events` table with `event_type='vault_crawl'`, timestamp, file count
- Hand changed/new files to Chunker for processing
- Log errors per file — one bad file must NOT stop the full crawl

**Error handling**: Wrap each file in try/except. On failure: log to `brain_errors` table with `subsystem='collector'`, `file_path`, `error_msg`, `severity` (1-3). Continue with next file.

---

### SUB-SYSTEM 2: THE CHUNKER
**File**: `brain/chunker.py`  
**Responsibility**: Convert raw markdown notes into factual proposition-based chunks ready for embedding

**Pipeline per file**:
1. Strip markdown syntax (headers, bullet markers, links) — keep plain sentences
2. Use `spacy` (`en_core_web_sm`) to detect sentence boundaries
3. For each sentence, run factual classifier (see below)
4. Group approved sentences into chunks of max 5 propositions
5. Return list of chunks with metadata: `{source_file, chunk_index, text, char_count}`

**Factual Classifier**:
- Primary: attempt Groq call with `llama-3.1-8b-instant`
- Prompt: `"Is this sentence a factual statement, idea, or meaningful claim? Reply only YES or NO. Sentence: {sentence}"`
- Filter: keep only YES sentences
- If Groq unavailable: fall back to heuristic (sentence length > 8 words AND does not start with `#`, `-`, `*`, `>`)
- Do NOT block the pipeline on classifier failure — use heuristic as fallback

**What gets filtered out**: headings, bullet fragments under 8 words, metadata lines (e.g., `date: 2026-04-01`), blank lines, code blocks

**Output**: Pass chunks to Qdrant service for batch embedding. Also store chunk metadata in Postgres `vault_chunks` table: `(id, file_path, chunk_index, text, embedding_id, created_at)`

---

### SUB-SYSTEM 3: THE READER
**File**: `brain/reader.py`  
**Responsibility**: Open a specific file on demand and return its full raw content as a string for injection into LLM context

**API endpoint**: `POST /brain/read`  
**Request body**: `{ "file_path": "relative/path/from/vault/root.md" }`  
**Response**: `{ "content": "<full raw text>", "word_count": int, "found": bool }`

**Rules**:
- Always read from the actual file on disk — never from cached index
- If file not found: return `{ "found": false, "content": null }` — do NOT guess or hallucinate
- Strip only YAML frontmatter before returning — preserve all other content including headers
- If file is over 8000 words: return first 8000 words and flag `truncated: true` in response
- Log every read call to `behavioral_events` with `event_type='file_read'`, `file_path`

**Usage in Telegram bot**: When user asks "read [filename]" or "what does [filename] say" — call Reader first, inject the returned content into LLM context with instruction: `"Answer ONLY from the following document content. If the answer is not in the document, say so. Do not invent. Document: {content}"`

---

### SUB-SYSTEM 4: THE RETRIEVER
**File**: `brain/retriever.py`  
**Responsibility**: Search across all stored data to find relevant context before any LLM response

**Three retrieval modes** (auto-selected by query classifier):

**Mode A — Semantic Search (Qdrant)**  
Use when: query is conceptual, exploratory, or about vault knowledge  
```python
async def semantic_search(query: str, top_k: int = 5) -> list[dict]:
    # embed query with fastembed
    # search qdrant collection
    # return: [{text, source_file, score}]
```

**Mode B — Structured Query (Postgres)**  
Use when: query is about specific logged data (tasks, check-ins, scores, history)  
Examples: "what did I do this week", "show my DCS for the past 7 days", "what tasks are overdue"  
```python
async def structured_query(intent: str, params: dict) -> list[dict]:
    # map intent to SQL query
    # intents: 'recent_tasks', 'checkin_history', 'faction_scores', 'deferred_tasks', 'goal_stack'
    # return structured rows
```

**Mode C — Graph Query (Neo4j)**  
Use when: query is about relationships, patterns, or the user's model  
Examples: "what skills am I building", "how are my goals connected", "what patterns does Locus see in me"  
```python
async def graph_query(entity: str, relationship: str = None) -> list[dict]:
    # Cypher query against Neo4j
    # return: [{node, relationship, related_node}]
```

**Query Classifier** (determines which mode to use):
```python
def classify_query(query: str) -> str:
    # Keywords → Postgres: "task", "did i", "this week", "score", "dcs", "log", "check-in", "overdue", "today"
    # Keywords → Graph: "pattern", "connected", "related", "skill", "relationship", "model"  
    # Default → Qdrant semantic search
```

**Output format** (consistent across all modes):
```python
{
    "results": [{"text": str, "source": str, "score": float}],
    "mode_used": str,
    "result_count": int,
    "query": str
}
```

**Rule**: If zero results in any mode — return empty results clearly. Do NOT fall back to LLM guessing. The response to the user must include: "I don't have any stored data on that."

---

### SUB-SYSTEM 5: THE PATTERN ENGINE
**File**: `brain/pattern_engine.py`  
**Trigger**: APScheduler weekly job (Sunday 11:00 PM VM time) + on-demand  
**Responsibility**: Analyze behavioral history and surface real patterns about the user

**Patterns to detect and store** (all from Postgres queries):

**5.1 — DCS Trend**  
```sql
SELECT date, dcs FROM checkins ORDER BY date DESC LIMIT 14
-- Detect: rising, falling, flat, volatile
-- Flag: if avg DCS < 4.0 for 7+ consecutive days → 'extended_low_capacity' alert
```

**5.2 — Faction Lag Score** (per the System Bible formula)  
```
LS = target_hours - actual_hours (this week per faction)
target_hours = [17.5, 17.5, 21.0, 14.0] for factions [1,2,3,4]
If LS > 3: flag as 'behind'
If LS > 6: flag as 'critical'
```

**5.3 — Deferral Patterns**  
```sql
SELECT task_id, COUNT(*) as deferrals FROM task_deferrals GROUP BY task_id HAVING COUNT(*) >= 3
-- These are things the user is actively avoiding
```

**5.4 — Action Gap** (per System Bible)  
```
AG = declared_faction_priority - (actual_hrs / target_hrs × 10)
AG > 5 → system alert: "You say [faction] matters but you haven't shown up"
```

**5.5 — Exhaustion Risk Predictor**  
```
If avg_task_difficulty (last 5 days) > 7 AND avg_DCS (last 5 days) < 5:
    → flag 'exhaustion_risk': True
    → Scheduler uses this to reduce next-day task load by 30%
```

**5.6 — Best Focus Windows**  
```sql
SELECT time_of_day, AVG(quality) as avg_quality FROM task_completions GROUP BY time_of_day
-- Bins: morning (6-12), afternoon (12-17), evening (17-22), night (22-6)
-- Output: user's historically best time window for high-D tasks
```

**Output**: Write all detected patterns to Neo4j `Person` node as properties. Also write summary to Postgres `pattern_snapshots` table: `(snapshot_date, faction_lag_json, dcs_trend, exhaustion_risk, action_gap_json, deferral_count)`

---

### SUB-SYSTEM 6: THE SCHEDULER
**File**: `brain/scheduler.py`  
**Trigger**: Every morning check-in completion + on-demand  
**Responsibility**: Produce a ranked, realistic daily task list based on the user's actual current state

**Required inputs** (pull from Postgres before running):
- Today's DCS and Mode
- All active tasks with their TWS scores
- This week's faction lag scores (from Pattern Engine snapshot)
- Available time `T` (from morning log)
- Exhaustion risk flag (from Pattern Engine)

**The Scheduling Algorithm** (implement exactly as specified):

```
STEP 1 — LOCK NON-NEGOTIABLES
Non-negotiables are immovable and consumed first:
  - Sleep block (7 hrs minimum — affects available T)
  - Movement (20 min)
  - Meals (45 min total)
  - Any academic deadline within 48 hrs → P=10, U=10 override
  - Any calendar commitment (from Google Calendar)
T_available = T - non_negotiable_hours

STEP 2 — DCS MODE FILTER
  SURVIVAL  → task_pool = [] (empty, non-negotiables only)
  RECOVERY  → task_pool = tasks where D <= 4
  NORMAL    → task_pool = tasks where D <= 7
  DEEP/PEAK → task_pool = all active tasks

STEP 3 — LAG BONUS APPLICATION
For each faction:
  If LS > 3 hrs: all faction tasks get TWS += 2
  If LS > 6 hrs: all faction tasks get TWS += 4
  If faction is ahead of target: all faction tasks get TWS -= 1

STEP 4 — EXHAUSTION RISK ADJUSTMENT
If exhaustion_risk == True:
  T_available = T_available * 0.70  (reduce workload by 30%)
  task_pool = tasks where D <= 6  (cap difficulty)

STEP 5 — SORT AND SELECT
Sort task_pool by adjusted TWS descending.
Select tasks from top, accumulating Est.
Stop when: accumulated_Est >= T_available * 0.80

STEP 6 — FACTION BALANCE CHECK
If selected tasks represent <= 1 faction AND mode != SURVIVAL/RECOVERY:
  Replace lowest TWS selected task with highest TWS task from underrepresented faction

STEP 7 — TIME BLOCK ASSIGNMENT
  Highest D task → user's best focus window (from Pattern Engine)
  Medium D tasks → midday
  Lowest D tasks → late afternoon / evening
  Faction 4 tasks → evening preferred

OUTPUT: {
  "date": today,
  "mode": current_mode,
  "dcs": dcs_value,
  "task_list": [
    {
      "task_id": str,
      "title": str,
      "faction": int,
      "tws_score": float,
      "difficulty": int,
      "estimated_hours": float,
      "suggested_time_block": str,
      "project": str,
      "outcome": str
    }
  ],
  "total_estimated_hours": float,
  "available_hours": float,
  "faction_lag_flags": dict,
  "exhaustion_risk": bool
}
```

**Emergency Rescheduling**: Expose endpoint `POST /brain/reschedule` that accepts `{ "reason": str, "lost_hours": float }` and recomputes the schedule on demand. Defer deferred tasks automatically — no guilt, no accumulation. Just recalculate.

**Dead Node Detection**: Any goal/project not touched in 60 days → flag as `status='dead_node'` in Postgres and include in weekly review output.

---

### SUB-SYSTEM 7: THE WEB SEARCHER
**File**: `brain/web_searcher.py`  
**Responsibility**: Fetch external information when user's query requires it

**When to activate** (query classifier logic):
- Query contains: "latest", "current", "what is", "how does", "news", "2026", "today" AND topic is not in vault
- Retriever returned zero relevant results for a knowledge question
- User explicitly says "search", "look up", "find"

**When NOT to activate**:
- Any query about the user's own data, history, tasks, or vault
- Any query answerable from stored context

**Implementation**: Use existing Groq/LLM gateway. If a web search tool is available via OpenClaw, use it. Otherwise use a fallback HTTP search via SerpAPI or similar configured in env.

**Output**: Return `{ "query": str, "results": [{"title", "snippet", "url"}], "source": "web" }`  
Always surface the source URL to the user. Never present web results as if they came from the vault.

---

### SUB-SYSTEM 8: THE GOAL TRACKER
**File**: `brain/goal_tracker.py`  
**Trigger**: Weekly (Sunday APScheduler job) + on-demand  
**Responsibility**: Monitor the three-layer goal stack and surface the honest state of the user's progress

**The Goal Stack** (stored in Postgres):
```
outcomes (id, title, faction, why, status, created_at, last_touched_at)
  └── projects (id, outcome_id, title, completion_state, deadline, difficulty, status, active)
        └── tasks (id, project_id, title, P, D, U, est_hours, status, created_at, completed_at)
```

**Weekly checks to run**:

1. **Dead Node Detection**  
   `SELECT * FROM projects WHERE last_touched_at < NOW() - INTERVAL '60 days' AND status = 'active'`  
   → Update status to `'dead_node'`, include in weekly review

2. **Active Project Cap Enforcement**  
   Per faction: max 3 active projects. If > 3:  
   → Flag `'project_overload'` for that faction in weekly review  
   → Do not auto-kill — surface to user for decision

3. **Action Gap Calculation** (per System Bible)  
   ```
   AG = declared_faction_priority - (actual_hrs_this_week / target_hrs * 10)
   AG > 5 → 'avoidance_alert' for that faction
   ```

4. **Completion Rate per Project**  
   `CR = tasks_completed / tasks_total * 100`  
   Projects with CR < 20% and age > 30 days → flag `'stalled'`

5. **Deferral Pattern Summary**  
   Tasks deferred 3+ times → flag for user review with the honest question: "You have avoided this 3+ times. Kill it or commit."

**Weekly Review Output** (write to Postgres `weekly_reviews` table AND create Obsidian note at `05-Content/WeeklyReview/YYYY-MM-DD.md`):
```json
{
  "week_ending": "date",
  "faction_hours": {"1": float, "2": float, "3": float, "4": float},
  "faction_lag": {"1": float, "2": float, "3": float, "4": float},
  "action_gaps": {"1": float, "2": float, "3": float, "4": float},
  "dead_nodes": [project_ids],
  "stalled_projects": [project_ids],
  "deferral_patterns": [task_ids],
  "dcs_avg_this_week": float,
  "momentum_scores": {"1": float, "2": float, "3": float, "4": float}
}
```

---

### SUB-SYSTEM 9: THE GENERATOR
**File**: `brain/generator.py`  
**Responsibility**: The ONLY place where the LLM produces a final response to the user. Sits at the end of every pipeline.

**Rule**: The Generator is called AFTER all relevant sub-systems have run. It receives assembled context — it does not go get its own data.

**Standard input format**:
```python
{
  "user_query": str,
  "retrieved_context": list[dict],    # From Retriever (Qdrant/Postgres/Neo4j results)
  "user_state": {                      # From latest check-in
    "dcs": float,
    "mode": str,
    "faction_health": dict,
    "exhaustion_risk": bool
  },
  "file_content": str | None,         # From Reader, if a specific file was requested
  "schedule": dict | None,            # From Scheduler, if scheduling was requested
  "patterns": dict | None,            # From Pattern Engine, if pattern question
  "web_results": list | None,         # From Web Searcher, if external search ran
  "instruction": str                  # What the Generator is being asked to produce
}
```

**System prompt for the LLM** (inject with every Generator call):
```
You are Locus, a Personal Cognitive Operating System for one specific user.
Your job is to speak — not to remember, not to guess, not to invent.
You have been given real data retrieved from the user's actual records.
RULES:
1. Answer ONLY from the provided context. If the data is not in the context, say "I don't have that information stored."
2. Never fabricate file contents, task names, syllabi, scores, or any personal data.
3. Be direct. No bullet-pointed generic advice. Speak to this specific person from their specific data.
4. If user_state.mode is SURVIVAL or RECOVERY, match your tone accordingly. Don't push tasks.
5. If the context is empty and the query is personal, respond: "I don't have data on that yet. Would you like to log it?"
6. You are not a therapist. You are a precise cognitive tool. Be warm but stay factual.
```

**Anti-hallucination guard** (implement as middleware before returning response):
```python
def validate_response(response: str, context: dict) -> bool:
    # If response contains any proper noun not present in context → flag for review
    # If response references a specific file/task/date → verify it exists in context
    # If validation fails → return: "I don't have reliable data on that. Try asking me to search or log it."
```

---

## PIPELINE WIRING — HOW THE SUB-SYSTEMS CONNECT

Every user query goes through this decision pipeline before the Generator speaks:

```
USER MESSAGE
     │
     ▼
QUERY CLASSIFIER
     │
     ├── "read [file]"           → Reader → Generator (with file_content)
     │
     ├── personal data query     → Retriever (Postgres/Graph mode) → Generator
     │
     ├── vault knowledge query   → Retriever (Qdrant semantic mode) → Generator
     │
     ├── "what should I do"      → Retriever + Scheduler → Generator (with schedule)
     │
     ├── "what patterns..."      → Pattern Engine → Generator (with patterns)
     │
     ├── external knowledge      → Web Searcher → Generator (with web_results)
     │
     └── general conversation    → Retriever (semantic, top 3) → Generator

GENERATOR always receives assembled context. Never runs blind.
```

---

## API ENDPOINTS TO EXPOSE

All under `/brain/` prefix:

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/brain/collect` | Trigger manual vault crawl |
| `POST` | `/brain/read` | Read a specific vault file |
| `POST` | `/brain/retrieve` | Query retriever directly |
| `POST` | `/brain/schedule` | Generate today's task list |
| `POST` | `/brain/reschedule` | Emergency reschedule |
| `GET` | `/brain/patterns` | Get latest pattern snapshot |
| `GET` | `/brain/goals` | Get full goal stack status |
| `GET` | `/brain/weekly-review` | Get latest weekly review |
| `POST` | `/brain/chat` | Main entry point: full pipeline |

The `/brain/chat` endpoint is what the Telegram bot calls. It runs the full pipeline (classifier → retrieval → generation) and returns a response grounded in real data.

---

## DATABASE SCHEMA ADDITIONS

Add these tables to Postgres (run as migration):

```sql
-- Vault indexing state tracker
CREATE TABLE vault_index_state (
    file_path TEXT PRIMARY KEY,
    file_hash TEXT NOT NULL,
    last_indexed_at TIMESTAMPTZ DEFAULT NOW(),
    chunk_count INT DEFAULT 0
);

-- Vault chunks metadata
CREATE TABLE vault_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    file_path TEXT NOT NULL,
    chunk_index INT NOT NULL,
    text TEXT NOT NULL,
    qdrant_point_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Brain error log
CREATE TABLE brain_errors (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subsystem TEXT NOT NULL,
    file_path TEXT,
    error_msg TEXT NOT NULL,
    severity INT CHECK (severity IN (1,2,3)),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Pattern snapshots
CREATE TABLE pattern_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    snapshot_date DATE NOT NULL,
    faction_lag_json JSONB,
    dcs_trend TEXT,
    exhaustion_risk BOOL DEFAULT FALSE,
    action_gap_json JSONB,
    deferral_count INT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Weekly reviews
CREATE TABLE weekly_reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    week_ending DATE NOT NULL,
    review_json JSONB NOT NULL,
    obsidian_note_path TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Task deferrals tracker
CREATE TABLE task_deferrals (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID NOT NULL,
    deferred_at TIMESTAMPTZ DEFAULT NOW(),
    reason TEXT
);
```

---

## FILE STRUCTURE

```
skills/locus/brain/
├── __init__.py
├── collector.py          # Sub-system 1
├── chunker.py            # Sub-system 2
├── reader.py             # Sub-system 3
├── retriever.py          # Sub-system 4
├── pattern_engine.py     # Sub-system 5
├── scheduler.py          # Sub-system 6
├── web_searcher.py       # Sub-system 7
├── goal_tracker.py       # Sub-system 8
├── generator.py          # Sub-system 9
├── pipeline.py           # Query classifier + pipeline orchestrator
└── router.py             # FastAPI router registering all /brain/ endpoints
```

Register `brain/router.py` in the main FastAPI app.

---

## APSCHEDULER JOBS TO ADD

```python
# In scheduler config:
scheduler.add_job(collector.run_nightly_crawl,    'cron', hour=2,  minute=0)   # 2:00 AM
scheduler.add_job(pattern_engine.run_weekly,       'cron', day_of_week='sun', hour=23)  # Sunday 11 PM
scheduler.add_job(goal_tracker.run_weekly_review,  'cron', day_of_week='sun', hour=23, minute=30)
```

---

## CRITICAL IMPLEMENTATION RULES

1. **Never call the Generator without retrieved context.** If retrieval returns nothing, pass that explicitly. The Generator must handle empty context gracefully.

2. **The Collector must handle the real vault directory names.** Read `VAULT_SCAN_DIRS` from env. Default value must be `01-Journal,03-AI-Chats,04-Resources,05-Content` — NOT the old wrong values.

3. **Incremental indexing is mandatory.** Never re-process a file whose hash hasn't changed. The nightly job must be fast enough to run without timeout on 1,600+ files.

4. **All sub-systems are independently callable.** No sub-system should depend on another being called first, except via explicit input parameters. Loose coupling — tight contracts.

5. **Every sub-system writes to `behavioral_events`.** Every crawl, read, retrieval, schedule generation, and pattern run gets logged. This is the audit trail.

6. **Mode-awareness in all outputs.** Every sub-system that produces user-facing output must receive the current DCS/Mode and adjust accordingly. Do not recommend D=9 tasks when mode is RECOVERY.

7. **Deferral is not failure.** When a task is deferred, it is never deleted. It is timestamped, logged in `task_deferrals`, and re-enters the scheduling pool the next day with its existing scores intact. Only the user can kill a task.

8. **The Telegram bot is the primary interface.** All brain endpoints must be callable from the existing Telegram bot handlers. The bot sends the message to `/brain/chat`. The response comes back. That's it.

---

## SUCCESS CRITERIA

The Brain Module is working correctly when:

- A user asks "what syllabi did I generate" → Locus searches Qdrant, finds the real chunks from the real file, and returns actual content. Not invented content.
- A user asks "read [filename]" → Locus opens the actual file, reads it, and the LLM answers only from that content.
- A user asks "what should I do today" → Locus returns a task list computed from today's real DCS, real faction lag scores, and real TWS values.
- A user asks "what patterns do you see in me" → Locus returns data-backed observations from the Pattern Engine, not generic advice.
- Any query about personal data that has no stored records returns: "I don't have that stored yet" — not an invention.

---

*Build this as a series of independent modules, one at a time, starting with Collector → Chunker → Reader → Retriever. Get those four right first. The rest depends on having real data flowing.*
