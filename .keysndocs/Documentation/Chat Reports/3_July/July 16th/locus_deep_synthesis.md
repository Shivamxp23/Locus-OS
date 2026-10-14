# Locus OS — Deep Synthesis & Architecture Map

> **Status**: Complete system read. This document represents the full understanding of what Locus is, where it stands, and what the restart should look like.

---

## 1. What Locus Actually Is

Locus is **not** a productivity app. It's a **Personal Cognitive Operating System (PCOS)** — a system that builds a deep, data-driven model of one specific human (Shivam) over time and uses that model to make better decisions about how he spends his time, energy, and attention.

The core philosophy from [My Initial idea.txt](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Ideas%20and%20System/Ideas/My%20Initial%20idea.txt):

> *"The entire system is also responsible for breaking down big tasks into small manageable chunks... Everything will stem from: 1. Goals for what I wanna do 2. Why do I wanna do it."*

The vision from the Claude transcript: **"A personal chief of staff that eliminates regret through intelligent planning."**

### The Non-Negotiable Core Laws
1. **Every word Locus says must be grounded in real retrieved data** — silence > hallucination
2. **Metric-driven, not vibes** — every decision traces to a number (DCS, TWS, LS, AG)
3. **One human, one system** — this is hyper-personalized, not generic

---

## 2. The Four Factions (Life Domains)

| Faction | Color | Weekly Target | Examples |
|---------|-------|---------------|----------|
| **1 — Health/Stability** | `#22C55E` | 17.5 hrs | Fitness, sleep, nutrition, academics, CS fundamentals |
| **2 — Leverage/Money** | `#3B82F6` | 17.5 hrs | Freelance, startups, networking, career visibility |
| **3 — Craft/Skills** | `#F97316` | 21.0 hrs | Cinematography, software engineering, passion projects |
| **4 — Expression/Exploration** | `#A855F7` | 14.0 hrs | Identity, hobbies, reading, unstructured time |

Every action, task, goal, and log entry belongs to **exactly one** faction. This is the organizational backbone.

---

## 3. The Metric System

### Daily Capacity Score (DCS)
```
DCS = ((E + M + S) / 3) × (1 − ST/20)
```
Where E = Energy (1-10), M = Mood (1-10), S = Sleep (1-10), ST = Stress (1-10)

### DCS → Operating Mode
| DCS Range | Mode | Behavior |
|-----------|------|----------|
| 0.0–2.0 | SURVIVAL | Non-negotiables only. Gentle tone. |
| 2.1–4.0 | RECOVERY | Easy tasks only (D ≤ 4). Supportive. |
| 4.1–6.0 | NORMAL | Standard operation. Direct. |
| 6.1–8.0 | DEEP WORK | Focused, minimal response. Don't break flow. |
| 8.1–10.0 | PEAK | Challenge mode. Push limits. |

### Task Weight Score (TWS)
```
TWS = (P × 0.4) + (U × 0.4) + (D × 0.2)
```
With dynamic Lag Bonus: LS > 3h → +2, LS > 6h → +4, faction ahead → -1

### Faction Health Metrics (Weekly)
- **CR** = Completion Rate = done/attempted × 100
- **CS** = Consistency Score = active_days/7 × 100
- **MS** = Momentum Score = avg CR over 3 weeks
- **LS** = Lag Score = target_hours − actual_hours
- **AG** = Action Gap = declared_priority − (actual_hrs/target_hrs × 10)

---

## 4. The Architecture (Service Pyramid)

```
┌─────────────────────────────────────────────────┐
│              INTERFACE LAYER                      │
│  Telegram Bot (primary)  │  Obsidian Dashboard    │
│  MCP Server (universal)  │  Voice (Phase 3)       │
├─────────────────────────────────────────────────┤
│              ORCHESTRATION LAYER                  │
│  Query Router/Intent Classifier (12 intents)      │
│  Context Forge (800-token, 6-layer assembly)      │
│  Mode-Aware Instruction Builder                   │
│  Anti-Hallucination Guard                         │
├─────────────────────────────────────────────────┤
│              REASONING LAYER                      │
│  Generator (DeepSeek V4 Flash - speaks only)      │
│  Inner Loop / Proactive Thinker (every 90min)     │
│  Cause Chain Engine (why am I like this?)         │
│  Scheduler (7-step DCS→TWS→Lag algorithm)         │
├─────────────────────────────────────────────────┤
│              INTELLIGENCE LAYER                   │
│  Pattern Engine (5 horizons: 6h→30d→all-time)     │
│  State Engine (CURRENT_STATE via PG NOTIFY)       │
│  Reward Model (sklearn on 👍/👎 signals)          │
│  Hebbian Weighting (graph reinforcement + decay)  │
│  User Identity Profile (rolling, never overwrite) │
├─────────────────────────────────────────────────┤
│              INFRASTRUCTURE LAYER                 │
│  PostgreSQL + pgvector (structured + semantic)    │
│  Neo4j (relationships + Hebbian pathways)         │
│  FastAPI Backend (routers + event stream)          │
│  Vault via Git (Obsidian ↔ VM, dir partitioned)   │
│  Oracle ARM64 VM (4 OCPU, 24GB, always free)      │
│  Cloudflare Tunnel (api.locusapp.online)          │
└─────────────────────────────────────────────────┘
```

---

## 5. The Two Loops (How Locus Thinks)

### Loop 1: Reactive (User-Triggered) — 12 Stages
```
User Message → Intake → Injection Filter → Intent Classification (50t)
→ State Injection (DCS/Mode) → Parallel 4-Source Retrieval
→ Headroom Compression → Context Forge (800t assembly)
→ Special Routing (commands/coding/research)
→ Mode-Aware Instruction → Generator (DeepSeek)
→ Anti-Hallucination Guard → Deliver + 👍/👎
→ Post-Turn Learning (memory write, Hebbian update, reward signal, state engine)
```

### Loop 2: Proactive (Self-Triggered) — "The Samantha Layer"
- **Standard pass**: every 90 min, 07:00-00:00 IST
- **Deep pass**: 03:00 IST (30-day analysis)
- **Sunday synthesis**: 03:00 IST (uses Gemini 2.5 Pro)
- **Morning briefing**: 08:00 IST daily

Pipeline: Budget check → Gather state → Think about user (NOT talk to user) → Dedup → Reward gate → Route → Spaced repetition → Wants engine → Log

---

## 6. The Brain Module (9 Sub-Systems)

| # | Sub-System | File | Responsibility |
|---|------------|------|---------------|
| 1 | **Collector** | `brain/collector.py` | Nightly vault crawl, incremental by MD5 hash |
| 2 | **Chunker** | `brain/chunker.py` | Proposition-based chunking via spaCy |
| 3 | **Reader** | `brain/reader.py` | Direct file read from disk (never cache) |
| 4 | **Retriever** | `brain/retriever.py` | 3-mode: Semantic (pgvector) + Structured (PG) + Graph (Neo4j) |
| 5 | **Pattern Engine** | `brain/pattern_engine.py` | DCS trends, faction lag, deferrals, action gap, exhaustion risk |
| 6 | **Scheduler** | `brain/scheduler.py` | 7-step daily task list (DCS→TWS→Lag→Faction balance) |
| 7 | **Web Searcher** | `brain/web_searcher.py` | External knowledge when vault has nothing |
| 8 | **Goal Tracker** | `brain/goal_tracker.py` | 3-layer stack health, dead nodes, stalled projects |
| 9 | **Generator** | `brain/generator.py` | THE ONLY place LLM speaks. Receives assembled context. |

**Build order**: Collector → Chunker → Reader → Retriever first. Everything else depends on real data flowing.

---

## 7. Current State of the Codebase

### What Exists (locus-os repo)
- **`core/`**: Agent loop, memory, tools, channels, heartbeat, scheduler, skills, voice, browser — **borrowed heavily from Hermes Agent patterns**
- **`gateway/`**: Telegram bot with slash commands, agent bridge, platform registry — **functional but not wired to brain module**
- **`locus_cli/`**: CLI entry point
- **`SETTINGS.md`**: 1838-line master config spec (comprehensive)
- **`pyproject.toml`**: v0.2.0, FastAPI not in deps, dependencies are for a chat agent not a PCOS

### What's Missing (The Gap)
1. **No brain module** — the entire 9-subsystem pipeline doesn't exist
2. **No PostgreSQL integration** — using SQLite instead of PG+pgvector
3. **No Neo4j integration** — `neo4j_memory.py` exists but not connected
4. **No DCS/TWS/Metric system** — formulas documented but not implemented
5. **No Inner Loop** — no proactive thinking capability
6. **No Context Forge** — no 800-token assembly
7. **No Query Router** — all messages treated the same
8. **No vault processing** — no PageIndex, no embedding pipeline
9. **The Telegram bot hallucinates** — no retrieval grounding
10. **FastAPI backend** — not set up (deps missing from pyproject.toml)

### Adjacent Projects (Explored, Not Used)
| Project | What It Is | Verdict |
|---------|-----------|---------|
| **Hermes Agent** | Self-improving coding agent by Nous Research | Too general-purpose. Patterns borrowed. Not suitable as Locus core. |
| **OpenHuman** | Personal AI with local memory | Managed services dependency. Not enough control. Patterns noted. |
| **Pi Agent** | Coding agent harness | Coding agent loop ≠ cognitive OS loop. Used for comparison only. |

---

## 8. Key Architectural Decisions (v2)

| Decision | What Changed | Why |
|----------|-------------|-----|
| Retrieval | LightRAG → **PageIndex + direct pgvector + direct Neo4j** | Query Router + Context Forge already do what LightRAG does |
| Vault sync | Syncthing → **Git (Obsidian Git + GitHub private repo)** | Version history free, no extra service |
| Vector DB | Qdrant → **pgvector (PostgreSQL extension)** | <50K vectors, one fewer container |
| LLM | Multi-provider → **DeepSeek V4 Flash only** | One model, one behavior, ~$0.012/day |
| Cache | Redis required → **Redis optional** | Single-user scale, PG covers it |
| OAuth | Composio → **Manual google-api-python-client** | 50 lines, full control |

---

## 9. The "Nuke & Restart" Context

The user explicitly said: *"I am going to nuke my entire working project and restart from the beginning."*

This means:
1. The current `core/` directory (Hermes-borrowed patterns) needs to be **replaced**, not patched
2. The brain module needs to be built **from scratch** following the spec in [LOCUS_BRAIN_MODULE_PROMPT.md](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Ideas%20and%20System/Systems/Agent%20Loop/LOCUS_BRAIN_MODULE_PROMPT.md)
3. The 161-feature list in [locus_features.md](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Ideas%20and%20System/Systems/Features/locus_features.md) is the roadmap
4. Documentation (`.keysndocs/`) is preserved — it's the system bible

---

## 10. What Needs Discussion

Before building, these architectural decisions need resolution:

### A. Infrastructure Questions
1. **PostgreSQL setup**: Local dev vs. Oracle VM from day 1?
2. **Neo4j deployment**: Container on VM? Free Aura tier?
3. **FastAPI structure**: Monolith with routers or microservice split?

### B. Model Strategy
1. **DeepSeek V4 Flash**: Confirmed as primary. But what's the fallback if it goes down?
2. **Inner Loop model**: V4 Flash for standard, Gemini 2.5 Pro for Sunday — still the plan?
3. **Cerebras 70B**: Mentioned for state engine in earlier conversation — still in play?

### C. Build Order
The spec says: Collector → Chunker → Reader → Retriever first. But to test anything, you need:
- A running FastAPI backend
- PostgreSQL with the schema
- At least one data source (vault files or Telegram messages)

### D. The "Borrowed Code" Question
The current `core/` has Hermes-style patterns. Three options:
1. **Keep the shell, gut the internals** — reuse channel/gateway code, replace agent loop
2. **Clean slate** — new `src/` directory, keep only the docs
3. **Selective extraction** — cherry-pick what works (Telegram bot, config loader) into a new structure

### E. Phase 1 vs Phase 2 vs Phase 3 Boundary
The features doc marks things as Phase 2/3 but doesn't define when Phase 1 ends. What's the MVP?

---

> **Ready to discuss.** What aspect do you want to dive into first?
