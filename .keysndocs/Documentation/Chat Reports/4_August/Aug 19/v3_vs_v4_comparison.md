# Comparison: v3 vs v4 — Feature Logic Decomposition

## Top-Level Metrics

| Metric | v3 (edited by us) | v4 (separate copy) | Delta |
|--------|-------------------|---------------------|-------|
| **Lines** | 5,359 | 4,862 | v3 +497 lines |
| **Bytes** | 244 KB | 262 KB | v4 +18 KB |
| **`## Feature` headers** | 113 | 95 | v3 +18 headers |
| **Code blocks** | 80 | 83 | v4 +3 blocks |
| **`# Section` headers** | 40 | 41 | ~equal |
| **Last modified** | 15:37 (by us) | 15:13 (by Pi) | v4 older |

> [!NOTE]
> v3 has MORE lines and headers because we atomized the KEEP-PI tables into per-feature headers. v4 has MORE bytes because its §10.8 Self-Evolving Architect and §10.9 Agent Experience sections are more narrative/dense.

---

## Structural Shape

Both documents share the **same skeleton** — identical `# Section` headers in the same order. The title of v4 still says "(v3)" — it's a working fork, not a clean version bump.

---

## Content Unique to v3 (our edits)

These are sections we inserted or converted that v4 does NOT have:

| Section | What v3 Has | v4 Status |
|---------|-------------|-----------|
| **§2.1-2.9 atomic headers** | 7 individual `## Feature` headers for KEEP-PI providers | v4 uses a table |
| **§3.1-3.12 atomic headers** | 12 individual `## Feature` headers for KEEP-PI tools | v4 uses a table |
| **§15.1 atomic header** | `## Feature §15.1` | v4 uses a table |
| **§24.1 atomic header** | `## Feature §24.1` | v4 uses a table |
| **§2.7-2.8 Intelligent Routing** | Full policy engine with classify→decide→dispatch, 3-category system, health cache, Aho-Corasick refusal DFA, privacy fail-closed, RoutingRecord telemetry | v4 has it too but as TWO separate sections (§2.7 + §2.8) |
| **MCP §18 — Registry deepening** | Full Smithery, supervisor reconnect, opaque secret-ref lifecycle, setup agent | v4 has a similar deepening |
| **MCP §18 — Server deepening** | Full tool catalog table, security policy, write audit pipeline, resource catalog | v4 has a similar deepening |
| **Telegram Gateway §17.1** | Full PTB connect flow, adaptive text batch ingress, fallback IP transport, DM topics, inline keyboards, polling error recovery, notification modes | v4 is shallower here |

---

## Content Unique to v4 (Pi's edits)

These are sections v4 has that v3 does NOT:

| Section | What v4 Has | v3 Status |
|---------|-------------|-----------|
| **§10.8 Self-Evolving Architect Bot** | Full Locus-original design: scan reward signals → classify patch target (config vs code) → risk-gate deploy (low/medium/high) → close-the-loop. ~50 lines of pseudocode + philosophy. | ❌ MISSING from v3 |
| **§18.5 Obsidian MCP (Vault Bridge)** | Full spec: 5 MCP tools (`vault.read/write/search/tag/stats`), approval gate integration, wikilink resolution, 3-level tag hierarchy enforcement. ~60 lines. | ❌ MISSING from v3 |
| **§2.7 and §2.8 as separate sections** | v4 splits routing into two atomic `## Feature` headers (§2.7 routing + §2.8 refusal), each with its own adaptation block | v3 combines them as §2.7-2.8 |

---

## Content Present in Both (different depth)

| Section | v3 Depth | v4 Depth | Winner |
|---------|----------|----------|--------|
| **§4.5 Memory Tree** | Full OpenHuman logic: seal-cascade, TreeNode struct, SEAL_GATE config, topic routing, stale flush, persistence schema | Full logic: identical coverage + narrative framing | **Tie** |
| **§4.7 Memory Sync** | Full: 3 pipeline kinds, SyncPipeline trait, 3 scheduler loops, raw-archive self-healing | Full: similar coverage | **Tie** |
| **§4.8 Memory Queue** | Full: job pipeline, 6 JobKind variants, SQLite schema, dedupe, claim_token, worker pool, scheduler | Full: similar | **Tie** |
| **§4.9 Memory Diff** | Full: Snapshot/DiffResult types, named checkpoints, agent tool, RPC surface | Full: similar | **Tie** |
| **§10.4/10.9 Agent Experience** | Full: 3-heuristic auto-capture, lexical scoring formula (tool 0.4/tag 0.2/query 0.3), redact_text, prompt injection | Full + more narrative: stable_experience_id, capture hook details, Context Forge integration notes | **v4 slightly** |
| **§18.1-18.4 MCP** | Full: dual transport + registry + server + write audit + resource catalog + safety filter + prompt injection scan | Full: similar depth, slightly different framing | **Tie** |
| **§13.1 Prompt Injection** | Full 6-step normalization + 3-variant DFA (deepened by us in prior session) | Same content (both forked from the same base) | **Tie** |
| **§13.3 Sandbox** | Full 4-backend system (deepened by us in prior session) | Same content | **Tie** |
| **§17.1 Telegram** | Full PTB connect flow with fallback IPs, adaptive batch ingress, inline keyboards, DM topics, polling error recovery | Shallower — registry + basic adapter interface only | **v3** |
| **KEEP-PI sections** | Atomic `## Feature` headers (audit-compliant) | Tables (audit gap — the original audit finding) | **v3** |

---

## Summary of Gaps

### v3 is missing (should steal from v4):
1. **§10.8 Self-Evolving Architect Bot** — Locus-original, ~50 lines pseudocode, the self-improvement loop
2. **§18.5 Obsidian MCP** — 5 vault tools, approval gate, wikilink resolution, ~60 lines

### v4 is missing (should steal from v3):
1. **KEEP-PI atomic headers** — v4 still uses tables (§2, §3, §15, §24)
2. **Telegram Gateway depth** — v4 is shallow; v3 has the full PTB connect flow
3. **§2.7-2.8 as a unified routing section** — v3's combined format is denser

---

## Recommendation

> [!IMPORTANT]
> **Merge v4's unique content INTO v3**, then rename v3 → v4. The two missing sections from v4 (§10.8 + §18.5) are ~130 lines of high-value Locus-original design. Everything else v4 has, v3 already matches or exceeds.

Merge checklist:
- [ ] Copy §10.8 Self-Evolving Architect from v4 into v3 (insert after §10.4 Agent Experience)
- [ ] Copy §18.5 Obsidian MCP from v4 into v3 (insert after §18.1-18.4)
- [ ] Update title from "(v3)" to "(v4)"
- [ ] Delete the separate v4 file (or archive it)
