"""Spaced Repetition Memory Consolidation (SM-2 / FSRS) (§4.13).

Computes next review intervals, ease factors, and stability scores for memory nodes,
enabling cognitive consolidation and preventing knowledge decay.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional


MIN_EASE_FACTOR: float = 1.30
DEFAULT_EASE_FACTOR: float = 2.50


@dataclass
class MemoryNodeState:
    node_id: str
    repetition_count: int = 0
    ease_factor: float = DEFAULT_EASE_FACTOR
    interval_days: int = 1
    stability: float = 1.0
    last_reviewed_at: Optional[str] = None
    due_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MemoryNodeState:
        return cls(
            node_id=str(data.get("node_id", "")),
            repetition_count=int(data.get("repetition_count", 0)),
            ease_factor=float(data.get("ease_factor", DEFAULT_EASE_FACTOR)),
            interval_days=int(data.get("interval_days", 1)),
            stability=float(data.get("stability", 1.0)),
            last_reviewed_at=data.get("last_reviewed_at"),
            due_date=data.get("due_date"),
        )


def calculate_next_review(
    state: MemoryNodeState,
    quality_grade: int,
    current_time: Optional[datetime] = None,
) -> MemoryNodeState:
    """Calculate next review schedule using the SuperMemo SM-2 algorithm.

    quality_grade: 0 to 5.
    0 = Blackout, 1 = Incorrect, 2 = Hard recall,
    3 = Pass with effort, 4 = Good recall, 5 = Perfect/Reflexive.
    """
    now = current_time or datetime.now(timezone.utc)
    grade = max(0, min(5, quality_grade))

    if grade >= 3:
        if state.repetition_count == 0:
            state.interval_days = 1
        elif state.repetition_count == 1:
            state.interval_days = 6
        else:
            state.interval_days = max(1, round(state.interval_days * state.ease_factor))
        state.repetition_count += 1
    else:
        state.repetition_count = 0
        state.interval_days = 1

    # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
    delta_ef = 0.1 - (5 - grade) * (0.08 + (5 - grade) * 0.02)
    state.ease_factor = max(MIN_EASE_FACTOR, state.ease_factor + delta_ef)

    # Approximate stability update (FSRS inspiration)
    if grade >= 3:
        state.stability = round(state.stability * (1.0 + (grade - 2) * 0.2), 3)
    else:
        state.stability = max(0.5, round(state.stability * 0.6, 3))

    state.last_reviewed_at = now.isoformat()
    state.due_date = (now + timedelta(days=state.interval_days)).isoformat()
    return state


class MemoryScheduler:
    """Schedules, queries, and consolidates memory nodes according to SM-2 review cadences."""

    def __init__(self) -> None:
        self.node_states: Dict[str, MemoryNodeState] = {}

    def register_node(
        self,
        node_id: str,
        ease_factor: float = DEFAULT_EASE_FACTOR,
        initial_due: Optional[datetime] = None,
    ) -> MemoryNodeState:
        now = datetime.now(timezone.utc)
        due_str = (initial_due or now).isoformat()
        state = MemoryNodeState(
            node_id=node_id,
            ease_factor=ease_factor,
            due_date=due_str,
        )
        self.node_states[node_id] = state
        return state

    def get_node(self, node_id: str) -> Optional[MemoryNodeState]:
        return self.node_states.get(node_id)

    def record_review(
        self,
        node_id: str,
        quality_grade: int,
        review_time: Optional[datetime] = None,
    ) -> MemoryNodeState:
        state = self.node_states.get(node_id)
        if not state:
            state = self.register_node(node_id)
        updated = calculate_next_review(state, quality_grade, current_time=review_time)
        self.node_states[node_id] = updated
        return updated

    def get_due_nodes(self, as_of: Optional[datetime] = None) -> List[MemoryNodeState]:
        target = as_of or datetime.now(timezone.utc)
        target_iso = target.isoformat()
        due_list: List[MemoryNodeState] = []
        for state in self.node_states.values():
            if state.due_date is None or state.due_date <= target_iso:
                due_list.append(state)
        return sorted(due_list, key=lambda s: s.due_date or "")
