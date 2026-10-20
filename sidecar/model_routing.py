"""
Implementation of Intelligent Model Routing + Quality-Based Fallback (SPEC §2.7-2.8, F-0096).
Steals OpenHuman routing architecture: 3-tier classification, health caching, refusal DFA,
privacy-required fail-closed routing, and quality fallback.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import requests

from sidecar import config
from sidecar.providers.model_routing import (
    BaseModelRoutingProvider,
    ChatRequest,
    ChatResponse,
    CostSensitivity,
    HealthCheckResult,
    LatencyBudget,
    RoutingDecision,
    RoutingHints,
    RoutingRecord,
    TargetBackend,
    TaskCategory,
)
from sidecar.registry import get_registry

logger = logging.getLogger(__name__)

# Spec §2.7-2.8 constants
MIN_RESPONSE_BYTES: int = 10
EMPTY_NOISE_TOKENS: Set[str] = {"...", "I", "", "?"}
HEALTH_CACHE_TTL_SECONDS: float = 30.0
HEALTH_PROBE_TIMEOUT_SECONDS: float = 3.0

REFUSAL_PATTERNS: List[str] = [
    "I cannot",
    "I can't",
    "I'm unable",
    "I apologize but",
    "As an AI",
    "I don't have the ability",
    "I'm not able",
    "I am not able",
]

# Compiled refusal pattern
REFUSAL_REGEX = re.compile("|".join(re.escape(p) for p in REFUSAL_PATTERNS), re.IGNORECASE)

MODEL_REASONING_V1 = "google/gemini-2.5-pro"
MODEL_CHAT_V1 = "deepseek/deepseek-chat"
MODEL_AGENTIC_V1 = "deepseek/deepseek-chat"
MODEL_CODING_V1 = "deepseek/deepseek-chat"
MODEL_LOCAL_DEFAULT = "ollama/llama3.2:3b"


class ModelRoutingProvider(BaseModelRoutingProvider):
    """
    Concrete provider for Intelligent Model Routing and Quality-Based Fallback.
    Implements in-process policy decisions per OpenHuman routing module.
    """

    def __init__(
        self,
        local_base_url: str = "http://127.0.0.1:11434",
        provider_type: str = "ollama",
        health_cache_ttl: float = HEALTH_CACHE_TTL_SECONDS,
        custom_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.local_base_url = local_base_url.rstrip("/")
        self.provider_type = provider_type.lower()
        self.health_cache_ttl = health_cache_ttl
        self.custom_config = custom_config

        self._cached_health: Optional[HealthCheckResult] = None
        self._cache_lock = threading.Lock()
        self._telemetry_history: List[RoutingRecord] = []

    def classify(self, model_string: str) -> TaskCategory:
        """
        Classify task from hint prefix or model name.
        SPEC §2.7-2.8:
        'hint:quick', 'hint:fast' -> Lightweight
        'hint:medium' -> Medium
        'hint:reasoning', 'hint:agentic', 'hint:coding', 'hint:chat' -> Heavy
        explicit model name or unknown -> Heavy
        """
        ms = (model_string or "").strip().lower()
        if ms.startswith("hint:"):
            hint = ms[5:]
            if hint in ("quick", "fast"):
                return TaskCategory.LIGHTWEIGHT
            elif hint == "medium":
                return TaskCategory.MEDIUM
            elif hint in ("reasoning", "agentic", "coding", "chat"):
                # "hint:chat" goes remote despite being conversational (local TTFT too slow)
                return TaskCategory.HEAVY
            else:
                return TaskCategory.HEAVY

        # Explicit model name or unknown default to Heavy
        return TaskCategory.HEAVY

    def normalize_model_id(self, hint_or_model: str) -> str:
        """Map hint strings to backend model IDs."""
        h = (hint_or_model or "").strip()
        if h == "hint:reasoning":
            return MODEL_REASONING_V1
        elif h in ("hint:chat", "hint:agentic", "hint:coding"):
            return MODEL_CHAT_V1
        elif h in ("hint:quick", "hint:fast"):
            return MODEL_LOCAL_DEFAULT
        elif h == "hint:medium":
            return MODEL_CHAT_V1
        return h

    def decide(
        self,
        category: TaskCategory,
        local_healthy: bool,
        hints: RoutingHints,
        has_tools: bool = False,
    ) -> RoutingDecision:
        """
        SPEC §2.7-2.8 ROUTING DECISION:
        Lightweight: Default Local, Remote if local unhealthy
        Medium: Default Remote, Local if LatencyBudget::Low OR CostSensitivity::High (and local healthy)
        Heavy: Remote (always), Local ONLY if privacy_required

        PRIVACY_REQUIRED:
          Forces local routing for ALL categories (even Heavy)
          No remote fallback - fails closed
          Disables streaming (supports_streaming -> False)

        TOOLS FORCE REMOTE:
          If request carries tools and policy chose local -> override to remote
        """
        # Privacy mode override from global config
        privacy_required = hints.privacy_required
        if self._get_config_value("locus.routing.privacy_mode", False):
            privacy_required = True

        # Check if routing is globally disabled
        routing_enabled = self._get_config_value("locus.routing.enabled", True)
        if not routing_enabled:
            return RoutingDecision(
                category=category,
                primary=TargetBackend.REMOTE,
                fallback=None,
                supports_streaming=True,
                resolved_model=MODEL_CHAT_V1,
                reason="Routing disabled globally; default remote primary",
            )

        # Privacy required forces local and disables fallback + streaming
        if privacy_required:
            return RoutingDecision(
                category=category,
                primary=TargetBackend.LOCAL,
                fallback=None,
                supports_streaming=False,
                resolved_model=MODEL_LOCAL_DEFAULT,
                reason="Privacy required: local execution forced, fail-closed with no fallback",
            )

        # Baseline category defaults
        primary = TargetBackend.REMOTE
        fallback: Optional[TargetBackend] = None
        reason = "Default remote execution"

        if category == TaskCategory.LIGHTWEIGHT:
            if local_healthy:
                primary = TargetBackend.LOCAL
                fallback = TargetBackend.REMOTE
                reason = "Lightweight task routed to local model server"
            else:
                primary = TargetBackend.REMOTE
                fallback = None
                reason = "Lightweight task routed to remote because local model is unhealthy"
        elif category == TaskCategory.MEDIUM:
            if local_healthy and (
                hints.latency_budget == LatencyBudget.LOW
                or hints.cost_sensitivity == CostSensitivity.HIGH
            ):
                primary = TargetBackend.LOCAL
                fallback = TargetBackend.REMOTE
                reason = "Medium task routed to local due to Low latency budget or High cost sensitivity"
            else:
                primary = TargetBackend.REMOTE
                fallback = TargetBackend.LOCAL if local_healthy else None
                reason = "Medium task routed to remote by default"
        elif category == TaskCategory.HEAVY:
            primary = TargetBackend.REMOTE
            fallback = None
            reason = "Heavy task routed to remote backend"

        # Tools Force Remote override
        if has_tools and primary == TargetBackend.LOCAL:
            primary = TargetBackend.REMOTE
            fallback = None
            reason = "Tool calling requested; local lacks native tool support, overriding to remote"

        resolved = MODEL_LOCAL_DEFAULT if primary == TargetBackend.LOCAL else MODEL_CHAT_V1

        return RoutingDecision(
            category=category,
            primary=primary,
            fallback=fallback,
            supports_streaming=True,
            resolved_model=resolved,
            reason=reason,
        )

    def check_local_health(self, force_refresh: bool = False) -> HealthCheckResult:
        """
        Check health of local model server with cached TTL.
        Lock discipline: read cache, check timestamp, release lock, probe if stale.
        """
        now = time.time()
        with self._cache_lock:
            if not force_refresh and self._cached_health is not None:
                if (now - self._cached_health.last_check) < self.health_cache_ttl:
                    return self._cached_health

        # Probe without holding lock across network I/O
        is_healthy = False
        target_url = f"{self.local_base_url}/api/tags" if self.provider_type == "ollama" else f"{self.local_base_url}/models"
        try:
            resp = requests.get(target_url, timeout=HEALTH_PROBE_TIMEOUT_SECONDS)
            if resp.status_code == 200:
                is_healthy = True
        except Exception as e:
            logger.debug(f"Local health check probe failed for {target_url}: {e}")
            is_healthy = False

        result = HealthCheckResult(
            healthy=is_healthy,
            last_check=time.time(),
            endpoint=target_url,
            provider_type=self.provider_type,
        )

        with self._cache_lock:
            self._cached_health = result

        return result

    def set_cached_health(self, healthy: bool) -> None:
        """Helper for test mock injection."""
        with self._cache_lock:
            self._cached_health = HealthCheckResult(
                healthy=healthy,
                last_check=time.time(),
                endpoint=self.local_base_url,
                provider_type=self.provider_type,
            )

    def is_low_quality(self, response_text: str) -> bool:
        """
        SPEC §2.7-2.8 QUALITY-BASED FALLBACK:
        Check 1: Length floor (< MIN_RESPONSE_BYTES)
        Check 2: Empty-noise tokens (strip() in ['...', 'I', '', '?'])
        Check 3: Refusal DFA / patterns
        """
        if not response_text:
            return True

        # Check 1: Length floor in UTF-8 bytes
        encoded = response_text.encode("utf-8")
        if len(encoded) < MIN_RESPONSE_BYTES:
            return True

        # Check 2: Empty-noise tokens
        if response_text.strip() in EMPTY_NOISE_TOKENS:
            return True

        # Check 3: Refusal pattern matching
        if REFUSAL_REGEX.search(response_text):
            return True

        return False

    def execute_routed_chat(
        self,
        request: ChatRequest,
        local_invoker: Optional[Callable[[ChatRequest], ChatResponse]] = None,
        remote_invoker: Optional[Callable[[ChatRequest], ChatResponse]] = None,
    ) -> Tuple[ChatResponse, RoutingRecord]:
        """
        Dispatch flow:
        - Classify task
        - Check local health
        - Decide primary + fallback
        - Invoke primary
        - Fallback on error or low quality (if local primary)
        - Emit telemetry record
        """
        start_time = time.time()
        category = self.classify(request.model)
        health = self.check_local_health()
        has_tools = bool(request.tools)
        decision = self.decide(category, health.healthy, request.hints, has_tools=has_tools)

        def _default_invoker(backend: TargetBackend, req: ChatRequest) -> ChatResponse:
            return ChatResponse(
                text=f"Response from {backend.value} for {req.model}",
                model=decision.resolved_model,
                backend=backend,
                usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            )

        call_local = local_invoker or (lambda r: _default_invoker(TargetBackend.LOCAL, r))
        call_remote = remote_invoker or (lambda r: _default_invoker(TargetBackend.REMOTE, r))

        used_fallback = False
        target = decision.primary
        response: Optional[ChatResponse] = None

        # Primary attempt
        try:
            if decision.primary == TargetBackend.LOCAL:
                response = call_local(request)
            else:
                response = call_remote(request)
        except Exception as primary_err:
            if decision.primary == TargetBackend.LOCAL and decision.fallback == TargetBackend.REMOTE:
                logger.info(f"Primary local dispatch failed ({primary_err}); engaging remote fallback")
                response = call_remote(request)
                used_fallback = True
                target = TargetBackend.REMOTE
            else:
                raise primary_err

        # Quality gate for local primary responses
        if (
            decision.primary == TargetBackend.LOCAL
            and not used_fallback
            and not request.hints.privacy_required
            and decision.fallback == TargetBackend.REMOTE
        ):
            if self.is_low_quality(response.text):
                logger.info("Local response flagged as low quality / refusal; executing remote fallback")
                response = call_remote(request)
                used_fallback = True
                target = TargetBackend.REMOTE

        latency_ms = (time.time() - start_time) * 1000.0
        tokens_in = response.usage.get("prompt_tokens", 0) if response else 0
        tokens_out = response.usage.get("completion_tokens", 0) if response else 0
        estimated_cost = (tokens_in * 0.00000014) + (tokens_out * 0.00000028) if target == TargetBackend.REMOTE else 0.0

        record = RoutingRecord(
            category=category,
            target=target,
            resolved_model=response.model if response else decision.resolved_model,
            health_status=health.healthy,
            used_fallback=used_fallback,
            latency_ms=latency_ms,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            estimated_cost=estimated_cost,
        )

        self._telemetry_history.append(record)
        return response, record

    def get_telemetry_history(self) -> List[RoutingRecord]:
        return list(self._telemetry_history)

    def _get_config_value(self, key: str, default: Any = None) -> Any:
        if self.custom_config and key in self.custom_config:
            return self.custom_config[key]
        return config.get(key, default)


# Auto-register with provider registry
_registry = get_registry()
_registry.register("model_routing", "default", ModelRoutingProvider)
_registry.register("intelligent_model_routing_quality_based_fallback", "default", ModelRoutingProvider)
