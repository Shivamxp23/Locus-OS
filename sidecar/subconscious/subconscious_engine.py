"""Locus Subconscious Background Processing Engine (§29.7).

Executes idle-time micro-tasks: memory consolidation, vector index warming,
stale cache eviction, and proactive schedule preparation during user downtime.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SubconsciousTaskState(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class SubconsciousTask:
    task_id: str
    name: str
    priority: int  # 1 (lowest) to 10 (highest)
    interval_seconds: float
    action: Optional[Callable[[], Any]] = None
    last_run_timestamp: float = 0.0
    state: SubconsciousTaskState = SubconsciousTaskState.PENDING
    execution_count: int = 0
    last_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "priority": self.priority,
            "interval_seconds": self.interval_seconds,
            "last_run_timestamp": self.last_run_timestamp,
            "state": self.state.value,
            "execution_count": self.execution_count,
            "last_error": self.last_error,
        }


class SubconsciousEngine:
    """Manages low-priority background worker tasks during agent idle periods."""

    def __init__(self, idle_threshold_seconds: float = 5.0):
        self.idle_threshold_seconds = idle_threshold_seconds
        self.last_user_activity: float = time.time()
        self.tasks: Dict[str, SubconsciousTask] = {}
        self.running: bool = False

    def record_activity(self) -> None:
        """Called whenever the user or active agent executes an action."""
        self.last_user_activity = time.time()

    def is_idle(self) -> bool:
        return (time.time() - self.last_user_activity) >= self.idle_threshold_seconds

    def register_task(
        self,
        task_id: str,
        name: str,
        interval_seconds: float,
        action: Callable[[], Any],
        priority: int = 5,
    ) -> SubconsciousTask:
        task = SubconsciousTask(
            task_id=task_id,
            name=name,
            priority=priority,
            interval_seconds=interval_seconds,
            action=action,
        )
        self.tasks[task_id] = task
        return task

    def step(self) -> List[str]:
        """Runs eligible tasks if system is idle. Returns list of executed task_ids."""
        if not self.is_idle():
            return []

        now = time.time()
        executed: List[str] = []

        # Sort tasks by priority (descending)
        sorted_tasks = sorted(
            self.tasks.values(),
            key=lambda t: t.priority,
            reverse=True,
        )

        for task in sorted_tasks:
            if now - task.last_run_timestamp >= task.interval_seconds:
                task.state = SubconsciousTaskState.RUNNING
                try:
                    if task.action:
                        task.action()
                    task.state = SubconsciousTaskState.COMPLETED
                    task.execution_count += 1
                    task.last_error = None
                except Exception as e:
                    task.state = SubconsciousTaskState.FAILED
                    task.last_error = str(e)
                finally:
                    task.last_run_timestamp = now
                    executed.append(task.task_id)

        return executed
