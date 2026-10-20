"""
SPEC §4.13 / §30.5: Proactive Inner Loop Spaced Repetition Integration.
Integrates proactive background observation generation and due node verification.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from sidecar.memory.memory_scheduler import SpacedRepetitionMemoryScheduler
from sidecar.memory.spaced_repetition import evaluate_node_retention
from sidecar.providers.spaced_repetition import MemoryNodeState


class ProactiveInnerLoopMemoryBridge:
    """
    SPEC §4.13 line 1393 and §30.5 steps 1-5:
    Proactive inner loop bridge that evaluates memory nodes not traversed recently,
    assembles observations, and feeds review evaluations into the spaced repetition scheduler.
    """

    def __init__(self, scheduler: Optional[SpacedRepetitionMemoryScheduler] = None) -> None:
        self.scheduler = scheduler or SpacedRepetitionMemoryScheduler()

    def scan_due_concepts(self, limit: int = 50, timestamp: Optional[float] = None) -> List[MemoryNodeState]:
        """Fetch concepts due for review by the inner loop."""
        return self.scheduler.get_due_nodes(limit=limit, timestamp=timestamp)

    def assemble_repetition_observation(
        self,
        node: MemoryNodeState,
        connected_projects_count: int = 1,
    ) -> Dict[str, Any]:
        """
        SPEC §30.5 step 3:
        Assemble observation: "You haven't engaged with [Concept] in X days, but it connects to active projects."
        """
        return {
            "observation_type": "SPACED_REPETITION_PROMPT",
            "node_id": node.node_id,
            "interval_days": node.interval_days,
            "repetition_count": node.repetition_count,
            "ease_factor": node.ease_factor,
            "prompt": (
                f"You haven't engaged with concept '{node.node_id}' in {node.interval_days} days, "
                f"which connects to {connected_projects_count} active projects."
            ),
        }

    def process_user_engagement(
        self,
        node_id: str,
        user_reacted: bool,
        explicit_grade: Optional[int] = None,
        timestamp: Optional[float] = None,
    ) -> MemoryNodeState:
        """
        SPEC §30.5 step 5:
        If user reacts (👍 or responds): reinforce (grade 4 or 5).
        If user ignores / thumbs down: grade 1 or 2 (decay / lapse).
        """
        if explicit_grade is not None:
            grade = explicit_grade
        elif user_reacted:
            grade = 4
        else:
            grade = 1
        return self.scheduler.record_review(node_id=node_id, quality_grade=grade, timestamp=timestamp)
