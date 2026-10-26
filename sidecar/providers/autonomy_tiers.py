"""
SPEC §13.4 lines 3308-3332:
Autonomy Tiers Provider Interface and Implementation (F-0108 / US-70).

Implements BaseAutonomyTiersProvider and DefaultAutonomyTiersProvider with modular off-switches:
- locus.autonomy_tiers.enabled
- locus.security.autonomy_tiers.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, List, Optional, Union

from sidecar.security.autonomy_tiers import (
    AutonomyTier,
    AutonomyTierManager,
    TierEvaluationDecision,
    ToolCategory,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseAutonomyTiersProvider(ABC):
    """
    SPEC §13.4: Provider Interface: AutonomyTiersProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Autonomy Tiers provider is enabled."""
        raise NotImplementedError

    @abstractmethod
    def get_tier(self) -> str:
        """Get the current active autonomy tier (readonly, supervised, full)."""
        raise NotImplementedError

    @abstractmethod
    def set_tier(self, tier: str) -> Dict[str, Any]:
        """Update active autonomy tier."""
        raise NotImplementedError

    @abstractmethod
    def classify_tool(self, tool_name: str, explicit_category: Optional[str] = None) -> Dict[str, Any]:
        """Classify a tool into read, write, terminal, or system."""
        raise NotImplementedError

    @abstractmethod
    def evaluate_tool(
        self,
        tool_name: str,
        has_approval: bool = False,
        category: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Evaluate whether a tool can execute under the active or specified tier."""
        raise NotImplementedError

    @abstractmethod
    def get_tiers_info(self) -> List[Dict[str, Any]]:
        """List available tiers and descriptions."""
        raise NotImplementedError


class DefaultAutonomyTiersProvider(BaseAutonomyTiersProvider):
    """
    SPEC §13.4: Default implementation of AutonomyTiersProvider.
    Reads active tier from runtime configuration (default: supervised),
    and enforces tier policies with approval requirements.
    """

    def __init__(self, initial_tier: Optional[str] = None):
        cfg_tier = initial_tier or config.get("locus.security.autonomy_tier") or config.get("locus.autonomy_tier")
        self.manager = AutonomyTierManager(initial_tier=cfg_tier or "supervised")

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.autonomy_tiers.enabled
        - locus.security.autonomy_tiers.enabled
        """
        v1 = config.get("locus.autonomy_tiers.enabled")
        if v1 is not None and not config.is_enabled("locus.autonomy_tiers.enabled"):
            return False

        v2 = config.get("locus.security.autonomy_tiers.enabled")
        if v2 is not None and not config.is_enabled("locus.security.autonomy_tiers.enabled"):
            return False

        return True

    def get_tier(self) -> str:
        # Check if config specifies a tier override
        cfg_tier = config.get("locus.security.autonomy_tier") or config.get("locus.autonomy_tier")
        if cfg_tier and str(cfg_tier).strip().lower() != self.manager.tier.value:
            self.manager.set_tier(str(cfg_tier))
        return self.manager.tier.value

    def set_tier(self, tier: str) -> Dict[str, Any]:
        new_tier = self.manager.set_tier(tier)
        return {
            "status": "ok",
            "tier": new_tier.value,
        }

    def classify_tool(self, tool_name: str, explicit_category: Optional[str] = None) -> Dict[str, Any]:
        cat = self.manager.classify_tool(tool_name=tool_name, explicit_category=explicit_category)
        return {
            "status": "ok",
            "tool_name": tool_name,
            "category": cat.value,
        }

    def evaluate_tool(
        self,
        tool_name: str,
        has_approval: bool = False,
        category: Optional[str] = None,
        tier: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Sync current configured tier if not overridden
        if not tier:
            cfg_tier = config.get("locus.security.autonomy_tier") or config.get("locus.autonomy_tier")
            if cfg_tier and str(cfg_tier).strip().lower() != self.manager.tier.value:
                self.manager.set_tier(str(cfg_tier))

        decision = self.manager.evaluate(
            tool_name=tool_name,
            has_approval=has_approval,
            custom_category=category,
            tier_override=tier,
        )
        return {
            "status": "ok",
            "decision": decision.to_dict(),
        }

    def get_tiers_info(self) -> List[Dict[str, Any]]:
        return self.manager.get_tiers_info()
