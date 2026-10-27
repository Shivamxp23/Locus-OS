"""
SPEC §29.1 lines 7435-7471: Error Classifier Provider (F-0065 / US-102).
Modular off-switches:
- locus.error_classifier.enabled (master toggle, returns 503 when off)
- locus.diagnostics.error_classifier.enabled (subsystem toggle)
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from typing import Any, Dict, Optional, Tuple

from sidecar import config

logger = logging.getLogger("locus.providers.error_classifier")


class BaseErrorClassifierProvider(ABC):
    """
    Abstract contract for Error Classifier Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def classify_error(self, error: Any) -> Dict[str, Any]:
        """Classify error into 7-category taxonomy and recovery action."""

    @abstractmethod
    def get_taxonomy(self) -> Dict[str, Any]:
        """Get taxonomy details and retry recovery strategies."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultErrorClassifierProvider(BaseErrorClassifierProvider):
    """
    Default provider wrapping ErrorClassifier with modular off-switch enforcement.
    """

    FEATURE_SWITCH = "locus.error_classifier.enabled"

    def __init__(self, classifier: Optional[Any] = None) -> None:
        if classifier is None:
            from sidecar.diagnostics.error_classifier import ErrorClassifier
            self.classifier = ErrorClassifier()
        else:
            self.classifier = classifier

    @property
    def name(self) -> str:
        return "default_error_classifier"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master toggle locus.error_classifier.enabled."""
        val = config.get(self.FEATURE_SWITCH)
        if val is not None and not config.is_enabled(self.FEATURE_SWITCH):
            return False, self.FEATURE_SWITCH
        return True, self.FEATURE_SWITCH

    def classify_error(self, error: Any) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        res = self.classifier.classify(error)
        out = res.to_dict()
        out["status_code"] = 200
        return out

    def get_taxonomy(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        tax = self.classifier.get_taxonomy()
        tax["status_code"] = 200
        return tax

    def get_status(self) -> Dict[str, Any]:
        enabled, switch_name = self.is_feature_enabled()
        if not enabled:
            return {
                "error": f"Feature {switch_name} is disabled",
                "status_code": 503,
                "disabled": switch_name,
            }

        st = self.classifier.get_status()
        st["provider_enabled"] = True
        st["provider_name"] = self.name
        st["status_code"] = 200
        return st
