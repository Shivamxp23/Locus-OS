# Audit: LOCUS_FEATURE_LOGIC_DECOMPOSITION.md vs. Original Prompt

> **Verdict**: The document is **~65% compliant** with what the original prompt asked for. It delivers on pseudocode and adaptation notes, but **fundamentally misses the core purpose**: acting as a precise codebase-to-codebase logic stripping reference that an AI coder can use to locate source files in OTHER codebases, understand their logic, and replicate it for Locus. Below is the full breakdown.

---

## What You Were Actually Trying to Do

Your prompt had a **very specific pipeline** in mind:

```
1. Feature List (from Atomic Selections) → 
2. For each feature, identify which OTHER codebase(s) it borrows from →
3. Use /understand-anything to find ALL relevant files in those codebases →
4. List out every file with its PURPOSE + how files interrelate →
5. STRIP the logic from those files (atomic, per-feature) →
6. Write pseudocode/algorithms (NO raw code) →
7. Detail how each feature ADAPTS to Locus' architecture →
8. Output one surgically precise markdown document an AI can code from
```

**The goal was**: Make a document so complete that an AI coder can:
- Read a feature section
- Know EXACTLY which files from Pi/Hermes/OpenHuman to study
- Understand the distilled logic without ever reading those files
- Know precisely what to KEEP, ADAPT, and DROP for Locus
- Have enough pseudocode precision to write working code without ambiguity

---

## Section-by-Section Audit

### ✅ What the Document Does Well

| Aspect | Score | Notes |
|--------|-------|-------|
| **Overall structure** | ✅ Good | Clean per-feature sections with Source → Files → Pseudocode → Adaptation |
| **Pseudocode quality** | ✅ Good | Most pseudocode is detailed enough to implement (agent loop, Context Forge, CCR, DCS) |
| **Adaptation notes** | ✅ Good | KEEP/ADAPT/DROP pattern is consistent and useful |
| **Provider interface coverage** | ✅ Excellent | All 25 provider interfaces documented with lifecycle pattern |
| **Data flow summary** | ✅ Excellent | The 12-stage pipeline + proactive loop + morning briefing visualization |
| **Database schema** | ✅ Excellent | Complete PG schema with all tables and columns |
| **Cross-cutting architecture** | ✅ Good | Sidecar architecture, docker-compose, CLI commands |
| **Verification tags** | ✅ Good idea | `[✅ VERIFIED]`, `[📐 DESIGNED]`, `[❓ ESTIMATE]` are useful trust signals |

---

### ❌ Critical Failures (Must Fix)

#### 1. **File Mappings Are Shallow or Fabricated**

> [!CAUTION]
> This is the #1 failure. The prompt EXPLICITLY asked: *"List out in detail (preferably in a clean table) for which feature, which codebase we will be referring from, which all files are linked to that particular feature and the detailed purpose of each file and how they work in congruence with the other files."*

**What was delivered**:
- §1.1 (Pi Agent Loop): ✅ Lists 4 files with line counts and purposes — **this is what every section should look like**
- §4.1-4.2 (Neo4j Memory): ❌ Lists `client.py`, `long_term.py`, `short_term.py`, `reasoning.py` — **these are GUESSES from repo documentation, not verified file reads**. Tagged `[❓ ESTIMATE]`.
- §4.17 (Headroom CCR): ❌ Lists `compress.py`, `proxy.py`, `mcp.py`, `ccr.py` — **GUESSES, not verified**. Tagged `[❓ ESTIMATE]`.
- §27.1 (PageIndex): ❌ Lists `tree_index.py`, `reasoning_rag.py` — **GUESSES**. Tagged `[❓ ESTIMATE]`.
- §1.7 (Post-Turn Review): ✅ Lists 3 Hermes files with line counts — **good**
- §10.3 (User Profile): ✅ Lists 6 files across 2 codebases — **good**
- §13 (Security): ✅ Lists 10 files across 3 codebases — **good**
- §17 (Channels): ⚠️ Lists Hermes files but misses specifics
- §18 (MCP): ✅ Lists 8 OpenHuman files — **good**

**Problem**: For the three EXTERNAL repos (neo4j-agent-memory, headroom, PageIndex), the file listings are entirely speculative. The agent never cloned these repos or read their actual file structures. It invented plausible filenames from README documentation.

**Impact**: An AI coder following this document for Memory, Compression, or Retrieval would immediately get stuck because the file paths, function signatures, and module structures are WRONG.

**Fix Required**: 
- Clone all three repos
- Read their actual directory structures and key files
- Replace `[❓ ESTIMATE]` sections with `[✅ VERIFIED]` after actual file reads
- List REAL filenames with REAL line counts

---

#### 2. **Missing: How Files Work Together (Inter-File Flow)**

> [!IMPORTANT]
> The prompt asked: *"how they work in congruence with the other files"*

The document lists files in tables but rarely explains the **call chain** between them. For example:

- §1.7: Lists `background_review.py`, `memory_manager.py`, `insights.py` but doesn't show: "background_review imports memory_manager, calls `memory_manager.sync_turn()`, which in turn calls `memory_provider.store()`, which writes to the active provider."
- §13: Lists 10 security files but doesn't show which calls which, or the execution order.

**The document needed**: Mermaid diagrams or explicit call-chain pseudocode showing file A calls file B which writes to file C. The §1.1 agent loop section does this implicitly (the pseudocode shows the hook chain), but most other sections don't.

**Fix Required**: For each feature that involves 3+ files, add a brief call-chain or dependency diagram:
```
background_review.py 
  → fork_agent() using parent runtime
  → tool_whitelist filter → only "memory", "skill_manage"
  → memory_manager.py.sync_turn() → memory_provider.store()
  → insights.py.extract_insights() → curator pattern
```

---

#### 3. **External Repos Not Actually Analyzed**

> [!WARNING]
> The prompt said: *"For all the features... you will then need to use the /understand-anything skill to accurately find all the relevant files attached to the feature."*

The document marks three critical features with `[❓ ESTIMATE]`:
- **Neo4j Agent Memory** — The CORE memory system
- **Headroom** — The CORE compression system  
- **PageIndex** — The CORE retrieval system

These three are the **Memory + Token Compression + Smart Retrieval** tri-stack that the user described as the STANDARD memory pipeline. They are the most important features to get right, and they're the least verified.

**Fix Required**:
- Clone `neo4j-labs/agent-memory`, `headroomlabs-ai/headroom`, `VectifyAI/PageIndex`
- Read actual source files (entry points, core modules, config)
- Produce verified file tables and pseudocode from REAL code, not README guesses
- Describe the actual integration surface (API, CLI, MCP, library import?)

---

#### 4. **Missing: Locus-Specific Additions from User Prompt**

The user's prompt added several explicit requirements that the document either ignores or undercovers:

| User Requirement | Document Coverage | Status |
|-----------------|-------------------|--------|
| Memory = Neo4j Agent Memory + Headroom + PageIndex as DEFAULT tri-stack | ⚠️ Mentioned in §4 but not architected as a unified pipeline | **Needs a dedicated "Memory Tri-Stack Integration" section showing how the three work as one** |
| Other memory providers (mem0, supermemory, honcho, mastra, cognee, custom) as OPTIONS | ✅ Listed in provider table | OK |
| File crawlers for proactive agent work | ⚠️ Mentioned as `vault_crawler` in inner loop but no dedicated file listing or logic stripping | **Needs its own section with crawler logic** |
| `karpathy/autoresearch` as invokeable | ✅ Covered in §11.6 / Research layer | OK but `[❓ ESTIMATE]` — not verified |
| Locus should delegate to external coding harnesses (Antigravity, Claude Code, OpenCode, Pi) | ✅ Covered well in §3.7 / Harness Delegation | Good |
| Native MCP support | ✅ Covered in §18 | Good |
| Refer to HTML files in Ideas & System | ❌ Not referenced at all | **Three HTML files (`Comprehensive Locus System Design.html`, `locus_microsystems.html`, `locus_pyramid.html`) were never read** |

---

#### 5. **Some Pseudocode Is Too Vague to Code From**

The document's own stated goal: *"An AI coder can implement any feature from this document alone, without ever reading the original codebase files."*

Sections that fail this test:

| Section | Problem |
|---------|---------|
| §4.1-4.2 (Neo4j Memory) | POLE+O schema is described but Cypher queries are generic examples, not the actual agent-memory repo's queries. GLiNER/GLiREL integration path is vague. |
| §4.17 (Headroom CCR) | Content type routing logic (`JSON`, `CODE`, `PROSE`, `MIXED`) is listed but the actual algorithms for each type are "keep keys, summarize values" — too vague to implement. |
| §27.1 (PageIndex) | Tree construction pseudocode is reasonable but the "LLM navigates tree by choosing most relevant node" lacks the actual prompt template. |
| §10.3 (User Profile) | Stability detector's "consistency scoring" function is mentioned but never defined. What does `score_consistency()` actually compute? |
| §29 (Miscellaneous) | Code Graph Analysis is a 6-line sketch. Workflows are 12 lines. Subconscious is 8 lines. These are too skeletal. |

---

#### 6. **Duplicate Content**

The "Data Flow Summary" (12-stage pipeline + proactive loop) appears **twice** in the document:
- Lines 2103-2128
- Lines 3149-3189

The second instance has additional detail (budget check, deduplication, Wants Engine, morning briefing). These should be merged into one canonical version.

---

### ⚠️ Minor Issues

| Issue | Location | Fix |
|-------|----------|-----|
| Inconsistent section numbering | §4.16 is used for both "Memory Orchestrator" (Atomic Selections) and "Context Compression" (decomposition doc) and "Memory Provider Interface" (decomposition doc) | Normalize references |
| Feature numbering gaps | Document covers §1-§13, §17-§18, §25-§29 but skips §14-§16, §19-§24 in detail | Some are covered under different headers (Voice = §14, Browser = §16), but §15 (notifications), §19 (export), §20 (desktop), §22 (config), §24 (privacy) need coverage or explicit "inherited from Pi" notes |
| Verification drift | §1.7 says "first 100 lines read" for a 609-line file — that's only 16% | Should note what the remaining 509 lines cover, or flag as partial read |
| Component paths are aspirational | Paths like `locus/providers/memory/neo4j-agent-memory.ts` don't exist yet | Fine for a planning doc, but should be explicitly marked as "target path" |

---

## Recommendations: What to Change for the Perfect Document

### Tier 1: Must Fix (Document Is Unreliable Without These)

1. **Clone and verify all three external repos** (neo4j-agent-memory, headroom, PageIndex). Replace all `[❓ ESTIMATE]` sections with verified file tables and pseudocode.

2. **Add inter-file dependency chains** for every multi-file feature. Format: `FileA.function() → FileB.function() → writes to DataStore`.

3. **Add a dedicated "Memory Tri-Stack Integration" section** showing how Neo4j Agent Memory + Headroom CCR + PageIndex work as a unified pipeline. Include:
   - Data flow diagram
   - Which component calls which
   - Where each sits in the 12-stage reactive pipeline
   - How they share data (cache keys, entity IDs, etc.)

4. **Read the three HTML files** in Ideas & System (`Comprehensive Locus System Design.html`, `locus_microsystems.html`, `locus_pyramid.html`) and integrate any architectural insights that the markdown files don't capture.

5. **Flesh out vague pseudocode** in §4.17 (compression algorithms per content type), §10.3 (stability scoring function), §29 (code graph, workflows, subconscious).

### Tier 2: Should Fix (Quality Improvements)

6. **Add a master feature↔file mapping table** at the top of the document. One giant table: Feature ID | Feature Name | Source Codebase | Key Files | Verification Status. This gives an AI coder instant lookup.

7. **Merge duplicate data flow summaries** into one canonical version (keep the more detailed one from lines 3149-3189).

8. **Add the "File Crawler" as a first-class feature** with its own section, not buried inside the Inner Loop. It needs: directory scanning logic, MD5 change detection, incremental reindexing, and how it feeds both PageIndex and pgvector.

9. **Standardize section format**. Every section should have EXACTLY:
   ```
   ## Feature §X.Y: Name
   ### Source (codebase + verification tag)
   ### Files Involved (table with file, lines, purpose, interacts-with)
   ### Inter-File Call Chain (dependency flow)
   ### Stripped Logic (pseudocode)
   ### Adaptation to Locus Architecture (component path, provider interface, KEEP/ADAPT/DROP)
   ```
   Several sections skip the Files Involved table or the Call Chain.

### Tier 3: Nice to Have

10. **Add estimated implementation complexity** per feature (T-shirt size: S/M/L/XL) to help prioritize build order.

11. **Add a "Provider Stacking" section** explaining how multiple providers of the same interface compose (e.g., Neo4j + mem0 for memory — who wins on conflict? How are results merged?).

12. **Add error/failure paths** to pseudocode. Most pseudocode shows the happy path only. What happens when Neo4j is down? When GLiNER fails? When the sidecar is unreachable?

---

## Compliance Scorecard

| Prompt Requirement | Compliance | Score |
|--------------------|-----------|-------|
| "List which codebase we refer from for each feature" | ✅ Done for most features | 8/10 |
| "Find ALL relevant files using /understand-anything" | ⚠️ Done for Pi/Hermes/OpenHuman, NOT done for 3 external repos | 5/10 |
| "Detailed purpose of each file" | ⚠️ Done for some, missing for many | 6/10 |
| "How files work in congruence" | ❌ Rarely shown | 3/10 |
| "Atomic feature-wise logic stripping" | ✅ Pseudocode is generally good | 7/10 |
| "How logic adapts to Locus architecture" | ✅ Consistently provided | 8/10 |
| "No code directly baked in (only pseudocode)" | ✅ Fully compliant | 10/10 |
| "Surgically precise and atomic" | ⚠️ Precise for core features, vague for peripherals | 6/10 |
| "An AI can code from this alone" | ⚠️ True for ~60% of features, false for Memory/Compression/Retrieval tri-stack | 5/10 |
| "Refer to HTML files in Ideas & System" | ❌ Not done | 0/10 |
| **Overall** | | **5.8/10** |

---

## TL;DR

The document is a **solid first draft** with good structural instincts (per-feature sections, pseudocode, adaptation notes, provider tables). But it fails on the **core value proposition** your prompt was designed for: being a reliable bridge between other codebases and Locus implementation. The three most critical features (Memory, Compression, Retrieval) are based on guesswork rather than verified file reads, inter-file dependency flows are mostly absent, and three system design HTML files were never consulted. 

To make this the "perfect report file to give to an AI model to follow to copy and code from," the fixes in Tier 1 are non-negotiable.
