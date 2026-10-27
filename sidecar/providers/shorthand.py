"""
SPEC §27.3 lines 7115-7151: LOCUS_SHORTHAND 4× Text Compressor Provider (F-0122 / US-96).
Modular off-switches:
- locus.locus_shorthand_4_text_compressor.enabled (returns HTTP 503 when off)
- locus.compression.shorthand.enabled (subsystem toggle; when off, returns uncompressed text)
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.compression.shorthand import (
    LocusShorthandCompressor,
    ShorthandCompressionResult,
)

logger = logging.getLogger("locus.providers.shorthand")


class BaseShorthandCompressorProvider(ABC):
    """
    Abstract contract for LOCUS_SHORTHAND 4× Text Compressor Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def compress(self, text: str, strip_articles: bool = True) -> Dict[str, Any]:
        """Compress text using LOCUS_SHORTHAND regex pipeline."""

    @abstractmethod
    def decompress(self, text: str) -> Dict[str, Any]:
        """Decompress/expand shorthand tokens back to human-readable form."""

    @abstractmethod
    def compress_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Compress behavioral event into compact event schema."""

    @abstractmethod
    def get_decoder_dictionary(self) -> Dict[str, Any]:
        """Return decoder dictionary for system prompt prepending."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultShorthandCompressorProvider(BaseShorthandCompressorProvider):
    """
    Default provider wrapping LocusShorthandCompressor with modular off-switch enforcement.
    """

    def __init__(self, compressor: Optional[LocusShorthandCompressor] = None) -> None:
        self.compressor = compressor or LocusShorthandCompressor()

    @property
    def name(self) -> str:
        return "default_shorthand_compressor_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        switch = "locus.locus_shorthand_4_text_compressor.enabled"
        val = config.get(switch)
        if val is not None and not config.is_enabled(switch):
            return False, switch
        return True, ""

    def compress(self, text: str, strip_articles: bool = True) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                "disabled": switch,
            }

        res: ShorthandCompressionResult = self.compressor.compress(
            text=text,
            strip_articles=strip_articles,
        )
        return res.to_dict()

    def decompress(self, text: str) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                "disabled": switch,
            }

        decompressed = self.compressor.decompress(text=text)
        return {
            "compressed_text": text,
            "decompressed_text": decompressed,
        }

    def compress_event(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                "disabled": switch,
            }

        encoded = self.compressor.compress_event(event_type=event_type, data=data)
        return {
            "event_type": event_type,
            "raw_data": data,
            "compressed_event": encoded,
        }

    def get_decoder_dictionary(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                "disabled": switch,
            }

        return {
            "decoder": self.compressor.get_decoder_dictionary(),
            "count": len(self.compressor.get_decoder_dictionary()),
        }

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        subsystem_enabled = self.compressor.is_shorthand_enabled()

        if not enabled:
            return {
                "status_code": 503,
                "detail": "LOCUS_SHORTHAND 4x text compressor is disabled",
                "disabled": switch,
                "feature_enabled": False,
                "subsystem_enabled": subsystem_enabled,
            }

        return {
            "feature_enabled": True,
            "subsystem_enabled": subsystem_enabled,
            "provider": self.name,
            "dictionary_size": len(self.compressor.get_decoder_dictionary()),
        }
