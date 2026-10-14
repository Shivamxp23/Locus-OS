# v3 → v4 Decomposition Upgrade — Task List

## Batch 1 — Critical Deepenings

- `[x]` 1. §13.3-13.5: Deepen Sandbox System (4 backends with real logic)
- `[x]` 2. §4.5: Add Memory Tree/Cascade (missing)
- `[x]` 3. §4.7-4.9: Add Memory Sync, Queue, Diff (missing)
- `[x]` 4. §18.1-18.4: Deepen MCP System (stdio client, server, registry)
- `[x]` 5. §18.5: Add Obsidian MCP (missing)
- `[x]` 6. §13.8: Deepen Prompt Injection Protection
- `[x]` 7. §3.7: Deepen Harness Delegation (user-understanding logic)
- `[x]` 8. §17.1: Deepen Telegram Gateway (PTB handlers, inline keyboards)
- `[x]` 9. §2.7-2.8: Add Intelligent Routing + Refusal Detection logic
- `[x]` 10. §10.8-10.9: Add Self-Evolving Architect + Agent Experience (missing)

## Source File Reading Status

- `[x]` `openhuman/security/traits.rs` (80 lines)
- `[x]` `openhuman/security/bubblewrap.rs` (184 lines)
- `[x]` `openhuman/security/firejail.rs` (196 lines)
- `[x]` `openhuman/security/landlock.rs` (247 lines)
- `[x]` `openhuman/mcp_client/stdio.rs` (241 lines)
- `[x]` `openhuman/memory_tree/` (mod, io, ingest, tree/bucket_seal, tree/factory, retrieval/drill_down)
- `[x]` `openhuman/memory_sync/` (mod, traits, canonicalize)
- `[x]` `openhuman/memory_queue/` (mod, types, scheduler, worker)
- `[x]` `openhuman/memory_diff/` (mod, types, ops)
- `[x]` `openhuman/mcp_server/` (mod, protocol, stdio, tools/dispatch)
- `[x]` `openhuman/mcp_registry/` (registry surface — via §18 deep-read)
- `[x]` `openhuman/prompt_injection/` (detector.rs, mod)
- `[x]` `openhuman/routing/` (mod, policy, provider, quality, factory)
- `[x]` `openhuman/agent_experience/` (mod, types, capture, prompt)
- `[ ]` `openhuman/channels/traits.rs` (deferred — Batch 2 §17.6)
- `[x]` `hermes-agent/gateway/platforms/telegram.py` (handler registration, callback, connect)
- `[x]` `hermes-agent/gateway/platform_registry.py` (PlatformEntry + registry)

## Notes

- v4 written to `Implementation Plans/LOCUS_FEATURE_LOGIC_DECOMPOSITION_v4.md` (4,861 lines, 95 `## Feature` sections — up from 86).
- `/graphify` was available this run (graph at `5_Locus/graphify-out/graph.json`); module maps confirmed via the graph, flag-level logic read directly from the named files. The 12 remaining `direct file read (/graphify unavailable)` tags are untouched pre-existing sections (Batch 2/3 scope).
- `openhuman/channels/traits.rs` intentionally deferred — §17.6 (additional channels) is Batch 2, not Batch 1.
