"""
SPEC §27.6 lines 7254-7304: Link Dump & Web Resource Logger Provider (F-0062 / US-99).
Modular off-switches:
- locus.link_dump_logger.enabled (master toggle, returns 503 when off)
- locus.ingestion.link_logger.enabled (subsystem toggle)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.providers.link_logger")


class BaseLinkDumpLoggerProvider(ABC):
    """
    Abstract contract for Link Dump & Web Resource Logger Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def process_link(
        self,
        url: str,
        user_commentary: str = "",
        html_content: Optional[str] = None,
        save_to_vault: bool = True,
        vault_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Scrape URL, generate summary takeaways, and archive to vault."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultLinkDumpLoggerProvider(BaseLinkDumpLoggerProvider):
    """
    Default provider wrapping LinkDumpLogger with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.link_dump_logger.enabled"

    def __init__(self, logger_instance: Optional[Any] = None) -> None:
        if logger_instance is None:
            from sidecar.ingestion.link_logger import LinkDumpLogger
            self.link_logger = LinkDumpLogger()
        else:
            self.link_logger = logger_instance

    @property
    def name(self) -> str:
        return "default_link_dump_logger"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """
        Check master toggle locus.link_dump_logger.enabled.
        """
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, self.FEATURE_SWITCH

    def process_link(
        self,
        url: str,
        user_commentary: str = "",
        html_content: Optional[str] = None,
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
        res = self.link_logger.process_link_dump(
            url=url,
            user_commentary=user_commentary,
            html_content=html_content,
            save_to_vault=save_to_vault,
            vault_root=custom_root,
        )

        out = res.to_dict()
        out["status_code"] = 200 if res.status == "SAVED" else 400
        return out

    def get_status(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        status = self.link_logger.get_status()
        status["provider_enabled"] = True
        status["provider_name"] = self.name
        status["status_code"] = 200
        return status
