"""
SPEC §9.9 lines 6143-6199:
Plugin LLM Provider Interface and Implementation (F-0034 / US-65).
Implements BasePluginLLMProvider and DefaultPluginLLMProvider with modular off-switches:
- locus.plugin_llm.enabled
- locus.plugins.auxiliary_llm.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.plugins.llm_bridge import (
    AuxiliaryTimeoutError,
    PluginLLMBridge,
    QuotaExceededError,
)

logger = logging.getLogger(__name__)


class BasePluginLLMProvider(ABC):
    """
    SPEC §9.9: Provider Interface: PluginLLMProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Plugin LLM Sandboxing is enabled."""
        raise NotImplementedError

    @abstractmethod
    def generate(
        self,
        plugin_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 500,
        temperature: float = 0.2,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        """Execute sandboxed secondary LLM call for given plugin."""
        raise NotImplementedError

    @abstractmethod
    def get_quota(self, plugin_id: str) -> Dict[str, Any]:
        """Get daily quota and token usage for plugin."""
        raise NotImplementedError

    @abstractmethod
    def reset_quota(self, plugin_id: str) -> Dict[str, Any]:
        """Reset daily token usage for plugin."""
        raise NotImplementedError

    @abstractmethod
    def get_all_usage(self) -> Dict[str, Any]:
        """Get aggregate usage metrics across all plugins."""
        raise NotImplementedError


class DefaultPluginLLMProvider(BasePluginLLMProvider):
    """
    SPEC §9.9: Default implementation of PluginLLMProvider.
    Sandboxed secondary LLM execution bridge with daily token quota and persistent tracking.
    """

    def __init__(self, usage_file_path: Optional[Path] = None):
        self.usage_file_path = usage_file_path or (Path.home() / ".locus" / "usage" / "plugins.json")
        self._bridges: Dict[str, PluginLLMBridge] = {}

    def is_available(self) -> bool:
        """Check modular off-switches locus.plugin_llm.enabled and locus.plugins.auxiliary_llm.enabled."""
        val1 = config.get("locus.plugin_llm.enabled")
        if val1 is not None and not config.is_enabled("locus.plugin_llm.enabled"):
            return False
        val2 = config.get("locus.plugins.auxiliary_llm.enabled")
        if val2 is not None and not config.is_enabled("locus.plugins.auxiliary_llm.enabled"):
            return False
        return True

    def _get_bridge(self, plugin_id: str) -> PluginLLMBridge:
        if plugin_id not in self._bridges:
            self._bridges[plugin_id] = PluginLLMBridge(
                plugin_id=plugin_id,
                usage_file_path=self.usage_file_path,
            )
        return self._bridges[plugin_id]

    def generate(
        self,
        plugin_id: str,
        messages: List[Dict[str, Any]],
        max_tokens: int = 500,
        temperature: float = 0.2,
        timeout: float = 15.0,
    ) -> Dict[str, Any]:
        """Execute sandboxed LLM invocation with quota enforcement and 15s fail-fast timeout."""
        bridge = self._get_bridge(plugin_id)
        try:
            content = bridge.call_plugin_llm(
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                timeout=timeout,
            )
            return {
                "status": "ok",
                "plugin_id": plugin_id,
                "content": content,
                "quota": bridge.get_quota_info(),
            }
        except QuotaExceededError as e:
            logger.warning("Quota exceeded for plugin %s: %s", plugin_id, e)
            return {
                "status": "error",
                "error": "quota_exceeded",
                "detail": str(e),
                "quota": bridge.get_quota_info(),
            }
        except AuxiliaryTimeoutError as e:
            logger.warning("Timeout during plugin LLM call for %s: %s", plugin_id, e)
            return {
                "status": "error",
                "error": "timeout",
                "detail": str(e),
                "quota": bridge.get_quota_info(),
            }
        except Exception as e:
            logger.exception("Unexpected error in plugin LLM call: %s", e)
            return {
                "status": "error",
                "error": "execution_failed",
                "detail": str(e),
                "quota": bridge.get_quota_info(),
            }

    def get_quota(self, plugin_id: str) -> Dict[str, Any]:
        """Return quota and token usage details."""
        bridge = self._get_bridge(plugin_id)
        return {
            "status": "ok",
            "quota": bridge.get_quota_info(),
        }

    def reset_quota(self, plugin_id: str) -> Dict[str, Any]:
        """Reset daily tokens used counter."""
        bridge = self._get_bridge(plugin_id)
        bridge.reset_daily_quota()
        return {
            "status": "ok",
            "message": f"Daily quota for plugin {plugin_id} reset successfully.",
            "quota": bridge.get_quota_info(),
        }

    def get_all_usage(self) -> Dict[str, Any]:
        """Return all tracked plugin usage records."""
        usage_data: Dict[str, Any] = {}
        if self.usage_file_path.is_file():
            try:
                usage_data = json.loads(self.usage_file_path.read_text(encoding="utf-8"))
            except Exception:
                usage_data = {}
        # Also include any in-memory bridges
        for pid, bridge in self._bridges.items():
            if pid not in usage_data:
                usage_data[pid] = bridge.get_quota_info()
        return {
            "status": "ok",
            "plugins": usage_data,
        }
