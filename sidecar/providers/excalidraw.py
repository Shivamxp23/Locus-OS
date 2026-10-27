"""
SPEC §27.7 lines 7305-7378: Excalidraw MCP Skill / Diagram Generator Provider (F-0063 / US-100).
Modular off-switches:
- locus.tools.excalidraw.enabled (master toggle, returns 503 when off)
- locus.display.excalidraw.enabled (subsystem toggle)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.providers.excalidraw")


class BaseDiagramGeneratorProvider(ABC):
    """
    Abstract contract for Diagram Generator Provider (SPEC §27.7).
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def generate_diagram(
        self,
        system_spec: str,
        output_filename: str = "architecture_diagram",
        save_to_vault: bool = True,
        vault_root: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Synthesize Excalidraw diagram from architecture description."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


# Alias per SPEC adaptation: Provider Interface: DiagramGeneratorProvider
DiagramGeneratorProvider = BaseDiagramGeneratorProvider


class DefaultDiagramGeneratorProvider(BaseDiagramGeneratorProvider):
    """
    Default provider wrapping ExcalidrawDiagramBuilder with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.tools.excalidraw.enabled"

    def __init__(self, builder: Optional[Any] = None) -> None:
        if builder is None:
            from sidecar.display.excalidraw_builder import ExcalidrawDiagramBuilder
            self.builder = ExcalidrawDiagramBuilder()
        else:
            self.builder = builder

    @property
    def name(self) -> str:
        return "default_diagram_generator"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """
        Check master toggle locus.tools.excalidraw.enabled.
        """
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, self.FEATURE_SWITCH

    def generate_diagram(
        self,
        system_spec: str,
        output_filename: str = "architecture_diagram",
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
        res = self.builder.generate_diagram(
            system_spec=system_spec,
            output_filename=output_filename,
            save_to_vault=save_to_vault,
            vault_root=custom_root,
        )
        return res

    def get_status(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        status = self.builder.get_status()
        status["provider_enabled"] = True
        status["provider_name"] = self.name
        status["status_code"] = 200
        return status
