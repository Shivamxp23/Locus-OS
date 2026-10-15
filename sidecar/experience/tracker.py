"""Locus Agent Experience Tracking (Procedural Memory) (§10.9).

Records successful multi-step tool calling trajectories, action paths, error recovery steps,
and outcomes into indexed procedural memory for rapid retrieval by future agent sessions.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ProceduralTrajectory:
    trajectory_id: str
    task_goal: str
    action_sequence: List[str]  # e.g., ["grep", "read_file", "edit_file", "run_tests"]
    success: bool
    confidence_score: float  # 0.0 to 1.0 based on test results and human approval
    duration_seconds: float
    error_recovery_count: int = 0
    tags: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trajectory_id": self.trajectory_id,
            "task_goal": self.task_goal,
            "action_sequence": self.action_sequence,
            "success": self.success,
            "confidence_score": self.confidence_score,
            "duration_seconds": self.duration_seconds,
            "error_recovery_count": self.error_recovery_count,
            "tags": self.tags,
            "timestamp": self.timestamp,
        }


class AgentExperienceTracker:
    """Stores and retrieves procedural trajectories to accelerate agent problem-solving."""

    def __init__(self):
        self.trajectories: List[ProceduralTrajectory] = []

    def record_trajectory(
        self,
        task_goal: str,
        action_sequence: List[str],
        success: bool = True,
        duration_seconds: float = 1.0,
        error_recovery_count: int = 0,
        tags: Optional[List[str]] = None,
    ) -> ProceduralTrajectory:
        traj_id = f"traj_{uuid.uuid4().hex[:8]}"
        confidence = 0.95 if success and error_recovery_count == 0 else (0.80 if success else 0.20)

        trajectory = ProceduralTrajectory(
            trajectory_id=traj_id,
            task_goal=task_goal,
            action_sequence=action_sequence,
            success=success,
            confidence_score=confidence,
            duration_seconds=duration_seconds,
            error_recovery_count=error_recovery_count,
            tags=tags or [],
        )
        self.trajectories.append(trajectory)
        return trajectory

    def find_similar_trajectories(self, task_goal: str, min_confidence: float = 0.5) -> List[ProceduralTrajectory]:
        q_words = set(task_goal.lower().split())
        results: List[tuple[float, ProceduralTrajectory]] = []

        for t in self.trajectories:
            if t.confidence_score < min_confidence:
                continue
            t_words = set(t.task_goal.lower().split())
            overlap = len(q_words.intersection(t_words))
            if overlap > 0:
                score = overlap * t.confidence_score
                results.append((score, t))

        results.sort(key=lambda x: x[0], reverse=True)
        return [t for _, t in results]
