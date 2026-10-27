"""
SPEC §25.10 lines 4759-4777: Unit tests for Exhaustion Predictor (F-0112 / US-88).
Tests:
- Forecast of predicted DCS drop based on consecutive high-D tasks, sleep deficit, and stress trend
- Triggering of pre-emptive SURVIVAL mode recommendation when predicted drop > 2.0 within 24h
- Maintenance of standard mode when drop <= 2.0
- Swappable provider interface and modular HTTP 503 off-switches
"""
from __future__ import annotations

from typing import Any, Dict

import pytest

import sidecar.config as config
from sidecar.life_os.exhaustion import (
    ExhaustionMetrics,
    ExhaustionPrediction,
    ExhaustionPredictor,
)
from sidecar.providers.exhaustion import (
    BaseExhaustionPredictorProvider,
    DefaultExhaustionPredictorProvider,
)


def test_exhaustion_metrics_calculation() -> None:
    """SPEC §25.10 line 4768: "EXHAUSTION PREDICTOR: monitors consecutive high-D tasks, sleep deficit, and stress trend." """
    predictor = ExhaustionPredictor()

    # consecutive_high_d = 2 (* 0.45 = 0.90), sleep_deficit = 1.0 (* 0.65 = 0.65), stress = 2.0 (* 0.25 = 0.50) -> sum = 2.05
    drop = predictor.calculate_predicted_dcs_drop(
        consecutive_high_d=2,
        sleep_deficit_hours=1.0,
        stress_trend=2.0,
    )
    assert round(drop, 2) == 2.05


def test_preemptive_survival_recommendation_threshold() -> None:
    """SPEC §25.10 line 4769: "If predicted DCS drop > 2.0 within 24h → pre-emptive SURVIVAL mode recommendation." """
    predictor = ExhaustionPredictor()

    # Metrics that induce drop > 2.0 (e.g. 3 high-D tasks + 2h sleep deficit -> 3*0.45 + 2*0.65 = 1.35 + 1.30 = 2.65 > 2.0)
    exhausting_metrics = ExhaustionMetrics(
        consecutive_high_d_tasks=3,
        sleep_deficit_hours=2.0,
        stress_trend=1.0,
        current_dcs=7.0,
    )
    pred = predictor.predict(exhausting_metrics)

    assert pred.predicted_dcs_drop > 2.0
    assert pred.preemptive_survival_recommended is True
    assert pred.recommended_mode == "SURVIVAL"
    assert "Pre-emptive SURVIVAL mode recommendation" in pred.message
    assert pred.predicted_dcs_24h < 7.0


def test_capacity_stable_under_threshold() -> None:
    """SPEC §25.10 line 4769: "If predicted DCS drop > 2.0 within 24h → pre-emptive SURVIVAL mode recommendation." """
    predictor = ExhaustionPredictor()

    # Mild metrics (1 high-D task, 0h sleep deficit, 0 stress -> drop = 0.45 <= 2.0)
    mild_metrics = ExhaustionMetrics(
        consecutive_high_d_tasks=1,
        sleep_deficit_hours=0.0,
        stress_trend=0.0,
        current_dcs=8.0,
    )
    pred = predictor.predict(mild_metrics)

    assert pred.predicted_dcs_drop <= 2.0
    assert pred.preemptive_survival_recommended is False
    assert pred.recommended_mode != "SURVIVAL"
    assert "Capacity stable" in pred.message


def test_exhaustion_provider_swappability_and_off_switches() -> None:
    """SPEC §25.10 line 4775: "Swappable / off state: locus.life_os.exhaustion.enabled." """
    # Swappability test
    class CustomExhaustionProvider(BaseExhaustionPredictorProvider):
        @property
        def name(self) -> str:
            return "custom_exhaustion"

        def is_feature_enabled(self) -> tuple[bool, str]:
            return True, ""

        def predict_exhaustion(self, metrics: dict[str, Any]) -> dict[str, Any]:
            return {"status": "ok", "custom": True}

        def get_status(self) -> dict[str, Any]:
            return {"status": "ok", "custom_active": True}

    custom = CustomExhaustionProvider()
    assert custom.name == "custom_exhaustion"
    assert custom.predict_exhaustion({})["custom"] is True

    # DefaultExhaustionPredictorProvider off-switches
    provider = DefaultExhaustionPredictorProvider()

    old_get = config.get
    try:
        # Master switch
        config.get = lambda k, default=None: False if k == "locus.exhaustion_predictor.enabled" else old_get(k, default)
        res1 = provider.predict_exhaustion({})
        assert res1.get("status_code") == 503
        assert res1["disabled"] == "locus.exhaustion_predictor.enabled"

        # Life OS sub-switch
        config.get = lambda k, default=None: False if k == "locus.life_os.exhaustion.enabled" else old_get(k, default)
        res2 = provider.get_status()
        assert res2.get("status_code") == 503
        assert res2["disabled"] == "locus.life_os.exhaustion.enabled"
    finally:
        config.get = old_get
