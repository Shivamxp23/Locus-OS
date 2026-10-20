# Spec Trace for US-48: Memory Sync (Multi-Source Ingestion Pipelines)

| Spec Ref | Spec Sentence | Code Implementation | Test File:Line |
|---|---|---|---|
| §4.7 line 824 | "## Feature §4.7: Memory Sync (Multi-Source Ingestion Pipelines)" | `sidecar/memory_sync.py:186` | `tests/unit/test_memory_sync.py:28` |
| §4.7 line 843 | "trait SyncPipeline: Send + Sync { async fn init(&self, config: &Config) → Result<()> async fn tick(&self, config: &Config) → Result<SyncOutcome> fn id(&self) → &str fn kind(&self) → SyncPipelineKind }" | `sidecar/providers/memory_sync.py:91`, `locus-extension/src/memory-sync.ts:43` | `tests/unit/test_memory_sync.py:28` |
| §4.7 line 850 | "SyncOutcome { records_ingested: u64, more_pending: bool, note: Option<String> }" | `sidecar/providers/memory_sync.py:29`, `locus-extension/src/memory-sync.ts:13` | `tests/unit/test_memory_sync.py:46`, `tests/integration/test_memory_sync_service.py:38` |
| §4.7 line 856 | "THREE PIPELINE KINDS: 1. COMPOSIO PIPELINES ... 2. WORKSPACE PIPELINES ... 3. MCP PIPELINES" | `sidecar/providers/memory_sync.py:20`, `sidecar/memory_sync.py:28`, `sidecar/memory_sync.py:77`, `sidecar/memory_sync.py:133` | `tests/unit/test_memory_sync.py:28`, `tests/integration/test_memory_sync_service.py:24` |
| §4.7 line 860 | "Each provider has its own ingest.rs + pagination cursor + retry policy" | `sidecar/memory_sync.py:93` | `tests/unit/test_memory_sync.py:68` |
| §4.7 line 863 | "Vault file watch (Obsidian .md files)" | `sidecar/memory_sync.py:38` | `tests/unit/test_memory_sync.py:46` |
| §4.7 line 868 | "One pipeline per connected MCP server" | `sidecar/memory_sync.py:133` | `tests/unit/test_memory_sync.py:101` |
| §4.7 line 874 | "THREE BACKGROUND LOOPS: Composio periodic (20-min tick) Workspace periodic (20-min tick) Queue scheduler (3 h)" | `sidecar/memory_sync.py:307`, `sidecar/providers/memory_sync.py:73` | `tests/unit/test_memory_sync.py:151`, `tests/integration/test_memory_sync_service.py:38` |
| §4.7 line 887 | "FUNCTION check_and_rebuild_tree(source): on_disk = list_raw_files(source.raw_archive_path) uncovered = on_disk - ingested IF uncovered.is_not_empty(): FOR EACH file IN uncovered: enqueue_job(JobKind::ExtractChunk, file)" | `sidecar/memory_sync.py:314` | `tests/unit/test_memory_sync.py:122`, `tests/integration/test_memory_sync_service.py:60` |
| §4.7 line 899 | "// GOTCHA: tree scope and raw-archive ID slugify DIFFERENTLY for GitHub: \"github:owner/repo\" vs \"github.com/owner/repo\" Always carry both (SourceScope struct)" | `sidecar/providers/memory_sync.py:53`, `locus-extension/src/memory-sync.ts:22` | `tests/unit/test_memory_sync.py:122`, `tests/integration/test_memory_sync_service.py:60` |
| §4.7 line 914 | "Provider Interface: SyncPipelineProvider (mirrors the trait SyncPipeline)" | `sidecar/providers/memory_sync.py:128`, `sidecar/service.py:2778` | `tests/unit/test_memory_sync.py:28` |
| §4.7 line 919 | "sync state + cursors in .locus/memory/sync_state.db" | `sidecar/memory_sync.py:206` | `tests/unit/test_memory_sync.py:186`, `tests/integration/test_memory_sync_service.py:84` |
| §4.7 line 921 | "Swappable / off state: locus.memory.sync.enabled (global) + per-pipeline toggles. Off → no automatic ingestion" | `sidecar/memory_sync.py:237`, `sidecar/service.py:2807` | `tests/unit/test_memory_sync.py:169`, `tests/integration/test_memory_sync_service.py:97` |
