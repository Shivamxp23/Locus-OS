"""
Unit tests for Auxiliary LLM Client (F-0124 / US-103).
SPEC §29.2 lines 7472-7500.
"""
from __future__ import annotations

import pytest

from sidecar import config
from sidecar.diagnostics.auxiliary_client import (
    AuxiliaryGenerationRequest,
    AuxiliaryGenerationResult,
    AuxiliaryLLMClient,
    AuxiliaryLLMConfig,
    DEFAULT_AUXILIARY_MODEL,
    DEFAULT_MAIN_MODEL,
)
from sidecar.providers.auxiliary_llm import (
    BaseAuxiliaryLLMProvider,
    DefaultAuxiliaryLLMProvider,
)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.auxiliary_llm_client.enabled", True)
    config.set("locus.auxiliary_client.enabled", True)
    config.set("auxiliary_model", None)
    config.set("auxiliary_api_key", None)
    config.set("deepseek_api_key", "sk-test-deepseek")
    yield
    config.set("locus.auxiliary_llm_client.enabled", True)
    config.set("locus.auxiliary_client.enabled", True)
    config.set("auxiliary_model", None)
    config.set("auxiliary_api_key", None)
    config.set("deepseek_api_key", None)


def test_default_model_resolution():
    """SPEC §29.2 line 7484: 'ELSE: RETURN create_client(\"deepseek-v4-flash\", config.deepseek_api_key)'"""
    client = AuxiliaryLLMClient()
    cfg = client.resolve_config()
    assert cfg.model == "deepseek-v4-flash"
    assert cfg.api_key == "sk-test-deepseek"


def test_custom_model_resolution():
    """SPEC §29.2 line 7482: 'IF config.auxiliary_model: RETURN create_client(config.auxiliary_model, config.auxiliary_api_key)'"""
    config.set("auxiliary_model", "gemini-2.5-flash")
    config.set("auxiliary_api_key", "sk-custom-aux")

    client = AuxiliaryLLMClient()
    cfg = client.resolve_config()
    assert cfg.model == "gemini-2.5-flash"
    assert cfg.api_key == "sk-custom-aux"


def test_generate_auxiliary_success():
    """SPEC §29.2 line 7475: 'AUXILIARY CLIENT: separate LLM client for background tasks. Never contests main model prompt cache.'"""
    client = AuxiliaryLLMClient()
    req = AuxiliaryGenerationRequest(prompt="Summarize recent inbox captures", system_prompt="You are a concise indexer")

    res = client.generate(req)
    assert res.is_auxiliary is True
    assert res.model_used == DEFAULT_AUXILIARY_MODEL
    assert "Auxiliary Client" in res.content
    assert res.prompt_tokens > 0
    assert res.completion_tokens > 0
    assert res.total_tokens == res.prompt_tokens + res.completion_tokens
    assert res.cost_usd > 0.0


def test_generate_main_model_fallback():
    """SPEC §29.2 line 7490: 'Swappable / off state: locus.auxiliary_client.enabled. Off -> background tasks use the main model client.'"""
    client = AuxiliaryLLMClient()
    config.set("locus.auxiliary_client.enabled", False)

    req = AuxiliaryGenerationRequest(prompt="Generate daily recap")
    res = client.generate(req)
    assert res.is_auxiliary is False
    assert res.model_used == DEFAULT_MAIN_MODEL
    assert "Main Model Fallback" in res.content


def test_provider_modular_off_switch():
    """SPEC §29.2 line 7490: Master toggle locus.auxiliary_llm_client.enabled returns HTTP 503 when off."""
    provider = DefaultAuxiliaryLLMProvider()
    config.set("locus.auxiliary_llm_client.enabled", False)

    res_gen = provider.generate(prompt="Test background prompt")
    assert res_gen["status_code"] == 503
    assert res_gen["disabled"] == "locus.auxiliary_llm_client.enabled"

    res_mod = provider.get_model_info()
    assert res_mod["status_code"] == 503

    res_st = provider.get_status()
    assert res_st["status_code"] == 503


def test_provider_normal_delegation():
    """SPEC §29.2: Provider delegation when enabled."""
    provider = DefaultAuxiliaryLLMProvider()
    config.set("locus.auxiliary_llm_client.enabled", True)

    res_gen = provider.generate(prompt="Generate search tags", system_prompt="System prompt")
    assert res_gen["status_code"] == 200
    assert res_gen["is_auxiliary"] is True
    assert "deepseek" in res_gen["model_used"]

    res_mod = provider.get_model_info()
    assert res_mod["status_code"] == 200
    assert res_mod["model"] == DEFAULT_AUXILIARY_MODEL

    res_st = provider.get_status()
    assert res_st["status_code"] == 200
    assert res_st["provider_enabled"] is True
    assert res_st["provider_name"] == "default_auxiliary_llm"


def test_provider_polymorphism():
    """SPEC §29.2: BaseAuxiliaryLLMProvider polymorphic compliance."""
    class CustomAuxiliaryLLMProvider(BaseAuxiliaryLLMProvider):
        @property
        def name(self) -> str:
            return "custom_aux_llm"

        def is_feature_enabled(self):
            return True, ""

        def generate(self, prompt: str, system_prompt: str = None, model: str = None):
            return {"content": "custom content", "is_auxiliary": True, "status_code": 200}

        def get_model_info(self):
            return {"model": "custom-model", "status_code": 200}

        def get_status(self):
            return {"custom": True, "status_code": 200}

    prov = CustomAuxiliaryLLMProvider()
    assert prov.name == "custom_aux_llm"
    assert prov.generate("hello")["content"] == "custom content"
