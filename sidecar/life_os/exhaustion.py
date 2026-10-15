"""sidecar/life_os/exhaustion.py - Exhaustion Predictor.

Implements Spec §25.10:
EXHAUSTION PREDICTOR:
- Monitors consecutive high-D tasks (Difficulty >= 8.0), sleep deficit, and stress trend.
- If predicted DCS drop > 2.0 within 24h -> pre-emptive SURVIVAL or RECOVERY mode recommendation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sidecar.life_os.modes import OperatingMode


@dataclass
class ExhaustionPrediction:
    predicted_dcs_drop: float
    current_dcs: float
    predicted_dcs: float
    is_at_risk: bool
    recommended_mode: Optional[OperatingMode]
    reasoning: str


class ExhaustionPredictor:
    """Predicts cognitive exhaustion and recommends preemptive operating modes."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def predict(
        self,
        current_dcs: float,
        consecutive_high_d_hours: float,
        sleep_deficit_hours: float,
        stress_trend_score: float,
    ) -> ExhaustionPrediction:
        """Predict DCS drop over next 24h.

        Factors:
        - consecutive_high_d_hours: hours of difficulty >= 8.0 completed recently
        - sleep_deficit_hours: sleep shortfall below target (e.g. 8.0 - actual)
        - stress_trend_score: 1.0 to 10.0 scale reflecting recent stress spike
        """
        if not self.enabled:
            return ExhaustionPrediction(
                predicted_dcs_drop=0.0,
                current_dcs=current_dcs,
                predicted_dcs=current_dcs,
                is_at_risk=False,
                recommended_mode=None,
                reasoning="Exhaustion predictor is disabled.",
            )

        # Drop modeling
        # Every 2h of high-D adds ~0.6 drop
        d_penalty = (consecutive_high_d_hours / 2.0) * 0.6
        # Sleep deficit: >2h deficit adds ~0.8 drop per hour
        sleep_penalty = max(0.0, sleep_deficit_hours) * 0.8
        # High stress (>6.0) adds linear penalty
        stress_penalty = max(0.0, (stress_trend_score - 6.0)) * 0.5

        total_drop = round(d_penalty + sleep_penalty + stress_penalty, 2)
        predicted_dcs = max(0.0, round(current_dcs - total_drop, 2))
        is_at_risk = total_drop > 2.0

        recommended_mode = None
        reasoning = f"Predicted DCS drop: {total_drop:.2f} (High-D: {d_penalty:.2f}, Sleep: {sleep_penalty:.2f}, Stress: {stress_penalty:.2f})."

        if is_at_risk:
            if predicted_dcs <= 2.0:
                recommended_mode = OperatingMode.SURVIVAL
            elif predicted_dcs <= 4.0:
                recommended_mode = OperatingMode.RECOVERY
            else:
                recommended_mode = OperatingMode.NORMAL
            reasoning += f" Severe fatigue risk detected! Recommended mode shift to {recommended_mode.value}."
        else:
            reasoning += " Cognitive capacity remains stable."

        return ExhaustionPrediction(
            predicted_dcs_drop=total_drop,
            current_dcs=current_dcs,
            predicted_dcs=predicted_dcs,
            is_at_risk=is_at_risk,
            recommended_mode=recommended_mode,
            reasoning=reasoning,
        )
