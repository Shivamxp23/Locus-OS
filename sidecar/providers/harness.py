"""
SPEC §3.7 + §11.5 / §03 line 18: Base Harness Provider Interface.
Declares abstract contracts for external coding harness delegation (Pi, Claude Code,
OpenCode, Antigravity) running in isolated scratch git worktrees.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class HarnessType(str, Enum):
    """Supported external coding harnesses."""
    PI = "pi"
    CLAUDE = "claude-code"
    OPENCODE = "opencode"
    ANTIGRAVITY = "antigravity"


@dataclass
class TaskBrief:
    """Brief describing the coding task delegated to an external harness."""
    description: str
    target_files: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    test_commands: List[str] = field(default_factory=list)
    timeout: int = 600
    complexity: str = "normal"  # "high", "normal", "quick_fix"
    requires_autonomous: bool = False
    is_quick_fix: bool = False
    harness_override: Optional[HarnessType] = None


@dataclass
class DelegationResult:
    """Outcome of delegated coding task execution."""
    status: str
    harness_used: str
    exit_code: int
    diff: str
    modified_files: List[str]
    execution_time_seconds: float
    stdout: str = ""
    stderr: str = ""
    worktree_path: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "harness_used": self.harness_used,
            "exit_code": self.exit_code,
            "diff": self.diff,
            "modified_files": self.modified_files,
            "execution_time_seconds": self.execution_time_seconds,
            "stdout": self.stdout,
            "stderr": self.stderr,
            "worktree_path": self.worktree_path,
            "error": self.error,
        }


class BaseHarnessProvider(ABC):
    """Abstract provider interface for delegating tasks to coding harnesses."""

    def __init__(self, name: str = "harness_provider") -> None:
        self.name = name
        self._enabled: bool = True

    def is_enabled(self) -> bool:
        """Return whether coding harness delegation is enabled."""
        return self._enabled

    @abstractmethod
    def initialize(self) -> None:
        """Initialize provider lifecycle and verify available harness binaries."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return health status, available harnesses, and latency."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully release provider resources."""
        pass

    @abstractmethod
    def select_harness(self, brief: TaskBrief) -> HarnessType:
        """Select best harness based on task requirements and availability."""
        pass

    @abstractmethod
    def format_command_args(self, harness: HarnessType, brief: TaskBrief, prompt: str) -> List[str]:
        """Construct command-line arguments for executing the harness subprocess."""
        pass

    @abstractmethod
    def execute_delegation(
        self, brief: TaskBrief, repo_root: Optional[Path] = None
    ) -> DelegationResult:
        """Execute delegated task inside an isolated scratch git worktree."""
        pass
