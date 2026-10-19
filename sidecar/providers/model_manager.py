"""
Base provider definitions for Model Management & Escalation (SPEC §1.4, F-0004).
Defines contracts for model tiers, escalation decisions, and provider interfaces.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ModelTier(str, Enum):
    STANDARD = "standard"        # Routine fast conversational turns (DeepSeek Flash / lowest cost)
    REASONING = "reasoning"      # Complex reasoning / Sunday synthesis (Gemini 2.5 Pro / 1M context)
    BACKGROUND = "background"    # Autonomous background jobs (auxiliary client / cheap)


@dataclass
class ModelDescriptor:
    model_id: str
    provider: str
    tier: ModelTier
    context_window: int = 128000
    max_thinking_budget: int = 0
    supports_thinking: bool = False
    api_key_name: str = "LOCUS_LLM_KEY"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "tier": self.tier.value if hasattr(self.tier, "value") else str(self.tier),
            "context_window": self.context_window,
            "max_thinking_budget": self.max_thinking_budget,
            "supports_thinking": self.supports_thinking,
            "api_key_name": self.api_key_name,
        }


@dataclass
class TurnEscalationRequest:
    task_type: str = "general"
    estimated_tokens: int = 1000
    complexity_score: float = 1.0
    is_sunday_synthesis: bool = False
    is_background: bool = False
    user_preferred_model: Optional[str] = None


@dataclass
class TurnEscalationDecision:
    model_id: str
    provider: str
    tier: ModelTier
    thinking_budget: int = 0
    reason: str = "Standard routine turn"
    api_key_name: str = "LOCUS_LLM_KEY"
    swapped: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "tier": self.tier.value if hasattr(self.tier, "value") else str(self.tier),
            "thinking_budget": self.thinking_budget,
            "reason": self.reason,
            "api_key_name": self.api_key_name,
            "swapped": self.swapped,
        }


class BaseModelManagementProvider(ABC):
    """Abstract base provider for model management and turn-by-turn escalation."""

    @abstractmethod
    def list_models(self) -> List[ModelDescriptor]:
        """Return catalog of available models and capabilities."""
        raise NotImplementedError

    @abstractmethod
    def resolve_turn_model(self, request: TurnEscalationRequest) -> TurnEscalationDecision:
        """Evaluate turn complexity and decide whether to escalate model."""
        raise NotImplementedError

    @abstractmethod
    def clamp_thinking_level(self, model_id: str, requested_budget: int) -> int:
        """Clamp thinking level to model's supported bounds."""
        raise NotImplementedError

    @abstractmethod
    def is_escalation_enabled(self) -> bool:
        """Check if automatic turn escalation is enabled in config."""
        raise NotImplementedError
