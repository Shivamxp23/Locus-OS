# Phase 3 Walkthrough: Deep Knowledge & Autonomy Engine

## Overview

Phase 3 implements the **Deep Knowledge & Autonomy Engine**, bringing online the capabilities from the cloned dependencies (`deps/headroom`, `deps/PageIndex`, `deps/ai to obsidian`, `deps/autoresearch`) and high-impact subsystems specified in `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md`.

---

## What Was Built

### 1. Headroom CCR Context Compression (§4.17)
**Files**:
- [`core/context/headroom_adapter.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/context/headroom_adapter.py)
- [`core/context/__init__.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/context/__init__.py)
- [`core/locus_tools.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/locus_tools.py)

**Features**:
- **Smart Content Routing**: Detects JSON, Code, Logs, and Prose.
- **SmartCrusher for JSON**: Deduplicates keys, samples massive arrays, strips null/empty fields.
- **AST Structural Code Compressor**: Preserves function signatures, classes, docstrings, and imports while collapsing dense bodies.
- **Log Compressor**: Preserves head and tail error traces while pruning repetitive logs.
- **Prompt-Cache Alignment**: Freezes system prompt and recent turns to maximize KV prompt caching hits.
- **Reversible Retrieval (CCR)**: Caches full uncompressed chunks in `~/.locus/headroom_cache/` and injects retrieval markers.
- **`headroom_retrieve` tool**: Allows the LLM to lazily pull back full uncompressed original content on demand.

---

### 2. PageIndex Vectorless Tree-Search (§27.1)
**Files**:
- [`core/search/pageindex.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/search/pageindex.py)
- [`core/conductor.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/conductor.py)
- [`core/locus_tools.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/locus_tools.py)

**Features**:
- **Markdown Header Hierarchy Parser**: Builds structural Table-of-Contents tree from `#` to `######` headings and bold headings, ignoring fenced code blocks.
- **Bottom-Up Token Count Roll-Up**: Computes cumulative tokens for every subtree.
- **Tree Thinning**: Merges small leaf nodes into parent branches while retaining structural headings.
- **Reasoning-Based Tree Traversal**: Navigates root $\to$ branch $\to$ leaf nodes using branch summaries without vector embedding drift.
- **Conductor Integration**: Step 5 parallel retrieval fires PageIndex queries alongside Neo4j and memory.
- **`locus_pageindex` tool**: Exposes `index` and `query` actions directly to the agent.

---

### 3. Daily AI Chat Archiver (§19.3, §27.2)
**Files**:
- [`core/ingestion/chat_archiver.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/ingestion/chat_archiver.py)
- [`core/ingestion/__init__.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/ingestion/__init__.py)

**Features**:
- **Multi-Platform Parsing**: Ingests ChatGPT JSON exports, Claude conversation exports, Cursor transcripts, Telegram exports, and markdown dumps.
- **Data Normalization & Cleaning**: Strips ChatGPT sentinel/PUA characters (`\ue000-\uf8ff`) and extracts Q&A pairs.
- **Decision & Summary Extraction**: Automatically isolates key decisions and takeaways.
- **Faction Tagging**: Maps conversations to Health, Leverage, Craft, or Expression.
- **Obsidian Output**: Writes structured notes with YAML frontmatter to `/vault/04-Captures/AI Chats/YYYY-MM-DD/{title}.md`.
- **Auto-Indexing**: Automatically indexes new archives into PageIndex.

---

### 4. Collector & Multi-Source Chunker (§30.1)
**Files**:
- [`core/ingestion/collector.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/ingestion/collector.py)

**Features**:
- **MD5 Vault Crawler**: Incremental directory traversal skipping unchanged notes.
- **Markdown Sanitizer**: Strips Dataview blocks, Obsidian transclusions `![[...]]`, YAML noise, and normalizes wikilinks.
- **Sentence Boundary Detection**: Factual candidate sentence segmentation filtering out fluff.
- **5-Proposition Chunk Assembler**: Groups sentences into dense semantic chunks with entity continuity.
- **SQLite Storage**: Persists indexed chunks in `~/.locus/vault_chunks.db` with faction tags and token counts.

---

### 5. Faction Subagents & AutoResearch Loop (§11.1–11.6)
**Files**:
- [`core/delegation/archetypes.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/delegation/archetypes.py)
- [`core/delegation/autoresearch.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/delegation/autoresearch.py)
- [`core/delegation/__init__.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/delegation/__init__.py)

**Features**:
- **4 Faction Archetypes**:
  - `Planner` (Health/Life OS, DCS, scheduling)
  - `Curator` (Craft/Vault, memory hygiene, spaced repetition)
  - `Analyst` (Leverage, pattern engine, cause chain)
  - `Builder` (Craft, Pi-style 4-step coding loop)
- **Depth Limiting**: Enforces `MAX_SPAWN_DEPTH = 3` and budget limits.
- **Karpathy-Style AutoResearch**: Iterative hypothesis generation, multi-source evidence gathering (Web, Vault, PageIndex), validation scoring, and Research Brief generation in `/vault/01-Projects/Research/`.

---

### 6. Autonomous Content Engine (§30.4)
**Files**:
- [`core/content/voice_matcher.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/content/voice_matcher.py)
- [`core/content/engine.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/content/engine.py)
- [`core/content/__init__.py`](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/core/content/__init__.py)

**Features**:
- **Milestone Detection**: Event listener for $L \ge 8$ task completions, goal milestones, and git releases.
- **Anti-Cringe Voice Matcher**: Strictly penalizes corporate buzzwords (*"excited to share"*, *"humbled"*, *"in today's fast-paced world"*, *"leverage synergies"*).
- **Multi-Platform Draft Generator**: Produces 4 format variants:
  1. Substack / Blog Long-Form Essay (600–1200 words)
  2. LinkedIn Post (Structured technical bullets)
  3. X / Twitter Thread (5 tweets)
  4. Telegram Status Update
- **Vault Draft Assembly**: Stores drafts in `/vault/06-Content/Drafts/` with status `pending_review`.
- **Conductor Integration**: Automatically detects milestone achievements in `post_turn_sync()`.

---

## Verification & Test Results

All 16 tests across Phase 1, Phase 2, and Phase 3 passed:

```
============================= test session starts =============================
platform win32 -- Python 3.13.7, pytest-7.4.0, pluggy-1.6.0
plugins: anyio-4.12.0, hydra-core-1.3.2, langsmith-0.3.9, asyncio-0.22.0, typeguard-4.5.1
asyncio: mode=Mode.STRICT
collected 16 items

core/test_core.py::test_cron_matcher PASSED                              [  6%]
core/test_core.py::test_approval_store PASSED                            [ 12%]
core/test_core.py::test_cost_tracker PASSED                              [ 18%]
core/test_memory_backends.py::TestMemoryBackends::test_default_config_schema PASSED [ 25%]
core/test_memory_backends.py::TestMemoryBackends::test_holographic_backend PASSED [ 31%]
core/test_memory_backends.py::TestMemoryBackends::test_neo4j_backend_nams PASSED [ 37%]
core/test_memory_backends.py::TestMemoryBackends::test_sqlite_fallback PASSED [ 43%]
core/test_phase3.py::test_headroom_ccr_compression PASSED                [ 50%]
core/test_phase3.py::test_headroom_code_and_log_compression PASSED       [ 56%]
core/test_phase3.py::test_pageindex_tree_building_and_query PASSED       [ 62%]
core/test_phase3.py::test_chat_archiver_multi_platform PASSED            [ 68%]
core/test_phase3.py::test_vault_collector_and_sanitizer PASSED           [ 75%]
core/test_phase3.py::test_subagent_archetypes_and_depth_limiting PASSED  [ 81%]
core/test_phase3.py::test_autoresearch_loop PASSED                       [ 87%]
core/test_phase3.py::test_voice_matcher_anti_cringe_evaluation PASSED    [ 93%]
core/test_phase3.py::test_content_engine_milestone_drafts PASSED         [100%]

============================= 16 passed in 11.00s =============================
```
