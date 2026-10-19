# Revise Atomic Selections — Locus as Pi Agent Augmentation

## The Paradigm Shift (Package → Augmentation)

The previous version treated Locus as a **Pi Package** sitting _on top_ of Pi. The user has clarified this is wrong. The correct architecture is:

> **Locus AUGMENTS Pi Agent's codebase.** It is a **fork/extension of the Pi Agent repository** that adds Locus-unique functionality while inheriting 100% of Pi's infrastructure. Users run `locus` as a separate CLI binary alongside `pi`.

### Key Differences from Previous Version

| Aspect | Old (Package) | New (Augmentation) |
|--------|--------------|-------------------|
| Relationship to Pi | Installable package on top | Fork/augmentation of Pi's codebase |
| CLI | `pi install @locus/package` | `locus` is its own CLI binary, mirrors all `pi` commands |
| Install scope | `pi install X` | `pi install X` (global), `locus install X` (Locus-scoped) |
| Architecture | Extension API only | Direct codebase augmentation + Extension API |
| Language | TypeScript extensions + Python sidecar | TypeScript (core, inherits Pi) + Python sidecar |
| Modularity | Extension-level | **EVERYTHING** is modular — every component swappable, toggleable |

### Dual CLI Architecture

```
$ pi install some-extension      # Installs globally for both pi and locus
$ locus install some-extension   # Installs for Locus scope only
$ pi help                        # Pi's help
$ locus help                     # Locus's help (mirrors pi commands + Locus-specific)
$ locus doctor                   # Locus diagnostics (sidecar health, Neo4j, Telegram, etc.)
$ locus config                   # Locus-specific config
```

### Maximum Modularity Philosophy

**EVERY component must be:**
1. **Swappable** — Users can replace any subsystem (e.g., swap Neo4j for mem0 for memory)
2. **Toggleable** — Users can turn off any feature via config
3. **Hookable** — Users can inject their own custom system at any integration point
4. **Independently testable** — Each module works in isolation

### Multi-Provider Options (Memory & Brain as Examples)

The document must offer MAXIMUM choice. For every major subsystem, list ALL available providers:

**Memory Providers (user picks one or more):**
- Neo4j Agent Memory (default)
- mem0
- Supermemory
- Honcho
- Mastra
- Cognee
- Custom (user-provided adapter)

**Brain/Reasoning Systems:**
- Locus Brain Engine (default — Inner Loop, Context Forge, Pattern Engine)
- OpenHuman's post-turn hooks (Archivist, Reflection, ToolTracker, UserProfile)
- Hermes' curator system (background_review + memory nudge)
- Custom (user-provided adapter)

## What the Revised Document Must Contain

### Structure

```
Part 0: The Augmentation Paradigm
  - What "augmenting Pi" means technically (forked codebase, dual CLI)
  - The Locus modularity contract (every component = interface + providers)
  - Available codebases: Pi (c:\...\pi), Hermes (c:\...\hermes-agent), OpenHuman (c:\...\openhuman)
  - Coding philosophy (laziness-first, steal logic, /understand-anything)

Part I: AUGMENTED Feature Matrix (§1-§29)
  - Same 29 sections as COMBINED_ATOMIC_FEATURES.md
  - For each feature: KEEP/SKIP/AUGMENT verdict + source codebase + modularity options
  - Emphasis on giving users MAXIMUM options for memory/brain/learning systems
  - ALL implementations from ALL codebases listed as swappable options

Part II: Feature → Source Codebase Mapping
  - For each selected feature: which codebase to steal from
  - Which files are linked to that feature
  - Detailed purpose of each file
  - How files work in congruence

Part III: Atomic Logic Stripping
  - For each feature: pseudocode/algorithm extracted from source files
  - How the logic adapts to Locus' architecture
  - Integration points with other Locus modules

Part IV: Modularity Contract Specifications
  - Interface definitions for every swappable component
  - Provider registry pattern
  - Config schema for enabling/disabling/swapping
```

> [!IMPORTANT]
> **User Instruction**: The user will provide a specific feature list in a follow-up message, selected from `full_feature_matrix.md` plus additional features. This document should be structured to RECEIVE that list and have the framework ready.

> [!IMPORTANT]
> **Coding Philosophy Compliance**: 
> - No direct code in the document (only pseudocode, algorithms, logic)
> - Never directly reference codebase files — use `/understand-anything` to query details
> - Laziness-first: use pre-built infrastructure where possible
> - Steal logic & implementation strategy from existing codebases

## Proposed Changes

### [MODIFY] Atomic Selections from Antigravity.md

**Path:** `locus-os\.keysndocs\Documentation\Implementation Reports\July 16th\Atomic Selections from Antigravity.md`

Complete rewrite to reflect the augmentation paradigm. The document becomes a living blueprint that:

1. **Augments** COMBINED_ATOMIC_FEATURES.md with selection verdicts
2. **Maps** every feature to its source codebase and files
3. **Strips** atomic logic into pseudocode
4. **Specifies** modularity contracts for every swappable component
5. **Provides** maximum customization options (memory, brain, channels, etc.)

## Verification Plan

### Manual Verification
- All 29 sections from COMBINED_ATOMIC_FEATURES covered
- Every feature has a KEEP/SKIP/AUGMENT verdict
- Every KEEP/AUGMENT feature has a source codebase + files mapping
- Modularity contracts specify interfaces for all swappable components
- No direct code — only pseudocode, algorithms, and logic descriptions
- Dual CLI architecture clearly defined
- Maximum provider options listed for memory, brain, learning systems

## Open Questions

> [!IMPORTANT]
> **Should I proceed NOW with rewriting the document using the general framework, or should I WAIT for your specific feature list?**
> 
> Your message says "I will give you a long list of features that I will select..." which implies I should wait. But you also say "you still need to edit... Atomic Selections from Antigravity.md" which implies I should act now.
> 
> My recommendation: I rewrite the document NOW with the new paradigm framework (Part 0 + the augmented feature matrix for all 29 sections with KEEP/SKIP/AUGMENT verdicts), and then when you provide your specific feature list, I populate Parts II-III with the detailed file mappings and logic stripping using `/understand-anything`.
