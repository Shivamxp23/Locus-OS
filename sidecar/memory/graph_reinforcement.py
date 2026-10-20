"""
SPEC §4.12: Graph Reinforcement and Edge Weight Plasticity.
`sidecar/memory/graph_reinforcement.py`
Manages relationship weight clamping [0.05, 1.0], batch turn STDP processing,
decay cycles, and low-weight relationship pruning.
"""
from __future__ import annotations

import logging
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.memory.stdp_updater import apply_stdp_update
from sidecar.providers.stdp_reinforcement import (
    BaseGraphPlasticityProvider,
    OutcomeEvent,
    PRUNE_THRESHOLD,
    RetrievalEvent,
    STDPConfig,
    TraversedEdgeRecord,
    TurnAuditLog,
    W_MAX,
    W_MIN,
)

logger = logging.getLogger(__name__)

DEFAULT_EDGE_WEIGHT = 0.50


class GraphPlasticityProvider(BaseGraphPlasticityProvider):
    """
    SPEC §4.12 line 1319:
    Provider Interface: GraphPlasticityProvider.
    Maintains edge weights and applies STDP reinforcement cycles.
    """

    def __init__(
        self,
        name: str = "default",
        config: Optional[STDPConfig] = None,
        db_path: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, config=config)
        self.db_path = db_path or (self.config.storage_path if self.config else None)
        self._weights: Dict[str, float] = {}
        self._prune_tags: Dict[str, Dict[str, Any]] = {}
        self._audit_logs: List[Dict[str, Any]] = []
        self._lock = threading.RLock()

        if self.db_path:
            self._init_sqlite()

    def _init_sqlite(self) -> None:
        if not self.db_path:
            return
        p = Path(self.db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stdp_edge_weights (
                    edge_id TEXT PRIMARY KEY,
                    weight REAL NOT NULL,
                    updated_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stdp_prune_tags (
                    edge_id TEXT PRIMARY KEY,
                    reason TEXT NOT NULL,
                    weight REAL NOT NULL,
                    tagged_at REAL NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS stdp_audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    turn_id TEXT,
                    edge_id TEXT,
                    old_weight REAL,
                    new_weight REAL,
                    success INTEGER,
                    delta_t REAL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()
            cursor = conn.execute("SELECT edge_id, weight FROM stdp_edge_weights")
            for edge_id, weight in cursor.fetchall():
                self._weights[edge_id] = float(weight)
        finally:
            conn.close()

    def apply_stdp_update(
        self,
        retrieval: RetrievalEvent,
        outcome: OutcomeEvent,
        current_weight: float,
    ) -> float:
        """
        SPEC §4.12 line 1286:
        Calculate updated edge weight via STDP rule.
        """
        return apply_stdp_update(
            retrieval=retrieval,
            outcome=outcome,
            current_weight=current_weight,
            config=self.config,
        )

    def get_edge_weight(self, edge_id: str) -> float:
        """
        Fetch current weight for an edge (defaults to 0.50 if unset).
        """
        with self._lock:
            return self._weights.get(edge_id, DEFAULT_EDGE_WEIGHT)

    def set_edge_weight(self, edge_id: str, weight: float) -> None:
        """
        Update and persist weight for an edge clamped to [W_MIN, W_MAX].
        """
        with self._lock:
            clamped = self.clamp(weight)
            self._weights[edge_id] = clamped
            now = time.time()
            if self.db_path:
                conn = None
                try:
                    conn = sqlite3.connect(self.db_path)
                    conn.execute(
                        "INSERT OR REPLACE INTO stdp_edge_weights (edge_id, weight, updated_at) VALUES (?, ?, ?)",
                        (edge_id, clamped, now),
                    )
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Failed to persist edge weight in SQLite: {e}")
                finally:
                    if conn:
                        conn.close()

    def tag_edge_for_pruning(self, edge_id: str, reason: str = "STDP_DEPLETION") -> None:
        """
        SPEC §4.12 line 1314:
        IF updated_w <= PRUNE_THRESHOLD:
            neo4j.tag_edge_for_pruning(edge.id, reason="STDP_DEPLETION")
        """
        with self._lock:
            now = time.time()
            weight = self.get_edge_weight(edge_id)
            tag_data = {
                "edge_id": edge_id,
                "reason": reason,
                "weight": weight,
                "tagged_at": now,
            }
            self._prune_tags[edge_id] = tag_data
            if self.db_path:
                conn = None
                try:
                    conn = sqlite3.connect(self.db_path)
                    conn.execute(
                        "INSERT OR REPLACE INTO stdp_prune_tags (edge_id, reason, weight, tagged_at) VALUES (?, ?, ?, ?)",
                        (edge_id, reason, weight, now),
                    )
                    conn.commit()
                except Exception as e:
                    logger.warning(f"Failed to persist prune tag in SQLite: {e}")
                finally:
                    if conn:
                        conn.close()

    def list_prune_candidates(self) -> List[Dict[str, Any]]:
        """
        List all edges currently tagged or eligible for pruning (weight <= PRUNE_THRESHOLD).
        """
        with self._lock:
            candidates: Dict[str, Dict[str, Any]] = dict(self._prune_tags)
            for edge_id, weight in self._weights.items():
                if weight <= self.config.prune_threshold and edge_id not in candidates:
                    candidates[edge_id] = {
                        "edge_id": edge_id,
                        "reason": "STDP_DEPLETION",
                        "weight": weight,
                        "tagged_at": time.time(),
                    }
            return list(candidates.values())

    def process_turn_stdp(self, turn_audit_log: TurnAuditLog) -> Dict[str, Any]:
        """
        SPEC §4.12 line 1307:
        BATCH GRAPH REINFORCEMENT CYCLE:
            FUNCTION process_turn_stdp(turn_audit_log):
                FOR EACH edge IN turn_audit_log.traversed_edges:
                    current_w = neo4j.get_edge_weight(edge.id)
                    updated_w = apply_stdp_update(edge.retrieval_event, turn_audit_log.outcome, current_w)
                    neo4j.update_edge_weight(edge.id, updated_w)
                    
                    IF updated_w <= PRUNE_THRESHOLD:
                        neo4j.tag_edge_for_pruning(edge.id, reason="STDP_DEPLETION")
        """
        with self._lock:
            outcome = turn_audit_log.outcome
            if outcome is None:
                return {
                    "session_id": turn_audit_log.session_id,
                    "turn_id": turn_audit_log.turn_id,
                    "updated_edges": [],
                    "pruned_tags": [],
                }

            updated_edges: List[Dict[str, Any]] = []
            pruned_tags: List[str] = []

            for edge in turn_audit_log.traversed_edges:
                edge_id = edge.edge_id
                current_w = (
                    edge.initial_weight
                    if edge.initial_weight is not None
                    else self.get_edge_weight(edge_id)
                )

                updated_w = self.apply_stdp_update(
                    retrieval=edge.retrieval_event,
                    outcome=outcome,
                    current_weight=current_w,
                )
                self.set_edge_weight(edge_id, updated_w)

                is_pruned = False
                if updated_w <= self.config.prune_threshold:
                    self.tag_edge_for_pruning(edge_id, reason="STDP_DEPLETION")
                    pruned_tags.append(edge_id)
                    is_pruned = True

                delta_t = float(outcome.occurred_at - edge.retrieval_event.retrieved_at)
                record = {
                    "edge_id": edge_id,
                    "node_id": edge.retrieval_event.node_id,
                    "old_weight": current_w,
                    "new_weight": updated_w,
                    "delta_t": delta_t,
                    "success": outcome.success,
                    "pruned": is_pruned,
                }
                updated_edges.append(record)

                if self.db_path:
                    conn = None
                    try:
                        conn = sqlite3.connect(self.db_path)
                        conn.execute(
                            """
                            INSERT INTO stdp_audit_log (
                                session_id, turn_id, edge_id, old_weight, new_weight, success, delta_t, created_at
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                turn_audit_log.session_id,
                                turn_audit_log.turn_id,
                                edge_id,
                                current_w,
                                updated_w,
                                1 if outcome.success else 0,
                                delta_t,
                                time.time(),
                            ),
                        )
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"Failed to log STDP audit in SQLite: {e}")
                    finally:
                        if conn:
                            conn.close()

            return {
                "session_id": turn_audit_log.session_id,
                "turn_id": turn_audit_log.turn_id,
                "updated_edges": updated_edges,
                "pruned_tags": pruned_tags,
            }

    def apply_decay_cycle(self, decay_rate: float = 0.01) -> Dict[str, float]:
        """
        Passive decay cycle applying exponential/linear decay towards W_MIN for inactive edges.
        """
        with self._lock:
            updated = {}
            for edge_id, weight in list(self._weights.items()):
                new_w = max(self.config.w_min, weight * (1.0 - decay_rate))
                self.set_edge_weight(edge_id, new_w)
                updated[edge_id] = new_w
                if new_w <= self.config.prune_threshold:
                    self.tag_edge_for_pruning(edge_id, reason="STDP_DECAY")
            return updated


# Backward-compatible aliases
STDPUpdater = GraphPlasticityProvider
HebbianManager = GraphPlasticityProvider
