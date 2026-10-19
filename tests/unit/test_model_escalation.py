"""
Unit tests for Model Management & Escalation (SPEC §1.4, F-0004, US-23).
Verifies tiered model resolution, thinking level clamping, dynamic credential resolution,
and modular off-switch behavior.
"""
from __future__ import annotations

import pytest

from sidecar.model_escalation import ModelEscalationProvider
from sidecar.providers.model_manager import (
    ModelDescriptor,
    ModelTier,
    TurnEscalationDecision,
    TurnEscalationRequest,
)


def test_model_resolution_default_selection():
    """SPEC §1.4 line 485: "1. User selects model via config or CLI flag"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    models = provider.list_models()
    assert len(models) >= 3
    tier_map = {m.tier: m for m in models}
    assert ModelTier.STANDARD in tier_map
    assert ModelTier.REASONING in tier_map
    assert ModelTier.BACKGROUND in tier_map


def test_model_registry_resolution():
    """SPEC §1.4 line 486: "2. ModelRegistry resolves provider + model name"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    model = provider.get_model("google/gemini-2.5-pro")
    assert model is not None
    assert model.provider == "google"
    assert model.context_window == 1000000
    assert model.supports_thinking is True


def test_dynamic_api_key_resolution(monkeypatch):
    """SPEC §1.4 line 487: "3. API key resolved dynamically per call (for expiring tokens)"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    from sidecar import config
    monkeypatch.setattr(config, "get_env", lambda key, default=None: "sk-dynamic-key-12345" if key == "GEMINI_API_KEY" else default)
    key = provider.resolve_model_credentials("GEMINI_API_KEY")
    assert key == "sk-dynamic-key-12345"


def test_thinking_level_clamping():
    """SPEC §1.4 line 488: "4. Thinking level clamped to model's supported levels"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    # Gemini 2.5 Pro supports up to 32768
    clamped_high = provider.clamp_thinking_level("google/gemini-2.5-pro", 50000)
    assert clamped_high == 32768
    clamped_valid = provider.clamp_thinking_level("google/gemini-2.5-pro", 8192)
    assert clamped_valid == 8192
    # Standard DeepSeek model has no thinking support -> 0
    clamped_standard = provider.clamp_thinking_level("deepseek/deepseek-chat", 8192)
    assert clamped_standard == 0


def test_prepare_next_turn_model_swap():
    """SPEC §1.4 line 489: "5. prepareNextTurn() can swap model mid-conversation"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    req = TurnEscalationRequest(task_type="synthesis", estimated_tokens=80000, complexity_score=8.5)
    decision = provider.resolve_turn_model(req)
    assert decision.swapped is True
    assert decision.model_id == "google/gemini-2.5-pro"
    assert decision.tier == ModelTier.REASONING


def test_escalation_tier_standard_turn():
    """SPEC §1.4 line 492: "Standard turns: DeepSeek V4 Flash (cheapest available, ~$0.012/day)"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    req = TurnEscalationRequest(task_type="chat", estimated_tokens=150, complexity_score=2.0)
    decision = provider.resolve_turn_model(req)
    assert decision.tier == ModelTier.STANDARD
    assert decision.model_id == "deepseek/deepseek-chat"
    assert decision.swapped is False


def test_escalation_tier_complex_reasoning():
    """SPEC §1.4 line 493: "Complex reasoning / Sunday synthesis: Gemini 2.5 Pro (1M context)"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    req = TurnEscalationRequest(is_sunday_synthesis=True)
    decision = provider.resolve_turn_model(req)
    assert decision.tier == ModelTier.REASONING
    assert decision.model_id == "google/gemini-2.5-pro"
    assert "Sunday synthesis" in decision.reason


def test_escalation_tier_background_tasks():
    """SPEC §1.4 line 494: "Background tasks: auxiliary client (separate API key, cheapest model)"."""
    provider = ModelEscalationProvider(custom_config={"locus.model_management_escalation.enabled": True})
    req = TurnEscalationRequest(is_background=True)
    decision = provider.resolve_turn_model(req)
    assert decision.tier == ModelTier.BACKGROUND
    assert decision.api_key_name == "AUXILIARY_API_KEY"


def test_model_escalation_disabled_passthrough():
    """SPEC §1.4 line 500: "Off -> Locus uses a single model for all turns; no automatic escalation."."""
    # When escalation is disabled via config
    provider = ModelEscalationProvider(custom_config={
        "locus.model_management_escalation.enabled": True,
        "locus.models.escalation.enabled": False,
    })
    req = TurnEscalationRequest(is_sunday_synthesis=True, complexity_score=9.5)
    decision = provider.resolve_turn_model(req)
    assert decision.tier == ModelTier.STANDARD
    assert decision.swapped is False
    assert "disabled" in decision.reason
