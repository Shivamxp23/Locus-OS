"""
SPEC §11.1-11.5 + §3.7: Subagent Archetypes, Spawning, Depth Limiting, and AutoResearch.
Defines abstract contracts, data structures, and default archetypes for subagent delegation.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional


class ArchetypeCategory(str, Enum):
    FACTION = "faction"
    OPENHUMAN = "openhuman"
    CUSTOM = "custom"


@dataclass
class SubagentArchetype:
    """Archetype defining subagent behavior, instructions, tools, and limits."""
    name: str
    description: str
    category: ArchetypeCategory
    system_prompt: str
    allowed_tools: List[str] = field(default_factory=list)
    default_model: str = "claude-3-7-sonnet"
    max_turns: int = 10

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category.value if isinstance(self.category, ArchetypeCategory) else str(self.category),
            "system_prompt": self.system_prompt,
            "allowed_tools": self.allowed_tools,
            "default_model": self.default_model,
            "max_turns": self.max_turns,
        }


@dataclass
class SubagentSpawnRequest:
    """Request to spawn an isolated subagent under a parent session."""
    task: str
    archetype: str
    parent_session_id: Optional[str] = None
    current_depth: int = 0
    model_override: Optional[str] = None
    context_extra: Optional[Dict[str, Any]] = None
    max_turns_override: Optional[int] = None


@dataclass
class SubagentSpawnResult:
    """Outcome of a subagent lifecycle execution."""
    session_id: str
    parent_session_id: Optional[str]
    archetype: str
    depth: int
    status: str  # "completed", "error", "depth_limit_exceeded"
    output: str
    turns_used: int
    skip_memory: bool = True
    skip_review: bool = True
    delegated_tasks: List[Dict[str, Any]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "parent_session_id": self.parent_session_id,
            "archetype": self.archetype,
            "depth": self.depth,
            "status": self.status,
            "output": self.output,
            "turns_used": self.turns_used,
            "skip_memory": self.skip_memory,
            "skip_review": self.skip_review,
            "delegated_tasks": self.delegated_tasks,
            "error": self.error,
        }


@dataclass
class AutoResearchRequest:
    """Request for autonomous multi-step research synthesis."""
    topic: str
    depth_mode: str = "quick"  # "quick" or "deep"
    hypotheses: List[str] = field(default_factory=list)
    parent_session_id: Optional[str] = None


@dataclass
class AutoResearchResult:
    """Outcome of AutoResearch topic investigation."""
    topic: str
    depth_mode: str
    summary: str
    findings: List[Dict[str, Any]] = field(default_factory=list)
    subagents_spawned: int = 0
    status: str = "completed"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "depth_mode": self.depth_mode,
            "summary": self.summary,
            "findings": self.findings,
            "subagents_spawned": self.subagents_spawned,
            "status": self.status,
            "error": self.error,
        }


class BaseSubagentProvider(ABC):
    """Abstract base provider for Subagent Archetype management and spawning."""

    MAX_SPAWN_DEPTH: int = 3

    def __init__(self, name: str = "subagents") -> None:
        self.name = name

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return whether subagent spawning is enabled in configuration."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize provider lifecycle and archetype registry."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform health check and return provider status and catalog count."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully release provider resources."""
        pass

    @abstractmethod
    def get_archetype(self, name: str) -> Optional[SubagentArchetype]:
        """Retrieve archetype configuration by name."""
        pass

    @abstractmethod
    def list_archetypes(self, category: Optional[str] = None) -> List[SubagentArchetype]:
        """List registered archetypes, optionally filtered by category."""
        pass

    @abstractmethod
    def spawn_subagent(
        self,
        request: SubagentSpawnRequest,
        memory_callback: Optional[Callable[[str, Any, str], None]] = None,
    ) -> SubagentSpawnResult:
        """
        Spawn a subagent instance adhering to MAX_SPAWN_DEPTH = 3,
        skip_memory=True, skip_review=True, and notifying parent memory provider.
        """
        pass

    @abstractmethod
    def execute_autoresearch(self, request: AutoResearchRequest) -> AutoResearchResult:
        """Execute autonomous research topic decomposition and hypothesis synthesis."""
        pass
