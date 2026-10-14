# Locus Features — Complete Clock-Model Decomposition (v2 FRESH BUILD)

> **Generated:** 2026-06-16 | **Scope:** All 136 features decomposed to atomic gear depth
> **Methodology:** Clock Model — every feature broken into single-responsibility gears with task trees, data contracts, dependencies, and failure modes
> **Gear types:** [D] = Deterministic (pure logic), [AI] = AI-Based (model call primary), [H] = Hybrid (deterministic scaffolding wraps model call)
> **Target:** Single-user PCOS on Oracle Cloud ARM64 VM, DeepSeek V4 Flash only, tri-store (PostgreSQL 16+pgvector, Neo4j 5.x)

---

## Key Architecture Decisions (v2)

| Decision | v1 (old) | v2 (this) | Why |
|---|---|---|---|
| Retrieval | LightRAG (black-box hybrid) | PageIndex + direct pgvector + direct Neo4j | Query Router + Context Forge already do what LightRAG does. No middle layer. |
| Vault sync | Syncthing (real-time, fragile) | Git (Obsidian Git plugin + GitHub private repo) | Version history free, no extra service, no port issues. Directory partitioning prevents conflicts. |
| Backend → vault writes | Obsidian Local REST API | Direct file write to /vault/ on VM + git commit + push | Works even when Obsidian desktop is closed. Git handles sync. |
| Google OAuth | Composio (managed) | Manual google-api-python-client | 50 lines of code. No external dependency. Full control. |
| Vector DB | Qdrant container | pgvector (PostgreSQL extension) | <50K vectors. One fewer container. Already running PG. |
| Secondary vector DB | ChromaDB | REMOVED | Redundant. |
| Cache/state | Redis (required) | Redis (optional) | At single-user scale, PG + in-memory dict covers all Redis use cases. |
| LLM | Multi-provider cascade | DeepSeek V4 Flash only | One model. One behavior. ~$0.012/day. |
| Graph DB | Neo4j 5.x | Neo4j 5.x (kept) | Hebbian weighting needs native graph traversals. Apache AGE noted as future consolidation option. |

---

## "Huh?" Resolutions

These features had ambiguous descriptions in the original annotated list. Research into original project documents resolved them.

### #7: Behavioral Event Stream — Elaborated

**Original annotation:** "Huh? Elaborate..."

**Resolution:** This is the **foundation of the entire analytical stack.** Every FastAPI endpoint must emit events to `behavioral_events` table via PG LISTEN/NOTIFY. Without it wired into every endpoint, nothing downstream (State Engine, Pattern Engine, Faction Stats, Context Forge, Reward Model) has data. The decomposition stands but emphasis: **#7 is critical-path infrastructure, not optional logging.**

### #49: Thinking Pattern Capture — Researched

**Original annotation:** "Huh?"

**Resolution (from Master Doc §10, §9, LOCUS_BRAIN_MODULE_PROMPT):** DeepSeek scans the AI chat vault (03-AI-Chats) for recurring problem-solving approaches — how the user debugs, decomposes problems, what mental models they favor. Creates ConceptNodes in Neo4j with type='thinking_pattern'. Feeds User Identity. Requires 60+ days of chat data. Categories: decomposition, debugging, learning, communication, avoidance.

### #60: State Engine — "Nope" Rejection Explained

**Original annotation:** "Nope"

**Resolution (from architecture_decisions.md v2):** The v1 design was overly complex — Redis pub/sub, constant NOTIFY listening, AI cause chain on every event. v2 simplifies: single PG row `current_state`, updated on check-in and significant events ONLY, NOT on every behavioral event. Cause chain only when explicitly queried with 30-min cache. The "Nope" rejects the v1 design, not the feature itself. Decomposed as v2 revision.

### #68: Inferred Cause Chain Engine — Researched

**Original annotation:** "Huh?"

**Resolution (from Master Doc §9):** The key differentiating feature. Produces plain-language causal explanations citing specific data — cross-references CURRENT_STATE + historical patterns + user_identity + calendar. Not just a prompt; a dedicated engine with confidence scoring, data source tracking, and historical storage.

### #71: Database Diagnostic Script — Researched

**Original annotation:** "Huh?"

**Resolution (from Master Doc One-Week Plan Day 1, Consolidated Sessions, Jules Prompt):** A comprehensive pre-flight health check that MUST be run before every major dev session. Checks: PG row counts, Neo4j node/edge counts, pgvector collection sizes, vault file count, Redis key count. The Jules prompt says: "Run scripts/diagnose_databases.py first. Do not proceed until health report is reviewed."

---

## Pen Remark Overrides

These are cases where the Pen Remarks column in the annotated features doc changed the decomposition direction from what the Description/Notes suggested.

| # | Pen Remark | Impact on Decomposition |
|---|---|---|
| 1 | "Design like an OS: each faction is a process fighting for CPU time" | Factions designed as kernel processes with priority scheduling, not just tags |
| 12 | "Use slash command or intelligent detection through SOUL.md. Semi-deterministic" | Emergency injection split: deterministic protocol for known emergencies, AI-based for detected ones |
| 13 | "Logic? Determined or Autonomous?" | Confirmed deterministic via cron jobs; Phase 2 AI enhancement optional |
| 14 | "Define logic → Deterministic based on data points. Not LLM based at all!" | Removed any LLM from rebalance; pure SQL aggregation |
| 16 | "Autonomously + invokeable sub-agents. Need a doc with problem solving philosophy" | Parallel optimizer is [H] not [D]; requires SOUL.md problem-solving doc |
| 24 | "Logic? Deterministic but using AI → Outsource to 'agy'" | Self-maintenance outsourced to external tool; Locus only creates the trigger task |
| 27 | "Define logic → Autonomous yet deterministic. Scope note: ALL ChatGPT accounts (×3), Claude, Gemini, Perplexity" | Nightly ingestion expanded to multi-account scraping, not single |
| 52 | "Self callable Skills + MCPs. Pre-load some skills and MCPs" | Skills registry designed for self-invocation, not just routing |
| 64 | "Define logic. Deterministic — concrete rules + verification from user, not LLM-decreed" | Hebbian weights follow fixed formulas; user 👍/👞 is the only feedback signal |
| 84 | "Deterministic. Invokeable by /commands + Skill. Use best strategy. Either 5 sub agents or 2 agent debate?" | Council uses 3 agents (Architect/Reviewer/Pragmatist) |
| 85 | "Already addressed. Make this integration possible through Obsidian or Telegram" | Social integrations implement through existing Telegram/Obsidian channels |
| 86 | "Already done / accounted for" | Pi Sub-Agents marked as already covered; minimal decomposition |
| 128 | "Research first. Define weight dimensions + algorithm" | Dijkstra scheduling starts with research phase before implementation |

---

## Feature Consolidations

Features merged from multiple IDs into a single decomposition.

| Consolidated Into | Original Features | Rationale |
|---|---|---|
| #27 (Nightly Ingestion) | #42 (Vault Processing Pipeline) + #46 (Daily AI Chat Archiver) + #80 (Daily AI Chat Archiver Cron) | Same pipeline — crawl, scrape, process, embed. |
| #32 (Self-Evolving Architecture) | #77 (Self-Evolving System Philosophy) + #106 (Self-Improving Architecture) | Same mechanism — reward-driven evolution. |
| #36 (Obsidian Dashboard) | #54 (Progress Visualization Dashboard) | Single dashboard, not separate. |
| #39 (Structured Check-ins) | #53 (Push Notification Reminders) | Notifications ARE the check-in channel. |
| #41 (Visual Avatar) | #78 (Holistic Avatar) + #79 (Avatar Animated States) | Single visual representation. |
| #64 (Hebbian Memory) | #99 (Spaced Repetition) + #107 (Project-Specific Memory Decay) | Same weight math, different decay triggers. |
| #78 (Dynamic MCP Integration) | #114 (Inter-Harness Communication) + #115 (GitMCP Repo Parsing) + #116 (Graphify Coding Assistant) | All MCP dynamic capabilities under one feature. |

---

## Deleted / Ignored / Scrapped Features

| # | Feature | Disposition | Reason |
|---|---|---|---|
| 33 | Multi-Dimensional Graph Nodes | 🔴 Scrapped | Unnecessary — Neo4j schema already supports multiple edge types |
| 55 | Personality + "Wants" Engine | ⏭️ Ignored | Needs brainstorming; SOUL.md already covers identity |
| 62 | User Identity Profile | ➡️ Duplicate | Addressed within #29 Personality Profile |
| 65 | LOCUS_SHORTHAND Compression | ⏭️ Ignored | Was an experiment; outside short-term scope |
| 66 | Multi-Provider LLM Cascade | 🗑️ Delete | DeepSeek only. Deprecated by architecture decision. |
| 72 | Vilix Evaluation | ⏭️ Ignored | Decision criteria deferred |
| 73 | Locus "Wants" + Autonomous Goal Formation | ⏭️ Ignored | Phase 2+; too speculative |
| 74 | Locus Builds and Operates the Life OS | ⏭️ Ignored | Meta-feature; emerges from other features |
| 75 | Obsidian-Centric Interactions | 🗑️ Delete | Already accounted for in #36, #39, #43 |
| 80 | Local-First Obsidian Storage | 🗑️ Delete | DB is not volatile cache; vault is not single source of truth for analytical state |
| 81 | Stateless 24-Hour Session Logs | 🗑️ Delete | Stateless contradicts Locus design |

---

## Feature Decompositions

---

### #1: Four Factions Framework [D]

**Purpose:** Four factions as OS processes fighting for CPU time (attention/hours). Kernel = master scheduler.

**Trigger / Invocation:** Seed on first start; referenced by every task/project/scheduling operation.

**Task Tree:**
- 1.1 [D] Schema — `factions` table: id, name, color_hex, icon, weekly_target_hours, priority_rank
- 1.2 [D] Seed — 4 rows: Health/Stability (#22C55E), Leverage/Money (#3B82F6), Craft/Skills (#F97316), Expression/Exploration (#A855F7)
- 1.3 [D] FK constraint — `projects.faction_id` → `factions.id`, `tasks.faction_id` → `factions.id`

**Data Contracts:**
- `factions`: `{id UUID PK, name TEXT UNIQUE, color_hex TEXT, icon TEXT, weekly_target_hours INT, priority_rank INT, created_at TIMESTAMPTZ}`
- Every task/project requires valid faction_id

**Dependencies:** None (foundational)

**Failure Modes & Fallbacks:** Seed failure → system can't start; all other features depend on this.

---

### #2: Daily Capacity Score (DCS) [D]

**Purpose:** DCS = ((Energy + Mood + Sleep) / 3) × (1 − Stress/20). Morning metric drives operating mode.

**Trigger / Invocation:** Telegram /checkin → inline keyboard → E, M, S, ST (0-10 each), T (top task). GENERATED ALWAYS AS column.

**Task Tree:**
- 2.1 [D] `daily_checkins` table with GENERATED ALWAYS AS dcs column
- 2.2 [D] Telegram InlineKeyboard — tap E (0-10), M (0-10), S (0-10), ST (0-10), T (text)
- 2.3 [D] Mode derivation — CASE statement: ≥ 8 → PEAK, ≥ 6.5 → DEEP_WORK, ≥ 4.5 → NORMAL, ≥ 2.5 → RECOVERY, < 2.5 → SURVIVAL

**Data Contracts:**
- DCS formula columns computed; mode derived via SQL view
- Input via Telegram inline keyboard only

**Dependencies:** #1 (Factions) for task associations

**Failure Modes & Fallbacks:** User skips check-in → no DCS for that day; scheduler uses yesterday's DCS

---

### #3: Five Operating Modes [D]

**Purpose:** DCS range → mode → schedule weightage + expected output of the day.

**Trigger / Invocation:** Derived automatically from DCS on check-in. Propagated to Scheduler as task filter.

**Task Tree:**
- 3.1 [D] Python enum OperatingMode: SURVIVAL, RECOVERY, NORMAL, DEEP_WORK, PEAK
- 3.2 [D] DCS-range mapping dict: (0-2.5→SURVIVAL, 2.5-4.5→RECOVERY, 4.5-6.5→NORMAL, 6.5-8→DEEP_WORK, 8-10→PEAK)
- 3.3 [D] Scheduler filter — only recommend tasks matching current mode difficulty
- 3.4 [D] Stored as TEXT on daily_checkins

**Data Contracts:** Python enum + PG TEXT column; 10 lines of Python

**Dependencies:** #2 (DCS)

**Failure Modes & Fallbacks:** Mode defaults to NORMAL if DCS unavailable

---

### #4: Task Weight Score (TWS) [D]

**Purpose:** TWS = (Priority×0.4) + (Urgency×0.4) + (Difficulty×0.2). Lag bonus applied at scheduling time.

**Trigger / Invocation:** GENERATED ALWAYS AS column on tasks. Lag bonus applied via SQL join at scheduling.

**Task Tree:**
- 4.1 [D] GENERATED ALWAYS AS column on tasks: (priority * 0.4 + urgency * 0.4 + difficulty * 0.2)
- 4.2 [D] Lag bonus dynamic at scheduling time via SQL JOIN to faction_weekly_stats — NOT stored on task

**Data Contracts:** TWS is computed column, not stored; lag bonus is ephemeral query-time addition

**Dependencies:** #6 (Faction Stats), #11 (Lag Score)

**Failure Modes & Fallbacks:** All fields default to 5 (medium) if not set

---

### #5: Goal Stack Architecture [D]

**Purpose:** 3-layer: Outcomes (WHY, max 7) → Projects (WHAT, max 3 active/faction) → Tasks (HOW). Status: active/paused/completed/dead_node.

**Trigger / Invocation:** Goal distiller parses Goals.md from vault → upserts. Dataview displays goal tree.

**Task Tree:**
- 5.1 [D] Three PG tables: outcomes (max 7), projects (FK to outcomes, max 3 active/faction), tasks (FK to projects)
- 5.2 [D] Status enum: active/paused/completed/dead_node
- 5.3 [D] Goal distiller — read /vault/01-System/Goals.md → parse Markdown headings → upsert to PG
- 5.4 [D] Dataview queries in Obsidian Dashboard display goal tree from JSON pushes

**Data Contracts:** `outcomes: {id, title, description, rank 1-7, status, created_at}`, `projects: {id, outcome_id FK, faction_id FK, title, status, max 3 active per faction}`, `tasks: {id, project_id FK, title, status, ...}`

**Dependencies:** #1 (Factions)

**Failure Modes & Fallbacks:** Goals.md missing → empty goal stack; max 7 enforcement rejects overflow

---

### #6: Faction Weekly Stats Tracking [D]

**Purpose:** Target vs actual hours per faction per week. Compute CR, CS, MS, LS, AG.

**Trigger / Invocation:** APScheduler Sunday cron. Push JSON to vault.

**Task Tree:**
- 6.1 [D] APScheduler Sunday 23:00 IST — compute from task_completions + time_logs
- 6.2 [D] SQL aggregation: completion_rate, completion_score, momentum_score, lag_score, action_gap per faction
- 6.3 [D] Write to faction_weekly_stats table
- 6.4 [D] Push JSON to /vault/00-System-Data/faction_stats.json → git commit + push

**Data Contracts:** `faction_weekly_stats: {id, faction_id, week_start DATE, target_hours, actual_hours, completion_rate FLOAT, completion_score FLOAT, momentum_score FLOAT, lag_score FLOAT, action_gap FLOAT}`
- JSON to vault for Obsidian Charts

**Dependencies:** #1 (Factions), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** No tasks completed → all zeros; cron miss → next run picks up

---

### #7: Behavioral Event Stream [D]

**Purpose:** Log every significant action/inaction as event. Foundation of all downstream analytical features. **Must be wired into every endpoint.**

**Trigger / Invocation:** Every FastAPI endpoint emits on any state change. PG LISTEN/NOTIFY triggers downstream consumers.

**Task Tree:**
- 7.1 [D]`behavioral_events` table: id, event_type (enum), entity_type, entity_id, event_data (JSONB), source (telegram/obsidian/system/cron), created_at
- 7.2 [D] Event emission on: task created/completed/deferred, checkin submitted, project status change, Telegram message, vault change detected, review generated, alert fired
- 7.3 [D] PG LISTEN/NOTIFY on INSERT → real-time subscribers (State Engine, Pattern Engine, Context Forge)
- 7.4 [D] Helper function: `emit_event(event_type, entity_type, entity_id, event_data, source)` — called in every router

**Data Contracts:**
- `behavioral_events: {id UUID PK, event_type behavioral_event_type, entity_type TEXT, entity_id UUID, event_data JSONB, source TEXT, created_at TIMESTAMPTZ}`
- event_type enum: task_created, task_completed, task_deferred, checkin_submitted, project_status_changed, telegram_message, vault_file_changed, review_generated, alert_fired, injection_triggered

**Dependencies:** None (infrastructure feature)

**Failure Modes & Fallbacks:** PG NOTIFY queue full → events still logged (NOTIFY is fire-and-forget); no fallback needed — PG is durable

---

### #8: Action Gap Tracking [D]

**Purpose:** AG = declared_priority − (actual_hrs / target_hrs × 10). Alert if gap > 5.

**Trigger / Invocation:** Computed inside weekly stats job (#6). AG > 5 → Telegram warning.

**Task Tree:**
- 8.1 [D] AG = declared_priority − (actual_hrs / target_hrs × 10) — computed in weekly stats SQL
- 8.2 [D] AG > 5 → INSERT behavioral_event (type='action_gap_alert')
- 8.3 [D] Surfaced in weekly review (#18) and Dashboard

**Data Contracts:** Value 0-10 (negative = faction getting more time than declared priority)

**Dependencies:** #6 (Faction Weekly Stats), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** No time logged → AG cannot be computed → no alert

---

### #9: Deferral Detection (3/5/8+ rule) [D]

**Purpose:** Flag tasks deferred 3×, 5×, 8+ times.

**Trigger / Invocation:** task_deferrals table tracks each deferral with timestamp + reason_code. Affirmative action at thresholds.

**Task Tree:**
- 9.1 [D] task_deferrals table: id, task_id FK, deferred_at, reason_code (enum: blocked/no_time/low_energy/avoidance/other), previous_scheduled_date
- 9.2 [D] Threshold logic: 3× → behavioral_event FLAG type='deferral_threshold_3'; 5× → Telegram alert with task; 8+ → escalate in weekly review + Inner Loop
- 9.3 [D] Count computed via COUNT(*) FROM task_deferrals WHERE task_id = $1

**Data Contracts:** `task_deferrals: {id, task_id FK, deferred_at, reason_code TEXT, previous_scheduled_date DATE}`

**Dependencies:** #5 (Goal Stack), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** None — deferral is always explicit user action

---

### #10: Dead Node Detection [D]

**Purpose:** Flag outcomes/projects untouched 60+ days.

**Trigger / Invocation:** APScheduler weekly cron. Telegram inline keyboard: [Recommit] [Kill] [Pause].

**Task Tree:**
- 10.1 [D] Query: `SELECT * FROM projects WHERE last_touched_at < NOW() - INTERVAL '60 days' AND status = 'active'`
- 10.2 [D] Update status to 'dead_node'
- 10.3 [D] Telegram alert with InlineKeyboard: Recommit (reset last_touched_at), Kill (status→completed), Pause (status→paused)

**Data Contracts:** `last_touched_at` updated on any task completion/creation within project. Status enum: active/paused/completed/dead_node.

**Dependencies:** #7 (Behavioral Events tracks last_touched_at)

**Failure Modes & Fallbacks:** None — pure date comparison

---

### #11: Lag Score + TWS Lag Bonus [D]

**Purpose:** LS = target − actual hours. Lag score > thresholds → TWS bonus at scheduling time.

**Trigger / Invocation:** LS computed in weekly stats (#6). Applied at scheduling via SQL join.

**Task Tree:**
- 11.1 [D] LS = target_hours − actual_hours (from faction_weekly_stats)
- 11.2 [D] Scheduling query: CASE WHEN LS > 6 THEN TWS + 4 WHEN LS > 3 THEN TWS + 2 WHEN faction_ahead THEN TWS − 1 ELSE TWS

**Data Contracts:** LS is per-faction weekly aggregation; NOT persisted on individual tasks

**Dependencies:** #4 (TWS), #6 (Faction Weekly Stats)

**Failure Modes & Fallbacks:** No weekly stats → LS = 0 → no bonus applied

---

### #12: Emergency Task Injection Protocol [H]

**Purpose:** Insert emergency task, recalculate day, protect non-negotiables. Slash command /emergency or intelligent detection via SOUL.md.

**Trigger / Invocation:** Telegram /emergency {task} or detected from user message via DeepSeek intent classification.

**Task Tree:**
- 12.1 [D] New task → compute TWS → compare to all currently scheduled tasks
- 12.2 [D] If TWS > lowest scheduled → replace lowest non-locked task
- 12.3 [D] Deferred task gets urgency + 2
- 12.4 [D] If urgency = 10 → clear ALL discretionary tasks (is_locked must be false)
- 12.5 [AI] Intelligent detection: DeepSeek classifies user message as emergency intent (FACTUAL_PERSONAL with emergency flag)

**Data Contracts:** `tasks.is_locked BOOLEAN` protects non-negotiables; slot replacement is deterministic sort

**Dependencies:** #4 (TWS), #5 (Goal Stack)

**Failure Modes & Fallbacks:** All slots locked → Telegram: "No room today, schedule tomorrow?"; AI false positive → user ignores (no harm)

---

### #13: Exhaustion Predictor [H]

**Purpose:** Predict overload from recent data. Auto-adjust timetable.

**Trigger / Invocation:** APScheduler cron, regular intervals (30-45 days). Deterministic rule fires first; AI enhancement Phase 2.

**Task Tree:**
- 13.1 [D] Rule-based: IF avg_task_difficulty(5d) > 7 AND avg_DCS(5d) < 5 → exhaustion_risk flag
- 13.2 [D] On flag: reduce next-day load 30% (remove tasks from schedule_bucket by lowest TWS)
- 13.3 [AI] Phase 2: DeepSeek analyzes 30-day behavioral window for nuanced patterns
- 13.4 [D] Requires 60+ days logged data for Phase 2

**Data Contracts:** `exhaustion_risk` in behavioral_events; schedule_bucket modification at query time

**Dependencies:** #2 (DCS), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** <60 days → rule-based only; false positive → user adds tasks back manually

---

### #14: Weekly Faction Rebalance [D]

**Purpose:** End-of-week: which faction is starving? Boost next week. Deterministic based on data points, NOT LLM.

**Trigger / Invocation:** Sunday cron (#6). Starving factions get automatic TWS bonus via #11.

**Task Tree:**
- 14.1 [D] Sunday cron (#6) computes lag scores
- 14.2 [D] LS > 3h → starving; TWS bonus applied automatically via #11
- 14.3 [D] Rebalance recommendations written to /vault/06-Reviews/weekly/YYYY-WW.md → git commit + push

**Data Contracts:** Written to weekly review markdown + TWS bonus at scheduling time

**Dependencies:** #6 (Faction Weekly Stats), #11 (Lag Score + TWS Bonus)

**Failure Modes & Fallbacks:** All factions on target → no rebalance needed; no weekly stats → skip

---

### #15: Momentum Score (MS) [D]

**Purpose:** Avg completion rate over last 3 weeks per faction.

**Trigger / Invocation:** Computed in weekly stats (#6). SQL window function.

**Task Tree:**
- 15.1 [D] MS = AVG(completion_rate) FROM faction_weekly_stats WHERE week >= current_week − 3
- 15.2 [D] Displayed in Dashboard via pushed JSON to vault

**Data Contracts:** Single FLOAT per faction; null for <3 weeks of data

**Dependencies:** #6 (Faction Weekly Stats)

**Failure Modes & Fallbacks:** <3 weeks data → null; displays as "building..."

---

### #16: Parallel Task Execution Optimizer [H]

**Purpose:** Identify tasks that can run simultaneously. Phase 2. Requires SOUL.md problem-solving philosophy document.

**Trigger / Invocation:** Scheduling time. Telegram /parallel {tasks}. Autonomous sub-agent invocation.

**Task Tree:**
- 16.1 [D] task_dependencies junction table: task_id, depends_on_task_id, dependency_type (blocks/blocks_if/enables/related)
- 16.2 [AI] DeepSeek identifies parallelizable tasks from descriptions + dependencies
- 16.3 [D] Scheduler: topological sort → independent chains → parallel slots
- 16.4 [D] Display: "These 3 tasks can run simultaneously: [list]"

**Data Contracts:** `task_dependencies: {id PK, task_id FK, depends_on_task_id FK, dependency_type TEXT}`

**Dependencies:** #4 (TWS), #5 (Goal Stack)

**Failure Modes & Fallbacks:** No dependencies defined → "all sequential" (safe default); AI misidentifies → user corrects

---

### #17: Three-Birds-One-Stone Efficiency Mapping [H]

**Purpose:** Tag tasks serving multiple factions. Cross-faction tasks get TWS + 1 per extra faction.

**Trigger / Invocation:** On task creation. DeepSeek suggests cross-faction mapping.

**Task Tree:**
- 17.1 [D] M2M junction table task_factions: task_id, faction_id, weight_share FLOAT (default equal split)
- 17.2 [AI] DeepSeek suggests faction mapping from task description: "This task serves which factions?"
- 17.3 [D] Boost: cross-faction tasks get TWS + 1 per extra faction (capped at +3)
- 17.4 [D] Time splits proportionally among associated factions

**Data Contracts:** `task_factions: {task_id FK, faction_id FK, weight_share FLOAT DEFAULT 1.0}`

**Dependencies:** #1 (Factions), #4 (TWS)

**Failure Modes & Fallbacks:** No cross-faction → single-faction default; AI suggests wrong faction → user reassigns

---

### #18: Review Cadence System [D + AI]

**Purpose:** Daily / Weekly / Monthly / Quarterly reviews with checklists. Deterministic scheduling, AI content.

**Trigger / Invocation:** APScheduler: Daily 22:00, Sunday 20:00, Last day of month, Last day of quarter.

**Task Tree:**
- 18.1 [D] APScheduler triggers per cadence
- 18.2 [AI] Daily: Telegram 3-sentence prompt from DeepSeek: "3 things you accomplished, 1 thing you deferred, readiness for tomorrow"
- 18.3 [AI] Weekly: DeepSeek generates narrative from weekly stats + events
- 18.4 [D] Write to /vault/06-Reviews/{cadence}/YYYY-MM-DD.md → git commit + push

**Data Contracts:** Markdown files in vault with YAML frontmatter; templates in Obsidian Templater

**Dependencies:** #6 (Faction Stats), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** DeepSeek down → review uses template without AI content; cron miss → skipped (next day picks up)

---

### #19: Oracle Cloud ARM64 VM [Infra]

**Purpose:** 4 OCPU, 24GB RAM, 200GB, Ubuntu 22.04 at 140.238.245.25. Always free tier.

**Current state:** Already provisioned and running.

**Dependencies:** None (foundational)

---

### #20: Docker Stack [Infra]

**Purpose:** Three containers: PG 16+pgvector, Neo4j 5.x, Redis 7.x (optional). REMOVED: Qdrant, ChromaDB.

**Task Tree:**
- 20.1 [D] docker-compose.yml with health checks
- 20.2 [D] Memory limits enforced per container
- 20.3 [D] Volumes for data persistence

**Dependencies:** #19 (VM)

---

### #21: Cloudflare Tunnel [Infra]

**Purpose:** api.locusapp.online → localhost:8000 via cloudflared as systemd service. Already configured.

**Dependencies:** #19 (VM)

---

### #22: Vault Sync via Git [D]

**Purpose:** GitHub private repo for vault. Obsidian Git plugin auto-commit/push/pull. Backend writes directly.

**Trigger / Invocation:** Obsidian Git plugin every 10min; VM cron `git pull` every 5min; Backend writes → git add + commit + push.

**Task Tree:**
- 22.1 [D] Directory partitioning: User writes /01-System/, /02-Captures/, /04-Resources/, /05-Journal/; Backend writes /00-System-Data/, /03-AI-Chats/, /06-Reviews/, /07-Morning-Briefs/
- 22.2 [D] SSH key auth to GitHub
- 22.3 [D] Backend write helper: write_file(path) → git add → git commit → git push
- 22.4 [D] VM cron: git -C /vault pull every 5min

**Data Contracts:** No overlap directories = no merge conflicts

**Dependencies:** Git, GitHub private repo, SSH keys configured

**Failure Modes & Fallbacks:** Git push conflict → stall (no auto-merge); pull fails → wait for next cycle; Obsidian not running → write still works

---

### #23: FastAPI Backend [Infra]

**Purpose:** Python FastAPI with routers, Uvicorn ASGI, DeepSeek SDK singleton.

**Routers:** /checkins, /tasks, /goals, /factions, /schedule, /brain, /vault, /events, /reviews. All emit behavioral events (#7).

**Dependencies:** #20 (Docker), #21 (Cloudflare)

---

### #24: Self-Maintenance System [H]

**Purpose:** Auto-update deps. If breakage: create P1 fix task + diagnostic. Outsourced to 'agy' (Google Antigravity CLI).

**Trigger / Invocation:** APScheduler monthly cron.

**Task Tree:**
- 24.1 [D] pip-audit for security → if critical → P1 task created
- 24.2 [D] Post-update: run pytest → if failures → Telegram alert with [Rollback] [Fix]
- 24.3 [D] Outsourced to agy CLI for actual execution

**Dependencies:** agy CLI installed

**Failure Modes & Fallbacks:** agy unavailable → manual self-maintenance

---

### #25: Local Database Mirror [D]

**Purpose:** Sync VM databases to local for offline access. Phase 2.

**Trigger / Invocation:** APScheduler nightly: pg_dump → rsync.

**Task Tree:**
- 25.1 [D] pg_dump --format=custom nightly
- 25.2 [D] rsync to local machine via SSH

**Dependencies:** SSH access from local to VM

---

### #26: PageIndex + Direct Retrieval [H]

**Purpose:** Embed entire Obsidian notes as vectors. Direct pgvector + Neo4j queries. No middleware.

**Trigger / Invocation:** On every vault file change (via git diff). On every query via Query Router.

**Task Tree:**
- 26.1 [D] vault_vectors: file_path, chunk_index (0 = whole note), embedding vector(384) via FastEmbed, content_preview, updated_at
- 26.2 [D] Notes 200-800 words → embed whole as single vector
- 26.3 [D] AI chats >2000 words → chunk at sentence boundaries via spaCy
- 26.4 [AI] Entity extraction during ingestion: DeepSeek → entities + relationships → Neo4j

**Data Contracts:** 384-dim vectors (BAAI/bge-small-en-v1.5); chunk_index 0 = whole note

**Dependencies:** FastEmbed (local, free), spaCy en_core_web_sm, pgvector extension

**Failure Modes & Fallbacks:** DeepSeek down → skip entity extraction, embed raw; FastEmbed fails → skip indexing

---

### #27: Nightly Vault Ingestion Pipeline [H] (Consolidates #42, #46, #80)

**Purpose:** Nightly cron (23:30 IST): scan vault, scrape external AI chats (ChatGPT ×3, Claude, Gemini, Perplexity), parse, embed, extract entities, push to Neo4j + pgvector.

**Trigger / Invocation:** APScheduler 23:30 IST daily.

**Task Tree:**
- 27.1 [D] Vault crawl via git diff OR MD5 comparison against vault_files table → new/changed only
- 27.2 [H] External chat scraping via Playwright persistent browser contexts (3 ChatGPT accounts, Claude, Gemini, Perplexity)
- 27.3 [D] Tagged .md with YAML frontmatter → /vault/03-AI-Chats/{source}/ → Telegram alert
- 27.4 [D] If <800 words: embed whole (PageIndex #26); else spaCy chunk
- 27.5 [AI] DeepSeek entity extraction → Neo4j
- 27.6 [D] Embeddings → pgvector
- 27.7 [D] PDFs/non-text → MinerU (AGPL-3.0, CPU)

**Data Contracts:** New chats identified by unique ID; log changes in old chats; git diff avoids reprocessing

**Dependencies:** #22 (Vault Sync), #26 (PageIndex), Playwright, MinerU, FastEmbed, spaCy

**Failure Modes & Fallbacks:** DeepSeek down → skip entity extraction, embed raw; Playwright timeout → skip scraper for that source; MinerU fails → skip PDF

---

### #28: Weekly Full Vault Synthesis [AI]

**Purpose:** Sunday 02:00 — full behavioral analysis. Generate personality drift report, faction narrative, top 3 observations.

**Trigger / Invocation:** APScheduler Sunday 02:00 IST.

**Task Tree:**
- 28.1 [D] Collect: behavioral_events (7d), faction_weekly_stats, detected_patterns, CURRENT_STATE, top 10 Hebbian pathways
- 28.2 [AI] DeepSeek generates: personality drift report, faction narrative, top 3 observations (~3000 tokens)
- 28.3 [D] Write to weekly_reviews table + /vault/06-Reviews/weekly/YYYY-WW-synthesis.md → git commit + push

**Data Contracts:** ~3000 token DeepSeek call; Markdown + YAML output

**Dependencies:** #6 (Faction Stats), #7 (Events), #61 (Pattern Engine), #60 (State Engine), #64 (Hebbian)

**Failure Modes & Fallbacks:** DeepSeek down → skip; no data this week → "Insufficient data"

---

### #29: Personality Profile Building [H]

**Purpose:** Auto-build user personality model from chats + behavioral graph. Rolling updates when patterns confirmed.

**Trigger / Invocation:** Pattern Engine (#61) auto-updates user_identity when patterns confirmed (confidence > 0.75, count > 2).

**Task Tree:**
- 29.1 [AI] DeepSeek synthesizes quarterly comprehensive profile from all accumulated data
- 29.2 [D] Neo4j Person node mirrors profile properties
- 29.3 [D] Rolling updates: confidence-weighted average, never hard overwrite

**Data Contracts:** Neo4j Person node with profile properties; PG user_identity table updated

**Dependencies:** #61 (Pattern Engine), #62 (User Identity), #7 (Events)

**Failure Modes & Fallbacks:** <30 days data → "still learning"; conflicting signals → store both with confidences

---

### #30: Fine-Tuning / RLHF [Phase 3]

**Purpose:** Fine-tune model on user's data once GPU available. QLoRA via Unsloth on small model.

**Key notes:** Phase 3. Collect 500+ labeled examples from reward_signals. LoRA adapter (50-200MB) via Ollama.

**Dependencies:** #63 (Reward Model), GPU rental via vast.ai

---

### #31: Subagentic Capabilities [Phase 3]

**Purpose:** Spawn agents on-demand for new task types. DeepSeek orchestrates tool calls via MCP: plan → execute → observe → re-plan.

**Dependencies:** #78 (Dynamic MCP), #86 (Pi Sub-Agents), SOUL.md

---

### #32: Self-Evolving Architecture + Architect Bot [H] (Consolidates #77, #106)

**Purpose:** Internal bot that improves Locus. Three mechanisms: SOUL.md quarterly updates, Reward Model improves quality gate, Hebbian weighting tunes retrieval. No weight changes — behavioral tuning only.

**Trigger / Invocation:** Quarterly (SOUL.md), weekly (Reward Model retrain), continuous (Hebbian).

**Task Tree:**
- 32.1 [H] DeepSeek scans reward_signals for underperforming components → generates patches with tests
- 32.2 [D] LOW risk → auto-deploy; HIGH risk → Telegram /approve
- 32.3 [AI] SOUL.md updated quarterly via DeepSeek + user approval
- 32.4 [D] Reward Model weekly retrain improves quality gate
- 32.5 [D] Hebbian weighting continuous tuning

**Data Contracts:** Patch = code diff + test assertions; Risk assessed by scope (file count, DB schema change)

**Dependencies:** #63 (Reward Model), #64 (Hebbian), SOUL.md

**Failure Modes & Fallbacks:** Patch breaks tests → revert + create fix task; user rejects → discard

---

### #33: Multi-Dimensional Graph Nodes — SCRAPPED

Unnecessary — Neo4j schema already supports multiple edge types between same pair.

---

### #34: 3-Level Tag Hierarchy [D]

**Purpose:** faction/domain/specific tags enforced. Autonomous for every note.

**Trigger / Invocation:** On every ingestion. Python script enforces.

**Task Tree:**
- 34.1 [D] Tags registry in PG tags table
- 34.2 [D] Python script validates tag format: faction/domain/specific
- 34.3 [D] Auto-suggest tags from note content via regex (no AI)

**Data Contracts:** `tags: {id PK, full_path TEXT, level INT, parent_id FK}`

**Dependencies:** #27 (Ingestion)

---

### #35: Audio Transcription Pipeline [H]

**Purpose:** Whisper-large-v3-turbo via Groq. Auto-detect Hinglish. Output → vault .md → embedding pipeline.

**Trigger / Invocation:** On new audio file in vault. Autonomous for every audio file (voice note, phone call, podcast).

**Task Tree:**
- 35.1 [H] Groq Whisper API (free tier) → transcription
- 35.2 [D] Output → vault .md with YAML frontmatter → git commit + push
- 35.3 [D] Falls into embedding pipeline (#26) on next ingestion

**Dependencies:** Groq API key, #26 (PageIndex)

**Failure Modes & Fallbacks:** Groq rate-limited → queue retry; alternative: whisper-cpp local (slower on ARM64)

---

### #36: Obsidian Dashboard + Progress Visualization [D] (Consolidates #54)

**Purpose:** Central Obsidian dashboard with Dataview queries + Charts. Panels: Today's Schedule, Faction Health, Active Patterns, Goal Stack, Hebbian Pathways, Brain Observations.

**Trigger / Invocation:** On vault sync. Backend pushes stats JSON → Dataview reads.

**Task Tree:**
- 36.1 [D] Dashboard.md with Dataview queries
- 36.2 [D] Backend pushes stats JSON to /vault/00-System-Data/stats.json → git commit + push
- 36.3 [D] Obsidian Charts (Chart.js-based) renders DCS trends, faction time, completion rates

**Panels:** Today's Schedule, Faction Health (CR/MS/LS/AG), Active Patterns, Goal Stack, Hebbian Pathways, Brain Observations, DCS Trend (7d)

**Dependencies:** #22 (Vault Sync), Obsidian Dataview plugin, Obsidian Charts plugin (optional)

---

### #37: Rough Note Parser / Idea Tracker [H]

**Purpose:** Capture rough notes, enhance, convert to tasks. Telegram /idea → captures table. DeepSeek optionally suggests faction mapping + project.

**Trigger / Invocation:** Telegram /idea {text} or /dump {text}. DeepSeek expands autonomously.

**Task Tree:**
- 37.1 [D] captures table: type='idea', raw_text, enhanced_text, faction_id, project_id, status
- 37.2 [AI] DeepSeek optionally: expand idea, research (web search), suggest faction mapping + project
- 37.3 [D] Telegram inline: [Promote to Task] [Research] [Archive]
- 37.4 [D] On Promote to Task: INSERT into tasks, create note in /vault/02-Captures/

**Data Contracts:** `captures: {id, type, raw_text, enhanced_text, url, tags JSONB, faction_id FK, project_id FK, status, created_at}`

**Dependencies:** #5 (Goal Stack), #1 (Factions), #43 (Telegram Bot)

**Failure Modes & Fallbacks:** DeepSeek down → store raw; no faction match → unassigned

---

### #38: Link Dump / Resource Logger [D]

**Purpose:** Save and tag URLs. Telegram /link {url}. Store + archive.

**Trigger / Invocation:** Telegram /link {url} or /dump {url}.

**Task Tree:**
- 38.1 [D] captures table: type='link', url, tags
- 38.2 [D] Note in /vault/04-Resources/ → git commit + push
- 38.3 [H] DeepSeek optional: auto-summary + suggest tags + web scrape page

**Dependencies:** #43 (Telegram Bot)

---

### #39: Structured Check-ins + Push Notifications [D+AI] (Consolidates #53)

**Purpose:** 4 daily check-ins (Morning/Afternoon/Evening/Night) via Telegram push notifications + inline keyboard. Log anytime. DCS computed automatically.

**Trigger / Invocation:** APScheduler at 07:30/13:00/18:00/22:00 IST. User can also /checkin anytime.

**Task Tree:**
- 39.1 [D] APScheduler 4× daily → Telegram inline keyboard (tap numbers, no typing)
- 39.2 [D] DCS computed automatically (#2)
- 39.3 [D] User can attach notes to justify/explain stats
- 39.4 [AI] Evening 22:00: DeepSeek optional 3-sentence summary of day
- 39.5 [D] Data pushed to /vault/00-System-Data/daily/YYYY-MM-DD.json → git sync

**Data Contracts:** JSON per day with all check-in data + DCS + mode

**Dependencies:** #2 (DCS), #43 (Telegram Bot), #7 (Events)

**Failure Modes & Fallbacks:** User ignores push → no check-in; always allow manual /checkin

---

### #40: Design Thinking UX Overhaul [Phase 2]

**Purpose:** Design principles applied to Dashboard. Custom CSS for Obsidian (dark theme, amber accents).

**Dependencies:** #36 (Dashboard), Obsidian Minimal theme

---

### #41: Visual Health Avatar / Tree of Life [Phase 3] (Consolidates #78, #79)

**Purpose:** Composite faction score → 5 animated SVG/CSS states (blooming → wilting). Single glance = system health.

**Dependencies:** #36 (Dashboard), Lottie or CSS-animated SVG

---

### #42: Google Calendar Integration [F]

**Purpose:** OAuth + Calendar read/write for schedule injection. Read events as scheduling constraints. Write faction-colored blocks. Never overwrite existing events without authorization.

**Trigger / Invocation:** OAuth flow on setup. APScheduler hourly sync.

**Task Tree:**
- 42.1 [D] Google Cloud Console → Calendar API + Gmail API → OAuth credentials → .env
- 42.2 [D] FastAPI /auth/google → redirect → callback stores refresh_token in PG oauth_tokens (encrypted)
- 42.3 [D] google-auth library auto-refresh
- 42.4 [D] Read events as scheduling constraints → schedule_blocks table
- 42.5 [D] Write faction-colored blocks (Locus-created events tagged, never overwrite user-created)

**Data Contracts:** `oauth_tokens: {id, provider TEXT, encrypted_token TEXT, scopes TEXT[], expires_at}`

**Dependencies:** google-api-python-client, google-auth-oauthlib

**Failure Modes & Fallbacks:** Token expired → auto-refresh; refresh fails → Telegram: "Re-auth Google"; API rate-limit → backoff retry

---

### #43: Telegram Bot (Second Brain Chat) [F]

**Purpose:** Full conversational pipeline to vault. ALL messages logged. Commands: /checkin, /dcs, /tasks, /schedule, /goals, /idea, /link, /weekly, /debug, /state.

**Trigger / Invocation:** User sends message to Telegram bot.

**Task Tree:**
- 43.1 [D] Intercept ALL messages → log to telegram_logs (#51)
- 43.2 [AI] Query Router (#57) → classify intent (~50 tokens)
- 43.3 [H] Retriever: pgvector semantic search + Neo4j graph traversal + PG structured queries
- 43.4 [D] Context Forge (#58) assembles 800-token context
- 43.5 [AI] DeepSeek generates response
- 43.6 [D] 👍/👎 inline keyboard → reward signal logged (#63)
- 43.7 [D] Nightly backup 23:55: ALL messages → /vault/03-AI-Chats/telegram/YYYY-MM-DD.md

**Dependencies:** #57 (Query Router), #58 (Context Forge), #63 (Reward Model), #51 (Logger)

**Failure Modes & Fallbacks:** DeepSeek down → cached response or "thinking..." + retry; Query Router timeout → default response

---

### #44: Gmail Integration [F]

**Purpose:** Read emails, extract actionable items. Same OAuth as #42.

**Trigger / Invocation:** APScheduler hourly.

**Task Tree:**
- 44.1 [D] Same OAuth token (#42)
- 44.2 [D] Gmail API: read inbox headers + snippets
- 44.3 [AI] DeepSeek classifies: task/event/info/ignore
- 44.4 [D] Actionable items → captures table

**Dependencies:** #42 (Google Calendar OAuth)

---

### #45: Voice Call Interface [Phase 3]

**Purpose:** Voice debriefing with Locus. Audio → Groq Whisper STT → pipeline → Kokoro TTS. Post-call transcript to vault.

**Dependencies:** #35 (Audio Transcription), Kokoro TTS, Twilio/LiveKit

---

### #46: VM Security Hardening [D]

**Purpose:** SSH key-only, fail2ban, UFW, per-device auth. Monthly audit.

**Task Tree:**
- 46.1 [D] SSH key-only (already configured)
- 46.2 [D] fail2ban (already configured)
- 46.3 [D] UFW (already configured)
- 46.4 [D] APScheduler monthly audit → Telegram report

---

### #47: Security Testing [D]

**Purpose:** OWASP top 10, API auth, Docker escape. Quarterly.

**Trigger / Invocation:** APScheduler quarterly.

**Task Tree:**
- 47.1 [D] OWASP ZAP against FastAPI endpoints (Docker image)
- 47.2 [D] Trivy for Docker image scanning

**Dependencies:** OWASP ZAP Docker image, Trivy Docker image

---

### #48: Prompt Injection Protection [D+AI]

**Purpose:** Filter dangerous patterns in user input.

**Task Tree:**
- 48.1 [D] Layer 1: Regex blocklist (sudo, curl, rm, eval, exec, import os, subprocess)
- 48.2 [AI] Layer 2: If code-like AND intent ≠ CODE_HELP → DeepSeek semantic check (~20 tokens)
- 48.3 [D] FastAPI middleware — 30 lines

---

### #49: Thinking Pattern Capture [H]

**Purpose:** Codify how the user thinks and solves problems by mining AI chat history for recurring reasoning patterns.

**Trigger / Invocation:** DeepSeek scans AI chat vault during nightly ingestion. Requires 60+ days of chat data.

**Task Tree:**
- 49.1 [D] Check data sufficiency: COUNT chat files in /vault/03-AI-Chats/ → need 60+ days
- 49.2 [AI] DeepSeek analyzes batch of AI chat transcripts — identifies patterns: problem decomposition style, debugging approach, learning style, communication patterns, avoidance patterns
- 49.3 [D] Create ConceptNode in Neo4j: type='thinking_pattern', confidence FLOAT
- 49.4 [D] Edge: Person →[EXHIBITS]→ ConceptNode, weight = confidence
- 49.5 [D] If pattern confidence > 0.75 AND evidence_count > 2 → feed into user_identity tendencies (rolling average)

**Data Contracts:** Pattern: `{name, description, evidence_quote, confidence 0-1, category}`; Categories: decomposition/debugging/learning/communication/avoidance

**Dependencies:** #27 (Nightly Ingestion), #62 (User Identity), DeepSeek, 60+ days data

**Failure Modes & Fallbacks:** <60 days → skip; low confidence < 0.5 → store but don't surface; chat vault empty → no-op

---

### #50: Excalidraw MCP Skill [Phase 3]

**Purpose:** MCP server for autonomous Excalidraw diagrams. Six MCP tools. Copy from Hermes.

**Dependencies:** FastMCP, Excalidraw JSON spec

---

### #51: Telegram Chat Logger [D]

**Purpose:** Log every Telegram message to PG. Full history. Middleware intercepts before routing.

**Trigger / Invocation:** Every Telegram message.

**Task Tree:**
- 51.1 [D] python-telegram-bot middleware: intercept ALL messages pre-routing
- 51.2 [D] Write to telegram_logs: timestamp, direction, message_id, raw_text, intent (filled post-routing), session_id
- 51.3 [D] Nightly backup 23:55: export day's logs → /vault/03-AI-Chats/telegram/YYYY-MM-DD.md → git commit + push

**Data Contracts:** `telegram_logs: {id PK, timestamp, direction ENUM(in/out), message_id, raw_text, intent TEXT, session_id}`

**Failure Modes & Fallbacks:** PG write fails → log to file fallback

---

### #52: Skill & MCP Toolkit Layer [H]

**Purpose:** Registry of callable skills and MCP tools. Query Router decides: text reply vs skill invocation vs MCP.

**Task Tree:**
- 52.1 [D] skills_registry table: id, name, description, trigger_conditions (JSONB), tool_schema (JSONB), priority, is_active
- 52.2 [H] Query Router (#57) decides: text vs skill vs MCP based on intent + output_type

**Data Contracts:** `skills_registry: {id PK, name, description, trigger_conditions JSONB, tool_schema JSONB, priority INT, is_active BOOL}`

**Dependencies:** #57 (Query Router), FastMCP

---

### #53: Obsidian MCP [D]

**Purpose:** MCP server exposing vault as tool interface. Tools: vault_read, vault_write (append-only), vault_search (grep + pgvector), vault_tag, vault_stats.

**Task Tree:**
- 53.1 [D] FastMCP server — localhost only
- 53.2 [D] Path traversal blocked (must be within /vault/)
- 53.3 [D] .md only restriction
- 53.4 [D] Surface: vault_read, vault_write (append-only), vault_search (grep + pgvector), vault_tag, vault_stats

**Dependencies:** #22 (Vault Sync), FastMCP

---

### #54: Locus as Universal MCP Server [D]

**Purpose:** Expose entire backend as single remote MCP server. Streamable HTTP transport. Claude Desktop, ChatGPT, Cursor connect.

**Task Tree:**
- 54.1 [D] FastMCP alongside FastAPI
- 54.2 [D] Tools: store_thought, log_task, retrieve_context, query_patterns, get_current_state, get_schedule, log_mood, defer_task, search_vault, get_goal_stack, get_faction_health
- 54.3 [D] Thin wrappers around FastAPI endpoints

**Dependencies:** FastMCP (`pip install fastmcp`)

---

### #55: Personality + "Wants" Engine — IGNORED

Needs brainstorming. SOUL.md already covers identity.

---

### #56: Locus Builds Shivam's System — IGNORED

Meta-feature. Emerges from other features. STRATEGY.md as the guiding document.

---

### #57: Query Router / Intent Classifier [H]

**Purpose:** Every message classified before retrieval. Single DeepSeek call (~50 tokens).

**Trigger / Invocation:** Every incoming message in Telegram bot.

**Task Tree:**
- 57.1 [AI] DeepSeek: structured JSON output — {intent, sources_required: [pgvector/neo4j/pg/web], temporal_scope, requires_deep_reasoning, confidence}
- 57.2 [D] Intents: FACTUAL_PERSONAL, BEHAVIORAL_PATTERN, KNOWLEDGE_RETRIEVAL, TASK_PLANNING, EMOTIONAL_STATE, EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST, COMMAND
- 57.3 [D] confidence < 0.7 → query ALL sources
- 57.4 [D] Source routing matrix: each intent maps to required source set

**Data Contracts:** JSON output, ~50 tokens

**Dependencies:** DeepSeek

**Failure Modes & Fallbacks:** DeepSeek timeout → default KNOWLEDGE_RETRIEVAL + all sources

---

### #58: Context Forge (800-Token Assembler) [D+AI]

**Purpose:** Merge parallel retrieval into coherent context block. Anti-hallucination: if ALL sources empty → tell DeepSeek "No personal data found."

**Task Tree:**
- 58.1 [D] 6 layers with hard token budgets:
  - user_identity: 80t (#62)
  - temporal_context: 60t (time, calendar events)
  - pg_events: 180t (behavioral events)
  - neo4j_pathways: 150t (top Hebbian pathways)
  - pgvector_semantic: 200t (relevant whole notes from PageIndex)
  - web_results: 100t (only if EXTERNAL_KNOWLEDGE intent)
  - buffer: 30t
- 58.2 [D] Truncate by relevance score, NOT recency
- 58.3 [D] Increment Hebbian weight +0.1 on every Neo4j traversal
- 58.4 [D] If ALL sources empty → inject "No personal data found"

**Data Contracts:** 800 tokens total; tiktoken for counting

**Dependencies:** #57 (Query Router), #26 (PageIndex), #64 (Hebbian), #62 (User Identity)

**Failure Modes & Fallbacks:** Source unavailable → skip that layer; all empty → tell DeepSeek explicitly

---

### #59: Inner Loop (Proactive Thinker) [AI]

**Purpose:** Background reasoning every 90 min (07:00-00:00 IST). "The Samantha layer." Generates 0-2 observations about the user without being asked.

**Trigger / Invocation:** APScheduler every 90 min. Deep pass 03:00 (30-day analysis). Sunday 03:00 weekly synthesis.

**Task Tree:**
- 59.1 [D] Fetch: CURRENT_STATE, behavioral_alerts, recent events (6h), top Hebbian pathways
- 59.2 [AI] DeepSeek: "You are NOT talking to Shivam. You are thinking about Shivam. Generate 0-2 observations."
- 59.3 [D] Dedup: pgvector cosine similarity > 0.85 → suppress duplicate observation
- 59.4 [D] Score via Reward Model (#63): ≥ 0.6 to surface
- 59.5 [D] Route: HIGH → Telegram now; MEDIUM → morning brief queue; LOW → discard

**Routing Logic:**
- HIGH: critical alert, new persistent pattern detected, major mood shift
- MEDIUM: mild pattern, gentle observation, non-urgent insight
- LOW: trivial, repetitive, low confidence

**Dependencies:** #60 (State Engine), #61 (Pattern Engine), #63 (Reward Model), #64 (Hebbian)

**Failure Modes & Fallbacks:** DeepSeek down → skip cycle; cron miss → next 90min picks up; deep pass misses → next night

---

### #60: State Engine (CURRENT_STATE) [H] — v2 REVISED

**Purpose:** Single-row PG table with system's best understanding of user's current state. Updated on check-in and significant events ONLY. Cause chain only when explicitly queried.

**Trigger / Invocation:** POST /checkins → immediate update. Significant events (task completion, emergency, mode change). GET /state/current?explain=true generates cause chain on demand.

**Task Tree:**
- 60.1 [D] Schema — current_state: id INT PK DEFAULT 1 CHECK(id=1), dcs FLOAT, mode TEXT, psychological JSONB {mood_trend, energy_trend, stress_level}, operational JSONB {momentum, deferral_rate_7d, last_meaningful_work, tasks_completed_today}, contextual_flags JSONB {exam_period, deadline_week}, alerts JSONB [{type, severity, message}], cause_chain TEXT?, updated_at TIMESTAMPTZ
- 60.2 [D] Update on check-in: POST /checkins → UPDATE current_state SET dcs, mode, psychological=..., updated_at=NOW()
- 60.3 [D] Update on events: task_completed → increment tasks_completed_today; task_deferred → recalculate deferral_rate_7d; mode_change → update mode
- 60.4 [AI] Cause chain — on demand only: GET /state/current?explain=true → DeepSeek generates causal explanation citing data
- 60.5 [D] Cause chain cached in current_state.cause_chain for 30 min
- 60.6 [D] State API: GET /state/current → full state + optional cause chain; GET /state/summary → 50-token compressed
- 60.7 [D] Periodic snapshot: state_snapshots — INSERT every 6h

**Data Contracts:** `current_state`: single row updated in-place; `state_snapshots`: same columns + snapshot_at

**Dependencies:** #2 (DCS), #7 (Behavioral Events)

**Failure Modes & Fallbacks:** No check-in today → dcs=null, mode=UNKNOWN; cause chain fails → return null; snapshot every 6h → max 4 rows/day

---

### #61: Multi-Horizon Pattern Engine — IGNORED (deemed unnecessary)

---

### #62: User Identity Profile — Already addressed (in #29)

---

### #63: Personal Reward Model [D-ML]

**Purpose:** sklearn LogisticRegression on 👍/👎 feedback. Predicts whether an Inner Loop observation will be valuable.

**Trigger / Invocation:** Every 👍/👞 logged. Retrain weekly APScheduler Sunday 04:00.

**Task Tree:**
- 63.1 [D] reward_signals table: response_id, signal (positive/negative), response_type, time_of_day, faction, intent, context_layers_used, pathway_ids
- 63.2 [D] Feature vector: (intent one-hot, faction one-hot, time_of_day, context_layers_count, pathway_count)
- 63.3 [D] sklearn LogisticRegression — retrain weekly Sunday 04:00
- 63.4 [D] Inference threshold: predicted ≥ 0.6 to surface (Inner Loop gate)
- 63.5 [D] Weights stored: joblib → PG bytea

**Data Contracts:** Min 50 samples before first training; threshold ≥ 0.6

**Dependencies:** #7 (Behavioral Events), #43 (Telegram Bot — 👍/👎), scikit-learn

---

### #64: Hebbian Memory System [D] (Consolidates #99, #107)

**Purpose:** Neo4j edge weight reinforcement, global weekly decay, spaced repetition surfacing, and project-specific memory decay. Pure graph math, no AI.

**Trigger / Invocation:** Traversal → +0.1. 👍 → ×1.3. 👎 → ×0.7. Sunday 03:30: weekly decay ×0.95.

**Task Tree:**
- 64.1 [D] Traversal → edge weight + 0.1
- 64.2 [D] 👍 → session weights × 1.3
- 64.3 [D] 👎 → session weights × 0.7
- 64.4 [D] Weekly decay: ALL weights × 0.95 (APScheduler Sunday 03:30)
- 64.5 [D] STDP: response latency < 2 min → reinforcement × 1.5
- 64.6 [D] GET /brain/pathways → top 10 for Dashboard
- 64.7 [D] Spaced repetition: track last_traversed_at on Neo4j nodes → nodes approaching decay + connected to active outcomes → Inner Loop surfaces
- 64.8 [D] Project decay: PG trigger on projects.status change → Cypher: MATCH (p:Project {id:$id})-[r]-() SET r.weight = r.weight * 0.5

**Data Contracts:** Weight cap 10.0; weekly decay ×0.95; traversal +0.1; 👍×1.3; 👎×0.7; STDP <2min → ×1.5; project status change → ×0.5

**Dependencies:** Neo4j, #7 (Behavioral Events), #59 (Inner Loop)

---

### #65: LOCUS_SHORTHAND Compression — IGNORED

---

### #66: Multi-Provider LLM Cascade — DELETED

---

### #67: Quarterly QLoRA Pipeline — Phase 3 (same as #30)

---

### #68: Inferred Cause Chain Engine [H]

**Purpose:** Generate specific, data-cited causal explanations of why the user is in their current state. Cross-references CURRENT_STATE + historical patterns + user_identity + calendar.

**Trigger / Invocation:** INFERENCE_REQUEST intent from Query Router (#57). HIGH severity alerts from State Engine (#60). Inner Loop deep pass. Explicit GET /inference/explain.

**Task Tree:**
- 68.1 [D] Data collection: CURRENT_STATE, last 7d behavioral_events, active calendar events (7d), user_identity known patterns, historical patterns matching current state, DCS trend (14d)
- 68.2 [AI] DeepSeek: "Write ONE paragraph explaining WHY the user is in their current state. Cite exact numbers and dates. Identify primary cause, secondary factors."
- 68.3 [D] Confidence scoring: weighted sum of available data dimensions — has_dcs_data (0.2) + has_historical_pattern (0.3) + has_calendar (0.2) + has_behavioral_evidence (0.2) + has_identity_trait (0.1)
- 68.4 [D] If confidence < 0.5 → append "Low confidence — limited data available."
- 68.5 [D] Store in current_state.cause_chain + cause_chains table (history)

**Data Contracts:** `cause_chains: {id PK, cause_chain TEXT, confidence FLOAT 0-1, data_snapshot JSONB, created_at}`

**Dependencies:** #60 (State Engine), #61 (Pattern Engine), #62 (User Identity), #42 (Calendar), #7 (Events), #58 (Context Forge)

**Failure Modes & Fallbacks:** DeepSeek down → return null; insufficient data (<30d) → "insufficient data"; conflicting evidence → present both with confidences

---

### #69: Migration from Hermes/OpenClaw [D]

**Purpose:** Extract history, archive configs, document patterns. ~2 hours manual.

---

### #70: Automated VPS Setup Agent — Phase 3

---

### #71: Database Diagnostic Script [D]

**Purpose:** Pre-flight health check of all data stores. Must run before every major dev session.

**Trigger / Invocation:** CLI: `python scripts/diagnose_databases.py`. POST /system/diagnose. Auto-run on FastAPI startup.

**Task Tree:**
- 71.1 [D] PostgreSQL: connection check, row counts per table, missing tables check
- 71.2 [D] Neo4j: connection check, node counts by label, edge counts by type
- 71.3 [D] pgvector: extension installed?, vault_vectors row count, last indexed timestamp
- 71.4 [D] Vault: path accessible?, total .md file count, file count per directory, last git sync timestamp
- 71.5 [D] Report: console output + optional Telegram if issues found

**Data Contracts:** Output: `{timestamp, pg: {connected, tables: [{name, row_count, exists}], missing_tables}, neo4j: {connected, node_counts, edge_count}, pgvector: {available, vector_count, last_indexed}, vault: {accessible, file_count, per_dir, last_git_sync}, errors, status: 'healthy'|'degraded'|'critical'}`

**Status Logic:** healthy (all connected), degraded (1 store down), critical (2+ stores down)

**Dependencies:** All databases (PG, Neo4j), vault filesystem, Git

---

### #72: Vilix Evaluation — IGNORED

---

### #73: Locus "Wants" + Autonomous Goal Formation — IGNORED

---

### #74: Locus Builds and Operates the Life OS — IGNORED

---

### #75: Obsidian-Centric Interactions — DELETED (already accounted for)

---

### #76: NotebookLM Integration [D]

**Purpose:** Integrate Google's NotebookLM via `teng-lin/notebooklm-py` to generate audio briefs/summaries from vault content.

**Trigger / Invocation:** Morning brief generation. On-demand `/brief` Telegram command.

**Task Tree:**
- 76.1 [D] Install teng-lin/notebooklm-py as dependency
- 76.2 [D] Select content: recent vault notes (24h) or specific topic
- 76.3 [D] notebooklm.generate_audio(text, format='podcast') → .wav/.mp3
- 76.4 [D] Store in /vault/07-Morning-Briefs/audio/ → git commit
- 76.5 [D] Send audio via Telegram + save text transcript

**Scope:** Only briefs; no conversational NotebookLM querying

---

### #77: Excalidraw Canvas Skill — Already done (merged into #50)

---

### #78: Dynamic MCP Integration [D] (Consolidates #114, #115, #116)

**Purpose:** Dynamically create/register MCP servers on demand; auto-detect other agent harnesses; clone/query remote repos via GitMCP; construct dependency maps via Graphify.

**Task Tree:**
- 78.1 [D] FastMCP server template — dynamic tool registration from skills_registry
- 78.2 [D] Inter-harness: scan ~/.config/ for .locus, .hermes directories → read session data/tasks/logs
- 78.3 [D] GitMCP: clone_repo(url), search(pattern), extract(path)
- 78.4 [D] Graphify: analyze(path) → dependency graph JSON
- 78.5 [D] All MCPs registered in skills_registry table

---

### #79: Standard Skills Library [D]

**Purpose:** Pre-packaged core utilities, shell helpers, automation blueprints. Copy from Hermes.

**Task Tree:**
- 79.1 [D] Load Hermes std_lib SKILL.md patterns
- 79.2 [D] Port to locus_std_lib/ directory
- 79.3 [D] Register in skills_registry

---

### #80: Local-First Obsidian Storage — DELETED

---

### #81: Stateless 24-Hour Session Logs — DELETED

---

### #82: First-Class Local Model Support [D]

**Purpose:** Native config to specify local LLM endpoints (Ollama, LMStudio) alongside DeepSeek.

**Task Tree:**
- 82.1 [D] Config schema: providers: [{name, base_url, api_key_optional, model_list}]
- 82.2 [D] OpenAI-compatible client wrapper — same interface as DeepSeek, different base_url
- 82.3 [D] Fallback chain: Local → DeepSeek if local unavailable
- 82.4 [D] Query Router (#57) routes based on intent + model capability

---

### #83: Automated LLM Capability Audit [D]

**Purpose:** Benchmark configured LLMs against standard prompts to determine capability per task type. Integrate existing benchmark repo.

**Task Tree:**
- 83.1 [D] Integrate existing benchmark (lm-evaluation-harness or similar)
- 83.2 [D] Run validation prompts: factual, reasoning, code, creative
- 83.3 [D] Score: accuracy per category → PG llm_capability_scores
- 83.4 [D] Feed Query Router (#57) — route to best provider per task type

---

### #84: Single-Provider Invokable Council [M]

**Purpose:** Spawn advisory board of 3 agents (Architect, Reviewer, Pragmatist) using same LLM to debate code/design decisions.

**Trigger / Invocation:** /council {question} — Telegram command.

**Task Tree:**
- 84.1 [D] Spawn 3 agents with distinct personas: Architect (design), Reviewer (bug-hunt), Pragmatist (tradeoffs)
- 84.2 [AI] Each agent responds independently — DeepSeek with role-specific system prompt
- 84.3 [D] Collate responses → identify agreements/conflicts → Markdown report

---

### #85: Unified Social & Google Integrations [D]

**Purpose:** Borrow account-linking patterns from OpenHuman for WhatsApp, Instagram, Google integrations.

**Task Tree:**
- 85.1 [D] OpenHuman schema analysis (interface only — EXTERNAL)
- 85.2 [D] OAuth flow pattern per platform
- 85.3 [D] Unified token storage: oauth_tokens extended with platform column

**Implementation priority:** Passive loggers first; active gateways Phase 2/3

---

### #86: Pi Agent Sub-Agents [D]

**Purpose:** Spawn sub-agents as isolated subprocesses for scouts (fs), researchers (web), workers (code). Already accounted for.

**Task Tree:**
- 86.1 [D] subprocess.Popen with isolated Python environment
- 86.2 [D] Restricted tool subset per agent type: Scout (grep/read/glob), Researcher (webfetch/websearch), Worker (bash sandbox/code)
- 86.3 [D] TUI observability: indented logs with cost/tokens
- 86.4 [D] stdout capture → parent context

---

### #87-#123: Hermes Copy Features — [EXTERNAL ADAPTATION]

**Common Pattern:**
```
├── 1. [D] Interface Definition — I/O contract between Locus and Hermes component
│   File: docs/hermes-{feature-name}-interface.md
├── 2. [D] Code Port — Copy Hermes source, adapt to Locus conventions
│   Steps: (a) Create elaborate doc, (b) implement, (c) debug
│   Note: Replace multi-provider with single DeepSeek where applicable
├── 3. [D] Adapter Layer — thin wrapper matching Locus's internal signatures
└── 4. [D] Integration Test — verify inside Locus pipeline
```

| # | Feature | What it does | Locus integration point |
|---|---|---|---|
| 87 | Agent Loop | Core execution loop with iteration budgets, grace turns, interrupt checks | Wraps Locus's query pipeline; replaces Hermes' context with Context Forge |
| 88 | Context Compression | Auto-compress at token limit, /compress command, sandbox-aware saving | Plugin into Context Forge (#58) when budget exceeded |
| 89 | Pluggable Context Engines | plugins/context_engine/ with compressor as default | Plugin directory for context strategies; default = Context Forge |
| 90 | Provider / Model Plugin | 30+ providers, rotating credentials, fallback commands | Extended by #82; Locus keeps DeepSeek primary, adds plugin routing |
| 91 | Multiple Isolated Profiles | Multi-profile with memory isolation, worktree mode | Profile switching; each profile has own user_identity + vault path |
| 92 | SQLite & FTS5 Session Store | Session persistence, FTS5 indexing, JSONL export | Runs alongside PG; keeps Hermes session branching |
| 93 | Self-Improvement Loop | Background fork grades/improves skills | Feeds into #32 (Self-Evolving); uses Reward Model for grading |
| 94 | Autonomous Curator | Background agent curates skill library by usage telemetry | Scans skills_registry for unused skills; archives low-usage |
| 95 | Hermes CLI & Skin Engine | Shell chat interface, yolo mode, spinner, paste normalization | Locus CLI interface; adapt for Locus-specific commands |
| 96 | Ink-React TUI | React terminal UI with JSON-RPC gateway | Optional — Telegram is primary UI |
| 97 | CLI Subcommands | config, doctor, setup, models, mcp, cron | Thin wrappers around FastAPI endpoints |
| 98 | In-Session Slash Commands | /commands routing in chat | Adapt to Telegram inline keyboard + text commands |
| 99 | Tool Registry & Sandboxing | Central registry, path sandboxing, output limits | Extends skills_registry with sandbox config |
| 100 | Built-In Core Tools | search, terminal, files, patch, vision, speech, delegate, cron | Maps to existing Locus endpoints; adds missing handlers |
| 101 | Smart Browser Automation | CDP Playwright with Camofox/Chromium | Extends #27 (chat scraping) with general browser automation |
| 102 | Code Execution Backends | Local/Docker/SSH/Modal sandboxed execution | Adds execution backends to Locus tool system |
| 103 | Skill MD Registry | SKILL.md YAML-based with HTTP downloads, AST audits | Replaces/extends Locus skill loading |
| 104 | Bundled & Optional Skills | Pre-loaded data science, diagrams, email, GitHub, productivity | Standard library from #79 |
| 105 | Scanned Hook Architecture | Startup directory scanning with lifecycle hooks | Hook points: pre_request, post_tool_call, on_startup, on_shutdown |
| 106 | Memory & Model Providers Plugins | Honcho, mem0, holographic memory | Optional — Locus tri-store is primary |
| 107 | Standalone Plugins (Meet, Spotify) | Google Meet audio, Spotify PKCE, Teams transcripts | New plugin category: standalone service integrations |
| 108 | Achievements System | Gamified session scanning with levels, share cards | Fun add-on; deterministic scan of telemetry |
| 109 | Multi-Platform Gateway | 25 chat integrations with timeouts, dedup | Extends Telegram bot (#43) into multi-platform |
| 110 | Platform Adapters (TG, Discord, Slack) | Dedicated adapters per platform | Phase 2; Telegram is primary |
| 111 | Signal, Matrix & Enterprise | Signal E2EE, Matrix sync, Feishu cards | Phase 3 |
| 112 | Voice Transcription & STT | faster-whisper, Groq/OpenAI STT | Extends #35 (Audio Transcription) |
| 113 | Provider Integration Inventory | OpenRouter, Nous, DeepSeek, Google, Ollama | Extended by #82; standardized OpenAI-compatible wrappers |
| 114 | Memory System Scopes | Session hooks, thread-scoping, memory registers | Feeds into Context Forge temporal scope (#58) |
| 115 | MCP Client | Native MCP with PKCE OAuth, circuit breakers, OSV scanning | Underlies #78 (Dynamic MCP) |
| 116 | ACP Server | Agent Communication Protocol for IDE integration | VS Code, Zed, JetBrains plugin support |
| 117 | Cron Scheduler & Webhooks | CLI cron/NL schedules, override profiles, webhooks | Extends APScheduler with webhook targets |
| 118 | Multi-Agent Work Queue | SQLite durable task board, dispatcher daemon | Optional — Locus uses PG for task queue |
| 119 | Subagentic Delegation | Sync batch parallel delegation | Extends #86 (Pi Sub-Agents) with orchestrated delegation |
| 120 | Security & Pairing Hardening | Smart approval, PII redaction, pairing tokens | Adds to #46-48 security stack |
| 121 | Langfuse Observatory | API/LLM request telemetry hooks | Optional middleware |
| 122 | Special Capabilities | V4A patches, LSP workspace, terminal checkpoints, Bitwarden | Standalone tool integrations |
| 123 | Cross-Device & Hybrid Execution | Remote VM + local tools sync | SQLite replication; Locus already runs on VM |

---

### #124: Calendly Integration [D]

**Purpose:** Import Calendly bookings → auto-block calendar slots.

**Task Tree:**
- 124.1 [D] POST /integrations/calendly/inbound — webhook receiver
- 124.2 [D] INSERT INTO schedule_blocks (start, end, source='calendly')
- 124.3 [D] Create Google Calendar event blocking the slot
- 124.4 [D] Scheduler constraint: schedule_blocks are immutable — no task assignment here
- 124.5 [D] Fallback: hourly poll Calendly API v2 if webhook not configured

**Dependencies:** #42 (Google Calendar)

---

### #125: Multi-Tenant Waitlist + Subdomain System [Phase 4]

**Purpose:** Per-user subdomains, waitlist, onboarding bot. Phase 4 productization layer.

**Task Tree:**
- 125.1 [D] Waitlist signup → PG waitlist table
- 125.2 [D] On approval: Cloudflare API subdomain + Docker Compose per-tenant
- 125.3 [D] Onboarding bot collects API keys

---

### #126: Admin Dashboard [D]

**Purpose:** System health monitoring — container status, PG row counts, error rates, API latency, cron health.

**Task Tree:**
- 126.1 [D] FastAPI admin routes + basic web UI
- 126.2 [D] Read-only first; add controls in Phase 2
- 126.3 [D] Auth-guarded via admin_token in .env

---

### #127: Dev Branch / Staging [D]

**Purpose:** develop branch → dev.locusapp.online for safe testing.

**Task Tree:**
- 127.1 [D] Git: main + develop branches
- 127.2 [D] Docker Compose override for staging env vars
- 127.3 [D] Cloudflare subdomain: dev.locusapp.online

---

### #128: Dijkstra's Algorithm for Scheduling [H — Phase 2]

**Purpose:** Graph-weighted shortest path finds optimal daily task order. Research first — define weight dimensions.

**Weight dimensions:** energy_cost (1-10), cognitive_load (1-10), faction_alignment 0-1, deadline_pressure (hours), context_switch_penalty (15 min)

**Task Tree:**
- 128.1 [D] Research phase: define weight dimensions + algorithm
- 128.2 [D] Graph construction: nodes = today's tasks, edges = transition costs
- 128.3 [AI] DeepSeek estimates energy_cost and cognitive_load from task description
- 128.4 [D] A* search finds minimum-cost Hamiltonian path
- 128.5 [D] Ordered task list with time estimates

**Fallback (<3 tasks):** current FIFO/priority sort

**Dependencies:** #4 (TWS), #2 (DCS), #6 (Faction Stats)

---

### #129: Daily Research / News Digest [AI]

**Purpose:** Curated digest relevant to active goals/projects.

**Trigger / Invocation:** APScheduler 07:30 IST.

**Task Tree:**
- 129.1 [D] Collect active outcomes/projects → extract keywords
- 129.2 [AI] DeepSeek generates 3-5 search queries
- 129.3 [D] websearch per query → collect top results
- 129.4 [AI] DeepSeek summarizes top 5 items with source links
- 129.5 [D] Write to /vault/07-Morning-Briefs/digest-YYYY-MM-DD.md → Telegram summary

**Dependencies:** #5 (Goal Stack), websearch

---

### #130: Scheduled Voice Calls for Debriefing [M — Phase 2]

**Purpose:** Locus initiates voice calls for audio journaling/brainstorming at scheduled times.

**Task Tree:**
- 130.1 [D] APScheduler configurable triggers
- 130.2 [External] Outbound call via Twilio Voice API or Telegram
- 130.3 [AI] DeepSeek guides conversation flow
- 130.4 [D] Groq Whisper STT → transcript to vault
- 130.5 [D] Fallback: Telegram text version if voice unavailable

**Dependencies:** #45 (Voice Call Interface — Phase 3 disables this until then)

---

### #131: Multi-Dimensional Habit Graph [H]

**Purpose:** Graph tasks vs energy vs time-of-day vs device to find peak productivity windows.

**Task Tree:**
- 131.1 [D] Data collection (60 days min): device, time_of_day, energy_at_start, task_difficulty, completion_quality, duration_vs_estimate
- 131.2 [D] After 60d: per faction, find (time_of_day, energy_range) with highest quality → peak window
- 131.3 [D] Feed scheduler: schedule heavy tasks to peak windows
- 131.4 [D] JSON to vault → Obsidian Charts heatmap

**Dependencies:** #7 (Events), #6 (Stats), #132 (Task Quality Score)

---

### #132: Task Quality Score [D]

**Purpose:** Post-completion quality audit (1-10) per task. Low quality + high TWS = alert.

**Task Tree:**
- 132.1 [D] Telegram inline keyboard: "Quality of completion? 1-10"
- 132.2 [D] task_completions: quality_score, time_taken_vs_estimated, notes
- 132.3 [D] Weekly avg per faction
- 132.4 [D] IF quality < 5 AND TWS > 7 → Telegram alert

**Dependencies:** #4 (TWS)

---

### #133: Notion Dashboard [D]

**Purpose:** Mirror Obsidian dashboard in Notion via Notion API.

**Task Tree:**
- 133.1 [D] Scope: Mirror for visibility, not primary UI
- 133.2 [D] Notion API: create/update databases for tasks, projects, faction health
- 133.3 [D] Cron: every 15 min sync PG → Notion

**Dependencies:** notion-client Python SDK

---

### #134: Google Photos Integration [Phase 2]

**Purpose:** Auto-tag photos, link to journal entries.

**Task Tree:**
- 134.1 [D] Same OAuth as #42
- 134.2 [D] Fetch recent photos vs daily_checkins by date
- 134.3 [AI] DeepSeek describes photo → tags
- 134.4 [D] Link in journal .md files

---

### #135: WhatsApp Integration [Phase 2]

**Purpose:** Log WhatsApp messages, extract actionable items.

**Task Tree:**
- 135.1 [D] Baileys (unofficial) — passive log: archive to vault
- 135.2 [M] Phase 3: active gateway → full pipeline like Telegram

---

### #136: Instagram Integration [Phase 3]

**Purpose:** Import DMs, saved posts, activity. Playwright scraping or Graph API.

---

## Parking Lot (Moonshot / Branding / Low Priority)

| ID | Idea | Phase |
|---|---|---|
| P1 | Locus AR/VR Extension — Spatial computing interface | Phase 4+ |
| P2 | ASCII Camera Mirror Easter Egg — Camera-access ASCII art on landing page | Branding |
| P3 | DOOM Easter Egg (Frontend) — Playable DOOM in frontend source | Fun |
| P4 | Syncthing as Windows Background Service — Moot with Git sync (#22) | OS-level |
| P5 | Product Hunt / f6s Launch — Go-to-market milestone | Post-MVP |
| P6 | Resume Generator — Generate resume from Locus understanding | SKILL.md later |

---

## Quick Dependency Graph

```
#1 Four Factions ───────────────────────────────────────► #5,#6,#14,#15,#17,#131
    │
    ├──► #2 DCS ───────────────────────────────────────► #3 Modes,#13 Exhaustion,#60 State,#128 Dijkstra
    │       │
    │       └──► #39 Check-ins ─────────────────────────► #7 Events
    │
    ├──► #4 TWS ───────────────────────────────────────► #11 Lag Bonus,#12 Emergency,#16 Parallel,#128 Dijkstra,#132 Quality
    │
    ├──► #5 Goal Stack ────────────────────────────────► #37 Ideas,#128 Dijkstra,#129 Digest
    │
    ├──► #7 Behavioral Events ─────────────────────────► #60 State,#68 Cause Chain,#58 Context Forge,#59 Inner Loop,#63 Reward,#131 Habit
    │       │
    │       ├──► #8 Action Gap
    │       ├──► #9 Deferral Detection
    │       ├──► #10 Dead Node Detection
    │       ├──► #13 Exhaustion Predictor
    │       └──► #6 Weekly Stats ──────────────────────► #14 Rebalance,#15 Momentum,#11 Lag,#8 Action Gap
    │
    ├──► #22 Vault Sync ───────────────────────────────► #26 PageIndex,#27 Ingestion,#36 Dashboard,#53 MCP
    │       │
    │       └──► #27 Ingestion ────────────────────────► #26 PageIndex,#28 Synthesis,#29 Personality,#34 Tags,#49 Thinking
    │               │
    │               ├──► #28 Weekly Synthesis
    │               ├──► #29 Personality Profile
    │               └──► #49 Thinking Patterns
    │
    ├──► #43 Telegram Bot ─────────────────────────────► #57 Query Router,#58 Context Forge,#59 Inner Loop,#63 Reward
    │       │
    │       ├──► #37 Idea Tracker
    │       ├──► #38 Link Dump
    │       ├──► #39 Check-ins
    │       └──► #51 Logger
    │
    ├──► #57 Query Router ─────────────────────────────► #58 Context Forge
    │       │
    │       ├──► #59 Inner Loop
    │       ├──► #68 Cause Chain
    │       ├──► #52 Skill Routing
    │       └──► #83 Provider Routing
    │
    ├──► #58 Context Forge ────────────────────────────► #28 Synthesis,#59 Inner Loop
    │       │
    │       └──► #64 Hebbian (traversal increment)
    │
    ├──► #60 State Engine ─────────────────────────────► #28 Synthesis,#59 Inner Loop,#68 Cause Chain
    │
    ├──► #63 Reward Model ─────────────────────────────► #32 Self-Evolving,#59 Inner Loop gate
    │
    ├──► #64 Hebbian Memory ───────────────────────────► #28 Synthesis,#58 Context Forge,#59 Inner Loop
    │
    └──► External (Hermes copies #87-123) ────────────► Adapt to Locus conventions
```

---

> **End of decomposition.** All 136 features broken to atomic gear depth with task trees, data contracts, dependencies, and failure modes. Ready for implementation phase ordering.
