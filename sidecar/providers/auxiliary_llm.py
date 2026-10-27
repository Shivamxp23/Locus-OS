"""
SPEC §29.2 lines 7472-7500: Auxiliary LLM Client Provider (F-0124 / US-103).
Modular off-switches:
- locus.auxiliary_llm_client.enabled (master toggle, returns 503 when off)
- locus.auxiliary_client.enabled (subsystem toggle: when off, background tasks fall back to main model)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.providers.auxiliary_llm")


class BaseAuxiliaryLLMProvider(ABC):
    """
    Abstract contract for Auxiliary LLM Client Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Execute background generation with auxiliary client."""

    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """Get resolved auxiliary model configuration."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultAuxiliaryLLMProvider(BaseAuxiliaryLLMProvider):
    """
    Default provider wrapping AuxiliaryLLMClient with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.auxiliary_llm_client.enabled"

    def __init__(self, client: Optional[Any] = None) -> None:
        if client is None:
            from sidecar.diagnostics.auxiliary_client import AuxiliaryLLMClient
            self.client = AuxiliaryLLMClient()
        else:
            self.client = client

    @property
    def name(self) -> str:
        return "default_auxiliary_llm"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master toggle locus.auxiliary_llm_client.enabled."""
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, self.FEATURE_SWITCH

    def generate(self, prompt: str, system_prompt: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        from sidecar.diagnostics.auxiliary_client import AuxiliaryGenerationRequest
        req = AuxiliaryGenerationRequest(
            prompt=prompt,
            system_prompt=system_prompt,
            model=model,
        )
        res = self.client.generate(req)
        out = res.to_dict()
        out["status_code"] = 200
        return out

    def get_model_info(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        cfg = self.client.resolve_config()
        out = cfg.to_dict()
        out["status_code"] = 200
        return out

    def get_status(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        st = self.client.get_status()
        st["provider_enabled"] = True
        st["provider_name"] = self.name
        st["status_code"] = 200
        return st
