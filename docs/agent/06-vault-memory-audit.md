# 06 - Vault, memory, sync, and auditability

## Vault (DECIDED, errata D-2)
`vault/` has exactly 8 folders: `00-System 01-Projects 02-Areas 03-Resources 04-Captures 05-Daily 06-Content 07-Archives`.
Spec paths with old names map as: `00-System-Data` -> `00-System/`, `02-Reviews` -> `05-Daily/Weekly/`, `05-Logs` -> `05-Daily/Logs/`,
`06-Resources` -> `03-Resources/`, `07-Diagrams` -> `03-Resources/Diagrams/`. The guard fails any other top-level name.
Fixed destinations: AI chat archive `04-Captures/AI Chats/YYYY-MM-DD/<title>.md` (spec 19.3); weekly synthesis
`05-Daily/Weekly/YYYY-Www-Synthesis.md`; LiveSync guide `00-System/LIVESYNC_SETUP.md`.

## Sync: Obsidian Self-hosted LiveSync + CouchDB, nothing else (spec 27.2; tracker F-0060)
- Never Git sync, never Syncthing. CouchDB 3.3.3, container `locus-couchdb`, database `locus-vault`.
- Bridge `sidecar/vault/livesync_bridge.py` (changes feed <-> vault folder, deterministic 3-way conflict resolution); watcher
  `sidecar/crawlers/vault_crawler.py`. A markdown file must never contain conflict markers; conflicts stay in CouchDB `_conflicts`.
- Its security is mandatory, not optional: 10-security.md S-2.

## Memory (spec 4.1-4.2 and 4.18)
- The memory substrate is **Neo4j Agent Memory** (`neo4j-labs/agent-memory`, reference clone `5_Locus/deps/agent-memory`) behind
  `MemoryProvider`. mem0, supermemory, honcho, mastra, cognee are swap targets, never defaults.
- Three stores, three jobs: Neo4j (graph memory; `POLE+O` entities; edges such as `:TOUCHED` and `:DECIDED`), PageIndex (vectorless
  document tree), pgvector (384-dim `BAAI/bge-small-en-v1.5`). Never Qdrant.
- Agent Memory v0.5 hygiene types the spec lists: `User` scoping, `ConsolidationRun`, `MemoryReadAudit`. Use them; never invent parallel ones.
- `locus.memory.enabled=false` turns the whole subsystem off. Memory lives in the databases, never in the repo.

## Auditability: the owner's headline principle (spec status PARTIAL; errata D-4)
Owner's intent: every chat and every agent action is recorded and backed up into the Obsidian vault automatically, so the owner can
always see what Locus did and why. What the spec ALREADY specifies (build exactly this, nothing more, until D-4 is DECIDED):
| Piece | Where | Spec |
|---|---|---|
| Session/trajectory recording, one JSON per session | `sidecar/` trajectory writer | 19.2 (F-0049) |
| Nightly archiver 23:45: external AI chats (Claude, ChatGPT, Cursor, Pi, Telegram) -> markdown -> `04-Captures/AI Chats/` -> LiveSync | `sidecar/ingestion/chat_archiver.py` | 19.3 (F-0050) |
| One audit row per proactive thought | `inner_loop_audit` (and `inner_loop_log` per pass, D-11) | 26.1 step 9 |
| Tool usage, shutdown log, reinforcement audit, MCP write audit | `tool_usage`, `shutdown_log`, `stdp_audit_log`, `MCP audit.db` | schema, 4.x, 18.x |
NOT in the spec: the word "auditability" (0 hits), ONE audit trail across every channel, a rule that approvals and cron runs are
recorded, redaction rules for audit text, retention, and a way for the owner to browse it. Do not design these yourself: they are
questions for the owner (prompt P3).

## Rules that bind whatever D-4 says
1. Anything an agent writes into the vault is markdown with YAML frontmatter: `title`, `date`, `source`, `tags`.
2. Audit and chat text never contains a secret: run the redactor (spec 13.8) BEFORE writing, not after.
3. A failed backup is logged and retried; it never blocks the conversation.
4. An archived chat is never deleted or rewritten. A correction is a new note that links to the old one.
5. The vault is the owner's data: no agent reorganizes, renames, or "cleans" existing notes.
