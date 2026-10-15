"""Locus Workflow Engine (§29.8).

Declarative multi-step task workflow orchestrator with dependency ordering,
input/output variable passing, step-level retry mechanisms, and execution tracing.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    step_id: str
    action_name: str
    depends_on: List[str] = field(default_factory=list)
    params: Dict[str, Any] = field(default_factory=dict)
    max_retries: int = 1
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None


@dataclass
class WorkflowExecutionResult:
    workflow_id: str
    success: bool
    step_results: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    failed_step: Optional[str] = None


class WorkflowEngine:
    """Executes directed acyclic graphs of discrete workflow steps."""

    def __init__(self):
        self.action_registry: Dict[str, Callable[[Dict[str, Any], Dict[str, Any]], Any]] = {}

    def register_action(self, name: str, fn: Callable[[Dict[str, Any], Dict[str, Any]], Any]) -> None:
        self.action_registry[name] = fn

    def execute_workflow(self, workflow_id: str, steps: List[WorkflowStep]) -> WorkflowExecutionResult:
        start_time = time.time()
        context: Dict[str, Any] = {}
        completed_steps: set[str] = set()

        while len(completed_steps) < len(steps):
            ready_steps = [
                s for s in steps
                if s.step_id not in completed_steps
                and all(dep in completed_steps for dep in s.depends_on)
            ]

            if not ready_steps:
                return WorkflowExecutionResult(
                    workflow_id=workflow_id,
                    success=False,
                    step_results=context,
                    duration_seconds=time.time() - start_time,
                    failed_step="UNSATISFIED_DEPENDENCIES",
                )

            for step in ready_steps:
                fn = self.action_registry.get(step.action_name)
                if not fn:
                    step.status = StepStatus.FAILED
                    step.error = f"Action '{step.action_name}' not registered"
                    return WorkflowExecutionResult(
                        workflow_id=workflow_id,
                        success=False,
                        step_results=context,
                        duration_seconds=time.time() - start_time,
                        failed_step=step.step_id,
                    )

                step.status = StepStatus.RUNNING
                success = False
                last_err = None

                for attempt in range(step.max_retries + 1):
                    try:
                        res = fn(step.params, context)
                        step.status = StepStatus.SUCCESS
                        step.result = res
                        context[step.step_id] = res
                        success = True
                        break
                    except Exception as e:
                        last_err = str(e)

                if not success:
                    step.status = StepStatus.FAILED
                    step.error = last_err
                    return WorkflowExecutionResult(
                        workflow_id=workflow_id,
                        success=False,
                        step_results=context,
                        duration_seconds=time.time() - start_time,
                        failed_step=step.step_id,
                    )

                completed_steps.add(step.step_id)

        return WorkflowExecutionResult(
            workflow_id=workflow_id,
            success=True,
            step_results=context,
            duration_seconds=time.time() - start_time,
        )
