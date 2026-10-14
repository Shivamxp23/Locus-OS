# Atomic Selections v2 — Locus as a Pi Package

## Goal

Produce a new **Atomic Selections from Antigravity.md** in the July 16th folder that reframes every feature from the COMBINED_ATOMIC_FEATURES matrix (29 sections, ~130 features) under the new paradigm: **Locus is a Pi Package**, not a standalone Python framework.

## Architectural Paradigm Shift

The old document assumed Locus was a standalone Python harness. The new document assumes:

> **Pi Agent is the runtime.** Locus is a **Pi Package** (`@locus/pi-package`) that bundles extensions, skills, themes, and prompt templates to transform Pi into a personal Life OS agent.

### What Pi Gives You For Free (DON'T REINVENT)

- Agent loop, tool-calling, streaming, retry/recovery
- 30+ LLM providers (Anthropic, OpenAI, Google, etc.)
- 8 built-in tools (read, write, edit, bash, grep, find, web_search, fetch)
- Session management (JSONL tree, fork, resume, compress)
- Full TUI with themes, keybindings, editor
- Extension API (`pi.registerTool()`, `pi.on()`, `pi.registerCommand()`, etc.)
- Skills system (cross-harness compatible SKILL.md)
- Package system (npm/git install, bundle extensions+skills+themes)
- Compaction engine, context management
- Security (project trust, file safety)
- CLI flags (39), subcommands, self-update
- Custom providers, custom models, OAuth flows

### What Locus Adds as a Pi Package

- **Extensions** (TypeScript `.ts` files via Pi Extension API):
  - Memory Tri-Stack (Neo4j Agent Memory + PageIndex + Headroom)
  - Telegram gateway bridge
  - Life OS behavioral metrics engine
  - Brain Engine / Inner Loop (proactive reasoning)
  - Vault Intelligence (Obsidian integration)
  - Voice pipeline (STT/TTS)
  - Context Forge (multi-source context assembler)
  - Scheduling / Cron runner
  
- **Skills** (SKILL.md files):
  - `/locus-checkin` — structured daily check-ins
  - `/locus-research` — autoresearch integration
  - `/locus-vault` — vault operations
  - `/locus-life` — life OS dashboard
  
- **Themes** (JSON):
  - Locus dark/light branded themes
  
- **Prompt Templates**:
  - Locus system prompt (SOUL.md equivalent)

> [!IMPORTANT]  
> **Key Question for User:** The original Locus was Python-based with a Telegram-native interface (no TUI). Pi is Node.js/TypeScript with a TUI-first design. Should Locus as a Pi Package:
> 1. **Keep the TUI** — Use Pi's TUI but add a Telegram bridge extension?
> 2. **Run headless via SDK** — Use Pi's SDK/RPC mode to power a separate Telegram bot that calls Pi programmatically?
> 3. **Both** — TUI for desktop coding, Telegram for mobile Life OS, unified through Pi's session system?

> [!IMPORTANT]
> **Key Question:** Pi is TypeScript/Node.js. The original Locus and many Locus-unique features (Life OS formulas, Brain Engine, Neo4j integration) were designed for Python. Should Locus extensions:
> 1. **Be pure TypeScript** — Rewrite all logic in TS for the Pi extension API?
> 2. **Use Pi's `bash` tool + Python sidecar** — Extensions call Python scripts via `pi.exec()`?
> 3. **Hybrid** — Extension shell is TS, but heavy logic (ML, Neo4j queries, etc.) lives in Python microservices called via HTTP?

## Proposed Changes

### [NEW] Atomic Selections from Antigravity.md

**Path:** `locus-os\.keysndocs\Documentation\Implementation Reports\July 16th\Atomic Selections from Antigravity.md`

The document will follow the same structure as the original (Verdict → Source → Key Files → Congruence → Atomic Logic → Adaptation) but every verdict now classifies features into one of these **Pi Package categories**:

| Category | Meaning |
|----------|---------|
| **🟢 PI-NATIVE** | Pi already provides this. Don't build it. |
| **🔵 COMMUNITY** | A community Pi extension/package already exists or can be used. |
| **🟡 LOCUS-EXT** | Build as a Locus Pi extension (TypeScript). |
| **🟠 LOCUS-SKILL** | Build as a Locus skill (SKILL.md). |
| **🔴 LOCUS-SIDECAR** | Build as a Python sidecar service called by Locus extensions. |
| **⚪ SKIP** | Not needed or deliberately excluded. |

### Document Structure

```
Part 0: The Pi Package Paradigm
  - What a Pi Package is (extensions + skills + themes + prompts)
  - The Locus Package architecture diagram
  - What you get for free from Pi

Part I: Feature-by-Feature Selections (§1-§29)
  - Each of the 29 sections from COMBINED_ATOMIC_FEATURES.md
  - For each feature: Category | Source | Pi Mapping | Adaptation Logic

Part II: The Locus Extension Manifest
  - Every extension file in the package
  - Event hooks, custom tools, custom commands

Part III: The Locus Skills Bundle
  - Every skill in the package

Part IV: Locus-Unique Domains (Life OS, Brain Engine, Vault)
  - These have no Pi equivalent — full Locus-original implementations

Part V: Implementation Roadmap (as Pi Package)
  - Phase 1: Core package scaffold + theme + system prompt
  - Phase 2: Memory extensions + Telegram bridge
  - Phase 3: Life OS + Brain Engine sidecar
  - Phase 4: Vault Intelligence + Voice pipeline
```

## Verification Plan

### Manual Verification
- Confirm every feature from the original 29-section matrix is covered
- Confirm no Pi-native feature is being rebuilt
- Confirm community extensions are cited where available
- User review of the document for completeness and accuracy
