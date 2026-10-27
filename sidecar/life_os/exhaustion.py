"""
SPEC §25.10 lines 4759-4777: Exhaustion Predictor.
Rule:
    EXHAUSTION PREDICTOR: monitors consecutive high-D tasks, sleep deficit, and stress trend.
    If predicted DCS drop > 2.0 within 24h → pre-emptive SURVIVAL mode recommendation.
Off state:
    locus.life_os.exhaustion.enabled (when false, no pre-emptive mode recommendations).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

logger = logging.getLogger("locus.life_os.exhaustion")

PREDICTED_DROP_THRESHOLD = 2.0


@dataclass
class ExhaustionMetrics:
    consecutive_high_d_tasks: int = 0  # Difficulty >= 7 in sequence
    sleep_deficit_hours: float = 0.0  # Hours under baseline sleep
    stress_trend: float = 0.0  # Acute stress factor (0.0 to 10.0)
    current_dcs: float = 6.0  # Current Daily Capacity Score (0.0 to 10.0)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "consecutive_high_d_tasks": self.consecutive_high_d_tasks,
            "sleep_deficit_hours": self.sleep_deficit_hours,
            "stress_trend": self.stress_trend,
            "current_dcs": self.current_dcs,
        }


@dataclass
class ExhaustionPrediction:
    predicted_dcs_drop: float
    predicted_dcs_24h: float
    preemptive_survival_recommended: bool
    recommended_mode: str
    message: str
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "predicted_dcs_drop": round(self.predicted_dcs_drop, 2),
            "predicted_dcs_24h": round(self.predicted_dcs_24h, 2),
            "preemptive_survival_recommended": self.preemptive_survival_recommended,
            "recommended_mode": self.recommended_mode,
            "message": self.message,
            "metrics": self.metrics,
        }


class ExhaustionPredictor:
    """
    SPEC §25.10: Predictive engine forecasting cognitive exhaustion and DCS drops.
    """

    def calculate_predicted_dcs_drop(
        self,
        consecutive_high_d: int,
        sleep_deficit_hours: float,
        stress_trend: float,
    ) -> float:
        """
        Mathematical forecast of 24h capacity drop:
        drop = (consecutive_high_d * 0.45) + (sleep_deficit * 0.65) + (stress_trend * 0.25)
        """
        high_d_factor = float(max(0, consecutive_high_d)) * 0.45
        sleep_factor = float(max(0.0, sleep_deficit_hours)) * 0.65
        stress_factor = float(max(0.0, stress_trend)) * 0.25
        return round(high_d_factor + sleep_factor + stress_factor, 3)

    def predict(
        self,
        metrics: ExhaustionMetrics,
        threshold: float = PREDICTED_DROP_THRESHOLD,
    ) -> ExhaustionPrediction:
        """
        Evaluate metrics against the 2.0 DCS drop threshold within 24h.
        """
        drop = self.calculate_predicted_dcs_drop(
            consecutive_high_d=metrics.consecutive_high_d_tasks,
            sleep_deficit_hours=metrics.sleep_deficit_hours,
            stress_trend=metrics.stress_trend,
        )
        predicted_dcs_24h = max(0.0, metrics.current_dcs - drop)

        if drop > threshold:
            preemptive_survival = True
            rec_mode = "SURVIVAL"
            msg = f"Pre-emptive SURVIVAL mode recommendation: predicted DCS drop {drop:.2f} > {threshold:.1f} within 24h"
        else:
            preemptive_survival = False
            rec_mode = "NORMAL" if metrics.current_dcs >= 4.0 else "RECOVERY"
            msg = f"Capacity stable: predicted DCS drop {drop:.2f} <= {threshold:.1f} within 24h"

        return ExhaustionPrediction(
            predicted_dcs_drop=drop,
            predicted_dcs_24h=predicted_dcs_24h,
            preemptive_survival_recommended=preemptive_survival,
            recommended_mode=rec_mode,
            message=msg,
            metrics=metrics.to_dict(),
        )
