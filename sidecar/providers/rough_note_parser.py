"""
SPEC §27.5 lines 7192-7251: Rough Note Parser Provider (F-0061 / US-98).
Modular off-switches:
- locus.rough_note_parser.enabled (master toggle, returns 503 when off)
- locus.ingestion.rough_note_parser.enabled (subsystem toggle)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.providers.rough_note_parser")


class BaseRoughNoteParserProvider(ABC):
    """
    Abstract contract for Rough Note Parser Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def parse_note(
        self,
        raw_text: str,
        source: Optional[str] = None,
        save_to_vault: bool = True,
        vault_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Parse raw stream into structured note and save to vault."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultRoughNoteParserProvider(BaseRoughNoteParserProvider):
    """
    Default provider wrapping RoughNoteParser with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.rough_note_parser.enabled"

    def __init__(self, parser: Optional[Any] = None) -> None:
        if parser is None:
            from sidecar.ingestion.rough_note_parser import RoughNoteParser
            self.parser = RoughNoteParser()
        else:
            self.parser = parser

    @property
    def name(self) -> str:
        return "default_rough_note_parser"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """
        Check master toggle locus.rough_note_parser.enabled.
        """
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, self.FEATURE_SWITCH

    def parse_note(
        self,
        raw_text: str,
        source: Optional[str] = None,
        save_to_vault: bool = True,
        vault_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        custom_root = Path(vault_root).resolve() if vault_root else None
        res = self.parser.parse_rough_note_stream(
            raw_text=raw_text,
            source=source,
            save_to_vault=save_to_vault,
            vault_root=custom_root,
        )

        out = res.to_dict()
        out["status_code"] = 200 if res.success else 400
        return out

    def get_status(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        status = self.parser.get_status()
        status["provider_enabled"] = True
        status["provider_name"] = self.name
        status["status_code"] = 200
        return status
