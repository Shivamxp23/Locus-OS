"""
SPEC §25.13 lines 4883-4896: Review Cadence System Provider (F-0114 / US-91).
Modular off-switches returning HTTP 503:
- locus.review_cadence_system.enabled
- locus.life_os.reviews.enabled
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.life_os.reviews import (
    CADENCE_SCHEDULE_DEFAULTS,
    ReviewCadence,
    ReviewCadenceEngine,
    ReviewPrompt,
    ReviewResult,
)

logger = logging.getLogger("locus.providers.reviews")


class BaseReviewCadenceProvider(ABC):
    """Abstract contract for Review Cadence Provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switches."""

    @abstractmethod
    def generate_review(
        self, cadence: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate review output for cadence (daily standup, weekly retro, monthly deep)."""

    @abstractmethod
    def list_cadences(self) -> Dict[str, Any]:
        """List review cadences with schedules and enabled status."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultReviewCadenceProvider(BaseReviewCadenceProvider):
    """
    Default provider wrapping ReviewCadenceEngine with modular off-switch enforcement.
    """

    def __init__(self, engine: Optional[ReviewCadenceEngine] = None) -> None:
        self.engine = engine or ReviewCadenceEngine()

    @property
    def name(self) -> str:
        return "default_review_cadence_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        for switch in (
            "locus.review_cadence_system.enabled",
            "locus.life_os.reviews.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def generate_review(
        self, cadence: str, context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Review cadence system is disabled",
                "disabled": switch,
            }

        try:
            rc = ReviewCadence(cadence.lower())
        except ValueError:
            return {
                "status": "error",
                "detail": f"Invalid review cadence '{cadence}'. Expected one of: {[c.value for c in ReviewCadence]}",
            }

        # Check cadence-specific toggle
        c_enabled, c_switch = self.engine.is_cadence_enabled(rc)
        if not c_enabled:
            return {
                "status_code": 503,
                "detail": f"Review cadence '{cadence}' is disabled",
                "disabled": c_switch,
            }

        res = self.engine.generate_review(rc, context)
        return {
            "status": "ok",
            "review": res.to_dict(),
        }

    def list_cadences(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Review cadence system is disabled",
                "disabled": switch,
            }
        return {
            "status": "ok",
            "cadences": self.engine.list_cadences(),
        }

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {
                "status_code": 503,
                "detail": "Review cadence system is disabled",
                "disabled": switch,
            }
        return {
            "status": "ok",
            "provider": self.name,
            "enabled": True,
            "cadences": [c.value for c in ReviewCadence],
            "defaults": CADENCE_SCHEDULE_DEFAULTS,
        }


# Canonical alias
ReviewCadenceProvider = DefaultReviewCadenceProvider
