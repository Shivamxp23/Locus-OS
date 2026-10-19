# Implementation Plan: LOCUS_FEATURE_LOGIC_DECOMPOSITION_v5

## Goal

Consolidate v3/v4 (which are identical) into a finalized v5 that reaches **10/10 adherence** to the user's original prompt requirements. This plan identifies every gap and proposes the fix.

---

## Current State

- **v3 and v4 are byte-identical** (252,830 bytes). No iteration occurred.
- **Current score: 7.5/10** — excellent core but with systematic gaps in batch-covered features, HTML doc extraction, and inter-file congruence.
- **v5 target: 10/10** — every §1-§30 feature gets the full treatment.

---

## Gap Analysis: What v5 Must Fix

### Gap Category 1: Batch-Covered Features Need Full Decomposition

These features are covered in v3/v4 only as summary tables or short paragraphs. They need the FULL treatment: `### Source → ### Files Involved → ### Stripped Logic (Pseudocode) → ### Adaptation to Locus Architecture`.

| Feature | Current State in v3/v4 | What v5 Needs |
|---------|----------------------|---------------|
| **§1.9 Rate Limit Tracking** | One-line entry, no pseudocode | Full decomposition of Hermes `rate_limit_tracker.py` |
| **§1.10 Usage/Cost Tracking** | One-line entry | Full decomposition of Hermes `usage_pricing.py` + `credits_tracker.py` |
| **§1.11 Title Generation** | One-line entry | Full decomposition of Hermes `title_generator.py` |
| **§6.2 Context References** | Missing entirely | Full decomposition of Hermes `context_references.py` |
| **§6.3 Coding Context** | Missing entirely | Full decomposition of Hermes `coding_context.py` |
| **§9.4 ACP Protocol** | Missing from v3/v4 | Full decomposition of Hermes ACP adapter |
| **§9.9 Plugin LLM** | Missing from v3/v4 | Full decomposition of Hermes `plugin_llm.py` |
| **§13.6 Project Trust** | One-line table entry | Already KEEP-PI, but needs explicit Pi file reference |
| **§13.7 Shell Blocklist** | One-line table entry | Needs OpenHuman policy engine pseudocode |
| **§13.8-13.10 Redaction/Scrubbing/Sanitization** | One-line table entries each | Each needs full Hermes source decomposition |
| **§17.10 Graceful Restart** | Not decomposed | Hermes `restart.py` logic stripping |
| **§29.4 Notifications** | Has pseudocode but thin | Needs OpenHuman `notifications` module full decomposition |
| **§29.5 Connectivity Check** | Has pseudocode but thin | Needs OpenHuman `connectivity` module full decomposition |
| **§29.6 Code Graph** | Has pseudocode but thin | Needs OpenHuman `codegraph` module full decomposition |
| **§29.7 Subconscious** | Has pseudocode but thin | Needs OpenHuman `subconscious` full decomposition |
| **§29.8 Workflows** | Has pseudocode but thin | Needs OpenHuman `workflows` full decomposition |

> [!IMPORTANT]
> **16 features** currently lack the full `Files Involved → Stripped Logic → Adaptation` treatment that the user's prompt demands for EVERY feature.

---

### Gap Category 2: HTML Design Doc Under-Extraction

v3/v4 extracted step-by-step logic from `locus_microsystems.html` for 5 subsystems. But that 155K HTML file contains **18 subsystems**. The following need deep extraction:

| Subsystem from HTML | Extracted in v3/v4? | Action for v5 |
|---------------------|---------------------|---------------|
| Query Router (6-step) | ✅ Yes | Keep |
| State Engine (5-step) | ✅ Yes | Keep |
| Context Forge (12-step) | ✅ Yes | Keep |
| Collector + Chunker | ✅ Yes (§30.1) | Keep |
| Cause Chain Engine | ✅ Yes (§30.2) | Keep |
| **Master Conductor** | ❌ No | Extract the 11-step conductor flow |
| **Content Engine** | ❌ Partial (§30.4 is thin) | Full step-by-step extraction |
| **Dashboard / TUI** | ❌ No | Extract the dashboard layout spec |
| **Redis Integration** | ❌ No | Extract the Redis caching pattern (CURRENT_STATE TTL) |
| **Obsidian/LightRAG** | ❌ No | Extract the Obsidian bridge steps |

Also: `Comprehensive Locus System Design.html` (128K) and `locus_pyramid.html` (31K) have content that was referenced but not deeply stripped.

> [!WARNING]
> The user explicitly listed these HTML files as source documents. v5 must demonstrate that their content was read and incorporated.

---

### Gap Category 3: Inter-File Congruence (R4) Gaps

The user's prompt specifically asks: *"how they work in congruence with the other files"*. v3/v4 does this well for deep-mined features but poorly for:

| Area | Gap |
|------|-----|
| Hermes features (§1.9-1.11, §29.1-29.2) | Lists source file but doesn't explain how it connects to Hermes' `agent/` runtime, `gateway/`, or `memory_manager.py` |
| OpenHuman features (§29.4-29.8) | Lists module names but doesn't show which other OpenHuman modules they interact with |
| Locus sidecar endpoints | v3/v4 lists endpoints but doesn't trace the full call chain from TS → HTTP → sidecar → return |

---

### Gap Category 4: Part II Mapping Table Correction

The Atomic Selections bible (Part II) has **INCORRECT file names** for the 4 cloned deps:
- Neo4j: `client.py, long_term.py, short_term.py, reasoning.py` → WRONG (v3 Appendix D already corrects this)
- Headroom: `compress.py, proxy.py, mcp.py, ccr.py` → WRONG
- PageIndex: `tree_index.py, reasoning_rag.py` → WRONG

v3/v4 corrected these in the body sections (§4.1, §4.17, §27.1) and Appendix D, but the Part II mapping table from the Atomic Selections was never corrected inline. **v5 must include a corrected Part II table.**

---

### Gap Category 5: Structural Improvements

| Issue | Fix for v5 |
|-------|-----------|
| No master feature checklist | Add a feature coverage matrix at the top: every §X.Y feature with ✅/❌ decomposed status |
| Formula crosswalk is at the bottom | Move it up or link it prominently — it's critical for implementers |
| §26 features (Proactive Reasoning) are brief | §26.1-26.7 each need full pseudocode. Currently they have short descriptions pointing to other sections |
| §25 features (Life OS) have formulas but lack algorithm pseudocode for scheduling | §25.12 (Six-Step Scheduling Algorithm) needs the full algorithm, not just a description |
| Duplicate §2.4/§2.5 sections | Context Forge adaptation block is duplicated at lines 1392-1401 |
| No HRR (§4.10) decomposition | Holographic Reduced Representation is listed in Atomic Selections but has no pseudocode in v3/v4 |

---

### Gap Category 6: Missing/Thin Features

| Feature from Atomic Selections | Status in v3/v4 |
|-------------------------------|----------------|
| **§4.10 Holographic HRR** | ❌ Missing entirely |
| **§4.12 STDP Reinforcement** | Mentioned in passing, no pseudocode |
| **§4.13 Spaced Repetition** | Mentioned in §30.5, but lacks the Inner Loop integration algorithm |
| **§4.14 Project-specific memory decay** | One line, no pseudocode |
| **§19.3 Daily AI Chat Archiver** | ❌ Missing |
| **§20.1-20.3 Computer Use** | Present but §20.3 (VNC) has no pseudocode |
| **§27.5 Rough Note Parser** | ❌ Missing |
| **§27.6 Link Dump Logger** | ❌ Missing |
| **§27.7 Excalidraw MCP Skill** | ❌ Missing |

---

## Proposed Changes

### Phase 1: Fix Batch-Covered Features (16 features)

For each of the 16 batch-covered features listed in Gap Category 1:
1. Read the source file(s) from the relevant codebase (Hermes/OpenHuman/Pi)
2. Strip the logic into pseudocode following the established format
3. Write the full `### Source → ### Files Involved → ### Stripped Logic → ### Adaptation` section

#### [MODIFY] [LOCUS_FEATURE_LOGIC_DECOMPOSITION_v5.md](file:///c:/Users/soni8/Desktop/everything/University%202.0/Project(s)/5_Locus/locus-os/.keysndocs/Documentation/Implementation%20Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION_v5.md)
- Expand all 16 batch-covered features to full decomposition sections
- Each feature gets: Source verification, Files Involved table, Stripped Logic pseudocode block, Locus Adaptation block

---

### Phase 2: HTML Doc Deep Extraction (5 missing subsystems)

Read and extract step-by-step logic from `locus_microsystems.html` for:
- Master Conductor (11-step flow)
- Content Engine (full algorithm)
- Dashboard/TUI spec
- Redis integration pattern
- Obsidian/LightRAG bridge

Also scan `Comprehensive Locus System Design.html` and `locus_pyramid.html` for any unique logic not covered.

---

### Phase 3: Fill Missing Features (9 features)

Write full decomposition for:
- §4.10 (HRR), §4.12 (STDP), §4.13 (Spaced Repetition algorithm), §4.14 (Project decay)
- §19.3 (Daily AI Chat Archiver)
- §20.3 (VNC — at least a stub with "low priority" note)
- §27.5, §27.6, §27.7 (Rough Note Parser, Link Dump, Excalidraw)

---

### Phase 4: Structural Fixes

- Add master feature coverage matrix at document top
- Fix the duplicate §2.4/§2.5 Context Forge adaptation block
- Correct Part II mapping table with real file names
- Expand §25.12 with full 6-step scheduling algorithm pseudocode
- Expand §26.1-26.7 with full pseudocode for each proactive reasoning subsystem

---

### Phase 5: Inter-File Congruence Pass

For every feature, ensure the "Files Involved" table includes an "Interacts With" column showing cross-file dependencies.

---

## Open Questions

> [!IMPORTANT]
> **Q1**: Should v5 be a NEW file (`_v5.md`) or should it OVERWRITE v3/v4 (since they're identical)?

> [!IMPORTANT]  
> **Q2**: The HTML docs (`locus_microsystems.html`, `Comprehensive Locus System Design.html`) are 155K and 128K respectively. Do you want me to deep-extract ALL subsystems from them, or only the ones that map to features in the Atomic Selections?

> [!IMPORTANT]
> **Q3**: For the "batch-covered" features (§29.4-29.8 etc.) — should I actually read the OpenHuman source files to strip real logic, or is it acceptable to write design-level pseudocode based on the module descriptions (since some OpenHuman files may not be accessible)?

> [!IMPORTANT]
> **Q4**: v3/v4 is already 5,400 lines / 253KB. The v5 additions (16 expanded features + 9 missing features + HTML extractions) will likely push it to ~7,000-8,000 lines. Is that acceptable, or should we split into multiple files (e.g., `v5_core.md` + `v5_peripherals.md`)?

---

## Verification Plan

### Automated Checks
- Feature count audit: grep all `## Feature §` headings and verify every §X.Y from Atomic Selections has a matching section
- Pseudocode block count: every feature section must contain at least one ````  ``` ```` pseudocode block
- Adaptation block count: every feature section must contain a `### Locus adaptation` or `### Adaptation to Locus Architecture` block

### Manual Verification
- Side-by-side comparison of v5's feature list against the Atomic Selections §1-§29 table
- Formula crosswalk verification against `LOCUS_SYSTEM_v1.md`
- Spot-check 5 random pseudocode blocks for accuracy against source code
