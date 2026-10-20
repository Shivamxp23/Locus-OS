# US-54 Spec Trace — §4.14: Project-Specific Memory Decay Engine

Feature: F-0025 | Verdict: LOCUS-NEW | Author model: Claude Opus 4.6

| # | Spec sentence (verbatim) | Verdict | File:line | Test |
|---|---|---|---|---|
| 1 | `HALF_LIFE_DAYS = {"ACTIVE": 90.0, "MAINTENANCE": 45.0, "PAUSED": 30.0, "ABANDONED": 14.0, "ARCHIVED": 7.0}` | LOCUS-NEW | sidecar/memory/project_decay.py:20-26 | test_half_life_parameters |
| 2 | `COLD_STORAGE_THRESHOLD = 0.10 // Retention strength S(t) < 0.10 triggers cold archive` | LOCUS-NEW | sidecar/memory/project_decay.py:29 | test_half_life_parameters, test_cold_storage_threshold_trigger |
| 3 | `FUNCTION calculate_retention_strength(project_state: string, days_since_last_touch: float) -> float:` | LOCUS-NEW | sidecar/memory/project_decay.py:33-60 | test_calculate_retention_strength_exact |
| 4 | `half_life = HALF_LIFE_DAYS.get(project_state, 30.0)` | LOCUS-NEW | sidecar/memory/project_decay.py:49 | test_calculate_retention_strength_exact (UNKNOWN_STATE → 30.0) |
| 5 | `// Exponential half-life decay formula: S(t) = S_0 * 2^(-t / T_1/2)` | LOCUS-NEW | sidecar/memory/project_decay.py:58 | test_calculate_retention_strength_exact |
| 6 | `strength = 1.0 * (2.0 ** (-days_since_last_touch / half_life))` | LOCUS-NEW | sidecar/memory/project_decay.py:58 | test_retention_strength_bounds_and_clamping |
| 7 | `RETURN strength` | LOCUS-NEW | sidecar/memory/project_decay.py:60 | test_calculate_retention_strength_exact |
| 8 | `NIGHTLY PROJECT DECAY SWEEP (03:00 IST): FUNCTION sweep_project_memories():` | LOCUS-NEW | sidecar/memory/project_decay.py:168-243 | test_nightly_project_decay_sweep |
| 9 | `projects = neo4j.query("MATCH (p:Project) RETURN p")` | LOCUS-NEW | sidecar/memory/project_decay.py:195 (iterates self._projects, in-memory simulation per spec) | test_nightly_project_decay_sweep |
| 10 | `days_inactive = (now() - project.last_touched_at).days` | LOCUS-NEW | sidecar/memory/project_decay.py:197 | test_nightly_project_decay_sweep |
| 11 | `strength = calculate_retention_strength(project.status, days_inactive)` | LOCUS-NEW | sidecar/memory/project_decay.py:198-201 | test_nightly_project_decay_sweep |
| 12 | `MATCH (n)-[:BELONGS_TO\|SUBTASK_OF]->(p:Project {id: $proj_id}) SET n.retention_strength = $strength, n.last_decay_sweep = datetime()` | LOCUS-NEW | sidecar/memory/project_decay.py:204-209 (ProjectNode.relation in BELONGS_TO/SUBTASK_OF) | test_nightly_project_decay_sweep (active_nodes retention_strength > 0.90, last_decay_sweep == t0) |
| 13 | `IF strength < COLD_STORAGE_THRESHOLD:` | LOCUS-NEW | sidecar/memory/project_decay.py:220 | test_nightly_project_decay_sweep, test_cold_storage_threshold_trigger |
| 14 | `archive_cluster_to_cold_storage(project.id)` | LOCUS-NEW | sidecar/memory/project_decay.py:223-233, sidecar/memory/cold_archiver.py:35-73 | test_cold_archiver_roundtrip, test_nightly_project_decay_sweep |
| 15 | `MATCH (n)-[:BELONGS_TO]->(p:Project {id: $proj_id}) DETACH DELETE n` | LOCUS-NEW | sidecar/memory/project_decay.py:234 (remove_project_nodes) | test_nightly_project_decay_sweep (archived_nodes == 0) |
| 16 | `cold archived memory clusters compressed in .locus/memory/cold_archive/{project_id}.jsonl.gz` | LOCUS-NEW | sidecar/memory/cold_archiver.py:29-32 | test_cold_archiver_roundtrip (archive_path.name == "proj_alpha.jsonl.gz") |
| 17 | `Provider Interface: MemoryDecayProvider` | LOCUS-NEW | sidecar/providers/project_memory_decay.py:57-109 | test_provider_interface_implementation |
| 18 | `Swappable / off state: locus.memory.decay.enabled. Off → memory nodes never decay; all historical projects remain permanently active in Neo4j.` | LOCUS-NEW | sidecar/providers/project_memory_decay.py:37 (enabled flag), tests/integration/test_project_decay_service.py:125-149 (503 when disabled) | test_project_decay_config_off_switch, test_service_decay_modular_off_switch |
| 19 | `Registers as a provider in sidecar/providers/ with modular off-switch` | LOCUS-NEW | sidecar/providers/project_memory_decay.py:112-188 | test_project_decay_swap (ProviderRegistry swap) |
| 20 | Spec adaptation: "Integrated directly into Locus Faction goal tracking — when a project shifts from ACTIVE to ARCHIVED, its memory cluster automatically accelerates decay." | LOCUS-NEW | sidecar/memory/project_decay.py:198-201 (status drives half_life selection) | test_nightly_project_decay_sweep (ARCHIVED triggers cold archive) |

## Scope check
`git diff main...HEAD --stat` files:
- `sidecar/memory/project_decay.py` — new, §4.14 rows 1-15, 20
- `sidecar/memory/cold_archiver.py` — new, §4.14 rows 14, 16
- `sidecar/providers/project_memory_decay.py` — new, §4.14 rows 17-19
- `sidecar/memory/__init__.py` — re-exports for §4.14 symbols
- `tests/unit/test_project_decay.py` — tests rows 1-7, 13-14, 16-19
- `tests/integration/test_project_decay_service.py` — tests rows 3, 8, 18
- `tracker/` files — tracker evidence only

No file or behaviour outside the spec trace.
