"""
Base provider definitions for Post-Turn Background Review (SPEC §1.7 & §10.1, F-0007).
Defines contracts for daemon-threaded forked review, strict tool whitelisting,
memory/skill extraction, and the "never fatal" execution guarantee.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class SkillUpdatePreference(str, Enum):
    UPDATE_CURRENTLY_LOADED = "update_currently_loaded"
    UPDATE_EXISTING_UMBRELLA = "update_existing_umbrella"
    ADD_SUPPORT_FILE = "add_support_file"
    CREATE_NEW_UMBRELLA = "create_new_umbrella"


# Strict tool whitelist per SPEC §1.7 / §10.1 lines 2862-2868
# All other tools (bash, write_file, browser, edit) are strictly DENIED
ALLOWED_REVIEW_TOOLS: List[str] = [
    "memory",
    "skill_manage",
    "locus_memory",
    "locus_vault",
]


@dataclass
class PostTurnReviewResult:
    review_id: str
    session_id: str
    status: str
    memory_insights: List[Dict[str, Any]] = field(default_factory=list)
    skill_updates: List[Dict[str, Any]] = field(default_factory=list)
    denied_tools_attempted: List[str] = field(default_factory=list)
    execution_mode: str = "background_thread"
    duration_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "review_id": self.review_id,
            "session_id": self.session_id,
            "status": self.status,
            "memory_insights": self.memory_insights,
            "skill_updates": self.skill_updates,
            "denied_tools_attempted": self.denied_tools_attempted,
            "execution_mode": self.execution_mode,
            "duration_ms": round(self.duration_ms, 3),
        }


class BasePostTurnProvider(ABC):
    """Abstract contract for post-turn background review."""

    @abstractmethod
    def spawn_background_review(
        self,
        conversation_snapshot: List[Dict[str, Any]],
        session_id: Optional[str] = None,
        sync: bool = False,
    ) -> PostTurnReviewResult:
        """
        Fork a daemon background review task on a separate thread/process.
        Never blocks the main conversation turn.
        """
        raise NotImplementedError

    @abstractmethod
    def build_review_prompt(self, conversation_snapshot: List[Dict[str, Any]]) -> str:
        """Generate the combined memory and skill review prompt."""
        raise NotImplementedError

    @abstractmethod
    def is_tool_allowed(self, tool_name: str) -> bool:
        """Enforce strict tool whitelist; returns True only for memory and skill_manage tools."""
        raise NotImplementedError

    @abstractmethod
    def filter_tools(self, tool_names: List[str]) -> List[str]:
        """Filter tool names, denying any tool not in the whitelist."""
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if post-turn background review is enabled in config."""
        raise NotImplementedError
