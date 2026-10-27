"""
SPEC §25.11 lines 4778-4800: Weekly Faction Rebalance.
Logic:
    WEEKLY REBALANCE (Sunday 02:00 IST):
        actual = PG query: SUM(duration) per faction for current week
        FOR EACH faction:
            deficit = target_pct − actual_pct
            next_week_weight = base_weight + (deficit × correction_factor)
        Write adjusted weights to faction_weights table for next week's scheduling.
Off state:
    When disabled (locus.life_os.rebalance.enabled=false / locus.weekly_faction_rebalance.enabled=false),
    faction weights remain static.
"""
from __future__ import annotations

import datetime
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from sidecar.life_os.emergency import FACTION_ALIASES
from sidecar.life_os.factions import DEFAULT_FACTION_TARGETS

logger = logging.getLogger("locus.life_os.rebalance")

# Standard canonical faction names mapped to default targets
STANDARD_FACTION_TARGETS: Dict[str, float] = {
    "Health/Stability": 0.25,
    "Leverage/Money": 0.25,
    "Craft/Skills": 0.30,
    "Expression/Explore": 0.20,
}


def normalize_faction_name(faction: str) -> str:
    """Normalize input faction string to standard canonical label."""
    cleaned = faction.strip()
    return FACTION_ALIASES.get(cleaned.lower(), cleaned)


@dataclass
class RebalanceResult:
    actual_hours: Dict[str, float]
    total_hours: float
    actual_percentages: Dict[str, float]
    target_percentages: Dict[str, float]
    deficits: Dict[str, float]
    base_weights: Dict[str, float]
    adjusted_weights: Dict[str, float]
    normalized_weights: Dict[str, float]
    correction_factor: float
    rebalance_time: str = field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "actual_hours": {k: round(v, 2) for k, v in self.actual_hours.items()},
            "total_hours": round(self.total_hours, 2),
            "actual_percentages": {k: round(v, 4) for k, v in self.actual_percentages.items()},
            "target_percentages": {k: round(v, 4) for k, v in self.target_percentages.items()},
            "deficits": {k: round(v, 4) for k, v in self.deficits.items()},
            "base_weights": {k: round(v, 4) for k, v in self.base_weights.items()},
            "adjusted_weights": {k: round(v, 4) for k, v in self.adjusted_weights.items()},
            "normalized_weights": {k: round(v, 4) for k, v in self.normalized_weights.items()},
            "correction_factor": round(self.correction_factor, 2),
            "rebalance_time": self.rebalance_time,
        }


class WeeklyFactionRebalancer:
    """
    Weekly Faction Rebalancing Engine per SPEC §25.11.
    Calculates weekly deficit between target and actual faction allocations,
    and adjusts next week's scheduling weights accordingly.
    """

    def __init__(
        self,
        target_percentages: Optional[Dict[str, float]] = None,
        default_correction_factor: float = 1.0,
        min_weight_floor: float = 0.05,
    ) -> None:
        self.default_targets: Dict[str, float] = (
            target_percentages or dict(STANDARD_FACTION_TARGETS)
        )
        self.default_correction_factor = default_correction_factor
        self.min_weight_floor = min_weight_floor
        # Active weights in memory (representing faction_weights storage)
        self._persisted_weights: Dict[str, float] = dict(self.default_targets)
        self._logged_durations: Dict[str, float] = {k: 0.0 for k in self.default_targets}

    def record_duration(self, faction: str, duration_hours: float) -> None:
        """Record task duration logged under a faction."""
        norm_faction = normalize_faction_name(faction)
        self._logged_durations[norm_faction] = (
            self._logged_durations.get(norm_faction, 0.0) + max(0.0, float(duration_hours))
        )

    def get_logged_durations(self) -> Dict[str, float]:
        """Return currently accumulated durations for the active period."""
        return dict(self._logged_durations)

    def reset_logged_durations(self) -> None:
        """Reset accumulated logged durations for a new week."""
        self._logged_durations = {k: 0.0 for k in self.default_targets}

    def get_active_weights(self) -> Dict[str, float]:
        """Return the current active scheduling weights."""
        return dict(self._persisted_weights)

    def reset_to_static_targets(self) -> None:
        """Reset scheduling weights back to static baseline targets."""
        self._persisted_weights = dict(self.default_targets)

    def calculate_rebalance(
        self,
        actual_hours: Optional[Dict[str, float]] = None,
        base_weights: Optional[Dict[str, float]] = None,
        target_percentages: Optional[Dict[str, float]] = None,
        correction_factor: Optional[float] = None,
    ) -> RebalanceResult:
        """
        Execute rebalance formula:
            actual = SUM(duration) per faction for current week
            deficit = target_pct - actual_pct
            next_week_weight = base_weight + (deficit * correction_factor)
        """
        # Resolve inputs
        raw_actuals = actual_hours if actual_hours is not None else self._logged_durations
        norm_actuals: Dict[str, float] = {}
        for f, h in raw_actuals.items():
            norm_name = normalize_faction_name(f)
            norm_actuals[norm_name] = norm_actuals.get(norm_name, 0.0) + max(0.0, float(h))

        targets = target_percentages or self.default_targets
        norm_targets: Dict[str, float] = {
            normalize_faction_name(f): float(p) for f, p in targets.items()
        }

        # Ensure all target factions exist in actuals
        for f in norm_targets:
            if f not in norm_actuals:
                norm_actuals[f] = 0.0

        total_hours = sum(norm_actuals.values())
        c_factor = (
            correction_factor
            if correction_factor is not None
            else self.default_correction_factor
        )

        actual_pcts: Dict[str, float] = {}
        deficits: Dict[str, float] = {}
        resolved_bases: Dict[str, float] = {}
        adjusted_weights: Dict[str, float] = {}

        # Resolve base weights (defaults to targets or active persisted weights)
        if base_weights:
            resolved_bases = {
                normalize_faction_name(f): float(w) for f, w in base_weights.items()
            }
        else:
            resolved_bases = dict(norm_targets)

        for f, target_pct in norm_targets.items():
            if total_hours > 0:
                act_pct = norm_actuals.get(f, 0.0) / total_hours
            else:
                act_pct = target_pct
            actual_pcts[f] = act_pct

            # deficit = target_pct - actual_pct
            deficit = target_pct - act_pct
            deficits[f] = deficit

            base_w = resolved_bases.get(f, target_pct)
            # next_week_weight = base_weight + (deficit * correction_factor)
            raw_next_weight = base_w + (deficit * c_factor)
            clamped_weight = max(self.min_weight_floor, raw_next_weight)
            adjusted_weights[f] = clamped_weight

        # Calculate normalized weights summing to 1.0
        total_adj = sum(adjusted_weights.values())
        normalized_weights: Dict[str, float] = {}
        for f, w in adjusted_weights.items():
            normalized_weights[f] = (w / total_adj) if total_adj > 0 else (1.0 / len(adjusted_weights))

        result = RebalanceResult(
            actual_hours=norm_actuals,
            total_hours=total_hours,
            actual_percentages=actual_pcts,
            target_percentages=norm_targets,
            deficits=deficits,
            base_weights=resolved_bases,
            adjusted_weights=adjusted_weights,
            normalized_weights=normalized_weights,
            correction_factor=c_factor,
        )

        # Update persisted weights table
        self._persisted_weights = dict(result.normalized_weights)
        return result
