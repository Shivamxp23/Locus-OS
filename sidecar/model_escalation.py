"""
Implementation of Model Management & Escalation (SPEC §1.4, F-0004).
Provides turn-by-turn model escalation, tier routing, and dynamic credential resolution.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.providers.model_manager import (
    BaseModelManagementProvider,
    ModelDescriptor,
    ModelTier,
    TurnEscalationDecision,
    TurnEscalationRequest,
)

logger = logging.getLogger(__name__)

DEFAULT_MODELS: Dict[str, ModelDescriptor] = {
    "standard": ModelDescriptor(
        model_id="deepseek/deepseek-chat",
        provider="deepseek",
        tier=ModelTier.STANDARD,
        context_window=128000,
        max_thinking_budget=0,
        supports_thinking=False,
        api_key_name="DEEPSEEK_API_KEY",
    ),
    "reasoning": ModelDescriptor(
        model_id="google/gemini-2.5-pro",
        provider="google",
        tier=ModelTier.REASONING,
        context_window=1000000,
        max_thinking_budget=32768,
        supports_thinking=True,
        api_key_name="GEMINI_API_KEY",
    ),
    "background": ModelDescriptor(
        model_id="deepseek/deepseek-chat",
        provider="deepseek",
        tier=ModelTier.BACKGROUND,
        context_window=128000,
        max_thinking_budget=0,
        supports_thinking=False,
        api_key_name="AUXILIARY_API_KEY",
    ),
}


class ModelEscalationProvider(BaseModelManagementProvider):
    """Concrete model manager providing tiered escalation and credential resolution."""

    def __init__(self, custom_config: Optional[Dict[str, Any]] = None):
        self._custom_config = custom_config
        self._catalog = dict(DEFAULT_MODELS)

    def is_escalation_enabled(self) -> bool:
        if self._custom_config is not None:
            if not self._custom_config.get("locus.model_management_escalation.enabled", True):
                return False
            return bool(self._custom_config.get("locus.models.escalation.enabled", True))
        val = config.get("locus.model_management_escalation.enabled")
        if val is not None and not config.is_enabled("locus.model_management_escalation.enabled"):
            return False
        val2 = config.get("locus.models.escalation.enabled")
        if val2 is not None and not config.is_enabled("locus.models.escalation.enabled"):
            return False
        return True

    def list_models(self) -> List[ModelDescriptor]:
        return list(self._catalog.values())

    def get_model(self, model_id_or_tier: str) -> Optional[ModelDescriptor]:
        for descriptor in self._catalog.values():
            if descriptor.model_id == model_id_or_tier or descriptor.tier.value == model_id_or_tier:
                return descriptor
        return None

    def clamp_thinking_level(self, model_id: str, requested_budget: int) -> int:
        desc = self.get_model(model_id)
        if not desc or not desc.supports_thinking:
            return 0
        if requested_budget < 0:
            return 0
        return min(requested_budget, desc.max_thinking_budget)

    def resolve_model_credentials(self, api_key_name: str) -> Optional[str]:
        return config.get_env(api_key_name)

    def resolve_turn_model(self, request: TurnEscalationRequest) -> TurnEscalationDecision:
        standard_model = self._catalog["standard"]
        reasoning_model = self._catalog["reasoning"]
        background_model = self._catalog["background"]

        # If escalation is switched off, always stick to standard single model
        if not self.is_escalation_enabled():
            return TurnEscalationDecision(
                model_id=standard_model.model_id,
                provider=standard_model.provider,
                tier=standard_model.tier,
                thinking_budget=0,
                reason="Automatic escalation disabled; using standard base model",
                api_key_name=standard_model.api_key_name,
                swapped=False,
            )

        # 1. Background task tier
        if request.is_background:
            return TurnEscalationDecision(
                model_id=background_model.model_id,
                provider=background_model.provider,
                tier=background_model.tier,
                thinking_budget=0,
                reason="Background task executed on auxiliary client",
                api_key_name=background_model.api_key_name,
                swapped=True,
            )

        # 2. Complex reasoning / Sunday synthesis tier
        if (
            request.is_sunday_synthesis
            or request.complexity_score >= 7.0
            or request.estimated_tokens > 64000
            or request.task_type in ("synthesis", "deep_architecture", "complex_reasoning")
        ):
            thinking_budget = self.clamp_thinking_level(reasoning_model.model_id, 8192)
            return TurnEscalationDecision(
                model_id=reasoning_model.model_id,
                provider=reasoning_model.provider,
                tier=reasoning_model.tier,
                thinking_budget=thinking_budget,
                reason="Escalated: Sunday synthesis or high complexity reasoning",
                api_key_name=reasoning_model.api_key_name,
                swapped=True,
            )

        # 3. Standard turns (default)
        return TurnEscalationDecision(
            model_id=standard_model.model_id,
            provider=standard_model.provider,
            tier=standard_model.tier,
            thinking_budget=0,
            reason="Standard routine conversational turn",
            api_key_name=standard_model.api_key_name,
            swapped=False,
        )
