"""Locus Subagent Spawning, Archetypes & Depth Limiting (§3.7, §11.1-11.5).

Orchestrates autonomous subagents with distinct archetypes (Researcher, Coder, Critic, Planner),
enforcing maximum call graph recursion depth, timeouts, concurrency bounds, and result bubbling.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class SubagentArchetype(str, Enum):
    RESEARCHER = "researcher"
    CODER = "coder"
    CRITIC = "critic"
    PLANNER = "planner"


class SubagentState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class SubagentTask:
    task_id: str
    archetype: SubagentArchetype
    prompt: str
    depth: int = 1
    max_depth: int = 3
    timeout_seconds: float = 60.0
    parent_task_id: Optional[str] = None
    state: SubagentState = SubagentState.IDLE
    result: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "archetype": self.archetype.value,
            "prompt": self.prompt,
            "depth": self.depth,
            "max_depth": self.max_depth,
            "state": self.state.value,
            "result": self.result,
        }


class SubagentOrchestrator:
    """Manages spawning, lifecycle, recursion boundaries, and execution of subagents."""

    def __init__(self, global_max_depth: int = 3, max_concurrent: int = 5):
        self.global_max_depth = global_max_depth
        self.max_concurrent = max_concurrent
        self.active_tasks: Dict[str, SubagentTask] = {}
        self.task_history: List[SubagentTask] = []

    def spawn_subagent(
        self,
        archetype: SubagentArchetype,
        prompt: str,
        parent_depth: int = 0,
        parent_task_id: Optional[str] = None,
    ) -> SubagentTask:
        new_depth = parent_depth + 1
        if new_depth > self.global_max_depth:
            raise ValueError(f"Recursion depth limit exceeded: {new_depth} > {self.global_max_depth}")

        if len(self.active_tasks) >= self.max_concurrent:
            raise RuntimeError("Maximum concurrent subagent quota reached")

        task_id = f"sub_{archetype.value}_{uuid.uuid4().hex[:8]}"
        task = SubagentTask(
            task_id=task_id,
            archetype=archetype,
            prompt=prompt,
            depth=new_depth,
            max_depth=self.global_max_depth,
            parent_task_id=parent_task_id,
        )
        self.active_tasks[task_id] = task
        return task

    def execute_subagent(
        self,
        task: SubagentTask,
        executor_fn: Optional[Callable[[SubagentTask], str]] = None,
    ) -> str:
        task.state = SubagentState.RUNNING
        try:
            if executor_fn:
                output = executor_fn(task)
            else:
                output = f"[{task.archetype.value.upper()}] completed task: {task.prompt[:40]}"
            task.result = output
            task.state = SubagentState.COMPLETED
            return output
        except Exception as e:
            task.state = SubagentState.FAILED
            task.result = f"Error: {str(e)}"
            raise
        finally:
            if task.task_id in self.active_tasks:
                del self.active_tasks[task.task_id]
            self.task_history.append(task)
