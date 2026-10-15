"""sidecar/life_os/rebalance.py - Weekly Faction Rebalance.

Implements Spec §25.11:
WEEKLY REBALANCE (Sunday 02:00 IST):
- actual = PG query: SUM(duration) per faction for current week
- FOR EACH faction:
    deficit = target_pct − actual_pct
    next_week_weight = base_weight + (deficit × correction_factor)
- Normalized so weights sum to 1.0
- Writes adjusted weights to faction_weights table for next week's scheduling.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from sidecar.life_os.factions import Faction, FACTION_TARGET_PERCENTAGES


@dataclass
class FactionRebalanceRecord:
    faction: Faction
    target_pct: float
    actual_pct: float
    deficit_pct: float
    previous_weight: float
    new_weight: float


def compute_weekly_rebalance(
    actual_hours: dict[Faction, float],
    base_weights: dict[Faction, float] | None = None,
    target_percentages: dict[Faction, float] | None = None,
    correction_factor: float = 0.5,
) -> dict[Faction, FactionRebalanceRecord]:
    """Compute rebalanced faction weights for upcoming week."""
    targets = target_percentages or FACTION_TARGET_PERCENTAGES
    bases = base_weights or FACTION_TARGET_PERCENTAGES

    total_actual = sum(actual_hours.values())
    raw_new_weights: dict[Faction, float] = {}
    records: dict[Faction, FactionRebalanceRecord] = {}

    for faction in Faction:
        act_hrs = actual_hours.get(faction, 0.0)
        act_pct = (act_hrs / total_actual) if total_actual > 0 else 0.0
        tgt_pct = targets.get(faction, 0.25)
        deficit = tgt_pct - act_pct

        base_wt = bases.get(faction, tgt_pct)
        # Apply correction factor to deficit
        raw_wt = max(0.05, base_wt + (deficit * correction_factor))
        raw_new_weights[faction] = raw_wt

    # Normalize weights so sum is 1.0
    total_raw = sum(raw_new_weights.values())
    for faction in Faction:
        act_hrs = actual_hours.get(faction, 0.0)
        act_pct = (act_hrs / total_actual) if total_actual > 0 else 0.0
        tgt_pct = targets.get(faction, 0.25)
        deficit = tgt_pct - act_pct
        base_wt = bases.get(faction, tgt_pct)
        norm_wt = round(raw_new_weights[faction] / total_raw, 4)

        records[faction] = FactionRebalanceRecord(
            faction=faction,
            target_pct=round(tgt_pct, 4),
            actual_pct=round(act_pct, 4),
            deficit_pct=round(deficit, 4),
            previous_weight=round(base_wt, 4),
            new_weight=norm_wt,
        )

    return records


class WeeklyFactionRebalancer:
    """Manages Sunday 02:00 IST faction weight rebalancing."""

    def __init__(self, enabled: bool = True, correction_factor: float = 0.5) -> None:
        self.enabled = enabled
        self.correction_factor = correction_factor
        self.current_weights: dict[Faction, float] = dict(FACTION_TARGET_PERCENTAGES)

    def rebalance(self, actual_hours: dict[Faction, float]) -> dict[Faction, float]:
        if not self.enabled:
            return dict(self.current_weights)

        records = compute_weekly_rebalance(
            actual_hours=actual_hours,
            base_weights=self.current_weights,
            correction_factor=self.correction_factor,
        )
        self.current_weights = {f: rec.new_weight for f, rec in records.items()}
        return dict(self.current_weights)
