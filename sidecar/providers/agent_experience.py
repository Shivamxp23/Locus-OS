"""
SPEC §10.9 lines 6356-6430:
Agent Experience Tracking (Procedural Memory) Provider Interface and Implementation (F-0121 / US-67).
Implements BaseAgentExperienceProvider and DefaultAgentExperienceProvider with modular off-switches:
- locus.agent_experience_tracking_procedural_memory.enabled
- locus.experience.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.experience.procedural import (
    AgentExperience,
    AgentExperienceCaptureHook,
    ExperienceStore,
    prepend_experience_block,
    render_experience_hits,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseAgentExperienceProvider(ABC):
    """
    SPEC §10.9: Provider Interface: AgentExperienceProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Agent Experience Tracking is enabled."""
        raise NotImplementedError

    @abstractmethod
    def record_turn(self, turn_context: Dict[str, Any]) -> Dict[str, Any]:
        """Record and extract experiences from turn context."""
        raise NotImplementedError

    @abstractmethod
    def query_experiences(self, task_fingerprint: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query relevant procedural experiences."""
        raise NotImplementedError

    @abstractmethod
    def render_block(self, task_fingerprint: str, limit: int = 5, message: str = "") -> Dict[str, Any]:
        """Render and prepend experience block."""
        raise NotImplementedError

    @abstractmethod
    def list_experiences(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List experiences."""
        raise NotImplementedError


class DefaultAgentExperienceProvider(BaseAgentExperienceProvider):
    """
    SPEC §10.9: Default implementation of AgentExperienceProvider.
    Procedural memory capturing tool sequences, successes, repeated failures, and recovery.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".locus" / "experience")
        self.store = ExperienceStore(storage_dir=self.storage_dir)
        self.capture_hook = AgentExperienceCaptureHook(store=self.store)

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.agent_experience_tracking_procedural_memory.enabled
        - locus.experience.enabled
        """
        v1 = config.get("locus.agent_experience_tracking_procedural_memory.enabled")
        if v1 is not None and not config.is_enabled("locus.agent_experience_tracking_procedural_memory.enabled"):
            return False

        v2 = config.get("locus.experience.enabled")
        if v2 is not None and not config.is_enabled("locus.experience.enabled"):
            return False

        return True

    def record_turn(self, turn_context: Dict[str, Any]) -> Dict[str, Any]:
        """Extract and store candidates from turn context."""
        experiences = self.capture_hook.on_turn_complete(turn_context)
        return {
            "status": "ok",
            "extracted_count": len(experiences),
            "experiences": [exp.to_dict() for exp in experiences],
        }

    def query_experiences(self, task_fingerprint: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Query matching experiences."""
        hits = self.store.query(task_fingerprint=task_fingerprint, limit=limit)
        return [h.to_dict() for h in hits]

    def render_block(self, task_fingerprint: str, limit: int = 5, message: str = "") -> Dict[str, Any]:
        """Render relevant operating experience block prepended to message."""
        hits = self.store.query(task_fingerprint=task_fingerprint, limit=limit)
        block = render_experience_hits(hits)
        prepended = prepend_experience_block(message=message, hits=hits)
        return {
            "status": "ok",
            "hits_count": len(hits),
            "block": block,
            "prepended_message": prepended,
        }

    def list_experiences(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List stored experiences."""
        return [exp.to_dict() for exp in self.store.list(limit=limit)]
