"""
Headroom CCR Compression Provider (SPEC §4.17: Token Compression (Headroom CCR)).
Implements CompressionProvider interface for Stage 5 Context Forge and session compression.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.context.headroom_pipeline import (
    CompressConfig,
    CompressResult,
    HeadroomPipeline,
)

logger = logging.getLogger(__name__)


class CompressionProvider(ABC):
    """
    SPEC §4.17 line 707:
    Provider Interface: CompressionProvider
    """

    @abstractmethod
    def compress(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        config: Optional[CompressConfig] = None,
    ) -> CompressResult:
        """Compress messages list using pipeline."""
        raise NotImplementedError

    @abstractmethod
    def retrieve(self, cache_key: str) -> Optional[str]:
        """Retrieve original content by CCR key."""
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check if Headroom CCR is enabled."""
        raise NotImplementedError

    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """Return provider configuration dictionary."""
        raise NotImplementedError


class DefaultHeadroomCCRProvider(CompressionProvider):
    """
    Default implementation of CompressionProvider using HeadroomPipeline.
    Modular off-switch: locus.headroom_ccr.enabled (default: true) and locus.compression.enabled (default: true).
    """

    def __init__(self, pipeline: Optional[HeadroomPipeline] = None) -> None:
        self.pipeline = pipeline or HeadroomPipeline()

    def is_enabled(self) -> bool:
        val1 = config.get("locus.headroom_ccr.enabled")
        if val1 is not None and not config.is_enabled("locus.headroom_ccr.enabled"):
            return False
        val2 = config.get("locus.compression.enabled")
        if val2 is not None and not config.is_enabled("locus.compression.enabled"):
            return False
        return True

    def compress(
        self,
        messages: List[Dict[str, Any]],
        model: Optional[str] = None,
        config: Optional[CompressConfig] = None,
    ) -> CompressResult:
        return self.pipeline.compress(messages=messages, model=model, config=config)

    def retrieve(self, cache_key: str) -> Optional[str]:
        return self.pipeline.headroom_retrieve(cache_key)

    def get_config(self) -> Dict[str, Any]:
        return {
            "provider": "headroom-ccr",
            "enabled": self.is_enabled(),
            "protect_recent": self.pipeline.config.protect_recent,
            "min_tokens_to_compress": self.pipeline.config.min_tokens_to_compress,
            "compress_user_messages": self.pipeline.config.compress_user_messages,
            "target_ratio": self.pipeline.config.target_ratio,
            "frozen_message_count": self.pipeline.config.frozen_message_count,
        }
