"""
SPEC §4.13: Spaced Repetition Memory Consolidation Scheduler & Persistence Provider.
Implements MemoryConsolidationProvider, managing SQLite state persistence and
nightly consolidation runs per SPEC §4.13 lines 1381-1400.
"""
from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.memory.spaced_repetition import (
    calculate_next_review,
    evaluate_node_retention,
)
from sidecar.providers.spaced_repetition import (
    MemoryConsolidationProvider,
    MemoryNodeState,
    SpacedRepetitionConfig,
)


class SpacedRepetitionMemoryScheduler(MemoryConsolidationProvider):
    """
    SPEC §4.13 lines 1381-1400:
    Persistent memory consolidation scheduler executing the SM-2 / FSRS lifecycle,
    due node selection, and core fact promotions.
    """

    def __init__(
        self,
        name: str = "default",
        config: Optional[SpacedRepetitionConfig] = None,
        db_path: Optional[str] = None,
    ) -> None:
        super().__init__(name=name, config=config)
        self.db_path = db_path or (self.config.storage_path or ":memory:")
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self.db_path != ":memory:":
            Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS spaced_repetition_nodes (
                        node_id TEXT PRIMARY KEY,
                        repetition_count INTEGER NOT NULL DEFAULT 0,
                        ease_factor REAL NOT NULL DEFAULT 2.50,
                        interval_days INTEGER NOT NULL DEFAULT 1,
                        stability REAL NOT NULL DEFAULT 1.0,
                        last_reviewed_at REAL NOT NULL DEFAULT 0.0,
                        due_date REAL NOT NULL DEFAULT 0.0,
                        lapses INTEGER NOT NULL DEFAULT 0,
                        is_core_fact INTEGER NOT NULL DEFAULT 0,
                        metadata_json TEXT NOT NULL DEFAULT '{}',
                        updated_at REAL NOT NULL DEFAULT 0.0
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS spaced_repetition_review_log (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        node_id TEXT NOT NULL,
                        quality_grade INTEGER NOT NULL,
                        prior_interval INTEGER NOT NULL,
                        new_interval INTEGER NOT NULL,
                        prior_ease REAL NOT NULL,
                        new_ease REAL NOT NULL,
                        reviewed_at REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sr_due_date ON spaced_repetition_nodes(due_date)"
                )
        finally:
            conn.close()

    def calculate_next_review(
        self,
        state: MemoryNodeState,
        quality_grade: int,
        timestamp: Optional[float] = None,
    ) -> MemoryNodeState:
        """Calculate next state without mutating persistent storage."""
        return calculate_next_review(
            state=state,
            quality_grade=quality_grade,
            timestamp=timestamp,
            config=self.config,
        )

    def get_node_state(self, node_id: str) -> Optional[MemoryNodeState]:
        """Fetch current state for a memory node."""
        conn = self._get_connection()
        try:
            row = conn.execute(
                "SELECT * FROM spaced_repetition_nodes WHERE node_id = ?",
                (node_id,),
            ).fetchone()
            if not row:
                return None
            metadata = {}
            if row["metadata_json"]:
                try:
                    metadata = json.loads(row["metadata_json"])
                except Exception:
                    metadata = {}
            return MemoryNodeState(
                node_id=row["node_id"],
                repetition_count=int(row["repetition_count"]),
                ease_factor=float(row["ease_factor"]),
                interval_days=int(row["interval_days"]),
                stability=float(row["stability"]),
                last_reviewed_at=float(row["last_reviewed_at"]),
                due_date=float(row["due_date"]),
                lapses=int(row["lapses"]),
                is_core_fact=bool(row["is_core_fact"]),
                metadata=metadata,
            )
        finally:
            conn.close()

    def save_node_state(self, state: MemoryNodeState) -> None:
        """Persist or update spaced repetition state for a memory node."""
        conn = self._get_connection()
        now = time.time()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO spaced_repetition_nodes (
                        node_id, repetition_count, ease_factor, interval_days, stability,
                        last_reviewed_at, due_date, lapses, is_core_fact, metadata_json, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(node_id) DO UPDATE SET
                        repetition_count = excluded.repetition_count,
                        ease_factor = excluded.ease_factor,
                        interval_days = excluded.interval_days,
                        stability = excluded.stability,
                        last_reviewed_at = excluded.last_reviewed_at,
                        due_date = excluded.due_date,
                        lapses = excluded.lapses,
                        is_core_fact = excluded.is_core_fact,
                        metadata_json = excluded.metadata_json,
                        updated_at = excluded.updated_at
                    """,
                    (
                        state.node_id,
                        state.repetition_count,
                        state.ease_factor,
                        state.interval_days,
                        state.stability,
                        state.last_reviewed_at,
                        state.due_date,
                        state.lapses,
                        1 if state.is_core_fact else 0,
                        json.dumps(state.metadata),
                        now,
                    ),
                )
        finally:
            conn.close()

    def record_review(
        self,
        node_id: str,
        quality_grade: int,
        timestamp: Optional[float] = None,
    ) -> MemoryNodeState:
        """
        Record an explicit review outcome for a memory node, update state,
        and log the transition.
        """
        current_state = self.get_node_state(node_id)
        if current_state is None:
            current_state = MemoryNodeState(node_id=node_id)

        prior_interval = current_state.interval_days
        prior_ease = current_state.ease_factor
        review_time = float(time.time() if timestamp is None else timestamp)

        updated_state = self.calculate_next_review(
            state=current_state,
            quality_grade=quality_grade,
            timestamp=review_time,
        )
        self.save_node_state(updated_state)

        conn = self._get_connection()
        try:
            with conn:
                conn.execute(
                    """
                    INSERT INTO spaced_repetition_review_log (
                        node_id, quality_grade, prior_interval, new_interval,
                        prior_ease, new_ease, reviewed_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        node_id,
                        int(quality_grade),
                        prior_interval,
                        updated_state.interval_days,
                        prior_ease,
                        updated_state.ease_factor,
                        review_time,
                    ),
                )
        finally:
            conn.close()

        return updated_state

    def get_due_nodes(
        self,
        limit: int = 50,
        timestamp: Optional[float] = None,
    ) -> List[MemoryNodeState]:
        """
        SPEC §4.13 lines 1383-1389:
        Query nodes where due_date <= now() OR due_date == 0.0, ordered by due_date ASC.
        """
        now = float(time.time() if timestamp is None else timestamp)
        conn = self._get_connection()
        try:
            rows = conn.execute(
                """
                SELECT * FROM spaced_repetition_nodes
                WHERE due_date <= ? OR due_date = 0.0
                ORDER BY due_date ASC
                LIMIT ?
                """,
                (now, limit),
            ).fetchall()

            res: List[MemoryNodeState] = []
            for row in rows:
                metadata = {}
                if row["metadata_json"]:
                    try:
                        metadata = json.loads(row["metadata_json"])
                    except Exception:
                        metadata = {}
                res.append(
                    MemoryNodeState(
                        node_id=row["node_id"],
                        repetition_count=int(row["repetition_count"]),
                        ease_factor=float(row["ease_factor"]),
                        interval_days=int(row["interval_days"]),
                        stability=float(row["stability"]),
                        last_reviewed_at=float(row["last_reviewed_at"]),
                        due_date=float(row["due_date"]),
                        lapses=int(row["lapses"]),
                        is_core_fact=bool(row["is_core_fact"]),
                        metadata=metadata,
                    )
                )
            return res
        finally:
            conn.close()

    def run_consolidation(
        self,
        limit: int = 50,
        simulated_grades: Optional[Dict[str, int]] = None,
        timestamp: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        SPEC §4.13 lines 1381-1400:
        NIGHTLY MEMORY CONSOLIDATION WORKER:
            due_nodes = query(due_date <= now)
            FOR EACH node in due_nodes:
                grade = evaluate_node_retention(node)
                updated_state = calculate_next_review(node.state, grade)
                save_node_state(node.id, updated_state)
                IF repetition >= 5 AND ease >= 2.5: promote CORE_FACT
        """
        now = float(time.time() if timestamp is None else timestamp)
        due_nodes = self.get_due_nodes(limit=limit, timestamp=now)
        grades_map = simulated_grades or {}

        processed: List[Dict[str, Any]] = []
        promoted_core_facts: List[str] = []

        for node in due_nodes:
            simulated_grade = grades_map.get(
                node.node_id,
                evaluate_node_retention(node, current_timestamp=now),
            )
            updated_state = self.calculate_next_review(
                state=node,
                quality_grade=simulated_grade,
                timestamp=now,
            )
            self.save_node_state(updated_state)

            if updated_state.is_core_fact and not node.is_core_fact:
                promoted_core_facts.append(node.node_id)

            processed.append({
                "node_id": node.node_id,
                "grade": simulated_grade,
                "interval_days": updated_state.interval_days,
                "ease_factor": updated_state.ease_factor,
                "repetition_count": updated_state.repetition_count,
                "is_core_fact": updated_state.is_core_fact,
                "due_date": updated_state.due_date,
            })

        return {
            "processed_count": len(processed),
            "promoted_core_facts": promoted_core_facts,
            "nodes": processed,
            "timestamp": now,
        }

    def list_core_facts(self) -> List[MemoryNodeState]:
        """List all nodes marked as core facts."""
        conn = self._get_connection()
        try:
            rows = conn.execute(
                "SELECT * FROM spaced_repetition_nodes WHERE is_core_fact = 1 ORDER BY node_id ASC"
            ).fetchall()
            res: List[MemoryNodeState] = []
            for row in rows:
                metadata = {}
                if row["metadata_json"]:
                    try:
                        metadata = json.loads(row["metadata_json"])
                    except Exception:
                        metadata = {}
                res.append(
                    MemoryNodeState(
                        node_id=row["node_id"],
                        repetition_count=int(row["repetition_count"]),
                        ease_factor=float(row["ease_factor"]),
                        interval_days=int(row["interval_days"]),
                        stability=float(row["stability"]),
                        last_reviewed_at=float(row["last_reviewed_at"]),
                        due_date=float(row["due_date"]),
                        lapses=int(row["lapses"]),
                        is_core_fact=True,
                        metadata=metadata,
                    )
                )
            return res
        finally:
            conn.close()


# Canonical alias
MemoryScheduler = SpacedRepetitionMemoryScheduler
