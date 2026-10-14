# Fix LOCUS_FEATURE_LOGIC_DECOMPOSITION.md — Implementation Plan

## Goal

Surgically fix all 6 critical failures and all minor issues identified in the audit, transforming the document from a 5.8/10 draft into the "best-in-class report an AI can code from."

## Key Discovery: HTML Files Are the Missing Ground Truth

The three HTML files you built are **far more detailed than anything in the markdown docs**:

- [locus_microsystems.html](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Ideas%20and%20System/Systems/locus_microsystems.html) — Contains **micro-step breakdowns** for every system (Master Conductor 11 steps, Query Router 6 steps, Inner Loop 10 steps, Context Forge 12 steps, Pattern Engine 11 steps, Scheduler 11 steps, Goal Tracker 8 steps, State Engine 10+ steps, Collector+Chunker 10 steps, Neo4j 6 steps, Qdrant 4 steps, PostgreSQL 4 steps, Telegram Bot 7 steps, Voice 5 steps, AI Chat Archiver 7 steps, Obsidian Dashboard 6 steps, Content Engine 4+ steps) — each with inputs, outputs, and providers.
- [Comprehensive Locus System Design.html](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Ideas%20and%20System/Systems/Comprehensive%20Locus%20System%20Design.html) — Contains a **10-layer architecture pyramid** (Infrastructure, Storage, Ingestion, Retrieval, Intelligence, Reasoning, Orchestration, Interface, Output, Feedback) with node-level detail for ~40+ components.
- [locus_pyramid.html](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Ideas%20and%20System/Systems/locus_pyramid.html) — Contains the **architecture tier system** (T0 Master → T1 Orchestration → T2 Intelligence → T3 Retrieval → T4 Storage → Input/Output/Feedback/Self-Maintenance layers) with descriptions, inputs/outputs, and status for each node.

> [!IMPORTANT]
> These HTML files contain significantly richer detail than the decomposition doc for: DCS formula (with specific normalization), Context Forge's 12-step assembly with token budgets per layer, Pattern Engine's 11-step flow with Bayesian confidence updates, Scheduler's 11-step flow with faction lag bonus tiers, Collector+Chunker's 10-step ingestion pipeline, and the complete Neo4j Hebbian lifecycle.
>
> **This means**: For Locus-original features (§25 Life OS, §10.6 Hebbian, §10.7 Pattern Engine, etc.), the HTML files ARE the verified source — they replace the `[📐 DESIGNED]` tag with `[✅ VERIFIED: from microsystems.html]`.

---

## Proposed Changes

### Phase 1: Add Master Feature↔File Mapping Table + HTML Integration Tag

#### [MODIFY] [LOCUS_FEATURE_LOGIC_DECOMPOSITION.md](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Implementation%20Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION.md)

- Add a **master lookup table** at the top of the document (after the preamble, before §1)
- Format: `| §ID | Feature | Source Codebase | Key Files | Verification | Provider Interface |`
- Covers all ~90 features
- Add a new subsection: **"Source Documents Consulted"** listing all 6 source files (3 markdown + 3 HTML) with what was extracted from each

---

### Phase 2: Replace All `[❓ ESTIMATE]` with Verified Data

#### For Neo4j Agent Memory (§4.1-4.2):

The HTML microsystems file reveals the actual Neo4j usage pattern in Locus's own architecture. Since the user's prompt says to use `neo4j-labs/agent-memory` as a PRE-BUILT solution, I will:
- Document the **integration surface**: Neo4j Agent Memory is used as-is via its MCP/API interface. Locus does NOT rewrite the memory backend — it plugs in the agent-memory package.
- Replace the guessed file listings with the **actual integration pattern**: how Locus calls Neo4j Agent Memory's endpoints, what POLE+O schema it expects, and how it maps to the `MemoryProvider` interface.
- Tag as `[✅ VERIFIED: integration surface documented from repo README + microsystems.html Neo4j section]`

#### For Headroom CCR (§4.17):

- Document as a **consumed dependency**: Headroom is invoked via its MCP server or CLI. Locus implements a `CompressionProvider` that wraps Headroom's API.
- Replace guessed files with the actual **interface contract**: input (raw text + content type), output (compressed text + token count), configuration (compression ratios per content type).
- Tag as `[✅ VERIFIED: integration surface documented from repo README]`

#### For PageIndex (§27.1):

- Document as a **consumed dependency**: PageIndex is invoked via its Python API. Locus implements a `RetrievalProvider` that wraps PageIndex's tree-based retrieval.
- Replace guessed files with the actual **interface contract**: input (directory path), output (tree index), query interface (question → tree navigation → leaf content).
- Tag as `[✅ VERIFIED: integration surface documented from repo README]`

> [!NOTE]
> Since the user's "laziness first" philosophy means these are plug-in dependencies, not code to be rewritten, the correct documentation is the **integration surface** (what Locus passes in, what it gets back, how it maps to the provider interface), NOT the internal implementation of these repos.

---

### Phase 3: Add Inter-File Dependency Chains

For every feature involving 3+ files or 3+ components, add a **Call Chain** subsection showing the execution flow.

Format:
```
CALL CHAIN:
    user_message
    → telegram_handler.on_message()          [locus/channels/telegram.ts]
    → master_conductor.process()             [locus/core/conductor.ts]
    → query_router.classify(message)         [sidecar: POST /router/classify]
    → retriever.parallel_fetch(manifest)     [locus/core/retriever.ts]
        ├→ neo4j_provider.query()            [sidecar: POST /memory/query]
        ├→ pg_provider.structured_query()    [sidecar: POST /pg/query]
        └→ pageindex_provider.search()       [sidecar: POST /vault/search]
    → context_forge.assemble(results)        [sidecar: POST /forge/assemble]
    → llm_provider.generate(context)         [locus/core/llm-client.ts]
    → channel_provider.send(response)        [locus/channels/telegram.ts]
    → learning_pipeline.sync(turn)           [sidecar: POST /learning/sync]
```

Sections requiring this treatment:
- §1 Reactive Loop (12-stage full pipeline)
- §1.7 Post-Turn Review (background review chain)
- §4 Memory Pipeline (tri-stack: Neo4j → Headroom → PageIndex)
- §10.1 Post-Session Learning (4-hook chain)
- §13 Security (3-layer filter chain)
- §17 Telegram Channel (message → pipeline → response)
- §25 Life OS (checkin → DCS → mode → schedule)
- §2 Proactive Inner Loop (trigger → state → think → gate → deliver)
- §3.7 Harness Delegation (intent → selector → spawn → result)

---

### Phase 4: Add Memory Tri-Stack Integration Section

A new top-level section between §4 and §5:

```
# MEMORY TRI-STACK INTEGRATION — Neo4j Agent Memory + Headroom CCR + PageIndex

## Overview
The three pre-built dependencies compose as ONE unified memory pipeline:

Neo4j Agent Memory → STORE (episodic + semantic graph memory)
Headroom CCR       → COMPRESS (context window management)  
PageIndex          → RETRIEVE (tree-structured document retrieval)

## Data Flow
Query → PageIndex tree navigation → candidate documents
     → Headroom compresses candidates to token budget
     → Neo4j Agent Memory retrieves related episodic memories
     → Context Forge merges all into 800-token block

## Integration Points
- PageIndex runs in sidecar (Python), exposed at POST /vault/search
- Headroom runs as MCP server OR sidecar endpoint at POST /compress
- Neo4j Agent Memory connects via bolt:// to Neo4j 5 container
- All three implement their respective provider interfaces
- Context Forge orchestrates them all via parallel retrieval

## How They Share Data
- Entity IDs: GLiNER extracts entities → stored in both Neo4j (as nodes) and PageIndex (as tags)
- Embeddings: pgvector stores embeddings used by both PageIndex and Qdrant
- Token budgets: Headroom's CCR output is what Context Forge uses for its 800-token assembly
```

---

### Phase 5: Flesh Out Vague Pseudocode

Using the HTML microsystems data (which has **much richer detail**), upgrade these sections:

| Section | Current State | Fix |
|---------|--------------|-----|
| §4.17 Headroom CCR | Generic "keep keys, summarize values" | Add content-type-specific compression algorithms from microsystems (LOCUS_SHORTHAND rules, 4× compression) |
| §10.3 User Profile | `score_consistency()` undefined | Add full stability detector algorithm from microsystems Identity Profile section |
| §10.7 Pattern Engine | Basic 5-horizon description | Replace with microsystems' 11-step flow including Bayesian confidence update formula, novelty threshold (0.82), promotion criteria (confidence > 0.8 AND count ≥ 3) |
| §25 Scheduler | 6-step algorithm | Replace with microsystems' 11-step flow including specific lag bonus tiers (3h→+2, 6h→+4, 10h→+6), Three-Birds efficiency mapping, mode constraint rules |
| §25 DCS Formula | Basic weighted average | Replace with microsystems' formula: `DCS = ((E + M + S) / 3) × (1 − ST / 20)` with specific mode thresholds |
| §29 Code Graph | 6-line sketch | Expand with dependency graph construction, call-chain extraction, task scoping algorithm |
| §29 Workflows | 12-line sketch | Expand with step types, approval gates, rollback logic |
| §29 Subconscious | 8-line sketch | Expand with memory consolidation, pattern detection, idle detection |
| Collector+Chunker | Not a standalone section | Add as standalone section using microsystems' 10-step pipeline (MD5 crawl, spaCy SBD, factual classification, 5-proposition chunking, embedding) |

---

### Phase 6: Merge Duplicates + Standardize Format

1. **Merge duplicate Data Flow Summaries** (lines 2103-2128 and 3149-3189) into one canonical version. Keep the more detailed second version, delete the first.

2. **Add missing coverage** for skipped sections (§14-§16, §19-§24):
   - §14 Voice → already covered under "Voice/STT/TTS" section, just add section header
   - §15 Notifications → add from pyramid HTML's Push Notifications node
   - §19 Export → already covered under "Trajectory Recording", add header
   - §20 Desktop/Browser → already covered under "Browser & Computer Use", add header
   - §22 Config → already covered under "CLI & Configuration", add header  
   - §24 Privacy → add from pyramid HTML's Security Layer node

3. **Standardize every section** to this exact format:
   ```
   ## Feature §X.Y: Name
   ### Source (codebase + verification tag)
   ### Files Involved (table: file, lines, purpose, interacts-with)
   ### Call Chain (dependency flow diagram)
   ### Stripped Logic (pseudocode)
   ### Adaptation to Locus Architecture
   ```

---

## Verification Plan

### Manual Verification
- Every `[❓ ESTIMATE]` tag must be replaced with either `[✅ VERIFIED]` or `[✅ INTEGRATION SURFACE]`
- Every feature with 3+ components must have a Call Chain subsection
- The Memory Tri-Stack section must show a complete data flow from query to 800-token output
- The master feature table must cover all ~90 features from Atomic Selections
- Zero duplicate Data Flow Summaries
- All vague pseudocode must be precise enough to implement without ambiguity

## Open Questions

> [!IMPORTANT]
> **Q1**: For the three external repos (neo4j-agent-memory, headroom, PageIndex) — since your philosophy is "laziness first" and these are PRE-BUILT solutions, should I document them as **integration surfaces** (what goes in, what comes out, how Locus calls them) rather than attempting to strip their internal logic? This seems correct per your prompt: "I will provide you with a few things we will certainly use instead of recreating from scratch."
>
> **Q2**: The HTML microsystems file has a **significantly different DCS formula** than the decomposition doc. Microsystems says `DCS = ((E + M + S) / 3) × (1 − ST / 20)` (range 0-10). The decomposition doc says `DCS = (sleep*0.3 + energy*0.3 + mood*0.2 + (1-stress)*0.2) * 100` (range 0-100). Which is canonical?
>
> **Q3**: The microsystems HTML references systems NOT in the decomposition doc: **Cause Chain Engine** (9 steps), **Hebbian Manager** (8 steps), **SOUL.md** personality layer (6 steps), **Content Engine** (4+ steps), **QLoRA Pipeline** (10 steps), **Spaced Repetition** (7 steps). Should these be added as new sections in the decomposition doc?
