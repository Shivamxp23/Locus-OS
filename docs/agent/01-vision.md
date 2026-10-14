# 01 - What Locus is (understand the product; this file contains no code rules)

## In one paragraph
Locus is a personal intelligence FRAMEWORK. It comes pre-installed with many features, and any part of it can be added,
replaced, or switched off, because everything is modular. It is headless first: the backend runs 24/7 on an always-on
machine (normally a VM) and the owner talks to it through Telegram (the owner's main channel today), Discord, WhatsApp, or a
CLI/TUI on their own computer. It also acts on its own: cron jobs the owner defines make it research, write notes, and message
the owner without being prompted. It is built ON TOP of the Pi coding agent and never replaces Pi's agent loop.

## The seven principles (the owner's own words, made checkable)
| # | Principle | What it means in the repo | Spec status on 2026-10-05 |
|---|---|---|---|
| 1 | Framework: ANYTHING can be turned off or swapped | provider interface + `enabled` switch per feature (03-modularity.md) | Covered by convention: each spec feature has a "Swappable / off state" line |
| 2 | Headless first, backend on a VM, many front doors | 04-runtime-and-channels.md | Covered: spec sections 23, 28, 17 |
| 3 | Acts without being prompted (cron, research) | owner-defined schedules run Pi turns unattended | Covered: spec sections 12.x, 26.1 |
| 4 | Meta-harness: Locus orchestrates other harnesses (Pi, Claude Code, Antigravity, Hermes...) | `HarnessProvider` registry; Locus delegates, it does not copy their loops | PARTIAL: only coding delegation (3.7 + 11.5); the principle is never stated (errata D-5) |
| 5 | Every task, at every scale, gets its own multi-factor priority score | one score per task, scale-aware | CONFLICT: two incompatible TWS formulas (25.4, 25.12); "scale" is never defined (errata D-1, D-3) |
| 6 | Auditability is a headline feature: all chats and actions are recorded and backed up to the Obsidian vault automatically | trajectory recording + chat archiver + LiveSync | PARTIAL: nightly archiver of external chats (19.3), session recording (19.2), scattered audit tables; the word never appears and there is no single audit trail (errata D-4) |
| 7 | Neo4j Agent Memory is the memory substrate | `neo4j-labs/agent-memory` behind `MemoryProvider` | FULL: spec sections 4.1-4.2, 4.18 |

"Spec status" is what `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` actually says (checked by text search), not what any earlier
AI report claimed. Never build on a PARTIAL or CONFLICT row until the matching decision in 09-spec-errata.md is DECIDED.

## What Locus is NOT (each of these has already gone wrong once)
- Not a CLI-only tool. The CLI/TUI is one front door of several.
- Not a bespoke agent loop. Before 2026-10-02 the repo had drifted into its own loop instead of building on Pi. Pi's loop,
  tools, providers, sessions, and TUI are inherited; Locus adds extension tools/hooks and a Python sidecar.
- Not Git/Syncthing vault sync. The vault syncs through Obsidian Self-hosted LiveSync + CouchDB (spec 27.2) only.
- Not a fork. `packages/` stays byte-identical to upstream Pi.

## Words used in this repo
- **Pi**: the upstream coding agent in `packages/`.  **Extension**: Locus TypeScript loaded into Pi (`locus-extension/`).
- **Sidecar**: Locus Python daemon (`sidecar/`, FastAPI :8420).  **Harness**: any agent runner (Pi, Claude Code, Antigravity).
- **Vault**: the Obsidian notes folder (`vault/`, 8 fixed folders).  **`.locus`**: the runtime home `~/.locus` (config, secrets, DBs).
- **Dev vs runtime**: dev = coding agents changing this repo (rules in AGENTS.md); runtime = Locus serving the owner.
- **Verified level**: L0-L5 computed from evidence (07-tracker-evidence.md). "Done" is not a word an agent may use.

## Where truth lives
| Question | Authority |
|---|---|
| What must feature X do? | `LOCUS_FEATURE_LOGIC_DECOMPOSITION.md` via `tools/tracker/show.py F-xxxx --spec` |
| Spec contradicts itself or is silent | 09-spec-errata.md (DECIDED rows bind; OPEN rows: ask the owner) |
| Where may files live? | `tools/guard/guard.toml` (read only) |
| How complete is feature X? | `tracker/status.json`, computed by `tools/tracker/verify.py` |
| What does the owner want in general? | this segment and 04, 05, 06 (they preserve the owner's original instructions) |
