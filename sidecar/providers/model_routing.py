"""
SPEC §2.7-2.8 / F-0096 / US-37: Intelligent Model Routing + Quality-Based Fallback Provider Contract.
Defines interfaces and data structures for policy-driven routing between local and remote backends,
task classification, health caching, refusal detection, and telemetry records.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Callable, Dict, List, Optional, Tuple, Union


class TaskCategory(str, Enum):
    LIGHTWEIGHT = "lightweight"
    MEDIUM = "medium"
    HEAVY = "heavy"


class TargetBackend(str, Enum):
    LOCAL = "local"
    REMOTE = "remote"


class LatencyBudget(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CostSensitivity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass
class RoutingHints:
    """Hints provided per request to guide routing decisions."""
    latency_budget: LatencyBudget = LatencyBudget.MEDIUM
    cost_sensitivity: CostSensitivity = CostSensitivity.MEDIUM
    privacy_required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "latency_budget": self.latency_budget.value,
            "cost_sensitivity": self.cost_sensitivity.value,
            "privacy_required": self.privacy_required,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RoutingHints:
        return cls(
            latency_budget=LatencyBudget(data.get("latency_budget", "medium")),
            cost_sensitivity=CostSensitivity(data.get("cost_sensitivity", "medium")),
            privacy_required=bool(data.get("privacy_required", False)),
        )


@dataclass
class RoutingDecision:
    """Outcome of routing policy evaluation."""
    category: TaskCategory
    primary: TargetBackend
    fallback: Optional[TargetBackend]
    supports_streaming: bool
    resolved_model: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "primary": self.primary.value,
            "fallback": self.fallback.value if self.fallback else None,
            "supports_streaming": self.supports_streaming,
            "resolved_model": self.resolved_model,
            "reason": self.reason,
        }


@dataclass
class HealthCheckResult:
    """Result of local model server health probe."""
    healthy: bool
    last_check: float
    endpoint: str
    provider_type: str = "ollama"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "healthy": self.healthy,
            "last_check": self.last_check,
            "endpoint": self.endpoint,
            "provider_type": self.provider_type,
        }


@dataclass
class RoutingRecord:
    """Telemetry record emitted after routing execution."""
    category: TaskCategory
    target: TargetBackend
    resolved_model: str
    health_status: bool
    used_fallback: bool
    latency_ms: float
    tokens_in: int = 0
    tokens_out: int = 0
    estimated_cost: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "target": self.target.value,
            "resolved_model": self.resolved_model,
            "health_status": self.health_status,
            "used_fallback": self.used_fallback,
            "latency_ms": self.latency_ms,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "estimated_cost": self.estimated_cost,
        }


@dataclass
class ChatRequest:
    """Standard chat request payload for routing."""
    model: str
    messages: List[Dict[str, str]]
    hints: RoutingHints = field(default_factory=RoutingHints)
    tools: Optional[List[Dict[str, Any]]] = None
    stream: bool = False


@dataclass
class ChatResponse:
    """Standard response from model execution."""
    text: str
    model: str
    backend: TargetBackend
    usage: Dict[str, int] = field(default_factory=dict)
    finish_reason: str = "stop"


class BaseModelRoutingProvider(ABC):
    """
    Abstract interface for Intelligent Model Routing & Quality-Based Fallback.
    Modular, swappable component per AGENTS.md law 11 and modularity architecture (03).
    """

    @abstractmethod
    def classify(self, model_string: str) -> TaskCategory:
        """Classify task from model hint or explicit identifier."""
        pass

    @abstractmethod
    def decide(
        self,
        category: TaskCategory,
        local_healthy: bool,
        hints: RoutingHints,
        has_tools: bool = False,
    ) -> RoutingDecision:
        """Compute primary and fallback routing targets based on policy and hints."""
        pass

    @abstractmethod
    def check_local_health(self, force_refresh: bool = False) -> HealthCheckResult:
        """Check health of local model server with cached TTL discipline."""
        pass

    @abstractmethod
    def is_low_quality(self, response_text: str) -> bool:
        """Evaluate response text against length floor, noise tokens, and refusal DFA."""
        pass

    @abstractmethod
    def normalize_model_id(self, hint_or_model: str) -> str:
        """Map hint strings to backend model identifiers."""
        pass

    @abstractmethod
    def execute_routed_chat(
        self,
        request: ChatRequest,
        local_invoker: Optional[Callable[[ChatRequest], ChatResponse]] = None,
        remote_invoker: Optional[Callable[[ChatRequest], ChatResponse]] = None,
    ) -> Tuple[ChatResponse, RoutingRecord]:
        """Execute chat request through primary target with quality fallback."""
        pass
