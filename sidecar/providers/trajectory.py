"""
SPEC §19.2 line 10 / §03 line 12: Base Trajectory Recorder Provider Interface.
Declares abstract contracts for turn recording, session flushing, redaction,
and batch trajectory evaluation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class TurnRecord:
    """Represents a single conversational or tool-use turn within an agent session."""
    role: str
    content: str
    timestamp: str
    tokens: Dict[str, int] = field(default_factory=dict)
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "tokens": self.tokens,
            "tool_calls": self.tool_calls,
            "metadata": self.metadata,
        }


@dataclass
class TrajectorySession:
    """Full session trajectory containing metadata and sequential turns."""
    session_id: str
    model: str
    platform: str
    start_time: str
    end_time: Optional[str] = None
    turns: List[TurnRecord] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "model": self.model,
            "platform": self.platform,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "turns": [turn.to_dict() for turn in self.turns],
            "metadata": self.metadata,
        }


class BaseTrajectoryRecorder(ABC):
    """Abstract interface for session trajectory recording and evaluation."""

    def __init__(self, name: str = "trajectory_recorder") -> None:
        self.name = name
        self._enabled: bool = True

    def is_enabled(self) -> bool:
        """Return whether trajectory recording is enabled."""
        return self._enabled

    @abstractmethod
    def start_session(
        self, session_id: str, model: str = "unknown", platform: str = "locus", metadata: Optional[Dict[str, Any]] = None
    ) -> TrajectorySession:
        """Start or initialize a session trajectory."""
        pass

    @abstractmethod
    def record_turn(
        self,
        session_id: str,
        role: str,
        content: str,
        tool_calls: Optional[List[Dict[str, Any]]] = None,
        tokens: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[TurnRecord]:
        """Record a single turn for an active session."""
        pass

    @abstractmethod
    def flush_session(self, session_id: str) -> Optional[Path]:
        """Flush and persist session trajectory to disk."""
        pass

    @abstractmethod
    def get_trajectory(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve stored trajectory for a session."""
        pass

    @abstractmethod
    def batch_evaluate(
        self, session_ids: Optional[List[str]] = None, eval_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Compute aggregate evaluation metrics across recorded trajectories."""
        pass
