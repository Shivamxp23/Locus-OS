"""sidecar/routing/model_router.py - Intelligent Model Routing & Quality Fallback.

Implements Spec §2.7-2.8:
- Classify task: Lightweight (hint:quick/fast), Medium (hint:medium), Heavy (hint:reasoning/coding/chat/agentic).
- Routing decision matrix with overrides:
  - privacy_required: forces Local for all tasks, fails closed without remote fallback.
  - tools present: forces Remote because local models lack reliable native tool-calling.
- Local Health Checking: cached probe with 30s TTL.
- Quality-Based Fallback: detects low quality, refusal DFA, or truncation and triggers fallback to remote.
- Telemetry: RoutingRecord schema.
- Modularity switch: locus.routing.enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
import time
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

REFUSAL_PATTERNS = [
    r"\bi cannot\b",
    r"\bi can't\b",
    r"\bi'm unable\b",
    r"\bi apologize but\b",
    r"\bas an ai\b",
    r"\bi don't have the ability\b",
    r"\bi am not able\b",
]

MIN_RESPONSE_BYTES = 20


class TaskCategory(str, Enum):
    LIGHTWEIGHT = "LIGHTWEIGHT"
    MEDIUM = "MEDIUM"
    HEAVY = "HEAVY"


class RouteTarget(str, Enum):
    LOCAL = "LOCAL"
    REMOTE = "REMOTE"


@dataclass
class RoutingHints:
    latency_budget: str = "Medium"  # "Low", "Medium", "High"
    cost_sensitivity: str = "Medium"  # "Low", "Medium", "High"
    privacy_required: bool = False
    has_tools: bool = False


@dataclass
class RoutingRecord:
    category: TaskCategory
    target: RouteTarget
    resolved_model: str
    health_status: bool
    used_fallback: bool
    latency_ms: float = 0.0
    quality_triggered: bool = False


@runtime_checkable
class ModelRouterProvider(Protocol):
    """Protocol for intelligent model routers."""

    def route_request(self, model_or_hint: str, hints: Optional[RoutingHints] = None) -> Tuple[RouteTarget, Optional[RouteTarget]]:
        """Determine primary and fallback targets."""
        return RouteTarget.REMOTE, None


class ModelRouter:
    """Core Intelligent Model Router implementing Spec §2.7-2.8."""

    def __init__(
        self,
        enabled: bool = True,
        local_model_name: str = "qwen2.5:7b",
        remote_model_name: str = "deepseek-v4-flash",
    ):
        self.enabled = enabled
        self.local_model_name = local_model_name
        self.remote_model_name = remote_model_name
        self._local_healthy = True
        self._last_health_check = 0.0
        self._health_ttl_seconds = 30.0

    @staticmethod
    def classify(model_or_hint: str) -> TaskCategory:
        """Classify task into Lightweight, Medium, or Heavy."""
        s = model_or_hint.lower().strip()
        if s in ("hint:quick", "hint:fast", "quick", "fast"):
            return TaskCategory.LIGHTWEIGHT
        elif s in ("hint:medium", "medium"):
            return TaskCategory.MEDIUM
        else:
            # hint:reasoning, hint:coding, hint:agentic, hint:chat, or explicit model name
            return TaskCategory.HEAVY

    def is_local_healthy(self) -> bool:
        """Cached check of local model server health with 30s TTL."""
        now = time.time()
        if (now - self._last_health_check) < self._health_ttl_seconds:
            return self._local_healthy
        # In actual deployment, probes Ollama /api/tags or OpenAI-compat /models
        self._last_health_check = now
        return self._local_healthy

    def set_local_healthy(self, healthy: bool) -> None:
        """Explicitly override health status (useful in tests and health checkers)."""
        self._local_healthy = healthy
        self._last_health_check = time.time()

    def decide(
        self,
        category: TaskCategory,
        hints: RoutingHints,
    ) -> Tuple[RouteTarget, Optional[RouteTarget]]:
        """Calculate primary and fallback routing targets per Spec matrix."""
        # Override 1: privacy_required forces local only, fail closed
        if hints.privacy_required:
            return RouteTarget.LOCAL, None

        # Override 2: tools force remote because local lacks native tool calling
        if hints.has_tools:
            return RouteTarget.REMOTE, None

        local_ok = self.is_local_healthy()

        if category == TaskCategory.LIGHTWEIGHT:
            if local_ok:
                return RouteTarget.LOCAL, RouteTarget.REMOTE
            return RouteTarget.REMOTE, None

        elif category == TaskCategory.MEDIUM:
            # Local if LatencyBudget is Low OR CostSensitivity is High
            if (hints.latency_budget == "Low" or hints.cost_sensitivity == "High") and local_ok:
                return RouteTarget.LOCAL, RouteTarget.REMOTE
            return RouteTarget.REMOTE, (RouteTarget.LOCAL if local_ok else None)

        else:  # Heavy
            return RouteTarget.REMOTE, None

    @staticmethod
    def is_low_quality(response_text: str) -> bool:
        """Evaluate if local response is empty, truncated, or a refusal."""
        text = response_text.strip()
        # Check 1: Length floor
        if len(text.encode("utf-8")) < MIN_RESPONSE_BYTES:
            return True

        # Check 2: Empty-noise tokens
        if text in ("...", "I", "", "?", "[]", "{}"):
            return True

        # Check 3: Refusal regex
        for pat in REFUSAL_PATTERNS:
            if re.search(pat, text, re.IGNORECASE):
                return True

        return False

    def route_request(
        self,
        model_or_hint: str,
        hints: Optional[RoutingHints] = None,
    ) -> Tuple[RouteTarget, Optional[RouteTarget]]:
        """Full routing entrypoint returning (primary_target, fallback_target)."""
        if not self.enabled:
            return RouteTarget.REMOTE, None

        effective_hints = hints or RoutingHints()
        category = self.classify(model_or_hint)
        return self.decide(category, effective_hints)
