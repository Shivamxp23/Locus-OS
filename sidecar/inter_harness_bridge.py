"""sidecar/inter_harness_bridge.py - Inter-Harness Delegation Bridge.

Connects the Pi extension and external callers to Locus OS harness delegation.
Implements Spec §3.7, §11.5, and Security Rule S-3.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from sidecar.harness import (
    CodingTask,
    DelegationResult,
    HarnessManager,
    HarnessProvider,
    ScratchWorktreeManager,
    validate_security_flags,
)

__all__ = [
    "CodingTask",
    "DelegationResult",
    "HarnessManager",
    "HarnessProvider",
    "ScratchWorktreeManager",
    "validate_security_flags",
    "delegate_coding_task",
]


def delegate_coding_task(
    prompt: str,
    harness: str = "mock",
    timeout_seconds: int = 120,
    preserve_worktree: bool = False,
    metadata: Optional[dict[str, Any]] = None,
) -> DelegationResult:
    """Convenience bridge entrypoint for delegating a coding task."""
    manager = HarnessManager()
    task = CodingTask(
        prompt=prompt,
        target_harness=harness,
        timeout_seconds=timeout_seconds,
        preserve_worktree=preserve_worktree,
        metadata=metadata or {},
    )
    return manager.delegate(task)
