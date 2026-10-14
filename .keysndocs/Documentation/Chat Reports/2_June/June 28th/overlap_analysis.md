# Session 2 vs. Comprehensive Feature Audit — Overlap & Gap Analysis

> **Verdict up front:** The feature audit is more detailed on **agent infrastructure** (tools, providers, sessions, TUI internals). But Session 2 contains significant Locus-specific domain knowledge — the *entire* Life OS layer, the brain engine, the interface philosophy — that the feature audit either **omits** or reduces to a single line. The audit is **not** a superset of Session 2.

---

## 1. What the Audit Covers Better Than Session 2

These are areas where the June 28th audit genuinely has more depth:

| Area | Audit Detail | Session 2 Coverage |
|------|-------------|-------------------|
| **Pi Agent internals** | 39 CLI flags, 9 entry types, 29 session operations, 13 agent events, 7 tool lifecycle hooks, TUI components (30+ listed), extension events (25+), full provider table (10+ APIs, 36+ providers) | Summarizes Pi architecture from 3 video transcripts — captures concepts (agentic loop, JSONL trees, hooks, skills, compaction) but no line-level file inventory |
| **Hermes Agent internals** | 90 agent modules listed with filenames, 6 terminal backends, ACP adapter (11 files), learning loop flow, 15+ model providers with adapter filenames | Session 2 mentions Hermes by name in comparisons but never did a deep codebase read of Hermes |
| **OpenHuman internals** | 5 engine seams, 3 tool dispatchers, Aho-Corasick DFA refusal detection, 10+ memory modules, 15 subagent archetypes, ~80 domain modules listed, security tiers | Session 2 explored OpenHuman data directories for setup features but didn't do a full module inventory |
| **Cross-codebase matrix** | Side-by-side table: Language, source files, agent loop, TUI, providers, tools, memory, sessions, subagents, learning, channels, MCP, voice, search, browser, security, scheduler, CI/CD, extensions, export, computer use, config size | No equivalent matrix in Session 2 |
| **Locus OS infrastructure** | Documents CLI commands, core tools (12 listed), gateway, memory backends, 13 channels, voice backends (STT×4, TTS×4), search providers (5), browser, screen, computer use, context, display, learning, delegation, integrations, MCP, cron, security, coding subsystem, SETTINGS.md (28 sections) | Session 2 focused on Locus's *design philosophy* and *setup wizard*, not on cataloguing existing code modules |

> [!TIP]
> The audit excels at **breadth-of-inventory** — file-by-file, flag-by-flag, module-by-module listings across all 4 codebases. If you need to know "what files exist and what they do," the audit is the right document.

---

## 2. What Session 2 Covers That the Audit MISSES Entirely

This is the critical gap. Session 2 contains **substantial domain-specific knowledge** about Locus that the audit doesn't capture:

### 2.1 The Life OS Layer (14+ features — **completely absent** from audit)

The audit's Section 4 ("Locus OS") has zero mention of:

| Feature from Session 2 | Audit Coverage |
|------------------------|---------------|
| Four Factions Framework (Health/Leverage/Craft/Expression with weekly hour targets) | ❌ Not mentioned |
| Daily Capacity Score (DCS) formula: `((E+M+S)/3) × (1−ST/20)` | ❌ Not mentioned |
| Five Operating Modes (SURVIVAL → PEAK) gating task difficulty | ❌ Not mentioned |
| Task Weight Score (TWS) formula: `(P×0.4)+(U×0.4)+(D×0.2)` | ❌ Not mentioned |
| Three-Layer Goal Stack (Outcomes → Projects → Tasks, max caps) | ❌ Not mentioned |
| Action Gap Tracking (declared vs actual priority) | ❌ Not mentioned |
| Deferral Detection (3/5/8+ rule) with progressive alerts | ❌ Not mentioned |
| Lag Score + TWS Lag Bonus (faction rebalancing) | ❌ Not mentioned |
| Emergency Task Injection Protocol | ❌ Not mentioned |
| Exhaustion Predictor (5-day difficulty vs DCS average) | ❌ Not mentioned |
| Weekly Faction Rebalance | ❌ Not mentioned |
| Cross-Faction Efficiency ("3-birds-1-stone") | ❌ Not mentioned |
| Review Cadence System (Daily/Weekly/Monthly/Quarterly) | ❌ Not mentioned |
| Goal Stack Enforcement (max 7 outcomes, dead node detection) | ❌ Not mentioned |

### 2.2 The Brain Engine / "Samantha Layer" (13+ features — **mostly absent** from audit)

| Feature from Session 2 | Audit Coverage |
|------------------------|---------------|
| Inner Loop (APScheduler every 90min, proactive reasoning) | ❌ Not mentioned |
| State Engine with Inferred Cause Chain | ❌ Not mentioned |
| Multi-Horizon Pattern Engine (H1–H5 across 6h to all-time) | ❌ Not mentioned |
| User Identity Profile (PG table, rolling average, never hard-overwritten) | ❌ Not mentioned |
| Personal Reward Model (sklearn LogisticRegression, 👍/👎 feedback) | ❌ Not mentioned |
| Hebbian Pathway Weighting + STDP (Neo4j edge weights, biological decay) | Audit mentions "Holographic HRR" memory but **not** Hebbian weighting or STDP |
| Context Forge (800-token 6-layer assembler) | ❌ Not mentioned (audit says "basic" context) |
| Query Router / Intent Classifier (8 intent types) | ❌ Not mentioned |
| Spaced Repetition Memory Reinforcement | ❌ Not mentioned |
| Self-Evolving Architect Bot | ❌ Not mentioned |
| LOCUS_SHORTHAND (~4x token compression) | ❌ Not mentioned |
| Nightly Vault Ingestion Pipeline (multi-account Playwright scraping) | ❌ Not mentioned |
| Weekly Full Vault Synthesis | ❌ Not mentioned |

### 2.3 Interface Philosophy & Design Decisions (entirely Session 2 territory)

| Decision from Session 2 | Audit Coverage |
|-------------------------|---------------|
| Explicit rejection of TUI with reasoning | ❌ Audit lists "Curses TUI (basic)" as a feature |
| Telegram as PRIMARY interface (not just a channel) | Audit lists Telegram as one of 13 channels — misses the philosophical distinction |
| 4 Daily Structured Check-ins (Morning/Afternoon/Evening/Night) | ❌ Not mentioned |
| Voice Call Interface (Groq Whisper → Kokoro TTS → vault transcript) | Audit lists voice backends but not the call flow |
| Obsidian Dashboard replacing PWA | ❌ Not mentioned |
| Git for vault sync replacing Syncthing | ❌ Not mentioned |
| Manual OAuth replacing Composio | ❌ Not mentioned |
| pgvector replacing Qdrant + ChromaDB | ❌ Not mentioned |
| DeepSeek V4 Flash only (~$0.012/day, ~$4/year) | ❌ Not mentioned |
| Zero-cost constraint as 1st-class requirement | ❌ Not mentioned |

### 2.4 The "Don't Build on Pi" Analysis (Session 2 only)

Session 2 contains a detailed 7-point architectural analysis of why Locus should NOT be built on Pi Agent, covering:
- Language mismatch (TS↔Python boundary tax)
- Architectural mismatch (turn-based vs. always-on)
- TUI irrelevance for headless design
- Extension system limitations for Locus's needs
- What to borrow vs. what to couple
- The one scenario where Pi *would* make sense

The audit has **none** of this architectural reasoning.

### 2.5 The Headless Setup Wizard (Session 2 only)

Session 2 contains a complete command tree for the in-chat setup wizard:
- `/setup provider` (DeepSeek, Groq, OpenRouter)
- `/setup db` (health, migrate, reset)
- `/setup vault` (link, structure, index)
- `/setup skills` (install, list, sync)
- `/setup integration` (Google, Calendar, Gmail, Calendly)
- `/setup cron` (check-in times, review cadence)
- `/setup personality` (SOUL.md calibration)
- `/setup subconscious` (Inner Loop configuration)

The audit mentions slash commands but only lists generic ones (`/setup`, `/config`, `/help`, etc.).

---

## 3. Where the Audit Is Actually SHALLOWER on Locus

> [!WARNING]
> The audit's Locus OS section (Section 4) is the weakest section in the entire document. It's ~100 lines covering ~100 source files, while Pi gets ~300 lines for ~844 files, Hermes gets ~280 lines for ~5048 files, and OpenHuman gets ~50 dense lines for ~4725 files.

Specific shallowness:

| Audit Claim | Reality from Session 2 |
|------------|----------------------|
| "Basic ToolRegistry + LlmProvider" (agent loop) | Locus has a Context Forge, Query Router, 8-intent classifier, Inner Loop, State Engine — this is not "basic" |
| "Curses TUI (basic)" | Locus explicitly rejected TUI in favor of Telegram-native headless |
| "1 (OpenAI-compatible via httpx)" provider | Locus chose DeepSeek V4 Flash as the ONLY provider as an architectural decision, not a limitation |
| "Basic subagent + coding agent" (delegation) | Locus designed faction-specific sub-agents (Faction Planner, Vault Curator, Brain Analyst, Schedule Builder) |
| "Reflector + tool tracker + user profile" (learning) | Locus has Hebbian + STDP weighting, Personal Reward Model, Multi-Horizon Pattern Engine, Architect Bot — the "reflector" framing undersells it significantly |
| Audit Section 7 "Gaps": "No learning loop (beyond basic reflector)" | This is **factually wrong** if you include the Session 2 design. The Inner Loop, Pattern Engine, Hebbian weighting, and Reward Model constitute a far more sophisticated learning system than what Hermes or OpenHuman have — it's just in design/docs rather than fully implemented in code |

---

## 4. Honest Assessment

### What the Audit Does Well
- Exhaustive **file-level inventory** of Pi, Hermes, and OpenHuman internals
- Useful **cross-codebase comparison matrix** for infrastructure features
- Correctly identifies Locus's **infrastructure gaps** (no compaction code, no CI/CD, no full MCP server)
- Good for answering "what Python modules exist in the codebase right now"

### What the Audit Gets Wrong or Misses
- **Treats Locus as just another coding agent** and compares it on coding-agent dimensions. Locus's unique value (Life OS, behavioral metrics, proactive reasoning) is invisible in the audit.
- The "Features unique to Locus OS" section (lines 863-872) lists HRR memory, 13 channels, 5 search providers, voice backends, computer use, SETTINGS.md, secret_prompt, Neo4j, and deployment. It **entirely misses** the 51 unique features documented in Session 2 (Life OS metrics, brain engine, interface philosophy, infrastructure decisions).
- The "Gaps" analysis (Section 7) measures Locus against coding-agent expectations (compaction, skills marketplace, TUI keybindings) rather than against Locus's own design goals, where many of these "gaps" are intentional non-builds.
- The audit audited **code that exists in files**. Session 2 audited **design that exists in documentation**. For a project where the design docs are ahead of implementation, the audit misses most of what makes Locus unique.

### Bottom Line

**Session 2 and the feature audit are complementary, not overlapping.** The audit catalogs *what code exists* across 4 codebases. Session 2 catalogs *what Locus is supposed to be* and *why it's different*. Neither is a superset of the other. If you had to pick one document to hand someone who needs to understand Locus, you'd need Session 2 for the "why" and the audit for the "what's built."

The claim that the audit "should have more detailed information" than Session 2 is **only true for infrastructure-level features** (tools, providers, TUI components, file listings). For Locus-specific domain knowledge — the entire reason Locus exists — **Session 2 is significantly more detailed than the audit.**
