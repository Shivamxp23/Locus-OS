# v3 → v4 Decomposition Upgrade Plan

## Goal

Upgrade `LOCUS_FEATURE_LOGIC_DECOMPOSITION_v3.md` to v4 by fixing the gaps identified in the audit, bringing all sections to the depth standard set by the 4 cloned dependencies (§4.1-4.2, §4.17, §27.1, §11.6).

## Current State

- **v3**: 4,104 lines, ~184K bytes  
- **Audit score**: ~72% (vs target ~95%)
- **Graph available**: `5_Locus/graphify-out/graph.json` (278MB, covers all codebases)
- **Source codebases confirmed**: Pi, Hermes, OpenHuman all accessible under `5_Locus/`

## Scope Discovery: OpenHuman Has 100+ Modules

The OpenHuman codebase has **108 dedicated Rust modules** mapped directly to features in Atomic Selections. Many of the "missing features" already have complete implementations waiting to be stripped:

- `memory_tree/`, `memory_sync/`, `memory_queue/`, `memory_diff/` → Missing §4.5, §4.7-4.9
- `prompt_injection/` → Shallow §13.8
- `mcp_server/`, `mcp_registry/` → Shallow §18.2-18.3
- `channels/` → Missing channel detail for §17
- `workflows/`, `subconscious/`, `scheduler_gate/` → Shallow §29.7-29.8
- `screen_intelligence/` → Shallow §16.1-16.2
- `learning/` → Shallow §10.3

> [!IMPORTANT]
> **Scale concern**: Fully stripping 100+ OpenHuman modules, plus the Hermes features, would produce a document of ~8,000-12,000 lines. This is a **multi-session effort**. 
> 
> I propose a **3-batch approach**: Batch 1 = Critical (15 highest-impact features), Batch 2 = Important (20 features), Batch 3 = Nice-to-have (25 features + structural fixes).

## Open Questions

> [!WARNING]
> **Q1: Document size target?** v3 is already 4,104 lines (~184K). Full v4 could reach ~10,000 lines. Is that acceptable, or should I use a modular approach (main doc + per-subsystem deep-dive files)?

> [!IMPORTANT]
> **Q2: Which batch to execute now?** Given context window limits, I can execute Batch 1 (Critical: ~15 highest-impact features) in this session. Should I proceed with Batch 1 only, or do you want the full plan first?

> [!NOTE]
> **Q3: KEEP-PI table→header conversion**: The prior audit noted §2, §3, §15, §24 use tables instead of `## Feature` headers. This is a mechanical fix (~100 lines of edits). Should I include this in Batch 1 or defer?

---

## Proposed Changes

### Batch 1 — Critical Deepenings (This Session)

These are the features that most impact an implementer's ability to build Locus:

---

#### 1. [MODIFY] §13.3-13.5: Security/Sandbox System — DEEPEN

**Current**: 6 lines listing 5 backend kinds + generic `execute_in_sandbox`  
**Target**: Full `Sandbox` trait + 4 backend implementations with real logic

**Source files** (now read):
- `openhuman/src/openhuman/security/traits.rs` (80 lines) — Sandbox trait
- `openhuman/src/openhuman/security/bubblewrap.rs` (184 lines) — Bubblewrap impl
- `openhuman/src/openhuman/security/firejail.rs` (196 lines) — Firejail impl  
- `openhuman/src/openhuman/security/landlock.rs` (247 lines) — Landlock impl

**Logic to extract**: Trait interface, per-backend wrap_command args, availability probing, workspace isolation strategy.

---

#### 2. [NEW] §4.5: Memory Tree/Cascade — ADD MISSING

**Source**: `openhuman/src/openhuman/memory_tree/`
**Why critical**: Part of the memory subsystem — Locus's most important layer.

---

#### 3. [NEW] §4.7-4.9: Memory Sync, Queue, Diff — ADD MISSING

**Source**: `openhuman/src/openhuman/memory_sync/`, `memory_queue/`, `memory_diff/`
**Why critical**: These are the operational mechanics of how memory stays consistent.

---

#### 4. [MODIFY] §18.1-18.4: MCP System — DEEPEN

**Current**: Shallow coverage of MCP client, one-sentence MCP server  
**Target**: Full MCP stdio client protocol (JSON-RPC over stdin/stdout), tool listing, tool calling, server implementation

**Source files** (now read):
- `openhuman/src/openhuman/mcp_client/stdio.rs` (241 lines) — Complete stdio client
- `openhuman/src/openhuman/mcp_server/` — Server implementation
- `openhuman/src/openhuman/mcp_registry/` — Dynamic registry

---

#### 5. [NEW] §18.5: Obsidian MCP — ADD MISSING

**Source**: Locus-original design  
**Why critical**: Bridges external AI editors to Locus's vault operations.

---

#### 6. [MODIFY] §13.8: Prompt Injection Protection — DEEPEN

**Source**: `openhuman/src/openhuman/prompt_injection/`
**Current**: 6 lines  
**Target**: Full regex + semantic detection pipeline

---

#### 7. [MODIFY] §3.7 + Harness Delegation — DEEPEN

**Current**: Generic delegation flow without user-understanding logic  
**Target**: Add task complexity assessment, deadline awareness, harness detection, harness-specific prompting differences

---

#### 8. [MODIFY] §17.1: Telegram Gateway — DEEPEN  

**Source**: `hermes-agent/gateway/platforms/telegram.py`, `platform_registry.py`
**Current**: PlatformEntry dataclass + register pattern  
**Target**: Full PTB handler structure, inline keyboard handling, voice message pipeline

---

#### 9. [NEW] §2.7-2.8: Intelligent Routing + Refusal Detection — ADD LOGIC

**Source**: `openhuman/src/openhuman/routing/`
**Current**: Listed in table with no logic stripped

---

#### 10. [NEW] §10.8-10.9: Self-Evolving Architect + Agent Experience — ADD MISSING

**Source**: `openhuman/src/openhuman/agent_experience/`

---

### Batch 2 — Important Deepenings (Next Session)

11. §29.1 Error Classifier — deepen with Hermes retry strategies  
12. §29.7 Subconscious — deepen with OpenHuman `subconscious/`  
13. §29.8 Workflows — deepen with OpenHuman `workflows/`  
14. §10.3 User Profile Building — deepen stability detector, facets  
15. §16.1-16.2 Browser/Screen Intelligence — deepen  
16. §12.1 Scheduling — deepen with OpenHuman `scheduler_gate/`, `cron/`  
17. §14.4 Dictation — add missing  
18. §17.6 Additional Channels — add missing  
19. §6.2-6.3 Context References — add missing  
20. §27.7 Excalidraw MCP — add missing  

### Batch 3 — Structural & Polish (Following Session)

21-25. KEEP-PI table→header conversion for §2, §3, §15, §24  
26. Cross-reference links between related features  
27. Build Order appendix  
28. Memory provider comparison matrix  
29. Re-tag all sections with proper `/graphify` verification  
30. Mine `Comprehensive Locus System Design.html` deeper  

---

## Verification Plan

### Automated
- Word count / line count comparison (v3 vs v4)
- Grep for remaining `[✅ VERIFIED: direct file read (/graphify unavailable)]` tags (should decrease)
- Grep for `## Feature` header count (should increase from 86)

### Manual
- Re-run 9-point audit rubric on v4
- Re-run content depth audit on v4 (target: ≥90%)
- Spot-check 5 deepened sections against source files for accuracy
