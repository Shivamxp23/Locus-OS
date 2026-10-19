"""Base provider definition for System Prompt Construction (SPEC §1.2, F-0002)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, List, Optional


@dataclass
class ContextFile:
    path: str
    content: str


@dataclass
class SkillSummary:
    name: str
    description: str


@dataclass
class OperatingState:
    dcs: float = 5.0
    operating_mode: str = "NORMAL"
    faction_status: dict[str, float] = field(default_factory=lambda: {
        "Health": 25.0,
        "Leverage": 25.0,
        "Craft": 30.0,
        "Expression": 20.0,
    })


@dataclass
class PromptOptions:
    cwd: str
    custom_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None
    context_files: List[ContextFile] = field(default_factory=list)
    skills: List[SkillSummary] = field(default_factory=list)
    available_tools: List[str] = field(default_factory=lambda: ["read", "bash", "edit", "write"])
    prompt_guidelines: List[str] = field(default_factory=list)
    soul_context: Optional[str] = None
    context_forge_tokens: Optional[str] = None
    operating_state: Optional[OperatingState] = None


class BasePromptBuilderProvider(ABC):
    """Abstract base class for system prompt builders augmenting Pi with Locus SOUL personality."""

    @abstractmethod
    def build_system_prompt(self, options: PromptOptions) -> str:
        """Construct the full system prompt string given PromptOptions."""
        raise NotImplementedError

    @abstractmethod
    def load_soul_personality(self, vault_path: Optional[str] = None) -> str:
        """Load SOUL.md personality context from vault or default."""
        raise NotImplementedError

    @abstractmethod
    def format_operating_state(self, state: OperatingState) -> str:
        """Format State Engine DCS, operating mode, and faction metrics for system prompt injection."""
        raise NotImplementedError
