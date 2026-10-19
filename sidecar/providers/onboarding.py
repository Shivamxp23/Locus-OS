"""
SPEC §1.12 / F-0012 / US-31: Onboarding Flow Provider Contract.
Defines interfaces and schemas for multi-topology setup, configuration wizards,
cognitive tri-stack onboarding, and automated diagnostic probes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class TopologyType(str, Enum):
    LOCAL = "local"
    VM = "vm"
    HYBRID = "hybrid"


@dataclass
class DiagnosticProbeResult:
    name: str
    status: str  # "ok", "failed", "skipped"
    latency_ms: float = 0.0
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class OnboardingStepResult:
    step: str
    status: str  # "ok", "failed", "pending"
    data: Dict[str, Any] = field(default_factory=dict)
    message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step": self.step,
            "status": self.status,
            "data": self.data,
            "message": self.message,
        }


class BaseOnboardingProvider(ABC):
    """Abstract base class for Onboarding Flow provider."""

    @abstractmethod
    def set_topology(self, topology: str) -> OnboardingStepResult:
        """Select deployment topology: local, vm, or hybrid."""
        pass

    @abstractmethod
    def configure_llm(
        self,
        provider: str,
        model: str,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        fallback_provider: Optional[str] = None,
        fallback_key: Optional[str] = None,
    ) -> OnboardingStepResult:
        """Configure primary and secondary LLM providers."""
        pass

    @abstractmethod
    def configure_memory(
        self,
        enable_neo4j: bool,
        neo4j_uri: Optional[str] = None,
        neo4j_user: Optional[str] = None,
        neo4j_password: Optional[str] = None,
        enable_headroom: bool = True,
    ) -> OnboardingStepResult:
        """Configure Cognitive Memory Tri-Stack (Neo4j, Headroom, PageIndex)."""
        pass

    @abstractmethod
    def configure_vault(
        self,
        vault_path: str,
        enable_livesync: bool = False,
        couch_url: Optional[str] = None,
        couch_user: Optional[str] = None,
        couch_password: Optional[str] = None,
        couch_db: Optional[str] = None,
    ) -> OnboardingStepResult:
        """Configure Obsidian local vault and CouchDB LiveSync."""
        pass

    @abstractmethod
    def configure_life_os(
        self,
        timezone: str = "Asia/Kolkata",
        morning_checkin_time: str = "08:00",
        factions: Optional[Dict[str, Any]] = None,
    ) -> OnboardingStepResult:
        """Configure Life OS 4-faction baseline and morning check-in schedule."""
        pass

    @abstractmethod
    def configure_telegram(
        self,
        enabled: bool = False,
        token: Optional[str] = None,
        owner_id: Optional[str] = None,
    ) -> OnboardingStepResult:
        """Configure Telegram Ambient Gateway."""
        pass

    @abstractmethod
    def configure_cron(
        self,
        enabled: bool = True,
        schedules: Optional[List[Dict[str, Any]]] = None,
    ) -> OnboardingStepResult:
        """Configure 24/7 Autonomous Cron Engine."""
        pass

    @abstractmethod
    def run_diagnostics(
        self, probes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Execute diagnostic probe suite across configured subsystems."""
        pass

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return onboarding completion state and current configuration summary."""
        pass

    @abstractmethod
    def reset(self) -> None:
        """Reset onboarding state to uninitialized."""
        pass
