"""
SPEC §9.2 lines 6000-6056:
Skill Marketplace Provider Interface and Implementation (F-0119 / US-63).
Implements BaseSkillMarketplaceProvider and DefaultSkillMarketplaceProvider with modular off-switch.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.skills.marketplace import (
    INDEX_URLS,
    SkillManifest,
    SkillMarketplaceEngine,
)

logger = logging.getLogger(__name__)


class BaseSkillMarketplaceProvider(ABC):
    """
    SPEC §9.2: Provider Interface for Multi-Source Skill Marketplace.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if skill marketplace is enabled."""
        raise NotImplementedError

    @abstractmethod
    def get_manifest(self, source: str, skill_name: str) -> Dict[str, Any]:
        """Fetch remote manifest for skill."""
        raise NotImplementedError

    @abstractmethod
    def validate_prerequisites(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate environment variable prerequisites."""
        raise NotImplementedError

    @abstractmethod
    def install_skill(self, source: str, skill_name: str) -> Dict[str, Any]:
        """Install skill bundle from remote marketplace."""
        raise NotImplementedError

    @abstractmethod
    def list_installed(self) -> List[Dict[str, Any]]:
        """List currently installed skills."""
        raise NotImplementedError

    @abstractmethod
    def get_sources(self) -> Dict[str, str]:
        """List supported marketplace sources and root index URLs."""
        raise NotImplementedError


class DefaultSkillMarketplaceProvider(BaseSkillMarketplaceProvider):
    """
    Default implementation of SkillMarketplaceProvider.
    Off-switch: locus.skill_system_multi_source_marketplace.enabled (default: true).
    Secondary off-switch: locus.skills.marketplace.enabled (default: true).
    Off-state: endpoints return HTTP 503.
    """

    def __init__(self, engine: Optional[SkillMarketplaceEngine] = None) -> None:
        self.engine = engine or SkillMarketplaceEngine()

    def is_available(self) -> bool:
        """SPEC §9.2: Modular off-switch check."""
        val1 = config.get("locus.skill_system_multi_source_marketplace.enabled")
        if val1 is not None and not config.is_enabled("locus.skill_system_multi_source_marketplace.enabled"):
            return False
        val2 = config.get("locus.skills.marketplace.enabled")
        if val2 is not None and not config.is_enabled("locus.skills.marketplace.enabled"):
            return False
        return True

    def get_sources(self) -> Dict[str, str]:
        if not self.is_available():
            raise RuntimeError("SkillMarketplaceProvider is disabled via config")
        return dict(INDEX_URLS)

    def get_manifest(self, source: str, skill_name: str) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("SkillMarketplaceProvider is disabled via config")
        manifest = self.engine.fetch_manifest(source, skill_name)
        return manifest.to_dict()

    def validate_prerequisites(self, manifest_data: Dict[str, Any]) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("SkillMarketplaceProvider is disabled via config")
        manifest = SkillManifest.from_dict(manifest_data)
        return self.engine.validate_prerequisites(manifest)

    def install_skill(self, source: str, skill_name: str) -> Dict[str, Any]:
        if not self.is_available():
            raise RuntimeError("SkillMarketplaceProvider is disabled via config")
        manifest = self.engine.fetch_manifest(source, skill_name)
        prereqs = self.engine.validate_prerequisites(manifest)
        success = self.engine.install_skill_from_marketplace(source, skill_name, manifest_override=manifest)
        return {
            "success": success,
            "source": source,
            "skill_name": skill_name,
            "manifest": manifest.to_dict(),
            "prerequisites": prereqs,
        }

    def list_installed(self) -> List[Dict[str, Any]]:
        if not self.is_available():
            raise RuntimeError("SkillMarketplaceProvider is disabled via config")
        return self.engine.list_installed_skills()
