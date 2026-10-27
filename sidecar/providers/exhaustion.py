"""
SPEC §25.10 lines 4759-4777: Exhaustion Predictor Provider (F-0112 / US-88).
Modular off-switches returning HTTP 503:
- locus.exhaustion_predictor.enabled
- locus.life_os.exhaustion.enabled
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple

from sidecar import config
from sidecar.life_os.exhaustion import (
    ExhaustionMetrics,
    ExhaustionPrediction,
    ExhaustionPredictor,
)

logger = logging.getLogger("locus.providers.exhaustion")


class BaseExhaustionPredictorProvider(ABC):
    """Abstract contract for exhaustion prediction provider."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check modular off-switches."""

    @abstractmethod
    def predict_exhaustion(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Predict 24h DCS drop and evaluate pre-emptive survival recommendation."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Diagnostic state."""


class DefaultExhaustionPredictorProvider(BaseExhaustionPredictorProvider):
    """
    Default provider wrapping ExhaustionPredictor with modular off-switch enforcement.
    """

    def __init__(self, predictor: Optional[ExhaustionPredictor] = None) -> None:
        self.predictor = predictor or ExhaustionPredictor()

    @property
    def name(self) -> str:
        return "default_exhaustion_predictor_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        for switch in (
            "locus.exhaustion_predictor.enabled",
            "locus.life_os.exhaustion.enabled",
        ):
            val = config.get(switch)
            if val is not None and not config.is_enabled(switch):
                return False, switch
        return True, ""

    def predict_exhaustion(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}

        input_metrics = ExhaustionMetrics(
            consecutive_high_d_tasks=int(metrics.get("consecutive_high_d_tasks", 0)),
            sleep_deficit_hours=float(metrics.get("sleep_deficit_hours", 0.0)),
            stress_trend=float(metrics.get("stress_trend", 0.0)),
            current_dcs=float(metrics.get("current_dcs", 6.0)),
        )

        prediction = self.predictor.predict(input_metrics)
        return {"status": "ok", "prediction": prediction.to_dict()}

    def get_status(self) -> Dict[str, Any]:
        enabled, switch = self.is_feature_enabled()
        if not enabled:
            return {"error": "feature_disabled", "disabled": switch, "status_code": 503}
        return {
            "status": "ok",
            "provider": self.name,
            "threshold": 2.0,
            "active": True,
        }


# Alias for backward compatibility
ExhaustionPredictorProvider = DefaultExhaustionPredictorProvider
