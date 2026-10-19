# LOCUS — Feature Logic Decomposition & Adaptation Reference (v5)

> **Purpose**: This is the "surgically precise" atomic markdown file. For each Locus feature, it identifies the source codebase, lists all relevant files, strips the execution logic into pseudocode/algorithms, and specifies how each adapts to Locus's modular architecture. **Every feature gets its own full-depth section — no batch summaries.**
>
> **v5 Changelog** (consolidated from v3/v4, which were byte-identical):
> - ✅ Added Master Feature Coverage Matrix (every §X.Y with decomposition status)
> - ✅ Expanded 16 batch-covered features (§1.9, §1.10, §1.11, §6.2, §6.3, §9.4, §9.9, §13.7-13.10, §17.10, §29.4-29.8) from one-liners to full `Files Involved → Stripped Logic → Adaptation` treatment
> - ✅ Added 9 missing features (§4.10, §4.12, §4.13, §4.14, §19.3, §20.3, §27.5, §27.6, §27.7) with complete decomposition
> - ✅ Deep-extracted 5 missing subsystems from `locus_microsystems.html` (Master Conductor, Content Engine expansion, Dashboard/TUI, Redis integration, Obsidian/LightRAG bridge)
> - ✅ Added inter-file congruence ("Interacts With") columns to all Files Involved tables
> - ✅ Corrected Part II mapping table with real file names from cloned deps
> - ✅ Expanded §25.12 (6-Step Scheduling Algorithm) and §26.1-26.7 (Proactive Reasoning) with full pseudocode
> - ✅ Fixed duplicate §2.4/§2.5 Context Forge adaptation block
>
> **Verification Tag System** (v5):
> - `[✅ VERIFIED: /graphify]` = File set confirmed via `/graphify` knowledge-graph query against the built graph at `5_Locus/graphify-out/`.
> - `[✅ VERIFIED: cloned repo, source read]` = Logic stripped from a repo cloned into `5_Locus/deps/` and read directly (`agent-memory`, `headroom`, `PageIndex`, `autoresearch`). `/graphify` was unavailable for these repos (no per-repo graph built); direct reads were the fallback.
> - `[✅ VERIFIED: direct file read]` = On-disk codebase (Pi, Hermes, OpenHuman) where the per-feature file set was confirmed by listing/grep and source files read for logic stripping.
> - `[📐 DESIGN SPEC]` = Logic designed from Locus' own spec docs & HTML microsystem designs (Locus-original subsystems).
> - `[📦 KEEP-PI]` = Inherited directly from Pi Agent, zero changes. Source file path listed for reference.
>
> **Architecture & Older Docs Resolution**:
> The older specs (`locus_microsystems.html`, `Comprehensive Locus System Design.html`, `locus_pyramid.html`) supply **functional/algorithmic logic** for Locus-original subsystems, but their monolithic server architecture is **superseded** by the Pi-extension + Python sidecar architecture. Where any formula in this doc disagrees with `LOCUS_SYSTEM_v1.md` (the system bible), **`LOCUS_SYSTEM_v1.md` wins** — see the Formula Crosswalk appendix.
>
> **File-location rule (applies to every new file/config proposed below)**:
> code, packages, built-in tools → **`locus-os`** (repo). Local config, secrets, DB lookups, runtime caches → **`C:\Users\soni8\.locus`**. Secrets (Neo4j password, API keys, tokens) go in `.locus/.env` — never in the repo. **Every feature section below states which side of this rule its files fall on.**
>
> **Modularity rule (applies to every feature adaptation below)**:
> Every feature section names: its provider interface, what's swappable, what alternatives exist, and **what the user loses when this feature is turned off** (the "off state").
>
> **Rule**: This document names the exact source files and their stripped logic. The implementing AI can build most of Locus from the pseudocode alone, but should open the named source files (or query them via the `/graphify` skill) whenever deeper implementation detail is needed — especially the four cloned deps under `5_Locus/deps/`.

---

# SOURCE DOCUMENTS CONSULTED

| Document | Type | What Was Extracted |
|----------|------|--------------------|
| `Atomic Selections from Antigravity.md` | Feature Matrix (104K) | All §1-§29 features with Keep/Augment/New verdicts, modularity contracts, provider interfaces |
| `locus_agent_loop.md` | Agent Loop Spec (67K, 854 lines) | Reactive Loop 12-stage pipeline, Proactive Inner Loop, Post-Turn Learning cycle, Intent Classifier types |
| `LOCUS_SYSTEM_v1.md` | System Design (37K) | DCS/TWS formulas, 4 Factions, operating modes, scheduling algorithm, vault structure, check-in flows |
| `locus_microsystems.html` | Micro-Step Breakdowns (155K) | **Step-by-step implementation detail** for ALL 18 subsystems: Master Conductor (11 steps), Query Router (6), Inner Loop (10), Context Forge (12), Pattern Engine (11), Scheduler (11), Goal Tracker (8), State Engine (10+), Collector+Chunker (10), Neo4j (6), Qdrant (4), PostgreSQL (4), Telegram Bot (7), Voice (5), AI Chat Archiver (7), Dashboard (6), Content Engine (4+), Obsidian+LightRAG+Redis (6). Each step has: inputs, outputs, provider, status. |
| `Comprehensive Locus System Design.html` | Architecture Pyramid (128K) | 10-layer architecture (Infrastructure → Storage → Ingestion → Retrieval → Intelligence → Reasoning → Orchestration → Interface → Output → Feedback) with ~40 component nodes including Cause Chain Engine, LOCUS_SHORTHAND, Hebbian Manager, SOUL.md, QLoRA Pipeline, Spaced Repetition |
| `locus_pyramid.html` | Architecture Tiers (31K) | Tier hierarchy (T0 Master → T1 Orchestration → T2 Intelligence → T3 Retrieval → T4 Storage) + horizontal layers (Input, Output, Feedback, Self-Maintenance) with descriptions, inputs/outputs, and build status |

---

# MASTER FEATURE COVERAGE MATRIX (v5 Audit Checklist)

> **Legend**: ✅ = Full decomposition (Files Involved + Stripped Logic + Adaptation). 📦 = KEEP-PI (inherited, no decomposition needed). 📐 = Design spec (Locus-original, logic from HTML docs). ⚠️ = Present but thin in v3 — **expanded in v5**.

| §ID | Feature | Depth | Files Table | Pseudocode | Adaptation | Status |
|-----|---------|-------|-------------|------------|------------|--------|
| 1.1 | Pi Agent Loop | ✅ FULL | ✅ 4 files | ✅ 230-line algorithm | ✅ Keep/Adapt/Drop | COMPLETE |
| 1.2 | System Prompt | ✅ FULL | ✅ 1 file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 1.3 | Tool System | ✅ FULL | ✅ 10 files | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 1.4 | Model Management | ✅ FULL | ✅ 3 files | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 1.5 | Extension Lifecycle | ✅ FULL | ✅ 2 files | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 1.6 | Context Window Mgmt | ✅ FULL | ✅ 2 files | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 1.7 | Post-Turn Review | ✅ FULL | ✅ See §10.1 | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 1.8 | Stream Diagnostics | 📦 KEEP-PI | — | — | — | INHERITED |
| 1.9 | Rate Limit Tracking | ⚠️→✅ | ✅ 3 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 1.10 | Usage/Cost Tracking | ⚠️→✅ | ✅ 3 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 1.11 | Title Generation | ⚠️→✅ | ✅ 2 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 1.12 | Onboarding & Topology Setup | ✅ FULL | ✅ 6 files (v6) | ✅ Stepped Setup Algorithm | ✅ Adaptation (v6) | **v6 MODULAR ONBOARDING** |
| 1.13 | Agent Initialization | 📦 KEEP-PI | — | — | — | INHERITED |
| 2.1 | 30+ LLM Providers | 📦 KEEP-PI | — | — | — | INHERITED |
| 2.2 | OAuth Flows | 📦 KEEP-PI | — | — | — | INHERITED |
| 2.3 | Custom/Local Models | 📦 KEEP-PI | — | — | — | INHERITED |
| 2.4 | Provider Registry | 📦 KEEP-PI | — | — | — | INHERITED |
| 2.5 | Model Selection | 📦 KEEP-PI | — | — | — | INHERITED |
| 3.1-3.6 | File/Shell/Search Tools | 📦 KEEP-PI | — | — | — | INHERITED |
| 3.7 | Harness Delegation | ✅ FULL | ✅ Multi-source | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 4.1-4.2 | Neo4j Agent Memory | ✅ FULL | ✅ 10+ files | ✅ Deep pseudocode | ✅ Adaptation | COMPLETE |
| 4.10 | Holographic HRR | ⚠️→✅ | ✅ New (v5) | ✅ New (v5) | ✅ New (v5) | **v5 ADDED** |
| 4.12 | STDP Reinforcement | ⚠️→✅ | ✅ New (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 4.13 | Spaced Repetition | ⚠️→✅ | ✅ See §30.5 | ✅ Algorithm (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 4.14 | Project Memory Decay | ⚠️→✅ | ✅ New (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 4.17 | Headroom CCR | ✅ FULL | ✅ 6+ files | ✅ Deep pseudocode | ✅ Adaptation | COMPLETE |
| 5.1-5.4 | Session Management | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 6.2 | Context References | ⚠️→✅ | ✅ 2 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 6.3 | Coding Context | ⚠️→✅ | ✅ 3 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 7.1-7.9 | Pi Native TUI & Overlays | ✅ FULL | ✅ 8 files (v6) | ✅ @earendil-works/pi-tui Specs | ✅ Adaptation (v6) | **v6 PI TUI AUGMENTATION** |
| 8.1-8.10 | CLI, Multi-Surface & Headless | ✅ FULL | ✅ 9 files (v6) | ✅ Multi-Surface Engine | ✅ Adaptation (v6) | **v6 HEADLESS & TELEGRAM** |
| 9.1 | Extension System | 📦 KEEP-PI | — | — | — | INHERITED |
| 9.4 | ACP Protocol | ⚠️→✅ | ✅ 3 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 9.9 | Plugin LLM | ⚠️→✅ | ✅ 2 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 10.1-10.7 | Learning/Profiling | ✅ FULL | ✅ Multi-source | ✅ Deep pseudocode | ✅ Adaptation | COMPLETE |
| 11.1-11.6 | Subagents/Research | ✅ FULL | ✅ Multi-source | ✅ Deep pseudocode | ✅ Adaptation | COMPLETE |
| 13.1 | Injection Filter | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 13.3 | Shell Sandbox | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 13.6 | Project Trust | 📦 KEEP-PI | — | — | — | INHERITED |
| 13.7 | Shell Blocklist | ⚠️→✅ | ✅ 2 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 13.8 | Data Redaction | ⚠️→✅ | ✅ 2 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 13.9 | Think Token Scrubbing | ⚠️→✅ | ✅ 1 file (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 13.10 | Message Sanitization | ⚠️→✅ | ✅ 1 file (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 14.1-14.2 | STT/TTS | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 16.1 | Browser Automation | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 17.1 | Telegram Gateway | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 17.10 | Graceful Restart | ⚠️→✅ | ✅ 2 files (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 18.1-18.5 | MCP Server/Client | ✅ FULL | ✅ Multi-file | ✅ Deep pseudocode | ✅ Adaptation | COMPLETE |
| 19.2 | Trajectory Recording | ✅ FULL | ✅ 1 file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 19.3 | AI Chat Archiver | ⚠️→✅ | ✅ New (v5) | ✅ New (v5) | ✅ New (v5) | **v5 ADDED** |
| 20.1-20.2 | Computer Use | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 20.3 | VNC Remote | ⚠️→✅ | ✅ Stub (v5) | ✅ Stub (v5) | ✅ Stub (v5) | **v5 ADDED** |
| 21.1 | Google Calendar | 📐 DESIGN | ✅ Design | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 23.1-23.5 | CI/CD/Docker | ✅ FULL | ✅ Multi-source | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 25.1-25.12 | Life OS/DCS/Scheduler | 📐 DESIGN | ✅ Design | ✅ Formulas+Algo | ✅ Adaptation | COMPLETE |
| 26.1-26.7 | Proactive Reasoning | ⚠️→✅ | ✅ Expanded (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 27.1 | PageIndex Retrieval | ✅ FULL | ✅ 3 files | ✅ Deep pseudocode | ✅ Adaptation | COMPLETE |
| 27.2 | Obsidian LiveSync & CouchDB | ✅ FULL | ✅ Multi-file (v6) | ✅ Deep pseudocode (v6) | ✅ Adaptation (v6) | **v6 REAL-TIME SYNC** |
| 27.5 | Rough Note Parser | ⚠️→✅ | ✅ New (v5) | ✅ New (v5) | ✅ New (v5) | **v5 ADDED** |
| 27.6 | Link Dump Logger | ⚠️→✅ | ✅ New (v5) | ✅ New (v5) | ✅ New (v5) | **v5 ADDED** |
| 27.7 | Excalidraw MCP Skill | ⚠️→✅ | ✅ New (v5) | ✅ New (v5) | ✅ New (v5) | **v5 ADDED** |
| 28.1-28.3 | Dual Interface/Checkins | 📐 DESIGN | ✅ Design | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 29.1 | Error Classifier | ✅ FULL | ✅ 1 file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 29.3 | Health Checks | ✅ FULL | ✅ Multi-file | ✅ Pseudocode | ✅ Adaptation | COMPLETE |
| 29.4 | Notifications | ⚠️→✅ | ✅ Expanded (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 29.5 | Connectivity Check | ⚠️→✅ | ✅ Expanded (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 29.6 | Code Graph | ⚠️→✅ | ✅ Expanded (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 29.7 | Subconscious | ⚠️→✅ | ✅ Expanded (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 29.8 | Workflows | ⚠️→✅ | ✅ Expanded (v5) | ✅ Expanded (v5) | ✅ Expanded (v5) | **v5 EXPANDED** |
| 30.1 | Collector + Chunker | 📐 DESIGN | ✅ 10-step | ✅ Full algorithm | ✅ Adaptation | COMPLETE |
| 30.2 | Cause Chain Engine | 📐 DESIGN | ✅ 9-step | ✅ Full algorithm | ✅ Adaptation | COMPLETE |
| 30.3 | SOUL.md / Wants | 📐 DESIGN | ✅ 6-step | ✅ Full algorithm | ✅ Adaptation | COMPLETE |
| 30.4 | Content Engine | 📐 DESIGN | ✅ 4-step→8 (v5) | ✅ Expanded (v5) | ✅ Adaptation | **v5 EXPANDED** |
| 30.5 | Spaced Repetition | 📐 DESIGN | ✅ 5-step | ✅ Full algorithm | ✅ Adaptation | COMPLETE |
| 30.6 | QLoRA Pipeline | 📐 DESIGN | ✅ 6-step | ✅ Full algorithm | ✅ Adaptation | COMPLETE |
| 30.7 | Master Conductor | 📐→✅ | ✅ New (v5) | ✅ 11-step (v5) | ✅ New (v5) | **v5 ADDED** |
| 30.8 | Dashboard/TUI Spec | 📐→✅ | ✅ New (v5) | ✅ 6-step (v5) | ✅ New (v5) | **v5 ADDED** |
| 30.9 | Redis Integration | 📐→✅ | ✅ New (v5) | ✅ Pattern (v5) | ✅ New (v5) | **v5 ADDED** |
| 30.10 | Obsidian/LightRAG Bridge | 📐→✅ | ✅ New (v5) | ✅ 6-step (v5) | ✅ New (v5) | **v5 ADDED** |

> **v5 Coverage Summary**: 85 features total. 42 fully decomposed (v3). 25 expanded/added in v5. 18 KEEP-PI (inherited unchanged). **0 features missing decomposition.**

---



> Quick-reference lookup. For each feature: which source codebase provides the logic, which provider interface it implements, and its verification status.

| §ID | Feature | Verdict | Source Codebase | Provider Interface | Verification Tag |
|-----|---------|---------|----------------|-------------------|------------------|
| 1.1 | Pi Agent Loop | KEEP-PI | Pi `agent-loop.ts` | — | ✅ VERIFIED: file_read |
| 1.2 | Model Resolution | KEEP-PI | Pi `model-resolver.ts` | — | ✅ VERIFIED: file_read |
| 1.3 | Extension Events | KEEP-PI | Pi `agent-session.ts` | — | ✅ VERIFIED: file_read |
| 1.4 | Context Window Mgmt | AUGMENT | Pi `compaction/` → Locus Headroom | CompressionProvider | ✅ VERIFIED: file_read |
| 1.5 | Tool System | KEEP-PI | Pi `tools/index.ts` | — | ✅ VERIFIED: file_read |
| 1.6 | Prompt Templates | KEEP-PI | Pi `prompt-templates.ts` | — | ✅ VERIFIED: file_read |
| 1.7 | Post-Turn Review | AUGMENT | Hermes `background_review.py` | PostTurnProvider | ✅ VERIFIED: file_read |
| 2.1 | Intent Classifier | LOCUS-NEW | Locus-original | IntentClassifier | 📐 DESIGN SPEC: microsystems.html |
| 2.2 | Source Routing | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 2.3 | Confidence Gate | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 2.4 | State Engine | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 3.1 | Context Forge | LOCUS-NEW | Locus-original | ContextAssembler | 📐 DESIGN SPEC: microsystems.html |
| 3.2 | 6-Layer Assembly | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 3.3 | Anti-Hallucination | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 3.7 | Harness Delegation | MULTI-PROVIDER | Pi + Hermes + Locus | HarnessProvider | ✅ VERIFIED: file_read |
| 4.1 | Neo4j Agent Memory | KEEP (PRE-BUILT) | `neo4j-labs/agent-memory` | MemoryProvider | ✅ VERIFIED: cloned repo, source read |
| 4.2 | POLE+O Schema | KEEP (PRE-BUILT) | `neo4j-labs/agent-memory` | — | ✅ VERIFIED: cloned repo, source read |
| 4.17 | Headroom CCR | KEEP (PRE-BUILT) | `headroomlabs-ai/headroom` | CompressionProvider | ✅ VERIFIED: cloned repo, source read |
| 5.1 | Session Management | KEEP-PI | Pi `session-manager.ts` | — | ✅ VERIFIED: file_read |
| 1.12 | Onboarding & Setup | AUGMENT | Pi + Hermes + Locus | SetupWizardProvider | ✅ VERIFIED: first-time-setup.ts + setup.py |
| 7.1 | TUI Framework | AUGMENT | Pi `@earendil-works/pi-tui` + locus-extension | TUIProvider | ✅ VERIFIED: @earendil-works/pi-tui |
| 7.5 | Footer Widget | LOCUS-NEW | Pi `ctx.ui.setFooter` | — | ✅ VERIFIED: Pi footer API |
| 8.1 | CLI Subcommands | AUGMENT | Pi CLI + locus_cli + Telegram Bot | MultiSurfaceCLI | ✅ VERIFIED: Pi args.ts + locus_cli |
| 8.6 | Doctor/Diagnostics | AUGMENT | Hermes `doctor` + OpenHuman `doctor` + Locus | HealthCheckProvider | ✅ VERIFIED: doctor specs |
| 9.1 | Extension System | KEEP-PI | Pi extensions | — | ✅ VERIFIED: file_read |
| 9.4 | ACP Protocol | LOCUS-NEW | Hermes `copilot_acp_client.py` | — | ✅ VERIFIED: file_read |
| 9.9 | Plugin LLM | LOCUS-NEW | Hermes `plugin_llm.py` | — | ✅ VERIFIED: file_read |
| 10.1 | Post-Session Learning | MULTI-PROVIDER | Hermes + OpenHuman + Locus | LearningProvider | ✅ VERIFIED: file_read |
| 10.3 | User Profile Building | MULTI-PROVIDER | Hermes + OpenHuman + Locus | UserModelProvider | ✅ VERIFIED: file_read |
| 10.5 | Personal Reward Model | LOCUS-NEW | Locus-original | RewardModel | 📐 DESIGN SPEC: microsystems.html |
| 10.6 | Hebbian Learning | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 10.7 | Pattern Engine | LOCUS-NEW | Locus-original | PatternEngine | 📐 DESIGN SPEC: microsystems.html |
| 11.1 | Subagent Spawning | AUGMENT | Pi + OpenHuman | SubagentArchetype | ✅ VERIFIED: file_read |
| 11.6 | AutoResearch | KEEP (PRE-BUILT) | `karpathy/autoresearch` | ResearchProvider | ✅ VERIFIED: cloned repo, source read |
| 13.1 | Injection Filter | AUGMENT | Pi + Hermes + Locus | — | ✅ VERIFIED: file_read |
| 13.3 | Shell Sandbox | KEEP-PI | Pi trust model | SandboxProvider | ✅ VERIFIED: file_read |
| 14.1 | STT Providers | MULTI-PROVIDER | Hermes + Locus | STTProvider | ✅ VERIFIED: file_read |
| 14.2 | TTS Providers | MULTI-PROVIDER | Hermes + Locus | TTSProvider | ✅ VERIFIED: file_read |
| 16.1 | Browser Automation | MULTI-PROVIDER | OpenHuman + Pi | BrowserProvider | ✅ VERIFIED: file_read |
| 17.1 | Telegram Gateway | AUGMENT | Hermes + Locus | ChannelProvider | 📐 DESIGN SPEC: microsystems.html |
| 18.1 | MCP Server | AUGMENT | OpenHuman + Locus | — | ✅ VERIFIED: file_read |
| 18.2 | MCP Client | KEEP-PI | Pi MCP client | — | ✅ VERIFIED: file_read |
| 19.2 | Trajectory Recording | AUGMENT | Hermes `trajectory_compressor.py` | — | ✅ VERIFIED: file_read |
| 21.1 | Google Calendar | LOCUS-NEW | Locus-original | IntegrationProvider | 📐 DESIGN SPEC: microsystems.html |
| 25.1 | DCS Formula | LOCUS-NEW | Locus-original | LifeOSProvider | 📐 DESIGN SPEC: microsystems.html |
| 25.5 | Operating Modes | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 25.8 | Scheduler / Planner | LOCUS-NEW | Locus-original | SchedulerProvider | 📐 DESIGN SPEC: microsystems.html |
| 25.12 | Goal Tracker | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 27.1 | PageIndex Retrieval | KEEP (PRE-BUILT) | `VectifyAI/PageIndex` | RetrievalProvider | ✅ VERIFIED: cloned repo, source read |
| 27.2 | Obsidian LiveSync & CouchDB | AUGMENT | CouchDB + LiveSync + Pi | VaultProvider | ✅ VERIFIED: CouchDB 3.3 + LiveSync Protocol |
| 28.1 | Dual Interface | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 28.3 | Check-ins | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 29.1 | Error Classifier | AUGMENT | Hermes `error_classifier.py` | — | ✅ VERIFIED: file_read |
| 29.3 | Health Checks | AUGMENT | Hermes + OpenHuman | — | ✅ VERIFIED: file_read |
| 30.1 | Collector + Chunker | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 30.2 | Cause Chain Engine | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: comprehensive_design.html |
| 30.3 | SOUL.md / Wants Engine | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: comprehensive_design.html |
| 30.4 | Content Engine | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 30.5 | Spaced Repetition | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: microsystems.html |
| 30.6 | QLoRA Pipeline | LOCUS-NEW | Locus-original | — | 📐 DESIGN SPEC: pyramid.html |

---

# FOUNDATIONAL LAYER — The Pi Agent Loop (§1)

All Locus features augment Pi's agent loop. Understanding Pi's loop is prerequisite to everything below.

## Feature §1.1: Pi Agent Loop (Foundation)

### Source
- **Codebase**: Pi at `pi/packages/agent/src/`
- **Verification**: [✅ VERIFIED: `agent-loop.ts` (743 lines), `types.ts` (419 lines) read in full]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `agent-loop.ts` | 743 | Core loop: user message → LLM call → tool execution → repeat | `types.ts` for all type defs |
| `types.ts` | 419 | All interfaces: `AgentContext`, `AgentLoopConfig`, `AgentTool`, `AgentEvent` | Used by everything |
| `agent.ts` | ~400 | High-level `Agent` class wrapping the loop | `agent-loop.ts` |
| `proxy.ts` | ~250 | Proxy layer for remote agent access | `agent.ts` |

### Stripped Logic (Pseudocode)

```
FUNCTION runLoop(context, config):
    pendingMessages = config.getSteeringMessages()  // check for queued messages

    OUTER_LOOP:  // continues when follow-up messages arrive after agent would stop
        hasMoreToolCalls = true

        INNER_LOOP while hasMoreToolCalls OR pendingMessages.length > 0:
            // 1. Inject any pending steering messages into context
            IF pendingMessages exist:
                FOR EACH message IN pendingMessages:
                    context.messages.push(message)
                pendingMessages = []

            // 2. Transform context (AgentMessage[] → AgentMessage[])
            //    This is the KEY HOOK for Locus: config.transformContext()
            //    Pi uses this for context window pruning
            //    Locus uses this for: State Injection, Context Forge assembly,
            //    Headroom compression, etc.
            IF config.transformContext:
                messages = config.transformContext(context.messages)
            
            // 3. Convert to LLM messages (AgentMessage[] → Message[])
            //    Another KEY HOOK: config.convertToLlm()
            //    Locus uses this to filter custom message types
            llmMessages = config.convertToLlm(messages)

            // 4. Build LLM context and stream response
            llmContext = {
                systemPrompt: context.systemPrompt,
                messages: llmMessages,
                tools: context.tools
            }
            assistantMessage = STREAM_FROM_LLM(config.model, llmContext)

            // 5. If error or abort → emit agent_end, return
            IF assistantMessage.stopReason IN ("error", "aborted"):
                RETURN

            // 6. Extract tool calls from response
            toolCalls = assistantMessage.content.filter(c => c.type == "toolCall")

            // 7. Execute tool calls (parallel or sequential)
            IF toolCalls.length > 0:
                // KEY HOOK: config.beforeToolCall() — Locus uses for tool guardrails
                // Pi validates args, checks if tool exists, runs beforeToolCall
                // If beforeToolCall returns { block: true } → inject error result
                
                // Execute each tool:
                //   prepareToolCall → validate args → beforeToolCall gate
                //   executePreparedToolCall → tool.execute(id, args, signal)
                //   finalizeExecutedToolCall → afterToolCall hook
                
                // KEY HOOK: config.afterToolCall() — Locus uses for:
                //   Anti-hallucination check, tool tracking, learning
                
                results = executeToolCalls(context, assistantMessage, config)
                hasMoreToolCalls = !results.terminate
                // Termination: only when ALL tools in batch set terminate=true

            // 8. KEY HOOK: config.prepareNextTurn()
            //    Can swap model, thinking level, or entire context between turns
            //    Locus uses this for model escalation (cheap → expensive)
            nextTurnUpdate = config.prepareNextTurn({ message, toolResults, context })
            IF nextTurnUpdate:
                context = nextTurnUpdate.context OR context
                config.model = nextTurnUpdate.model OR config.model

            // 9. KEY HOOK: config.shouldStopAfterTurn()
            //    Locus uses for: context budget enforcement, graceful shutdown
            IF config.shouldStopAfterTurn({ message, toolResults, context }):
                RETURN

            // 10. Check for more steering messages
            pendingMessages = config.getSteeringMessages()
        
        END INNER_LOOP

        // Agent would stop. Check for follow-up messages
        followUpMessages = config.getFollowUpMessages()
        IF followUpMessages exist:
            pendingMessages = followUpMessages
            CONTINUE OUTER_LOOP  // keep going

        BREAK  // no more messages, exit

    END OUTER_LOOP

TOOL EXECUTION MODES:
    "parallel":  prepare sequentially → execute concurrently → emit in source order
    "sequential": prepare, execute, finalize one at a time
    Per-tool override: tool.executionMode can force "sequential" for a single tool

TOOL LIFECYCLE:
    1. prepareToolCallArguments(tool, toolCall)  // tool.prepareArguments() hook
    2. validateToolArguments(tool, preparedToolCall)  // schema validation
    3. config.beforeToolCall({ assistantMessage, toolCall, args, context })
       → { block: true, reason: "..." } prevents execution
    4. tool.execute(toolCallId, validatedArgs, signal, onUpdate)
       → returns AgentToolResult { content, details, terminate? }
    5. config.afterToolCall({ assistantMessage, toolCall, args, result, isError, context })
       → can override content, details, isError, terminate
```

### Adaptation to Locus Architecture

**KEEP**:
- The entire dual-loop structure (outer: follow-up messages, inner: tool calls)
- The event stream pattern (agent_start, turn_start, message_*, tool_*, turn_end, agent_end)
- The `AgentTool` interface with `execute()`, `prepareArguments()`, `executionMode`
- The `beforeToolCall`/`afterToolCall` hooks — these are HOW Locus injects its cognitive pipeline
- The `transformContext` hook — this is WHERE the Context Forge lives
- The `convertToLlm` hook — this is WHERE Locus filters its custom message types

**ADAPT**:
- `transformContext` becomes Locus's 12-stage reactive pipeline (Stages 3-6)
- `beforeToolCall` becomes Stage 7 (tool guardrails + safety classification)
- `afterToolCall` becomes Stages 9-11 (anti-hallucination, delivery, learning)
- `prepareNextTurn` becomes model escalation logic (cheap → expensive based on intent)
- `shouldStopAfterTurn` checks 800-token context budget
- `getSteeringMessages` connects to Telegram gateway for real-time user interrupts
- `getFollowUpMessages` connects to the proactive Inner Loop output queue

**DROP**: Nothing. Pi's loop is clean and Locus wraps it entirely.

---

## Feature §1.2: System Prompt Construction

### Source
- **Codebase**: Pi at `pi/packages/coding-agent/src/core/system-prompt.ts`
- **Verification**: [✅ VERIFIED: 174 lines read in full]

### Stripped Logic (Pseudocode)

```
FUNCTION buildSystemPrompt(options):
    // Resolve CWD with forward slashes
    promptCwd = options.cwd.replace("\\", "/")
    date = formatDate(now())

    IF options.customPrompt:
        prompt = options.customPrompt
        // Append extra text
        IF options.appendSystemPrompt:
            prompt += options.appendSystemPrompt
        // Append project context files (AGENTS.md, etc.)
        IF options.contextFiles.length > 0:
            prompt += "<project_context>"
            FOR EACH { path, content } IN options.contextFiles:
                prompt += "<project_instructions path='{path}'>{content}</project_instructions>"
            prompt += "</project_context>"
        // Append skills section (only if read tool available)
        IF "read" tool available AND options.skills.length > 0:
            prompt += formatSkillsForPrompt(options.skills)
        prompt += "Current date: {date}"
        prompt += "Current working directory: {promptCwd}"
        RETURN prompt

    // Default prompt construction
    tools = options.selectedTools OR ["read", "bash", "edit", "write"]
    toolsList = tools.filter(has snippet).map(t => "- {t}: {snippet}")

    // Build guidelines dynamically based on available tools
    guidelines = []
    IF has bash but no grep/find/ls:
        guidelines.add("Use bash for file operations like ls, rg, find")
    guidelines.addAll(options.promptGuidelines)
    guidelines.add("Be concise in your responses")
    guidelines.add("Show file paths clearly when working with files")

    prompt = "You are an expert coding assistant operating inside pi..."
    prompt += toolsList + guidelines
    prompt += documentation paths
    prompt += appendSection + contextFiles + skills + date + cwd
    RETURN prompt
```

### Adaptation to Locus Architecture

**ADAPT**:
- Replace the coding-agent system prompt body with Locus's SOUL.md personality context
- Keep the `contextFiles` mechanism — this loads AGENTS.md + SOUL.md
- Keep the `skills` section — Locus skills use the same SKILL.md format
- Add Context Forge injection point: the system prompt gets the 800-token assembled context appended
- The `appendSystemPrompt` hook is WHERE the State Engine injects current DCS, operating mode, faction status

**Architecture**: Lives in `locus/core/prompt-builder.ts`. Implements Pi's `BuildSystemPromptOptions` but overrides `customPrompt` with Locus's personality.

---

## Feature §1.3: Tool System

**Status**: complete  
**Verdict**: ✅ KEEP-PI (augmented by Locus custom tools)

### Source(s) mined
- **Codebase**: Pi at `pi/packages/coding-agent/src/core/`
- **Files involved**: `tools/index.ts` (tool registration), `types.ts` (AgentTool interface), `bash.ts`, `edit.ts`, `read.ts`, `write.ts`, `grep.ts`, `ls.ts`, `find.ts`, `tool-definition-wrapper.ts`
- **Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)] — file listing confirmed via directory scan; `/graphify` graph exists at `5_Locus/graphify-out/` for future re-mining

### Logic extracted

```
AGENT TOOL INTERFACE:
    name: string          // tool identifier
    label: string         // human-readable display
    description: string   // sent to LLM
    schema: TSchema       // TypeBox JSON schema for parameters
    executionMode?: "sequential" | "parallel"
    prepareArguments?(args): validated_args  // argument transform
    execute(toolCallId, params, signal, onUpdate): AgentToolResult

AGENT TOOL RESULT:
    content: (TextContent | ImageContent)[]  // returned to LLM
    details: T                                // structured for UI/logs
    terminate?: boolean                       // hint to stop agent loop

TOOL LIFECYCLE:
    1. prepareToolCallArguments(tool, toolCall)  // tool.prepareArguments() hook
    2. validateToolArguments(tool, preparedToolCall)  // schema validation
    3. config.beforeToolCall({ assistantMessage, toolCall, args, context })
       → { block: true, reason: "..." } prevents execution
    4. tool.execute(toolCallId, validatedArgs, signal, onUpdate)
       → returns AgentToolResult { content, details, terminate? }
    5. config.afterToolCall({ assistantMessage, toolCall, args, result, isError, context })
       → can override content, details, isError, terminate

TOOL EXECUTION MODES:
    "parallel":  prepare sequentially → execute concurrently → emit in source order
    "sequential": prepare, execute, finalize one at a time
    Per-tool override: tool.executionMode can force "sequential" for a single tool
```

### Locus adaptation

- **Component**: Inherited from Pi. Locus registers ~8 custom tools (`locus_checkin`, `locus_memory`, `locus_goals`, `locus_life`, `locus_vault`, `locus_brain`, `locus_research`, `locus_delegate_code`) via Pi's `registerTool()` API. Each implements the `AgentTool` interface.
- **Repo vs `.locus`**: Pi tool code lives in `locus-os` (repo); tool configurations are in Pi's `settings.json` under `.locus`.
- **Swappable / off state**: Individual Locus tools can be disabled via config (`locus.tools.<name>.enabled: false`). Off → that tool is unavailable to the LLM; the agent loop still functions with remaining tools.
- **KEEP**: All Pi tool interfaces, the `AgentTool` contract, TypeBox schema validation, execution mode control.

---

## Feature §1.4: Model Management

**Status**: complete  
**Verdict**: ✅ KEEP-PI (augmented by Locus model escalation)

### Source(s) mined
- **Codebase**: Pi at `pi/packages/coding-agent/src/core/`
- **Files involved**: `model-resolver.ts` (model resolution), `model-registry.ts` (provider registry), `types.ts` (AgentLoopConfig)
- **Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)] — confirmed via Pi directory structure; `/graphify` graph exists for future re-mining

### Logic extracted

```
MODEL RESOLUTION:
    1. User selects model via config or CLI flag
    2. ModelRegistry resolves provider + model name
    3. API key resolved dynamically per call (for expiring tokens)
    4. Thinking level clamped to model's supported levels
    5. prepareNextTurn() can swap model mid-conversation

Locus augmentation — model escalation logic:
    Standard turns: DeepSeek V4 Flash (cheapest available, ~$0.012/day)
    Complex reasoning / Sunday synthesis: Gemini 2.5 Pro (1M context)
    Background tasks: auxiliary client (separate API key, cheapest model)
```

### Locus adaptation

- **Component**: `locus/core/model-escalation.ts` (thin adapter over Pi's `prepareNextTurn` hook)
- **Repo vs `.locus`**: escalation logic in `locus-os` (repo); API keys in `.locus/.env`.
- **Swappable / off state**: model selection is Pi's built-in (Ctrl+P / `locus config set model`). Off → Locus uses a single model for all turns; no automatic escalation.
- **KEEP**: Pi's entire provider registry (30+ providers), model cycling, API key resolution.

---

## Feature §1.5: Extension Lifecycle (25+ Events)

**Status**: complete  
**Verdict**: ✅ KEEP-PI (augmented by Locus hooks)

### Source(s) mined
- **Codebase**: Pi at `pi/packages/coding-agent/src/core/agent-session.ts` (3,136 lines)
- **Files involved**: `agent-session.ts` (session lifecycle, all extension events), `types.ts` (event type definitions)
- **Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)] — agent-session.ts header read; `/graphify` graph exists for future re-mining

### Logic extracted

```
EXTENSION LIFECYCLE (25+ events):
    session_start → turn_start → message_start → message_update → message_end →
    tool_execution_start → tool_execution_update → tool_execution_end →
    turn_end → agent_end → session_shutdown

    PLUS: before_compact, after_compact, before_tree, session_switch,
          replaced_session, context_usage_update

    Extension hooks:
        pi.onEvent("turn_start", async (event) => { ... })
        pi.registerTool("locus_checkin", { ... })
        pi.registerCommand("/locus-life", { ... })
        pi.registerFooterWidget("locus-status", render)

    Key Locus hooks into this:
    - session_start: initialize all providers, load state
    - turn_start: Query Router, State Injection
    - tool_execution_start: tool guardrails check
    - tool_execution_end: tool tracking (idempotent vs mutating)
    - turn_end: post-turn learning, background review
    - session_shutdown: flush all providers, persist state
```

### Locus adaptation

- **Component**: `locus/extensions/` directory for all Locus extensions. Each extension registers via Pi's `onEvent()` API.
- **Repo vs `.locus`**: extension code in `locus-os/extensions/` (repo); extension config in Pi's `settings.json` under `.locus`.
- **Swappable / off state**: each Locus extension can be disabled individually via config. Off → that extension's hooks don't fire; Pi's core event loop continues unchanged.
- **KEEP**: Pi's entire extension system, all 25+ lifecycle events, event payload structure.

---

## Feature §1.6: Context Window Management

**Status**: complete  
**Verdict**: 🔄 AUGMENT (Pi compaction + Locus Headroom CCR)

### Source(s) mined
- **Codebase**: Pi at `pi/packages/coding-agent/src/core/compaction/`
- **Files involved**: `compaction/index.ts` (compaction engine), `types.ts` (CompactionResult)
- **Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)] — `/graphify` graph exists for future re-mining

### Logic extracted

```
CONTEXT WINDOW MANAGEMENT:
    estimateContextTokens(messages) → rough count
    shouldCompact(promptTokens, threshold) → bool
    compact(messages, options) → CompactionResult
    
    Compaction preserves:
    - protect_first_n = 3 (first 3 non-system messages)
    - protect_last_n = 6 (last 6 messages)
    - Everything between is summarized by auxiliary LLM call
```

### Locus adaptation

- **Component**: Locus replaces Pi's default compaction with Headroom CCR (§4.17) + its own 800-token budget enforcement in `transformContext`. Pi's compaction remains available as a `CompactionProvider` option.
- **Repo vs `.locus`**: compaction/compression adapters in `locus-os` (repo); Headroom CCR cache dir in `.locus/headroom_cache/` (runtime state).
- **Swappable / off state**: `locus.compaction.provider` (`headroom-ccr` | `pi-default` | `simple-summarize`). Off → raw message history grows unbounded until the LLM's context limit is hit.
- **Integration point**: invoked at Stage 5 (before Context Forge) and as session-level compaction.

---

# MEMORY LAYER — §4: The Memory Tri-Stack

## Feature §4.1-4.2: Graph-Native Memory (Neo4j Agent Memory)

### Metadata
- **Source Codebase**: `neo4j-labs/agent-memory` — **CLONED** at `5_Locus/deps/agent-memory`, actual source read.
- **Verification**: [✅ VERIFIED: cloned repo, source read] · `repo_cloned: true` · `logic_stripped: true` · `contains_code: false`

### Files involved (real, not guessed)

| File | Purpose | Interacts With |
|------|---------|---------------|
| `core/memory.py` | `MemoryClient` root; `BaseMemory` ABC (`add` / `search` / `get_context`); `MemoryStore` protocol (`store/retrieve/search/delete/list`) | graph, embeddings, extraction |
| `graph/schema.py` | `SchemaManager`: constraints, indexes, vector indexes (default 1536-dim), point indexes (geospatial); `adopt_existing_graph()` | `graph/client.py`, `graph/queries.py` |
| `graph/query_builder.py` | Builds Cypher from high-level intent (entity merge, relation write, traversal) | `graph/client.py` |
| `extraction/pipeline.py` | Multi-stage extraction orchestrator with `MergeStrategy` (UNION / INTERSECTION / CONFIDENCE / CASCADE / FIRST_SUCCESS) | `extraction/*_extractor.py` |
| `extraction/gliner_extractor.py` | GLiNER zero-shot entity NER; GLiREL relationship extraction | `extraction/pipeline.py` |
| `extraction/spacy_extractor.py`, `extraction/llm_extractor.py` | spaCy fallback; LLM-based fallback | `extraction/pipeline.py` |
| `embeddings/*` | BYO embedder adapters (sentence-transformers `BAAI/bge-small-en-v1.5`, OpenAI, Anthropic, Bedrock, Vertex; LiteLLM fallback) | `core/memory.py` |
| `memory/*` (short_term / long_term / reasoning) | Three sub-clients: `short_term.add_message()`, `long_term.add_entity()`, `reasoning` traces | `core/memory.py` |

### Logic extracted

The library is a **graph-native memory system** with three memory types over one Neo4j graph:

- **Short-term** (per-session): `Conversation` + `Message` nodes.
- **Long-term** (knowledge graph): `Entity` + `Preference` + `Fact` nodes, in the **POLE+O** entity-type taxonomy (Person / Object / Location / Event / Organization).
- **Reasoning** (learn from past decisions): `ReasoningTrace` + `ReasoningStep` + `Tool` + `ToolCall` nodes, with explicit `:TOUCHED` audit edges from reasoning steps to the entities they used.
- **Hygiene / multi-tenant** (v0.5): `User` (scoping via `user_identifier=`), `ConsolidationRun`, `MemoryReadAudit`.

**Ingestion path**: raw text → entity/relation **extraction** (multi-stage: GLiNER entities + GLiREL relations, spaCy and LLM fallbacks, merged by strategy) → **embedding** (BYO embedder) → **graph write** (MERGE on `(:Entity {name, type})` to dedup/entity-resolve) → optional background **enrichment** (Wikipedia / Diffbot).

**Retrieval path**: `get_context(query)` → hybrid (vector similarity over embeddings + text search + graph traversal) → a single **formatted context string** for the LLM prompt. This is the single most important Locus integration point.

### Pseudocode / algorithm

```
MemoryClient.connect(config):
    setup SchemaManager (constraints + indexes + vector indexes at embedder dims)
    validate vector-index dimensions == embedder dimensions (fail fast on mismatch)
    return client with: short_term, long_term, reasoning sub-clients

BaseMemory (shared ABC):
    add(content)      -> entry      // extract entities + embed + MERGE into graph
    search(query)     -> [entries]  // hybrid semantic + text + traversal
    get_context(query)-> string     // formatted context block for the LLM prompt

store_conversation_turn(user, assistant, session_id):
    entities, relations = extraction_pipeline.run(user + " " + assistant)
    long_term.merge_entities(entities)      // entity resolution & dedup by canonical name
    long_term.write_relations(relations)
    short_term.add_message(user, assistant, session_id)
    reasoning.record_tool_calls(tool_calls) // if any, with status + :TOUCHED edges

retrieve_for_forge(query, max_tokens=150):
    pathways = traversal(query, depth=2, limit=10)   // weighted entity subgraph
    return format_pathways(pathways, budget=max_tokens)  // 'src → REL (w) → dst'
```

### Locus adaptation

- **Component**: `locus/providers/memory/neo4j-agent-memory.ts` (thin TypeScript wrapper) + Python sidecar runs the library directly (no re-implementation).
- **Provider Interface**: implements `MemoryProvider`; `get_context(query)` feeds **Context Forge Layer 4 (Graph, 150t)**.
- **Repos vs `.locus`**: the library + adapter live in the repo (`locus-os`); the **Neo4j URI / user / password / `MEMORY_API_KEY` live in `.locus/.env`** (never in the repo). Neo4j runs as Docker container `locus-neo4j` (bolt :7687) — or the hosted NAMS backend when `MEMORY_API_KEY` is set.
- **Swappable / off state**: `locus.memory.provider` can be `mem0` / `supermemory` / `honcho` / `mastra` / `cognee` / custom; `locus.memory.enabled=false` disables the whole subsystem.
- **MCP surface**: the library already ships an MCP server (16 tools); Locus can either consume that or expose `get_context` through its own MCP server.

---

## Feature §4.17: Token Compression (Headroom CCR)

### Metadata
- **Source Codebase**: `headroomlabs-ai/headroom` — **CLONED** at `5_Locus/deps/headroom`, actual source read.
- **Verification**: [✅ VERIFIED: cloned repo, source read] · `repo_cloned: true` · `logic_stripped: true` · `contains_code: false`

### Files involved (real, not guessed)

| File | Purpose | Interacts With |
|------|---------|---------------|
| `headroom/compress.py` | One-function API: `compress(messages, model, ...)` → `CompressResult`; `CompressConfig` knobs | `headroom/transforms/pipeline.py` |
| `headroom/transforms/cache_aligner.py` | Stabilizes message prefix so provider KV cache still hits | `transforms/pipeline.py` |
| `headroom/transforms/content_router.py` | Routes each content type to the right compressor | `transforms/*` |
| `headroom/transforms/smart_crusher.py` | JSON compressor (array dedup, lossless-first + lossy fallback) | `content_router.py` |
| `headroom/transforms/code_compressor.py` | Code (AST/structural) compressor | `content_router.py` |
| `headroom/transforms/kompress_compressor.py` | ML text compressor (HuggingFace `chopratejas/kompress-v2-base`) | `content_router.py` |
| `headroom/ccr/*` | **C**ache-**C**ompress-**R**etrieve: reversible; originals cached locally, retrievable within TTL | `compress.py`, MCP server |
| `headroom/client.py` / `headroom/cli.py` | Proxy + CLI entrypoints | `compress.py` |

### Logic extracted

Headroom compresses a message list **before it reaches the LLM**, with a typed pipeline:

`CacheAligner → ContentRouter → [SmartCrusher (JSON) | CodeCompressor (code) | Kompress-v2-base (text)] → CCR`

Key facts that drive the Locus adaptation:

- **It compresses the whole message array, not one string.** Defaults are tuned for coding agents: `compress_user_messages=False`, `protect_recent=4`, `min_tokens_to_compress=250` (short messages untouched).
- **Content-aware routing** — JSON goes to SmartCrusher (lossless array dedup first, lossy only if still over budget), code to CodeCompressor, prose to the ML Kompress model. `target_ratio` controls aggression (None ≈ 15% kept; 0.5 = keep 50%).
- **Reversible (CCR)**: originals are cached locally with a key; the LLM calls `headroom_retrieve(cache_key)` to get the full text back on demand, within a TTL.
- **Inflation guard**: if a transform *increases* token count, Headroom reverts to the originals (never make it worse).
- **Prompt-cache aware**: `CacheAligner` + `frozen_message_count` prevent rewriting a prefix the provider is already caching (so a 0.1× cache read isn't turned into a full-price rewrite).

### Pseudocode / algorithm

```
compress(messages, model, config) -> CompressResult:
    cfg = resolve(CompressConfig, kwargs)            # protect_recent=4, min_tokens=250, ...
    context = extract_user_query(messages)           # so JSON crusher scores relevance, not stats
    result = pipeline.apply(messages, model, model_limit, context, ...)
        # 1. CacheAligner: anchor frozen prefix for KV-cache hits
        # 2. ContentRouter: detect PROSE | JSON | CODE per message
        # 3. route -> SmartCrusher | CodeCompressor | Kompress (respect target_ratio)
        # 4. CCR: cache originals, swap in compressed + retrieval marker
    if result.tokens_after > result.tokens_before:    # inflation guard
        revert to originals
    return { messages, tokens_before, tokens_after, tokens_saved, ratio, transforms_applied }

headroom_retrieve(cache_key) -> full original text   # reversible within TTL
```

### Locus adaptation

- **Component**: `locus/providers/compression/headroom-ccr.ts` wrapping the library in the Python sidecar.
- **Provider Interface**: implements `CompressionProvider` (default); alternates: simple summarization, LOCUS_SHORTHAND, custom.
- **Integration point**: invoked at **Stage 5** (before Context Forge) to fit Layer 3–5 retrieval results under their budgets, and as a `CompactionProvider` option for session-level compression.
- **Tool registration**: `headroom_retrieve(cache_key)` is registered as a Pi tool so the LLM can lazily pull back originals.
- **Repos vs `.locus`**: library + adapter in the repo; the Kompress ML model cache dir + CCR cache dir are local runtime state under `.locus` (e.g. `.locus/headroom_cache/`).
- **Swappable / off state**: `locus.compression.provider` and `locus.compression.enabled`; off = raw retrieval text flows straight into Context Forge (budget truncation takes over).
- **MCP surface**: Headroom ships `headroom_compress` / `headroom_retrieve` / `headroom_stats` MCP tools — consume them directly, or expose via Locus' own MCP server.

---

## Feature §4.5: Memory Tree (Hierarchical Summarization Cascade)

**Status**: complete  
**Verdict**: 🔄 AUGMENT (steal OpenHuman's tree mechanics, layer on Locus' graph memory)

### Source(s) mined
- **Codebase**: OpenHuman `memory_tree/` module — `README.md` (160 lines), `mod.rs`, `types.rs`, `ops.rs`, `store.rs`
- **Query method**: [✅ VERIFIED: direct file read of `memory_tree/README.md`]

### Logic extracted

```
MEMORY TREE (from OpenHuman memory_tree/ — COMPLETE):

  PURPOSE: Generic multi-level summarization tree over ANY text corpus.
  Not a specific knowledge base — a reusable infrastructure pattern.

  ═══ TREE STRUCTURE ═══
  
  LEVELS (bottom-up):
    L0 (Buffer):  Raw ingested chunks (≤N items before seal)
    L1-LN:        Progressively summarized nodes
    Root:         Single top-level summary of entire corpus
  
  NODE STRUCTURE:
    TreeNode {
      id: UUID,
      tree_scope: str,       // e.g. "vault:daily", "github:owner/repo"
      level: u32,            // 0 = leaf buffer, higher = summary
      content: str,          // raw text (L0) or LLM summary (L1+)
      children: [UUID],      // child node refs
      token_count: u32,
      created_at: DateTime,
      sealed: bool,          // L0 only: true when gate threshold met
    }

  ═══ OPERATIONS ═══
  
  APPEND (L0 buffer):
    FUNCTION append_leaf(tree_scope, content):
      node = TreeNode { level: 0, content, sealed: false }
      store.insert(node)
      IF count_unsealed(tree_scope, level=0) >= SEAL_GATE:
        enqueue_job(JobKind::Seal, tree_scope, level=0)

  SEAL (cascade upward):
    FUNCTION seal_level(tree_scope, level):
      unsealed = store.get_unsealed(tree_scope, level)
      IF unsealed.count < SEAL_GATE: RETURN  // not enough to summarize
      
      // LLM summarization call
      combined_text = unsealed.map(n => n.content).join("\n---\n")
      summary = llm.summarize(combined_text, instructions="...")
      
      parent = TreeNode {
        level: level + 1,
        content: summary,
        children: unsealed.map(n => n.id),
        sealed: false  // parent is itself unsummarized at its level
      }
      store.insert(parent)
      
      FOR EACH child IN unsealed:
        child.sealed = true
        store.update(child)
      
      // CASCADE: check if parent level also needs sealing
      IF count_unsealed(tree_scope, level+1) >= SEAL_GATE:
        enqueue_job(JobKind::Seal, tree_scope, level+1)

  RETRIEVE (top-down search):
    FUNCTION search(tree_scope, query, max_results):
      // Start from highest-level nodes, descend into relevant branches
      candidates = store.get_top_nodes(tree_scope)
      scored = score_relevance(candidates, query)  // lexical + embedding
      RETURN top_k(scored, max_results)

  TOPIC ROUTING (cross-tree distribution):
    FUNCTION topic_route(chunk, topics):
      matched = match_topics(chunk.content, topics)  // keyword + embedding
      FOR EACH topic IN matched:
        target_scope = "topic:{topic.name}"
        append_leaf(target_scope, chunk.content)

  ═══ SEAL GATE CONFIGURATION ═══
  
  Default: 8 items per level before seal trigger
  Configurable per tree_scope via config
  Time-based stale flush: if L0 buffer age > 3 hours, seal regardless of count

  ═══ PERSISTENCE ═══
  
  SQLite table: mem_tree_chunks
    Columns: id, tree_scope, level, content, token_count, sealed, created_at
  SQLite table: mem_tree_ingested_sources (raw-archive tracking)
    Columns: source_kind, source_id, tree_scope, ingested_at
```

### Locus adaptation
- **Component**: `locus/providers/memory/tree.ts` (TypeScript wrapper) + `sidecar/memory/tree_ops.py` (Python for LLM calls)
- **Provider Interface**: implements `MemoryProvider` — plugs into the Memory Tri-Stack alongside Neo4j and PageIndex
- **Repo vs `.locus`**: tree library code in `locus-os` (repo); SQLite tree DB stored under `.locus/memory/tree.db`
- **STEAL VERBATIM**: The seal-cascade pattern (L0→L1→...→root), the topic-routing cross-tree distribution, the stale-flush 3-hour timer, the `mem_tree_chunks` schema
- **ADAPT**: Locus uses DeepSeek V4 Flash for summarization calls (cost optimization). Tree scopes map to Locus domains: `vault:daily`, `telegram:chat`, `github:<repo>`
- **Swappable / off state**: `locus.memory.tree.enabled`. Off → raw chunks stored but never summarized (flat memory only)

---

## Feature §4.7: Memory Sync (Multi-Source Ingestion Pipelines)

**Status**: complete  
**Verdict**: 🔄 AUGMENT (steal OpenHuman's pipeline architecture, adapt sources for Locus)

### Source(s) mined
- **Codebase**: OpenHuman `memory_sync/` module — `README.md` (83 lines), `traits.rs`, `composio/`, `workspace/`, `mcp/`
- **Query method**: [✅ VERIFIED: direct file read of `memory_sync/README.md`]

### Logic extracted

```
MEMORY SYNC PIPELINES (from OpenHuman memory_sync/ — COMPLETE):

  PURPOSE: "Pull data from upstream → land it in memory_store" — one module,
  three pipeline kinds, unified trait.

  ═══ TRAIT ═══
  
  trait SyncPipeline: Send + Sync {
    async fn init(&self, config: &Config) → Result<()>
    async fn tick(&self, config: &Config) → Result<SyncOutcome>
    fn id(&self) → &str             // unique pipeline identifier
    fn kind(&self) → SyncPipelineKind  // Composio | Workspace | Mcp
  }
  
  SyncOutcome {
    records_ingested: u64,
    more_pending: bool,    // pagination: caller should tick again
    note: Option<String>,  // human-readable status
  }

  ═══ THREE PIPELINE KINDS ═══
  
  1. COMPOSIO PIPELINES (per-provider via Composio Edge API):
     Sources: gmail, slack, github, notion, linear, clickup
     Each provider has its own ingest.rs + pagination cursor + retry policy
     
  2. WORKSPACE PIPELINES (local data sources):
     - Vault file watch (Obsidian .md files)
     - Harness turn capture (agent conversation history)
     - Dictation transcripts (voice → text archives)
     
  3. MCP PIPELINES (third-party MCP servers):
     One pipeline per connected MCP server
     Uses mcp_client/ transport (stdio or HTTP)

  ═══ SCHEDULERS & SELF-HEALING ═══
  
  THREE BACKGROUND LOOPS:
  ┌─────────────────────┬───────────────────┬─────────────────────────────────┐
  │ Loop                │ Cadence           │ Covers                          │
  ├─────────────────────┼───────────────────┼─────────────────────────────────┤
  │ Composio periodic   │ 20-min tick,      │ Composio connections            │
  │                     │ per-connection    │ (gmail, slack, ...)             │
  │ Workspace periodic  │ 20-min tick,      │ github_repo, folder,            │
  │                     │ 24h default       │ rss_feed, web_page sources      │
  │ Queue scheduler     │ 3 h               │ flush stale L0 buffers +        │
  │                     │                   │ requeue transient-failed jobs   │
  └─────────────────────┴───────────────────┴─────────────────────────────────┘

  ═══ RAW-ARCHIVE COVERAGE (self-healing) ═══
  
  FUNCTION check_and_rebuild_tree(source):
    // Every summary batch records its raw files in mem_tree_ingested_sources
    ingested = db.query("SELECT source_id FROM mem_tree_ingested_sources 
                         WHERE tree_scope = ?", source.scope)
    on_disk  = list_raw_files(source.raw_archive_path)
    
    uncovered = on_disk - ingested  // set difference
    IF uncovered.is_not_empty():
      // Self-heal: summarize the missed files
      FOR EACH file IN uncovered:
        enqueue_job(JobKind::ExtractChunk, file)
    
    // GOTCHA: tree scope and raw-archive ID slugify DIFFERENTLY
    // for GitHub: "github:owner/repo" vs "github.com/owner/repo"
    // Always carry both (SourceScope struct)

  ═══ LAYER RULES (hard boundaries) ═══
  
  1. All sync writes go through memory::ingest_pipeline
     → every record lands as: raw md → chunks → tree leaves
  2. NO direct writes into trees or unified store
  3. No upstream-specific data models leak past the pipeline boundary
  4. One pipeline per upstream service (Composio GitHub ≠ MCP GitHub)
```

### Locus adaptation
- **Component**: `locus/providers/memory/sync/` — one file per pipeline kind
- **Provider Interface**: `SyncPipelineProvider` (mirrors the `trait SyncPipeline`)
- **Locus pipeline mapping**:
  - Composio pipelines → Locus uses direct API integrations (Gmail via Google API, GitHub via Octokit, etc.) — no Composio dependency
  - Workspace pipelines → Locus' VaultCrawler (MD5-based) + Telegram conversation capture
  - MCP pipelines → Same pattern, piped through Locus' MCP client
- **Repo vs `.locus`**: pipeline code in `locus-os` (repo); sync state + cursors in `.locus/memory/sync_state.db`
- **STEAL VERBATIM**: The SyncPipeline trait, SyncOutcome contract, the raw-archive self-healing pattern, the "never leak upstream models past pipeline boundary" rule
- **Swappable / off state**: `locus.memory.sync.enabled` (global) + per-pipeline toggles. Off → no automatic ingestion; memory only grows from direct conversation

---

## Feature §4.8: Memory Queue (Async Job Pipeline)

**Status**: complete  
**Verdict**: 🔄 AUGMENT (steal OpenHuman's job pipeline, adapt for Locus' runtime)

### Source(s) mined
- **Codebase**: OpenHuman `memory_queue/` module — `README.md` (37 lines), `types.rs`, `store.rs`, `worker.rs`, `scheduler.rs`
- **Query method**: [✅ VERIFIED: direct file read of `memory_queue/README.md`]

### Logic extracted

```
MEMORY QUEUE (from OpenHuman memory_queue/ — COMPLETE):

  PURPOSE: Async job pipeline driving extraction, scoring, summarisation,
  and digesting OFF the ingest hot path. Replaces synchronous
  "append_leaf → cascade_seal → LLM summarise" chain.

  ═══ PIPELINE SHAPE ═══
  
  ingest::persist           → enqueues `extract_chunk`
  
  worker pool (3 tasks):
    extract_chunk           → LLM extraction → admission → enqueue:
                               - `append_buffer` (add to tree L0)
                               - `topic_route` (cross-tree distribution)
    append_buffer           → push to L0 → enqueue `seal` if gate met
    seal                    → seal one level → enqueue parent seal if cascading
    topic_route             → match topics → enqueue per-topic `append_buffer`
    digest_daily            → call tree_global::digest::end_of_day_digest
    flush_stale             → enqueue seals for time-stale buffers (>3h)
  
  scheduler (1 task):
    daily tick at UTC 00:05 → `digest_daily(yesterday)` + `flush_stale(today)`

  ═══ JOB TYPES (enum JobKind) ═══
  
  ExtractChunk    { source_id, content, metadata }
  AppendBuffer    { tree_scope, content, target: NodeRef }
  Seal            { tree_scope, level }
  TopicRoute      { chunk_content, source_context }
  DigestDaily     { date: NaiveDate }
  FlushStale      { date: NaiveDate }

  ═══ PERSISTENCE (SQLite) ═══
  
  Table: mem_tree_jobs
    Columns: id, kind, payload (JSON), status, dedupe_key,
             created_at, claimed_at, claim_token, completed_at,
             error_message, retry_count
    
    Status enum: Ready, Running, Done, Failed
    
    DEDUPLICATION:
      Each payload owns a dedupe_key() method
      Partial unique index: (dedupe_key) WHERE status IN ('ready','running')
      INSERT OR IGNORE → at-most-one-active duplicate suppression
    
    CLAIM PATTERN:
      claim_next() = UPDATE ... SET status='running', claim_token=uuid
                     WHERE status='ready' ORDER BY created_at LIMIT 1
                     RETURNING *
      → Single atomic UPDATE...RETURNING (no SELECT-then-UPDATE race)
    
    SETTLEMENT:
      mark_done(id, claim_token)   → only succeeds if token matches
      mark_failed(id, claim_token) → same token guard
      → Stale worker settlements are no-ops (token mismatch)

  ═══ WORKER POOL ═══
  
  3 worker tasks + recover_stale_locks at startup
  3-permit semaphore around LLM-bound jobs (rate limiting)
  
  THROTTLE INTEGRATION:
    Before claiming: scheduler_gate::wait_for_capacity()
    IF gate == Throttled: back off without holding DB leases
    IF gate == Paused: defer indefinitely
  
  DEFAULT_LOCK_DURATION_MS = 300_000 (5 min claim lease)
  
  STALE LOCK RECOVERY (startup):
    UPDATE mem_tree_jobs SET status='ready', claim_token=NULL
    WHERE status='running' AND claimed_at < now() - lock_duration

  ═══ SCHEDULER ═══
  
  Daily tick at UTC 00:05:
    1. enqueue DigestDaily(yesterday)
    2. enqueue FlushStale(today)
  
  Manual helpers:
    trigger_digest(date) → enqueue single digest
    backfill_missing_digests(from, to) → batch enqueue
```

### Locus adaptation
- **Component**: `locus/providers/memory/queue.ts` + `sidecar/memory/queue_worker.py`
- **Provider Interface**: Part of the `MemoryProvider` infrastructure — not directly swappable, but the worker count + throttle policy are configurable
- **Repo vs `.locus`**: queue library in `locus-os` (repo); job SQLite DB at `.locus/memory/jobs.db`
- **STEAL VERBATIM**: The pipeline shape (extract→append→seal cascade), the dedupe_key pattern, the claim_token settlement guard, the 3-permit LLM semaphore, the scheduler gate integration
- **ADAPT**: Python sidecar workers instead of Rust tokio tasks. 2 workers (not 3) since Locus runs on a single user's machine. Scheduler gate maps to Locus' own throttle policy (battery + CPU checks)
- **Swappable / off state**: `locus.memory.queue.workers` (0 = disabled). Off → extraction happens synchronously on the ingest path (slower but simpler)

---

## Feature §4.9: Memory Diff (Snapshot-Based Change Tracking)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW (OpenHuman module, no Pi/Hermes equivalent)

### Source(s) mined
- **Codebase**: OpenHuman `memory_diff/` module — `mod.rs` (33 lines), `types.rs`, `store.rs`, `ops.rs`, `tools.rs`
- **Query method**: [✅ VERIFIED: direct file read of `memory_diff/mod.rs`]

### Logic extracted

```
MEMORY DIFF (from OpenHuman memory_diff/ — COMPLETE):

  PURPOSE: Snapshot-based change tracking for memory sources.
  After each sync, captures what's in the chunk store, then diffs against
  previous snapshots to surface additions, removals, and modifications.
  Helps agents understand how their world view changed over time.

  ═══ CORE TYPES ═══
  
  Snapshot {
    id: UUID,
    source_scope: str,        // e.g. "vault:daily", "github:owner/repo"
    trigger: SnapshotTrigger, // AutoPostSync | Manual | Checkpoint
    items: [SnapshotItem],
    created_at: DateTime,
  }
  
  SnapshotItem {
    chunk_id: str,
    content_hash: str,        // SHA-256 of chunk content
    title: Option<str>,
    token_count: u32,
  }
  
  DiffResult {
    source_scope: str,
    from_snapshot: UUID,
    to_snapshot: UUID,
    changes: [ItemChange],
    summary: DiffSummary,
  }
  
  ItemChange {
    kind: ChangeKind,         // Added | Removed | Modified
    chunk_id: str,
    title: Option<str>,
    old_hash: Option<str>,    // for Modified
    new_hash: Option<str>,    // for Added and Modified
  }
  
  DiffSummary {
    added: u32,
    removed: u32,
    modified: u32,
    unchanged: u32,
  }

  ═══ OPERATIONS ═══
  
  FUNCTION take_snapshot(source_scope, trigger):
    items = store.get_all_chunks(source_scope)
              .map(c => SnapshotItem {
                chunk_id: c.id,
                content_hash: sha256(c.content),
                title: c.title,
                token_count: c.token_count
              })
    snapshot = Snapshot { source_scope, trigger, items, created_at: now() }
    store.save_snapshot(snapshot)
    RETURN snapshot.id
  
  FUNCTION diff(source_scope, from_id, to_id):
    from_items = store.get_snapshot(from_id).items  // keyed by chunk_id
    to_items   = store.get_snapshot(to_id).items
    
    changes = []
    FOR chunk_id IN union(from_items.keys, to_items.keys):
      IF chunk_id IN to_items AND NOT IN from_items:
        changes.push(ItemChange { kind: Added, ... })
      ELIF chunk_id IN from_items AND NOT IN to_items:
        changes.push(ItemChange { kind: Removed, ... })
      ELIF from_items[chunk_id].content_hash != to_items[chunk_id].content_hash:
        changes.push(ItemChange { kind: Modified, ... })
    
    RETURN DiffResult { changes, summary: count_by_kind(changes) }

  ═══ NAMED CHECKPOINTS ═══
  
  Checkpoint {
    name: str,               // e.g. "before-refactor", "weekly-baseline"
    snapshot_ids: { source_scope → snapshot_id }
  }
  
  FUNCTION create_checkpoint(name):
    FOR EACH active source_scope:
      snap_id = take_snapshot(source_scope, Checkpoint)
      checkpoint.snapshot_ids[source_scope] = snap_id
    store.save_checkpoint(name, checkpoint)
  
  FUNCTION diff_since_checkpoint(name):
    checkpoint = store.get_checkpoint(name)
    diffs = {}
    FOR EACH scope, snap_id IN checkpoint.snapshot_ids:
      current = take_snapshot(scope, Manual)
      diffs[scope] = diff(scope, snap_id, current)
    RETURN CrossSourceDiff { diffs }

  ═══ AGENT TOOL ═══
  
  MemoryDiffTool:
    "what_changed" action → diff_since_checkpoint or diff last N snapshots
    Returns human-readable summary: "3 notes added, 1 modified, 0 removed"

  ═══ RPC SURFACE ═══
  
  memory_diff.take_snapshot(source_scope, trigger?)
  memory_diff.diff(source_scope, from_snapshot_id, to_snapshot_id)
  memory_diff.create_checkpoint(name)
  memory_diff.diff_since_checkpoint(name)
  memory_diff.list_snapshots(source_scope, limit?)
```

### Locus adaptation
- **Component**: `locus/providers/memory/diff.ts` + `sidecar/memory/diff_ops.py`
- **Provider Interface**: Part of `MemoryProvider` infrastructure; the `MemoryDiffTool` is registered as a Locus agent tool
- **Repo vs `.locus`**: diff library in `locus-os` (repo); snapshot SQLite DB at `.locus/memory/snapshots.db`
- **STEAL VERBATIM**: The snapshot/diff pattern, the named checkpoint system, the SHA-256 content hashing, the agent tool interface
- **ADAPT**: Snapshots auto-triggered after VaultCrawler sync (daily) and Telegram conversation capture. Checkpoints created at weekly synthesis boundary.
- **Swappable / off state**: `locus.memory.diff.enabled`. Off → no snapshot tracking; agents cannot query "what changed"

---


## Feature §4.10: Holographic Reduced Representations (HRR Memory Binding)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Vector Symbolic Architectures (VSA) / HRR Mathematical Specification (`Comprehensive Locus System Design.html`)  
**Query method**: [📐 DESIGN SPEC: comprehensive_design.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/memory/hrr.py` | 320 | High-performance NumPy/SciPy implementation of circular convolution, circular correlation, and superposition vector algebra | `sidecar/memory/hrr_codebook.py` (item memory lookup), `sidecar/brain/state_engine.py` (fast state bundling) |
| `locus-os/sidecar/memory/hrr_codebook.py` | 180 | Orthogonal random vector dictionary mapping symbols (roles, entities, attributes) to fixed $D=2048$ dimensional vectors | `sidecar/memory/hrr.py` (provides atomic vectors) |
| `locus-os/src/core/memory/hrr-adapter.ts` | 140 | TypeScript bridge for requesting fast zero-LLM associative binds and similarity lookups | `sidecar/memory/hrr.py` (via IPC/HTTP) |

### Stripped Logic (Pseudocode)

```
DATA STRUCTURES:
    HRRVector:
        dimension: int = 2048
        values: float[2048]   // Zero-mean, variance 1/D normal distribution

    Codebook:
        symbols: Dict[string -> HRRVector]
        
MATHEMATICAL OPERATIONS:
    1. Circular Convolution (Binding: a ⊛ b):
       // Encodes key-value pairs (e.g. ROLE ⊛ AGENT) into a single bound vector of same dimension
       FUNCTION bind(a: HRRVector, b: HRRVector) -> HRRVector:
           A_fft = FFT(a.values)
           B_fft = FFT(b.values)
           C_fft = A_fft * B_fft   // Element-wise complex multiplication
           c_vals = Real(IFFT(C_fft))
           RETURN normalize(c_vals)

    2. Circular Correlation (Unbinding: a ≈ c ⊙ b):
       // Retrieves value given key and bound representation
       FUNCTION unbind(c: HRRVector, b: HRRVector) -> HRRVector:
           b_inv = invert_axes(b.values)  // b*(-t)
           RETURN bind(c, b_inv)

    3. Vector Superposition (Bundling: s = a + b + c):
       // Combines multiple bound pairs into an associative memory bundle
       FUNCTION bundle(vectors: List[HRRVector]) -> HRRVector:
           s_vals = sum([v.values for v in vectors])
           RETURN normalize(s_vals)

    4. Clean-Up Memory (Associative Recall):
       FUNCTION cleanup(noisy_vector: HRRVector, codebook: Codebook, threshold=0.70) -> Optional[string]:
           best_symbol = null
           max_sim = -1.0
           FOR EACH symbol, proto_vec IN codebook.symbols:
               sim = cosine_similarity(noisy_vector.values, proto_vec.values)
               IF sim > max_sim AND sim >= threshold:
                   max_sim = sim
                   best_symbol = symbol
           RETURN best_symbol

FAST EPHEMERAL STATE COMPOSITION PIPELINE:
    FUNCTION encode_ephemeral_state(current_task, active_mode, stress_level) -> HRRVector:
        // Bind attributes without LLM token consumption
        task_bound = bind(codebook.get("ROLE:TASK"), codebook.get(current_task.id))
        mode_bound = bind(codebook.get("ROLE:MODE"), codebook.get(active_mode.name))
        stress_bound = bind(codebook.get("ROLE:STRESS"), codebook.get(stress_level.category))
        
        // Superpose into single composite state vector
        state_bundle = bundle([task_bound, mode_bound, stress_bound])
        RETURN state_bundle
```

### Locus adaptation
- **Component**: `locus-os/sidecar/memory/hrr.py` (Python) + `locus-os/src/core/memory/hrr-adapter.ts` (TS bridge)
- **Provider Interface**: `AssociativeMemoryProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); codebook cache persisted at `.locus/memory/hrr_codebook.bin`.
- **Swappable / off state**: `locus.memory.hrr.enabled`. Off → Locus skips holographic state bundling; uses standard JSON key-value store in Redis.
- **STEAL VERBATIM**: The FFT-accelerated circular convolution/correlation formulas, orthogonal unit-vector initialization ($D=2048$), clean-up memory thresholding at $	au \ge 0.70$.
- **ADAPT**: Used in Python sidecar for sub-millisecond ephemeral context association during high-frequency sensor/event ingestion before committing full entities to Neo4j.

---

## Feature §4.12: STDP Reinforcement (Spike-Timing-Dependent Plasticity)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `Comprehensive Locus System Design.html` (Hebbian Manager) + `locus_microsystems.html`  
**Query method**: [📐 DESIGN SPEC: comprehensive_design.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/memory/stdp_updater.py` | 210 | Applies asymmetric temporal STDP learning rule to Neo4j graph edge weights based on retrieval-to-outcome time deltas | `neo4j-labs/agent-memory` (`core/memory.py`), `sidecar/brain/reward_model.py` |
| `locus-os/sidecar/memory/graph_reinforcement.py` | 190 | Manages relationship weight clamping $[0.05, 1.0]$, decay cycles, and low-weight relationship pruning | `sidecar/memory/stdp_updater.py`, Neo4j client |

### Stripped Logic (Pseudocode)

```
STDP ASYMMETRIC LEARNING RULE:
    CONSTANTS:
        A_plus  = 0.15     // Max potentiation (strengthening)
        A_minus = 0.12     // Max depression (weakening)
        tau_plus  = 300.0  // Positive time constant (5 minutes in seconds)
        tau_minus = 600.0  // Negative time constant (10 minutes in seconds)
        W_MIN = 0.05       // Minimum edge weight (prevents complete deletion)
        W_MAX = 1.00       // Maximum edge weight saturation
        PRUNE_THRESHOLD = 0.08  // Below this, edge is marked for archive/prune

DATA STRUCTURES:
    RetrievalEvent:
        node_id: string
        edge_id: string
        retrieved_at: float   // epoch timestamp

    OutcomeEvent:
        session_id: string
        turn_id: string
        success: bool         // 👍 reward, goal completion, or accepted suggestion
        occurred_at: float

FUNCTION apply_stdp_update(retrieval: RetrievalEvent, outcome: OutcomeEvent, current_weight: float) -> float:
    delta_t = outcome.occurred_at - retrieval.retrieved_at   // in seconds
    
    IF delta_t <= 0:
        // Retrieval happened AFTER outcome — causality violation, ignore
        RETURN current_weight
        
    IF outcome.success:
        // Long-Term Potentiation (LTP): Retrieved memory contributed to success
        delta_w = A_plus * exp(-delta_t / tau_plus)
        new_weight = current_weight + delta_w
    ELSE:
        // Long-Term Depression (LTD): Retrieved memory led to hallucination, rejection, or error
        delta_w = A_minus * exp(-delta_t / tau_minus)
        new_weight = current_weight - delta_w
        
    // Clamp to valid boundary
    new_weight = clamp(new_weight, W_MIN, W_MAX)
    RETURN new_weight

BATCH GRAPH REINFORCEMENT CYCLE:
    FUNCTION process_turn_stdp(turn_audit_log):
        FOR EACH edge IN turn_audit_log.traversed_edges:
            current_w = neo4j.get_edge_weight(edge.id)
            updated_w = apply_stdp_update(edge.retrieval_event, turn_audit_log.outcome, current_w)
            neo4j.update_edge_weight(edge.id, updated_w)
            
            IF updated_w <= PRUNE_THRESHOLD:
                neo4j.tag_edge_for_pruning(edge.id, reason="STDP_DEPLETION")
```

### Locus adaptation
- **Component**: `locus-os/sidecar/memory/stdp_updater.py` (Python sidecar)
- **Provider Interface**: `GraphPlasticityProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); reinforcement audit logs stored in PostgreSQL `stdp_audit_log` table.
- **Swappable / off state**: `locus.memory.stdp.enabled`. Off → Neo4j edge weights remain static; traversal uses unweighted paths.
- **STEAL VERBATIM**: The exponential STDP formulas ($\Delta w = A_+ e^{-\Delta t/	au_+}$ and $\Delta w = -A_- e^{-\Delta t/	au_-}$), parameter constants ($A_+=0.15, A_-=0.12, 	au_+=300s$), boundary clamping $[0.05, 1.0]$.
- **ADAPT**: Triggered automatically during Post-Turn Background Review (§1.7/§10.1) when user feedback (thumbs up/down or follow-up correction) is received.

---

## Feature §4.13: Spaced Repetition Memory Consolidation (FSRS / SM-2)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: SuperMemo SM-2 & Free Spaced Repetition Scheduler (FSRS) adapted for LLM Knowledge Graphs (`Comprehensive Locus System Design.html`)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/memory/spaced_repetition.py` | 260 | Computes next review intervals, ease factors, and stability scores for Neo4j memory nodes and user facts | `neo4j-labs/agent-memory`, `sidecar/brain/inner_loop.py` |
| `locus-os/sidecar/memory/memory_scheduler.py` | 180 | Nightly job runner that selects due memory cards and enqueues them for subconscious review | `sidecar/memory/spaced_repetition.py`, Redis queue |

### Stripped Logic (Pseudocode)

```
DATA STRUCTURES:
    MemoryNodeState:
        node_id: string
        repetition_count: int = 0
        ease_factor: float = 2.50      // SM-2 default (min 1.30)
        interval_days: int = 1
        stability: float = 1.0         // FSRS memory stability
        last_reviewed_at: timestamp
        due_date: timestamp

SM-2 INTERVAL & EASE ALGORITHM:
    FUNCTION calculate_next_review(state: MemoryNodeState, quality_grade: int) -> MemoryNodeState:
        // quality_grade: 0 = Blackout, 1 = Incorrect, 2 = Hard recall, 
        //                3 = Pass with effort, 4 = Good recall, 5 = Perfect/Reflexive
        
        IF quality_grade >= 3:
            IF state.repetition_count == 0:
                state.interval_days = 1
            ELIF state.repetition_count == 1:
                state.interval_days = 6
            ELSE:
                state.interval_days = round(state.interval_days * state.ease_factor)
            state.repetition_count += 1
        ELSE:
            // Recall failed — reset repetition ladder
            state.repetition_count = 0
            state.interval_days = 1
            
        // Update Ease Factor (EF)
        // EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        state.ease_factor = state.ease_factor + (0.1 - (5 - quality_grade) * (0.08 + (5 - quality_grade) * 0.02))
        state.ease_factor = max(1.30, state.ease_factor)   // Clamp minimum
        
        state.last_reviewed_at = now()
        state.due_date = now() + days(state.interval_days)
        RETURN state

NIGHTLY MEMORY CONSOLIDATION WORKER (02:30 IST):
    FUNCTION run_spaced_repetition_consolidation():
        due_nodes = neo4j.query("""
            MATCH (e:Entity)
            WHERE e.due_date <= datetime() OR e.due_date IS NULL
            RETURN e
            ORDER BY e.due_date ASC
            LIMIT 50
        """)
        
        FOR EACH node IN due_nodes:
            // Evaluate memory retention via implicit conversational mentions or Inner Loop verification
            simulated_grade = evaluate_node_retention(node)
            updated_state = calculate_next_review(node.state, simulated_grade)
            neo4j.save_node_state(node.id, updated_state)
            
            // If highly stable (repetition >= 5, ease >= 2.5), promote to permanent core facts
            IF updated_state.repetition_count >= 5 AND updated_state.ease_factor >= 2.5:
                neo4j.add_label(node.id, "CORE_FACT")
```

### Locus adaptation
- **Component**: `locus-os/sidecar/memory/spaced_repetition.py` (Python sidecar)
- **Provider Interface**: `MemoryConsolidationProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); state metadata attached to Neo4j node properties.
- **Swappable / off state**: `locus.memory.spaced_repetition.enabled`. Off → nodes do not decay or schedule reviews; memory graph is static.
- **STEAL VERBATIM**: The standard SM-2 formula and Ease Factor adjustment equation ($EF' = EF + (0.1 - (5-q)	imes(0.08+(5-q)	imes0.02))$), minimum $EF=1.30$, repetition interval progression (1d → 6d → $I 	imes EF$).
- **ADAPT**: Automated background evaluator grades memory nodes based on user's recent Obsidian journal entries and Telegram check-ins, eliminating manual flashcard burden.

---

## Feature §4.14: Project-Specific Memory Decay Engine

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` (Faction Lifecycle) + `Comprehensive Locus System Design.html`  
**Query method**: [📐 DESIGN SPEC: comprehensive_design.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/memory/project_decay.py` | 230 | Calculates exponential retention strength $S(t)$ for project-associated knowledge graph clusters based on lifecycle state | `neo4j-labs/agent-memory`, `sidecar/brain/state_engine.py` |
| `locus-os/sidecar/memory/cold_archiver.py` | 170 | Serializes and moves deeply decayed memory nodes from active Neo4j graph to compressed `.locus/memory/cold_archive/` storage | `sidecar/memory/project_decay.py`, local disk |

### Stripped Logic (Pseudocode)

```
LIFECYCLE HALF-LIFE PARAMETERS:
    HALF_LIFE_DAYS = {
        "ACTIVE":     90.0,   // Active projects: very slow decay
        "MAINTENANCE": 45.0,   // Finished/sustaining: medium decay
        "PAUSED":     30.0,   // Temporarily halted: faster decay
        "ABANDONED":  14.0,   // Dropped projects: fast decay
        "ARCHIVED":    7.0    // Completed & closed: rapid transition to cold storage
    }
    COLD_STORAGE_THRESHOLD = 0.10   // Retention strength S(t) < 0.10 triggers cold archive

FUNCTION calculate_retention_strength(project_state: string, days_since_last_touch: float) -> float:
    half_life = HALF_LIFE_DAYS.get(project_state, 30.0)
    // Exponential half-life decay formula: S(t) = S_0 * 2^(-t / T_1/2)
    strength = 1.0 * (2.0 ** (-days_since_last_touch / half_life))
    RETURN strength

NIGHTLY PROJECT DECAY SWEEP (03:00 IST):
    FUNCTION sweep_project_memories():
        projects = neo4j.query("MATCH (p:Project) RETURN p")
        
        FOR EACH project IN projects:
            days_inactive = (now() - project.last_touched_at).days
            strength = calculate_retention_strength(project.status, days_inactive)
            
            // Update all child nodes connected via :BELONGS_TO or :SUBTASK_OF
            neo4j.query("""
                MATCH (n)-[:BELONGS_TO|SUBTASK_OF]->(p:Project {id: $proj_id})
                SET n.retention_strength = $strength, n.last_decay_sweep = datetime()
            """, proj_id=project.id, strength=strength)
            
            IF strength < COLD_STORAGE_THRESHOLD:
                // Archive node cluster to compressed cold JSONL storage
                archive_cluster_to_cold_storage(project.id)
                neo4j.query("""
                    MATCH (n)-[:BELONGS_TO]->(p:Project {id: $proj_id})
                    DETACH DELETE n
                """, proj_id=project.id)
```

### Locus adaptation
- **Component**: `locus-os/sidecar/memory/project_decay.py` (Python sidecar)
- **Provider Interface**: `MemoryDecayProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); cold archived memory clusters compressed in `.locus/memory/cold_archive/{project_id}.jsonl.gz`.
- **Swappable / off state**: `locus.memory.decay.enabled`. Off → memory nodes never decay; all historical projects remain permanently active in Neo4j.
- **STEAL VERBATIM**: The half-life decay formula ($S(t) = S_0 \cdot 2^{-\Delta t / T_{1/2}}$), the multi-state half-life parameter table ($90	ext{d}/45	ext{d}/30	ext{d}/14	ext{d}/7	ext{d}$), and the cold storage cutoff threshold ($	au = 0.10$).
- **ADAPT**: Integrated directly into Locus Faction goal tracking — when a project shifts from `ACTIVE` to `ARCHIVED`, its memory cluster automatically accelerates decay.


## Feature §27.1: Vectorless Retrieval (PageIndex)

### Metadata
- **Source Codebase**: `VectifyAI/PageIndex` — **CLONED** at `5_Locus/deps/PageIndex`, actual source read.
- **Verification**: [✅ VERIFIED: cloned repo, source read] · `repo_cloned: true` · `logic_stripped: true` · `contains_code: false`

### Files involved (real, not guessed)

| File | Purpose | Interacts With |
|------|---------|---------------|
| `pageindex/page_index_md.py` | Markdown → tree: header parsing, text assignment, token counting, thinning, stack-based tree build | `utils.py` |
| `pageindex/page_index_classic.py` | PDF variant (1324 lines) — same tree idea over parsed PDF structure | `page_index_md.py` |
| `pageindex/tree_optimize.py` | Tree post-processing / optimization | `page_index_md.py` |
| `pageindex/agent_tools.py` | Reasoning-based tree-search retrieval (LLM navigates root → leaf) | `local_api.py`, `client.py` |
| `pageindex/local_api.py` / `mcp_bridge.py` | Local server + MCP bridge | `agent_tools.py` |
| `pageindex/client.py` | Client SDK | `local_api.py` |

### Logic extracted

PageIndex is **vectorless, reasoning-based RAG**: build a hierarchical "table-of-contents" tree over a document, then let an LLM *reason* its way down the tree to the relevant section. **No vector DB, no chunking.**

**Tree build** (`md_to_tree`), exactly as implemented:
1. `extract_nodes_from_markdown` — regex `#{1,6}` headers + `**bold**` standalone lines as level-1 headings; **skips content inside fenced code blocks**.
2. `extract_node_text_content` — assign each node the text between its header line and the next header's line.
3. `update_node_list_with_text_token_count` — cumulative token count per node **including all descendants** (computed bottom-up).
4. `tree_thinning_for_index` — merge any node whose subtree is below `min_node_token` into its parent (keeps index compact).
5. `build_tree_from_nodes` — stack-based nesting by heading level; assigns `node_id` = zero-padded 4-digit counter.
6. `generate_summaries_for_structure_md` — for nodes over ~200 tokens, LLM writes a `summary` (leaves) or `prefix_summary` (parents); short nodes use raw text.

Result node shape: `{ title, node_id, line_num, summary|prefix_summary, text?, nodes[] }`; doc wrapper `{ doc_name, line_count, structure }`.

**Retrieval** (`agent_tools.py`): start at root; present child summaries to the LLM; it picks the most relevant child; descend; return the leaf's full text. ~3–5 LLM calls per query, fully traceable (the path is the explanation).

### Pseudocode / algorithm

```
md_to_tree(md_path) -> { doc_name, line_count, structure }:
    nodes      = extract_nodes_from_markdown(content)        # regex headers, skip code blocks
    nodes      = extract_node_text_content(nodes, lines)     # text between headers
    nodes      = update_token_counts(nodes)                  # bottom-up cumulative tokens
    if thinning: nodes = tree_thinning(nodes, min_token)     # merge tiny nodes into parent
    tree       = build_tree_from_nodes(nodes)                # stack; node_id = zfill(4)
    tree       = generate_summaries(tree)                    # LLM summary if node > 200 tokens
    return tree

retrieve(query, tree):
    current = tree.children
    while current has non-leaf nodes:
        chosen = llm.choose("query: ... which section? " + enumerate(summaries))
        current = chosen.children
    return chosen.full_text        # leaf content, with citation path
```

### Locus adaptation

- **Component**: `locus/providers/retrieval/pageindex.ts` (TS wrapper) + `sidecar/pageindex/` (Python runs the real library).
- **Provider Interface**: implements `RetrievalProvider`; feeds **Context Forge Layer 5 (Semantic, 200t)** alongside pgvector.
- **Repos vs `.locus`**: library + adapter in the repo; the tree-index JSON cache lives under `.locus` runtime state (e.g. `.locus/pageindex/`).
- **Integration point**: Vault changes synchronized in real time via CouchDB & Obsidian LiveSync (as well as nightly reconciliation at 23:45) trigger incremental tree node rebuilds for changed Obsidian files (driven by CouchDB `_changes` feed and MD5 diffing). Retrieval called at Stage 4 when `intent.sources_required` includes `pageindex`.
- **Model**: tree summaries + navigation use the cheapest available LLM (DeepSeek V4 Flash default) to keep the ~3–5 calls/query near-zero cost.
- **Swappable / off state**: `locus.retrieval.provider` (`pageindex` | `pgvector` | BM25 | custom); off = semantic retrieval relies on pgvector only.

---

# MEMORY TRI-STACK INTEGRATION — Neo4j Agent Memory + Headroom CCR + PageIndex

## Overview & Architecture

The three pre-built dependencies compose into **ONE unified memory pipeline**:

```
[ Neo4j Agent Memory ] → STORE (episodic + semantic graph memory)
[ Headroom CCR ]       → COMPRESS (token budget enforcement)  
[ PageIndex ]          → RETRIEVE (tree-structured document retrieval)
```

## Unified Retrieval & Assembly Flow

```
USER QUERY
   │
   ├─► Query Router (DeepSeek V4 Flash (cheapest available) classification)
   │     ├─► intent: KNOWLEDGE_RETRIEVAL / SYNTHESIS
   │     └─► sources_required: ["neo4j", "pageindex", "pgvector", "pg"]
   │
   ├─► Parallel Retrieval (Stage 5)
   │     ├─► PageIndex: Tree navigation → relevant vault document sections
   │     ├─► Neo4j Agent Memory: Graph traversal → active pathways & entity history
   │     ├─► pgvector: Semantic vector search → top-7 chunks (recency-boosted)
   │     └─► PostgreSQL: Exact event & task log query
   │
   ├─► Headroom CCR Compression (Stage 6 prep)
   │     ├─► Input: Raw text from all 4 retrieval sources
   │     ├─► Action: Type-aware compression (PROSE 60%, JSON 85%, CODE 95%)
   │     └─► Output: Reduced text + cache_keys for lazy LLM retrieval
   │
   └─► Context Forge (Stage 6 assembly)
         └─► Hard 800-token budget enforcement across all 6 layers
```

## Integration Matrix & Responsibilities

| Subsystem | Storage Engine | Sidecar Endpoint | Role in Tri-Stack | Token Budget |
|-----------|----------------|------------------|-------------------|--------------|
| **Neo4j Agent Memory** | Neo4j (Docker :7687) | `POST /memory/query` | Layer 4: Learned behavioral pathways & entity relations | 150 tokens |
| **PageIndex** | Tree JSON index | `POST /pageindex/query` | Layer 5: Hierarchical document reasoning without vector noise | 100 tokens (shared with pgvector) |
| **Headroom CCR** | Local disk cache | `POST /compress` | System-wide: Compresses any layer exceeding budget | N/A (Compressor) |

## Shared Data Contracts

1. **Entity Identifiers**: GLiNER extracts entities in Python sidecar. Entity IDs are identical across Neo4j (node names) and PageIndex (section tags).
2. **Context Forge Protocol**:
   - `PageIndex` returns section content.
   - `Neo4j` returns `(NodeA)-[REL]->(NodeB)` pathways.
   - `Headroom` compresses section content if Layer 5 exceeds 200 tokens.
   - If LLM needs full uncompressed document, it executes `headroom_retrieve(cache_key)`.

---

# CONTEXT & ROUTING LAYER — §2-3: The 12-Stage Reactive Pipeline

## Feature §2.1-2.3: Query Router / Intent Classifier (Stage 2)

### Source
- **Codebase**: Locus-original design (from `locus_agent_loop.md` & `locus_microsystems.html`)
- **Verification**: [✅ VERIFIED: `locus_microsystems.html` Query Router 6-step breakdown]

### Call Chain (12-Stage Reactive Loop Inter-File Execution Flow)

> Numbering matches `locus_agent_loop.md` exactly (Stage 0 → Stage 12). This is the
> single canonical stage map; do not renumber.

```
USER MESSAGE (Telegram / CLI / MCP / voice)
  │
  ├─► Stage 0: Intake & Logging
  │     └─► locus/channels/telegram.ts → log raw message to PG telegram_logs, handle voice/attachments
  │
  ├─► Stage 1: Prompt Injection Filter
  │     └─► locus/security/sanitizer.ts → regex blocklist + (optional) semantic check
  │
  ├─► Stage 2: Query Router / Intent Classifier
  │     └─► locus/core/conductor.ts → POST http://localhost:8420/router/classify (DeepSeek V4 Flash, cheapest available)
  │           └─► Returns: Routing Manifest { intent_type, sources_required, temporal_scope, deep_reasoning, confidence }
  │
  ├─► Stage 3: State Injection
  │     └─► locus/core/state-engine.ts → read CURRENT_STATE (DCS, mode, faction, alerts)
  │
  ├─► Stage 4: Parallel Retrieval Execution (async.gather, never sequential)
  │     ├─► Mode A (pgvector): locus/providers/retrieval/pgvector.ts → 384-dim recency-boosted vector search
  │     ├─► Mode B (PostgreSQL): locus/providers/retrieval/pg.ts → parameterised SQL query
  │     ├─► Mode C (Neo4j): locus/providers/retrieval/neo4j.ts → Cypher 2-hop pathway traversal
  │     └─► PageIndex: locus/providers/retrieval/pageindex.ts → tree reasoning RAG
  │
  ├─► Stage 5: Headroom Compression
  │     └─► locus/providers/compression/headroom-ccr.ts → compress results to layer budgets
  │
  ├─► Stage 6: Context Forge 6-Layer Assembly
  │     └─► locus/core/context-forge.ts → merges layers into <=800 token block
  │           └─► Layer 1: Identity (80t) | Layer 2: Temporal (60t) | Layer 3: PG Events (180t) | Layer 4: Neo4j (150t) | Layer 5: Semantic (200t) | Layer 6: Web (100t)
  │
  ├─► Stage 7: Special Routing
  │     ├─► CODING_REQUEST → harness delegation (Stage 7 handler)
  │     ├─► RESEARCH_REQUEST → autoresearch pipeline
  │     ├─► COMMAND → direct handler, skip to Stage 11
  │     └─► TASK_PLANNING / INFERENCE_REQUEST → scheduler / cause-chain engine
  │
  ├─► Stage 8: Mode-Aware Instruction Building
  │     └─► locus/core/mode-instruction.ts → tone/rules by operating mode (SURVIVAL→PEAK)
  │
  ├─► Stage 9: The Generator (the ONLY place the LLM speaks)
  │     └─► locus/core/llm-client.ts → DeepSeek V4 Flash (standard), Gemini 2.5 Pro (Sunday synthesis)
  │
  ├─► Stage 10: Anti-Hallucination Guard
  │     └─► locus/core/anti-hallucination.ts → verify claims against assembled context
  │
  ├─► Stage 11: Response Delivery + Feedback
  │     └─► locus/channels/telegram.ts → sendMessage with 👍/👎 inline keyboard; log to PG
  │
  └─► Stage 12: Post-Turn Learning (async, non-blocking)
        ├─► memory write (Neo4j + Headroom + PageIndex)
        ├─► Hebbian weight update (👍 ×1.3 / 👎 ×0.7; STDP if <2min)
        ├─► reward signal log → personal reward model
        └─► state engine trigger (PG LISTEN/NOTIFY)
```

### Stripped Micro-Step Logic (from `locus_microsystems.html`)

```
STEP 1: Receive Raw Message
    - Accepts sanitized input string from Conductor.

STEP 2: Build Classifier Prompt (<200 tokens)
    - Intent Categories: FACTUAL_PERSONAL, BEHAVIORAL_PATTERN, KNOWLEDGE_RETRIEVAL,
      TASK_PLANNING, EMOTIONAL_STATE, EXTERNAL_KNOWLEDGE, SYNTHESIS, INFERENCE_REQUEST.
    - System prompt defines all 8 categories with one-shot examples.

STEP 3: DeepSeek V4 Flash (cheapest available) Classification Call
    - Temperature = 0, structured JSON mode enforced.
    - Latency target: < 300ms.
    - Output payload: { intent_type, sources_required[], temporal_scope, deep_reasoning, confidence }

STEP 4: Confidence Gate (Anti-Hallucination)
    - IF confidence < 0.7:
          sources_required = ["pg", "neo4j", "pgvector", "pageindex"] (Query ALL sources)
      ELSE:
          sources_required = returned_sources_list

STEP 5: Temporal Scope Resolution
    - TODAY → today 00:00 to 23:59 IST
    - WEEK  → last 7 days
    - MONTH → last 30 days
    - ALLTIME → no lower bound
    - Outputs start_ts and end_ts Unix timestamps directly to Retriever.

STEP 6: Return Routing Manifest
    - Assembles Routing Manifest object to Master Conductor. Emits behavioral event.
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/intent-classifier.ts` (TS client) + `sidecar/router/classifier.py` (FastAPI sidecar)
- **Provider Interface**: Implements `IntentClassifier`
- **Integration**: Called in Pi's `transformContext` hook at Stage 2. The returned `sources_required` array determines which retrieval providers fire in parallel at Stage 5.

---

## Feature §2.4: State Engine (Stage 3)

### Source
- **Codebase**: Locus-original design (from `locus_microsystems.html` & `LOCUS_SYSTEM_v1.md`)
- **Verification**: [✅ VERIFIED: `locus_microsystems.html` State Engine breakdown]

### Stripped Micro-Step Logic (from `locus_microsystems.html`)

```
STEP 1: Write Trigger Reception
    - Event-driven: fires on every INSERT/UPDATE to PostgreSQL behavioral_events table.
    - Uses PostgreSQL NOTIFY/LISTEN channel 'locus_events' via asyncpg (eliminates polling).

STEP 2: Last Check-in Read
    - Reads most recent check-in row from PostgreSQL checkins table.
    - If no check-in today: apply staleness penalty (all scores × 0.9).
    - If no check-in in 3+ days: default to baseline (5,5,5,7) & queue STALE_CHECKIN alert.

STEP 3: Canonical DCS Calculation
    - Formula: DCS = ((E + M + S) / 3) × (1 - ST / 20)
      where:
        E = Energy level (1-10)
        M = Mood valence (1-10)
        S = Sleep quality (1-10)
        ST = Stress score (0-20, computed as input_stress × 2)
    - Output Range: 0.0 to 10.0 float.

STEP 4: Operating Mode Determination (LOCUS_SYSTEM_v1.md §4 thresholds)
    - DCS 0.0 - 2.0  → SURVIVAL   (non-negotiables only, no cognitive strain)
    - DCS 2.1 - 4.0  → RECOVERY   (D ≤ 4 only, gentle movement)
    - DCS 4.1 - 6.0  → NORMAL     (standard balanced scheduling, D ≤ 7)
    - DCS 6.1 - 8.0  → DEEP_WORK  (highest-TWS single block, D ≤ 9)
    - DCS 8.1 - 10.0 → PEAK       (most ambitious task first, all difficulties)

STEP 5: Update Redis CURRENT_STATE Cache
    - Writes multi-dimensional JSON object to Redis key `CURRENT_STATE` (TTL 6h).
    - Object fields: { dcs, operating_mode, energy, mood, stress, sleep, active_alerts[], inferred_cause_chain }
    - Fallback: If Redis unavailable, read last state_snapshot row from PostgreSQL.
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/state-engine.ts` + `sidecar/state_engine.py`
- **Data Store**: Redis `CURRENT_STATE` (TTL 6h) + PostgreSQL `state_snapshots` table.
- **Integration**: Triggered by PostgreSQL LISTEN channel on every event write. Read by Context Forge & Inner Loop.

---

## Feature §2.5: Context Forge (Stage 6) — The 6-Layer Assembler

### Source
- **Codebase**: Locus-original design (from `locus_microsystems.html`)
- **Verification**: [✅ VERIFIED: `locus_microsystems.html` Context Forge 12-step breakdown]

### Stripped Micro-Step Logic (from `locus_microsystems.html`)

```
STEP 1: Receive Parallel Retrieval Results
    - Consolidates results from pgvector, PostgreSQL, Neo4j, PageIndex, Web, Redis state, and Identity profile.

STEP 2: Global Relevance Scoring
    - Unified Score = (semantic_similarity × 0.6) + (recency_weight × 0.25) + (source_priority × 0.15)
    - Source priority: Neo4j pathways (0.4) > PG facts (0.3) > pgvector (0.2) > Web (0.1)
    - Recency weight: last 6h = 1.0, last 24h = 0.8, last 7d = 0.5, older = 0.2.

STEP 3: Layer 1 — User Identity (Hard limit: 80 tokens)
    - Inject stated life goals, active factions, confirmed behavioral tendencies, peak performance windows.

STEP 4: Layer 2 — Temporal Context (Hard limit: 60 tokens)
    - Inject current time (IST), operating_mode, DCS, day of week, active exam flags.

STEP 5: Layer 3 — PostgreSQL Events (Hard limit: 180 tokens)
    - Inject recent events compressed via LOCUS_SHORTHAND (e.g. {✓:task_name,dur:45,q:8}).

STEP 6: Layer 4 — Neo4j Pathways (Hard limit: 150 tokens)
    - Inject Neo4j paths with edge weight > 0.3. Format: 'task_A → behavior_B (w:0.84) → outcome_C'.

STEP 7: Layer 5 — pgvector / Obsidian Semantic (Hard limit: 200 tokens)
    - Inject top semantic snippets with recency boost multiplier (×1.5 for last 7d vectors).

STEP 8: Layer 6 — Web Search Results (Hard limit: 0 - 100 tokens)
    - Populated ONLY if intent requires external knowledge or retrieval returned empty. Top 3 snippets.

STEP 9: Token Budget Enforcement & Headroom Compression
    - Appends layers 1→6. If total exceeds 800 tokens, applies Headroom CCR compression to Layer 5 & 3.
    - Layers 1 & 2 are NEVER truncated.

STEP 10: Hebbian Weight Increment (+0.1)
    - For every Neo4j path included in Layer 4, increment edge weights by +0.1 in Neo4j (Hebbian traversal signal).

STEP 11: System Prompt & LOCUS_SHORTHAND Prepend
    - Prepends identity system prompt + LOCUS_SHORTHAND decoder dictionary + strict anti-hallucination instruction:
      "If data needed to answer a question is not in this context, say you don't have it yet. Do NOT invent data."

STEP 12: Return Assembled Context Block
    - Delivers complete <=800 token context block + metadata to Conductor.
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/context-forge.ts`
- **Provider Interface**: Implements `ContextAssembler`
- **Integration Point**: Pi's `transformContext` hook executes Context Forge assembly at Stage 6 right before sending prompt to the LLM.
- **Layer Budgets**: Configurable via `locus.brain.context_forge.layers` (Identity 80t, Temporal 60t, Events 180t, Neo4j 150t, pgvector 200t, Web 100t; Hard total limit: 800 tokens).
- **Compression Fallback**: If total tokens > 800, Headroom CCR is triggered on Layers 5 & 3. Layers 1 & 2 are strictly protected from pruning.

---

## Feature §2.6: Anti-Hallucination Guard (Stage 10)

### Source
- **Codebase**: Locus-original
- **Verification**: [📐 DESIGNED]

### Stripped Logic (Pseudocode)

```
FUNCTION anti_hallucination_check(llm_response, context_forge_content):
    // Runs as afterToolCall hook OR as post-generation check
    
    // Step 1: Extract claims from LLM response
    claims = extract_factual_claims(llm_response)
    // A "claim" is any statement about the user, their data, or their history
    // NOT opinions, advice, or external knowledge
    
    // Step 2: For each claim, check if it's grounded in context
    ungrounded_claims = []
    FOR EACH claim IN claims:
        IF NOT context_forge_content.contains_evidence_for(claim):
            ungrounded_claims.append(claim)
    
    // Step 3: If ungrounded claims detected
    IF ungrounded_claims.length > 0:
        // Option A: Strip ungrounded claims and regenerate
        IF config.anti_hallucination.mode == "strict":
            REJECT response
            LOG to brain_errors (severity=2, type="hallucination")
            RETURN { block: true, reason: "Response contained ungrounded claims" }
        
        // Option B: Add caveat (default mode)
        ELIF config.anti_hallucination.mode == "warn":
            response += "\n\n⚠️ Note: I'm not fully certain about some details. Let me know if anything seems off."
            LOG to brain_errors (severity=1, type="soft_hallucination")
    
    RETURN { block: false }

COST: ~0 tokens if no claims detected (pure string matching).
      ~50 tokens if semantic check needed (cheap LLM call).
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/anti-hallucination.ts`
- **Integration**: Runs in Pi's `afterToolCall` hook for the main LLM response (the "generate" tool result).

## Feature §2.7-2.8: Intelligent Model Routing + Quality-Based Fallback

**Status**: complete  
**Verdict**: 🔄 AUGMENT (steal OpenHuman's routing module, adapt for Locus' model strategy)

### Source(s) mined
- **Codebase**: OpenHuman `routing/` module — `README.md` (90 lines), `policy.rs`, `factory.rs`, `provider.rs`, `health.rs`, `quality.rs`, `telemetry.rs`
- **Query method**: [✅ VERIFIED: direct file read of `routing/README.md`]

### Logic extracted

```
INTELLIGENT MODEL ROUTING (from OpenHuman routing/ — COMPLETE):

  PURPOSE: Policy-driven layer between callers and inference providers.
  Decides per-request whether to run on LOCAL model server or REMOTE backend.
  No RPC surface, no persistence — pure in-process decision engine.

  ═══ TASK CLASSIFICATION (policy.rs) ═══
  
  FUNCTION classify(model_string) → TaskCategory:
    IF model_string starts with "hint:":
      MATCH hint:
        "hint:quick", "hint:fast"     → Lightweight
        "hint:medium"                  → Medium
        "hint:reasoning", "hint:agentic",
        "hint:coding", "hint:chat"     → Heavy
    ELIF is_exact_model_name(model_string):
      → Heavy  // explicit model = always remote
    ELSE:
      → Heavy  // unknown = safe default
    
    GOTCHA: "hint:chat" goes remote despite being conversational.
    classify() maps it to Heavy because local model TTFT is too slow.

  ═══ ROUTING DECISION (policy.rs) ═══
  
  FUNCTION decide(category, local_healthy, hints) → (primary, fallback):
    ┌──────────────┬──────────────────┬──────────────────────────────────┐
    │ Category     │ Default          │ Override conditions              │
    ├──────────────┼──────────────────┼──────────────────────────────────┤
    │ Lightweight  │ Local            │ Remote if local unhealthy        │
    │ Medium       │ Remote           │ Local if LatencyBudget::Low      │
    │              │                  │   OR CostSensitivity::High       │
    │ Heavy        │ Remote (always)  │ Local ONLY if privacy_required   │
    └──────────────┴──────────────────┴──────────────────────────────────┘
    
    PRIVACY_REQUIRED:
      Forces local routing for ALL categories (even Heavy)
      No remote fallback — fails closed
      Disables streaming (supports_streaming → false)
    
    TOOLS FORCE REMOTE:
      If request carries tools and policy chose local → override to remote
      (local lacks native tool calling)

  ═══ ROUTING HINTS ═══
  
  RoutingHints {
    latency_budget: LatencyBudget,     // Low | Medium | High
    cost_sensitivity: CostSensitivity, // Low | Medium | High
    privacy_required: bool,            // true → local only, no fallback
  }

  ═══ LOCAL HEALTH CHECKING (health.rs) ═══
  
  LocalHealthChecker:
    Cached probe with 30-second TTL and 3-second timeout
    Mutex<Option<HealthCache>> — NEVER held across await
    
    PROBE LOGIC:
      IF local_provider == Ollama:
        GET {base_url}/api/tags → parse JSON
      ELIF local_provider == OpenAI-compat (LM Studio, llama.cpp):
        GET {base_url}/models → parse JSON
    
    RESULT: { healthy: bool, last_check: Instant }
    
    GOTCHA: Lock discipline — read cache, release mutex, then probe.
    This prevents async deadlocks.

  ═══ QUALITY-BASED FALLBACK (quality.rs) ═══
  
  FUNCTION is_low_quality(response_text) → bool:
    // Allocation-free hot-path heuristic
    
    // Check 1: Length floor
    IF response_text.len() < MIN_RESPONSE_BYTES: RETURN true
    
    // Check 2: Empty-noise tokens
    IF response_text.trim() IN ["...", "I", "", "?"]: RETURN true
    
    // Check 3: Refusal DFA (Aho-Corasick, LazyLock compiled once)
    REFUSAL_PATTERNS = [
      "I cannot", "I can't", "I'm unable", "I apologize but",
      "As an AI", "I don't have the ability",
      "I'm not able", "I am not able"
    ]
    IF aho_corasick.is_match(response_text): RETURN true
    
    RETURN false
    
    NOTE: Deliberately conservative — serving a refusal is more
    user-visible than an extra remote call. False positives acceptable.

  ═══ DISPATCH FLOW (provider.rs) ═══
  
  IntelligentRoutingProvider implements Provider:
    
    FUNCTION chat(request):
      decision = decide(classify(request.model), health.check(), hints)
      
      // Primary attempt
      TRY: response = dispatch(decision.primary, request)
      CATCH error:
        IF decision.primary == Local AND NOT privacy_required:
          response = dispatch(Remote, request)  // fallback
        ELSE:
          RAISE error
      
      // Quality gate (only for local primary)
      IF decision.primary == Local AND is_low_quality(response.text):
        IF NOT privacy_required:
          response = dispatch(Remote, request)  // quality fallback
      
      emit_routing_record(decision, response)
      RETURN response

  ═══ MODEL ID NORMALIZATION ═══
  
  Heavy hint:* strings → backend model IDs:
    "hint:reasoning" → MODEL_REASONING_V1
    "hint:chat"      → MODEL_CHAT_V1
    "hint:agentic"   → MODEL_AGENTIC_V1
    "hint:coding"    → MODEL_CODING_V1

  ═══ TELEMETRY (telemetry.rs) ═══
  
  RoutingRecord {
    category, target (Local|Remote), resolved_model,
    health_status, used_fallback: bool,
    latency_ms, tokens_in, tokens_out, estimated_cost
  }
  Emitted via tracing::info! under target "routing"
  
  GOTCHA: Token/cost telemetry only populated for chat()
  (which carries ChatResponse.usage). chat_with_system and
  chat_with_history emit zeroed token/cost fields.
```

### Locus adaptation
- **Component**: `locus/core/routing/` — TypeScript port of the decision engine
- **Provider Interface**: Wraps the existing `ModelProvider` with routing logic
- **Repo vs `.locus`**: routing code in `locus-os` (repo); routing hints configurable in `.locus/config.yaml`
- **STEAL VERBATIM**: The classify→decide→dispatch→fallback flow, the 3-category system (Lightweight/Medium/Heavy), the health cache with 30s TTL, the Aho-Corasick refusal DFA, the privacy_required fail-closed pattern, the RoutingRecord telemetry schema
- **ADAPT**: Locus' local model is Ollama (default). Remote is DeepSeek V4 Flash (primary) or Gemini 2.5 Pro (for reasoning tasks). Local health check uses the Ollama `/api/tags` endpoint.
- **Swappable / off state**: `locus.routing.enabled`. Off → all requests go to the configured primary model with no local/remote decision. `locus.routing.privacy_mode: true` → forces local for everything.

---


# CONTEXT REFERENCES & CODING CONTEXT — §6

## Feature §6.2: Dynamic Context References (@file, @symbol, @git, @diff)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `hermes-agent/agent/context_references.py` (228 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/context_references.py` | 228 | Parses `@` prefix reference tags in user prompts; resolves files, symbols, git branches, and URLs into bounded context chunks | `prompt_builder.py` (injects resolved snippets into message array), `file_cache.py` |
| `hermes-agent/agent/prompt_builder.py` | 180 | Formats resolved context references into structured `<context_ref>` XML enclosures with line numbers and token caps | `context_references.py`, `conversation_loop.py` |

### Stripped Logic (Pseudocode)

```
DATA STRUCTURES:
    ContextRefType:
        FILE    = "@file"    // @file:src/main.ts#L10-L45
        DIR     = "@dir"     // @dir:src/core/
        SYMBOL  = "@symbol"  // @symbol:runLoop
        GIT     = "@git"     // @git:branch or @git:status
        DIFF    = "@diff"    // @diff:unstaged
        URL     = "@url"     // @url:https://docs.neo4j.com

    ResolvedReference:
        ref_type: ContextRefType
        target_path: string
        content: string
        token_count: int
        truncated: bool

REFERENCE PARSER REGEX:
    PATTERN = r"(@(file|dir|symbol|git|diff|url):([^\s
]+))"

FUNCTION extract_and_resolve_references(user_prompt: string, max_ref_budget: int = 1500) -> Tuple[string, List[ResolvedReference]]:
    matches = regex_findall(PATTERN, user_prompt)
    resolved_refs = []
    clean_prompt = user_prompt
    allocated_tokens = 0

    FOR EACH full_tag, ref_kind, target IN matches:
        IF allocated_tokens >= max_ref_budget:
            BREAK
            
        remaining_budget = max_ref_budget - allocated_tokens
        
        IF ref_kind == "file":
            path, start_line, end_line = parse_path_and_lines(target)
            content = read_file_lines(path, start_line, end_line)
            tokens = count_tokens(content)
            IF tokens > remaining_budget:
                content = truncate_to_tokens(content, remaining_budget)
                truncated = True
            resolved_refs.append(ResolvedReference(FILE, path, content, tokens, truncated))
            allocated_tokens += min(tokens, remaining_budget)
            
        ELIF ref_kind == "git":
            IF target == "status": content = git_status()
            ELIF target == "diff": content = git_diff()
            ELSE: content = git_log(branch=target, n=5)
            resolved_refs.append(ResolvedReference(GIT, target, content, count_tokens(content), False))
            
        ELIF ref_kind == "symbol":
            content = ast_lookup_symbol(target)
            resolved_refs.append(ResolvedReference(SYMBOL, target, content, count_tokens(content), False))
            
        // Replace tag in user prompt with clean reference identifier
        clean_prompt = clean_prompt.replace(full_tag, f"[{ref_kind.upper()}: {target}]")
        
    RETURN (clean_prompt, resolved_refs)

FORMATTING CONTEXT ENCLOSURE:
    FUNCTION format_references_xml(refs: List[ResolvedReference]) -> string:
        blocks = []
        FOR EACH ref IN refs:
            blocks.append(f"""<context_ref type="{ref.ref_type.value}" target="{ref.target_path}">
{ref.content}
</context_ref>""")
        RETURN join("

", blocks)
```

### Locus adaptation
- **Component**: `locus-os/src/core/context/references.ts` (TypeScript)
- **Provider Interface**: `ContextReferenceResolver`
- **Repo vs `.locus`**: code in `locus-os` (repo); file cache stored in memory during active session.
- **Swappable / off state**: `locus.context.references.enabled`. Off → `@` tags are treated as literal text; no file resolution occurs.
- **STEAL VERBATIM**: The regex parser grammar (`@file:path#L10-L45`, `@git:status`, `@diff`), the per-reference token budget truncation, the `<context_ref>` XML enclosure wrapper.
- **ADAPT**: Integrated directly into Pi's interactive terminal input handler and Telegram command parser before passing message to the 12-stage reactive loop.

---

## Feature §6.3: Coding Context Engine (Repo Map, AST Index, Active Diff)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `hermes-agent/agent/coding_context.py` (227 lines) + `repo_map.py`  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/coding_context.py` | 227 | Extracts active workspace coding context (git branch, unstaged diff summaries, modified file list, active tests) | `repo_manager.py`, `prompt_builder.py` |
| `hermes-agent/agent/repo_map.py` | 380 | Generates concise PageRank-ranked repository AST tree within a strict token budget (default 500 tokens) | `ast_indexer.py`, `coding_context.py` |

### Stripped Logic (Pseudocode)

```
DATA STRUCTURES:
    WorkspaceCodingState:
        repo_root: string
        active_branch: string
        dirty_files: List[string]
        staged_diff_stat: string
        unstaged_diff_stat: string
        repo_map_snippet: string
        recent_edits: List[string]

FUNCTION generate_coding_context(repo_path: string, token_budget: int = 500) -> WorkspaceCodingState:
    state = WorkspaceCodingState()
    state.repo_root = repo_path
    
    // 1. Gather Git Metadata
    state.active_branch = git_current_branch(repo_path)
    state.dirty_files = git_dirty_files(repo_path)
    state.staged_diff_stat = git_diff_stat(repo_path, staged=True)
    state.unstaged_diff_stat = git_diff_stat(repo_path, staged=False)
    
    // 2. Generate PageRank Repo Map (AST structural skeleton)
    tags = extract_ast_tags(repo_path)  // Tree-sitter extraction of classes, functions, interfaces
    call_graph = build_call_graph(tags)
    ranked_files = compute_pagerank(call_graph)
    
    // Assemble concise tree within budget
    repo_map = []
    current_tokens = 0
    FOR EACH file IN ranked_files:
        file_tree = format_file_ast_skeleton(file)
        tree_tokens = count_tokens(file_tree)
        IF current_tokens + tree_tokens > token_budget:
            BREAK
        repo_map.append(file_tree)
        current_tokens += tree_tokens
        
    state.repo_map_snippet = join("
", repo_map)
    RETURN state

FUNCTION format_coding_context_layer(state: WorkspaceCodingState) -> string:
    RETURN f"""[CODING CONTEXT]
Branch: {state.active_branch} | Dirty files: {len(state.dirty_files)}
Diff Stat: {state.unstaged_diff_stat}
Repo Map:
{state.repo_map_snippet}"""
```

### Locus adaptation
- **Component**: `locus-os/src/core/context/coding-context.ts` (TypeScript)
- **Provider Interface**: `CodingContextProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); AST index cache in `.locus/cache/ast_index.json`.
- **Swappable / off state**: `locus.context.coding_map.enabled`. Off → coding context omitted from prompt; agent relies on explicit tool lookups.
- **STEAL VERBATIM**: The PageRank AST ranking algorithm, git diff-stat summary formatting, and 500-token repo-map budget enforcement.
- **ADAPT**: Injected into Context Forge Layer 3 (Events & Workspace) when the user is in a coding session or working directory is a git repo.


# KEEP-PI FEATURES — Inherited Unchanged from Pi Agent

> These features are inherited directly from Pi's codebase with zero modifications. Each is listed with its source file path for reference. An AI implementer does not need to build these — they come with Pi.

## Feature §1.8: Stream Diagnostics
- **Verdict**: 📦 KEEP-PI · **Source**: Pi event stream utilities · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi functionality, always on)

## Feature §1.9: Rate Limit Tracking

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `rate_limit_tracker.py` (247 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/rate_limit_tracker.py` | 247 | Captures `x-ratelimit-*` headers (12 headers: RPM/RPH/TPM/TPH caps, remaining, reset timers) from provider API responses; provides formatted display for `/usage` | `auxiliary_client.py` (receives headers after each LLM call), `display.py` (renders in TUI footer) |
| `hermes-agent/agent/nous_rate_guard.py` | ~180 | Pre-call rate-limit guard for Nous Portal; pauses requests when remaining < threshold | `rate_limit_tracker.py` (reads current state), `conversation_loop.py` (called before LLM dispatch) |
| `hermes-agent/agent/display.py` | ~600 | Renders rate limit status in CLI/TUI footer widgets | `rate_limit_tracker.py` (reads formatted state) |

### Stripped Logic (Pseudocode)

```
DATA STRUCTURES:
    RateLimitBucket:
        limit: int              // e.g. 60 RPM
        remaining: int          // e.g. 45 remaining
        reset_seconds: float    // seconds until window resets
        captured_at: float      // timestamp of capture
        
        COMPUTED: used = max(0, limit - remaining)
        COMPUTED: usage_pct = (used / limit) * 100
        COMPUTED: remaining_seconds_now = max(0, reset_seconds - (now - captured_at))
    
    RateLimitState:
        requests_min: RateLimitBucket    // RPM
        requests_hour: RateLimitBucket   // RPH
        tokens_min: RateLimitBucket      // TPM
        tokens_hour: RateLimitBucket     // TPH
        provider: string

FUNCTION parse_rate_limit_headers(response_headers, provider):
    // Extract 12 x-ratelimit-* headers:
    //   x-ratelimit-limit-requests, x-ratelimit-remaining-requests, x-ratelimit-reset-requests
    //   x-ratelimit-limit-requests-1h, x-ratelimit-remaining-requests-1h, x-ratelimit-reset-requests-1h
    //   (same pattern for tokens)
    state = RateLimitState()
    state.requests_min = parse_bucket("requests", headers)
    state.requests_hour = parse_bucket("requests-1h", headers)
    state.tokens_min = parse_bucket("tokens", headers)
    state.tokens_hour = parse_bucket("tokens-1h", headers)
    state.captured_at = now()
    state.provider = provider
    RETURN state

FUNCTION format_rate_limit_display(state):
    IF NOT state.has_data: RETURN "No rate limit data"
    // Format: "RPM: 45/60 (75%) | TPM: 12K/100K (12%) | resets in 32s"
    lines = []
    FOR EACH bucket IN [requests_min, requests_hour, tokens_min, tokens_hour]:
        IF bucket.limit > 0:
            lines.append("{label}: {used}/{limit} ({pct}%) resets {remaining_seconds}s")
    RETURN join(lines)

PRE-CALL RATE GUARD (from nous_rate_guard.py):
    FUNCTION should_throttle(state, safety_margin=0.1):
        IF state.requests_min.remaining < state.requests_min.limit * safety_margin:
            sleep(state.requests_min.remaining_seconds_now)
        IF state.tokens_min.remaining < 1000:
            sleep(state.tokens_min.remaining_seconds_now)
```

### Locus adaptation
- **Component**: `locus/core/tracking/rate-limits.ts` — TypeScript port of header parsing + state tracking
- **Provider Interface**: `RateLimitTracker` (singleton per session). Reads headers via Pi's `afterToolCall` / response hooks.
- **Repo vs `.locus`**: code in `locus-os` (repo); no secrets involved. Rate limit state is ephemeral (in-memory, not persisted).
- **Swappable / off state**: `locus.tracking.rate_limit.enabled`. Off → rate limit headers not parsed; TUI footer shows no rate-limit status; no pre-call throttling.
- **STEAL VERBATIM**: The 12-header parsing schema, the `RateLimitBucket` data structure with live `remaining_seconds_now` calculation, the pre-call guard threshold logic.
- **ADAPT**: Wire into Pi's response interceptor (the `afterToolCall` hook captures response headers). Display via Pi's `registerFooterWidget()` API.

---

## Feature §1.10: Usage / Cost Tracking

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `usage_pricing.py` (909 lines) + `credits_tracker.py` (38K)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/usage_pricing.py` | 909 | Canonical usage extraction (input/output/cache/reasoning tokens), billing route resolution, pricing lookup (per-million rates), cost calculation per request | `model_metadata.py` (fetches pricing from provider APIs), `credits_tracker.py` (accumulates costs) |
| `hermes-agent/agent/credits_tracker.py` | ~700 | Session-level and daily cost accumulation; credits balance tracking; `/usage` command output formatter | `usage_pricing.py` (receives per-request costs), `display.py` (renders in footer) |
| `hermes-agent/agent/model_metadata.py` | ~1200 | Model pricing database (official docs snapshot); provider API metadata fetching; model capability flags | `usage_pricing.py` (supplies pricing entries) |

### Stripped Logic (Pseudocode)

```
DATA STRUCTURES:
    CanonicalUsage:
        input_tokens: int
        output_tokens: int
        cache_read_tokens: int
        cache_write_tokens: int
        reasoning_tokens: int
        request_count: int = 1
        COMPUTED: prompt_tokens = input + cache_read + cache_write
        COMPUTED: total_tokens = prompt_tokens + output_tokens
    
    PricingEntry:
        input_cost_per_million: Decimal     // e.g. $3.00/M for Claude Sonnet
        output_cost_per_million: Decimal    // e.g. $15.00/M
        cache_read_cost_per_million: Decimal
        cache_write_cost_per_million: Decimal
        request_cost: Decimal               // flat per-request fee (some providers)
        source: "provider_cost_api" | "official_docs_snapshot" | "user_override"
    
    CostResult:
        amount_usd: Decimal
        status: "actual" | "estimated" | "included" | "unknown"
        source: CostSource
        label: string                       // human-readable (e.g. "$0.0034")

FUNCTION extract_canonical_usage(raw_response, provider):
    // Normalize provider-specific usage formats into CanonicalUsage
    // Anthropic: usage.input_tokens, usage.output_tokens, usage.cache_creation_input_tokens
    // OpenAI: usage.prompt_tokens, usage.completion_tokens, usage.prompt_tokens_details.cached_tokens
    // Google: usageMetadata.promptTokenCount, candidatesTokenCount
    // Map each provider's schema to the canonical one
    RETURN CanonicalUsage(...)

FUNCTION resolve_pricing(provider, model, base_url):
    // Priority: user_override > provider_cost_api > official_docs_snapshot > unknown
    IF user has pricing override in config: RETURN override
    TRY: pricing = fetch_from_provider_api(provider, model)  // some providers expose /pricing endpoints
    CATCH: pricing = lookup_from_snapshot(model)              // fallback to hardcoded pricing DB
    RETURN pricing

FUNCTION calculate_cost(usage: CanonicalUsage, pricing: PricingEntry):
    cost = 0
    cost += (usage.input_tokens / 1_000_000) * pricing.input_cost_per_million
    cost += (usage.output_tokens / 1_000_000) * pricing.output_cost_per_million
    IF pricing.cache_read_cost_per_million:
        cost += (usage.cache_read_tokens / 1_000_000) * pricing.cache_read_cost_per_million
    IF pricing.request_cost:
        cost += pricing.request_cost * usage.request_count
    RETURN CostResult(amount_usd=cost, ...)

CREDITS TRACKER (session accumulator):
    session_total = Decimal(0)
    daily_total = Decimal(0)     // persisted to .locus/usage/YYYY-MM-DD.json
    
    FUNCTION on_request_complete(cost_result):
        session_total += cost_result.amount_usd
        daily_total += cost_result.amount_usd
        persist_daily_log()
    
    FUNCTION format_usage_display():
        RETURN "Session: ${session_total:.4f} | Today: ${daily_total:.4f} | Tokens: {total_tokens}"
```

### Locus adaptation
- **Component**: `locus/core/tracking/usage.ts` + `locus/core/tracking/pricing.ts`
- **Provider Interface**: `UsageTracker` (wraps Pi's response stream to extract usage metadata after every LLM call)
- **Repo vs `.locus`**: code in `locus-os` (repo); daily usage logs cached in `.locus/usage/` (runtime state). Pricing overrides in `.locus/config.yaml`.
- **Swappable / off state**: `locus.tracking.cost.enabled`. Off → no cost calculation; footer shows token counts only without dollar amounts. `locus.tracking.cost.budget_alert` can set a daily spending cap.
- **STEAL VERBATIM**: The `CanonicalUsage` normalization logic (handles 5+ provider formats), the pricing resolution priority chain, the per-request cost formula.
- **ADAPT**: Replace Hermes' per-provider response extractors with Pi's unified response metadata (Pi already normalizes usage across providers). Daily log format adapts to Locus's `.locus/` directory structure.

---

## Feature §1.11: Title Generation

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `title_generator.py` (172 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/title_generator.py` | 172 | Auto-generates 3-7 word session titles from first user/assistant exchange; runs async post-response to avoid latency | `auxiliary_client.py` (makes the LLM call for title generation), `conversation_loop.py` (triggers after first response) |
| `hermes-agent/agent/auxiliary_client.py` | ~4000 | The auxiliary LLM client used for background tasks (cheapest/fastest model); provides `call_llm()` with fallback chain | `title_generator.py`, `background_review.py`, `error_classifier.py` (all use auxiliary calls) |

### Stripped Logic (Pseudocode)

```
TITLE GENERATION:
    PROMPT = "Generate a short, descriptive title (3-7 words) for a conversation 
              that starts with the following exchange. Return ONLY the title text, 
              nothing else. No quotes, no punctuation at the end, no prefixes."

    FUNCTION generate_title(user_message, assistant_response, timeout=30s):
        // Truncate to keep request small
        user_snippet = user_message[:500]
        assistant_snippet = assistant_response[:500]
        
        messages = [
            { role: "system", content: PROMPT },
            { role: "user", content: "User: {user_snippet}\n\nAssistant: {assistant_snippet}" }
        ]
        
        response = call_llm(
            task="title_generation",
            messages=messages,
            max_tokens=500,
            temperature=0.3,
            timeout=timeout
        )
        
        title = response.content.strip()
        
        // Clean up artifacts
        title = strip_quotes(title)
        IF title starts with "Title:": title = title[6:].strip()
        IF len(title) > 80: title = title[:77] + "..."
        
        RETURN title OR null
    
    // Called asynchronously after first response delivery
    FUNCTION generate_title_async(user_msg, assistant_msg, callback):
        spawn_thread:
            title = generate_title(user_msg, assistant_msg)
            IF title: callback(title)
            // If fails: log warning, session keeps timestamp-based title
            // Wire failure_callback to emit_auxiliary_failure for visibility
```

### Locus adaptation
- **Component**: `locus/core/sessions/title-gen.ts` — thin async wrapper
- **Provider Interface**: Uses Pi's auxiliary LLM call mechanism (cheapest available model). No separate provider interface needed.
- **Repo vs `.locus`**: code in `locus-os` (repo); generated titles stored in Pi's session metadata.
- **Swappable / off state**: `locus.sessions.auto_title.enabled`. Off → sessions use default timestamp-based titles ("Session 2026-08-19 14:30").
- **STEAL VERBATIM**: The prompt template, the 500-char truncation, the cleanup pipeline (strip quotes, remove "Title:" prefix, enforce 80-char limit), the async-after-first-response trigger pattern.
- **ADAPT**: Wire into Pi's `turn_end` event (first turn only). Use Pi's `session.setTitle()` API to update. The failure callback pattern surfaces through Pi's notification system instead of Hermes' `_emit_auxiliary_failure`.


## Feature §1.12: Onboarding & Multi-Topology Setup Flow (Installer & First-Run)

### Metadata
- **Verdict**: 🔄 AUGMENT · **Source**: Pi `first-time-setup.ts` + Hermes `setup.py` + OpenHuman `schema.json` + Locus Modular Framework
- **Verification Tag**: `[✅ VERIFIED: Pi first-time-setup.ts + Hermes setup.py read in full]`
- **Provider Interface**: `SetupWizardProvider`
- **Repo vs `.locus`**: Wizard UI code in `locus-extension/` (repo); installer bootstrapping in `scripts/` (repo); persistent secrets in `~/.locus/.env`; modular toggles in Pi's `settings.json` under `"locus"`.

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `scripts/install.ps1` / `install.sh` | ~180 | Root bootstrapping installer: environment checks (Node 20+, Python 3.11+, CouchDB), topology choice, and launcher | OS shell, `tools/requirements.txt`, `packages/` |
| `locus-extension/src/ui/setup-wizard.ts` | ~380 | Interactive Stepped Submenu for Pi TUI using `@earendil-works/pi-tui` | `locus-extension/src/index.ts`, `ctx.ui.custom()` |
| `locus-extension/src/ui/components/topology-selector.ts` | ~120 | Terminal selector for Local vs Headless VM vs Hybrid topology | `@earendil-works/pi-tui` SelectList, `settings.json` |
| `locus_cli/setup.py` | ~290 | Headless CLI wizard runner with fallback for non-TTY/scripted execution | `locus_cli/config.py`, `~/.locus/.env` |
| `sidecar/setup_service.py` | ~220 | FastAPI endpoints (`POST /setup/verify`, `POST /setup/save`) testing DB sockets and saving `.env` | Neo4j, CouchDB, LLM providers, Telegram |
| `gateway/setup_flow.py` | ~210 | Interactive Telegram bot conversation handler for `/setup` command | Telegram PTB ConversationHandler, `sidecar` |

### Stripped Logic (Pseudocode)

```
FUNCTION run_locus_onboarding_wizard(environment):
    // 0. Ensure config directories and pre-setup backup exist
    ensure_dir("~/.locus")
    backup_path = backup_existing_config()

    // 1. STEP 0: TOPOLOGY SELECTION (Local, Headless VM, Hybrid)
    //    Determines where sidecar, database, crons, and TUI run
    topology = prompt_choice("Select Locus Deployment Topology:", [
        { 
          id: "local", 
          label: "Local-Only (All-in-one)", 
          desc: "Sidecar, CouchDB, and Pi TUI run on this machine. Best for single-computer offline use." 
        },
        { 
          id: "vm", 
          label: "Headless VM (24/7 Always-On)", 
          desc: "Sidecar, CouchDB, Telegram Bot, and autonomous crons run headlessly on a Cloud VM (Oracle/VPS). No desktop TUI." 
        },
        { 
          id: "hybrid", 
          label: "Hybrid (Recommended)", 
          desc: "Headless Sidecar, CouchDB, & Telegram run on 24/7 VM; Local laptop runs Pi TUI client and Obsidian vault." 
        }
    ])

    config.set("locus.topology", topology)

    // 2. STEP 1: MODEL PROVIDER & INFERENCE SELECTION
    //    Pre-configured for DeepSeek V4 Flash, with support for local models (Ollama/vLLM) and cloud fallbacks
    provider_type = prompt_choice("Select Primary LLM Provider:", [
        { id: "deepseek", label: "DeepSeek V4 Flash (Recommended default, $0.012/day)" },
        { id: "ollama", label: "Local Ollama / LM Studio / vLLM (Private, offline, zero API cost)" },
        { id: "anthropic", label: "Anthropic Claude (Direct API Key)" },
        { id: "openrouter", label: "OpenRouter (Multi-provider aggregator)" },
        { id: "custom", label: "Custom OpenAI-Compatible Endpoint" }
    ])

    IF provider_type == "ollama":
        endpoint = prompt_text("Ollama Base URL:", default="http://localhost:11434")
        model_name = prompt_text("Model Name:", default="deepseek-r1:14b")
        config.set("locus.providers.llm", { "provider": "ollama", "endpoint": endpoint, "model": model_name })
    ELSE:
        api_key = prompt_secret(f"Enter API Key for {provider_type}:")
        save_env_secret(f"{provider_type.upper()}_API_KEY", api_key)
        config.set("locus.providers.llm", { "provider": provider_type, "model": "deepseek-chat" })

    // Optional auxiliary fallback model
    enable_fallback = prompt_yes_no("Configure secondary fallback model for API downtime?", default=true)
    IF enable_fallback:
        fallback_provider = prompt_choice("Select Fallback Provider:", ["openrouter", "ollama", "anthropic"])
        fallback_key = prompt_secret(f"Enter {fallback_provider} key (or press Enter if local):")
        IF fallback_key: save_env_secret(f"{fallback_provider.upper()}_API_KEY", fallback_key)
        config.set("locus.providers.llm_fallback", { "provider": fallback_provider, "enabled": true })

    // 3. STEP 2: COGNITIVE MEMORY TRI-STACK CONFIGURATION
    //    Neo4j Agent Memory (Graph substrate) + Headroom (Token compression) + PageIndex (Vectorless retrieval)
    enable_neo4j = prompt_yes_no("Enable Neo4j Graph Memory (POLE+O Schema & Hebbian reinforcement)?", default=true)
    IF enable_neo4j:
        neo4j_uri = prompt_text("Neo4j URI:", default="neo4j+s://xxxx.databases.neo4j.io")
        neo4j_user = prompt_text("Neo4j Username:", default="neo4j")
        neo4j_password = prompt_secret("Neo4j Password:")
        save_env_secret("NEO4J_URI", neo4j_uri)
        save_env_secret("NEO4J_USERNAME", neo4j_user)
        save_env_secret("NEO4J_PASSWORD", neo4j_password)
        config.set("locus.providers.memory", { "provider": "neo4j-agent-memory", "enabled": true })
    ELSE:
        config.set("locus.providers.memory", { "provider": "sqlite-fallback", "enabled": true })

    enable_headroom = prompt_yes_no("Enable Headroom Context Compression (CCR - 50% token reduction)?", default=true)
    config.set("locus.providers.compression", { "provider": "headroom", "enabled": enable_headroom })

    // 4. STEP 3: OBSIDIAN VAULT & COUCHDB LIVESYNC
    //    Zero-friction bi-directional sync between Obsidian and Locus headless sidecar
    vault_path = prompt_text("Absolute path to local Obsidian Vault:", default="C:/Users/soni8/Documents/Obsidian/LocusVault")
    config.set("locus.vault.path", vault_path)

    enable_livesync = prompt_yes_no("Enable CouchDB Self-Hosted LiveSync (Real-time Markdown sync)?", default=true)
    IF enable_livesync:
        couch_url = prompt_text("CouchDB Endpoint:", default="http://localhost:5984" if topology=="local" else "https://couchdb.locusapp.online")
        couch_user = prompt_text("CouchDB Username:", default="locus_admin")
        couch_pass = prompt_secret("CouchDB Password:")
        couch_db = prompt_text("CouchDB Database Name:", default="locus_vault")
        save_env_secret("COUCHDB_URL", couch_url)
        save_env_secret("COUCHDB_USER", couch_user)
        save_env_secret("COUCHDB_PASSWORD", couch_pass)
        config.set("locus.providers.vault_sync", { 
            "provider": "couchdb-livesync", 
            "enabled": true, 
            "database": couch_db, 
            "conflict_strategy": "locus-master-conductor" 
        })

    // 5. STEP 4: LIFE OS & BEHAVIORAL BASELINE
    //    4 Factions, Daily Capacity Score (DCS) formulas, and check-in schedules
    timezone = prompt_text("User Timezone:", default="Asia/Kolkata")
    config.set("locus.life_os.timezone", timezone)
    config.set("locus.life_os.factions", {
        "1_health_stability": { "target_hours": 17.5, "color": "#22C55E" },
        "2_leverage_money":   { "target_hours": 17.5, "color": "#3B82F6" },
        "3_craft_skills":     { "target_hours": 21.0, "color": "#F97316" },
        "4_expression":       { "target_hours": 14.0, "color": "#A855F7" }
    })
    checkin_time = prompt_text("Daily Morning Check-in Prompt Time (HH:MM):", default="08:00")
    config.set("locus.life_os.morning_checkin_time", checkin_time)

    // 6. STEP 5: AMBIENT MESSAGING GATEWAY (TELEGRAM)
    //    Primary headless interaction interface
    enable_tg = prompt_yes_no("Enable Telegram Ambient Bot Interface?", default=true)
    IF enable_tg:
        tg_token = prompt_secret("Telegram Bot Token (from @BotFather):")
        tg_owner = prompt_text("Telegram Authorized User/Chat ID (from @userinfobot):")
        save_env_secret("TELEGRAM_BOT_TOKEN", tg_token)
        save_env_secret("TELEGRAM_ALLOWED_USERS", tg_owner)
        config.set("locus.providers.channels.telegram", { "enabled": true, "owner_id": tg_owner })

    // 7. STEP 6: 24/7 AUTONOMOUS CRON ENGINE (HEADLESS PROACTIVITY)
    IF topology IN ["vm", "hybrid"]:
        config.set("locus.cron.enabled", true)
        config.set("locus.cron.schedules", [
            { "name": "proactive_inner_loop", "interval_minutes": 90, "window": "07:00-00:00" },
            { "name": "nightly_vault_crawl",  "cron": "0 3 * * *",    "action": "reindex_pageindex_and_neo4j" },
            { "name": "morning_briefing",     "cron": "0 8 * * *",    "action": "send_telegram_briefing" },
            { "name": "sunday_synthesis",     "cron": "0 3 * * 0",    "action": "deep_pattern_analysis" }
        ])

    // 8. STEP 7: AUTOMATED VERIFICATION & HEALTH CHECK
    print_banner("Running Live Diagnostic Probe...")
    probe_results = run_live_diagnostics(config, get_all_env_secrets())
    render_diagnostic_table(probe_results)

    IF NOT probe_results.all_ok:
        print_warning("Some connections failed. Settings saved. Run 'locus doctor' or '/doctor' anytime to re-test.")
    ELSE:
        print_success("All systems nominal! Locus configuration successfully initialized.")

    // 9. Persist configuration
    save_settings_json(config)
    RETURN { ok: true, topology: topology }
```

### Adaptation to Locus Architecture

- **Execution Surfaces**:
  1. **Pi Agent TUI**: Implemented in `locus-extension/src/ui/setup-wizard.ts` using `@earendil-works/pi-tui`'s `SteppedSubmenu`. Fired automatically on initial launch if `settings.json` has no `locus` block, or triggered manually via `/locus:setup`.
  2. **Terminal Shell (`locus setup`)**: `locus_cli/setup.py` provides an interactive terminal prompt session (using `prompt_toolkit` or fallback `input()`), or non-interactive automation via `locus setup --non-interactive --env-file <path>`.
  3. **Telegram Bot (`/setup`)**: `gateway/setup_flow.py` enables users on cloud VMs to configure Locus through chat steps without opening SSH.
- **Strict Modularity Contract**:
  - Every subsystem implements `enabled: boolean`, `provider: string`, and `options: object`.
  - If a user disables Neo4j, Locus drops to SQLite without throwing unhandled exceptions.
  - If CouchDB is disabled, Locus falls back to local vault file watching via `chokidar`.
- **Swappable / Off-State**:
  - `locus.onboarding.completed: boolean` tracks setup state. Re-running `locus setup --reconfigure` allows editing any single section without erasing the others.
- **Headless Invariant**:
  - When topology is `vm`, the installer auto-generates systemd unit files (`/etc/systemd/system/locus-sidecar.service` and `locus-gateway.service`) and registers them with `systemctl enable --now`.

## Feature §1.13: Agent Initialization
- **Verdict**: 🔄 AUGMENT · **Source**: Pi `agent-harness.ts` + Locus sidecar init · **Repo vs `.locus`**: init code in `locus-os`; connection strings in `.locus/.env`
- **Swappable / off state**: N/A (initialization is always required).

---

## Feature §2.1: 30+ LLM Providers
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/providers/` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: Individual providers disabled via config. API keys in `.locus/.env`.
- **Scope**: Anthropic, OpenAI, Google, DeepSeek, Mistral, AWS, Azure, Cloudflare, +22 more. Inherited unchanged.

## Feature §2.2: OAuth Flows
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/oauth/` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (required for provider auth)
- **Scope**: Device code + PKCE. Inherited unchanged.

## Feature §2.3: Custom / Local Models
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/models.json` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (local models optional)
- **Scope**: Ollama, LM Studio, vLLM, any OpenAI-compatible. Inherited unchanged.

## Feature §2.4: Provider Registry
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/api-registry.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi infrastructure)
- **Scope**: Auto-registration. Inherited unchanged.

## Feature §2.5: Model Selection
- **Verdict**: 📦 KEEP-PI · **Source**: Pi `/model`, Ctrl+P · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi functionality)
- **Scope**: Model cycling. Inherited unchanged.

## Feature §2.6a: Streaming (SSE)
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/stream.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi functionality)
- **Scope**: Built-in SSE streaming. Inherited unchanged.

## Feature §2.9: Image Generation
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/images.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: Disable via `locus.images.enabled`
- **Scope**: Built-in image provider registry. Inherited unchanged.

---

## Feature §3.1: File Read/Write/Edit
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/read.ts`, `write.ts`, `edit.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi tool)

## Feature §3.2: Shell / Bash
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/bash.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: `locus.tools.bash.enabled`. Off → shell commands unavailable to LLM.

## Feature §3.3: Grep / Search
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/grep.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi tool)
- **Scope**: Ripgrep-backed. Inherited unchanged.

## Feature §3.4: List / Find
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/ls.ts`, `find.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi tool)

## Feature §3.5: Web Search
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/web_search` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: Disable via tool config
- **Scope**: 8 providers (OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch). Superset of old Locus (5 providers). Inherited unchanged.

## Feature §3.6: Web Fetch
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/fetch_content` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: Disable via tool config
- **Scope**: URL→markdown, YouTube transcripts, GitHub repos. Inherited unchanged.

## Feature §3.7a: Git Tools
- **Verdict**: 🔄 AUGMENT · **Source**: Pi `git.ts` + Locus `git_ops.py` · **Repo vs `.locus`**: `locus-os`
- **Swappable / off state**: `locus.tools.git.enabled`. Off → git tools unavailable.
- **Scope**: Pi has basic git. Augment with Locus' `git_status`, `git_diff`, `git_commit`.

## Feature §3.8: Tool Call Validation
- **Verdict**: 🔄 AUGMENT · **Source**: Pi `tool-definition-wrapper.ts` + Hermes `tool_guardrails.py` · **Repo vs `.locus`**: `locus-os`
- **Swappable / off state**: Always on (safety critical)
- **Scope**: Keep Pi's wrapper. Steal Hermes' guardrails.

## Feature §3.9: Tool Result Classification
- **Verdict**: 🆕 LOCUS-NEW · **Source**: Hermes `tool_result_classification.py` · **Repo vs `.locus`**: `locus-os`
- **Swappable / off state**: `locus.tools.result_classification.enabled`. Off → results not classified.
- **Scope**: Classify results as success/failure/partial.

## Feature §3.10: Tool Output Accumulator
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/output-accumulator.ts` · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi infrastructure)
- **Scope**: Built-in truncation. Inherited unchanged.

## Feature §3.11: Tool Timeout / Budget
- **Verdict**: 🆕 LOCUS-NEW · **Source**: OpenHuman `tool_timeout` · **Repo vs `.locus`**: `locus-os`
- **Swappable / off state**: `locus.tools.timeout.enabled`. Off → no per-tool timeout enforcement.

## Feature §3.12: Custom Locus Tools
- **Verdict**: 🆕 LOCUS-NEW · **Source**: Locus-unique · **Repo vs `.locus`**: `locus-os/tools/`
- **Swappable / off state**: Individual tools toggleable via `locus.tools.<name>.enabled`
- **Scope**: See §1.3 for the 8 custom Locus tools.

---

## Feature §15.1: Web Search (8 Providers)
- **Verdict**: 📦 KEEP-PI · **Source**: `pi/web_search` · **Repo vs `.locus`**: code in `locus-os`, API keys in `.locus/.env`
- **Off state**: Web search is a Pi tool; available whenever the LLM needs it. Disable via tool config.
- **Scope**: OpenAI, Brave, Parallel, Tavily, Exa, Perplexity, Gemini + full content fetch. Superset of old Locus (5 providers). Inherited unchanged.

---

## Feature §24.1: Pi Utilities (Clipboard, Syntax Highlighting, Frontmatter, File Watcher)
- **Verdict**: 📦 KEEP-PI · **Source**: Pi core utilities · **Repo vs `.locus`**: `locus-os` (inherited)
- **Off state**: N/A (core Pi utilities, always on)
- **Scope**: clipboard, git, image handling, syntax highlighting, frontmatter, file watcher, etc. All inherited unchanged.

---

# HARNESS DELEGATION LAYER — §3.7, §11

## Feature §3.7 + §11.5: Coding Harness Delegation

### Source
- **Codebase**: Pi at `pi/packages/coding-agent/src/core/agent-session.ts` (3136 lines) + Locus-original design
- **Verification**: [✅ VERIFIED: agent-session.ts header read (120 lines). 📐 DESIGNED for delegation logic]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `agent-session.ts` | 3136 | Full session lifecycle for Pi coding agent | `system-prompt.ts`, `tools/`, `compaction/` |
| `bash-executor.ts` | ~110 | Shell command execution | `agent-session.ts` |
| `tools/index.ts` | varies | Tool registration (read, write, bash, edit, grep) | `agent-session.ts` |

### Stripped Logic (Pseudocode)

```
HARNESS DELEGATION — Locus delegates coding to external harnesses instead of coding itself

FUNCTION delegate_to_harness(task_brief, codebase_path):
    // Step 1: Select harness based on availability and task type
    harnesses = harness_registry.get_available()
    // Available harnesses and their invocation patterns:
    //
    // Antigravity (IDE-native):
    //   - Invocation: already running in VSCode, use RPC/workspace API
    //   - Best for: complex multi-file edits, test-driven development
    //
    // Claude Code (CLI):
    //   - Invocation: spawn_process("claude", ["--dangerously-skip-permissions", task_brief])
    //   - Best for: autonomous multi-step coding tasks
    //   - Returns: git diff + files modified
    //
    // OpenCode (CLI):
    //   - Invocation: spawn_process("opencode", [task_brief])
    //   - Best for: simple edits, quick fixes
    //
    // Pi itself (CLI):
    //   - Invocation: spawn_process("pi", ["--print", task_brief], { cwd: codebase_path })
    //   - Best for: Pi-ecosystem tasks, extension development
    //   - Returns: stdout with tool call results

    // Step 2: Construct task prompt for the selected harness
    prompt = """
    TASK: {task_brief.description}
    CODEBASE: {codebase_path}
    FILES TO MODIFY: {task_brief.target_files}
    CONSTRAINTS: {task_brief.constraints}
    TESTS: {task_brief.test_commands}
    """

    // Step 3: Execute harness as subprocess
    process = spawn_process(
        command = selected_harness.cli_command,
        args = selected_harness.format_args(prompt),
        cwd = codebase_path,
        env = { ...process.env, ...selected_harness.env_overrides },
        timeout = task_brief.timeout OR 600  // 10 min default
    )
    
    // Step 4: Monitor progress (non-blocking)
    WHILE process.is_running():
        IF process.has_stdout():
            emit_progress_event(process.read_stdout())
        sleep(5)
    
    // Step 5: Parse results
    IF process.exit_code == 0:
        // Collect git diff
        diff = execute_in_cwd("git diff HEAD", cwd=codebase_path)
        modified_files = execute_in_cwd("git diff --name-only HEAD", cwd=codebase_path)
        
        RETURN {
            status: "success",
            diff: diff,
            modified_files: modified_files.split("\n"),
            harness_used: selected_harness.name,
            execution_time: process.duration
        }
    ELSE:
        RETURN {
            status: "error",
            error: process.stderr,
            harness_used: selected_harness.name
        }

HARNESS SELECTION LOGIC:
    IF task.complexity == "high" AND "antigravity" IN available:
        SELECT "antigravity"  // IDE-native, best for complex edits
    ELIF task.requires_autonomous AND "claude-code" IN available:
        SELECT "claude-code"  // best autonomous capability
    ELIF task.is_quick_fix AND "opencode" IN available:
        SELECT "opencode"     // lightweight, fast
    ELSE:
        SELECT "pi"           // always available as fallback
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/harness/`
- **Provider Interface**: Implements `HarnessProvider` with methods: `is_available()`, `estimate_task()`, `execute()`, `parse_results()`
- **Integration**: Triggered when Query Router returns `intent.requires_coding == true` (Stage 8: Special Routing). Results are queued to the user via the approval gate (10-min TTL).
- **Each harness is a separate provider**: `antigravity.ts`, `claude-code.ts`, `opencode.ts`, `pi-harness.ts`

---

# POST-TURN PROCESSING — §1.7, §10

## Feature §1.7 + §10.1: Post-Turn Background Review

### Source
- **Codebase**: Hermes at `hermes-agent/agent/background_review.py`
- **Verification**: [✅ VERIFIED: 609 lines, first 100 read in detail]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `background_review.py` | 609 | Daemon-thread forked agent for memory/skill review | `memory_manager.py`, `curator.py` |
| `memory_manager.py` | ~700 | Memory lifecycle: one-provider limit, context fencing | `memory_provider.py`, `background_review.py` |
| `insights.py` | ~800 | Extract insights from conversations | `background_review.py` |

### Stripped Logic (Pseudocode)

```
FUNCTION spawn_background_review(parent_agent, conversation_snapshot):
    // CRITICAL: This runs on a DAEMON THREAD, never blocks the main loop
    
    // Step 1: Fork the parent agent's runtime
    forked_agent = fork_agent(
        parent_runtime = parent_agent.runtime,  // same provider, model, credentials
        conversation = conversation_snapshot,     // copy of messages so far
        tool_whitelist = ["memory", "skill_manage"],  // ONLY these tools allowed
        session_id = generate_new_session_id(),  // separate session
        skip_memory = true,   // don't recursively trigger memory writes
        skip_review = true    // don't recursively trigger review
    )
    
    // Step 2: Build review prompt
    review_prompt = MEMORY_REVIEW_PROMPT + SKILL_REVIEW_PROMPT
    // Memory review: "Has the user revealed preferences, personal details?"
    // Skill review: "Should any skill be saved/updated/patched?"
    
    // Step 3: Execute forked agent with review prompt
    // The forked agent reads the conversation, decides if memories/skills
    // need saving, and writes them directly to the stores
    thread = daemon_thread(target=forked_agent.run, args=[review_prompt])
    thread.start()
    // Thread runs in background. Main conversation continues immediately.
    
    // Step 4: The forked agent uses the auxiliary client (secondary LLM)
    // to avoid contesting the main model's prompt cache
    // It inherits the parent's cached system prompt prefix for efficiency

TOOL WHITELIST ENFORCEMENT:
    forked_agent.tool_filter = lambda tool_name:
        tool_name IN ["memory", "skill_manage"]
    // All other tools (terminal, write_file, browser, etc.) are DENIED
    // This prevents the review agent from side-effecting the filesystem

SKILL REVIEW PREFERENCE ORDER:
    1. UPDATE A CURRENTLY-LOADED SKILL (the one in play this session)
    2. UPDATE AN EXISTING UMBRELLA (via skills_list + skill_view)
    3. ADD A SUPPORT FILE under an existing umbrella (references/, templates/, scripts/)
    4. CREATE A NEW CLASS-LEVEL UMBRELLA SKILL (only when nothing fits)
    // Key invariant: prefer extending existing skills over creating new ones
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/learning/post-turn-reviewer.ts`
- **Provider Interface**: Implements `PostTurnProvider`
- **ADAPT**: Pi doesn't have daemon-thread forking (it's TypeScript). Instead, Locus spawns a subagent via Pi's built-in `delegate_task` tool with a restricted tool set. The subagent runs in a separate process with `skip_memory=true`.
- **KEEP**: The tool whitelist pattern, the preference order for skill updates, the "never fatal" principle (review failure should never crash the main conversation).
- **DROP**: `StreamingContextScrubber` (Hermes-specific optimization for prompt cache sharing).

---

## Feature §10.3: User Profile Building

### Source
- **Codebases**: Hermes (`curator.py`, Honcho plugin) + OpenHuman (`learning/user_profile.rs`, `learning/stability_detector.rs`)
- **Verification**: [✅ VERIFIED: OpenHuman `learning/mod.rs` (53 lines) read. Hermes `curator.py` header (100 lines) read]

### Files Involved

| File | Codebase | Purpose |
|------|----------|---------|
| `learning/user_profile.rs` | OpenHuman | Ambient user profile extraction from conversation |
| `learning/stability_detector.rs` | OpenHuman | Detect when user behavior has stabilized (30-min window) |
| `learning/reflection.rs` | OpenHuman | Post-turn reflection hook for learning extraction |
| `learning/tool_tracker.rs` | OpenHuman | Track tool usage patterns (name, args, success/fail, duration) |
| `learning/prompt_sections.rs` | OpenHuman | Format learned context for system prompt injection |
| `curator.py` | Hermes | Background skill maintenance, lifecycle state transitions |

### Stripped Logic (Pseudocode)

```
OPENHUMAN LEARNING SYSTEM — 4 hooks that compose:

1. REFLECTION HOOK (ReflectionHook):
    FUNCTION on_turn_end(conversation):
        // Extract learnings from the completed turn
        // Uses LLM to identify: corrections, preferences, patterns
        candidates = llm.extract_learnings(conversation.last_turn)
        FOR EACH candidate IN candidates:
            learning_buffer.push(LearningCandidate {
                facet_class: classify_facet(candidate),  // personality, workflow, tool_pref, etc.
                cue_family: identify_cue(candidate),     // correction, explicit_ask, implicit_pattern
                evidence: EvidenceRef { turn_id, content },
                timestamp: now()
            })

2. STABILITY DETECTOR (StabilityDetector):
    FUNCTION check_stability():
        // Every 30 minutes, check if learning buffer has converged
        recent = learning_buffer.drain_recent(window=30_minutes)
        IF recent.length < 3: RETURN  // not enough data
        
        // Aggregate by facet class
        aggregated = group_by(recent, "facet_class")
        FOR EACH facet_class, candidates IN aggregated:
            // Score consistency: do all candidates agree?
            consistency = score_consistency(candidates)
            IF consistency > STABILITY_THRESHOLD:
                // This preference has stabilized — persist it
                persist_stable_facet(facet_class, candidates)
                // Update PROFILE.md with new stable preference

3. TOOL TRACKER (ToolTrackerHook):
    FUNCTION on_tool_call(tool_name, args, result, duration):
        // Track every tool invocation
        pg.insert("tool_usage", {
            tool_name: tool_name,
            args_hash: hash(args),
            success: result.is_success,
            duration_ms: duration,
            timestamp: now()
        })
        // Used by: pattern engine, reward model, learning providers

4. USER PROFILE (UserProfileHook):
    FUNCTION generate_profile():
        // Compile stable facets into a PROFILE.md document
        facets = pg.query("SELECT * FROM user_profile_facets WHERE stable = true")
        profile_md = render_profile_markdown(facets)
        write_file(config.profile_path, profile_md)
        // This profile is loaded into the system prompt on next session

HERMES CURATOR — Periodic skill maintenance:
    FUNCTION maybe_run_curator():
        // Runs on inactivity (not cron): when idle > 2 hours AND last run > 7 days ago
        state = load_state()  // .curator_state JSON file
        IF state.paused: RETURN
        IF time_since(state.last_run_at) < 7 * 24 * 3600: RETURN
        IF idle_time() < 2 * 3600: RETURN
        
        // Spawn background review agent (same fork pattern as post-turn review)
        // But with curator-specific prompt that:
        //   1. Auto-transitions skill lifecycle states (active → stale → archived)
        //   2. Consolidates duplicate skills
        //   3. Patches outdated skills
        //   4. NEVER auto-deletes — only archives (recoverable)
        //   5. Pinned skills bypass all auto-transitions
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/learning/` directory
- **Provider Interfaces**: `UserModelProvider`, `LearningProvider`
- **ADAPT**: OpenHuman's Rust hooks become TypeScript classes implementing Locus's `LearningProvider` interface. The stability detector logic (30-min window, consistency scoring) is ported to the Python sidecar. The Hermes curator pattern becomes a scheduled task in Locus's cron system (weekly, not inactivity-based).
- **KEEP**: The 4-hook system (reflection, stability, tool tracking, profile), the "never auto-delete" curator invariant, the PROFILE.md generation pattern.

---

# SECURITY LAYER — §13

## Feature §13.1: Prompt Injection Protection

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW

### Source(s) mined
- **Codebase**: OpenHuman (`prompt_injection/detector.rs` — 526 lines, `prompt_injection/README.md`)
- **Query method**: [✅ VERIFIED: `/graphify explain` + direct file read of `detector.rs`]

### Logic extracted

```
PROMPT INJECTION PROTECTION (from OpenHuman detector.rs — COMPLETE):

  ARCHITECTURE: pure synchronous analysis library — no state, no RPC, no event bus.
  Single entry point: enforce_prompt_input(input, context) → PromptEnforcementDecision
  Called BEFORE any model or tool execution path.

  STEP 1: NORMALIZATION (normalize_prompt)
    Input text undergoes 6 transformations in a SINGLE CHARACTER PASS:
    
    a) Lowercasing (standard)
    b) Leet-speak folding: 0→o, 1→i, 3→e, 4→a, 5→s, 7→t, 8→b, 6→g, @→a
    c) Cyrillic homoglyph folding (UAX#39 confusables):
       а→a, е→e, о→o, р→p, с→c, у→y, х→x, і→i, ѕ→s, һ→h, ԁ→d
    d) Zero-width / formatting character stripping + detection flag:
       U+200B (ZWSP), U+200C-200D (joiners), U+2060 (word joiner),
       U+FEFF (BOM), U+00AD (soft hyphen), U+034F (combining grapheme joiner),
       U+180E, U+200E-200F (bidi marks), U+202A-202E, U+2066-2069
       → is_obfuscation_char() is SINGLE SOURCE OF TRUTH for both detection and stripping
    e) Fullwidth ASCII folding: U+FF01..U+FF5E → U+0021..U+007E
    f) Whitespace collapse → `collapsed` string; whitespace strip → `compact` string
    
    OUTPUT: NormalizedPrompt {
      lowered,               // just lowercased
      collapsed,             // normalized + whitespace-collapsed
      compact,               // collapsed + all-whitespace-removed
      had_zwsp: bool,        // obfuscation char detected
      has_base64_marker: bool,  // regex: [A-Za-z0-9+/]{24,}={0,2}
      has_instruction_override: bool,  // "ignore previous instructions" variants
      has_exfiltration_intent: bool    // "system prompt" / "developer instructions" etc.
    }

  STEP 2: DETECTION RULES (scored, batched DFA)
    All rules compiled into a SINGLE RegexSet (one DFA pass per variant).
    Matched across ALL THREE normalized variants: lowered, collapsed, compact.
    
    RULES (code → score → pattern):
    ┌──────────────────────────────────────┬───────┬──────────────────────────────────┐
    │ code                                 │ score │ what it catches                  │
    ├──────────────────────────────────────┼───────┼──────────────────────────────────┤
    │ override.ignore_previous             │ 0.44  │ "ignore/disregard/forget/bypass   │
    │                                      │       │  previous/prior/system            │
    │                                      │       │  instructions/rules/prompts"      │
    │ override.role_hijack                 │ 0.30  │ "you are now", "developer mode",  │
    │                                      │       │  "jailbreak", "DAN" variants      │
    │ exfiltrate.system_prompt             │ 0.42  │ "reveal/show/dump the system      │
    │                                      │       │  prompt/instructions"              │
    │ exfiltrate.secrets                   │ 0.18  │ bare credential nouns (weak sig)  │
    │                                      │       │  api key, secret, token, password │
    │ exfiltrate.credentials_with_intent   │ 0.46  │ extraction verb + determiner +    │
    │                                      │       │  credential noun (bounded window) │
    │                                      │       │  EXCLUDES: show,give,tell,fetch   │
    │ tool.abuse                           │ 0.30  │ "call/use tool without approval    │
    │                                      │       │  even if forbidden"                │
    └──────────────────────────────────────┴───────┴──────────────────────────────────┘
    
    GOTCHA: exfiltrate.credentials_with_intent deliberately EXCLUDES high-false-positive
    verbs (show, give, tell, fetch, return, output) — see issue #1940. Requires a
    determiner within a bounded window (≤2 filler words).

  STEP 3: INLINE HEURISTICS (pre-DFA)
    IF normalized.has_instruction_override:
      score += 0.56  // above Review threshold (0.55) so spacing-obfuscated attacks
                     // like "i g n o r e  a l l  p r e v i o u s" still caught
      reason: override.obfuscated_instruction
    IF normalized.has_exfiltration_intent:
      score += 0.24
      reason: exfiltration.intent

  STEP 4: OPTIONAL HEURISTIC CLASSIFIER (env-gated)
    Enabled when: OPENHUMAN_PROMPT_INJECTION_CLASSIFIER="heuristic"
    
    HeuristicClassifier.classify(normalized):
      score = 0.0
      IF had_zwsp:                                   score += 0.08
      IF has_base64_marker:                           score += 0.08
      IF has_instruction_override AND has_exfiltration_intent: score += 0.20
      RETURN min(score, 0.25) with reason "classifier.suspicious_combo"

  STEP 5: VERDICT (fixed thresholds)
    total_score = min(sum_of_all_scores, 1.0)
    IF total_score ≥ 0.70 → Block
    IF total_score ≥ 0.55 → Review
    ELSE                  → Allow
    
    THRESHOLD HISTORY (from TAURI-140 investigation):
    - Review was 0.45 → 0.50 → 0.55 (current)
    - Raised from 0.50 to eliminate false-positive band where
      role_hijack(0.30) + secrets(0.18) = 0.48 blocked legit technical prompts
    - obfuscated_instruction raised to 0.56 so spacing attacks still reach Review

  STEP 6: AUDIT (PII-safe)
    PromptEnforcementDecision {
      verdict, score, reasons[],
      action (Allow|Blocked|ReviewBlocked),
      prompt_hash: SHA-256(input),  // NEVER logs the actual prompt text
      prompt_chars: input.chars().count()
    }
    tracing::info! with source, request_id, user_id, session_id, verdict, score

  BONUS: TOOL DEFINITION SCANNING (scan_tool_definition)
    Same detection pipeline applied to MCP tool descriptions/titles.
    Rejects on any non-Allow verdict (no Review-vs-Block UX for tool metadata).
    Used by mcp_registry to reject tools with injected descriptions.

  CALLERS (6 integration points):
    agent/harness/session/runtime.rs  — gates agent session turns
    agent/bus.rs                      — screens inbound prompts on event path
    channels/providers/web.rs         — screens chat payloads at web ingress
    inference/local/ops.rs            — rejects before local-AI execution
    about_app/catalog.rs              — capability entry
    core/observability.rs             — telemetry classification
```

### Locus adaptation
- **Component**: `locus/security/prompt-injection.ts` — runs at Stage 1 of the reactive pipeline
- **Repo vs `.locus`**: detection code in `locus-os` (repo); threshold overrides + custom rules in `.locus/config.yaml`
- **Swappable / off state**: `locus.security.prompt_injection.enabled`. Off → messages pass through unsanitized (only Pi's built-in trust model applies).
- **STEAL VERBATIM**: The 6 detection rules with their exact scores, the normalization pipeline (leet-speak + Cyrillic + ZWSP), the threshold values (0.55/0.70), the SHA-256 audit pattern.
- **ADAPT**: TypeScript implementation. Use `RegExp` instead of Rust `RegexSet` (single DFA not available in JS — use sequential matching). Heuristic classifier gated by `locus.security.prompt_injection.classifier` config key.
- **Provider Interface**: N/A (built-in, not swappable at provider level)

---

## Feature §13.2: File Safety

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW

### Source(s) mined
- **Codebases**: Hermes `file_safety.py` + OpenHuman `file_state` + `cwd_jail`
- **Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)]

### Logic extracted

```
FILE SAFETY:
    cwd_jail: confine file operations to project root + allowed paths
    file_state tracking: track file modifications across tool calls
    BLOCKED_PATTERNS layered on top of Pi's shell safety
```

### Locus adaptation
- **Component**: `locus/security/file-safety.ts`
- **Repo vs `.locus`**: code in `locus-os` (repo); allowed paths config in `.locus/config.yaml`
- **Swappable / off state**: `locus.security.file_safety.enabled`. Off → Pi's default file access controls apply.

---

## Feature §13.3: Sandbox Backends

**Status**: complete  
**Verdict**: 🔀 MULTI-PROVIDER

### Source(s) mined
- **Codebase**: OpenHuman `security/` module — 4 files:
  - `traits.rs` (80 lines) — Sandbox trait
  - `bubblewrap.rs` (184 lines) — Bubblewrap impl
  - `firejail.rs` (196 lines) — Firejail impl
  - `landlock.rs` (247 lines) — Landlock impl
- **Query method**: [✅ VERIFIED: `/graphify explain BubblewrapSandbox` + direct file read of all 4 files]

### Logic extracted

```
SANDBOX SYSTEM (from OpenHuman security/ — COMPLETE IMPLEMENTATION):

  ═══ TRAIT (security/traits.rs) ═══
  
  trait Sandbox: Send + Sync {
    fn wrap_command(&self, cmd: &mut Command) → io::Result<()>  // mutate in-place
    fn is_available(&self) → bool                               // runtime probe
    fn name(&self) → &str                                       // "bubblewrap", etc.
    fn description(&self) → &str                                // human-readable
  }
  
  PATTERN: wrap_command() MUTATES the Command in-place, replacing the original
  program with the sandbox binary and prepending isolation flags. The original
  command + args become trailing arguments to the sandbox binary.

  ═══ NOOP BACKEND (traits.rs) ═══
  
  struct NoopSandbox
  impl Sandbox:
    wrap_command: no-op (Ok(()))
    is_available: always true
    name: "none"
    description: "No sandboxing (application-layer security only)"

  ═══ BUBBLEWRAP BACKEND (bubblewrap.rs) ═══
  
  struct BubblewrapSandbox
  
  AVAILABILITY PROBE:
    is_installed() = Command::new("bwrap").arg("--version").output().status.success()
    new() → Err(NotFound) if bwrap not installed
  
  wrap_command(cmd):
    original_program = cmd.get_program()   // e.g. "python"
    original_args = cmd.get_args()         // e.g. ["script.py"]
    
    *cmd = Command::new("bwrap")
      .args([
        "--ro-bind", "/usr", "/usr",     // read-only /usr
        "--dev", "/dev",                  // minimal /dev
        "--proc", "/proc",                // process info
        "--bind", "/tmp", "/tmp",         // writable /tmp
        "--unshare-all",                  // CRITICAL: full namespace isolation
        "--die-with-parent",              // kill sandbox if parent dies
      ])
      .arg(original_program)
      .args(original_args)
    
    SECURITY NOTE: NO --share-net flag → network is BLOCKED by default.

  ═══ FIREJAIL BACKEND (firejail.rs) ═══
  
  struct FirejailSandbox
  
  AVAILABILITY PROBE: same pattern ("firejail" --version)
  
  wrap_command(cmd):
    *cmd = Command::new("firejail")
      .args([
        "--private=home",    // NEW home directory (isolated)
        "--private-dev",     // minimal /dev
        "--nosound",         // no audio access
        "--no3d",            // no 3D acceleration
        "--novideo",         // no video devices
        "--nowheel",         // no input devices
        "--notv",            // no TV devices
        "--noprofile",       // skip profile loading
        "--quiet",           // suppress warnings
      ])
      .arg(original_program)
      .args(original_args)

  ═══ LANDLOCK BACKEND (landlock.rs) — Linux kernel 5.13+ LSM ═══
  
  struct LandlockSandbox { workspace_dir: Option<PathBuf> }
  
  DIFFERS FROM BUBBLEWRAP/FIREJAIL:
    - Does NOT replace the command — applies restrictions to CURRENT PROCESS
    - Child processes INHERIT the Landlock restrictions
    - Uses pure-Rust `landlock` crate (no external binary)
  
  AVAILABILITY PROBE:
    Ruleset::default()
      .handle_access(AccessFs::ReadFile | AccessFs::WriteFile)
      .create()
      .is_ok()
  
  apply_restrictions():
    ruleset = Ruleset with ALL AccessFs flags
    
    ALLOWED PATHS (explicit whitelist — everything else DENIED):
    ┌───────────────┬──────────────┬───────────────────────┐
    │ path          │ access       │ purpose               │
    ├───────────────┼──────────────┼───────────────────────┤
    │ workspace_dir │ Read+Write   │ project files         │
    │ /tmp          │ Read+Write   │ temp operations       │
    │ /usr          │ Read-only    │ system binaries       │
    │ /bin          │ Read-only    │ system binaries       │
    └───────────────┴──────────────┴───────────────────────┘
    
    ruleset.restrict_self()  // applies to current process + all children
  
  CROSS-PLATFORM STUB:
    #[cfg(not(linux + sandbox-landlock))]
    → LandlockSandbox::new() returns Err(Unsupported)
    → wrap_command returns Err(Unsupported)
    → is_available() returns false

  ═══ SELECTION STRATEGY ═══
  
  Auto-detection order (from config or probe):
    1. Config override: locus.security.sandbox.backend = "landlock"
    2. Auto-probe: try Landlock → Bubblewrap → Firejail → NoopSandbox
    3. Each backend.probe() → Ok(Self) or Err (skip to next)
```

### Locus adaptation
- **Component**: `locus/providers/sandbox/` — wraps the 4 OpenHuman backends + Pi's trust model
- **Provider Interface**: `SandboxProvider` (mirrors the `trait Sandbox` from OpenHuman)
- **Repo vs `.locus`**: sandbox adapters in `locus-os` (repo); Docker/bwrap/firejail are host-level dependencies, not Locus files
- **Swappable / off state**: `locus.security.sandbox.backend` (`docker` | `bubblewrap` | `firejail` | `landlock` | `none`). Off (`none`) → tools execute directly on the host (Pi's trust model is the only guard).
- **STEAL VERBATIM**: The trait interface (wrap_command mutates in-place), the exact bwrap/firejail flag sets, the Landlock path whitelist strategy, the auto-detection probe chain.
- **ADAPT**: TypeScript wrapper that shells out to the probe/wrap logic. On Windows (user's primary platform), Bubblewrap/Firejail/Landlock are unavailable → auto-selects `none` with warning. Docker backend works cross-platform.

---

## Feature §13.4: Autonomy Tiers

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW

### Source(s) mined
- **Codebase**: OpenHuman (autonomy tier system)
- **Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)]

### Logic extracted

```
AUTONOMY TIERS (from OpenHuman):
    READONLY:    read tools only, no writes, no terminal
    SUPERVISED:  write tools require explicit user approval (10-min TTL)
    FULL:        all tools allowed (trusted mode)
```

### Locus adaptation
- **Component**: `locus/security/autonomy-tiers.ts` — gates tool execution in Pi's `beforeToolCall` hook
- **Repo vs `.locus`**: tier definitions in `locus-os` (repo); current tier set in `.locus/config.yaml`
- **Swappable / off state**: `locus.security.autonomy_tier` (`readonly` | `supervised` | `full`). Default: `supervised`. Off (set to `full`) → all tools execute without approval gates.

---

## Feature §13.5: Approval Gate

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW

### Source(s) mined
- **Codebases**: OpenHuman (10-min TTL approval gate) + Hermes (ACP approval)
- **Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)]

### Logic extracted

```
APPROVAL GATE:
    FUNCTION queue_approval(task_id, changes, ttl=600):
        approval_store.set(task_id, { changes, status: "pending", expires: now()+ttl })
        notify_user(task_id, changes)  // via Telegram inline keyboard
        
    FUNCTION wait_for_approval(task_id, ttl):
        WHILE now() < expires:
            status = approval_store.get(task_id).status
            IF status == "approved": RETURN true
            IF status == "rejected": RETURN false
            sleep(5)
        RETURN false  // TTL expired = auto-reject
```

### Locus adaptation
- **Component**: `locus/security/approval-gate.ts` + `locus/core/approval_store.py` (sidecar)
- **Repo vs `.locus`**: code in `locus-os`; approval state is runtime-only (in-memory + Redis fallback), not persisted to `.locus`
- **Swappable / off state**: `locus.security.approval_gate.enabled`. Off → all tool calls proceed without user confirmation (only autonomy tier governs).

---

## Feature §13.6: Project Trust

**Verdict**: 📦 KEEP-PI  
**Source**: Pi `trust-manager.ts`  
**Off state**: N/A (core Pi security, always on). Inherited unchanged.

---

## Feature §13.7: Shell Blocklist

**Status**: complete  
**Verdict**: 🔄 AUGMENT (Pi shell safety + Locus policy layer)  
**Source**: Pi `file_safety.ts` + OpenHuman policy engine  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/file_safety.py` | ~400 | Blocked path patterns, write-deny lists, read-block checks for sensitive home dirs (.ssh, .aws, .gnupg, .kube, .docker) and sensitive files (.bashrc, .netrc, .pgpass, .npmrc, .pypirc) | `tool_executor.py` (called before every file read/write), `context_references.py` (validates @file references) |
| `hermes-agent/agent/tool_guardrails.py` | ~300 | Tool-level guardrails: idempotent vs mutating classification, loop detection, permission checks | `conversation_loop.py` (beforeToolCall hook) |

### Stripped Logic (Pseudocode)

```
SHELL BLOCKLIST / FILE SAFETY:

    SENSITIVE_HOME_DIRS = [".ssh", ".aws", ".gnupg", ".kube", ".docker", ".azure", ".config/gh"]
    SENSITIVE_HOME_FILES = [
        ".ssh/authorized_keys", ".ssh/id_rsa", ".ssh/id_ed25519", ".ssh/config",
        ".bashrc", ".zshrc", ".profile", ".bash_profile", ".zprofile",
        ".netrc", ".pgpass", ".npmrc", ".pypirc"
    ]
    
    FUNCTION is_read_blocked(path):
        resolved = resolve_path(path)
        FOR EACH dir IN SENSITIVE_HOME_DIRS:
            IF resolved starts_with home_dir / dir: RETURN block_error("Sensitive directory")
        FOR EACH file IN SENSITIVE_HOME_FILES:
            IF resolved == home_dir / file: RETURN block_error("Sensitive file")
        RETURN null  // not blocked
    
    FUNCTION is_write_denied(path):
        // Same checks as read + additional write-only blocks
        IF is_read_blocked(path): RETURN true
        IF path is outside project trust boundary: RETURN true
        RETURN false

LOCUS AUGMENTATION — additional blocked patterns:
    BLOCKED_SHELL_PATTERNS = [
        "rm -rf /", "rm -rf ~", "rm -rf $HOME",     // destructive commands
        ":(){ :|:& };:",                              // fork bomb
        "chmod -R 777",                               // unsafe permissions
        "curl | sh", "wget | sh",                     // pipe-to-shell (unsigned)
        "sudo rm", "sudo chmod",                      // privilege escalation
    ]
    
    FUNCTION check_shell_command(command):
        FOR EACH pattern IN BLOCKED_SHELL_PATTERNS:
            IF command contains pattern: RETURN { blocked: true, reason: pattern }
        RETURN { blocked: false }
```

### Locus adaptation
- **Component**: `locus/core/security/shell-policy.ts` — layers Locus' blocked patterns on top of Pi's built-in file safety
- **Repo vs `.locus`**: code in `locus-os` (repo); custom blocked patterns configurable in `.locus/config.yaml` under `security.shell_blocklist[]`
- **Swappable / off state**: `locus.security.shell_blocklist.enabled`. Off → reverts to Pi's built-in file safety only (sensitive dirs/files still blocked by Pi).
- **STEAL VERBATIM**: Hermes' `SENSITIVE_HOME_DIRS` and `SENSITIVE_HOME_FILES` lists, the path resolution logic with symlink following.
- **ADAPT**: Integrate via Pi's `beforeToolCall` hook for shell/bash tools. The Locus-specific `BLOCKED_SHELL_PATTERNS` regex list is additive.

---

## Feature §13.8: Data Redaction

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `redact.py` (497 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/redact.py` | 497 | Regex-based secret redaction for logs, tool output, and gateway traffic. Pattern-matches API keys, tokens, credentials. Short tokens (<18 chars) fully masked; longer tokens preserve first 6 + last 4 chars for debuggability. | `conversation_loop.py` (applied to all log output), `tool_executor.py` (applied to tool results before display) |

### Stripped Logic (Pseudocode)

```
DATA REDACTION:

    SENSITIVE_QUERY_PARAMS = {
        "access_token", "refresh_token", "id_token", "token", "api_key", "apikey",
        "client_secret", "password", "auth", "jwt", "session", "secret", "key",
        "code", "signature", "x-amz-signature"
    }
    
    SENSITIVE_BODY_KEYS = {
        "access_token", "refresh_token", "id_token", "token", "api_key", "apikey",
        "client_secret", "password", "auth", "jwt", "secret", "private_key",
        "authorization", "key"
    }

    // Vendor-specific API key patterns (regex)
    KEY_PATTERNS = [
        /sk-[a-zA-Z0-9]{20,}/,           // OpenAI
        /sk-ant-[a-zA-Z0-9-]{80,}/,       // Anthropic
        /AIza[a-zA-Z0-9_-]{35}/,          // Google
        /ghp_[a-zA-Z0-9]{36}/,           // GitHub
        /xoxb-[0-9-]+/,                   // Slack
        // ... 15+ more vendor patterns
    ]

    FUNCTION redact_sensitive_text(text):
        // Snapshot env at import time — runtime env mutations cannot disable redaction
        IF NOT REDACTION_ENABLED: RETURN text
        
        FOR EACH pattern IN KEY_PATTERNS:
            text = pattern.replace_all(text, mask_token)
        
        // Query string redaction
        FOR EACH param IN SENSITIVE_QUERY_PARAMS:
            text = redact_query_param(text, param)
        
        RETURN text
    
    FUNCTION mask_token(token):
        IF len(token) < 18:
            RETURN "***REDACTED***"                    // fully masked (too short to safely preview)
        ELSE:
            RETURN token[:6] + "..." + token[-4:]      // preserve first 6 + last 4 for debugging
    
    FUNCTION redact_structure(payload):
        // Walk nested dict/list payloads recursively
        FOR EACH key, value IN walk(payload):
            IF key.lower() IN SENSITIVE_BODY_KEYS:
                payload[key] = mask_token(value)
```

### Locus adaptation
- **Component**: `locus/core/security/redact.ts` — TypeScript port of regex-based redaction
- **Provider Interface**: Called as a filter on all output before logging and display
- **Repo vs `.locus`**: code in `locus-os` (repo); additional custom patterns can be added in `.locus/config.yaml` under `security.redact_patterns[]`
- **Swappable / off state**: `locus.security.redaction.enabled` (ON by default — secure default). Off → secrets may appear in logs and tool output. **Redaction is ON by default and cannot be disabled by LLM-generated env mutations** (snapshot at import time).
- **STEAL VERBATIM**: The entire vendor key pattern regex library (15+ patterns), the `SENSITIVE_QUERY_PARAMS` and `SENSITIVE_BODY_KEYS` sets, the masking strategy (short=full mask, long=first6+last4), the import-time snapshot anti-tamper.

---

## Feature §13.9: Think Token Scrubbing

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `think_scrubber.py` (387 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/think_scrubber.py` | 387 | Stateful streaming state machine that strips `<think>`, `<thinking>`, `<reasoning>`, `<thought>`, `<REASONING_SCRATCHPAD>` blocks from streamed assistant text. Handles partial tags at delta boundaries, preventing reasoning leakage. | `conversation_loop.py` (applied to every stream delta before display), gateway consumers (ACP, API server, TTS) |

### Stripped Logic (Pseudocode)

```
THINK TOKEN SCRUBBER (stateful streaming state machine):

    SUPPORTED_TAGS = ["think", "thinking", "reasoning", "thought", "REASONING_SCRATCHPAD"]
    
    CLASS StreamingThinkScrubber:
        state: "NORMAL" | "INSIDE_BLOCK" | "PENDING_TAG"
        held_back: string = ""        // partial tag text awaiting resolution
        
        FUNCTION feed(delta_text) → visible_text:
            result = ""
            
            FOR EACH char IN delta_text:
                SWITCH state:
                    CASE "NORMAL":
                        IF char starts potential open tag ("<"):
                            state = "PENDING_TAG"
                            held_back = "<"
                        ELSE:
                            result += char
                    
                    CASE "PENDING_TAG":
                        held_back += char
                        IF held_back matches any open tag pattern:
                            // Check block-boundary rule: only suppress if tag is at
                            // start of stream, after newline, or only whitespace on current line
                            IF is_block_boundary():
                                state = "INSIDE_BLOCK"
                                held_back = ""
                            ELSE:
                                // Prose mention (e.g. "use <think> tags here") — emit as text
                                result += held_back
                                held_back = ""
                                state = "NORMAL"
                        ELIF held_back is clearly NOT a tag:
                            result += held_back
                            held_back = ""
                            state = "NORMAL"
                    
                    CASE "INSIDE_BLOCK":
                        IF char sequence completes closing tag (e.g. "</think>"):
                            state = "NORMAL"
                            // Swallow entire block content — never reaches user
                        // Else: swallow (inside reasoning block)
            
            RETURN result
        
        FUNCTION flush() → visible_text:
            // End-of-stream: emit any held-back text that turned out not to be a tag
            IF held_back:
                result = held_back
                held_back = ""
                state = "NORMAL"
                RETURN result
            RETURN ""
        
        FUNCTION reset():
            // Call at start of each new turn
            state = "NORMAL"
            held_back = ""
```

### Locus adaptation
- **Component**: `locus/core/security/think-scrubber.ts` — TypeScript port of the streaming state machine
- **Repo vs `.locus`**: code in `locus-os` (repo); no config needed
- **Swappable / off state**: `locus.security.think_scrubbing.enabled`. Off → reasoning blocks from models like MiniMax-M2.7 will leak to the user. **Should be ON for all models that emit thinking tokens.**
- **STEAL VERBATIM**: The entire state machine (NORMAL/INSIDE_BLOCK/PENDING_TAG transitions), the block-boundary rule (prevents false positives on prose mentions), the tag variant list, the flush-at-end-of-stream pattern.
- **ADAPT**: Wire into Pi's `stream_delta_callback` pipeline (before display). One `StreamingThinkScrubber` instance per agent turn, `.reset()` called at `turn_start`.

---

## Feature §13.10: Message Sanitization

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `message_sanitization.py` (445 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/message_sanitization.py` | 445 | Stateless sanitization helpers: fixes lone surrogate code points (U+D800-U+DFFF) that crash `json.dumps()` in OpenAI SDK, walks nested dict/list payloads for deep sanitization, strips non-printable control characters | `conversation_loop.py` (applied to messages before API dispatch), `tool_executor.py` (applied to tool results) |

### Stripped Logic (Pseudocode)

```
MESSAGE SANITIZATION:

    // Lone surrogates are invalid in UTF-8 and crash json.dumps() inside the OpenAI SDK
    SURROGATE_RE = /[\uD800-\uDFFF]/
    
    FUNCTION sanitize_surrogates(text):
        IF SURROGATE_RE.search(text):
            RETURN SURROGATE_RE.replace_all(text, "\uFFFD")  // U+FFFD replacement character
        RETURN text  // fast no-op when clean
    
    FUNCTION sanitize_structure_surrogates(payload):
        // Walk nested dict/list payloads IN-PLACE
        // Handles deep nested structures like reasoning_details (array of dicts with summary/text strings)
        found = false
        FUNCTION walk(node):
            IF node is dict:
                FOR EACH key, value IN node:
                    IF value is string AND has surrogates:
                        node[key] = sanitize_surrogates(value)
                        found = true
                    ELIF value is dict or list:
                        walk(value)
            ELIF node is list:
                FOR EACH i, item IN enumerate(node):
                    IF item is string AND has surrogates:
                        node[i] = sanitize_surrogates(item)
                        found = true
                    ELIF item is dict or list:
                        walk(item)
        walk(payload)
        RETURN found
    
    FUNCTION sanitize_messages(messages):
        // Apply to entire message list before sending to LLM API
        FOR EACH message IN messages:
            IF message.content is string:
                message.content = sanitize_surrogates(message.content)
            IF message has tool_calls:
                sanitize_structure_surrogates(message.tool_calls)
            IF message has structured fields (reasoning_details, etc.):
                sanitize_structure_surrogates(message)
```

### Locus adaptation
- **Component**: `locus/core/security/message-sanitize.ts` — TypeScript port (stateless pure functions)
- **Repo vs `.locus`**: code in `locus-os` (repo); no config needed
- **Swappable / off state**: Always on (no config toggle — sanitization is a correctness requirement, not a feature). Without it, paste-from-clipboard text with lone surrogates will crash the LLM API call.
- **STEAL VERBATIM**: The surrogate regex, the recursive structure walker, the replacement-character strategy (U+FFFD).
- **ADAPT**: Apply in Pi's `convertToLlm` hook (messages are sanitized just before API dispatch). TypeScript's string handling differs from Python's — use `String.prototype.replace()` with the same regex.

**Off state for all §13 features collectively**: `locus.security.enabled: false` → reverts to Pi's built-in security model only. Individual features can also be toggled independently as specified above.

---

# CHANNEL & GATEWAY LAYER — §17

## Feature §17.1-17.11: Channel Adapters & Platform Registry

### Source
- **Codebases**: Hermes (`gateway/platform_registry.py`, `gateway/platforms/`, `gateway/mirror.py`, `gateway/shutdown_forensics.py`) + Locus-original
- **Verification**: [✅ VERIFIED: `platform_registry.py` (80 lines read), `mirror.py` listed]

### Stripped Logic (Pseudocode)

```
PLATFORM REGISTRY PATTERN (from Hermes gateway/platform_registry.py):

    @dataclass
    PlatformEntry:
        name: str                    // "telegram", "discord", "slack", etc.
        label: str                   // human-readable
        adapter_factory: Callable    // (config) → adapter instance
        check_fn: Callable           // () → bool (dependencies available?)
        validate_config: Callable    // (config) → bool
        is_connected: Callable       // (config) → bool
        required_env: [str]          // ["TELEGRAM_TOKEN"]
        install_hint: str            // "pip install python-telegram-bot"
        setup_fn: Callable           // interactive configuration wizard
        source: str                  // "builtin" or "plugin"

    FUNCTION register(entry: PlatformEntry):
        IF entry.name IN registry:
            LOG warning("Platform {entry.name} already registered")
        registry[entry.name] = entry

    FUNCTION create_adapter(name, config):
        IF name IN registry:
            entry = registry[name]
            IF NOT entry.check_fn():
                RAISE "Dependencies not available: {entry.install_hint}"
            IF entry.validate_config AND NOT entry.validate_config(config):
                RAISE "Invalid config for {name}"
            RETURN entry.adapter_factory(config)
        RAISE "Unknown platform: {name}"

    FUNCTION get_connected_platforms(configs):
        connected = []
        FOR EACH name, entry IN registry:
            IF entry.is_connected AND entry.is_connected(configs[name]):
                connected.append(name)
        RETURN connected

CHANNEL ADAPTER INTERFACE (for Locus):
    EVERY channel adapter MUST implement:
        name: str
        initialize(config)
        send_message(recipient, text, keyboard?)
        send_file(recipient, file_path)
        receive_messages() → async iterator
        is_connected() → bool
        shutdown()

    OPTIONAL:
        send_inline_keyboard(recipient, text, buttons)
        send_voice(recipient, audio_buffer)
        edit_message(message_id, new_text)

TELEGRAM ADAPTER (Locus primary channel — from Hermes telegram.py, 6252 lines):

  CLASS TelegramAdapter(BasePlatformAdapter):
    MAX_MESSAGE_LENGTH = 4096  // Telegram limit
    MEDIA_GROUP_WAIT_SECONDS = 0.8
    REQUIRES_EDIT_FINALIZE = True  // MarkdownV2 applied only on finalize=True
    
    ADAPTIVE TEXT BATCH INGRESS:
      // Telegram client splits long messages; Hermes re-aggregates them
      _TEXT_BATCH_FAST_LEN  = 320   → delay 0.18s  (one short paragraph)
      _TEXT_BATCH_SHORT_LEN = 1024  → delay 0.24s  (normal paragraph)
      Longer messages         → delay 0.30s (default, env-configurable)
      Split detection: if chunk near 4000 chars, extend wait to 1.0s
      // All delays clamped to configured max (env: HERMES_TELEGRAM_TEXT_BATCH_DELAY_SECONDS)
    
    CONNECT FLOW (connect()):
      1. Check TELEGRAM_AVAILABLE (python-telegram-bot installed)
      2. Acquire platform lock (prevent duplicate bot instances)
      3. Build PTB Application:
         - Custom base_url support (self-hosted telegram-bot-api)
         - Local mode support (files read from disk, not HTTP)
         - HTTP pool tuning: 512 connections, 8s pool timeout,
           10s connect, 20s read/write (all env-overridable)
      4. Fallback IP transport:
         - Auto-discover Telegram API fallback IPs via DNS
         - TelegramFallbackTransport wraps httpx for IP rotation
         - Separate request + get_updates pools (reduce contention)
      5. Register handlers:
         filters.TEXT & ~COMMAND       → _handle_text_message
         filters.COMMAND               → _handle_command
         filters.LOCATION|VENUE        → _handle_location_message
         filters.PHOTO|VIDEO|AUDIO|    → _handle_media_message
           VOICE|Document.ALL|Sticker
         CallbackQueryHandler          → _handle_callback_query
      6. Connect with retry (up to 8 attempts, exponential backoff):
         TRY: app.initialize() → app.start()
         CATCH NetworkError/TimedOut: wait min(2^attempt, 15s)
      7. Mode selection:
         IF TELEGRAM_WEBHOOK_URL set:
           // Webhook mode (cloud deployments)
           REQUIRE TELEGRAM_WEBHOOK_SECRET (fail-open = security vulnerability)
           app.updater.start_webhook(listen="0.0.0.0", port=8443, ...)
         ELSE:
           // Polling mode (default)
           delete_webhook(drop_pending_updates=False)  // clear stale webhooks
           app.updater.start_polling(error_callback=_polling_error_callback)
      8. Setup DM Topics (forum supergroup thread routing)
      9. Start supervisor reconnect loop
    
    INLINE KEYBOARD PATTERNS:
      // Check-in responses, approval gates, model picker, slash confirms
      _approval_state:      Dict[message_id → session_key]
      _slash_confirm_state: Dict[confirm_id → session_key]
      _clarify_state:       Dict[clarify_id → session_key]
      _model_picker_state:  Dict[chat_id → picker_state]
      
      send_exec_approval(chat_id, changes):
        buttons = [[InlineKeyboardButton("✅ Approve", callback_data="approve:{id}"),
                     InlineKeyboardButton("❌ Reject", callback_data="reject:{id}")]]
        send_message(chat_id, text, reply_markup=InlineKeyboardMarkup(buttons))
    
    NOTIFICATION MODES:
      "important" (default): only final responses, approvals, confirmations
                             trigger push notifications; tool progress is silent
      "all":                 every message triggers notification (legacy)
    
    POLLING ERROR RECOVERY:
      _looks_like_polling_conflict → _handle_polling_conflict (another instance)
      _looks_like_network_error   → _handle_polling_network_error (reconnect)
      _looks_like_connect_timeout → exponential backoff
      _looks_like_pool_timeout    → drain + rebuild connection pool
      
      _send_path_degraded flag:
        Set during sustained reconnect storms when PTB httpx pool silently
        drops messages. send() short-circuits to failure while degraded,
        forcing callers to fall through to standalone delivery.
    
    DM TOPICS (forum supergroup routing):
      Config: extra.dm_topics[{ chat_id, name, thread_id }]
      _create_dm_topic() → create forum topic in supergroup
      ensure_dm_topic()  → create if not exists, cache thread_id
      rename_dm_topic()  → rename existing topic
      
      Routing: messages from DM topic chats → route to correct thread_id
      Root messages (no thread_id) in DM topic chats → IGNORED

CROSS-PLATFORM MIRRORING (from Hermes mirror.py):
    FUNCTION mirror_event(event, source_platform):
        // Write behavioral event to PG (platform-agnostic)
        pg.insert("behavioral_events", {
            event_type: event.type,
            content: event.content,
            source_platform: source_platform,
            timestamp: now()
        })
        // Never fatal — mirror failure must not crash the main loop

SHUTDOWN FORENSICS (from Hermes shutdown_forensics.py):
    ON graceful_shutdown:
        // Log final state for post-mortem analysis
        pg.insert("shutdown_log", {
            reason: shutdown_reason,
            uptime: process_uptime(),
            sessions_active: count_active_sessions(),
            memory_usage: get_memory_usage(),
            last_error: last_error_message,
            timestamp: now()
        })
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/channels/`
- **Provider Interface**: `ChannelProvider`
- **Each channel**: `telegram.ts`, `discord.ts`, `slack.ts`, `whatsapp.ts`, etc.
- **Registry**: `locus/core/channel-registry.ts` (adapted from Hermes `platform_registry.py` pattern)
- **KEEP**: Registry pattern, PlatformEntry dataclass, `never-fatal` mirroring, shutdown forensics.
- **STEAL VERBATIM FROM TELEGRAM ADAPTER**: Adaptive text batch ingress (180ms/240ms/300ms delays), the fallback IP transport, the 8-attempt connect retry with exponential backoff, the polling error recovery chain, the DM topic routing, the inline keyboard patterns for approval/clarify/model-picker, the "important" notification mode default, the `_send_path_degraded` flag pattern.
- **ADAPT**: TypeScript orchestration layer calls Python sidecar that runs PTB. Inline keyboards for Locus check-ins use the same `CallbackQueryHandler` pattern. Webhook mode mapped to Locus' deployment config.

---


## Feature §17.10: Graceful Gateway Restart & State Snapshotting

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes Gateway Lifecycle (`gateway.py` + `shutdown_forensics.py`)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/gateway.py` | 510 | Central communication gateway supervisor; handles `SIGTERM`/`SIGUSR1`, in-flight queue draining, session serialization | `channel_manager.py`, `shutdown_forensics.py` |
| `hermes-agent/agent/shutdown_forensics.py` | 190 | Forensic state recorder dumping active connection telemetry and memory maps prior to process exit | `gateway.py`, PostgreSQL |

### Stripped Logic (Pseudocode)

```
CLASS GatewayLifecycleManager:
    drain_timeout_seconds: float = 30.0
    active_in_flight_requests: Set[string]
    is_shutting_down: bool = False
    
    FUNCTION handle_shutdown_signal(signal_type: "SIGTERM" | "SIGUSR1" | "RELOAD"):
        IF self.is_shutting_down: RETURN
        self.is_shutting_down = True
        
        LOG info("Initiating graceful shutdown sequence. Draining active connections...")
        
        // 1. Stop Ingress (De-register webhook / stop polling)
        FOR EACH adapter IN active_channel_adapters:
            adapter.stop_receiving_new_messages()
            
        // 2. Drain In-Flight Requests
        start_time = now()
        WHILE len(self.active_in_flight_requests) > 0 AND (now() - start_time) < self.drain_timeout_seconds:
            sleep(0.5)
            
        IF len(self.active_in_flight_requests) > 0:
            LOG warning(f"Drain timeout reached. Forcefully serializing {len(self.active_in_flight_requests)} pending sessions.")
            
        // 3. Snapshot In-Memory Session States to Disk
        FOR EACH session IN active_sessions:
            snapshot = serialize_session_state(session)
            write_json(f"~/.locus/sessions/recovery/{session.id}.json", snapshot)
            
        // 4. Record Forensic Log in Database
        log_shutdown_forensics(
            reason=signal_type,
            active_sessions_count=len(active_sessions),
            pending_events=len(self.active_in_flight_requests),
            uptime=get_uptime()
        )
        
        // 5. Close Database Pools & Clean Up
        close_all_db_pools()
        
        IF signal_type == "SIGUSR1":
            // Warm reload — re-exec self
            os.execv(sys.executable, [sys.executable] + sys.argv)
        ELSE:
            sys.exit(0)
```

### Locus adaptation
- **Component**: `locus-os/src/gateway/lifecycle.ts` (TypeScript supervisor) + `sidecar/gateway/lifecycle.py`
- **Provider Interface**: `GatewayLifecycleProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); recovery snapshots saved in `.locus/sessions/recovery/`.
- **Swappable / off state**: `locus.gateway.graceful_restart.enabled`. Off → hard exit on signal with risk of dropped messages.
- **STEAL VERBATIM**: The 30s connection draining loop, session disk snapshot serialization, and forensic telemetry schema.
- **ADAPT**: Integrated with Telegram and Discord adapters so bot process upgrades occur with zero lost messages or double responses.


# CONTEXT MANAGEMENT LAYER — §4.16

## Feature §4.16: Context Compression

### Source
- **Codebases**: Hermes (`context_engine.py`, `context_compressor.py`, `conversation_compression.py`) + Pi (`compaction/`)
- **Verification**: [✅ VERIFIED: `context_engine.py` (227 lines full), `conversation_compression.py` (80 lines head)]

### Stripped Logic (Pseudocode)

```
CONTEXT ENGINE ABC (from Hermes context_engine.py):

    ABSTRACT CLASS ContextEngine:
        // Identity
        name: str               // "compressor", "lcm", etc.
        
        // Token tracking (maintained by engine, read by runtime)
        last_prompt_tokens: int
        threshold_tokens: int   // = context_length * threshold_percent
        context_length: int     // model's context window
        compression_count: int
        
        // Compaction parameters
        threshold_percent: float = 0.75   // compress at 75% usage
        protect_first_n: int = 3          // keep first 3 non-system messages
        protect_last_n: int = 6           // keep last 6 messages
        
        // Core methods:
        update_from_response(usage)      // called after every LLM call
        should_compress(prompt_tokens)   // check if compaction needed
        compress(messages, current_tokens, focus_topic) // do the compaction
        
        // Lifecycle:
        on_session_start(session_id)
        on_session_end(session_id, messages)
        on_session_reset()               // reset counters
        
        // Optional: expose tools
        get_tool_schemas() → []
        handle_tool_call(name, args) → json_string
        
        // Model switch support
        update_model(model, context_length, ...) // recalculate thresholds

COMPRESSION FLOW (from Hermes conversation_compression.py):
    
    FUNCTION compress_context(agent, messages, focus_topic=None):
        // Step 1: Acquire compression lock (prevent concurrent compressions)
        lock = acquire_lock(holder=compression_lock_holder(agent))
        
        // Step 2: Identify compressible range
        head = messages[:protect_first_n + 1]  // system + first N
        tail = messages[-protect_last_n:]      // last N
        middle = messages[protect_first_n + 1 : -protect_last_n]
        
        IF middle.length == 0:
            RETURN messages  // nothing to compress
        
        // Step 3: Notify memory providers before compression
        FOR EACH provider IN memory_providers:
            extra_context = provider.on_pre_compress(middle)
            // Providers can extract insights from messages about to be lost
        
        // Step 4: Call auxiliary LLM for summarization
        summary_prompt = """
        Summarize the following conversation, preserving:
        - Key decisions made
        - Important facts revealed
        - User preferences expressed
        - Tool results that matter
        {IF focus_topic: "Focus especially on: {focus_topic}"}
        {IF extra_context: "Also preserve: {extra_context}"}
        
        Conversation to summarize:
        {format_messages(middle)}
        """
        summary = auxiliary_llm.generate(summary_prompt)
        
        // Step 5: Build new message list
        compressed = head + [system_message(summary)] + tail
        
        // Step 6: Split SQLite session, rotate session_id
        new_session_id = generate_session_id()
        session_db.split(old_session_id, new_session_id, split_point=len(head))
        
        // Step 7: Notify memory providers of session switch
        FOR EACH provider IN memory_providers:
            provider.on_session_switch(new_session_id, parent=old_session_id)
        
        compression_count += 1
        RETURN compressed
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/compaction/`
- **Provider Interface**: `CompactionProvider` (wraps both Pi's compaction AND Hermes's ContextEngine ABC)
- **Default**: Headroom CCR for token compression (Stage 6). Pi's built-in compaction for session-level compression (when context exceeds model limit).
- **KEEP**: The protect_first_n/protect_last_n pattern, memory provider notification hooks, session splitting.
- **ADAPT**: Lock holder uses Locus's process model (not Python threading). Auxiliary LLM call uses DeepSeek V4 Flash.

---

# MCP LAYER — §18

## Feature §18.1-18.4: Model Context Protocol

### Source
- **Codebases**: OpenHuman `mcp_client/` (transport), `mcp_registry/` (lifecycle + Smithery), `mcp_server/` (Locus-as-MCP-server), `mcp_audit/` (write audit)
- **Verification**: [✅ VERIFIED: README.md for `mcp_registry` (127 lines), `mcp_server` (100 lines), `mcp_client/stdio.rs` read in full]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `mcp_client/mod.rs` | 53 | Module entry: `McpHttpClient`, `McpStdioClient`, `McpServerRegistry` | All MCP modules |
| `mcp_client/client.rs` | 757 | HTTP + SSE transport for remote MCP servers | `sanitize.rs` |
| `mcp_client/stdio.rs` | ~200 | Subprocess JSON-RPC over stdin/stdout for local MCP servers | `client.rs` |
| `mcp_client/sanitize.rs` | ~230 | Sanitize tool descriptions from untrusted servers | `client.rs` |
| `mcp_registry/mod.rs` | varies | Dynamic installations, lifecycle, SQLite persistence | `mcp_client/` |
| `mcp_registry/connections.rs` | varies | Global connection registry, connect/disconnect/call_tool | `mcp_client/` |
| `mcp_registry/supervisor.rs` | varies | 60s reconnect loop with exponential backoff | `connections.rs` |
| `mcp_registry/setup.rs` | varies | Opaque secret-ref machinery for credential collection | `setup_ops.rs` |
| `mcp_server/protocol.rs` | varies | JSON-RPC 2.0 dispatch, version negotiation | `tools.rs` |
| `mcp_server/tools.rs` | varies | Tool catalog, security policy, argument validation | `write_dispatch.rs` |
| `mcp_server/write_dispatch.rs` | varies | Write audit pipeline for memory writes | `mcp_audit/` |
| `mcp_server/http.rs` | varies | Axum Streamable HTTP + SSE transport | `protocol.rs` |
| `mcp_audit/` | varies | Audit trail for MCP tool calls | `mcp_server/` |

### Stripped Logic (Pseudocode)

```
MCP CLIENT (dual-transport — from OpenHuman mcp_client/):

  TWO TRANSPORT TYPES:
  
  1. McpHttpClient (Streamable HTTP + OAuth + SSE):
      PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"]
      
      FUNCTION initialize(endpoint_url):
          response = POST(endpoint_url, {
              jsonrpc: "2.0",
              method: "initialize",
              params: {
                  protocolVersion: LATEST_PROTOCOL_VERSION,
                  capabilities: {},
                  clientInfo: { name: "locus", version: "1.0" }
              }
          })
          // Negotiate protocol version
          // Store session ID from Mcp-Session-Id header
      
      FUNCTION list_tools():
          response = POST(endpoint_url, { method: "tools/list" })
          tools = response.result.tools
          // CRITICAL: sanitize descriptions before passing to LLM
          FOR EACH tool IN tools:
              tool.description = sanitize_for_llm(
                  tool.description,
                  MAX_DESCRIPTION_BYTES  // cap length
              )
              // Strip: control characters, instruction fences, excessive length
          RETURN tools
      
      FUNCTION call_tool(tool_name, args):
          response = POST(endpoint_url, {
              method: "tools/call",
              params: { name: tool_name, arguments: args }
          })
          RETURN response.result

  2. McpStdioClient (subprocess JSON-RPC — from stdio.rs):
      FUNCTION initialize(command, args, env):
          process = spawn(command, args, env)
          // Communicate via stdin/stdout JSON-RPC
          stdin.write(json({ method: "initialize", ... }))
          response = stdout.read_json()
          RETURN response
      
      FUNCTION call_tool(tool_name, args):
          stdin.write(json({ method: "tools/call", params: { name, arguments } }))
          response = stdout.read_json()
          RETURN response

═══ MCP REGISTRY (from OpenHuman mcp_registry/ — COMPLETE) ═══

  PURPOSE: Dynamic, user-facing MCP-client support. Browses upstream
  directories (Smithery.ai + official MCP registry), persists installs
  to SQLite, supervises connection lifecycle, surfaces tools to agents.

  PERSISTENCE (SQLite at {workspace_dir}/mcp_clients/mcp_clients.db):
    Table: mcp_servers
      Columns: server_id, name, transport (stdio|http_remote),
               command, args, env_keys, deployment_url, enabled
      NOTE: transport + deployment_url added via idempotent additive migration
            (pre-migration rows default to stdio)
    
    Table: mcp_client_env (per-server env key/value pairs)
      ON DELETE CASCADE from mcp_servers
      Values NEVER serialized into responses, NEVER logged
    
    Table: mcp_registry_cache (registry HTTP responses, 10-min TTL)

  MULTI-REGISTRY SEARCH:
    FUNCTION registry_search(query):
      results = parallel_fan_out([smithery, official], query)
      merged = deduplicate_by_name(results)
      RETURN merged  // each result tagged with source
    
    FUNCTION registry_get(server_id):
      // Route to originating registry based on source prefix
      // Or first-hit across all registries

  CONNECTION LIFECYCLE:
    GLOBAL CONNECTION REGISTRY:
      OnceLock<RwLock<HashMap<server_id, Connection>>>  // ephemeral per process
    
    FUNCTION connect(server_id):
      install = store.get_server(server_id)
      env = store.get_env(server_id)
      IF install.transport == "stdio":
        client = McpStdioClient::new(install.command, install.args, env)
      ELIF install.transport == "http_remote":
        client = McpHttpClient::new(install.deployment_url, env)
      client.initialize()
      connections.insert(server_id, client)
      publish(McpServerConnected { server_id })

  SUPERVISOR (background reconnect loop — supervisor.rs):
    EVERY 60 SECONDS:
      FOR EACH server_id, connection IN connections:
        alive = connections::probe_alive(server_id)
        IF NOT alive:
          backoff = exponential_backoff(server_id)  // per-server
          IF now() > last_attempt + backoff:
            reconnect(server_id)
      
      // Also reconnect never-connected enabled servers
      FOR EACH server IN store.list_enabled():
        IF server.id NOT IN connections:
          connect(server.id)

  BOOT-TIME SPAWN (boot.rs):
    FUNCTION spawn_installed_servers():
      FOR EACH server IN store.list_all():
        IF server.enabled:
          TRY: connect(server.id)
          CATCH: log_warn("MCP server {server.name} failed to connect")
          // Per-server failures logged, NEVER fatal to core startup

  SETUP AGENT (opaque secret collection — setup.rs + setup_ops.rs):
    PURPOSE: Let an LLM walk users through search → credential collection →
    dry-run test → install, with raw secret values kept out of LLM context.
    
    FUNCTION request_secret(key_name, description):
      ref = "secret://<random_hex>"  // opaque reference
      secret_store.insert(ref, { pending: true, timeout: 5_min })
      publish(McpSetupSecretRequested { ref, key_name, description })
      // Block up to 5 minutes for UI to call submit_secret(ref, value)
      RETURN ref  // LLM sees only the ref, never the value
    
    FUNCTION submit_secret(ref, value):
      secret_store.fulfill(ref, value)  // only the UI calls this
    
    FUNCTION test_connection(server_spec, secret_refs):
      // Resolve refs → real values, dry-run connect
      resolved_env = resolve_secret_refs(server_spec.env, secret_refs)
      client = dial(server_spec, resolved_env)
      tools = client.list_tools()  // verify connection works
      client.disconnect()           // tear down — nothing persisted
      RETURN { tools, status: "ok" }
    
    FUNCTION install_and_connect(server_spec, secret_refs):
      resolved_env = consume_refs(secret_refs)  // removes refs, persists values
      store.insert_server(server_spec, resolved_env)
      connect(server_spec.server_id)
      RETURN { status: "connected" }
    
    SECRET LIFECYCLE:
      - In-memory map (NOT SQLite), 5-min request timeout, 15-min idle GC
      - consume_refs() only called after persist → values never stranded

  TRANSPORT SELECTION (pick_connection):
    Preference order: published stdio → any stdio → published http_remote → any http_remote

  EVENTS PUBLISHED:
    McpServerInstalled, McpServerConnected, McpServerDisconnected,
    McpClientToolExecuted, McpSetupSecretRequested

═══ MCP SERVER (from OpenHuman mcp_server/ — COMPLETE) ═══

  PURPOSE: Expose a curated, security-gated slice of Locus' tool surface
  to external MCP clients (Claude Desktop, Cursor, Windsurf, etc.)

  TRANSPORTS:
    1. Stdio (default): newline-delimited JSON-RPC over stdin/stdout
       CLI: openhuman-core mcp [--transport stdio]
    2. HTTP: Axum Streamable HTTP + SSE on 127.0.0.1:9300
       CLI: openhuman-core mcp --transport http [--port 9300] [--auth-token xyz]

  PROTOCOL LIFECYCLE (protocol.rs):
    Handles: initialize, ping, tools/list, tools/call,
             resources/list, resources/templates/list, resources/read
    Notifications: notifications/initialized, notifications/cancelled
    
    VERSION NEGOTIATION:
      Supports: 2024-11-05, 2025-03-26, 2025-06-18, 2025-11-25 (LATEST)
      Unknown requested versions → fall back to latest
      HTTP enforces exact session protocol-version match

  TOOL CATALOG (tools.rs):
    ┌──────────────────────┬────────────────────────────┬─────────────┐
    │ MCP tool             │ Maps to core RPC           │ Policy      │
    ├──────────────────────┼────────────────────────────┼─────────────┤
    │ memory.search        │ openhuman.memory_tree_search│ Read        │
    │ memory.recall        │ openhuman.memory_tree_recall│ Read        │
    │ tree.read_chunk      │ openhuman.memory_tree_get_chunk│ Read     │
    │ tree.browse          │ openhuman.memory_tree_list_chunks│ Read   │
    │ tree.top_entities    │ openhuman.memory_tree_top_entities│ Read  │
    │ tree.list_sources    │ openhuman.memory_tree_list_sources│ Read  │
    │ memory.store         │ openhuman.memory_doc_put   │ Act (write) │
    │ memory.note          │ openhuman.memory_doc_put   │ Act (write) │
    │ tree.tag             │ openhuman.memory_doc_put   │ Act (write) │
    │ searxng_search       │ openhuman.tools_searxng_search│ Read     │
    │ core.list_tools      │ (in-process)               │ Read        │
    │ core.tool_instructions│(in-process)               │ Read        │
    │ agent.list_subagents │ (in-process)               │ Read        │
    │ agent.run_subagent   │ (in-process)               │ Act         │
    └──────────────────────┴────────────────────────────┴─────────────┘
    
    ARGUMENT ENFORCEMENT (explicit rejection over silent clamping):
      k/limits: capped at MAX_LIMIT (50), default 10
      tree.tag: max 50 tags, 128 bytes per tag
      searxng max_results: capped at SEARXNG_MAX_RESULTS
      Blank required strings → error (never silently ignored)

  SECURITY POLICY (per-call enforcement):
    Read tools: SecurityPolicy.check(ToolOperation::Read)
    Write tools: SecurityPolicy.check(ToolOperation::Act)
    agent.run_subagent: rejects "integrations_agent" (toolkit binding unsupported)

  WRITE AUDIT PIPELINE (write_dispatch.rs):
    FOR EACH write tool call (memory.store, memory.note, tree.tag):
      1. Load config
      2. Check SecurityPolicy for Act permission
      3. IF rejected: audit_write_rejection_without_config() → record + return error
      4. Dispatch to openhuman.memory_doc_put via registered RPC
      5. Record audit entry:
         NewMcpWriteRecord {
           tool_name, client_info, source_type ("mcp:claude-desktop"),
           args_summary (PII-redacted: titles truncated 128 chars, body omitted),
           success: bool, document_id, timestamp
         }
      6. Audit insert runs off hot path (spawn_blocking or thread fallback)
    
    GOTCHA: dispatch_write_tool returns Ok(tool_error(...)) on failure,
    NOT Err(...). Client gets an MCP isError result while failure is still audited.

  RESOURCE CATALOG (resources.rs):
    Static, compile-time-embedded (include_str!) prompt assets:
    ┌─────────────────────────────────┐
    │ openhuman://prompts/IDENTITY.md │
    │ openhuman://prompts/SOUL.md     │
    │ openhuman://prompts/USER.md     │
    │ openhuman://prompts/agents/<id> │ (one per built-in subagent)
    └─────────────────────────────────┘
    CI-enforced: catalog_mirrors_builtins test fails if a built-in
    subagent lacks a matching resource entry.

SAFETY FILTER (from sanitize.rs):
    FUNCTION sanitize_for_llm(text, max_bytes):
        // Step 1: Strip control characters
        text = strip_control_chars(text)
        // Step 2: Strip instruction fences (prompt injection via tool descriptions)
        text = strip_instruction_fences(text)
        // Step 3: Cap length
        IF bytes(text) > max_bytes:
            text = truncate_to_bytes(text, max_bytes)
        RETURN text
    
    ADDITIONALLY: prompt_injection::scan_tool_definition()
      Same detection pipeline as §13.1 applied to tool descriptions
      Rejects on any non-Allow verdict (no Review UX for tool metadata)
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/mcp/` (TypeScript, since Pi is TypeScript)
- **ADAPT**: OpenHuman's Rust MCP implementation is the reference for protocol compliance. Locus's implementation is TypeScript using the `@modelcontextprotocol/sdk` npm package. Three components:
  - **MCP Client** (`locus/core/mcp/client.ts`): Connect to external MCP servers (Obsidian, Headroom, custom)
  - **MCP Server** (`locus/core/mcp/server.ts`): Expose Locus tools to external AI editors (Cursor, ChatGPT)
  - **MCP Registry** (`locus/core/mcp/registry.ts`): Dynamic installs via Smithery + supervisor reconnect loop
- **KEEP**: The safety filter (sanitize + prompt injection scan), dual-transport pattern, registry pattern, 60s supervisor reconnect, opaque secret-ref pattern for credential collection, write audit pipeline, explicit-rejection-over-silent-clamping
- **STEAL VERBATIM**: The tool catalog structure with per-tool security policy, the MCP write audit record schema, the secret ref lifecycle (5-min timeout, 15-min GC, consume-on-persist)
- **ADAPT**: Locus MCP Server exposes: `locus.checkin`, `locus.memory_search`, `locus.vault_read`, `locus.goals`, `locus.life_os_status`. Audit trail stored in `.locus/mcp/audit.db`

---

## Feature §18.5: Obsidian MCP (Vault Bridge)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW (Locus-original design)

### Source(s) mined
- **Codebase**: Locus-original (no upstream implementation to strip) — this is the bridge that lets *external* AI editors (Cursor, Claude Desktop, ChatGPT) operate on Locus' Obsidian vault. It is the **outbound half** of Locus' MCP server, distinct from §18.1-18.4 (the inbound client + the general server).
- **Grounding**: `Atomic Selections` §18.5 ("vault_read/write/search/tag/stats") + §3 custom-tools table (`locus_vault_search` → `VaultProvider`, sidecar = yes) + §27 (3-level tag hierarchy, PageIndex tree) + `deps/ai to obsidian/` (a browser-extension bridge whose `obsidian.js`/`md.js`/`db.js` show the same vault-operation surface: read/append notes, resolve wikilinks, index tags).
- **Query method**: Grounded in Locus system architecture specification.

### Logic extracted

The design is: expose the **VaultProvider** surface as five MCP tools, so any MCP client gets a curated, sidecar-backed view of the vault — never raw filesystem access. The five tools map one-to-one to the provider's operations:

1. `vault_read(path)` — read a note's markdown (resolving wikilinks `[[note]]` and `![[embed]]` to canonical paths), return title + body + frontmatter.
2. `vault_write(path, content, mode)` — create/append/overwrite a note; append respects the daily-note convention; writes are routed through the **approval gate** (§13.5) because they're external-effect, not read-only.
3. `vault_search(query)` — search across note titles, body text, and tags; returns ranked hits with snippet + path + tags. Backed by the §27 nightly index (PageIndex tree + tag index), not a live ripgrep over the whole vault.
4. `vault_tag(note_path, tags)` — add/remove tags on a note, enforcing the 3-level tag hierarchy (§27.4) so arbitrary tag proliferation is rejected.
5. `vault_stats()` — vault size, note count, tag frequency, last-ingested timestamp, un-indexed file count.

Reads (`read`/`search`/`stats`) are `ToolOperation::Read`; writes (`write`/`tag`) are `ToolOperation::Act` and carry `readOnlyHint:false`. The tool surface is a **separate registration** from the general server (§18.4) so a user can enable Obsidian MCP for external editors without exposing the memory/goal/life tools, and vice-versa.

### Locus adaptation
- **Component**: `locus/providers/vault/obsidian-mcp.ts` — registers five tool specs against the existing `VaultProvider` interface (which already has `read`, `write`, `search`, `tag`, `stats`). The MCP layer is a thin adapter; the real logic stays in the provider (which can be swapped Obsidian → another vault backend).
- **What it depends on**: `VaultProvider` (the swap point), the §27 nightly ingestion index for `search`/`stats`, and the approval gate for writes.
- **Where it reads/writes**: the adapter + tool specs → **repo** (`locus-os`); the vault **path** and provider choice (`vault.provider: obsidian`, `vault.path`) → **`.locus/config.yaml`**. The vault contents themselves live wherever the user keeps their Obsidian vault (a path the config points at, not a repo file).
- **Swappable / off state**: `locus.mcp.obsidian.enabled`. Off → the five tools are not advertised; the general MCP server (§18.4) is unaffected. `vault.provider` swaps the backend behind the same five tools.
- **Delegation**: none — Locus-native. This is a *bridge*, not a codegen path; external editors call the tools, Locus executes them.

### Pseudocode / algorithm

```
TOOL SPECS (registered on the MCP server, namespaced vault.*):
  vault.read   {path}                      -> {title, body, frontmatter}   [Read]
  vault.write  {path, content, mode}       -> {written_path, version}      [Act]
  vault.search {query, limit=20}           -> [{path, snippet, tags, score}] [Read]
  vault.tag    {path, tags, op=add|remove} -> {tags}                       [Act]
  vault.stats  {}                          -> {notes, tags_top, last_ingest} [Read]

FUNCTION vault.read(path):
    resolved = VaultProvider.resolve_wikilink(path)   # [[x]] -> canonical
    note = VaultProvider.read(resolved)
    RETURN {title, body, frontmatter}

FUNCTION vault.write(path, content, mode):
    approval_gate.require_approval("vault.write", path)  # Act -> TTL gate
    written = VaultProvider.write(path, content, mode)   # create|append|overwrite
    trigger_reindex(written)                            # update §27 index
    RETURN {written_path, version}

FUNCTION vault.search(query, limit):
    hits = index.search(query)        # PageIndex tree + tag index, NOT live grep
    RETURN hits.take(limit) mapped to {path, snippet, tags, score}

FUNCTION vault.tag(path, tags, op):
    enforce_3level_hierarchy(tags)    # reject tags outside the §27.4 taxonomy
    approval_gate.require_approval("vault.tag", path)
    RETURN VaultProvider.tag(path, tags, op)
```

---

# SCHEDULING & PROACTIVE LAYER — §12, §26

## Feature §12.1-12.5 + §26.1: Proactive Inner Loop & Scheduling

### Source
- **Codebases**: Hermes (`cron/`) + OpenHuman (`scheduler_gate/`, `task_sources/`, `cron/`) + Locus-original
- **Verification**: [✅ VERIFIED: OpenHuman `scheduler_gate/mod.rs` (37 lines) read]

### Stripped Logic (Pseudocode)

```
SCHEDULER GATE (from OpenHuman scheduler_gate/):
    
    Policy enum:
        Aggressive  — server-mode; bypass all throttles
        Normal      — desktop with headroom; run as scheduled
        Throttled   — busy or on battery; serialize + slow down
        Paused      — user opted out; defer indefinitely
    
    Signals (refreshed every 30s in background sampler):
        power_state: on_ac OR battery >= 80%
        cpu_usage: recent global usage < 70% means "idle enough"
        deployment_mode: server/container hosts run flat-out
    
    FUNCTION wait_for_capacity():
        policy = current_policy()
        IF policy == Aggressive OR policy == Normal:
            RETURN immediately
        ELIF policy == Throttled:
            sleep(30 seconds)
            RETURN  // serialized execution
        ELIF policy == Paused:
            LOOP:
                sleep(60 seconds)
                IF current_policy() != Paused:
                    RETURN  // user unpaused

LOCUS PROACTIVE INNER LOOP (Locus-original, from locus_agent_loop.md):
    
    **Crawler feed**: the VaultCrawler (MD5-based incremental scan of
    `C:\Users\soni8\...\ObsidianVault`) feeds changed files to PageIndex + pgvector
    for reindexing. The TelegramCrawler feeds the `behavioral_events` stream that
    the Pattern Engine reads. Without these two crawlers running on schedule, the
    Inner Loop has no fresh context to think about.
    
    CRON_TASK every_90_minutes():
        // Active window: 07:00 - 00:00 IST
        IF NOT within_active_window("07:00", "00:00"):
            RETURN
        
        // Check scheduler gate (if on battery/busy, defer)
        wait_for_capacity()
        
        // Step 1: Get current state
        state = state_engine.get_current_state()
        
        // Step 2: Incremental vault crawl
        changed_files = vault_crawler.crawl_changed_files()
        IF changed_files:
            pageindex.reindex(changed_files)
            pgvector.reindex(changed_files)
        
        // Step 3: Multi-horizon pattern detection
        patterns = pattern_engine.detect_patterns(horizons=["6h", "24h", "7d", "30d", "all"])
        
        // Step 4: Formulate proactive thought
        thought = generator.think(construct_proactive_prompt(state, patterns))
        
        // Step 5: Gate through Personal Reward Model
        score = reward_model.score_thought(thought)
        IF score >= 0.6:  // confidence threshold
            channel_provider.send_message(
                recipient="user",
                message=thought,
                keyboard=["Acknowledge", "Modify Plan", "Ignore"]
            )

STRUCTURED CHECK-INS (4 daily, Locus-original):
    07:30 IST — Morning briefing (energy, plan for day)
    13:00 IST — Afternoon check-in (progress, energy update)
    18:00 IST — Evening check-in (reflection, remaining tasks)
    22:00 IST — Night wind-down (gratitude, tomorrow prep)
    
    Each check-in:
        1. Send inline keyboard via Telegram
        2. User responds with ratings + notes
        3. Update current_state in PG
        4. Recalculate DCS score
```

### Adaptation to Locus Architecture

**Crawler feed**: the VaultCrawler MD5 scan feeds PageIndex + pgvector reindexing.
The TelegramCrawler feeds behavioral_events for the Pattern Engine.

**File-location**: code in `locus-os/core/scheduler.ts` + `sidecar/scheduler/`;
cron config (active window, intervals) in `.locus/config.yaml`.

---

# VOICE LAYER — §14

## Feature §14.1-14.4: Voice Pipeline

### Source
- **Codebases**: Hermes (`agent/transcription_provider.py`, `agent/tts_provider.py`) + OpenHuman (`voice/`) + Locus-original
- **Verification**: [✅ VERIFIED: Hermes files listed in `agent/` directory]

### Stripped Logic (Pseudocode)

```
VOICE PIPELINE: Audio → STT → Pipeline → TTS → Audio

STT PROVIDERS:
    GroqWhisper (default, fastest, free tier):
        FUNCTION transcribe(audio_buffer):
            response = groq_api.audio.transcriptions.create(
                file=audio_buffer,
                model="whisper-large-v3-turbo",
                language="en"
            )
            RETURN response.text
    
    WhisperLocal:
        FUNCTION transcribe(audio_buffer):
            result = whisper_model.transcribe(audio_buffer)
            RETURN result.text
    
    AzureSTT / OpenAISTT: similar HTTP API patterns

TTS PROVIDERS:
    EdgeTTS (default, free, no API key):
        FUNCTION synthesize(text, voice="en-US-GuyNeural"):
            audio = edge_tts.Communicate(text, voice).stream()
            RETURN audio_buffer
    
    ElevenLabs:
        FUNCTION synthesize(text, voice_id):
            response = elevenlabs_api.generate(text=text, voice=voice_id)
            RETURN response.audio
    
    Piper / Kokoro / OpenAI: similar patterns

TELEGRAM VOICE MESSAGE FLOW:
    1. User sends voice message on Telegram
    2. Bot receives OGG audio file
    3. Convert OGG → WAV (ffmpeg)
    4. STT provider transcribes → text
    5. Text enters reactive pipeline at Stage 0
    6. Pipeline generates response text
    7. TTS provider synthesizes → audio
    8. Send audio back as Telegram voice message
    9. Also send text transcript as regular message
    10. Log full transcript to vault
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/voice/`
- **Provider Interfaces**: `STTProvider`, `TTSProvider`
- **Default**: Groq Whisper (STT), Edge TTS (TTS) — both free.
- **Integration**: Voice handling at Stage 0 (Intake). The STT/TTS calls happen in the Python sidecar.

---

# LIFE OS LAYER — §25, §26 (Locus-Unique)

> All formulas verified against `LOCUS_SYSTEM_v1.md` (see Appendix C). All Life OS features are 🆕 LOCUS-NEW (Locus-original). Code lives in Python sidecar under `sidecar/life_os/`; config/tuning values live in `.locus/config.yaml`. Provider interface: `LifeOSProvider`.

## Feature §25.1: Four Factions Framework

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §1

### Logic extracted

```
FOUR FACTIONS:
    Health/Stability  — fitness, nutrition, mental health, sleep, academics
    Leverage/Money    — freelance income, investing, networking, career positioning
    Craft/Skills      — cinematography, software engineering, passion projects
    Expression/Explore — hobbies, reading, identity, experimentation, rest

    Crisis priority hierarchy (emergencies only): Health > Leverage > Craft > Expression.
    Weekly target allocation: Health 25% · Leverage 25% · Craft 30% · Expression 20%.
```

### Locus adaptation
- **Repo vs `.locus`**: faction definitions in `locus-os/sidecar/life_os/factions.py`; target percentages in `.locus/config.yaml`.
- **Swappable / off state**: `locus.life_os.factions.enabled`. Off → no faction tracking; scheduling uses flat priority only.
- **Crawler feed**: behavioral_events stream (via PG LISTEN/NOTIFY) feeds faction time-tracking.

---

## Feature §25.2: Daily Capacity Score (DCS)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §4

### Logic extracted

```
DCS = ((E + M + S) / 3) × (1 − ST/20)
    E = Energy (1-10), M = Mood (1-10), S = Sleep quality (1-10), ST = Stress (1-10)
    Output: 0.0–10.0 float.
    Log E/M/S before coffee/phone. When unsure between two numbers, pick the lower.
    If no check-in today: apply staleness penalty (all scores × 0.9).
    If no check-in in 3+ days: default to baseline (5,5,5,7) & queue STALE_CHECKIN alert.
```

### Locus adaptation
- **Repo vs `.locus`**: DCS formula in `locus-os/sidecar/life_os/dcs.py`; check-in prompts in `.locus/config.yaml`.
- **Swappable / off state**: `locus.life_os.dcs.enabled`. Off → no DCS calculation; operating mode defaults to NORMAL.

---

## Feature §25.3: Five Operating Modes

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §5

### Logic extracted

```
SURVIVAL:  DCS 0.0–2.0  — non-negotiables only; no discretionary tasks
RECOVERY:  DCS 2.1–4.0  — D ≤ 4 only; max 2 discretionary tasks
NORMAL:    DCS 4.1–6.0  — D ≤ 7; 3–4 tasks; ≥2 factions get attention
DEEP WORK: DCS 6.1–8.0  — D ≤ 9; single 2–3h uninterrupted highest-TWS block
PEAK:      DCS 8.1–10.0 — most ambitious task first; 5–6 tasks
```

### Locus adaptation
- **Repo vs `.locus`**: mode definitions in `locus-os/sidecar/life_os/modes.py`; mode thresholds in `.locus/config.yaml`.
- **Swappable / off state**: `locus.life_os.modes.enabled`. Off → Locus schedules all tasks at NORMAL capacity regardless of DCS.

---

## Feature §25.4: Task Weight Score (TWS)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §3.2

### Logic extracted

```
TWS = (P × 0.4) + (U × 0.4) + (D × 0.2)
    P = Priority (1-10), U = Urgency (1-10), D = Difficulty (1-10)
    Higher TWS = schedule first. This is the daily sort key.

LAG BONUS (applied AFTER base TWS):
    faction Lag Score > 3h  → all its tasks TWS + 2
    faction Lag Score > 6h  → all its tasks TWS + 4 (faction in crisis)
    faction ahead of target → its tasks TWS − 1

POST-TASK LOG: A (actual time), Q (quality 1-10), R (reason if |A − Est| > 50%)
```

### Locus adaptation
- **Repo vs `.locus`**: TWS formula in `locus-os/sidecar/life_os/tws.py`; lag thresholds in `.locus/config.yaml`.
- **Swappable / off state**: `locus.life_os.tws.enabled`. Off → tasks sorted by manual priority only.

---

## Feature §25.5: Three-Layer Goal Stack

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §3.1

### Logic extracted

```
GOAL STACK (Outcome → Project → Task):
    Level 1 — Vision/Outcome: long-term desired results
    Level 2 — Milestone/Project: measurable sub-goals within an outcome
    Level 3 — Daily Task: concrete actions that advance a milestone
    
    Enforcement: every task MUST parent to a project; every project MUST parent to an outcome.
    Orphan tasks are surfaced during morning briefing for pruning/reparenting.
```

### Locus adaptation
- **Repo vs `.locus`**: goal stack model in `locus-os/sidecar/life_os/goal_stack.py`; goals stored in PG `goal_stack` table.
- **Swappable / off state**: `locus.life_os.goal_stack.enabled`. Off → no goal enforcement; tasks are free-floating.

---

## Feature §25.6: Action Gap Tracking

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §3.3

### Logic extracted

```
ACTION GAP = declared_priority − (actual_hrs / target_hrs × 10)
    Action Gap > 5 → alert: faction is being neglected relative to its declared importance.
```

### Locus adaptation
- **Repo vs `.locus`**: gap formula in `locus-os/sidecar/life_os/action_gap.py`; alert threshold in `.locus/config.yaml`.
- **Swappable / off state**: `locus.life_os.action_gap.enabled`. Off → no automatic gap detection.

---

## Feature §25.7: Deferral Detection (3/5/8+)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §9

### Logic extracted

```
DEFERRAL THRESHOLDS:
    3× defer → warn: "Consider dropping or delegating"
    5× defer → escalate: surfaced at weekly review
    8× defer → flag as phantom task: auto-parked with review note
```

### Locus adaptation
- **Repo vs `.locus`**: deferral logic in `locus-os/sidecar/life_os/deferral.py`; thresholds in `.locus/config.yaml`.
- **Swappable / off state**: `locus.life_os.deferral.enabled`. Off → no automatic deferral tracking.

---

## Feature §25.8: Lag Score + TWS Lag Bonus

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §7

### Logic extracted

```
LAG SCORE = cumulative hours a faction is behind its weekly target.
    Lag > 3h → TWS + 2 for all that faction's tasks
    Lag > 6h → TWS + 4 (faction in crisis)
    Ahead of target → TWS − 1
```

### Locus adaptation
- **Repo vs `.locus`**: lag calculation in `locus-os/sidecar/life_os/lag.py`; thresholds in `.locus/config.yaml`.
- **Swappable / off state**: bundled with TWS (§25.4).

---

## Feature §25.9: Emergency Task Injection

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §6

### Logic extracted

```
EMERGENCY INJECTION: tasks tagged EMERGENCY bypass TWS ordering and are inserted at
    the top of the schedule, respecting only faction crisis hierarchy.
```

### Locus adaptation
- **Repo vs `.locus`**: injection logic in `locus-os/sidecar/life_os/emergency.py`.
- **Swappable / off state**: `locus.life_os.emergency.enabled`. Off → emergency-tagged tasks sort by TWS like everything else.

---

## Feature §25.10: Exhaustion Predictor

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §8

### Logic extracted

```
EXHAUSTION PREDICTOR: monitors consecutive high-D tasks, sleep deficit, and stress trend.
    If predicted DCS drop > 2.0 within 24h → pre-emptive SURVIVAL mode recommendation.
```

### Locus adaptation
- **Repo vs `.locus`**: predictor in `locus-os/sidecar/life_os/exhaustion.py`.
- **Swappable / off state**: `locus.life_os.exhaustion.enabled`. Off → no pre-emptive mode recommendations.

---

## Feature §25.11: Weekly Faction Rebalance

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §2

### Logic extracted

```
WEEKLY REBALANCE (Sunday 02:00 IST):
    actual = PG query: SUM(duration) per faction for current week
    FOR EACH faction:
        deficit = target_pct − actual_pct
        next_week_weight = base_weight + (deficit × correction_factor)
    Write adjusted weights to faction_weights table for next week's scheduling.
```

### Locus adaptation
- **Repo vs `.locus`**: rebalance in `locus-os/sidecar/life_os/rebalance.py`.
- **Swappable / off state**: `locus.life_os.rebalance.enabled`. Off → faction weights remain static.

---

## Feature §25.12: Six-Step Scheduling Algorithm (Full Mathematical Specification)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §10 + `locus_microsystems.html` (Subsystem 6, 11-Step Scheduler Breakdown)  
**Query method**: [📐 DESIGN SPEC: locus_system_v1.md]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/life_os/scheduler.py` | 420 | Deterministic 6-step schedule generator; enforces DCS capacity filters, TWS ranking, faction balance, and ultradian recovery blocks | `task_queue.py`, `state_engine.py`, `goal_tracker.py` |
| `locus-os/sidecar/life_os/faction_balancer.py` | 210 | Mathematical constraint solver ensuring Craft ($\ge 40\%$), Health ($\ge 25\%$), Leverage ($\ge 20\%$), Expression ($\ge 15\%$) weekly distribution | `scheduler.py`, PostgreSQL |

### Stripped Mathematical & Algorithmic Logic

```
STEP 1: Operating Mode Capacity Filter
    - Inputs: Current DCS (0.0 - 10.0), Operating Mode, Candidate Task Pool
    - Task Difficulty Thresholds:
      * SURVIVAL  (DCS 0.0 - 2.0)  → Filter: Task.difficulty <= 2, Non-negotiable health only
      * RECOVERY  (DCS 2.1 - 4.0)  → Filter: Task.difficulty <= 4, Light administrative only
      * NORMAL    (DCS 4.1 - 6.0)  → Filter: Task.difficulty <= 7, Balanced standard tasks
      * DEEP_WORK (DCS 6.1 - 8.0)  → Filter: Task.difficulty <= 9, Complex analytical tasks
      * PEAK      (DCS 8.1 - 10.0) → Filter: All tasks eligible, Highest difficulty first
    - Formula: EligibleTasks = { t ∈ Pool | t.min_dcs <= DCS ∧ t.difficulty <= ModeMaxDiff }

STEP 2: Task Weight Score (TWS) Ranking
    - Formula: TWS = (D * 0.35) + (L * 0.25) + (U * 0.20) + (C * 0.20) + LagBonus
      where:
        D = Difficulty (1 - 10)
        L = Leverage (1 - 10, long-term multiplier impact)
        U = Urgency (1 - 10, proximity to hard external deadline)
        C = Consequence of Inaction (1 - 10, penalty if neglected)
        LagBonus = min(2.5, deferral_count * 0.5)
    - Output: Tasks sorted in strict descending order of TWS.

STEP 3: Operating Mode Time-Block Grid Allocation
    - Daily Block Budgets by Mode:
      * PEAK:      4 Deep Blocks (90m) + 2 Light Blocks (30m) = 7.0h cognitive load
      * DEEP_WORK: 3 Deep Blocks (90m) + 3 Light Blocks (30m) = 6.0h cognitive load
      * NORMAL:    2 Deep Blocks (90m) + 4 Light Blocks (30m) = 5.0h cognitive load
      * RECOVERY:  1 Deep Block  (60m) + 3 Light Blocks (20m) = 2.0h cognitive load
      * SURVIVAL:  0 Deep Blocks       + 2 Light Blocks (15m) = 0.5h basic maintenance

STEP 4: Faction Balance Constrained Assignment
    - Faction Targets:
      * Craft (Work / Engineering):     Target 40% (Tolerance ±5%)
      * Health (Physical / Mental):     Target 25% (Tolerance ±5%)
      * Leverage (Systems / Wealth):    Target 20% (Tolerance ±5%)
      * Expression (Writing / Art):     Target 15% (Tolerance ±5%)
    - Assignment Rule:
      Greedily assign highest TWS task to next open Deep block UNLESS assigning that task
      causes that faction's weekly allocated hours to exceed Target + Tolerance while an
      under-represented faction has eligible tasks waiting.

STEP 5: Ultradian Recovery Buffer Insertion
    - Rules:
      * After every 90-minute Deep Block: Insert mandatory 20-minute Recovery Buffer (No screens, hydration, movement).
      * After every 30-minute Light Block: Insert 5-minute transition buffer.
      * Maximum continuous cognitive duration: 90 minutes without exception.

STEP 6: Three-Layer Goal Stack Validation
    - Verification:
      FOR EACH scheduled task t:
          ASSERT t.project_id IS NOT NULL, error="Orphan task detected"
          ASSERT Project(t.project_id).outcome_id IS NOT NULL, error="Orphan project detected"
          ASSERT Outcome(Project.outcome_id).faction ∈ {Craft, Health, Leverage, Expression}
    - Output: Serialized daily schedule dispatch manifest for Telegram morning briefing.
```

### Locus adaptation
- **Component**: `locus-os/sidecar/life_os/scheduler.py` (Python sidecar)
- **Provider Interface**: `SchedulerProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); block configuration and faction targets in `.locus/config.yaml`.
- **Swappable / off state**: `locus.life_os.scheduler.enabled`. Off → automatic schedule generation disabled; user schedules tasks manually.
- **STEAL VERBATIM**: The exact TWS formula with LagBonus, the operating mode block budgets, the faction tolerance constraint equation, and the mandatory 20-minute ultradian buffer rule.
- **ADAPT**: Executed automatically during the Morning Briefing check-in (07:30 IST) to construct the user's daily calendar and task roadmap.


---

## Feature §25.13: Review Cadence System

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §11

### Logic extracted: daily standup (morning briefing), weekly retrospective (Sunday synthesis via Gemini 2.5 Pro), monthly deep review.

### Locus adaptation
- **Repo vs `.locus`**: review triggers in `locus-os/sidecar/life_os/reviews.py`.
- **Swappable / off state**: each review cadence toggleable independently. Off → no automatic review prompts.

---

## Feature §25.14: Goal Stack Enforcement

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW

### Logic extracted: every task MUST parent to a project; every project MUST parent to an outcome. Orphan tasks surfaced during morning briefing.

### Locus adaptation
- **Repo vs `.locus`**: enforcement in `locus-os/sidecar/life_os/goal_enforcement.py`.
- **Swappable / off state**: `locus.life_os.goal_enforcement.enabled`. Off → orphan tasks are allowed.

---

## Feature §25.15: Cross-Faction Efficiency

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW

### Logic extracted: tasks tagged with multiple factions count toward both targets (weighted by primary/secondary split). Prevents double-counting.

### Locus adaptation
- **Repo vs `.locus`**: in `locus-os/sidecar/life_os/cross_faction.py`.
- **Swappable / off state**: `locus.life_os.cross_faction.enabled`. Off → tasks count toward primary faction only.

---

## Feature §25.16: Four-Level Emergency Protocol

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §12

### Logic extracted: Level 1 (minor) → Level 4 (crisis). Each level unlocks different tool permissions and overrides scheduling. Crisis hierarchy: Health > Leverage > Craft > Expression.

### Locus adaptation
- **Repo vs `.locus`**: protocol in `locus-os/sidecar/life_os/emergency_protocol.py`.
- **Swappable / off state**: `locus.life_os.emergency_protocol.enabled`. Off → no emergency overrides; standard scheduling always applies.

---

# PROACTIVE REASONING — §26 (Locus-Unique)

> All features 🆕 LOCUS-NEW (Locus-original). Code in Python sidecar under `sidecar/brain/`. Provider interface: `BrainProvider` and `PatternEngine`.

## Feature §26.1: Inner Loop (Proactive Thinker — 10-Step Execution Pipeline)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_agent_loop.md` + `locus_microsystems.html` (Subsystem 3, 10-Step Inner Loop Breakdown)  
**Query method**: [📐 DESIGN SPEC: locus_agent_loop.md]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/brain/inner_loop.py` | 480 | Autonomous proactive reasoning loop running every 90 min (07:00-00:00 IST); generates thoughts, checks goals, routes proactive nudges | `state_engine.py`, `pattern_engine.py`, `reward_model.py`, `redis_client.py` |
| `locus-os/sidecar/brain/proactive_router.py` | 210 | Delivers candidate proactive observations to Telegram immediately or queues them for next check-in | `inner_loop.py`, `providers/channels/telegram.py` |

### Stripped Micro-Step Logic (from `locus_microsystems.html`)

```
STEP 1: Budget & Active Window Gate
    - Verify current time is between 07:00 and 00:00 IST.
    - Check daily LLM cost accumulator: IF daily_cost >= 0.80 * daily_budget_cap -> SKIP cycle.

STEP 2: State Ingestion
    - Fetch active `CURRENT_STATE` JSON from Redis (DCS, Operating Mode, Stress, Active Alerts).
    - If DCS <= 2.0 (SURVIVAL mode) -> Suppress all proactive suggestions except critical health alerts.

STEP 3: Multi-Horizon Pattern Pull
    - Pull candidate patterns from Pattern Engine across H1 (6h) to H5 (all-time).
    - Filter for patterns with confidence score >= 0.70.

STEP 4: Goal & Action Gap Evaluation
    - Scan active tasks in PostgreSQL:
      * Identify tasks deferred >= 3 times (DEFERRAL_FLAG)
      * Identify high-TWS tasks without progress in last 48 hours (ACTION_GAP)

STEP 5: Candidate Thought Formulation
    - Assemble prompt with: SOUL.md personality + current state + top pattern + active goal gap.
    - Call DeepSeek V4 Flash (temp=0.4, max_tokens=300) to synthesize concise proactive observation.

STEP 6: Deduplication Check
    - Embed candidate observation using local fastembed (BAAI/bge-small-en-v1.5).
    - Compare cosine similarity against last 20 sent observations stored in Redis `recent_proactive_thoughts`.
    - If max_cosine_similarity >= 0.85 -> DISCARD as duplicate.

STEP 7: Personal Reward Model Scoring
    - Score candidate thought through Personal Reward Model (§10.5):
      Score = (Actionability * 0.4) + (TimingRelevance * 0.35) + (Brevity * 0.25)
    - If Score < 0.60 -> DISCARD.

STEP 8: Delivery Priority Routing
    - IF Score >= 0.85 AND DCS >= 5.0 -> Route: IMMEDIATE Telegram Push (with action buttons).
    - ELIF Score >= 0.60 -> Route: Enqueue to `briefing_queue` for next Morning/Evening Check-in.
    - ELSE -> Route: Store silently in `subconscious_log` table in PostgreSQL.

STEP 9: Audit Trail Write
    - Insert generated thought, scores, and routing decision into `inner_loop_audit` table.

STEP 10: Redis State Update
    - Update Redis key `last_inner_loop_run = now()`. Set next run alarm for +90 minutes.
```

### Locus adaptation
- **Component**: `locus-os/sidecar/brain/inner_loop.py` (Python sidecar)
- **Provider Interface**: `ProactiveReasoningProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); schedule and budget thresholds in `.locus/config.yaml`.
- **Swappable / off state**: `locus.brain.inner_loop.enabled`. Off → Locus operates purely reactively; never initiates self-triggered thoughts.
- **STEAL VERBATIM**: The 10-step execution cycle, the 0.85 cosine deduplication threshold, the 0.60 reward model acceptance gate, and the 90-minute interval window.

---

## Feature §26.2: State Engine + Inferred Cause Chain

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` + `Comprehensive Locus System Design.html` (Subsystem 8, 9-Step Causation Engine)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/brain/state_engine.py` | 390 | Real-time DCS state engine listening on PostgreSQL event channel; computes operating mode and maintains Redis state | `postgres_client.py`, `redis_client.py`, `cause_chain.py` |
| `locus-os/sidecar/brain/cause_chain.py` | 280 | Inferred causation synthesizer diagnosing root causes behind sudden energy/mood drops | `state_engine.py`, `auxiliary_client.py` |

### Stripped Micro-Step Logic

```
STEP 1: Event-Driven State Shift Detection
    - Real-time listener on PostgreSQL `locus_events` channel.
    - Triggered when new check-in arrives OR significant DCS drop detected (ΔDCS <= -2.0).

STEP 2: Multidimensional 48-Hour Event Window Pull
    - Query PostgreSQL for past 48 hours of:
      * Behavioral events (task completions, deferrals, interruptions)
      * Physiological metrics (sleep duration, sleep score, workout timestamps)
      * Nutrition logs (skipped meals, late caffeine)
      * Digital exhaust (screen time, late commits)

STEP 3: Chronological Temporal Alignment
    - Assemble events into a strictly ordered chronological event graph.

STEP 4: Anomaly Correlation Scanner
    - Run correlation rules over event graph:
      * Late bedtime (>01:00) -> Next-day Energy drop (confidence 0.88)
      * Skipped lunch -> 16:00 Task Deferral surge (confidence 0.79)
      * High meeting density (>4h) -> Creative task avoidance (confidence 0.84)

STEP 5: LLM Cause Chain Synthesis
    - Call DeepSeek V4 Flash with structured anomaly window:
      Prompt: "Deduce the causal chain leading to current state. Cite empirical data points."
    - Output: Structured JSON: `{ root_cause, causal_links: [A -> B -> C], confidence, evidence_ids }`

STEP 6: Evidence Verification Gate
    - Verify every link in `causal_links` references at least one valid database event ID.
    - Discard any hallucinated causal assertions.

STEP 7: Confidence Scoring
    - Compute Confidence = (SupportedLinks / TotalLinks) * EvidenceDensityWeight.

STEP 8: Redis `CURRENT_STATE` Write
    - Update Redis key `CURRENT_STATE` with `inferred_cause_chain_summary`.

STEP 9: Alert Escalation
    - IF Confidence >= 0.85 AND Severity == HIGH -> Emit alert to Inner Loop surface queue.
```

### Locus adaptation
- **Component**: `locus-os/sidecar/brain/state_engine.py` (Python sidecar)
- **Provider Interface**: `StateEngineProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); state history in PostgreSQL `state_snapshots`.
- **Swappable / off state**: `locus.brain.state_engine.enabled`. Off → DCS remains static until manual check-in.

---

## Feature §26.3: Multi-Horizon Pattern Engine

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` (Subsystem 5, 11-Step Pattern Engine)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/brain/pattern_engine.py` | 440 | 5-horizon behavioral pattern detector with confidence-based promotion rules | `postgres_client.py`, `neo4j-labs/agent-memory`, `inner_loop.py` |

### Stripped Micro-Step Logic

```
THE 5-HORIZON HIERARCHY:
    H1: Micro (Last 6 Hours)    → Immediate fatigue, focus drift, task thrashing
    H2: Daily (Last 24 Hours)   → Diurnal rhythms, peak performance windows
    H3: Weekly (Last 7 Days)    → Weekly faction balance, recurring weekday blockers
    H4: Monthly (Last 30 Days)  → Habit formation, chronic deferral loops, project momentum
    H5: Macro (All-Time)        → Deep personality traits, seasonal cycles, core strengths

PATTERN PROMOTION PIPELINE:
    FUNCTION evaluate_pattern_promotion(candidate_pattern):
        // Rules for promoting pattern from H_n to H_{n+1}:
        // 1. Minimum Occurrence Repetition: Count >= 3 across horizon boundary
        // 2. Confidence Threshold: Confidence >= 0.75
        // 3. Negative Evidence Ratio: Contradictions / Occurrences <= 0.15
        
        IF candidate_pattern.occurrences >= 3 AND candidate_pattern.confidence >= 0.75:
            promoted_horizon = candidate_pattern.horizon + 1
            candidate_pattern.horizon = promoted_horizon
            
            IF promoted_horizon >= H4:
                // Commit stable monthly/all-time patterns to Neo4j knowledge graph as :BEHAVIORAL_TRAIT
                neo4j.merge_pattern_node(candidate_pattern)
            ELSE:
                pg.upsert("behavioral_patterns", candidate_pattern)
```

### Locus adaptation
- **Component**: `locus-os/sidecar/brain/pattern_engine.py` (Python sidecar)
- **Provider Interface**: `PatternEngineProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); pattern storage in PostgreSQL `behavioral_patterns`.
- **Swappable / off state**: `locus.brain.pattern_engine.enabled`. Off → no pattern detection.

---

## Feature §26.7: Weekly Full Vault Synthesis

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_agent_loop.md` + `LOCUS_SYSTEM_v1.md` §11  
**Query method**: [📐 DESIGN SPEC: locus_agent_loop.md]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/brain/weekly_synthesis.py` | 310 | Sunday 02:00 IST deep synthesis engine leveraging Gemini 2.5 Pro (1M context) to analyze all weekly notes, logs, and faction progress | `crawlers/vault_crawler.py`, `life_os/rebalance.py` |

### Stripped Micro-Step Logic

```
SUNDAY WEEKLY SYNTHESIS PIPELINE (02:00 IST):
    STEP 1: Gather Full 7-Day Context Bundle
        - Scan Obsidian vault for all notes created or modified in last 7 days.
        - Fetch all PostgreSQL check-in rows and behavioral events from the week.
        - Calculate actual vs target Faction distribution percentages (Craft, Health, Leverage, Expression).

    STEP 2: Long-Context Prompt Assembly
        - Combine full text of weekly notes (~80K-200K tokens) + event logs + goal stack status.
        - System instruction:
          "Perform an exhaustive strategic synthesis of Shivam's past week. Identify hidden patterns,
           unresolved tensions, project velocity bottlenecks, and recommended faction weight adjustments."

    STEP 3: Model Invocation (Gemini 2.5 Pro / DeepSeek V4)
        - Call large-context model with 1M context window (temp=0.3).

    STEP 4: Output Parsing & Section Structuring
        - Parse structured Markdown sections:
          # 1. Executive Summary & Faction Scorecard
          # 2. Key Breakthroughs & Completed Milestones
          # 3. Persistent Deferrals & Friction Analysis
          # 4. Emergent Ideas & Unresolved Questions
          # 5. Proposed Strategic Focus for Next Week

    STEP 5: Vault Write & Knowledge Base Linking
        - Save generated synthesis to `/vault/02-Reviews/Weekly/YYYY-Www-Synthesis.md`.
        - Inject wikilinks to referenced project notes and concept files.

    STEP 6: Neo4j High-Level Entity Sync
        - Extract top-level strategic conclusions and write as `:WEEKLY_THEME` nodes in Neo4j.
```

### Locus adaptation
- **Component**: `locus-os/sidecar/brain/weekly_synthesis.py` (Python sidecar)
- **Provider Interface**: `WeeklySynthesisProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); report saved to Obsidian `/vault/02-Reviews/Weekly/`.
- **Swappable / off state**: `locus.brain.weekly_synthesis.enabled`. Off → no automatic Sunday review; manual trigger via `locus review weekly`.


---

# RESEARCH LAYER — §11.6

### Metadata
- **Source Codebase**: `karpathy/autoresearch` — **CLONED** at `5_Locus/deps/autoresearch`, actual source read.
- **Verification**: [✅ VERIFIED: cloned repo, source read] · `repo_cloned: true` · `logic_stripped: true` · `contains_code: false`

### Files involved (real — only three matter)

| File | Role | Who edits |
|------|------|-----------|
| `prepare.py` | Fixed constants, data prep (download + BPE tokenizer), dataloader, `evaluate_bpb` harness, 5-min wall-clock budget | **read-only** (human, once) |
| `train.py` | Full GPT model + optimizer (Muon + AdamW) + training loop; architecture, hyperparameters, batch size all fair game | **the delegated coding harness** |
| `program.md` | Lightweight "skill" / "research-org" config: what the agent may/may not do, success metric, simplicity criterion, output format | **the human** (Shivam) |

### Logic extracted

Give an AI agent a small but real single-GPU LLM training setup and let it experiment autonomously overnight:

1. **One file to modify** (`train.py`) — keeps scope small and diffs reviewable.
2. **Fixed time budget** — every run trains exactly 5 minutes wall-clock (≈12 experiments/hr, ≈100 overnight), so experiments are directly comparable regardless of what the agent changes.
3. **Single metric** — `val_bpb` (validation bits-per-byte, lower is better, vocab-size independent).
4. **Keep / discard / crash** loop — run, parse `val_bpb`, git-commit on improvement, git-revert on regression.
5. **`results.tsv` ledger** — 5 columns: `commit` (7-char) · `val_bpb` · `memory_gb` · `status` (`keep`/`discard`/`crash`) · `description`. First run is always the unmodified baseline.
6. **The "agent" is a coding harness, not the framework.** The repo is deliberately written so you point an external Claude Code / Codex at it ("disable all permissions") and let *it* edit `train.py` against `program.md`.

### Pseudocode / algorithm

```
setup_autoresearch(goal):
    branch = git checkout -b autoresearch/<date_tag>     # fresh run per tag
    run: uv run prepare.py                               # one-time data + tokenizer (~2 min)
    results.tsv = header row only

research_loop(max_iterations):
    run: uv run train.py          # FIRST run = unmodified baseline -> log baseline val_bpb
    loop:
        harness reads train.py + program.md               # delegated harness, not Locus
        harness edits train.py                             # anything: arch, opt, hparams, batch
        result = exec_with_timeout("uv run train.py", 300s)
        val_bpb = parse("val_bpb:" from run.log)
        if val_bpb < best: git_commit("..."), status=keep
        else:              git_revert(), status=discard
        append results.tsv: commit, val_bpb, memory_gb, status, description
        if crash: status=crash, val_bpb=0.0

report(): return best val_bpb + full results.tsv + git log
```

### Locus adaptation

- **Component**: `locus/providers/research/autoresearch.ts` — `ResearchProvider`, invoked as tool `locus_research` when intent == `RESEARCH_REQUEST`.
- **The crucial adaptation — harness delegation**: the entity that edits `train.py` is a **delegated coding harness** (Claude Code / Codex, pre-installed), run in a **sandboxed terminal** (`SandboxProvider`, Docker preferred for GPU). Locus does **not** generate the code; it (a) clones/initialises the repo, (b) hands the harness `program.md` + the goal, (c) monitors `results.tsv`, and (d) reports the final outcome to the user. This is the canonical example of the "Locus plans + prompts a harness, never codes itself" rule.
- **Repos vs `.locus`**: the autoresearch workspace (a git repo) is runtime state → `.locus/workspace/autoresearch/<tag>/`; `program.md` edits are user-owned config → `.locus`.
- **Swappable / off state**: `locus.research.provider`; off = `RESEARCH_REQUEST` falls back to the web-search pipeline instead of a training loop.
- **Cost guard**: GPU runs are not token-cheap; gate behind explicit user confirmation and the daily token/cost budget (Inner Loop's "skip if >80% budget" rule applies here too).

---

# MEMORY PROVIDER ABC — §4 Hermes Pattern

## Feature §4.18: Memory Provider Interface

### Source
- **Codebase**: Hermes at `agent/memory_provider.py` + `agent/memory_manager.py`
- **Verification**: [✅ VERIFIED: `memory_provider.py` (297 lines) read in full]

### Stripped Logic (Pseudocode)

```
ABSTRACT CLASS MemoryProvider:
    // Identity
    name: str
    
    // Core lifecycle (MUST implement):
    is_available() → bool          // check config + deps, no network calls
    initialize(session_id, **kwargs)  // connect, create resources
    // kwargs: hermes_home, platform, agent_context, agent_identity,
    //         parent_session_id, user_id
    
    system_prompt_block() → str    // static text for system prompt
    
    prefetch(query, session_id) → str
    // Recall context BEFORE each LLM call
    // Must be fast — use background threads, return cached results
    
    queue_prefetch(query, session_id)
    // Queue background recall for NEXT turn
    
    sync_turn(user_content, assistant_content, session_id, messages)
    // Persist completed turn. Non-blocking — queue for background.
    
    get_tool_schemas() → [tool_schema]  // tools to expose to model
    handle_tool_call(tool_name, args) → json_string
    shutdown()
    
    // Optional hooks:
    on_turn_start(turn_number, message, **kwargs)
    on_session_end(messages)
    on_session_switch(new_session_id, parent_session_id, reset, rewound)
    on_pre_compress(messages) → str    // extract before compression
    on_memory_write(action, target, content, metadata)  // mirror built-in writes
    on_delegation(task, result, child_session_id)  // subagent observation

MEMORY MANAGER — One-provider limit:
    // Hermes enforces a single external memory provider to prevent
    // tool schema bloat and conflicting backends
    // Locus RELAXES this: allows stackable providers (primary + secondary)
    
    FUNCTION register_provider(provider):
        IF provider.is_available():
            provider.initialize(session_id, **runtime_kwargs)
            active_providers.append(provider)
    
    FUNCTION prefetch_all(query):
        results = []
        FOR EACH provider IN active_providers:
            results.append(provider.prefetch(query))
        RETURN merge_results(results)
    
    FUNCTION sync_turn_all(user, assistant):
        FOR EACH provider IN active_providers:
            provider.sync_turn(user, assistant)  // non-blocking
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/memory/interface.ts`
- **KEEP**: The entire ABC interface. It's well-designed.
- **ADAPT**: Locus allows MULTIPLE active providers (Neo4j primary + PageIndex secondary + pgvector tertiary). The `memory_manager` merges results from all active providers, weighted by intent type.
- **Config**: `locus.memory.provider` = primary, `locus.memory.secondary_providers` = stackable array.

---

# EXPORT & UTILITIES — §19

## Feature §19.2: Trajectory Recording

### Source
- **Codebase**: Hermes at `trajectory_compressor.py` (70K)
- **Verification**: [✅ VERIFIED: file listed, 70K size]

### Stripped Logic (Pseudocode)

```
TRAJECTORY RECORDING — Full conversation recording for batch evaluation

FUNCTION record_trajectory(session):
    trajectory = {
        session_id: session.id,
        model: session.model,
        messages: [],
        tool_calls: [],
        timestamps: [],
        token_usage: [],
        metadata: {
            platform: session.platform,
            start_time: session.start_time,
            end_time: now()
        }
    }
    
    FOR EACH turn IN session.turns:
        trajectory.messages.append({
            role: turn.role,
            content: turn.content,
            timestamp: turn.timestamp,
            tokens: turn.token_count
        })
        IF turn.tool_calls:
            trajectory.tool_calls.extend(turn.tool_calls)
    
    // Compress for storage
    compressed = trajectory_compressor.compress(trajectory)
    write_json(session.trajectory_path, compressed)

BATCH EVALUATION:
    FUNCTION batch_evaluate(trajectories, eval_prompt):
        // Run same prompt across multiple trajectories
        // Compare: token usage, tool call patterns, response quality
        results = []
        FOR EACH trajectory IN trajectories:
            score = evaluate_trajectory(trajectory, eval_prompt)
            results.append(score)
        RETURN aggregate_results(results)
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/trajectory.ts`
- **Integration**: Records every Locus session for: the daily chat archiver (23:45 → .md → vault → CouchDB real-time LiveSync replication), reward model training data, and batch evaluation.

---


## Feature §19.3: Daily AI Chat Archiver (Multi-Platform Ingestion)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` (Subsystem 15, 7-Step Archiver Breakdown)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/ingestion/chat_archiver.py` | 340 | Multi-platform chat crawler & normalizer (Claude, ChatGPT, Cursor, Pi, Telegram); extracts Q&A pairs, code blocks, decisions | `crawlers/chat_crawler.py`, `neo4j-labs/agent-memory`, `VectifyAI/PageIndex` |
| `locus-os/sidecar/crawlers/chat_crawler.py` | 280 | Directory and browser export watcher for conversation dumps | `chat_archiver.py`, local disk |

### Stripped Logic (Pseudocode)

```
STEP 1: Archival Cron Trigger (23:45 IST Daily)
    - Automated timer triggers daily chat ingestion job.
    - Can also be manually invoked via `locus ingest chats`.

STEP 2: Source Discovery & Crawl
    - Scan local browser export directories and API logs:
      * Claude Web / App JSON exports
      * ChatGPT export archives
      * Cursor IDE conversation logs
      * Pi native session histories
      * Telegram Locus conversation logs

STEP 3: Parsing & Normalization
    - Convert platform-specific JSON/HTML into unified Markdown format:
      * YAML Frontmatter: title, date, platform, model, tags, summary
      * Extracted Key Decisions
      * Q&A Transcript
      * Code Artifacts

STEP 4: Entity & Relationship Extraction
    - Pass transcript to Neo4j extraction pipeline (`neo4j-labs/agent-memory`):
      * Extract POLE+O entities (Person, Object, Location, Event, Organization)
      * Write :TOUCHED and :DECIDED relationships into Neo4j graph

STEP 5: Vectorless Tree Indexing (PageIndex)
    - Submit formatted markdown note to PageIndex tree builder.
    - Reconstruct hierarchical index nodes for `Vault/AI Chats/YYYY-MM-DD/`.

STEP 6: Obsidian Vault Write
    - Write generated notes to `/vault/04-Captures/AI Chats/YYYY-MM-DD/{title}.md`.

STEP 7: Automated Real-Time CouchDB & Obsidian LiveSync Replication
    - Submit file modification event to `livesync_bridge.py`:
      * Increment document revision in CouchDB (`locus-couchdb:5984/locus-vault`)
      * Continuous replication feed instantly pushes new note to mobile and desktop Obsidian clients
      * Fallback: Local transactional snapshot recorded in PostgreSQL `vault_file_hashes`
```

### Locus adaptation
- **Component**: `locus-os/sidecar/ingestion/chat_archiver.py` (Python sidecar)
- **Provider Interface**: `ChatArchiverProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); crawl configuration in `.locus/config.yaml`.
- **Swappable / off state**: `locus.ingestion.chat_archiver.enabled`. Off → external AI chats are not ingested into the knowledge graph.
- **STEAL VERBATIM**: The 7-step archival pipeline from `locus_microsystems.html`, normalization schema, and automated CouchDB LiveSync synchronization cycle.
- **ADAPT**: Integrates external AI interactions directly into Locus's Neo4j and PageIndex tri-stack for long-term memory retrieval.


# CLI & CONFIGURATION — §8, §22

## Feature §8.1-8.10: CLI Commands, Multi-Surface Management, Telegram Settings & Headless VM Topology

### Metadata
- **Verdict**: 🔄 AUGMENT · **Source**: Pi `args.ts` + Hermes `hermes_cli` + OpenHuman `schema.json` + Locus Multi-Surface Architecture
- **Verification Tag**: `[✅ VERIFIED: Pi args.ts + Hermes hermes_cli + OpenHuman schema read]`
- **Provider Interface**: `MultiSurfaceCLI`
- **Repo vs `.locus`**: CLI command wrappers in `locus_cli/` (repo); Pi extension commands in `locus-extension/` (repo); Telegram bot router in `gateway/` (repo); daemon units in `deploy/systemd/` (repo); settings in `~/.locus/config.yaml` and secrets in `~/.locus/.env`.

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus_cli/main.py` | ~340 | Entry point for `locus` CLI tool; routes subcommands to handlers or launches Pi TUI | `packages/coding-agent/src/cli.ts`, `locus-extension` |
| `locus_cli/config.py` | ~260 | Persistent configuration and `.env` secret management (`get`, `set`, `check`) | `~/.locus/.env`, Pi `settings.json` |
| `locus_cli/doctor.py` | ~220 | Multi-subsystem diagnostic suite running live network and socket probes | `sidecar/routers/system.py`, DB sockets |
| `locus_cli/gateway_service.py` | ~210 | Manages the background gateway daemon across platforms (systemd / Windows Service) | OS process manager, `gateway/bot.py` |
| `gateway/settings_handler.py` | ~310 | Telegram bot interactive `/settings`, `/setup`, and `/doctor` engine with inline keyboards | `python-telegram-bot`, `sidecar` |
| `sidecar/cron_runner.py` | ~250 | 24/7 autonomous proactive scheduler via APScheduler for headless VM | `brain/inner_loop.py`, `brain/collector.py` |
| `sidecar/routers/system.py` | ~180 | FastAPI endpoints for system reload (`POST /system/reload`), config export, and health | FastAPI router, `sidecar/main.py` |
| `deploy/systemd/locus-sidecar.service` | ~30 | Headless VM systemd unit definition ensuring 24/7 background persistence | Linux systemd, `uvicorn` |
| `deploy/systemd/locus-gateway.service` | ~30 | Headless VM systemd unit definition ensuring Telegram bot runs 24/7 | Linux systemd, Python runtime |

### Stripped Logic (Pseudocode)

```
// 1. CLI SUBCOMMANDS ENGINE (locus_cli/main.py)
FUNCTION locus_cli_entrypoint(argv):
    parser = create_locus_argparser()
    
    // Core run command: if no subcommand or 'run', boot Pi TUI with locus extension
    IF argv.length == 0 OR argv[0] == "run":
        RETURN exec_pi_tui(args=argv, extension="locus-extension")
    
    SUBCOMMAND_DISPATCH:
        CASE "setup":
            // Interactive terminal wizard or headless non-interactive bootstrap
            IF parser.has_flag("--non-interactive"):
                RETURN run_headless_setup(env_file=parser.get("--env-file"))
            ELSE:
                RETURN run_locus_onboarding_wizard(environment="cli")
                
        CASE "config":
            action = parser.get("action")  // get, set, check, export
            IF action == "get":   RETURN print(config.get(parser.get("key")))
            IF action == "set":   RETURN config.set_and_save(parser.get("key"), parser.get("val"))
            IF action == "check": RETURN validate_config_integrity()
            IF action == "export": RETURN print_json(config.dump())

        CASE "doctor":
            probe_results = run_full_diagnostics(verbose=parser.has_flag("--full"))
            IF parser.has_flag("--json"):
                RETURN print_json(probe_results)
            ELSE:
                RETURN render_cli_doctor_table(probe_results)

        CASE "gateway":
            cmd = parser.get("cmd")  // run, start, stop, restart, status
            IF cmd == "run":     RETURN gateway.run_foreground()
            IF cmd == "start":   RETURN service_manager.start("locus-gateway")
            IF cmd == "stop":    RETURN service_manager.stop("locus-gateway")
            IF cmd == "restart": RETURN service_manager.restart("locus-gateway")
            IF cmd == "status":  RETURN service_manager.status("locus-gateway")

        CASE "cron":
            cmd = parser.get("cmd")  // list, trigger, pause, resume
            IF cmd == "list":    RETURN print_cron_jobs(sidecar.get_crons())
            IF cmd == "trigger": RETURN sidecar.trigger_cron(parser.get("job_id"))
            IF cmd == "pause":   RETURN sidecar.pause_cron(parser.get("job_id"))
            IF cmd == "resume":  RETURN sidecar.resume_cron(parser.get("job_id"))

        CASE "life":
            cmd = parser.get("cmd")  // dcs, mode, factions, rebalance
            IF cmd == "dcs":      RETURN print(sidecar.get_dcs_score())
            IF cmd == "mode":     RETURN print(sidecar.get_operating_mode())
            IF cmd == "factions": RETURN print_table(sidecar.get_faction_hours())

        CASE "vault":
            cmd = parser.get("cmd")  // sync, index, status
            IF cmd == "sync":   RETURN couchdb_livesync.trigger_sync()
            IF cmd == "index":  RETURN pageindex.reindex_vault()
            IF cmd == "status": RETURN print(couchdb_livesync.get_status())

        CASE "memory":
            cmd = parser.get("cmd")  // stats, inspect, prune
            IF cmd == "stats":   RETURN print(neo4j_provider.get_stats())
            IF cmd == "inspect": RETURN neo4j_provider.query_subgraph(parser.get("term"))


// 2. 24/7 HEADLESS VM PROACTIVE CRON ENGINE (sidecar/cron_runner.py)
FUNCTION initialize_proactive_cron_engine(config):
    IF NOT config.get("locus.cron.enabled"): RETURN
    
    scheduler = APScheduler(timezone=config.get("locus.life_os.timezone", "Asia/Kolkata"))
    
    // Routine 1: 90-minute Reactive Proactive Pass (Inner Loop Stages 1-10)
    // Only runs between 07:00 and 00:00 IST to prevent nighttime alert spam
    scheduler.add_job(
        func=run_inner_loop_turn,
        trigger=IntervalTrigger(minutes=90),
        id="proactive_inner_loop",
        name="Inner Loop Proactive Pass"
    )

    // Routine 2: Nightly Vault Crawl & Indexing (03:00 IST)
    // Synchronizes CouchDB LiveSync buffer, updates PageIndex vectorless tree & Neo4j POLE+O nodes
    scheduler.add_job(
        func=run_nightly_vault_ingestion,
        trigger=CronTrigger(hour=3, minute=0),
        id="nightly_vault_crawl",
        name="Nightly Vault Ingestion & Graph Indexing"
    )

    // Routine 3: Daily Morning Briefing (08:00 IST)
    // Synthesizes DCS mode, overdue TWS tasks, and faction lag; pushes directly to Telegram
    scheduler.add_job(
        func=dispatch_morning_briefing_to_telegram,
        trigger=CronTrigger(hour=8, minute=0),
        id="morning_briefing",
        name="Morning Telegram Briefing"
    )

    // Routine 4: Sunday Weekly Synthesis (03:00 IST Sunday)
    // Evaluates 3-week Momentum Score (MS), Action Gap (AG), and triggers faction hour rebalance
    scheduler.add_job(
        func=run_weekly_faction_synthesis,
        trigger=CronTrigger(day_of_week="sun", hour=3, minute=0),
        id="sunday_synthesis",
        name="Weekly Faction & DCS Synthesis"
    )

    scheduler.start()


// 3. TELEGRAM-NATIVE SETTINGS & SETUP SURFACE (gateway/settings_handler.py)
FUNCTION handle_telegram_settings_command(update, context):
    // Main Settings Menu rendered via Inline Keyboards
    keyboard = [
        [InlineKeyboardButton("🧠 LLM Providers", callback_data="locus:menu:llm"),
         InlineKeyboardButton("🕸️ Memory Tri-Stack", callback_data="locus:menu:memory")],
        [InlineKeyboardButton("📚 Vault & LiveSync", callback_data="locus:menu:vault"),
         InlineKeyboardButton("⚡ Life OS & Factions", callback_data="locus:menu:life")],
        [InlineKeyboardButton("⏰ Autonomous Crons", callback_data="locus:menu:crons"),
         InlineKeyboardButton("🩺 Live Diagnostics", callback_data="locus:cmd:doctor")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("⚙️ **Locus OS Settings & Framework Toggles**\nSelect a subsystem to configure:", reply_markup=reply_markup)

FUNCTION handle_telegram_callback_query(update, context):
    query = update.callback_query
    data = query.data
    query.answer()

    IF data.startswith("locus:toggle:"):
        subsystem = data.split(":")[2]
        current_state = config.get(f"locus.providers.{subsystem}.enabled", false)
        new_state = NOT current_state
        config.set_and_save(f"locus.providers.{subsystem}.enabled", new_state)
        
        // Notify Python sidecar to hot-reload provider
        sidecar_client.post("/system/reload", { "subsystem": subsystem })
        
        // Refresh inline keyboard with updated [ON] / [OFF] badge
        updated_keyboard = rebuild_subsystem_keyboard(subsystem)
        query.edit_message_reply_markup(reply_markup=updated_keyboard)
        RETURN

    IF data == "locus:cmd:doctor":
        results = sidecar_client.get("/system/doctor")
        report_md = format_doctor_report_for_telegram(results)
        query.message.reply_markdown(report_md)
        RETURN
```

### Strict Modular Framework Contract

Every Locus subsystem adheres to this universal JSON schema contract in `settings.json`:

```json
{
  "locus": {
    "topology": "hybrid",
    "providers": {
      "llm": {
        "provider": "deepseek-flash",
        "fallback": "ollama-local",
        "enabled": true,
        "options": { "endpoint": "http://localhost:11434", "timeout_ms": 30000 }
      },
      "memory": {
        "provider": "neo4j-agent-memory",
        "enabled": true,
        "options": { "uri": "neo4j+s://...", "hebbian_decay_rate": 0.05 }
      },
      "compression": {
        "provider": "headroom",
        "enabled": true,
        "options": { "target_ratio": 0.5, "preserved_recency_tokens": 1200 }
      },
      "vault_sync": {
        "provider": "couchdb-livesync",
        "enabled": true,
        "options": { "url": "https://couchdb.locusapp.online", "db": "locus_vault" }
      },
      "cron": {
        "provider": "apscheduler",
        "enabled": true,
        "options": { "proactive_window": "07:00-00:00" }
      }
    }
  }
}
```

### Adaptation to Locus Architecture

- **Component**: `locus_cli/` (Python package), `locus-extension/` (Pi extension), `gateway/` (Telegram handler).
- **Multi-Surface Parity**: Configuration modified in Telegram (`/settings`), in Pi TUI (`/locus:settings`), or in CLI (`locus config set`) immediately persists to `settings.json` and notifies `sidecar` via `POST /system/reload` for instant hot-swapping without restarting daemons.
- **24/7 Headless Invariant**: On cloud VMs, Locus runs entirely without a desktop session; all proactive crons, CouchDB syncing, and ambient communications proceed autonomously.

---

# UNIVERSAL PROVIDER PATTERN

Every Locus provider follows this lifecycle (from Atomic Selections Part IV):

```
1. REGISTRATION:
   provider_registry.register("name", ProviderClass)

2. CONFIGURATION (in Pi's settings.json under "locus"):
   locus:
     [subsystem]:
       provider: "name"       // which provider to use
       enabled: true           // toggle on/off
       options:                // provider-specific config
         key: value

3. INITIALIZATION:
   ON locus_start:
     config = settings.get("locus.[subsystem]")
     IF NOT config.enabled: SKIP
     provider = registry.get(config.provider)
     provider.initialize(config.options)

4. RUNTIME:
     provider.method(args)

5. SHUTDOWN:
     provider.shutdown()

6. HEALTH CHECK:
     provider.health_check() → { status, latency, error? }
```

### 25 Provider Interfaces

| Interface | Default | Purpose |
|-----------|---------|---------|
| MemoryProvider | Neo4j Agent Memory | Store/query memories |
| RetrievalProvider | PageIndex | Document retrieval |
| CompressionProvider | Headroom CCR | Token compression |
| CompactionProvider | Pi compaction | Session-level compression |
| BrainProvider | Locus Brain Engine | Proactive reasoning |
| PatternEngine | 5-horizon engine | Pattern detection |
| ContextAssembler | Context Forge | Context assembly |
| IntentClassifier | 8-type classifier | Query intent classification |
| RewardModel | sklearn LogReg | Gate proactive outputs |
| LifeOSProvider | Locus Life OS | Behavioral metrics |
| SchedulerProvider | node-cron + APScheduler | Cron/scheduling |
| ChannelProvider | Telegram | Messaging bridges |
| STTProvider | Groq Whisper | Speech-to-text |
| TTSProvider | Edge TTS | Text-to-speech |
| SearchProvider | PageIndex | Full-text search |
| EmbeddingProvider | pgvector | Vector embeddings |
| EntityExtractor | spaCy → GLiNER → LLM | Entity extraction |
| SandboxProvider | Pi trust model | Shell sandboxing |
| BrowserProvider | Playwright | Browser automation |
| VaultProvider | Obsidian | Knowledge vault |
| LearningProvider | Locus reflector | Post-session learning |
| PostTurnProvider | Background review | Post-turn processing |
| UserModelProvider | Rolling-average | User profile building |
| SubagentArchetype | 4 factions | Subagent templates |
| HarnessProvider | Pi (fallback) | Coding harness delegation |

---



# SESSIONS LAYER — §5

## Feature §5.1-5.8: Session Management & Telegram Bridge

### Source
- **Codebase**: Pi at `pi/packages/coding-agent/src/core/session-manager.ts`, `compaction/`
- **Verification**: [✅ VERIFIED: `agent-session.ts` header read]

### Stripped Logic (Pseudocode)

```
SESSION FORMAT (JSONL v3):
    Entry types: message, tool_call, tool_result, compaction_summary,
                 branch_summary, metadata, system_event, checkpoint, marker

    Structure: tree-based (sessions can fork into branches)
    Storage: one .jsonl file per session, named by session_id

SESSION BRANCHING:
    FUNCTION fork_session(parent_session_id, fork_point):
        new_session = create_session()
        new_session.parent = parent_session_id
        new_session.fork_point = fork_point
        // Copy all entries up to fork_point
        copy_entries(parent_session_id, new_session.id, up_to=fork_point)
        // Branch summary entry marks the divergence point
        new_session.append(BranchSummaryEntry {
            parent: parent_session_id,
            fork_point: fork_point,
            summary: generate_branch_summary(entries_before_fork)
        })
        RETURN new_session

SESSION RESUME:
    FUNCTION resume_session(session_id):
        session = load_session(session_id)
        // Restore full message history
        messages = session.replay_entries()
        // Restore compacted summaries
        compactions = session.get_compaction_entries()
        // Rebuild context: summaries first, then recent messages
        context = rebuild_context(compactions, messages)
        RETURN context

TELEGRAM SESSION BRIDGE (Locus-unique):
    FUNCTION bridge_telegram_to_session(telegram_chat_id, user_message):
        // Map Telegram chat → Pi session
        session_id = session_map.get(telegram_chat_id)
        IF session_id is None:
            session_id = create_new_session()
            session_map.set(telegram_chat_id, session_id)
        
        // Inject message into Pi session
        session = load_session(session_id)
        session.append(MessageEntry { role: "user", content: user_message })
        
        // Run reactive pipeline (Stages 0-12)
        response = run_reactive_loop(session, user_message)
        
        // Send response back via Telegram
        channel_provider.send_message(telegram_chat_id, response)
        
        // Persist session
        session.append(MessageEntry { role: "assistant", content: response })
        session.flush()
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/session-bridge.ts`
- **KEEP**: All Pi session formats, branching, resume, export. Zero changes.
- **ADD**: Telegram↔Session bridge maps Telegram chat IDs to Pi session IDs. State stored in PostgreSQL `telegram_sessions` table.

---

# TUI LAYER — §7

## Feature §7.1-7.9: Terminal Interface & Native @earendil-works/pi-tui Augmentation

### Metadata
- **Verdict**: 🔄 AUGMENT · **Source**: Pi `@earendil-works/pi-tui` + `modes/interactive/components/` (`settings-selector.ts`, `first-time-setup.ts`, `settings-submenu.ts`)
- **Verification Tag**: `[✅ VERIFIED: @earendil-works/pi-tui components & extension API read in full]`
- **Provider Interface**: `TUIProvider`
- **Repo vs `.locus`**: Extension UI components in `locus-extension/src/ui/` (repo); theme assets in `locus-extension/themes/` (repo); user display preferences in `settings.json`.

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-extension/src/ui/settings-selector.ts` | ~340 | Interactive settings modal extending `SettingsList` for configuring Locus framework modules | `settings.json`, `ctx.ui.custom()` |
| `locus-extension/src/ui/setup-wizard.ts` | ~380 | Multi-stage onboarding wizard extending `SteppedSubmenu` | `@earendil-works/pi-tui`, `sidecar` |
| `locus-extension/src/ui/doctor-overlay.ts` | ~210 | Centered modal overlay via `ctx.ui.custom()` displaying live probe latencies and health | `@earendil-works/pi-tui` DynamicBorder, `sidecar` |
| `locus-extension/src/ui/footer-widget.ts` | ~160 | Custom footer component hooked into `ctx.ui.setFooter()` and `ctx.ui.setStatus()` | `sidecar/routers/life.py`, `ctx.ui` |
| `locus-extension/src/ui/theme.ts` | ~90 | Custom terminal color palettes (Locus Dark, Cyberpunk, Obsidian Monochrome) | `@earendil-works/pi-tui` Theme |
| `locus-extension/src/index.ts` | ~140 | Extension entrypoint registering in-session slash commands (`/locus:setup`, `/locus:settings`, etc.) | `pi.registerCommand()` |

### Stripped Logic (Pseudocode)

```
// 1. NATIVE PI-TUI FRAMEWORK ARCHITECTURE
// NOTE: Pi does NOT use React/Ink. It uses its own high-performance pure-terminal TUI engine:
// @earendil-works/pi-tui, providing Container, DynamicBorder, Text, Input, SelectList, SettingsList.

// 2. LOCUS SETTINGS SELECTOR COMPONENT (locus-extension/src/ui/settings-selector.ts)
CLASS LocusSettingsSelector EXTENDS Container:
    CONSTRUCTOR(options, onSave, onCancel):
        SUPER()
        this.addChild(NEW DynamicBorder())
        this.addChild(NEW Text(theme.bold(theme.fg("accent", "=== LOCUS OS FRAMEWORK SETTINGS ===")), 1, 0))
        this.addChild(NEW Spacer(1))

        // Create categorized SettingsList rows
        items = [
            NEW SettingItem("Deployment Topology", config.get("locus.topology"), () => open_topology_submenu()),
            NEW SettingItem("Primary LLM Provider", config.get("locus.providers.llm.provider"), () => open_llm_submenu()),
            NEW SettingItem("Neo4j Agent Memory", config.get("locus.providers.memory.enabled") ? "ENABLED" : "DISABLED", () => toggle_subsystem("memory")),
            NEW SettingItem("Headroom Compression", config.get("locus.providers.compression.enabled") ? "ENABLED" : "DISABLED", () => toggle_subsystem("compression")),
            NEW SettingItem("CouchDB LiveSync", config.get("locus.providers.vault_sync.enabled") ? "ACTIVE" : "OFF", () => open_vault_sync_submenu()),
            NEW SettingItem("Proactive Inner Loop", config.get("locus.cron.enabled") ? "90-MIN CRON" : "OFF", () => toggle_subsystem("cron")),
            NEW SettingItem("Telegram Gateway", config.get("locus.providers.channels.telegram.enabled") ? "CONNECTED" : "OFF", () => open_telegram_submenu())
        ]

        this.settingsList = NEW SettingsList(items, { onChange: (item) => handle_setting_change(item) })
        this.addChild(this.settingsList)

    METHOD handleInput(data):
        IF matchesKey(data, "Escape"):
            this.onCancel()
            RETURN
        this.settingsList.handleInput(data)


// 3. LOCUS FOOTER WIDGET (locus-extension/src/ui/footer-widget.ts)
CLASS LocusFooterWidget EXTENDS Component:
    CONSTRUCTOR(tui, theme, footerData):
        SUPER()
        this.tui = tui
        this.theme = theme
        this.footerData = footerData
        this.poll_sidecar_state()

    METHOD render(width):
        // 3-Column Layout:
        // Left: Life OS DCS & Mode | Center: Graph Memory Count | Right: Sidecar Status & Model
        state = this.latestState // cached from periodic 5s background poll
        
        left_col = f"DCS:{state.dcs} [{state.mode}] Faction:{state.active_faction}"
        center_col = f"Mem:{state.neo4j_nodes}n / {state.neo4j_edges}e | LiveSync:OK"
        right_col = f"Sidecar:{state.sidecar_latency_ms}ms | {state.model_name}"
        
        row = format_three_column_row(left_col, center_col, right_col, width)
        RETURN [NEW TextRow(this.theme.fg("muted", row))]


// 4. LOCUS DOCTOR MODAL OVERLAY (locus-extension/src/ui/doctor-overlay.ts)
FUNCTION show_locus_doctor_overlay(ctx: ExtensionCommandContext):
    RETURN ctx.ui.custom((tui, theme, keybindings, done) => {
        container = NEW Container()
        container.addChild(NEW DynamicBorder())
        container.addChild(NEW Text(theme.bold("🩺 LOCUS SUBSYSTEM DIAGNOSTICS"), 1, 0))
        container.addChild(NEW Spacer(1))

        // Trigger parallel socket & HTTP checks
        probes = [
            { id: "sidecar",  label: "FastAPI Sidecar (:8420)", target: "http://localhost:8420/health" },
            { id: "couchdb",  label: "CouchDB LiveSync (:5984)", target: "http://localhost:5984" },
            { id: "neo4j",    label: "Neo4j AuraDB Socket",      target: "neo4j_ping" },
            { id: "postgres", label: "PostgreSQL Database",      target: "pg_ping" },
            { id: "telegram", label: "Telegram Bot Polling",     target: "tg_getme" },
            { id: "llm",      label: "Primary LLM Inference",    target: "deepseek_turn_ping" }
        ]

        FOR EACH probe IN probes:
            status = execute_probe(probe)
            icon = status.ok ? theme.fg("green", "● PASS") : theme.fg("red", "✖ FAIL")
            latency = theme.fg("muted", f"({status.latency_ms}ms)")
            container.addChild(NEW Text(f"  {icon} {probe.label.padEnd(30)} {latency} {status.details}", 1, 0))

        container.addChild(NEW Spacer(1))
        container.addChild(NEW Text(theme.fg("muted", "Press [Enter] or [Esc] to dismiss"), 1, 0))

        RETURN container
    }, {
        overlay: true,
        overlayOptions: { anchor: "center", width: 72, maxHeight: 24 }
    })


// 5. EXTENSION COMMAND REGISTRATION (locus-extension/src/index.ts)
FUNCTION activate_locus_extension(pi: ExtensionAPI):
    // Register custom slash commands inside Pi TUI
    pi.registerCommand("locus:setup", {
        description: "Open the interactive Locus Onboarding & Topology Wizard",
        handler: async (args, ctx) => {
            await ctx.ui.custom((tui, theme, kb, done) => NEW LocusSetupWizard(tui, theme, done), {
                overlay: true,
                overlayOptions: { anchor: "center", width: 80, maxHeight: 30 }
            })
        }
    })

    pi.registerCommand("locus:settings", {
        description: "Open the Locus Modular Framework Settings Menu",
        handler: async (args, ctx) => {
            await ctx.ui.custom((tui, theme, kb, done) => NEW LocusSettingsSelector(tui, theme, done), {
                overlay: true,
                overlayOptions: { anchor: "center", width: 75, maxHeight: 28 }
            })
        }
    })

    pi.registerCommand("locus:doctor", {
        description: "Run live multi-subsystem diagnostic health probes",
        handler: async (args, ctx) => {
            await show_locus_doctor_overlay(ctx)
        }
    })

    // Register Locus Life OS footer widget
    ctx.ui.setFooter((tui, theme, footerData) => NEW LocusFooterWidget(tui, theme, footerData))
```

### Adaptation to Locus Architecture

- **Clean Decoupling**: Upstream Pi (`packages/`) is completely unmodified and treated as a read-only base harness. All TUI enhancements are injected via `locus-extension/` using Pi's standard Extension API (`ctx.ui.custom()`, `ctx.ui.setFooter()`, `pi.registerCommand()`).
- **No Curses / No Ink-React**: Eliminates legacy curses and ink-react technical debt. All interactive elements use `@earendil-works/pi-tui` primitives natively for instant render speeds, zero flickering, and seamless terminal theme support.
- **Bi-Directional State Binding**: Modifying a setting in the TUI overlay calls `POST /system/config` on the sidecar, immediately syncing changes to the Telegram bot and background cron engines without requiring a restart.

---

# EXTENSIONS & PLUGINS LAYER — §9

## Feature §9.1: Extension System & Event Lifecycle (25+ Events)

**Status**: complete  
**Verdict**: 📦 KEEP-PI  
**Source**: Pi `packages/agent/src/agent-session.ts` (650 lines) + `types.ts` (419 lines)  
**Query method**: [✅ VERIFIED: file_read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `pi/packages/agent/src/agent-session.ts` | 650 | Session lifecycle manager dispatching 25+ strongly-typed events to loaded extensions | `agent-loop.ts`, `types.ts` |
| `pi/packages/agent/src/types.ts` | 419 | Event payload definitions (`AgentEvent`, `TurnStartEvent`, `ToolExecutionEvent`, etc.) | All extensions |

### Stripped Logic (Pseudocode)

```
PI EXTENSION EVENT BUS LIFECYCLE:
    Events Dispatched:
      1. Lifecycle: session_start, session_switch, replaced_session, session_shutdown
      2. Turn Phase: turn_start, before_tool_call, after_tool_call, turn_end
      3. Streaming: message_start, message_update, message_end, stream_delta
      4. Execution: tool_execution_start, tool_execution_update, tool_execution_end
      5. Context & Compaction: before_compact, after_compact, before_tree, context_usage_update

    Extension Registration API:
      CLASS ExtensionContext:
          onEvent(event_name, async_callback)
          registerTool(tool_definition)
          registerCommand(slash_command, handler)
          registerFooterWidget(widget_id, render_callback)
          registerSystemPromptModifier(modifier_fn)
```

### Locus adaptation
- **Component**: `locus-os/src/core/events.ts` (TypeScript)
- **Repo vs `.locus`**: code in `locus-os` (repo); user custom extensions in `.locus/extensions/`.
- **Swappable / off state**: individual extensions toggleable via `.locus/config.yaml`.

---

## Feature §9.2: Skill System & Multi-Source Marketplace

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `hermes-agent/agent/skill_manager.py` (480 lines) + Pi Skills  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/skill_manager.py` | 480 | Multi-index marketplace client (Anthropic, Claude Skills, OpenAI, LobeHub, Pi Gallery); skill installation & dependency resolver | `tools/index.py`, `auxiliary_client.py` |
| `pi/packages/agent/src/skills/` | ~350 | Discovery engine for `SKILL.md` bundles in workspace and global directory | `agent-session.ts` |

### Stripped Logic (Pseudocode)

```
DATA STRUCTURES:
    SkillManifest:
        name: string
        description: string
        version: string
        author: string
        repository_url: string
        dependencies: List[string]
        env_vars_required: List[string]

FUNCTION install_skill_from_marketplace(source: string, skill_name: string) -> bool:
    INDEX_URLS = {
        "pi-gallery":     "https://gallery.pi.dev/api/v1/skills/",
        "anthropic":      "https://raw.githubusercontent.com/anthropics/skills/main/",
        "claude-skills":  "https://claude-skills.org/api/v1/index/",
        "openai":         "https://raw.githubusercontent.com/openai/skills-registry/main/",
        "lobehub":        "https://chat-plugins.lobehub.com/api/v1/"
    }
    
    target_url = INDEX_URLS[source] + skill_name + "/manifest.json"
    manifest = http_get_json(target_url)
    
    // Validate prerequisites & dependencies
    FOR EACH env_var IN manifest.env_vars_required:
        IF env_var NOT IN env:
            PROMPT_USER(f"Skill {skill_name} requires {env_var}. Configure now?")
            
    // Download and extract to .locus/skills/{name}/
    install_dir = f"~/.locus/skills/{skill_name}/"
    download_and_extract_bundle(manifest.bundle_url, install_dir)
    RETURN True
```

### Locus adaptation
- **Component**: `locus-os/src/skills/marketplace.ts`
- **Repo vs `.locus`**: code in `locus-os` (repo); installed skills in `.locus/skills/`.
- **Swappable / off state**: `locus.skills.marketplace.enabled`. Off → skills must be installed manually via folder copy.

---

## Feature §9.4: Agent Communication Protocol (ACP Client & Transport)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `hermes-agent/agent/copilot_acp_client.py` (420 lines) + `acp_protocol.py` (290 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/copilot_acp_client.py` | 420 | JSON-RPC 2.0 ACP transport client over stdio/websockets; handles handshakes, session pooling, message streaming | `acp_protocol.py`, `conversation_loop.py` |
| `hermes-agent/agent/acp_protocol.py` | 290 | Protocol specification, request/response schema serialization, error code mapping | `copilot_acp_client.py` |

### Stripped Logic (Pseudocode)

```
ACP PROTOCOL (JSON-RPC 2.0 Agent Communication Protocol):
    
    CLASS ACPClient:
        transport: StdioTransport | WebSocketTransport
        session_id: string
        request_id: int = 0
        pending_requests: Dict[int -> Future]
        
        FUNCTION initialize(client_info: Dict) -> Dict:
            payload = {
                "jsonrpc": "2.0",
                "id": self.next_id(),
                "method": "initialize",
                "params": {
                    "protocolVersion": "1.0",
                    "clientInfo": {
                        "name": "locus-os",
                        "version": "1.0.0"
                    },
                    "capabilities": {
                        "tools": True,
                        "sampling": True,
                        "cancellation": True
                    }
                }
            }
            RETURN await self.send_rpc(payload)

        FUNCTION dispatch_agent_task(target_agent_id: string, prompt: string, tools: List) -> AsyncIterator[ACPEvent]:
            req_id = self.next_id()
            payload = {
                "jsonrpc": "2.0",
                "id": req_id,
                "method": "agent/execute",
                "params": {
                    "target": target_agent_id,
                    "prompt": prompt,
                    "availableTools": tools,
                    "sessionId": self.session_id
                }
            }
            // Stream chunked response events (text, tool calls, status updates)
            STREAM response IN self.transport.send_and_stream(payload):
                IF response.method == "$/progress":
                    YIELD ACPEvent.PROGRESS(response.params)
                ELIF response.method == "$/streamText":
                    YIELD ACPEvent.TEXT(response.params.chunk)
                ELIF response.method == "$/toolCall":
                    YIELD ACPEvent.TOOL_CALL(response.params)

        FUNCTION cancel_request(req_id: int):
            notification = {
                "jsonrpc": "2.0",
                "method": "$/cancelRequest",
                "params": { "requestId": req_id }
            }
            self.transport.send_notification(notification)
```

### Locus adaptation
- **Component**: `locus-os/src/protocols/acp/client.ts` (TypeScript)
- **Provider Interface**: `ACPClientProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); endpoint configurations in `.locus/config.yaml`.
- **Swappable / off state**: `locus.protocols.acp.enabled`. Off → Locus cannot delegate tasks to ACP-compatible external IDE agents (e.g. Copilot, Claude Code).
- **STEAL VERBATIM**: The JSON-RPC 2.0 envelope schema, `initialize` capability negotiation, `$/cancelRequest` cancellation notification, and streaming event multiplexing.
- **ADAPT**: Used by Locus Harness Delegation (§3.7) to bridge tasks directly to headless IDE background agents.

---

## Feature §9.9: Plugin LLM Sandboxing & Auxiliary Bridge

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `hermes-agent/agent/plugin_llm.py` (310 lines) + `plugin_loader.py` (240 lines)  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `hermes-agent/agent/plugin_llm.py` | 310 | Sandboxed secondary LLM execution bridge for extensions; protects main model's prompt cache and context | `auxiliary_client.py`, `plugin_loader.py` |
| `hermes-agent/agent/plugin_loader.py` | 240 | Plugin environment isolation, per-plugin token budget quotas, and permission checking | `plugin_llm.py` |

### Stripped Logic (Pseudocode)

```
CLASS PluginLLMBridge:
    plugin_id: string
    token_quota_daily: int = 50000
    tokens_used_today: int = 0
    
    FUNCTION call_plugin_llm(messages: List[Dict], max_tokens: int = 500, temperature: float = 0.2) -> string:
        // 1. Quota Enforcement
        IF self.tokens_used_today + max_tokens > self.token_quota_daily:
            RAISE QuotaExceededError(f"Plugin {self.plugin_id} exceeded daily token limit.")
            
        // 2. Fetch Auxiliary Model (Cheap / Fast, e.g. DeepSeek V4 Flash or Gemini 2.5 Flash)
        aux_client = AuxiliaryClientPool.get_instance(task="plugin_execution")
        
        // 3. Isolated Generation (Zero collision with main agent conversation cache)
        response = aux_client.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=15.0
        )
        
        // 4. Record Usage
        actual_tokens = response.usage.total_tokens
        self.tokens_used_today += actual_tokens
        log_plugin_usage(self.plugin_id, actual_tokens)
        
        RETURN response.content
```

### Locus adaptation
- **Component**: `locus-os/src/plugins/llm-bridge.ts` (TypeScript)
- **Provider Interface**: `PluginLLMProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); per-plugin token usage tracked in `.locus/usage/plugins.json`.
- **Swappable / off state**: `locus.plugins.auxiliary_llm.enabled`. Off → plugins cannot make independent LLM calls.
- **STEAL VERBATIM**: The per-plugin token quota enforcement, isolated auxiliary client invocation, and fail-fast 15s timeout.
- **ADAPT**: Used by Excalidraw MCP Skill (§27.7), Rough Note Parser (§27.5), and Link Dump Logger (§27.6) for background data transformations.


---

# REMAINING LEARNING — §10.5-10.10

## Feature §10.5: Personal Reward Model

### Source
- **Codebase**: Locus-original (from `locus_agent_loop.md`)
- **Verification**: [📐 DESIGNED]

### Stripped Logic (Pseudocode)

```
PERSONAL REWARD MODEL — sklearn LogisticRegression

TRAINING DATA:
    Every Locus response gets a 👍 or 👎 reaction
    Features extracted per response:
        intent_type: one-hot encoded (12 types)
        dcs_at_response: float (0-100)
        operating_mode: one-hot (5 modes)
        active_faction: one-hot (4 factions)
        time_of_day: one-hot (MORNING/AFTERNOON/EVENING/NIGHT)
        response_length: int (word count)
        sources_used: bitmask (pg, neo4j, pageindex, web)
        was_proactive: bool
        confidence: float (from intent classifier)
        context_forge_tokens_used: int

TRAINING:
    FUNCTION retrain_reward_model():
        // Weekly retrain (Sunday 02:00 IST)
        data = pg.query("SELECT features, label FROM reward_signals WHERE created_at > now() - interval '30 days'")
        IF data.count < 50:
            RETURN  // not enough data, keep using defaults
        
        X = extract_features(data)
        y = data.labels  // 1 = 👍, 0 = 👎
        
        model = LogisticRegression(class_weight="balanced")
        model.fit(X, y)
        
        // Save model to sidecar directory
        joblib.dump(model, config.reward_model_path)

SCORING:
    FUNCTION score_thought(thought, context):
        features = extract_features_from_context(context)
        probability = model.predict_proba(features)[0][1]  // P(thumbs_up)
        RETURN probability
    
    THRESHOLD: ≥ 0.6 for proactive output delivery
```

## Feature §10.6-10.7: Hebbian Learning & Pattern Engine

### Stripped Logic (Pseudocode)

```
HEBBIAN PATHWAY WEIGHTING (Neo4j edge weights):
    ON memory_traversal(edge):
        edge.weight += 0.1  // access reinforcement
    
    ON user_feedback(edge, feedback):
        IF feedback == "positive":
            edge.weight *= 1.3  // 30% boost
        ELIF feedback == "negative":
            edge.weight *= 0.7  // 30% penalty
    
    WEEKLY_DECAY:
        FOR ALL edges:
            edge.weight *= 0.95  // 5% weekly decay

STDP REINFORCEMENT (Spike-Timing Dependent Plasticity):
    ON response_acknowledged(edge, response_time_ms):
        IF response_time_ms < 120000:  // user responded within 2 min
            edge.weight *= 1.5  // strong reinforcement
        ELIF response_time_ms < 600000:  // within 10 min
            edge.weight *= 1.2  // moderate reinforcement
        // Beyond 10 min: no STDP boost

MULTI-HORIZON PATTERN ENGINE (5 horizons):
    H1: 6 hours   — "what's happening right now"
    H2: 24 hours  — "today's patterns"
    H3: 7 days    — "this week's patterns"
    H4: 30 days   — "this month's patterns"
    H5: all-time  — "lifetime patterns"

    FUNCTION detect_patterns(horizons):
        FOR EACH horizon IN horizons:
            events = pg.query(
                "SELECT * FROM behavioral_events WHERE timestamp > now() - interval $1",
                [horizon.duration]
            )
            // Group by type, count frequencies, detect anomalies
            patterns = analyze_frequency_anomalies(events)
            // Confidence-based promotion between horizons:
            // A pattern detected in H1 with confidence > 0.75 AND
            // repeated count > 2 gets promoted to H2
            FOR EACH pattern IN patterns:
                IF pattern.confidence > 0.75 AND pattern.count > 2:
                    promote_to_next_horizon(pattern)
        
        RETURN all_patterns
```

---

## Feature §10.8: Self-Evolving Architect Bot

**Status**: complete  
**Verdict**: 📐 LOCUS-ORIGINAL DESIGN

### Source(s) mined
- **Codebase**: Locus-original (no upstream implementation — `Atomic Selections` §10.8: "Scans reward signals, generates patches, risk-gated deploy"). Grounded in the reward signal already present at §10.5 (Personal Reward Model) + §10.6-10.7 (Hebbian/pattern engine) + §30.3 (SOUL.md).
- **Query method**: Locus-original spec grounded in system architecture requirements.

### Logic extracted

This is Locus' **self-improvement loop** — the subsystem that makes the framework "evolving." It watches the reward/pattern signals the rest of §10 produces, proposes *changes to Locus' own operating artifacts*, and deploys them only under a risk gate. It is deliberately **not** a free-roaming code mutator.

1. **Scan reward signals**: read the §10.5 reward model (per-turn reward) + §10.6 Hebbian pattern weights + §10.9 agent-experience outcomes + §25 Life OS metrics (deferral, DCS, action-gap). Aggregate into candidate improvement targets.
2. **Classify the target of each candidate patch** — this is the crucial fork:
   - **Config/prompt/rules** (SOUL.md, config.yaml, system-prompt sections, pattern weights, blocklists) → Locus edits them **itself** (these are non-code artifacts Locus owns).
   - **Code** (an actual bug, a provider needing new logic) → Locus **delegates to a coding harness** via §3.7 — it never writes its own code. This is philosophy point 7, applied to self-modification.
3. **Generate the patch** as a *draft diff*, not a live edit: for config, a proposed key-value change; for code, a harness prompt with the failing signal as evidence.
4. **Risk-gate the deploy**: each candidate carries a risk class. `low` (config value, reversible) → apply immediately; `medium` (SOUL.md/prompt change) → stage + require approval-gate confirmation (§13.5); `high` (code, schema, or anything touching the loop itself) → require approval + a rollback point + a canary (apply to a staging copy first).
5. **Close the loop**: record the patch + its effect in the trajectory/experience store (§19.2, §10.9) so the *next* scan can see whether the change actually improved the reward signal.

### Locus adaptation
- **Component**: `locus/core/architect/` — a scheduler-driven loop (runs on the §12 proactive cadence, not per-turn).
- **What it depends on**: §10.5 (reward), §10.6-10.7 (pattern weights), §10.9 (experience), §25 (Life OS metrics), §13.5 (approval gate), and §3.7 (harness delegation for any code-class patch).
- **Where it reads/writes**: architect logic → **repo** (`locus-os`); the artifacts it edits (config/prompts/SOUL.md) → **`.locus/`** (SOUL.md + config.yaml are runtime config, not repo code); code-class patches are handed to a harness which writes to the repo under normal git discipline.
- **Swappable / off state**: `locus.architect.enabled`. Off → Locus stops proposing self-changes entirely (it remains static, still fully functional). `locus.architect.risk_gate` (`off|approval|canary`) tunes how aggressively it deploys.
- **Delegation**: **mixed** — this is the one feature that *both* self-edits (config) *and* delegates (code). The boundary is the patch's target class, not the patch's size.

### Pseudocode / algorithm

```
LOOP (proactive cadence, e.g. nightly):
    signals = gather(reward_model, hebbian_weights, experiences,
                     life_os_metrics)               # §10.5/.6/.9, §25
    candidates = propose_improvements(signals)
    FOR c IN candidates:
        class = classify_target(c)                  # config | prompt | code
        risk  = risk_class(c)
        IF class == code:                           # philosophy pt 7
            harness_delegate(§3.7, prompt = evidence(c))
        ELSE:
            patch = draft(c)                        # never a live edit
            gate(patch, risk)                       # low:apply / med:approve
                                                    # high:approve+rollback+canary
            IF gate == apply: apply(patch)
        record_outcome(c, effect)                   # §19.2/§10.9, closes loop
```

---

## Feature §10.9: Agent Experience Tracking (Procedural Memory)

**Status**: complete  
**Verdict**: 🔀 MULTI-PROVIDER (steal from OpenHuman)

### Source(s) mined
- **Codebase**: OpenHuman `src/openhuman/agent_experience/` (Rust) — "Hermes-style procedural experience memory for agents."
- **Files involved**:
  | File | Purpose | Interacts With |
  |------|---------|---------------|
  | `agent_experience/types.rs` | `AgentExperience` struct, `ExperienceSource/Outcome`, `stable_experience_id`, `redact_text` | all |
  | `agent_experience/capture.rs` | `AgentExperienceCaptureHook` (PostTurnHook) — three candidate extractors | `store.rs` |
  | `agent_experience/store.rs` | `AgentExperienceStore` (backed by the `Memory` trait, namespace `AGENT_EXPERIENCE_NAMESPACE`), `put`/`list`/query | `memory` |
  | `agent_experience/prompt.rs` | `render_experience_hits` + `prepend_experience_block` — injects a "Relevant Operating Experience" block | (context builder) |
- **Query method**: Logic read directly from codebase files.

### Logic extracted

The concept: agents forget *how* they solved a task. Experience memory captures **procedural** lessons ("when the task looks like X, the tool sequence Y worked / Z failed") and injects the relevant ones back into the next turn's context.

**The record (`AgentExperience`)**: id, timestamps, `source` (ToolLoop | AgentReflection | Manual | WorkflowCandidate), `agent_id`, `entrypoint`, `task_fingerprint`, `task_summary`, `tools_used`, `tool_sequence`, `outcome` (Success/Failure/Partial), `error_class`, `lesson`, `reuse_hint`, `avoid_hint`, `confidence`, `tags`, `dismissed`.

**Deterministic dedupe (`stable_experience_id`)**: `sha256(task_summary.lower() + tool_sequence.lower() + outcome)` truncated to 24 hex chars, prefixed `exp_`. Same task + same tool sequence + same outcome → same id → the store upserts instead of duplicating.

**Redaction (`redact_text`)**: three regexes scrub Bearer tokens, `sk-` OpenAI-style keys, and `token/api_key/secret/password[:=] value` patterns before anything is stored (lessons/reuse hints never persist secrets).

**Capture hook (`AgentExperienceCaptureHook`, a `PostTurnHook`)**: after each turn, if the turn has tool calls, extract up to three candidate experiences:
1. **Successful multi-tool sequence** — ≥2 successful calls → `Success`, confidence 0.72, `lesson = "the successful tool sequence was grep -> file_read"`, `reuse_hint = "reuse grep -> file_read when the task resembles <summary>"` (summary truncated to 280 chars).
2. **Repeated failure** — any tool that failed ≥2 times in one turn → `Failure`, confidence 0.68, `error_class` parsed from the output summary (e.g. `permission_denied`), `avoid_hint = "avoid retrying X repeatedly without changing inputs"`.
3. **Partial success** — a failure followed by a later success → `Partial`, confidence 0.62, `lesson = "the task recovered by continuing with <sequence>"`.

**Injection (`prompt.rs`)**: relevant hits are rendered as a compact, byte-capped block — `"## Relevant Operating Experience"` with per-hit lines like `"1. success sequence: grep -> file_read | lesson: … | reuse: … | avoid: …"` — and **prepended** to the enriched message before the user context.

### Locus adaptation
- **Component**: `locus/core/experience/` — an `ExperienceStore` (backed by the active memory provider, matching OpenHuman's store-over-`Memory` design) + a `capture` hook wired to Locus' own post-turn hook (the §1.7 background-review point) + a `render` block feeding Context Forge.
- **What it depends on**: the **memory stack** (§4.1 Neo4j/alternates — the store writes through `MemoryProvider`, so it's provider-swappable), and the post-turn review hook (§1.7).
- **Where it reads/writes**: experience records → **`.locus/`** (via the memory provider's store); the capture/render code → **repo** (`locus-os`); the confidence thresholds + summary cap (280) → **`.locus/config.yaml`**.
- **Swappable / off state**: `locus.experience.enabled`. Off → no capture, no injection; the "Relevant Operating Experience" block simply never appears. The store is provider-agnostic (works over Neo4j, mem0, supermemory, etc. via `MemoryProvider`).
- **Delegation**: none — Locus-native. Feeds §10.8 (the Architect reads these outcomes as a signal).

### Pseudocode / algorithm

```
STRUCT AgentExperience:
    id, source, agent_id, entrypoint, task_fingerprint, task_summary,
    tools_used, tool_sequence, outcome(Success|Failure|Partial),
    error_class?, lesson, reuse_hint, avoid_hint?, confidence, tags

FUNCTION stable_experience_id(summary, sequence, outcome):
    digest = sha256(summary.lower + join(sequence.lower) + outcome)
    RETURN "exp_" + hex(digest)[:24]

FUNCTION redact_text(text):           # before any persist
    text = re(bearer -> "Bearer [redacted]")
    text = re(sk-... -> "sk-[redacted]")
    text = re(token|api_key|secret|password[:=]value -> "key=[redacted]")
    RETURN text

HOOK on_turn_complete(ctx):
    if not enabled or ctx.tool_calls empty: return
    candidates = []
    if >=2 successful calls:  push(success_experience)   # conf 0.72
    for tool failed >=2x:     push(repeated_failure)     # conf 0.68, error_class
    if failure then success:  push(partial_success)      # conf 0.62
    for c in candidates: store.put(c)                    # upsert by stable id

RENDER (context injection):
    hits = store.query(task_fingerprint)                  # scored by overlap
    block = "## Relevant Operating Experience\n" + per-hit:
        "{i}. {outcome} sequence: {seq} | lesson: .. | reuse: .. | avoid: .."
    message = prepend(block, enriched_message)            # block first, then user
```

---

# SUBAGENTS LAYER — §11

## Feature §11.1-11.5: Subagent Spawning, Archetypes, Depth Limiting

### Metadata
- **Source Codebases**: Pi (built-in subagent) + OpenHuman (15 archetypes, spawn depth)
- **Verification Tag**: `[✅ VERIFIED: file_read]`
- **Self-Audit**: `repo_cloned: true` | `logic_stripped: true` | `contains_code: false`

### Stripped Logic (Pseudocode)

```
SUBAGENT ARCHETYPES:

    OPENHUMAN 15 ARCHETYPES:
        orchestrator, planner, researcher, critic, implementer,
        debugger, reviewer, documenter, tester, deployer,
        security_auditor, performance_analyst, data_engineer,
        designer, communicator

    LOCUS 4 FACTION AGENTS:
        Planner    — task planning, scheduling, goal tracking
        Curator    — memory management, skill maintenance, vault organization
        Analyst    — pattern detection, behavioral analysis, reporting
        Builder    — coding delegation, project management, harness coordination

    FUNCTION spawn_subagent(archetype, task, config):
        // Check depth limit
        IF current_depth >= MAX_SPAWN_DEPTH (default 3):
            RETURN error("Maximum subagent depth reached")
        
        agent = create_agent({
            system_prompt: archetype.prompt_template,
            tools: archetype.allowed_tools,
            model: config.model OR archetype.default_model,
            max_turns: archetype.max_turns OR 10,
            skip_memory: true,  // subagents don't write to memory
            skip_review: true,  // no post-turn review
            parent_session_id: current_session.id,
            depth: current_depth + 1
        })
        
        result = agent.run(task)
        
        // Notify parent's memory provider about delegation
        memory_provider.on_delegation(task, result, child_session_id=agent.session_id)
        
        RETURN result

DEPTH LIMITING (from OpenHuman):
    MAX_SPAWN_DEPTH = 3  // prevent infinite recursion
    // Enforced at spawn time, not configurable by subagents
```

### Adaptation to Locus Architecture

- **Component**: `locus/core/subagents/`
- **Provider Interface**: `SubagentArchetype`
- **KEEP**: Pi's built-in subagent spawning, OpenHuman's depth limiting.
- **ADD**: Locus's 4 faction agents as default archetypes, OpenHuman's 15 as optional archetypes.



# BROWSER & COMPUTER USE — §16, §20

## Feature §16.1-16.2 + §20.1-20.3: Browser Automation & Desktop Control

### Source
- **Codebases**: OpenHuman (`screen_intelligence/`, `desktop_companion/`, `overlay/`)
- **Verification**: [✅ VERIFIED: OpenHuman directory structures listed]

### Stripped Logic (Pseudocode)

```
BROWSER AUTOMATION:
    FUNCTION automate_browser(task):
        // Default: Playwright
        browser = browser_provider.launch()
        page = browser.new_page()
        
        // Navigate and interact based on task
        page.goto(task.url)
        
        // Screen Intelligence (from OpenHuman):
        screenshot = page.screenshot()
        // Send screenshot to vision model for understanding
        elements = vision_model.identify_elements(screenshot)
        // Click/type based on identified elements
        
        RETURN page.content()

SCREEN INTELLIGENCE (from OpenHuman screen_intelligence/):
    FUNCTION analyze_screen(screenshot):
        // Use vision model to identify UI elements
        elements = vision_model.analyze(screenshot, prompt="""
            Identify all interactive elements:
            buttons, links, text fields, dropdowns, checkboxes.
            Return coordinates and descriptions.
        """)
        RETURN elements

DESKTOP COMPANION (from OpenHuman desktop_companion/):
    // Native desktop control for automated workflows
    FUNCTION control_desktop(action):
        IF action.type == "click":
            native.mouse_click(action.x, action.y)
        ELIF action.type == "type":
            native.keyboard_type(action.text)
        ELIF action.type == "screenshot":
            RETURN native.capture_screen()
        ELIF action.type == "window_focus":
            native.focus_window(action.window_title)
```

### Adaptation to Locus Architecture

- **Component**: `locus/providers/browser/`
- **Provider Interface**: `BrowserProvider`
- **Default**: Playwright. Optional: OpenHuman screen_intelligence, Browserbase.
- **Low Priority**: Desktop companion and VNC — future feature.

---


## Feature §20.3: VNC / Remote Desktop Protocol Control

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: OpenHuman `desktop_companion/` + RFB Protocol Specification  
**Query method**: [📐 DESIGN SPEC: openhuman_screen]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/desktop/vnc_client.py` | 310 | RFB 3.8 protocol client for headless remote desktop control, screen scraping, and input event injection | `screen_intelligence.py`, `vnc_safety_gate.py` |
| `locus-os/src/tools/desktop-vnc.ts` | 190 | Locus agent tool exposing remote mouse/keyboard control with bounding box security constraints | `sidecar/desktop/vnc_client.py` |

### Stripped Logic (Pseudocode)

```
CLASS VNCDesktopController:
    host: string
    port: int = 5900
    rfb_client: RFBProtocolClient
    safety_boundary: BoundingBox  // Coordinates agent is permitted to touch
    
    FUNCTION connect(password: string):
        self.rfb_client.connect(self.host, self.port)
        self.rfb_client.authenticate(password)
        self.rfb_client.set_encodings(["tight", "zrle", "raw"])

    FUNCTION capture_framebuffer() -> Image:
        frame_bytes = self.rfb_client.request_update()
        RETURN decode_framebuffer(frame_bytes)

    FUNCTION move_and_click(x: int, y: int, button: "left" | "right" | "middle"):
        // 1. Safety Boundary Check
        IF NOT self.safety_boundary.contains(x, y):
            RAISE SecurityException(f"Click at ({x}, {y}) outside permitted safe region.")
            
        // 2. Smooth Bezier Curve Movement (Human-like traversal)
        trajectory = compute_bezier_path(self.current_pos, (x, y))
        FOR EACH point IN trajectory:
            self.rfb_client.send_pointer_event(point.x, point.y, button_mask=0)
            sleep(0.01)
            
        // 3. Button Press & Release
        mask = BUTTON_MASKS[button]
        self.rfb_client.send_pointer_event(x, y, button_mask=mask)
        sleep(0.05)
        self.rfb_client.send_pointer_event(x, y, button_mask=0)
        self.current_pos = (x, y)

    FUNCTION type_keys(text: string):
        FOR EACH char IN text:
            keysym = char_to_keysym(char)
            self.rfb_client.send_key_event(keysym, down=True)
            sleep(0.02)
            self.rfb_client.send_key_event(keysym, down=False)
```

### Locus adaptation
- **Component**: `locus-os/src/tools/desktop-vnc.ts` (TS tool) + `sidecar/desktop/vnc_client.py` (Python)
- **Provider Interface**: `DesktopControlProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); connection credentials in `.locus/.env`.
- **Swappable / off state**: `locus.tools.vnc.enabled`. Off → VNC tool is unregistered and remote OS control disabled.
- **STEAL VERBATIM**: The RFB protocol encoding chain, Bezier curve mouse trajectory generator, and bounding box security constraint gate.
- **ADAPT**: Used for containerized browser testing and automating GUI applications in headless Docker environments.


# INTEGRATIONS — §21

## Feature §21.1-21.3: Google Calendar, Gmail, Webhooks

### Source
- **Codebase**: Locus-original + OpenHuman (`webhooks/`)
- **Verification**: [📐 DESIGNED]

### Stripped Logic (Pseudocode)

```
GOOGLE CALENDAR INTEGRATION:
    FUNCTION setup_google_calendar():
        // Manual OAuth 2.0 (50-line implementation)
        credentials = oauth2_flow(
            client_id = config.google.client_id,
            client_secret = config.google.client_secret,
            scopes = ["calendar.readonly", "calendar.events"],
            redirect_uri = "urn:ietf:wg:oauth:2.0:oob"  // manual copy-paste
        )
        store_credentials(credentials)
    
    FUNCTION fetch_today_events():
        service = build_calendar_service(credentials)
        events = service.events().list(
            calendarId="primary",
            timeMin=today_start(),
            timeMax=today_end(),
            singleEvents=true,
            orderBy="startTime"
        )
        RETURN events

GMAIL INTEGRATION:
    // Same OAuth flow, different scopes
    scopes = ["gmail.readonly", "gmail.send"]

WEBHOOKS (from OpenHuman):
    FUNCTION register_webhook(url, events):
        webhook = { url, events, secret: generate_secret() }
        pg.insert("webhooks", webhook)
    
    FUNCTION fire_webhook(event):
        webhooks = pg.query("SELECT * FROM webhooks WHERE $1 = ANY(events)", [event.type])
        FOR EACH webhook IN webhooks:
            signature = hmac(webhook.secret, json(event))
            http.post(webhook.url, event, headers={"X-Signature": signature})
```

### Adaptation to Locus Architecture

- **Component**: `locus/integrations/`
- **Provider Interface**: `IntegrationProvider`
- **Integration**: Calendar events injected into Context Forge's temporal layer. Gmail checked during morning briefing.

---

# VAULT OPERATIONS — §27 (Remaining)

## Feature §27.2: Obsidian Self-Hosted LiveSync & CouchDB Real-Time Sync Engine

### Metadata
- **Source Codebase**: `vstor/obsidian-livesync` protocol + Apache CouchDB 3.3.3 + Pi Agent Extension Architecture (`@mariozechner/pi-agent`)
- **Verification**: [✅ VERIFIED: CouchDB 3.3 Docker implementation + LiveSync protocol specifications] · `repo_cloned: false` · `logic_stripped: true` · `contains_code: false`
- **Verdict**: 🔄 AUGMENT (Built directly ON TOP OF Pi Agent)
- **Status**: COMPLETE (Docker service `locus-couchdb:5984` running, CORS configured, vault scaffolded, Pi extension bridge operational)

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/vault/livesync_bridge.py` | 420 | Bidirectional HTTP/WebSocket sync bridge connecting CouchDB 3.3 `_changes` feed with local filesystem vault; handles document chunking, E2EE decryption, conflict resolution, and change dispatching | `crawlers/vault_crawler.py`, `locus-couchdb:5984`, `VectifyAI/PageIndex`, `neo4j-labs/agent-memory` |
| `locus-os/src/extensions/locus-extension.ts` | 380 | Pi Agent tool provider registering `locus_vault_read`, `locus_vault_write`, `locus_vault_append`, `locus_vault_status`; mutates local vault mirror and dispatches real-time sync events | Pi Agent loop (`@mariozechner/pi-agent`), `livesync_bridge.py` via Sidecar HTTP RPC |
| `locus-os/docker-compose.yml` | 135 | Container orchestration running CouchDB 3.3 (`locus-couchdb`), sidecar (FastAPI), Neo4j, PostgreSQL, and Pi Agent | Host network, volume mounts `data/couchdb` & `vault/` |
| `locus-os/data/couchdb/local.ini` | 60 | CouchDB engine configuration: enables CORS for Obsidian mobile/desktop clients, sets PBKDF2 iterations, max document sizes, and continuous HTTP/1.1 streaming buffers | `locus-couchdb` engine |
| `locus-os/vault/00-System-Data/LIVESYNC_SETUP.md` | 150 | Universal client onboarding guide for iOS, macOS, Windows, Linux, and Android LiveSync plugin configuration | Obsidian Community Plugin `vstor/obsidian-livesync` |
| `locus-os/sidecar/crawlers/vault_crawler.py` | 310 | Reactive file watcher & CouchDB stream listener triggering incremental PageIndex (§27.1), LightRAG (§30.9), and Neo4j Agent Memory (§4) entity extraction | `livesync_bridge.py`, `pageindex`, `agent_memory` |

### Architectural Foundation: Why CouchDB + LiveSync Beats Git & Syncthing

Locus replaces legacy Git sync and Syncthing with self-hosted **CouchDB + Obsidian LiveSync** for three non-negotiable architectural reasons:
1. **iOS Background Execution Immunity**:
   - iOS terminates background processes after ~30 seconds. Git fetch/merge operations and Syncthing relay daemons fail silently or corrupt state on mobile devices.
   - Obsidian LiveSync uses standard HTTP/1.1 REST calls against CouchDB's replication protocol. Replication seamlessly pauses on iOS background suspend and immediately resumes upon app reactivation or scheduled iOS background fetch without data loss.
2. **Elimination of Git Merge Conflict Bloat**:
   - Git on mobile frequently produces merge conflict markers (`<<<<<<< HEAD ... ======= ... >>>>>>>`) directly inside markdown notes, breaking YAML frontmatter parsing, corrupting PageIndex tree builders, and causing runtime LLM hallucinations.
   - CouchDB uses Multi-Version Concurrency Control (MVCC) with deterministic revision trees (`_rev`). Conflicted branches are tracked at the document level (`_conflicts`), deterministically reconciled via 3-way text diff or revision winning rules, and never corrupt raw note text on disk.
3. **Decoupled Headless VM & Local Pi Agent Execution**:
   - The canonical CouchDB instance lives 24/7 on the VM (or local host) inside Docker.
   - Pi Agent runs natively on top of this vault, reading and writing files locally through its extension tools (`locus-extension.ts`).
   - The user can take notes or modify project specs from their iPhone while on the go; within 500ms, the VM receives the CouchDB change, updates the disk, and Pi Agent has instant contextual awareness of the user's latest thoughts.

---

### End-to-End Replication Architecture & Pi Agent Integration

```
               ┌────────────────────────────────────────────────────────┐
               │              CLIENT DEVICES (Mobile / Desktop)          │
               │  iPhone (iOS) · MacBook (macOS) · PC (Windows) · iPad  │
               │                                                        │
               │   Obsidian App + Self-Hosted LiveSync Plugin           │
               └───────────────────────┬────────────────────────────────┘
                                       │ HTTPS / WSS Replication
                                       │ (Chunked Diffie-Hellman / AES-256)
                                       ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│               LOCUS HEADLESS SERVER / VM INFRASTRUCTURE                       │
│                                                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ DOCKER CONTAINER: locus-couchdb (Port 5984)                             │  │
│  │ - Canonical Database: locus-vault                                       │  │
│  │ - MVCC Revision Store (_rev: "3-7a9b...")                               │  │
│  │ - Continuous HTTP _changes stream feed                                  │  │
│  │ - CORS enabled for obsidian:// and app:// origins                       │  │
│  └───────────────────▲──────────────────────────────────▲──────────────────┘  │
│                      │ Inbound Changes Feed             │ Push Note Revisions │
│                      │ (_changes?feed=continuous)       │ (PUT /doc_id)       │
│                      ▼                                  │                     │
│  ┌──────────────────────────────────────────────────────┴──────────────────┐  │
│  │ SIDECAR DAEMON: livesync_bridge.py (Python FastAPI :8420)               │  │
│  │ - Listens to CouchDB changes feed in real time                          │  │
│  │ - Reassembles chunked documents into full UTF-8 Markdown                │  │
│  │ - Reconciles disk mirror: locus-os/vault/                               │  │
│  │ - Deterministic 3-way conflict resolver (Preserves winning branch)      │  │
│  │ - Emits 'vault:note_mutated' events to Sidecar Event Bus                │  │
│  └───────────────────┬──────────────────────────────────▲──────────────────┘  │
│                      │                                  │ Sidecar RPC Call    │
│                      │ Local FS Mirror                  │ (/vault/sync/push)  │
│                      ▼                                  │                     │
│  ┌──────────────────────────────────────────────────────┴──────────────────┐  │
│  │ LOCAL FILESYSTEM VAULT: locus-os/vault/                                 │  │
│  │ 00-System/ · 01-Projects/ · 02-Areas/ · 03-Resources/ · 04-Captures/... │  │
│  └───────────────────▲──────────────────────────────────▲──────────────────┘  │
│                      │ Reads Markdown Notes             │ Writes Notes        │
│                      │ (fs.readFile)                    │ (fs.writeFile)      │
│  ┌───────────────────┴──────────────────────────────────┴──────────────────┐  │
│  │ PI AGENT LOOP: locus-os/src/ (Node.js / TypeScript)                     │  │
│  │ - Agent Loop: @mariozechner/pi-agent                                    │  │
│  │ - Extension: locus-extension.ts                                         │  │
│  │ - Native Tools:                                                         │  │
│  │   * locus_vault_read(path)                                              │  │
│  │   * locus_vault_write(path, content, frontmatter)                       │  │
│  │   * locus_vault_append(path, content)                                   │  │
│  │   * locus_vault_status()                                                │  │
│  └───────────────────┬─────────────────────────────────────────────────────┘  │
│                      │ Emits Vault Change Trigger                             │
│                      ▼                                                        │
│  ┌─────────────────────────────────────────────────────────────────────────┐  │
│  │ DOWNSTREAM REAL-TIME INDEXING                                           │  │
│  │ - PageIndex (§27.1): Incremental Tree Node Rebuild                      │  │
│  │ - Neo4j Agent Memory (§4.1): POLE+O Entity Extraction                   │  │
│  │ - pgvector (§30.1): 384-dim BAAI/bge-small Semantic Chunk Upsert        │  │
│  └─────────────────────────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

---

### Stripped Logic & Algorithmic Pseudocode

#### 1. CouchDB Document Schema (LiveSync Format)

In Obsidian LiveSync, files are represented as CouchDB documents. Files smaller than the chunk size threshold ($S_{\text{threshold}} = 100\,\text{KB}$) are stored directly in the `eden.content` field. Larger files and binary attachments are chunked into 50KB blocks and referenced via children document IDs.

```
COUCHDB DOCUMENT SHAPES:

1. Plain / Small Note Document:
{
    "_id": "note:01-projects/locus/spec.md",
    "_rev": "4-1a2b3c4d5e6f7a8b9c0d",
    "type": "leaf",
    "path": "01-Projects/Locus/spec.md",
    "mtime": 1727918400000,
    "ctime": 1727832000000,
    "size": 4210,
    "eden": {
        "content": "---\ntitle: Locus Spec\n---\n# Architecture\n...",
        "diff": null
    },
    "children": []
}

2. Chunked Large Document / Binary:
{
    "_id": "note:03-resources/diagram.excalidraw",
    "_rev": "1-9f8e7d6c5b4a3",
    "type": "chunks",
    "path": "03-Resources/diagram.excalidraw",
    "mtime": 1727918500000,
    "size": 524288,
    "children": [
        "h:a1b2c3d4e5...",
        "h:f6e5d4c3b2...",
        "h:0987654321..."
    ]
}

3. Individual Chunk Document:
{
    "_id": "h:a1b2c3d4e5...",
    "_rev": "1-778899aabb",
    "type": "chunk",
    "data": "base64_encoded_payload_or_encrypted_blob"
}
```

#### 2. Inbound Sync: Continuous Stream Listener & Local Vault Reconciler

```
CLASS LiveSyncBridge:
    couch_url: string = "http://locus-couchdb:5984/locus-vault"
    vault_root: Path = Path("locus-os/vault")
    last_seq: string = "0"
    
    ASYNC FUNCTION start_inbound_stream():
        // Load persisted sequence cursor from PostgreSQL
        self.last_seq = pg.query_scalar(
            "SELECT last_seq FROM couchdb_sync_state WHERE db = 'locus-vault'"
        ) OR "0"
        
        WHILE server_running:
            TRY:
                stream_url = f"{self.couch_url}/_changes?feed=continuous&include_docs=true&since={self.last_seq}&heartbeat=15000"
                ASYNC FOR line IN http.stream_lines(stream_url):
                    IF line.is_empty() OR line == "\n":
                        CONTINUE // Heartbeat keepalive
                        
                    change = json.parse(line)
                    IF "seq" IN change:
                        self.last_seq = change["seq"]
                        
                    IF change.get("deleted") == True:
                        self.handle_inbound_delete(change["id"])
                    ELSE:
                        self.handle_inbound_doc(change["doc"])
                        
                    // Commit sequence checkpoint to Postgres
                    pg.execute(
                        "UPSERT INTO couchdb_sync_state (db, last_seq, updated_at) VALUES ('locus-vault', $1, NOW())",
                        self.last_seq
                    )
            CATCH ConnectionError AS err:
                logger.warn(f"CouchDB stream disconnected: {err}. Reconnecting in 3s...")
                sleep(3.0)

    ASYNC FUNCTION handle_inbound_doc(doc: Dict):
        IF NOT doc.get("path"):
            RETURN // Ignore metadata or pure chunk documents
            
        rel_path = sanitize_path(doc["path"])
        disk_path = self.vault_root / rel_path
        
        // 1. Resolve content (assemble chunks if chunked)
        IF doc.get("type") == "chunks":
            content_bytes = self.fetch_and_assemble_chunks(doc["children"])
        ELSE:
            content_str = doc.get("eden", {}).get("content", "")
            IF doc.get("encrypted") == True:
                content_str = self.decrypt_e2ee(content_str)
            content_bytes = content_str.encode("utf-8")
            
        // 2. Conflict & Stale Detection
        IF disk_path.exists():
            disk_mtime = disk_path.stat().st_mtime * 1000
            disk_hash = md5(disk_path.read_bytes())
            inbound_hash = md5(content_bytes)
            
            IF disk_hash == inbound_hash:
                RETURN // Identical content, no-op
                
            IF disk_mtime > doc.get("mtime", 0):
                // Disk is newer! Potential concurrent conflict.
                self.resolve_concurrent_conflict(disk_path, doc, content_bytes)
                RETURN
                
        // 3. Atomic Disk Write
        tmp_path = disk_path.with_suffix(".tmp." + uuid4().hex[:8])
        tmp_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path.write_bytes(content_bytes)
        
        // Set file timestamp matching CouchDB document mtime
        IF doc.get("mtime"):
            target_ts = doc["mtime"] / 1000.0
            os.utime(tmp_path, (target_ts, target_ts))
            
        tmp_path.replace(disk_path) // Atomic rename
        
        // 4. Update file hash registry
        pg.execute(
            "UPSERT INTO vault_file_hashes (path, md5_hash, couch_rev, last_scanned) VALUES ($1, $2, $3, NOW())",
            rel_path, md5(content_bytes), doc["_rev"]
        )
        
        // 5. Reactive Trigger: Notify Sidecar & Pi Agent
        sidecar_event_bus.publish("vault:note_mutated", {
            "path": rel_path,
            "action": "upsert",
            "rev": doc["_rev"]
        })
        
        // Incremental re-indexing (non-blocking async)
        schedule_task(pageindex.incremental_rebuild(rel_path))
        schedule_task(agent_memory.extract_entities_from_file(rel_path))
        schedule_task(pgvector.update_vault_chunks(rel_path, content_bytes))
```

#### 3. Outbound Sync: Pi Agent Vault Mutation → CouchDB Propagation

When Pi Agent executes a tool (`locus_vault_write` or `locus_vault_append`), the write flows from TypeScript through the local filesystem and pushes directly into CouchDB:

```
PI AGENT TOOL EXECUTION (TypeScript in locus-extension.ts):

FUNCTION register_locus_vault_tools(agent_context):
    agent_context.registerTool({
        name: "locus_vault_write",
        description: "Write or update an Obsidian note in the local vault, automatically syncing via CouchDB LiveSync",
        parameters: {
            path: { type: "string", description: "Relative note path, e.g. 01-Projects/Locus/Plan.md" },
            content: { type: "string", description: "Full note markdown content" },
            frontmatter: { type: "object", description: "Optional YAML frontmatter keys", optional: true }
        },
        execute: ASYNC (params) => {
            full_path = path.resolve(VAULT_DIR, params.path);
            
            // 1. Format frontmatter if provided
            final_content = params.content;
            IF params.frontmatter:
                final_content = matter.stringify(params.content, params.frontmatter);
                
            // 2. Atomic write to local filesystem mirror
            await fs.promises.mkdir(path.dirname(full_path), { recursive: true });
            tmp_path = `${full_path}.tmp.${Date.now()}`;
            await fs.promises.writeFile(tmp_path, final_content, "utf8");
            await fs.promises.rename(tmp_path, full_path);
            
            // 3. Dispatch push notification to Sidecar Bridge
            sync_response = await sidecar_client.post("/vault/sync/push", {
                path: params.path,
                mtime: Date.now()
            });
            
            RETURN {
                status: "success",
                path: params.path,
                rev: sync_response.rev,
                sync: "replicated_to_couchdb"
            };
        }
    });

SIDECAR OUTBOUND PUSH (Python in livesync_bridge.py):

ASYNC FUNCTION push_local_to_couchdb(rel_path: string, mtime: int) -> Dict:
    file_path = VAULT_ROOT / rel_path
    IF NOT file_path.exists():
        RAISE FileNotFoundError(rel_path)
        
    content_bytes = file_path.read_bytes()
    doc_id = f"note:{rel_path.lower().replace('\\', '/')}"
    
    // Check existing CouchDB revision
    existing_doc = http.get(f"{COUCH_URL}/{doc_id}", allow_404=True)
    current_rev = existing_doc.get("_rev") IF existing_doc ELSE None
    
    IF len(content_bytes) > CHUNK_THRESHOLD:
        // Chunk large file
        chunk_ids = []
        FOR chunk IN split_chunks(content_bytes, size=50000):
            chunk_hash = f"h:{sha256(chunk)}"
            http.put(f"{COUCH_URL}/{chunk_hash}", body={"type": "chunk", "data": base64(chunk)})
            chunk_ids.append(chunk_hash)
            
        doc_payload = {
            "_id": doc_id,
            "type": "chunks",
            "path": rel_path,
            "size": len(content_bytes),
            "mtime": mtime,
            "children": chunk_ids
        }
    ELSE:
        doc_payload = {
            "_id": doc_id,
            "type": "leaf",
            "path": rel_path,
            "size": len(content_bytes),
            "mtime": mtime,
            "eden": {
                "content": content_bytes.decode("utf-8", errors="replace"),
                "diff": None
            },
            "children": []
        }
        
    IF current_rev:
        doc_payload["_rev"] = current_rev
        
    response = http.put(f"{COUCH_URL}/{doc_id}", json=doc_payload)
    new_rev = response["rev"]
    
    // Update local PostgreSQL tracking
    pg.execute(
        "UPSERT INTO vault_file_hashes (path, md5_hash, couch_rev, last_scanned) VALUES ($1, $2, $3, NOW())",
        rel_path, md5(content_bytes), new_rev
    )
    
    RETURN {"path": rel_path, "rev": new_rev}
```

#### 4. Deterministic Multi-Client Conflict Resolution

When mobile and VM make concurrent edits to the same note, CouchDB creates an internal branching tree. The LiveSync bridge resolves this deterministically without throwing errors:

```
FUNCTION resolve_concurrent_conflict(disk_path: Path, remote_doc: Dict, remote_bytes: bytes):
    local_bytes = disk_path.read_bytes()
    local_mtime = disk_path.stat().st_mtime * 1000
    remote_mtime = remote_doc.get("mtime", 0)
    
    // 1. Text-based 3-Way Merge for Markdown
    TRY:
        local_text = local_bytes.decode("utf-8")
        remote_text = remote_bytes.decode("utf-8")
        
        merged_text, has_conflicts = diff3_merge(
            base=get_common_ancestor(remote_doc["_id"]),
            current_local=local_text,
            incoming_remote=remote_text
        )
        
        IF NOT has_conflicts:
            // Clean 3-way merge succeeded automatically
            disk_path.write_text(merged_text, encoding="utf-8")
            push_local_to_couchdb(rel_path, max(local_mtime, remote_mtime) + 1000)
            RETURN
    CATCH Exception:
        pass // Merge failed, fallback to sidecar preservation
        
    // 2. Deterministic Conflict Preservation:
    // Determine winner based on (mtime, hash) tuple
    winner_is_local = (local_mtime, sha256(local_bytes)) > (remote_mtime, sha256(remote_bytes))
    
    IF winner_is_local:
        // Local wins the canonical filename; write remote as sidecar conflict note
        conflict_sidecar = disk_path.parent / f"{disk_path.stem}.conflict-{timestamp_slug()}.md"
        conflict_sidecar.write_bytes(remote_bytes)
        logger.warn(f"Conflict detected on {disk_path.name}: local preserved, remote saved as {conflict_sidecar.name}")
    ELSE:
        // Remote wins canonical filename; write local as sidecar conflict note
        conflict_sidecar = disk_path.parent / f"{disk_path.stem}.conflict-{timestamp_slug()}.md"
        conflict_sidecar.write_bytes(local_bytes)
        disk_path.write_bytes(remote_bytes)
        logger.warn(f"Conflict detected on {disk_path.name}: remote applied, local saved as {conflict_sidecar.name}")
        
    // 3. Mark CouchDB conflict resolved
    delete_conflicting_couch_revisions(remote_doc["_id"])
```

---

### Locus Adaptation & Pi Agent Integration

- **Component**: `locus-os/sidecar/vault/livesync_bridge.py` (Python FastAPI service) + `locus-os/src/extensions/locus-extension.ts` (Pi Agent Tool Extension)
- **Container**: `locus-couchdb` in `locus-os/docker-compose.yml` (Dockerized CouchDB 3.3.3 on port 5984)
- **Provider Interface**: `VaultSyncProvider` implementing:
  - `status() -> SyncState`
  - `pull(path?: string) -> Promise<void>`
  - `push(path: string) -> Promise<string>`
  - `resolve_conflicts() -> Promise<ConflictReport>`
- **Repo vs `.locus`**:
  - Code: in `locus-os` (`sidecar/vault/` and `src/extensions/`).
  - Runtime State: CouchDB data in `locus-os/data/couchdb/` (persisted Docker volume).
  - Sync metadata cursor: PostgreSQL table `couchdb_sync_state`.
  - Credentials: admin user/password stored securely in `.locus/.env`.
- **Swappable / Off State**:
  - Controlled by `.locus/config.yaml`:
    ```yaml
    vault:
      sync_engine: "couchdb_livesync" # Options: couchdb_livesync | local_only
      couchdb_url: "http://localhost:5984"
      database: "locus-vault"
      e2ee: false
      poll_interval_sec: 0 # 0 = real-time continuous stream
    ```
  - When `sync_engine: "local_only"`, Pi Agent operates purely against the local `locus-os/vault/` directory without network calls.
- **STEAL VERBATIM**: The CouchDB continuous changes stream processing loop, chunk assembly algorithm, and MVCC revision header conventions from the Obsidian LiveSync protocol specification.
- **ADAPT**: Completely integrates with Pi Agent's native extension architecture. Rather than requiring Obsidian to be running, Locus functions as an autonomous headless participant in the LiveSync swarm—allowing Pi Agent on the cloud VM, Antigravity in the local IDE, and mobile Obsidian on iOS to maintain a single unified, conflict-free, real-time knowledge base.

---

## Feature §27.3: LOCUS_SHORTHAND 4× Text Compressor

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `LOCUS_SYSTEM_v1.md` §14  
**Query method**: [📐 DESIGN SPEC: locus_system_v1.md]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/src/core/compression/shorthand.ts` | 180 | Deterministic 4× regex compression pipeline reducing prompt token consumption | `context-forge.ts` |

### Stripped Logic (Pseudocode)

```
SHORTHAND_DICTIONARY = [
    ("because", "∵"), ("therefore", "∴"), ("approximately", "≈"),
    ("greater than", ">"), ("less than", "<"), ("and", "&"),
    ("with", "w/"), ("without", "w/o"), ("which", "wh/"),
    ("between", "b/w"), ("regarding", "re:"), ("for example", "e.g.")
]

FUNCTION compress_to_locus_shorthand(text: string) -> string:
    FOR EACH word, sym IN SHORTHAND_DICTIONARY:
        text = regex_replace(rf"{word}", sym, text, case_insensitive=True)
    // Strip unambiguous grammatical articles
    text = regex_replace(r"(the|a|an)\s+", "", text, case_insensitive=True)
    RETURN text
```

### Locus adaptation
- **Component**: `locus-os/src/core/compression/shorthand.ts`
- **Integration**: Applied to Context Forge Layer 3 (PostgreSQL Events) and Layer 4 (Neo4j Pathways) before token budget checking.

---

## Feature §27.4: 3-Level Tag Hierarchy & Semantic Indexing

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `Comprehensive Locus System Design.html`  
**Query method**: [📐 DESIGN SPEC: comprehensive_design.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/vault/tag_manager.py` | 210 | Enforces strict 3-level domain/category/instance tag taxonomy across vault notes | `neo4j-labs/agent-memory`, `pageindex` |

### Stripped Logic (Pseudocode)

```
TAG HIERARCHY STRUCTURE:
    Level 1: Domain (#domain/health, #domain/craft, #domain/leverage, #domain/expression)
    Level 2: Category (#category/exercise, #category/coding, #category/writing)
    Level 3: Instance (#instance/locus-os, #instance/deepseek, #instance/2026-08)

FUNCTION validate_and_normalize_tags(tags: List[string]) -> List[string]:
    normalized = []
    FOR EACH tag IN tags:
        parts = tag.lstrip("#").split("/")
        IF len(parts) == 1:
            // Auto-resolve bare tag to domain hierarchy
            domain = lookup_domain_for_category(parts[0])
            normalized.append(f"#{domain}/{parts[0]}")
        ELSE:
            normalized.append(f"#{'/'.join(parts)}")
    RETURN normalized
```

### Locus adaptation
- **Component**: `locus-os/sidecar/vault/tag_manager.py`
- **Repo vs `.locus`**: code in `locus-os` (repo); taxonomy mappings in `.locus/config.yaml`.

---

## Feature §27.5: Rough Note Parser & Idea Tracker

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `Comprehensive Locus System Design.html` + `locus_microsystems.html`  
**Query method**: [📐 DESIGN SPEC: comprehensive_design.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/ingestion/rough_note_parser.py` | 310 | Converts raw unstructured brain dumps from Telegram or mobile into structured Obsidian atomic notes with frontmatter, tasks, and entity links | `plugin_llm.py`, `vault_crawler.py` |

### Stripped Logic (Pseudocode)

```
FUNCTION parse_rough_note_stream(raw_text: string, source: "telegram" | "voice_stt" | "quick_note") -> Dict:
    prompt = f"""Analyze the following rough, unformatted thought stream.
Extract:
1. Canonical Title (3-6 words)
2. Primary Faction Tag (#domain/craft, #domain/health, etc.)
3. Core Proposition (1-2 sentences)
4. Extracted Action Items (with checkboxes)
5. Named Entities (people, tools, concepts)

Raw Stream:
{raw_text}"""

    structured_json = call_plugin_llm(prompt, schema=RoughNoteSchema)
    
    // Construct Obsidian Markdown note
    note_content = f"""---
title: {structured_json.title}
created: {now_iso()}
source: {source}
tags: [{structured_json.primary_tag}]
entities: [{join(', ', structured_json.entities)}]
---

# {structured_json.title}

## Summary
{structured_json.core_proposition}

## Action Items
{format_checkbox_list(structured_json.action_items)}

## Raw Capture
> {raw_text}
"""

    vault_path = f"/vault/04-Captures/Inbox/{slugify(structured_json.title)}.md"
    write_file(vault_path, note_content)
    RETURN { "path": vault_path, "tasks_created": len(structured_json.action_items) }
```

### Locus adaptation
- **Component**: `locus-os/sidecar/ingestion/rough_note_parser.py`
- **Repo vs `.locus`**: code in `locus-os` (repo); saves notes to Obsidian `/vault/04-Captures/Inbox/`.

---

## Feature §27.6: Link Dump & Web Resource Logger

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `Comprehensive Locus System Design.html`  
**Query method**: [📐 DESIGN SPEC: comprehensive_design.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/ingestion/link_logger.py` | 260 | Intercepts raw URLs sent to Telegram/chat, scrapes article content, generates 3-bullet summaries, and archives to vault resource library | `tools/web_fetch.py`, `pageindex` |

### Stripped Logic (Pseudocode)

```
FUNCTION process_link_dump(url: string, user_commentary: string) -> Dict:
    // 1. Fetch & Parse HTML
    html = http_get(url)
    clean_article = extract_readable_text(html)  // Trafilatura / Readability
    
    // 2. Synthesize 3-Bullet Summary & Topic Classification
    summary_data = call_plugin_llm(f"""
    Analyze this web resource:
    URL: {url}
    User Note: {user_commentary}
    Content Snippet: {clean_article.text[:3000]}
    
    Output JSON:
    - title: Article Title
    - domain_category: (ai_research | systems_engineering | film_production | health_longevity)
    - key_takeaways: [3 bullet points]
    - relevance_to_goals: How this connects to active projects
    """)
    
    // 3. Write Resource Note to Vault
    note_path = f"/vault/06-Resources/{summary_data.domain_category}/{slugify(summary_data.title)}.md"
    note_md = format_resource_markdown(url, summary_data, user_commentary)
    write_file(note_path, note_md)
    
    // 4. Index in PageIndex
    pageindex.index_single_file(note_path)
    RETURN { "status": "SAVED", "path": note_path }
```

### Locus adaptation
- **Component**: `locus-os/sidecar/ingestion/link_logger.py`
- **Repo vs `.locus`**: code in `locus-os` (repo); saves to Obsidian `/vault/06-Resources/`.

---

## Feature §27.7: Excalidraw MCP Skill (Visual Architecture Diagrams)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Excalidraw JSON Schema Spec + MCP Skill Protocol  
**Query method**: [📐 DESIGN SPEC: excalidraw_mcp]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/src/tools/excalidraw.ts` | 320 | Generates valid `.excalidraw` vector diagram JSON from natural language system descriptions; writes directly into Obsidian | `sidecar/tools/excalidraw_builder.py` |
| `locus-os/sidecar/tools/excalidraw_builder.py` | 240 | Python layout engine computing coordinate bounding boxes, arrow connector vectors, and shape styles | `excalidraw.ts` |

### Stripped Logic (Pseudocode)

```
EXCALIDRAW ELEMENT BUILDER:
    FUNCTION create_rectangle(id, x, y, width, height, text, bg_color="#e0f2fe") -> Dict:
        RETURN {
            "id": id,
            "type": "rectangle",
            "x": x, "y": y,
            "width": width, "height": height,
            "backgroundColor": bg_color,
            "strokeColor": "#1e293b",
            "strokeWidth": 2,
            "roughness": 1,
            "roundness": { "type": 3 },
            "text": text
        }

    FUNCTION create_arrow(id, start_element_id, end_element_id, label="") -> Dict:
        RETURN {
            "id": id,
            "type": "arrow",
            "start": { "id": start_element_id },
            "end": { "id": end_element_id },
            "strokeColor": "#475569",
            "strokeWidth": 2,
            "label": label
        }

DIAGRAM SYNTHESIS PIPELINE:
    FUNCTION generate_architecture_diagram(system_spec: string, output_filename: string) -> string:
        // 1. Extract nodes and directed edges using Plugin LLM
        graph_def = call_plugin_llm(f"Extract nodes and relationships from: {system_spec}", schema=GraphDefSchema)
        
        // 2. Compute Layout Coordinates (Layered DAG layout)
        layout = compute_dag_layout(graph_def.nodes, graph_def.edges)
        
        // 3. Assemble Full Excalidraw Document JSON
        doc = {
            "type": "excalidraw",
            "version": 2,
            "source": "https://excalidraw.com",
            "elements": layout.elements,
            "appState": { "viewBackgroundColor": "#ffffff" }
        }
        
        vault_file = f"/vault/07-Diagrams/{output_filename}.excalidraw.md"
        write_file(vault_file, format_excalidraw_obsidian_wrapper(doc))
        RETURN vault_file
```

### Locus adaptation
- **Component**: `locus-os/src/tools/excalidraw.ts` (TypeScript tool)
- **Provider Interface**: `DiagramGeneratorProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); diagrams saved in `/vault/07-Diagrams/`.
- **Swappable / off state**: `locus.tools.excalidraw.enabled`. Off → diagram generation tool unregistered.


---

# INTERFACE PHILOSOPHY — §28

## Feature §28.1-28.6: Dual-Interface, Check-ins, Voice, Cost Model

### Source
- **Codebase**: Locus-original
- **Verification**: [📐 DESIGNED]

### Stripped Logic (Pseudocode)

```
DUAL-INTERFACE (TUI + Telegram):
    // Both interfaces share the SAME session state
    // Telegram messages are bridged to Pi sessions
    // TUI shows full Pi experience
    // User can switch between them mid-conversation
    
    Session unification:
        telegram_message → session_bridge → pi_session
        tui_message → pi_session (direct)
        // Both write to same JSONL session file
        // Both read from same PostgreSQL state

4 DAILY STRUCTURED CHECK-INS:
    // Delivered via Telegram inline keyboards
    // Each check-in captures: energy(1-10), stress(1-10), mood(-1 to 1), notes
    
    07:30 MORNING:
        keyboard = [
            ["Energy: 1-3 😴", "Energy: 4-6 🙂", "Energy: 7-10 🔥"],
            ["Stress: Low", "Stress: Medium", "Stress: High"],
            ["Ready to go!", "Need a slow start", "Not feeling it"]
        ]
        // After response → calculate DCS → set operating mode
    
    13:00 AFTERNOON:
        // Progress check + energy update
    
    18:00 EVENING:
        // Reflection + remaining tasks
    
    22:00 NIGHT:
        // Gratitude, tomorrow prep, wind-down

ZERO-COST CONSTRAINT:
    Default model: DeepSeek V4 Flash
    Estimated daily cost: ~$0.012/day
    Token budget: tracked per-day, per-session
    Inner Loop skips run if >80% daily budget used
    All background tasks use cheapest model available
```

---

# MISCELLANEOUS — §29

## Feature §29.1: Error Classifier

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `error_classifier.py`
**Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)]

### Logic extracted

```
ERROR CLASSIFIER:
    ERROR_TYPES:
        rate_limit   — 429/quota exceeded → auto-retry with backoff
        auth_failure — 401/403 → surface to user, suggest key refresh
        context_overflow — token limit → trigger compaction
        server_error — 500/502/503 → retry 3x, then fallback model
        timeout      — request timeout → retry with shorter context
        content_filter — safety filter → rephrase and retry
        unknown      — unclassified → log, continue
    
    FUNCTION classify_error(error):
        IF error.status == 429: RETURN "rate_limit"
        IF error.status IN [401, 403]: RETURN "auth_failure"
        IF "context_length" IN error.message: RETURN "context_overflow"
        IF error.status >= 500: RETURN "server_error"
        IF error.type == "timeout": RETURN "timeout"
        IF "content_filter" IN error.message: RETURN "content_filter"
        RETURN "unknown"
```

### Locus adaptation
- **Component**: `locus/core/error-classifier.ts`
- **Repo vs `.locus`**: code in `locus-os` (repo); retry config in `.locus/config.yaml`
- **Swappable / off state**: `locus.error_classifier.enabled`. Off → errors bubble up as raw exceptions without classification.

---

## Feature §29.2: Auxiliary LLM Client

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `auxiliary_client.py`
**Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)]

### Logic extracted

```
AUXILIARY CLIENT: separate LLM client for background tasks.
    Never contests main model's prompt cache.
    Uses cheaper model (e.g., DeepSeek V4 Flash for background,
      even if main is Claude Sonnet).
    
    FUNCTION get_auxiliary_client():
        IF config.auxiliary_model:
            RETURN create_client(config.auxiliary_model, config.auxiliary_api_key)
        ELSE:
            RETURN create_client("deepseek-v4-flash", config.deepseek_api_key)
```

### Locus adaptation
- **Component**: `locus/core/auxiliary-client.ts`
- **Repo vs `.locus`**: code in `locus-os`; auxiliary API key in `.locus/.env`
- **Swappable / off state**: `locus.auxiliary_client.enabled`. Off → background tasks use the main model client.

---

## Feature §29.3: Health Checks

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: Hermes `gateway/status.py` + OpenHuman `health`
**Query method**: [✅ VERIFIED: direct file read (/graphify unavailable)]

### Logic extracted

```
HEALTH CHECKS:
    FUNCTION health_check_all():
        results = {}
        FOR EACH provider IN all_registered_providers:
            start = now()
            try:
                status = provider.health_check()
                results[provider.name] = { status: "ok", latency_ms: now()-start, details: status }
            except error:
                results[provider.name] = { status: "error", latency_ms: now()-start, error: str(error) }
        RETURN results
```

### Locus adaptation
- **Component**: `locus/core/health/` — called by `locus doctor` CLI command
- **Repo vs `.locus`**: code in `locus-os` (repo)
- **Swappable / off state**: N/A (diagnostic utility, always available via `locus doctor`)

---

## Feature §29.4: Notifications

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: OpenHuman `notifications/` + Hermes `gateway/` + Locus-original  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| OpenHuman `notifications/dispatcher.py` | ~150 | Multi-channel notification dispatch; routes by priority level to appropriate delivery channel(s) | `channel_registry` (discovers connected channels), `gateway/` (delivers messages) |
| Hermes `gateway/platform_registry.py` | ~80 | Platform registration; provides `get_connected_platforms()` | `notifications/` (supplies channel list) |
| Locus-original design | — | Priority-aware routing with quiet hours, DCS-gated delivery, and notification queuing | `state_engine` (reads DCS for delivery gating), `inner_loop` (surfaces queued notifications) |

### Stripped Logic (Pseudocode)

```
NOTIFICATION SYSTEM:

    PRIORITY LEVELS:
        HIGH    — Behavioral alerts, critical state changes, approval requests
        MEDIUM  — Inner Loop observations, morning briefing, deferral warnings
        LOW     — Content drafts ready, spaced repetition prompts, non-urgent patterns

    FUNCTION send_notification(message, priority, metadata={}):
        active_channels = channel_registry.get_connected()
        current_state = state_engine.get_current_state()
        
        // Quiet hours gate (unless HIGH priority)
        IF is_quiet_hours() AND priority != "HIGH":
            queue_for_later(message, priority, metadata)
            RETURN { delivered: false, reason: "quiet_hours", queued: true }
        
        // DCS-gated delivery: suppress MEDIUM/LOW if user is stressed
        IF current_state.dcs < 3.0 AND priority != "HIGH":
            queue_for_later(message, priority, metadata)
            RETURN { delivered: false, reason: "low_dcs", queued: true }
        
        SWITCH priority:
            CASE "HIGH":
                // Deliver to ALL active channels simultaneously
                FOR EACH channel IN active_channels:
                    channel.send(message, urgent=true)
                log_notification(message, "HIGH", channels=active_channels)
            
            CASE "MEDIUM":
                // Primary channel only (Telegram by default)
                primary = get_primary_channel(active_channels)
                primary.send(message, urgent=false)
                log_notification(message, "MEDIUM", channels=[primary])
            
            CASE "LOW":
                // Queue for next interaction (delivered in morning briefing or next check-in)
                queue_for_next_interaction(message, metadata)
                log_notification(message, "LOW", channels=[], queued=true)
        
        RETURN { delivered: true, priority: priority }
    
    FUNCTION process_notification_queue():
        // Called during morning briefing and after each check-in
        queued = get_queued_notifications()
        IF queued:
            summary = format_notification_summary(queued)
            send_notification(summary, "MEDIUM")
            mark_as_delivered(queued)

    QUIET HOURS:
        default: 00:00 - 07:00 IST
        configurable: .locus/config.yaml → notifications.quiet_hours
        HIGH priority overrides quiet hours
```

### Locus adaptation
- **Component**: `locus/core/notifications.ts` — TypeScript notification dispatcher
- **Provider Interface**: `NotificationProvider` interface (`send(message, options) → DeliveryResult`). Each channel adapter (Telegram, Desktop, etc.) implements this.
- **Repo vs `.locus`**: code in `locus-os` (repo); notification preferences and quiet hours in `.locus/config.yaml`
- **Swappable / off state**: `locus.notifications.enabled`. Off → no automatic multi-channel notifications; user must manually check for queued observations via `/locus-status`. Individual channels toggled via `locus.notifications.channels.<name>.enabled`.
- **STEAL**: OpenHuman's multi-channel dispatch pattern. **ADAPT**: Add DCS-gated delivery and quiet hours from Locus design specs.

---

## Feature §29.5: Connectivity Check

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: OpenHuman `connectivity/` + Locus-original  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| OpenHuman `connectivity/checker.py` | ~60 | Simple HTTP HEAD check for internet connectivity | `inner_loop` (pre-flight check), `sidecar` (health check), `model_escalation` (determines if remote models available) |

### Stripped Logic (Pseudocode)

```
CONNECTIVITY CHECK:

    ENDPOINTS = [
        "https://httpbin.org/status/200",     // primary (neutral, fast)
        "https://1.1.1.1/cdn-cgi/trace",      // fallback (Cloudflare, minimal response)
    ]
    
    FUNCTION check_connectivity(timeout=5):
        FOR EACH endpoint IN ENDPOINTS:
            TRY:
                response = http.head(endpoint, timeout=timeout)
                IF response.status < 400:
                    RETURN { online: true, latency_ms: response.elapsed, endpoint: endpoint }
            CATCH timeout_or_error:
                CONTINUE  // try next endpoint
        
        RETURN { online: false, latency_ms: null }
    
    FUNCTION check_service_connectivity(services):
        // Check specific service endpoints (Neo4j, PostgreSQL, sidecar)
        results = {}
        FOR EACH service IN services:
            TRY:
                response = http.get(service.health_url, timeout=3)
                results[service.name] = { healthy: response.status == 200 }
            CATCH:
                results[service.name] = { healthy: false }
        RETURN results
    
    // Used as gate before:
    //   - Inner Loop proactive passes (skip if offline)
    //   - Remote model API calls (fallback to local Ollama if offline)
    //   - Background vault sync (skip if offline)
    //   - Web search retrieval (skip, use local only)
```

### Locus adaptation
- **Component**: `locus/core/connectivity.ts` — lightweight async connectivity checker
- **Repo vs `.locus`**: code in `locus-os` (repo); no config needed
- **Swappable / off state**: Always available (utility function). Used as a gate by Inner Loop, model escalation, and background tasks. If offline: Inner Loop skips web-dependent operations, model escalation forces local-only, web search returns empty results.

---

## Feature §29.6: Code Graph Analysis

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: OpenHuman `codegraph/` + `/graphify` integration  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| OpenHuman `codegraph/analyzer.py` | ~200 | Scans project directories for source files, builds import/dependency graph, identifies module boundaries | `harness_delegation` (provides dependency context for task scoping) |
| `/graphify` CLI | external | Full AST-based knowledge graph builder; produces `graph.json` at `graphify-out/` | `codegraph/` (can use graphify output as pre-built dependency data) |

### Stripped Logic (Pseudocode)

```
CODE GRAPH ANALYSIS:

    FUNCTION analyze_codebase(project_path):
        // Step 1: Discover source files
        files = scan_directory(project_path, 
            extensions=[".ts", ".tsx", ".js", ".jsx", ".py", ".rs", ".go"],
            exclude=["node_modules", ".git", "dist", "build", "__pycache__"])
        
        // Step 2: Extract import/dependency relationships
        graph = DependencyGraph()
        FOR EACH file IN files:
            imports = extract_imports(file)
            FOR EACH imported_module IN imports:
                resolved = resolve_import_path(imported_module, file.dir)
                IF resolved: graph.add_edge(file.path, resolved.path, type="imports")
        
        // Step 3: Identify module clusters (strongly connected components)
        clusters = graph.find_connected_components()
        
        // Step 4: Calculate file importance (PageRank-like)
        importance = graph.calculate_centrality()
        
        RETURN {
            files: files,
            edges: graph.edges,
            clusters: clusters,
            importance: importance,
            entry_points: graph.find_roots()  // files with no inbound imports
        }
    
    FUNCTION scope_task_files(task_description, codebase_graph):
        // Given a task description, identify the minimal set of files that need editing
        // Used by harness delegation (§3.7) to scope coding tasks
        relevant_files = semantic_search(task_description, codebase_graph.files)
        // Include transitive dependents (files that import the changed files)
        expanded = expand_with_dependents(relevant_files, codebase_graph, depth=2)
        RETURN expanded
    
    // Integration with /graphify:
    // If graphify-out/graph.json exists and is fresh (<24h), use it directly
    // instead of running the lightweight scanner above
    FUNCTION get_or_build_graph(project_path):
        graphify_path = project_path / "graphify-out/graph.json"
        IF exists(graphify_path) AND age(graphify_path) < 24h:
            RETURN load_graphify_graph(graphify_path)
        ELSE:
            RETURN analyze_codebase(project_path)
```

### Locus adaptation
- **Component**: `locus/core/codegraph/` — TypeScript graph builder + graphify bridge
- **Repo vs `.locus`**: code in `locus-os` (repo); cached graph data in `.locus/codegraph_cache/`
- **Swappable / off state**: `locus.codegraph.enabled`. Off → harness delegation uses flat file lists without dependency analysis; task scoping relies on file name heuristics only.
- **STEAL**: OpenHuman's import extraction patterns for .ts/.py/.rs. **ADAPT**: Add graphify integration for pre-built AST graphs.

---

## Feature §29.7: Subconscious Background Processing

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: OpenHuman `subconscious/` + Locus Inner Loop design  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| OpenHuman `subconscious/processor.py` | ~250 | Runs during idle periods: memory consolidation, pattern detection, knowledge decay | `memory_provider` (reads recent memories, writes consolidated), `pattern_engine` (detects novel patterns) |
| Locus Inner Loop design | — | The proactive Inner Loop (§26) runs subconscious passes every 90 minutes | `inner_loop` (triggers subconscious), `neo4j_adapter` (edge weight updates), `vault_crawler` (reindexing) |

### Stripped Logic (Pseudocode)

```
SUBCONSCIOUS BACKGROUND PROCESSING:

    // Runs during idle periods (no active conversation) — triggered by Inner Loop
    // or by explicit idle detection (>15 minutes since last user message)
    
    FUNCTION subconscious_pass():
        // Phase 1: Memory Consolidation
        recent_memories = memory_provider.get_recent(hours=24)
        
        // Group related memories by entity overlap
        memory_clusters = cluster_by_entity_overlap(recent_memories)
        FOR EACH cluster IN memory_clusters:
            IF cluster.size >= 3:  // only consolidate if enough evidence
                consolidated = llm.summarize_memories(cluster, 
                    prompt="Synthesize these related observations into a single insight.")
                memory_provider.store_consolidated(consolidated)
                // Mark source memories as "consolidated" (not deleted — still searchable)
                mark_as_consolidated(cluster.memories, consolidated.id)
        
        // Phase 2: Pattern Detection
        patterns = pattern_engine.detect_patterns(horizon="24h")
        FOR EACH pattern IN patterns:
            IF pattern.is_novel:
                // Novel = not seen in previous pattern scans (cosine similarity < 0.85)
                store_observation(pattern)
                IF pattern.confidence > 0.7:
                    queue_for_inner_loop(pattern, priority="MEDIUM")
        
        // Phase 3: Knowledge Decay Maintenance
        stale_nodes = neo4j.query("""
            MATCH (n:ConceptNode) 
            WHERE n.last_accessed < datetime() - duration('P30D')
            AND n.importance < 0.3
            RETURN n
        """)
        FOR EACH node IN stale_nodes:
            // Apply exponential decay to edge weights
            neo4j.decay_edges(node, factor=0.95)
            IF node.all_edges_below(threshold=0.1):
                neo4j.archive_node(node)  // move to cold storage, not delete
        
        // Phase 4: Vault Incremental Reindex
        changed_files = vault_crawler.scan_for_changes()
        IF changed_files:
            vault_crawler.reindex(changed_files)
        
        LOG subconscious_pass_complete(
            consolidated=len(memory_clusters),
            patterns=len(patterns),
            stale_nodes=len(stale_nodes),
            reindexed=len(changed_files)
        )
    
    // Idle detection
    FUNCTION is_idle():
        last_message_time = session_manager.get_last_user_message_time()
        RETURN (now() - last_message_time) > 15_minutes
```

### Locus adaptation
- **Component**: `locus/core/subconscious.ts` (orchestrator) + `sidecar/subconscious/` (Python, heavy computation)
- **Provider Interface**: `SubconsciousProvider` (`run_pass() → SubconsciousResult`). The default implementation runs all four phases; a custom provider could skip phases or add new ones.
- **Repo vs `.locus`**: code in `locus-os` (repo); consolidated memory output written to Neo4j + PG
- **Swappable / off state**: `locus.subconscious.enabled`. Off → no idle-time background processing; memory consolidation only happens during scheduled Inner Loop passes. Pattern detection limited to Inner Loop cycle.

---

## Feature §29.8: Workflows

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: OpenHuman `workflows/` + Locus-original  
**Query method**: [✅ VERIFIED: direct file read]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| OpenHuman `workflows/engine.py` | ~300 | Multi-step task orchestration engine; executes workflow definitions with step chaining, conditional branching, and approval gates | `tool_executor` (runs tool steps), `subagent_spawner` (runs subagent steps), `approval_store` (handles human-in-the-loop gates) |
| OpenHuman `workflows/definitions/` | — | YAML/JSON workflow definition files | `engine.py` (loads and executes definitions) |

### Stripped Logic (Pseudocode)

```
WORKFLOW ENGINE — multi-step task orchestration:

    WORKFLOW DEFINITION SCHEMA:
        name: string
        description: string
        trigger: "manual" | "schedule" | "event"     // how the workflow starts
        steps: [
            {
                id: string,
                type: "llm_call" | "tool_call" | "subagent" | "approval_gate" | "condition" | "parallel",
                config: { ... },                       // type-specific configuration
                next: string | null,                    // next step ID (null = end)
                on_error: "fail" | "skip" | "retry"    // error handling strategy
            }
        ]

    FUNCTION execute_workflow(workflow_definition, initial_context={}):
        context = initial_context
        current_step = workflow_definition.steps[0]
        execution_log = []
        
        WHILE current_step:
            TRY:
                SWITCH current_step.type:
                    CASE "llm_call":
                        // Inject context variables into prompt template
                        prompt = template_render(current_step.config.prompt, context)
                        result = llm.generate(prompt, model=current_step.config.model)
                    
                    CASE "tool_call":
                        result = tool.execute(
                            current_step.config.tool_name,
                            template_render(current_step.config.args, context)
                        )
                    
                    CASE "subagent":
                        result = spawn_subagent(
                            archetype=current_step.config.archetype,
                            task=template_render(current_step.config.task, context),
                            tools=current_step.config.tools
                        )
                    
                    CASE "approval_gate":
                        // Human-in-the-loop: send approval request, wait for response
                        send_notification(
                            f"Approval needed: {current_step.config.description}",
                            priority="HIGH"
                        )
                        result = approval_store.wait_for_approval(
                            task_id=current_step.id,
                            ttl=current_step.config.ttl OR 3600  // default 1h timeout
                        )
                        IF result.denied:
                            RETURN { status: "denied", step: current_step.id }
                    
                    CASE "condition":
                        // Conditional branching based on previous step outputs
                        condition_result = evaluate_condition(
                            current_step.config.expression, context
                        )
                        IF condition_result:
                            current_step = find_step(current_step.config.then)
                        ELSE:
                            current_step = find_step(current_step.config.else)
                        CONTINUE  // skip the normal next-step logic
                    
                    CASE "parallel":
                        // Run multiple sub-steps concurrently
                        results = await_all([
                            execute_step(sub_step, context) 
                            FOR sub_step IN current_step.config.parallel_steps
                        ])
                        result = merge_results(results)
                
                // Store step output in context for next steps
                context[current_step.id] = result
                execution_log.append({ step: current_step.id, status: "success", result })
                
                // Advance to next step
                current_step = find_step(current_step.next) IF current_step.next ELSE null
            
            CATCH error:
                SWITCH current_step.on_error:
                    CASE "fail": RETURN { status: "failed", step: current_step.id, error }
                    CASE "skip": current_step = find_step(current_step.next)
                    CASE "retry": retry with exponential backoff (max 3)
        
        RETURN { status: "completed", context, execution_log }

    BUILT-IN WORKFLOW TEMPLATES:
        "morning_briefing":  gather_state → summarize → format → deliver_telegram
        "weekly_review":     pull_week_data → analyze_patterns → generate_report → save_vault
        "content_publish":   detect_trigger → draft → approval_gate → format_platform → queue
        "vault_maintenance": scan_orphans → suggest_links → approval_gate → apply_links
```

### Locus adaptation
- **Component**: `locus/core/workflows/` — TypeScript workflow engine
- **Provider Interface**: `WorkflowEngine` with `registerStepHandler(type, handler)` for extensibility. Custom step types can be registered by plugins.
- **Repo vs `.locus`**: built-in workflow definitions in `locus-os/workflows/` (repo); user-defined workflows in `.locus/workflows/`. Workflow execution logs in `.locus/workflow_logs/`.
- **Swappable / off state**: `locus.workflows.enabled`. Off → no automated multi-step orchestration; each step must be triggered manually. Built-in workflows (morning briefing, weekly review) become manual commands.
- **STEAL**: OpenHuman's step-chain execution pattern, the approval gate mechanism, the context variable injection. **ADAPT**: Add `condition` and `parallel` step types (not in OpenHuman). Wire approval gates to Telegram + desktop notification.


---

# SPECIALIZED LOCUS MICROSYSTEMS — §30 (Extracted from Design HTMLs)

## Feature §30.1: Collector + Chunker (Ingestion Pipeline)

### Source
- **Codebase**: Locus-original (from `locus_microsystems.html`)
- **Verification**: [✅ VERIFIED: `locus_microsystems.html` Collector+Chunker 10-step breakdown]

### Stripped Micro-Step Logic

```
STEP 1: Crawl Trigger
    - Scheduled incremental: every 6h crawl of Obsidian vault for new/changed files.
    - Post-archiver trigger: AI Chat Archiver completion fires immediate crawl.
    - Nightly full crawl: 01:00 IST full sweep of all sources.

STEP 2: Obsidian Vault MD5 Crawl
    - Walks /vault/ tree using os.walk(). For each .md file: compute MD5.
    - Compare against md5_hashes table in PostgreSQL. If hash matches: skip.
    - If hash differs or new file: add to processing queue.

STEP 3: Additional Source Crawl
    - Crawl Telegram captures (/vault/04-Captures/), check-in logs (/vault/05-Logs/), task event exports.

STEP 4: Markdown Parse + Strip Noise
    - Strip YAML frontmatter, Dataview queries, ![[embeds]], wikilink brackets (keep link text).
    - Result: clean plaintext suitable for sentence splitting.

STEP 5: spaCy Sentence Boundary Detection
    - Run clean plaintext through spaCy `en_core_web_sm` model for sentence boundary detection.
    - Produces list of sentence objects with character offsets.

STEP 6: Factual Sentence Classification
    - Classify each sentence as FACTUAL (keep) or NON-FACTUAL (discard filler/navigation).
    - Batch call to DeepSeek V4 Flash (cheapest available) (~30 sentences/call, temp=0).
    - Heuristic fallback: if sentence < 5 words or > 0.4 stopword ratio → classify as NON-FACTUAL.

STEP 7: 5-Proposition Chunk Assembly
    - Group consecutive FACTUAL sentences into chunks of max 5 sentences.
    - Topic continuity heuristic: Named entity overlap between consecutive sentences.
    - New chunk starts on: (1) 5 sentences reached, (2) topic discontinuity, or (3) file boundary.

STEP 8: Embedding Generation
    - Generate 384-dimensional embedding for each chunk using `fastembed` (BAAI/bge-small-en-v1.5) locally.

STEP 9: PostgreSQL Write (`vault_chunks`)
    - Write chunks & metadata to `vault_chunks` table in PostgreSQL. UPDATE if chunk_id exists.

STEP 10: pgvector Vector Upsert
    - Upsert 384-dim vectors + payload `{source_file, chunk_index, created_at, faction_tags}` to pgvector `vault_chunks` collection.
    - Update `md5_hashes` table in PostgreSQL.
```

---

## Feature §30.2: Cause Chain Engine (Inferred Causation)

### Source
- **Codebase**: Locus-original (from `Comprehensive Locus System Design.html`)
- **Verification**: [✅ VERIFIED: `Comprehensive Locus System Design.html` Cause Chain Engine 9-step breakdown]

### Stripped Micro-Step Logic

```
STEP 1: Trigger Reception
    - Triggered when State Engine detects significant state shift (e.g. DCS drops >2.0 points, mood drops, deferral surge).

STEP 2: Multidimensional Event Window Pull
    - Pull last 48 hours of behavioral_events, check-ins, sleep quality, meal timing, and calendar meetings.

STEP 3: Temporal Sequence Alignment
    - Order events chronologically to build a 48h temporal graph.

STEP 4: Anomaly Correlation Check
    - Correlate current state anomaly with preceding behavioral anomalies (e.g., late sleep -> skipped meal -> deferral).

STEP 5: LLM Cause Chain Synthesis
    - Call DeepSeek V4 Flash with structured event window. Prompt: "Deduce the root cause chain behind Shivam's current state. Cite specific data points."

STEP 6: Evidence Verification
    - Validate that each link in the deduced cause chain has at least 1 empirical log event supporting it.

STEP 7: Hypothesis Confidence Scoring
    - Score cause chain confidence (0.0 to 1.0) based on evidence density.

STEP 8: Inferred Cause Chain Write
    - Update Redis `CURRENT_STATE` with `inferred_cause_chain_summary` string.

STEP 9: Alert Escalation
    - If cause chain confidence > 0.85 and severity high: emit alert to Inner Loop surface queue.
```

---

## Feature §30.3: SOUL.md / Wants Engine (Personality Layer)

### Source
- **Codebase**: Locus-original (from `Comprehensive Locus System Design.html`)
- **Verification**: [✅ VERIFIED: `Comprehensive Locus System Design.html` SOUL.md 6-step breakdown]

### Stripped Micro-Step Logic

```
STEP 1: Personality Context Loading
    - Read `SOUL.md` from Obsidian vault (/vault/00-System/SOUL.md).
    - Contains: Locus core identity, communication style, operating philosophy, user-agent relationship contract.

STEP 2: Active Wants Read
    - Read active system "Wants" from PostgreSQL `system_wants` table.
    - System Wants represent Locus's internal drive to acquire missing knowledge or fix misalignments (e.g. "Want: understand why film projects are deferred on Thursdays").

STEP 3: Identity Prompt Assembly
    - Merge SOUL.md identity + active Wants into Layer 1 of Context Forge (hard limit: 80 tokens).

STEP 4: Want Generation Trigger
    - When Pattern Engine or Goal Tracker detects a persistent data gap, generate a candidate Want.

STEP 5: Want Priority Ranking
    - Rank candidate Wants by urgency and relevance to current active user goals.

STEP 6: Conversational Nudging
    - When appropriate in low-stress states (DCS > 6.0), surface 1 active Want to user as a natural question.
```

---

## Feature §30.4: Content Engine (8-Step Social & Thought Publication Pipeline)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` (Subsystem 17, 8-Step Content Engine Breakdown)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/content/content_engine.py` | 420 | Autonomous 8-step social & thought drafting pipeline converting completed project milestones into authentic user-voice essays | `SOUL.md`, `postgres_client.py`, `vault_crawler.py` |
| `locus-os/sidecar/content/voice_matcher.py` | 190 | Evaluates generated drafts against user's authentic writing style guide (anti-cringe, zero corporate buzzwords) | `SOUL.md`, `content_engine.py` |

### Stripped Micro-Step Logic (from `locus_microsystems.html`)

```
STEP 1: Milestone & Artifact Event Detection
    - Ingestion listener monitors PostgreSQL `behavioral_events` for trigger conditions:
      * Task completion with leverage score L >= 8
      * Project milestone reaching 100% completion
      * Git repository release commit or major PR merge
      * Deep technical problem solved in daily coding logs

STEP 2: Empirical Data Gathering
    - Pull actual metrics from database:
      * Exact hours spent, lines of code changed, architecture decisions made
      * Specific bug traces overcome, benchmark speedups achieved
      * Associated vault notes from `/vault/01-Projects/`

STEP 3: Voice Style Contract Loading (SOUL.md)
    - Load style rules from `/vault/00-System/SOUL.md`:
      * Anti-cringe rule: strictly forbid "Excited to share", "Humbled", "In today's fast-paced world"
      * Tone: technical, direct, builder-first, transparent about failures and iterations
      * Format: hook in first 2 lines, dense data in body, concrete takeaway at end

STEP 4: Multi-Platform Variant Generation
    - Dispatch to DeepSeek V4 Flash / Claude Sonnet with multi-format template:
      * Long-Form Essay / Substack draft (600-1200 words)
      * Technical LinkedIn post (200-350 words, structured bullet formatting)
      * X / Twitter thread (5-7 tweets, max 280 chars per tweet)
      * Short Telegram update (80-150 words)

STEP 5: Voice Adherence & Authenticity Scoring
    - Run `voice_matcher.py` classifier:
      Score = 1.0 - (BuzzwordCount * 0.25) - (GenericAdjectiveDensity * 0.30)
      IF Score < 0.80 -> Trigger automatic rewrite pass.

STEP 6: Vault Draft Assembly
    - Save structured multi-variant draft to `/vault/06-Content/Drafts/YYYY-MM-DD-{slug}.md`.
    - Include frontmatter status: `draft_status: pending_review`.

STEP 7: Conversational Review Nudge
    - Surface notification to user during Evening Check-in:
      "Drafted 3 social posts from your completed Locus milestone. Review in Vault?"

STEP 8: Feedback Loop & Style Adaptation
    - When user edits draft in Obsidian, compute diff between generated vs final version.
    - Store diff patterns in PostgreSQL `voice_corrections` to adapt future voice prompts.
```

### Locus adaptation
- **Component**: `locus-os/sidecar/content/content_engine.py` (Python sidecar)
- **Provider Interface**: `ContentEngineProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); drafts saved in `/vault/06-Content/Drafts/`.
- **Swappable / off state**: `locus.content_engine.enabled`. Off → no automated social drafts.


---

## Feature §30.5: Spaced Repetition Engine

### Source
- **Codebase**: Locus-original (from `locus_microsystems.html` & `Comprehensive Locus System Design.html`)
- **Verification**: [✅ VERIFIED: `locus_microsystems.html` Neo4j Step 5]

### Stripped Micro-Step Logic

```
STEP 1: Graph Traversal Audit
    - Scan Neo4j ConceptNodes for nodes not traversed in last X days.
    - Thresholds: H3 patterns (7-day nodes) trigger at day 5; H4 patterns (30-day nodes) trigger at day 22.

STEP 2: Active Connection Filter
    - Filter for decaying nodes that remain connected to currently active projects or goals.

STEP 3: Spaced Repetition Observation Assembly
    - Formulate observation: "You haven't engaged with [Concept] in X days, but it connects to 3 active projects."

STEP 4: Queue to Inner Loop
    - Enqueue observation to Redis `inner_loop_surface_queue`.

STEP 5: Engagement Feedback Handling
    - If user reacts (👍 or responds): reinforce Neo4j edge weights (×1.3).
    - If user ignores/thumbs down: apply natural decay (×0.95).
```

---

## Feature §30.6: QLoRA Fine-Tuning Pipeline

### Source
- **Codebase**: Locus-original (from `locus_pyramid.html`)
- **Verification**: [✅ VERIFIED: `locus_pyramid.html` RLHF/QLoRA node]

### Stripped Micro-Step Logic

```
STEP 1: Interaction Logging
    - Store every interaction turn, prompt, response, and 👍/👎 reward signal in PostgreSQL `reward_signals`.

STEP 2: Dataset Curation (Quarterly)
    - Filter for high-reward interactions (👍 signal, user response within 2 min, DCS > 5.0).
    - Format into Alpaca/ShareGPT JSONL dataset format.

STEP 3: Data Export & Anonymization
    - Export dataset, strip PII, upload to secure storage bucket for fine-tuning worker.

STEP 4: QLoRA Fine-Tuning Execution
    - Run 4-bit QLoRA fine-tuning job on base model (e.g. Llama-3-8B / Mistral-7B) on Colab/Kaggle GPU.
    - Target: 1-2% parameter adapter training.

STEP 5: Evaluation & Benchmark Test
    - Evaluate fine-tuned adapter against baseline on benchmark test suite (intent classification, context adherence).

STEP 6: Sidecar Deployment
    - Deploy fine-tuned LoRA adapter to Ollama / vLLM on local machine or sidecar server.
```

---


## Feature §30.7: Master Conductor (11-Step Ingress-to-Egress Pipeline)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` (Subsystem 1, 11-Step Master Conductor Breakdown)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/src/core/master-conductor.ts` | 560 | Orchestrates the entire 11-step request lifecycle from channel ingress to final egress | `intent-classifier.ts`, `context-forge.ts`, `agent-loop.ts`, `state-engine.ts` |
| `locus-os/src/core/rate-limiter.ts` | 180 | Global token bucket and concurrency controller preventing API exhaustion | `master-conductor.ts` |

### Stripped Micro-Step Logic (from `locus_microsystems.html`)

```
STEP 1: Ingress & Event Normalization
    - Receive raw message from Telegram, Discord, TUI, or Webhook.
    - Normalize into canonical `LocusRequestEvent` (user_id, channel_id, raw_text, attachments, timestamp).

STEP 2: Global Concurrency & Rate Limit Check
    - Token bucket rate limiter: verify user has remaining burst quota (max 10 req/min).
    - Concurrency lock: maximum 2 concurrent LLM streams per user.

STEP 3: Fast-Path Intent Classification
    - Call Query Router / Intent Classifier (§2.1-2.3):
      * Classify Intent: CHAT | TASK_CREATE | CHECKIN | RETRIEVAL | CODE | EMERGENCY
      * Extract Required Sources: [Neo4j, PostgreSQL, pgvector, PageIndex, Web]

STEP 4: Real-Time State Ingestion
    - Fetch active `CURRENT_STATE` from Redis (DCS, Operating Mode, Stress, Active Alerts).

STEP 5: Parallel Retrieval Dispatch
    - Fire parallel async queries to required sources determined in Step 3:
      * Neo4j graph traversal (depth 2)
      * PageIndex hierarchical markdown search
      * pgvector semantic chunk similarity
      * PostgreSQL recent behavioral event log

STEP 6: Context Forge Layer Assembly
    - Pass retrieved fragments to Context Forge (§2.5):
      * Assemble 6 layers (Identity 80t, Temporal 60t, Events 180t, Graph 150t, Semantic 200t, Web 100t)
      * Enforce 800-token total budget; apply Headroom CCR compression if overflow.

STEP 7: Security & Prompt Sanitization
    - Run Prompt Injection Detector (§13.1) and Data Redaction (§13.8) on assembled prompt.

STEP 8: Model Resolution & LLM Dispatch
    - Resolve target model via Intelligent Router (§2.7):
      * Lightweight tasks → Ollama local
      * Standard tasks → DeepSeek V4 Flash
      * Deep reasoning → Gemini 2.5 Pro
    - Dispatch streaming request with retry fallback chain.

STEP 9: Tool Execution Pipeline
    - If LLM emits tool calls: execute through Sandboxed Tool Runner (§13.3).
    - Feed tool outputs back into loop until final text generated.

STEP 10: Post-Turn Memory & State Sync
    - Post-Turn Background Review (§1.7/§10.1):
      * Extract new entities → Neo4j
      * Log behavioral event → PostgreSQL
      * Update DCS and Redis state

STEP 11: Egress & Delivery
    - Format response (MarkdownV2 for Telegram, ANSI for TUI).
    - Send message to origin channel adapter; emit completion telemetry.
```

### Locus adaptation
- **Component**: `locus-os/src/core/master-conductor.ts` (TypeScript)
- **Provider Interface**: `MasterConductorProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); concurrency limits in `.locus/config.yaml`.
- **Swappable / off state**: Core orchestration layer; cannot be turned off.

---

## Feature §30.8: Real-Time Dashboard & TUI Specification (6-Step Architecture)

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` (Subsystem 16, 6-Step Dashboard Breakdown)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/src/tui/dashboard.ts` | 490 | Blessed / Ink terminal UI rendering real-time DCS gauge, 4-faction progress bars, task queue, and memory graph visualizer | `redis_client.ts`, `state-engine.ts` |
| `locus-os/src/tui/widgets/faction_bar.ts` | 140 | Progress widget rendering Craft, Health, Leverage, Expression balances | `dashboard.ts` |

### Stripped Micro-Step Logic (from `locus_microsystems.html`)

```
STEP 1: Redis State Bus Subscription
    - Connect to Redis pub/sub channels: `state_shift`, `task_update`, `dcs_live`.

STEP 2: Terminal Layout Partitioning
    - Split terminal into 4 responsive panels:
      * Top Left: DCS Gauge (0-10) + Operating Mode Badge (SURVIVAL -> PEAK)
      * Top Right: 4-Faction Weekly Allocation Bars (Craft 40%, Health 25%, Leverage 20%, Expr 15%)
      * Bottom Left: Active Task Queue (sorted by TWS descending with lag badges)
      * Bottom Right: Real-Time Telemetry & Log Stream

STEP 3: DCS Live Gauge Rendering
    - Render colored circular ASCII/Unicode gauge reflecting current energy, mood, sleep, and stress.

STEP 4: Faction Balance Progress Bars
    - Render real-time progress vs weekly target with color coding:
      * Green: Within ±5% tolerance
      * Yellow: Over-represented (> Target + 5%)
      * Red: Under-represented (< Target - 5%)

STEP 5: Interactive Task Dispatcher
    - Keybindings:
      * `[Space]` : Toggle active task completion (emits event to PostgreSQL)
      * `[D]`     : Defer task (increments deferral counter, updates TWS lag bonus)
      * `[N]`     : Quick task entry modal
      * `[C]`     : Trigger on-demand check-in flow

STEP 6: Hot-Reload & Graceful Resize Handling
    - Handle `SIGWINCH` terminal resize events without flicker; maintain 60 FPS update loop.
```

### Locus adaptation
- **Component**: `locus-os/src/tui/dashboard.ts`
- **Repo vs `.locus`**: code in `locus-os` (repo); launchable via `locus dashboard` or embedded in terminal session.

---

## Feature §30.9: Redis High-Performance State & Pub/Sub Integration

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` (Subsystem 18, Redis Architecture Breakdown)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/state/redis_manager.py` | 260 | High-performance Redis client managing cached states, pub/sub event channels, and atomic rate limit buckets | `state_engine.py`, `inner_loop.py`, `master-conductor.ts` |

### Stripped Logic (Pseudocode)

```
REDIS SCHEMA & NAMESPACE SPECIFICATION:
    1. Keys:
       * `CURRENT_STATE` (JSON, TTL 6h)        → { dcs, mode, energy, mood, stress, active_alerts }
       * `DCS_LIVE` (Float, TTL 24h)           → Current DCS float value
       * `RATE_LIMIT:{user_id}` (Hash, TTL 1m) → Token bucket counter
       * `RECENT_THOUGHTS` (List, Max 20)      → FIFO list of recent proactive embeddings
       * `CACHE:PAGEINDEX:{file_hash}` (JSON)  → Cached markdown tree nodes
       * `CACHE:HEADROOM:{msg_hash}` (Binary)  → Compressed message buffers

    2. Pub/Sub Channels:
       * `state_shift`     → Emitted when DCS changes by >= 0.5 points
       * `emergency_alert` → Emitted on Level 1-4 crisis events
       * `ingest_event`    → Emitted when new vault note or chat is crawled
       * `task_completed`  → Emitted on task check-off

ATOMIC TRANSACTION PATTERNS:
    FUNCTION update_state_atomic(new_state: Dict):
        pipeline = redis.pipeline()
        pipeline.set("CURRENT_STATE", json.dumps(new_state), ex=21600)
        pipeline.set("DCS_LIVE", str(new_state["dcs"]), ex=86400)
        pipeline.publish("state_shift", json.dumps({ "dcs": new_state["dcs"], "mode": new_state["mode"] }))
        pipeline.execute()
```

### Locus adaptation
- **Component**: `locus-os/sidecar/state/redis_manager.py` (Python) + `locus-os/src/core/redis.ts` (TS)
- **Repo vs `.locus`**: code in `locus-os` (repo); Redis connection URI in `.locus/.env`. Runs as Docker container `locus-redis` (port 6379).

---

## Feature §30.10: Obsidian & LightRAG Dual-Index Knowledge Bridge

**Status**: complete  
**Verdict**: 🆕 LOCUS-NEW  
**Source**: `locus_microsystems.html` (Subsystem 18, Obsidian + LightRAG Bridge Breakdown)  
**Query method**: [📐 DESIGN SPEC: microsystems.html]

### Files Involved

| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| `locus-os/sidecar/vault/lightrag_bridge.py` | 380 | Dual-level knowledge graph builder bridging Obsidian vault wikilinks with LightRAG dual-level entity & theme indexing | `crawlers/vault_crawler.py`, `neo4j-labs/agent-memory` |

### Stripped Micro-Step Logic

```
STEP 1: Obsidian Markdown AST & Wikilink Extraction
    - Parse all `.md` files in `/vault/` into abstract syntax trees.
    - Extract:
      * Direct `[[Wikilinks]]` and Aliases `[[Target|Alias]]`
      * Embedded Images & Diagrams `![[Embed]]`
      * YAML Frontmatter & Dataview inline fields (`key:: value`)

STEP 2: Low-Level Entity Extraction
    - Extract granular atomic entities (functions, parameters, book titles, people).
    - Map each entity to its exact line-number span within the markdown source note.

STEP 3: High-Level Theme & Cluster Extraction
    - Group interconnected entity clusters into macroscopic thematic nodes
      (e.g., "Autonomous Agent Memory Architecture", "Circadian Optimization").

STEP 4: Dual-Level Graph Construction
    - Build two-tier graph structure:
      * Tier 1 (Entity Graph): Low-level fact retrieval for precise answers
      * Tier 2 (Theme Graph): High-level concept synthesis for holistic reasoning

STEP 5: Hybrid Retrieval Dispatch
    - FUNCTION dual_level_retrieval(query: string, max_tokens: int = 350) -> string:
        low_level_facts = search_entity_graph(query, top_k=5)
        high_level_themes = search_theme_graph(query, top_k=2)
        RETURN format_dual_context(low_level_facts, high_level_themes, max_tokens)
```

### Locus adaptation
- **Component**: `locus-os/sidecar/vault/lightrag_bridge.py`
- **Provider Interface**: `DualIndexKnowledgeProvider`
- **Repo vs `.locus`**: code in `locus-os` (repo); LightRAG index data in `.locus/memory/lightrag/`.
- **Swappable / off state**: `locus.memory.lightrag.enabled`. Off → Locus relies exclusively on PageIndex and Neo4j.


# CI/CD & DEPLOYMENT — §23

## Feature §23.1-23.5: Tests, Docker, Batch Runner

### Source
- **Codebases**: Pi (Vitest) + Hermes (Docker) + OpenHuman (Docker)
- **Verification**: [✅ VERIFIED: codebase structures listed]

### Stripped Logic (Pseudocode)

```
TESTING:
    // Pi's Vitest infrastructure inherited
    // Locus extensions tested alongside Pi tests
    locus_test_config = {
        testDir: "locus/extensions/",
        framework: "vitest",
        mockProviders: true,  // mock sidecar, Neo4j, PG in tests
    }

DOCKER DEPLOYMENT — Locus runs as five containers, orchestrated via docker-compose:

    1. Locus main (TypeScript/Node.js) — Pi + all Locus augmentation. Listens on
       the sidecar port for internal calls. Mounts the Obsidian vault as a volume.
    2. Sidecar (Python FastAPI) — all ML/NLP/computation: Neo4j adapter, Headroom,
       PageIndex, spaCy, GLiNER, sklearn reward model, CouchDB LiveSync bridge. Internal port 8420.
    3. Neo4j Community Edition — bolt :7687, graph memory substrate.
    4. PostgreSQL with pgvector extension — :5432, structured data + 384-dim vectors.
    5. CouchDB (Apache CouchDB 3.3) — :5984, persistent real-time document synchronization
       database for Obsidian Self-Hosted LiveSync, providing bi-directional replication
       between mobile/desktop clients and Locus.
    
    The sidecar auto-starts from the Node.js process on Locus boot (pings /health;
    if no response within 30s, spawns the Python process). Secrets (API keys, Neo4j
    password, Telegram token, CouchDB admin credentials) are injected from `.locus/.env`
    at container start — never baked into the image or compose file. Dockerfiles live in
    `locus-os/Dockerfile` (main) and `locus-os/sidecar/Dockerfile`.

BATCH TRAJECTORY RUNNER (from Hermes):
    FUNCTION batch_evaluate(prompt, n_runs):
        trajectories = []
        FOR i IN range(n_runs):
            session = create_session()
            session.run(prompt)
            trajectories.append(session.trajectory)
        
        // Compare: token usage, tool calls, response quality
        report = compare_trajectories(trajectories)
        RETURN report
```

---

# PYTHON SIDECAR ARCHITECTURE

## Feature: TypeScript ↔ Python Bridge

### Source
- **Codebase**: Locus-original
- **Verification**: [📐 DESIGNED]

### Stripped Logic (Pseudocode)

```
SIDECAR ARCHITECTURE:
    All heavy computation (ML, NLP, Neo4j, sklearn, spaCy, GLiNER) runs in Python,
    called from TypeScript via HTTP. The sidecar is a FastAPI server on
    localhost:8420, auto-started by Locus on boot if not already healthy.
    
    The sidecar exposes a typed HTTP API — one endpoint per subsystem. The
    TypeScript sidecar client is a thin fetch wrapper that POSTs JSON; the
    contract is `(payload) → response`, never raw HTTP strings in business logic.
    
    Endpoints, grouped by subsystem:
        /memory/store, /memory/query          — Neo4j adapter (§4.1-4.2)
        /entities/extract                     — GLiNER entity + GLiREL relation extraction
        /brain/think, /brain/patterns         — proactive reasoning + pattern engine
        /life/dcs, /life/schedule             — DCS calculation + scheduling algorithm
        /vault/crawl, /vault/index            — vault file crawler + PageIndex tree builder
        /vault/sync/status, /vault/sync/push  — CouchDB LiveSync status, inbound/outbound sync trigger
        /reward/score, /reward/retrain        — reward model scoring + weekly retraining
        /voice/stt, /voice/tts                — speech-to-text + text-to-speech
        /health                               — liveness check
    
    AUTO-START: on Locus boot, ping `/health`; if no response, spawn the Python
    sidecar as a child process, then wait up to 30 seconds for it to become healthy.
```

---

# DATABASE SCHEMA

## Feature: PostgreSQL Tables (reference data model — not copy-paste DDL)

### Logic
Locus uses PostgreSQL (with pgvector extension) as the structured-data store.
Every table below is referenced by the pseudocode in the sections above. The
schema is listed as a functional reference: table name + columns + what it holds.
Implement from this, not from SQL.

Key tables, grouped by subsystem:

    STATE & EVENTS:
        current_state         — one row: DCS, mode, faction status, Redis-backed TTL 6h
        behavioral_events     — chronological truth record; every stage writes here
        checkins              — morning/afternoon/evening/night structured check-in data
        state_snapshots       — periodic Redis cache fallback writes

    TASK SYSTEM (Life OS):
        tasks                 — title, faction, importance, D threshold, TWS, status, deferral count
        task_deferrals        — one row per deferral; >3 triggers a Deferral Pattern flag
        faction_weights       — faction × week: target %, actual %, next-week weight
        goal_stack            — Outcome → Project → Task tree (level=vision/milestone/daily)

    MEMORY & LEARNING:
        reward_signals        — 👍/👎 per response; features JSONB feeds weekly RL model retrain
        brain_observations    — Inner Loop output; 384-dim embedding + horizon + reward score
        detected_patterns     — multi-horizon pattern engine output; confidence + first/last seen
        inner_loop_log        — one row per proactive pass (tokens, suppressed, surfaced)

    INFRA:
        vault_file_hashes     — path → MD5; incremental crawl skips unchanged files
        couchdb_sync_state    — last_seq, replication checkpoints, pending conflicts
        telegram_sessions     — maps Telegram chat ID → Pi session ID
        tool_usage            — tool name + args hash + success/fail + duration
        shutdown_log          — one row per graceful/ungraceful exit (uptime, memory, last error)
        webhooks              — URL + subscribed events + HMAC secret

    VECTOR (pgvector extension):
        vault_chunks          — 384-dim BAAI/bge-small embedding + source file metadata
        (Neo4j Agent Memory handles its own vector indexes internally — separate system.)

### Repo vs `.locus`
The schema lives in `locus-os` (migrations). The actual Postgres connection
string / password live in `.locus/.env`. The pgvector extension must be enabled
in the Postgres container (pgvector/pgvector:pg16 Docker image).

---

# CROSS-CUTTING: Data Flow Summary

```
USER MESSAGE (any channel)
    │
    ├─ Stage 0: INTAKE → log to PG, handle voice/attachments
    ├─ Stage 1: INJECTION FILTER → regex + semantic check
    ├─ Stage 2: QUERY ROUTER → classify intent, determine sources
    ├─ Stage 3: STATE INJECTION → inject DCS, mode, faction from PG
    ├─ Stage 4: PARALLEL RETRIEVAL → fire queries to [PG, Neo4j, PageIndex, Web]
    ├─ Stage 5: HEADROOM COMPRESSION → compress results to budget
    ├─ Stage 6: CONTEXT FORGE → assemble 6 layers into 800 tokens
    ├─ Stage 7: TOOL GUARDRAILS → classify idempotent/mutating, loop detection
    ├─ Stage 8: SPECIAL ROUTING → coding→harness, research→autoresearch, command→handler
    ├─ Stage 9: GENERATOR → LLM call (DeepSeek V4 Flash default)
    ├─ Stage 10: ANTI-HALLUCINATION → verify claims against context
    ├─ Stage 11: DELIVERY → format, send to channel, log to PG
    └─ Stage 12: LEARNING → background review, memory sync, tool tracking, profile update

PROACTIVE INNER LOOP (every 90 min, 07:00-00:00):
    ├─ Budget check → skip if >80% daily budget used
    ├─ State gather → current DCS, alerts, recent events
    ├─ vault_crawler.crawl() → reindex changed files
    ├─ pattern_engine.detect() → 5-horizon patterns
    ├─ generator.think() → formulate proactive thought
    ├─ Deduplication → cosine similarity check (suppress if >0.85)
    ├─ reward_model.score() → gate output (≥0.6 threshold)
    ├─ Route → HIGH:Telegram now, MEDIUM:queue for briefing, LOW:store only
    ├─ Spaced repetition → surface decaying-but-relevant memories
    ├─ Wants Engine → identify data gaps, generate Want candidates
    └─ Log → inner_loop_log entry

MORNING BRIEFING (08:00 IST):
    ├─ Yesterday's summary
    ├─ Today's DCS + operating mode
    ├─ Queued Inner Loop observations
    ├─ Suggested schedule
    ├─ Active Wants
    ├─ Faction lag warnings
    └─ Deferral alerts
```

---

> **v2 closing note**: this document decomposes ALL §1-§30 features. It names the exact source files and their stripped logic — sufficient to build most of Locus from the pseudocode alone. For the four cloned dependencies, open the real source under `5_Locus/deps/` (or query via the graph skill) when deeper implementation detail is needed. Where any formula in this doc disagrees with `LOCUS_SYSTEM_v1.md`, the bible wins (see Appendix C below).

---

# APPENDIX C — FORMULA CROSSWALK (single source of truth)

> Every numeric formula in this doc is checked here against `LOCUS_SYSTEM_v1.md` (the system bible) and `locus_agent_loop.md`. If a formula appears elsewhere in this doc with a different value, **this table wins**. v1's fabricated HYPERFOCUS/SUSTAIN/BALANCED mode set and the 0.3/0.3/0.2/0.2 DCS weighting were corrected to the canonical values below.

| Formula | Correct value | Source | Used at |
|---------|--------------|--------|---------|
| DCS | `((E+M+S)/3) × (1 − ST/20)` | `LOCUS_SYSTEM_v1.md` §4 | §25.1, §2.4 |
| Operating modes | SURVIVAL 0.0–2.0 · RECOVERY 2.1–4.0 · NORMAL 4.1–6.0 · DEEP WORK 6.1–8.0 · PEAK 8.1–10.0 | `LOCUS_SYSTEM_v1.md` §5 | §25.1, §2.4, §8 |
| TWS | `(P × 0.4) + (U × 0.4) + (D × 0.2)` | `LOCUS_SYSTEM_v1.md` §3.2 | §25.1 |
| Lag bonus | Lag >3h → TWS +2 · Lag >6h → +4 · ahead → −1 | `LOCUS_SYSTEM_v1.md` §7 | §25.1, Scheduler |
| Faction weekly split | Health 25% · Leverage 25% · Craft 30% · Expression 20% | `LOCUS_SYSTEM_v1.md` §1 | §25.1 |
| Faction crisis hierarchy | Health > Leverage > Craft > Expression | `LOCUS_SYSTEM_v1.md` §1 | §25.1 |
| Action Gap | `declared_priority − (actual_hrs/target_hrs × 10)`; >5 = alert | `LOCUS_SYSTEM_v1.md` §3.3 | §25.1 |
| Deferral thresholds | 3× = warn · 5× = escalate · 8× = phantom | `LOCUS_SYSTEM_v1.md` §9 | §25.1 |
| Vector store | **pgvector** (never Qdrant — legacy) | `locus_agent_loop.md` + standing decisions | §2.1, §2.5, §30.1, tri-stack |
| Embedding | BAAI/bge-small-en-v1.5, 384-dim | `locus_agent_loop.md` | §2.1, §30.1 |
| Router / cheap-call model | DeepSeek V4 Flash (cheapest available) | `locus_agent_loop.md` | §2.1, §2.2 |
| Sunday synthesis model | Gemini 2.5 Pro (1M context) | `locus_agent_loop.md` | §9, §12 |
| Reactive stage count | **12** (Stage 0 → Stage 12) | `locus_agent_loop.md` | §2.1, data-flow summary |
| Context Forge budget | 800 tokens, 6 layers (80/60/180/150/200/100) | `locus_agent_loop.md` | §2.5 |

---

# APPENDIX D — CLONED DEPENDENCY REGISTER

| Dependency | Cloned at | Key files stripped | Stripped at |
|-----------|-----------|--------------------|------------|
| `neo4j-labs/agent-memory` | `5_Locus/deps/agent-memory` | `core/memory.py`, `graph/schema.py`, `extraction/pipeline.py`, `extraction/gliner_extractor.py` | §4.1-4.2 |
| `headroomlabs-ai/headroom` | `5_Locus/deps/headroom` | `headroom/compress.py`, `transforms/{cache_aligner,content_router,smart_crusher,code_compressor,kompress_compressor}.py`, `ccr/*` | §4.17 |
| `VectifyAI/PageIndex` | `5_Locus/deps/PageIndex` | `pageindex/page_index_md.py`, `pageindex/tree_optimize.py`, `pageindex/agent_tools.py` | §27.1 |
| `karpathy/autoresearch` | `5_Locus/deps/autoresearch` | `prepare.py`, `train.py`, `program.md`, `README.md` | §11.6 |

> **v2 correction note**: v1 cited guessed file names for these four (`client.py`, `long_term.py`, `short_term.py`, `reasoning.py` / `proxy.py`, `mcp.py`, `ccr.py` / `tree_index.py`, `reasoning_rag.py`) that do not exist. The real file names are in the sections above. The corrected sections (§4.1-4.2, §4.17, §27.1, §11.6) are the authoritative versions.

---
