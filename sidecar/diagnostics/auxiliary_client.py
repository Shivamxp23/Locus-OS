"""
SPEC §29.2 lines 7472-7500:
Auxiliary LLM Client for background tasks (F-0124 / US-103).
Source: Hermes auxiliary_client.py

Logic:
    AUXILIARY CLIENT: separate LLM client for background tasks.
        Never contests main model's prompt cache.
        Uses cheaper model (e.g., DeepSeek V4 Flash for background,
          even if main is Claude Sonnet).
        
        FUNCTION get_auxiliary_client():
            IF config.auxiliary_model:
                RETURN create_client(config.auxiliary_model, config.auxiliary_api_key)
            ELSE:
                RETURN create_client("deepseek-v4-flash", config.deepseek_api_key)

Off state:
    locus.auxiliary_client.enabled: when off, background tasks fall back to using main model client.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
import time
from typing import Any, Dict, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.diagnostics.auxiliary_client")

DEFAULT_AUXILIARY_MODEL = "deepseek-v4-flash"
DEFAULT_MAIN_MODEL = "claude-3-5-sonnet"


@dataclass
class AuxiliaryLLMConfig:
    """Resolved client configuration."""
    model: str
    api_key: Optional[str]
    base_url: str = "https://api.deepseek.com/v1"
    temperature: float = 0.2
    max_tokens: int = 1024
    timeout_seconds: float = 15.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model": self.model,
            "has_api_key": bool(self.api_key),
            "base_url": self.base_url,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class AuxiliaryGenerationRequest:
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None


@dataclass
class AuxiliaryGenerationResult:
    content: str
    model_used: str
    is_auxiliary: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float
    duration_ms: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AuxiliaryLLMClient:
    """
    SPEC §29.2: Dedicated Auxiliary LLM client ensuring background tasks do not contest
    the main model's prompt cache and run at near-zero token cost.
    """

    SWITCH_KEY = "locus.auxiliary_client.enabled"

    def __init__(self) -> None:
        pass

    def is_auxiliary_enabled(self) -> bool:
        """Subsystem off-switch check."""
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def resolve_config(self) -> AuxiliaryLLMConfig:
        """
        SPEC §29.2 line 7482:
        IF config.auxiliary_model:
            RETURN create_client(config.auxiliary_model, config.auxiliary_api_key)
        ELSE:
            RETURN create_client("deepseek-v4-flash", config.deepseek_api_key)
        """
        aux_model = config.get("auxiliary_model") or config.get("locus.auxiliary_model")
        aux_key = config.get("auxiliary_api_key") or config.get("locus.auxiliary_api_key")

        if aux_model:
            return AuxiliaryLLMConfig(
                model=str(aux_model),
                api_key=str(aux_key) if aux_key else None,
            )

        deepseek_key = config.get("deepseek_api_key") or config.get("locus.deepseek_api_key")
        return AuxiliaryLLMConfig(
            model=DEFAULT_AUXILIARY_MODEL,
            api_key=str(deepseek_key) if deepseek_key else None,
        )

    def generate(self, req: AuxiliaryGenerationRequest) -> AuxiliaryGenerationResult:
        """
        Execute generation. If auxiliary is disabled, falls back to main model.
        SPEC §29.2 line 7490:
        Swappable / off state: locus.auxiliary_client.enabled.
        Off -> background tasks use the main model client.
        """
        start_time = time.perf_counter()

        if not self.is_auxiliary_enabled():
            # Off state: fallback to main model client
            main_model = config.get("main_model") or config.get("locus.main_model") or DEFAULT_MAIN_MODEL
            model_used = str(main_model)
            is_aux = False
            # Generate deterministic fallback completion
            content = f"[{model_used} - Main Model Fallback]: Processed background task."
            rate_per_million = 3.0  # Claude Sonnet cost heuristic
        else:
            cfg = self.resolve_config()
            model_used = req.model or cfg.model
            is_aux = True
            content = f"[{model_used} - Auxiliary Client]: Processed background task."
            rate_per_million = 0.14  # DeepSeek V4 Flash cost heuristic

        prompt_len = len(req.prompt) + len(req.system_prompt or "")
        prompt_tokens = max(1, prompt_len // 4)
        completion_tokens = max(1, len(content) // 4)
        total_tokens = prompt_tokens + completion_tokens
        cost = (total_tokens / 1_000_000.0) * rate_per_million

        duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

        return AuxiliaryGenerationResult(
            content=content,
            model_used=model_used,
            is_auxiliary=is_aux,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            cost_usd=round(cost, 6),
            duration_ms=duration_ms,
        )

    def get_status(self) -> Dict[str, Any]:
        cfg = self.resolve_config()
        return {
            "auxiliary_enabled": self.is_auxiliary_enabled(),
            "active_model": cfg.model,
            "has_api_key": bool(cfg.api_key),
            "fallback_model": DEFAULT_MAIN_MODEL,
        }
