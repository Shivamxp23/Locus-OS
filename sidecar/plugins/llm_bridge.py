"""
SPEC §9.9 lines 6143-6199:
Plugin LLM Sandboxing & Auxiliary Bridge (F-0034 / US-65).
Sandboxed secondary LLM execution bridge for extensions; protects main model's prompt cache and context.
Provides token quota enforcement, auxiliary client pool isolation, and persistent usage tracking.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from datetime import date, datetime
import json
import logging
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class QuotaExceededError(Exception):
    """SPEC §9.9 line 6171: Raised when a plugin exceeds its daily token quota."""
    pass


class AuxiliaryTimeoutError(Exception):
    """SPEC §9.9 line 6194: Raised when auxiliary LLM call exceeds fail-fast timeout (15.0s)."""
    pass


@dataclass
class TokenUsage:
    """SPEC §9.9 lines 6180-6184: Token usage tracking."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return asdict(self)


@dataclass
class AuxiliaryResponse:
    """SPEC §9.9 lines 6176-6185: Isolated generation response."""
    content: str
    usage: TokenUsage
    model: str = "auxiliary-flash-v1"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "usage": self.usage.to_dict(),
            "model": self.model,
        }


class AuxiliaryClient(ABC):
    """
    SPEC §9.9 lines 6172-6179:
    Auxiliary model client interface (Cheap / Fast, e.g. DeepSeek V4 Flash or Gemini 2.5 Flash).
    Isolated generation with zero collision with main agent conversation cache.
    """

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 500,
        temperature: float = 0.2,
        timeout: float = 15.0,
    ) -> AuxiliaryResponse:
        """Isolated generation with fail-fast timeout."""
        raise NotImplementedError


class DefaultAuxiliaryClient(AuxiliaryClient):
    """
    SPEC §9.9 lines 6172-6179:
    Default auxiliary model client implementation for plugin LLM execution.
    """

    def __init__(self, model_name: str = "auxiliary-flash-v1", artificial_delay: float = 0.0):
        self.model_name = model_name
        self.artificial_delay = artificial_delay

    def generate(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 500,
        temperature: float = 0.2,
        timeout: float = 15.0,
    ) -> AuxiliaryResponse:
        start_time = time.time()
        if self.artificial_delay > 0:
            if self.artificial_delay > timeout:
                time.sleep(timeout)
                raise AuxiliaryTimeoutError(f"Auxiliary generation timed out after {timeout:.1f}s")
            time.sleep(self.artificial_delay)

        elapsed = time.time() - start_time
        if elapsed > timeout:
            raise AuxiliaryTimeoutError(f"Auxiliary generation timed out after {timeout:.1f}s")

        # Estimate simple token counts from input messages and response
        input_text = " ".join(str(m.get("content", "")) for m in messages)
        prompt_tokens = max(1, len(input_text.split()))
        
        # Deterministic synthetic response for secondary transformations
        summary_prefix = f"[{self.model_name}]"
        if messages:
            last_msg = messages[-1].get("content", "")
            completion_text = f"{summary_prefix} Transformed: {last_msg[:60]}"
        else:
            completion_text = f"{summary_prefix} Processed empty input"

        completion_tokens = min(max_tokens, max(1, len(completion_text.split())))
        total_tokens = prompt_tokens + completion_tokens

        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
        )

        return AuxiliaryResponse(
            content=completion_text,
            usage=usage,
            model=self.model_name,
        )


class AuxiliaryClientPool:
    """
    SPEC §9.9 line 6173:
    Pool of auxiliary clients mapped by task name (e.g. 'plugin_execution').
    """

    _instances: Dict[str, AuxiliaryClient] = {}

    @classmethod
    def get_instance(cls, task: str = "plugin_execution") -> AuxiliaryClient:
        """Get or initialize auxiliary client for a given task."""
        if task not in cls._instances:
            cls._instances[task] = DefaultAuxiliaryClient()
        return cls._instances[task]

    @classmethod
    def register_instance(cls, task: str, client: AuxiliaryClient) -> None:
        """Register custom client implementation for a given task."""
        cls._instances[task] = client

    @classmethod
    def reset_pool(cls) -> None:
        """Reset registry to default instances."""
        cls._instances.clear()


class PluginLLMBridge:
    """
    SPEC §9.9 lines 6160-6187:
    Sandboxed secondary LLM execution bridge for extensions; protects main model's prompt cache and context.
    Tracks per-plugin daily token quota and records usage in .locus/usage/plugins.json.
    """

    DEFAULT_DAILY_QUOTA: int = 50000

    def __init__(
        self,
        plugin_id: str,
        token_quota_daily: int = DEFAULT_DAILY_QUOTA,
        usage_file_path: Optional[Path] = None,
        aux_client: Optional[AuxiliaryClient] = None,
    ):
        self.plugin_id = str(plugin_id)
        self.token_quota_daily = int(token_quota_daily)
        self.tokens_used_today: int = 0
        self.last_reset_date: str = date.today().isoformat()
        self.usage_file_path = usage_file_path or (Path.home() / ".locus" / "usage" / "plugins.json")
        self._custom_aux_client = aux_client
        self._load_usage()

    def _load_usage(self) -> None:
        """Load stored usage metrics from .locus/usage/plugins.json if present."""
        try:
            if self.usage_file_path.is_file():
                raw = json.loads(self.usage_file_path.read_text(encoding="utf-8"))
                plugin_data = raw.get(self.plugin_id, {})
                today = date.today().isoformat()
                if plugin_data.get("last_reset_date") == today:
                    self.tokens_used_today = int(plugin_data.get("tokens_used_today", 0))
                    self.last_reset_date = today
                else:
                    # New day: automatically roll over daily counter
                    self.tokens_used_today = 0
                    self.last_reset_date = today
                    self._save_usage()
        except Exception as e:
            logger.warning("Failed to load plugin usage from %s: %s", self.usage_file_path, e)
            self.tokens_used_today = 0

    def _save_usage(self) -> None:
        """Save stored usage metrics to .locus/usage/plugins.json."""
        try:
            data: Dict[str, Any] = {}
            if self.usage_file_path.is_file():
                try:
                    data = json.loads(self.usage_file_path.read_text(encoding="utf-8"))
                except Exception:
                    data = {}

            data[self.plugin_id] = {
                "plugin_id": self.plugin_id,
                "token_quota_daily": self.token_quota_daily,
                "tokens_used_today": self.tokens_used_today,
                "last_reset_date": self.last_reset_date,
                "updated_at": datetime.now().isoformat(),
            }

            self.usage_file_path.parent.mkdir(parents=True, exist_ok=True)
            self.usage_file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as e:
            logger.warning("Failed to save plugin usage to %s: %s", self.usage_file_path, e)

    def call_plugin_llm(
        self,
        messages: List[Dict[str, Any]],
        max_tokens: int = 500,
        temperature: float = 0.2,
        timeout: float = 15.0,
    ) -> str:
        """
        SPEC §9.9 lines 6165-6187:
        1. Quota Enforcement
        2. Fetch Auxiliary Model (Cheap / Fast)
        3. Isolated Generation (Zero collision with main agent conversation cache)
        4. Record Usage
        """
        today = date.today().isoformat()
        if self.last_reset_date != today:
            self.tokens_used_today = 0
            self.last_reset_date = today

        # 1. Quota Enforcement
        if self.tokens_used_today + max_tokens > self.token_quota_daily:
            raise QuotaExceededError(
                f"Plugin {self.plugin_id} exceeded daily token limit ({self.tokens_used_today}/{self.token_quota_daily})."
            )

        # 2. Fetch Auxiliary Model (Cheap / Fast)
        if self._custom_aux_client:
            aux_client = self._custom_aux_client
        else:
            aux_client = AuxiliaryClientPool.get_instance(task="plugin_execution")

        # 3. Isolated Generation (Zero collision with main agent conversation cache)
        response = aux_client.generate(
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout=timeout,
        )

        # 4. Record Usage
        actual_tokens = response.usage.total_tokens
        self.tokens_used_today += actual_tokens
        self._save_usage()

        return response.content

    def reset_daily_quota(self) -> None:
        """Reset daily tokens used counter to 0."""
        self.tokens_used_today = 0
        self.last_reset_date = date.today().isoformat()
        self._save_usage()

    def get_quota_info(self) -> Dict[str, Any]:
        """SPEC §9.9: Return token quota and usage status."""
        today = date.today().isoformat()
        if self.last_reset_date != today:
            self.tokens_used_today = 0
            self.last_reset_date = today
            self._save_usage()

        remaining = max(0, self.token_quota_daily - self.tokens_used_today)
        return {
            "plugin_id": self.plugin_id,
            "token_quota_daily": self.token_quota_daily,
            "tokens_used_today": self.tokens_used_today,
            "tokens_remaining": remaining,
            "last_reset_date": self.last_reset_date,
            "quota_exceeded": self.tokens_used_today >= self.token_quota_daily,
        }
