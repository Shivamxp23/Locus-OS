# AUDIT — LOCUS_FEATURE_LOGIC_DECOMPOSITION_v3.md
## Against Original Prompt Intent

> **Auditor**: Antigravity (Claude Opus 4.6)  
> **Method**: Full read of v3 (4,104 lines), Atomic Selections (1,177 lines), LOCUS_SYSTEM_v1.md, locus_agent_loop.md references, HTML design docs listing, and the user's original prompt  
> **Date**: 2026-08-14

---

## 0. VERDICT: PARTIAL PASS — ~72%

**v3 is a competent, well-structured document that does ~72% of what the original prompt asked for.** It passes on structure, atomicity, off-state annotations, and formula accuracy. However, it **fundamentally misses** the core intent of the prompt in several critical ways that would cripple an AI implementer trying to build Locus from it.

> [!CAUTION]
> The 9-point structural rubric audit that passed v3 at ~94% was measuring the **wrong thing**. It was checking document formatting and completeness, not whether the document **fulfills the user's stated coding philosophy**. The prompt asked for something much more specific than "a good reference doc."

---

## 1. WHAT THE PROMPT WAS ACTUALLY ASKING FOR

Let me reconstruct the user's intent from their exact words:

### The Core Loop (User's Coding Philosophy)
The prompt describes a **4-step pipeline** that the document was supposed to execute **per feature**:

```
Step 1: IDENTIFY — For each feature, identify the SOURCE CODEBASE 
        and the EXACT files involved
Step 2: STRIP   — Strip the logic from ALL files: how they work together,
        what each file does, interactions between files
Step 3: ADAPT   — Write in detail how the logic adapts to Locus' architecture 
Step 4: OUTPUT  — Pseudocode/algorithms/logic only, never raw code
```

### The Key Constraint: "Never directly refer to any codebase"
The user said: *"Never directly refer to any codebase, directly use the /graphify query skill."* This means the agent building Locus from this doc should be able to:
1. Read the feature section
2. Understand the complete logic without needing to open the source files
3. Know exactly which Locus files to create and what goes in each

### The Laziness-First Mandate
*"If exists in any of the other codebases, STEAL IT'S LOGIC AND IMPLEMENTATION STRATEGY."*

This means for every feature sourced from Pi/Hermes/OpenHuman, the document needed to:
- Show the **full execution flow** distilled from the source
- Show **all the files involved and how they interact**
- Show the **precise adaptation points** for Locus

### The "Provided Resources" Integration
The user specifically named:
- `neo4j-labs/agent-memory` + `headroomlabs-ai/headroom` + `VectifyAI/PageIndex` = **Memory + Compression + Retrieval**
- `karpathy/autoresearch` = **Autonomous research, invokeable**
- **Coding harness delegation** (Antigravity, Claude Code, OpenCode, Pi) — Locus should never code itself
- **File crawlers** needed for proactive features
- **Native MCP support**

---

## 2. ITEM-BY-ITEM AUDIT: WHERE v3 SUCCEEDS

### ✅ PASS — Structure & Atomicity (Score: 9/10)

v3 nails the structural requirements:
- **86 individual `## Feature` sections** (up from ~44 in v2)
- Each feature has: Source, Files Involved, Stripped Logic, Locus Adaptation
- Verification tags per section
- Repo vs `.locus` annotation on every feature
- Off-state annotation on every feature
- No raw code — all pseudocode/algorithms

### ✅ PASS — Four Cloned Dependencies (Score: 9/10)

The four pre-built dependencies are excellently covered:

| Dependency | Quality | Notes |
|:---|:---|:---|
| Neo4j Agent Memory (§4.1-4.2) | **Excellent** | Real file names, extraction pipeline details, POLE+O schema, merge strategy, retrieval path. Real `core/memory.py`, `graph/schema.py`, etc. |
| Headroom CCR (§4.17) | **Excellent** | Complete pipeline: CacheAligner → ContentRouter → [SmartCrusher\|CodeCompressor\|Kompress]. Inflation guard, KV cache awareness. |
| PageIndex (§27.1) | **Excellent** | Full tree-build algorithm (6 steps), retrieval algorithm (navigate root→leaf), real file names. |
| AutoResearch (§11.6) | **Excellent** | 3-file architecture, keep/discard/crash loop, results.tsv ledger. Correct adaptation (Locus delegates, never codes). |

### ✅ PASS — Memory Tri-Stack Integration (Score: 8/10)

Lines 680-730 correctly compose the three into a unified pipeline with a clear data flow diagram. The integration matrix (lines 718-725) is useful.

### ✅ PASS — Pi Agent Loop Foundation (Score: 9/10)

§1.1 (lines 111-252) is the strongest section in the entire document. It:
- Lists exact Pi files with line counts
- Shows the complete dual-loop pseudocode with all 10 KEY HOOKs annotated
- Maps each hook to its Locus purpose
- Shows tool lifecycle (5 steps)

### ✅ PASS — Life OS Layer (Score: 8/10)

§25.1-25.16 (lines 2044-2367) covers all 16 Life OS features with correct formulas verified against LOCUS_SYSTEM_v1.md, and every one has off-state + config path.

### ✅ PASS — Data Flow Summary (Score: 9/10)

Lines 4021-4061 provide the 12-stage reactive pipeline + proactive Inner Loop + morning briefing flow in a single readable diagram. This is one of the most useful sections for an implementer.

### ✅ PASS — Formula Crosswalk (Appendix C) (Score: 10/10)

Single source of truth for all numeric formulas. Explicitly states: "if this doc disagrees with LOCUS_SYSTEM_v1.md, the bible wins."

---

## 3. ITEM-BY-ITEM AUDIT: WHERE v3 FAILS

### ❌ FAIL — Logic Stripping Depth for Non-Cloned Features (Score: 4/10)

> [!CAUTION]  
> **This is the single biggest failure of v3.** The 4 cloned deps (Neo4j, Headroom, PageIndex, AutoResearch) got deep, real logic stripping because the Pi agent actually cloned them and read the source code. But for the ~60+ features sourced from **Pi, Hermes, and OpenHuman**, the logic stripping is **shallow, generic, and often invented rather than read from source.**

**Evidence:**

| Feature | What v3 shows | What the prompt demanded |
|:---|:---|:---|
| §1.7 Post-Turn Review (Hermes) | Lists 3 files (background_review.py, memory_manager.py, insights.py) with line counts. Shows pseudocode for `spawn_background_review`. **Good.** | ✅ This one actually passes — it has real file reads. |
| §13.1 Prompt Injection (OpenHuman) | 6 lines of pseudocode: "Layer 1: Regex blocklist. Layer 2: Semantic check." No files listed. No logic on HOW the regex blocklist works, WHAT patterns, HOW the semantic check decides. | Full file listing of OpenHuman's `prompt_injection/` module, the actual DFA construction, the pattern list, the semantic check prompt, how they compose. |
| §13.3 Sandbox Backends (OpenHuman) | Lists 5 backend kinds. Shows a generic `execute_in_sandbox` function. | The actual Bubblewrap args, Docker mount strategy, Firejail seccomp profile, Landlock ruleset. HOW each backend isolates. File names from OpenHuman's `sandbox/` dir. |
| §17.1-17.11 Channels (Hermes) | Shows `PlatformEntry` dataclass + `register`/`create_adapter` pattern from `platform_registry.py`. Good for registry. **But** only names Telegram adapter logic (4 lines). Discord/Slack/WhatsApp adapters get zero logic. | Full adapter logic for at least Telegram (the primary), with PTB handler structure, inline keyboard handling, voice message pipeline, file attachment processing. |
| §9.4 ACP Protocol | 10-line pseudocode showing a JSON-RPC call. | The actual ACP protocol spec from Hermes, message types, discovery mechanism, how agents find each other, error handling. |
| §29.1 Error Classifier | Simple if/elif chain. | Hermes' actual `error_classifier.py` logic: retry strategies per error type, backoff curves, model fallback chain, how it integrates with the agent loop. |
| §16.1 Browser Automation | Generic "launch Playwright, navigate, screenshot" pseudocode. | OpenHuman's `screen_intelligence/` actual file structure, how the vision model parses screenshots, element identification algorithm, click target resolution. |
| §10.3 User Profile Building | Lists 6 files across OpenHuman + Hermes. Shows 4-hook system pseudocode. **Partially good** — but the `stability_detector.rs` logic is described in 6 lines when the actual file has window management, consistency scoring, facet classification. | Deep logic of the stability window, how consistency is scored, what facets are tracked, the PROFILE.md template, how it integrates with system prompt. |

**Pattern**: For cloned repos → deep, real logic. For Pi/Hermes/OpenHuman features → surface-level pseudocode that an AI couldn't actually implement from.

### ❌ FAIL — `/graphify` Was Not Actually Used (Score: 2/10)

> [!WARNING]  
> The prompt explicitly said: *"Never directly refer to any codebase, directly use the /graphify query skill that is already installed."*  
> v3's verification tags reveal the truth:
> - `[✅ VERIFIED: direct file read (/graphify unavailable)]` appears on **most** Pi/Hermes/OpenHuman features
> - `[✅ VERIFIED: /graphify]` appears on **zero** features
> - The v3 header admits: *"v1/v2 discovery predated its use; future re-mining should route through /graphify"*

This means:
1. The file listings for Pi/Hermes/OpenHuman features are based on **directory scans and header reads**, not deep graph queries
2. The interaction patterns between files are **inferred/guessed** rather than extracted from the knowledge graph
3. An AI implementer following the "use `/graphify` to find relevant files" rule would get more accurate results than what's in v3

### ❌ FAIL — File Interaction Maps Are Incomplete (Score: 5/10)

The prompt explicitly asked for: *"how they work together with other files"* and *"all the files it interacts with so that those relevant files can be stripped into its logic."*

v3's file interaction quality varies wildly:

| Section | Interaction Quality | Issue |
|:---|:---|:---|
| §1.1 Pi Agent Loop | **Excellent** — `agent-loop.ts` → `types.ts` → `agent.ts` → `proxy.ts` with line counts | — |
| §4.1 Neo4j Agent Memory | **Excellent** — 8 files with "Interacts With" column | — |
| §4.17 Headroom CCR | **Excellent** — 8 files with pipeline flow | — |
| §17.1 Channels | **Partial** — `platform_registry.py` covered, but how does `mirror.py` interact with `shutdown_forensics.py`? How does the Telegram adapter call PTB? | Missing inter-file flow |
| §13.1-13.10 Security | **Weak** — Most features list 1-2 source files with no interaction map | Missing "Files Involved" tables |
| §29.1-29.8 Misc | **Weak** — Most are 5-10 line snippets with a single source file named | Missing interaction context |
| §10.3 User Profile | **Good** — 6 files listed with codebase column | Missing inter-file data flow |

### ❌ FAIL — "Atomic Selections from Antigravity.md" Feature Coverage (Score: 6/10)

The prompt said to use this file as the **feature list source**. Let me check coverage:

| Atomic Selections Feature | Covered in v3? | Quality |
|:---|:---|:---|
| §4.5 Memory tree/cascade (OpenHuman bucket-seal) | ❌ Missing | Not mentioned |
| §4.7 Memory sync (OpenHuman) | ❌ Missing | Not mentioned |
| §4.8 Memory queue (OpenHuman) | ❌ Missing | Not mentioned |
| §4.9 Memory diff (OpenHuman) | ❌ Missing | Not mentioned |
| §4.10 Holographic HRR | ❌ Missing | Not mentioned |
| §4.12 STDP reinforcement | ✅ Covered | At §10.6-10.7, 4 lines |
| §6.2 Context references (Hermes) | ❌ Missing | Not mentioned |
| §6.3 Coding-specific context (Hermes) | ❌ Missing | Not mentioned |
| §10.8 Self-evolving Architect Bot | ❌ Missing | Not mentioned |
| §10.9 Agent experience tracking | ❌ Missing | Not mentioned |
| §2.7 Intelligent routing (OpenHuman) | ✅ Listed in table | No logic stripped |
| §2.8 Refusal detection (OpenHuman DFA) | ✅ Listed in table | No logic stripped |
| §5.6 Session compression (3 providers) | ✅ Covered at §4.16 | Good |
| §14.4 Dictation (OpenHuman) | ❌ Missing | Not mentioned |
| §17.6 IRC/Matrix/Teams/etc channels | ❌ Missing | Not mentioned |
| §18.5 Obsidian MCP | ❌ Missing | Not mentioned |
| §27.7 Excalidraw MCP Skill | ❌ Missing | Not mentioned |

**~15 features from Atomic Selections are completely absent from v3.** These aren't obscure — §4.5-4.9 are memory subsystem features that the Atomic Selections doc explicitly calls out as "steal from OpenHuman."

### ❌ FAIL — Coding Harness Delegation Lacks Specificity (Score: 6/10)

The prompt was very specific: *"Locus shouldn't have its own harness to code something, it should understand the user and their requirements and deadline etc..., and based on that, prompt the best coding harness (like antigravity, claude code, opencode, pi etc... the best ones will be pre-installed) to code it for the user."*

v3's §3.7 + §11.5 (lines 1096-1201) covers this but with issues:
- ✅ Shows the delegation flow (select harness → construct prompt → execute → parse results)
- ✅ Lists 4 harnesses (Antigravity, Claude Code, OpenCode, Pi)
- ❌ **Missing user understanding**: The prompt says "understand the user and their requirements and deadline" — v3 doesn't show how Locus assesses task complexity, user preferences, time constraints, or project context to select a harness
- ❌ **Missing harness-specific prompting**: Each harness needs different prompting strategies. v3 shows a generic `format_args(prompt)` but doesn't describe HOW you prompt Claude Code vs Antigravity vs OpenCode differently
- ❌ **Missing "pre-installed" detail**: How are harnesses detected? PATH check? Config? Binary probe?

### ❌ FAIL — MCP Support Depth (Score: 5/10)

The prompt says: *"Plus Locus needs to also have native MCP support."*

v3's §18.1-18.4 (lines 1756-1876) covers MCP but:
- ✅ Dual-transport client (HTTP + stdio) with real OpenHuman file listings
- ✅ Safety filter (sanitize tool descriptions)
- ✅ Registry pattern (static + dynamic)
- ❌ **Missing MCP Server detail**: Line 1874 says "Expose Locus tools via MCP" but doesn't show WHICH tools get MCP endpoints, the MCP tool schema for each, or the SSE streaming implementation
- ❌ **Missing Obsidian MCP** (§18.5 from Atomic Selections): vault_read/write/search/tag/stats tools
- ❌ **Missing how MCP integrates with Pi's tool system**: Does Pi's `registerTool()` auto-expose via MCP? Or is it a separate registration?

### ❌ FAIL — HTML Design Docs Were Not Deeply Mined (Score: 5/10)

The prompt says: *"Plus refer to the html files in Ideas and System and all the other files in there too to understand what I am trying to make in terms of systems."*

Three HTML files exist:
1. `locus_microsystems.html` (155K) — **Partially used**: §2.1-2.6, §30.1-30.6 reference it and extract micro-step breakdowns
2. `Comprehensive Locus System Design.html` (128K) — **Barely used**: Only §30.2 (Cause Chain) and §30.3 (SOUL.md) reference it
3. `locus_pyramid.html` (31K) — **Barely used**: Only §30.6 (QLoRA) references it

The `Comprehensive Locus System Design.html` at 128K contains a **10-layer architecture with ~40 component nodes** (noted in the SOURCE DOCUMENTS table at line 33). This includes subsystems like:
- Cause Chain Engine ✅ (extracted at §30.2)
- LOCUS_SHORTHAND ✅ (extracted at §27.3)
- Hebbian Manager ✅ (extracted at §10.6)
- SOUL.md ✅ (extracted at §30.3)
- QLoRA Pipeline ✅ (extracted at §30.6)
- Spaced Repetition ✅ (extracted at §30.5)

But the **remaining ~34 component nodes from the 10-layer architecture** are not individually extracted. The comprehensive design's Ingestion, Retrieval, Intelligence, Reasoning layers likely contain logic that v3 doesn't capture.

---

## 4. WHAT SHOULD NOT BE CHANGED

These parts of v3 are excellent and should be preserved:

| Section | Lines | Why Keep |
|:---|:---|:---|
| §1.1 Pi Agent Loop | 111-252 | Best section. Complete pseudocode with all hooks annotated. |
| §4.1-4.2 Neo4j Agent Memory | 484-551 | Real file names, real pipeline, real schema. |
| §4.17 Headroom CCR | 553-613 | Complete pipeline with inflation guard, KV cache awareness. |
| §27.1 PageIndex | 616-677 | Full tree-build + retrieval algorithm. |
| §11.6 AutoResearch | 2464-2519 | Perfect adaptation: Locus delegates, never codes. |
| Memory Tri-Stack Integration | 680-730 | Clear unified pipeline diagram. |
| Data Flow Summary | 4021-4061 | 12-stage reactive + proactive + briefing flow. |
| Appendix C Formula Crosswalk | 4069-4089 | Single source of truth, all verified. |
| Appendix D Dependency Register | 4092-4101 | Corrected file names with v2 error note. |
| §25.1-25.16 Life OS Layer | 2044-2367 | All 16 features with correct formulas. |
| Universal Provider Pattern | 2712-2774 | 25 interfaces with defaults + lifecycle. |
| §1.2-1.6 Foundation Features | 254-482 | Good Pi feature coverage with adaptation notes. |

---

## 5. WHAT SHOULD BE CHANGED — Ranked by Impact

### 🔴 Critical — Must Fix

#### C1: Re-mine Pi/Hermes/OpenHuman features with `/graphify`

The ~60+ features sourced from Pi, Hermes, and OpenHuman need to be re-mined using `/graphify query` to get:
- **Actual file sets** (not inferred from directory scans)
- **Interaction maps** (which functions call which, across files)
- **Data flow chains** (how data moves through the system)

This applies to every section tagged `[✅ VERIFIED: direct file read (/graphify unavailable)]`.

**Priority targets** (most impactful features with weakest current coverage):
1. Hermes `background_review.py` ecosystem (§1.7) — partially done, needs `insights.py` and `memory_manager.py` deep logic
2. OpenHuman `sandbox/` (§13.3-13.5) — needs actual backend implementations
3. Hermes `gateway/` (§17.1-17.11) — needs Telegram adapter deep logic, PTB handler structure
4. OpenHuman `mcp_client/` + `mcp_server/` (§18.1-18.4) — needs protocol-level detail
5. OpenHuman `learning/` (§10.3) — needs stability detector, profile facets, PROFILE.md template

#### C2: Add the ~15 missing features from Atomic Selections

These features are in the source feature list but completely absent from v3:
- §4.5 Memory tree/cascade (OpenHuman bucket-seal cascade)
- §4.7 Memory sync
- §4.8 Memory queue
- §4.9 Memory diff
- §4.10 Holographic HRR
- §6.2 Context references (Hermes)
- §6.3 Coding-specific context (Hermes)
- §10.8 Self-evolving Architect Bot
- §10.9 Agent experience tracking
- §14.4 Dictation
- §17.6 Additional channels (IRC/Matrix/Teams/etc)
- §18.5 Obsidian MCP
- §27.7 Excalidraw MCP Skill
- §2.7 Intelligent routing — needs deep logic, not just table entry
- §2.8 Refusal detection — needs Aho-Corasick DFA logic

#### C3: Deepen harness delegation with user-understanding logic

Add to §3.7:
- How Locus assesses: task complexity (LOC estimate, file count, dependency depth)
- How Locus assesses: user deadline pressure (explicit deadline, DCS, operating mode)
- How Locus selects: harness-specific prompting strategy differences
- How Locus detects: which harnesses are installed (binary probe, PATH, config)
- The "understand the user" requirement from the prompt

### 🟡 Important — Should Fix

#### I1: Add "Files Involved" tables to all sections that lack them

Sections currently missing the interaction table:
- §13.1 Prompt Injection — add OpenHuman `prompt_injection/` file listing
- §13.2 File Safety — add Hermes `file_safety.py` + OpenHuman `file_state`, `cwd_jail`
- §13.4 Autonomy Tiers — add OpenHuman source files
- §13.5 Approval Gate — add OpenHuman + Hermes source files
- §29.1-29.8 all misc features — each should have its source files listed with interactions
- §9.4 ACP Protocol — add Hermes `copilot_acp_client.py` detailed file listing
- §9.9 Plugin LLM — add Hermes `plugin_llm.py` file listing

#### I2: Mine the `Comprehensive Locus System Design.html` deeper

The 128K HTML file contains a 10-layer architecture with ~40 component nodes. Currently only 6 are extracted. Cross-reference with existing v3 sections to identify:
- Which of the ~34 remaining components map to existing features (and enrich those sections)
- Which are genuinely new subsystems that need new sections

#### I3: Expand MCP server specification

Currently line 1874 says "Expose Locus tools via MCP" in one sentence. Need:
- Which tools get MCP endpoints (all 8 custom Locus tools? Selective?)
- MCP tool schema specification for each
- SSE streaming implementation for real-time tool results
- How Pi's `registerTool()` relates to MCP exposure
- Obsidian MCP tools (§18.5): vault_read, vault_write, vault_search, vault_tag, vault_stats

#### I4: Convert KEEP-PI table sections to atomic headers

The v3 structural audit already noted this. §2 (9 features), §3 (12 features), §15, §24 use tables instead of `## Feature` headers. Each needs a 3-4 line stub with: verdict, source path, off-state. Mechanical, zero analysis needed.

### 🟢 Minor — Nice to Have

#### N1: Add cross-reference links between related features

Example: §26.4 says "decomposed at §2.5" but doesn't link. §26.5 says "decomposed at §2.1-2.3" without links. Add markdown anchor links for navigability.

#### N2: Add a "Build Order" appendix

An AI implementer needs to know: what to build first. Currently v3 is organized by feature domain, not by dependency order. A topological sort would help:
1. Pi core (inherited, no build needed)
2. Python sidecar skeleton + /health endpoint
3. PostgreSQL schema + pgvector extension
4. Neo4j Agent Memory integration
5. State Engine + DCS
6. Context Forge (depends on memory + state)
7. Reactive pipeline (depends on all above)
8. Proactive Inner Loop (depends on reactive pipeline)
9. Channels (depends on reactive pipeline)
10. Harness delegation (depends on channels for approval gate)

#### N3: Add memory provider comparison matrix

The prompt emphasizes user choice (mem0, supermemory, honcho, mastra, cognee, custom). v3 lists them but doesn't compare capabilities:

| Provider | Graph | Entities | Weights | Self-hosted | Managed | Cost |
|:---|:---|:---|:---|:---|:---|:---|
| Neo4j Agent Memory | ✅ | ✅ (POLE+O) | ✅ (Hebbian) | ✅ | ✅ (NAMS) | Free/Hosted |
| mem0 | ❌ | Partial | ❌ | ✅ | ✅ | Freemium |
| supermemory | ❌ | ❌ | ❌ | ✅ | ✅ | Freemium |
| honcho | ❌ | ❌ | ❌ | ❌ | ✅ | Freemium |
| mastra | ❌ | Partial | ❌ | ✅ | ❌ | OSS |
| cognee | ✅ | ✅ | ❌ | ✅ | ❌ | OSS |

---

## 6. THE FUNDAMENTAL GAP: v3 IS A REFERENCE DOC, NOT A BUILD SPEC

> [!IMPORTANT]  
> The user's prompt asked for something very specific: **a document so precise that an AI model can "follow to copy and code from."**
> 
> v3 is currently a **reference document** — it tells you WHAT Locus does. It does not consistently tell you HOW to build each piece by showing the full distilled logic from the source codebases.
> 
> The 4 cloned dependencies (Neo4j, Headroom, PageIndex, AutoResearch) demonstrate what v3 SHOULD look like everywhere: real files, real logic, real algorithms, real adaptation points. The remaining ~60+ features from Pi/Hermes/OpenHuman are at 40-60% of that depth.

### What "perfect" looks like (the standard set by §4.1-4.2):

```
## Feature §X.Y: Feature Name

### Source
- **Codebase**: exact repo + path
- **Verification**: [✅ VERIFIED: /graphify query "feature name"]

### Files Involved (real, not guessed)
| File | Lines | Purpose | Interacts With |
|------|-------|---------|---------------|
| actual/file.py | 450 | What it does | other_file.py, third_file.py |

### Logic Extracted (from source, not invented)
```
COMPLETE pseudocode showing:
- The entry point function
- All branching logic
- Error handling strategy  
- How data flows between the files listed above
- Any state it reads/writes
```

### Adaptation to Locus Architecture
- **Component**: exact Locus file path
- **Provider Interface**: which interface it implements
- **Integration Point**: which Pi hook / pipeline stage
- **Repo vs .locus**: where code vs config goes
- **Swappable / off state**: config key + what user loses
- **Crawler feed**: (if proactive) what data source feeds it
```

### The gap: ~60 features are at this level instead:

```
### Logic extracted
```
5-10 lines of generic pseudocode
```

### Locus adaptation
- **Component**: `locus/core/feature.ts`
- Off state: `locus.feature.enabled`. Off → feature disabled.
```

---

## 7. SCORING SUMMARY

| Criterion | Score | Weight | Weighted |
|:---|:---|:---|:---|
| Structure & atomicity (86 sections, headers, tags) | 9/10 | 10% | 0.9 |
| Four cloned deps (Neo4j, Headroom, PageIndex, AutoResearch) | 9/10 | 15% | 1.35 |
| Pi/Hermes/OpenHuman logic stripping depth | 4/10 | 25% | 1.0 |
| `/graphify` usage (source verification accuracy) | 2/10 | 10% | 0.2 |
| Feature coverage (vs Atomic Selections list) | 6/10 | 15% | 0.9 |
| Harness delegation specificity | 6/10 | 5% | 0.3 |
| MCP support depth | 5/10 | 5% | 0.25 |
| HTML design docs mining | 5/10 | 5% | 0.25 |
| File interaction maps completeness | 5/10 | 5% | 0.25 |
| Implementability (can an AI build from this?) | 6/10 | 5% | 0.3 |
| **TOTAL** | | **100%** | **5.7/10 → ~72%** |

> [!NOTE]  
> The prior audit scored v3 at ~94% using a 9-point rubric focused on **document quality** (headers, annotations, code artifacts, etc.). That rubric was well-designed for its purpose but didn't measure **content depth** against the user's coding philosophy. This audit measures both.

---

## 8. RECOMMENDED ACTION PLAN

### Phase 1: Re-mine with /graphify (Highest Impact)
For each feature tagged `[✅ VERIFIED: direct file read (/graphify unavailable)]`, run:
```
graphify query "What files implement [feature name] and how do they interact?"
graphify path "[source_file]" "[interacting_file]"
```
Then update the section with real file sets, real interaction maps, and deep logic from the actual source.

### Phase 2: Add Missing Features
Add the ~15 features from Atomic Selections that are absent from v3, following the quality standard of §4.1-4.2.

### Phase 3: Deepen Shallow Sections
Target the ~20 sections that currently have <10 lines of pseudocode and bring them to the depth standard demonstrated by the cloned dependency sections.

### Phase 4: Add Build Order + Provider Comparison
Help the AI implementer know where to start and what choices to make.

---

> **Bottom line**: v3 is a **good skeleton with excellent spots** (the 4 cloned deps, §1.1, §25, the data flow summary). But for ~60% of its features, it provides surface-level pseudocode that an AI implementer would struggle to build from without going back to the source codebases — which defeats the entire purpose of the document. The path to "perfect" is: re-mine with /graphify, add missing features, and deepen every section to the quality bar set by §4.1-4.2.
