# Spec Trace for US-52: STDP Reinforcement (Spike-Timing-Dependent Plasticity)

| Spec Ref | Spec Sentence | Code Implementation | Test File:Line |
|---|---|---|---|
| §4.12 line 1247 | "## Feature §4.12: STDP Reinforcement (Spike-Timing-Dependent Plasticity)" | `sidecar/memory/stdp_updater.py:1` | `tests/unit/test_stdp_reinforcement.py:27` |
| §4.12 line 1265 | "A_plus = 0.15 // Max potentiation (strengthening)" | `sidecar/providers/stdp_reinforcement.py:12` | `tests/unit/test_stdp_reinforcement.py:27` |
| §4.12 line 1267 | "A_minus = 0.12 // Max depression (weakening)" | `sidecar/providers/stdp_reinforcement.py:13` | `tests/unit/test_stdp_reinforcement.py:27` |
| §4.12 line 1268 | "tau_plus = 300.0 // Positive time constant (5 minutes in seconds)" | `sidecar/providers/stdp_reinforcement.py:14` | `tests/unit/test_stdp_reinforcement.py:27` |
| §4.12 line 1269 | "tau_minus = 600.0 // Negative time constant (10 minutes in seconds)" | `sidecar/providers/stdp_reinforcement.py:15` | `tests/unit/test_stdp_reinforcement.py:27` |
| §4.12 line 1270 | "W_MIN = 0.05 // Minimum edge weight (prevents complete deletion)" | `sidecar/providers/stdp_reinforcement.py:16` | `tests/unit/test_stdp_reinforcement.py:27`, `tests/unit/test_stdp_reinforcement.py:110` |
| §4.12 line 1271 | "W_MAX = 1.00 // Maximum edge weight saturation" | `sidecar/providers/stdp_reinforcement.py:17` | `tests/unit/test_stdp_reinforcement.py:27`, `tests/unit/test_stdp_reinforcement.py:110` |
| §4.12 line 1272 | "PRUNE_THRESHOLD = 0.08 // Below this, edge is marked for archive/prune" | `sidecar/providers/stdp_reinforcement.py:18` | `tests/unit/test_stdp_reinforcement.py:27`, `tests/unit/test_stdp_reinforcement.py:126` |
| §4.12 line 1275 | "RetrievalEvent: node_id: string, edge_id: string, retrieved_at: float // epoch timestamp" | `sidecar/providers/stdp_reinforcement.py:22` | `tests/unit/test_stdp_reinforcement.py:27` |
| §4.12 line 1280 | "OutcomeEvent: session_id: string, turn_id: string, success: bool, occurred_at: float" | `sidecar/providers/stdp_reinforcement.py:44` | `tests/unit/test_stdp_reinforcement.py:27` |
| §4.12 line 1286 | "FUNCTION apply_stdp_update(retrieval: RetrievalEvent, outcome: OutcomeEvent, current_weight: float) -> float:" | `sidecar/memory/stdp_updater.py:44`, `sidecar/service.py:3595` | `tests/unit/test_stdp_reinforcement.py:53`, `tests/integration/test_stdp_reinforcement_service.py:49` |
| §4.12 line 1289 | "IF delta_t <= 0: // Retrieval happened AFTER outcome — causality violation, ignore RETURN current_weight" | `sidecar/memory/stdp_updater.py:73` | `tests/unit/test_stdp_reinforcement.py:53` |
| §4.12 line 1293 | "IF outcome.success: delta_w = A_plus * exp(-delta_t / tau_plus) new_weight = current_weight + delta_w" | `sidecar/memory/stdp_updater.py:38` | `tests/unit/test_stdp_reinforcement.py:70`, `tests/integration/test_stdp_reinforcement_service.py:49` |
| §4.12 line 1297 | "ELSE: delta_w = A_minus * exp(-delta_t / tau_minus) new_weight = current_weight - delta_w" | `sidecar/memory/stdp_updater.py:41` | `tests/unit/test_stdp_reinforcement.py:90`, `tests/integration/test_stdp_reinforcement_service.py:49` |
| §4.12 line 1303 | "new_weight = clamp(new_weight, W_MIN, W_MAX)" | `sidecar/memory/stdp_updater.py:87`, `sidecar/memory/graph_reinforcement.py:126` | `tests/unit/test_stdp_reinforcement.py:110` |
| §4.12 line 1307 | "FUNCTION process_turn_stdp(turn_audit_log): FOR EACH edge IN turn_audit_log.traversed_edges: current_w = neo4j.get_edge_weight(edge.id) updated_w = apply_stdp_update(...) IF updated_w <= PRUNE_THRESHOLD: neo4j.tag_edge_for_pruning(edge.id, reason='STDP_DEPLETION')" | `sidecar/memory/graph_reinforcement.py:202`, `sidecar/service.py:3610` | `tests/unit/test_stdp_reinforcement.py:126`, `tests/integration/test_stdp_reinforcement_service.py:101` |
| §4.12 line 1319 | "Provider Interface: GraphPlasticityProvider" | `sidecar/providers/stdp_reinforcement.py:155`, `sidecar/service.py:3533` | `tests/unit/test_stdp_reinforcement.py:126` |
| §4.12 line 1321 | "Swappable / off state: locus.memory.stdp.enabled. Off -> Neo4j edge weights remain static; traversal uses unweighted paths." | `sidecar/service.py:3569` | `tests/integration/test_stdp_reinforcement_service.py:141` |
