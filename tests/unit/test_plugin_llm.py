"""
SPEC §9.9 lines 6143-6199:
Unit tests for Plugin LLM Sandboxing & Auxiliary Bridge (F-0034 / US-65).
"""
import json
from pathlib import Path
import pytest
import time
from typing import Any, Dict, List

import sidecar.config as config
from sidecar.plugins.llm_bridge import (
    AuxiliaryClient,
    AuxiliaryClientPool,
    AuxiliaryResponse,
    AuxiliaryTimeoutError,
    DefaultAuxiliaryClient,
    PluginLLMBridge,
    QuotaExceededError,
    TokenUsage,
)
from sidecar.providers.plugin_llm import (
    BasePluginLLMProvider,
    DefaultPluginLLMProvider,
)


def test_plugin_llm_within_quota(tmp_path: Path):
    """SPEC §9.9 line 6165: "FUNCTION call_plugin_llm(messages: List[Dict], max_tokens: int = 500, temperature: float = 0.2) -> string" """
    usage_file = tmp_path / "plugins.json"
    bridge = PluginLLMBridge(
        plugin_id="excalidraw-skill",
        token_quota_daily=1000,
        usage_file_path=usage_file,
    )
    assert bridge.tokens_used_today == 0

    messages = [{"role": "user", "content": "Generate excalidraw diagram coordinates"}]
    content = bridge.call_plugin_llm(messages, max_tokens=100)

    assert "[auxiliary-flash-v1]" in content
    assert bridge.tokens_used_today > 0
    assert bridge.tokens_used_today <= 1000
    info = bridge.get_quota_info()
    assert info["quota_exceeded"] is False
    assert info["tokens_remaining"] == 1000 - bridge.tokens_used_today


def test_plugin_llm_quota_exceeded(tmp_path: Path):
    """SPEC §9.9 line 6168: "1. Quota Enforcement: IF self.tokens_used_today + max_tokens > self.token_quota_daily: RAISE QuotaExceededError" """
    usage_file = tmp_path / "plugins.json"
    bridge = PluginLLMBridge(
        plugin_id="rough-note-parser",
        token_quota_daily=200,
        usage_file_path=usage_file,
    )
    bridge.tokens_used_today = 150

    messages = [{"role": "user", "content": "Parse this extensive note"}]
    with pytest.raises(QuotaExceededError) as exc_info:
        # Requesting 100 tokens when 150 + 100 > 200 daily quota
        bridge.call_plugin_llm(messages, max_tokens=100)
    assert "exceeded daily token limit" in str(exc_info.value)


def test_plugin_llm_daily_quota_reset(tmp_path: Path):
    """SPEC §9.9 line 6188: "Repo vs .locus: code in locus-os (repo); per-plugin token usage tracked in .locus/usage/plugins.json" """
    usage_file = tmp_path / "plugins.json"
    bridge = PluginLLMBridge(
        plugin_id="link-dump-logger",
        token_quota_daily=500,
        usage_file_path=usage_file,
    )
    bridge.tokens_used_today = 450
    bridge.reset_daily_quota()

    assert bridge.tokens_used_today == 0
    info = bridge.get_quota_info()
    assert info["tokens_remaining"] == 500
    assert info["tokens_used_today"] == 0


def test_plugin_llm_auxiliary_isolation_and_response(tmp_path: Path):
    """SPEC §9.9 line 6176: "3. Isolated Generation (Zero collision with main agent conversation cache)" """
    usage_file = tmp_path / "plugins.json"

    class IsolatedMockAuxClient(AuxiliaryClient):
        def generate(
            self,
            messages: List[Dict[str, Any]],
            max_tokens: int = 500,
            temperature: float = 0.2,
            timeout: float = 15.0,
        ) -> AuxiliaryResponse:
            return AuxiliaryResponse(
                content="Mocked isolated extraction output",
                usage=TokenUsage(prompt_tokens=15, completion_tokens=10, total_tokens=25),
                model="mock-deepseek-flash",
            )

    bridge = PluginLLMBridge(
        plugin_id="isolated-plugin",
        token_quota_daily=5000,
        usage_file_path=usage_file,
        aux_client=IsolatedMockAuxClient(),
    )
    result = bridge.call_plugin_llm([{"role": "user", "content": "isolate me"}])
    assert result == "Mocked isolated extraction output"
    assert bridge.tokens_used_today == 25


def test_plugin_llm_timeout_fail_fast():
    """SPEC §9.9 line 6194: "STEAL VERBATIM: The per-plugin token quota enforcement, isolated auxiliary client invocation, and fail-fast 15s timeout." """
    slow_client = DefaultAuxiliaryClient(artificial_delay=0.2)
    with pytest.raises(AuxiliaryTimeoutError) as exc_info:
        slow_client.generate(
            messages=[{"role": "user", "content": "slow task"}],
            timeout=0.05,
        )
    assert "timed out" in str(exc_info.value)


def test_plugin_llm_persistent_usage_file(tmp_path: Path):
    """SPEC §9.9 line 6188: "Repo vs .locus: code in locus-os (repo); per-plugin token usage tracked in .locus/usage/plugins.json" """
    usage_file = tmp_path / "test_usage.json"
    bridge1 = PluginLLMBridge(
        plugin_id="plugin-alpha",
        token_quota_daily=2000,
        usage_file_path=usage_file,
    )
    bridge1.call_plugin_llm([{"role": "user", "content": "hello world"}], max_tokens=50)

    assert usage_file.is_file()
    data = json.loads(usage_file.read_text(encoding="utf-8"))
    assert "plugin-alpha" in data
    assert data["plugin-alpha"]["tokens_used_today"] > 0

    # Instantiate new bridge instance pointing to same file
    bridge2 = PluginLLMBridge(
        plugin_id="plugin-alpha",
        token_quota_daily=2000,
        usage_file_path=usage_file,
    )
    assert bridge2.tokens_used_today == bridge1.tokens_used_today


def test_plugin_llm_provider_is_available(monkeypatch, tmp_path: Path):
    """SPEC §9.9 line 6189: "Swappable / off state: locus.plugins.auxiliary_llm.enabled. Off -> plugins cannot make independent LLM calls." """
    usage_file = tmp_path / "provider_usage.json"
    provider = DefaultPluginLLMProvider(usage_file_path=usage_file)

    monkeypatch.setattr(config, "get", lambda k: True)
    monkeypatch.setattr(config, "is_enabled", lambda k: True)
    assert provider.is_available() is True

    # Test locus.plugin_llm.enabled = False
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.plugin_llm.enabled" else True)
    assert provider.is_available() is False

    # Test locus.plugins.auxiliary_llm.enabled = False
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.plugins.auxiliary_llm.enabled" else True)
    assert provider.is_available() is False


def test_plugin_llm_provider_swappable():
    """SPEC §9.9 line 6187: "Provider Interface: PluginLLMProvider" """
    class CustomSwappedProvider(BasePluginLLMProvider):
        def is_available(self) -> bool:
            return True

        def generate(self, plugin_id, messages, max_tokens=500, temperature=0.2, timeout=15.0):
            return {"status": "ok", "plugin_id": plugin_id, "content": "swapped"}

        def get_quota(self, plugin_id):
            return {"status": "ok", "quota": {"tokens_remaining": 9999}}

        def reset_quota(self, plugin_id):
            return {"status": "ok", "reset": True}

        def get_all_usage(self):
            return {"status": "ok", "plugins": {}}

    provider: BasePluginLLMProvider = CustomSwappedProvider()
    assert provider.is_available() is True
    res = provider.generate("test-pid", [{"role": "user", "content": "hi"}])
    assert res["content"] == "swapped"
