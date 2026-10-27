"""
SPEC §25.12 lines 4813 & 4843-4856: Mathematical Faction Constraint Solver.
Ensures weekly distribution:
- Craft (Work / Engineering):     Target 40% (Tolerance ±5%)
- Health (Physical / Mental):     Target 25% (Tolerance ±5%)
- Leverage (Systems / Wealth):    Target 20% (Tolerance ±5%)
- Expression (Writing / Art):     Target 15% (Tolerance ±5%)
Assignment Rule:
    Greedily assign highest TWS task to next open Deep block UNLESS assigning that task
    causes that faction's weekly allocated hours to exceed Target + Tolerance while an
    under-represented faction has eligible tasks waiting.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from sidecar.life_os.emergency import FACTION_ALIASES

logger = logging.getLogger("locus.life_os.faction_balancer")

# Canonical targets per §25.12 line 4845
SCHEDULER_FACTION_TARGETS: Dict[str, float] = {
    "Craft": 0.40,
    "Health": 0.25,
    "Leverage": 0.20,
    "Expression": 0.15,
}

# Tolerance per §25.12 line 4845
FACTION_TOLERANCE: float = 0.05


def canonicalize_faction(faction: str) -> str:
    """Map any alias to one of {Craft, Health, Leverage, Expression}."""
    cleaned = faction.strip()
    norm = FACTION_ALIASES.get(cleaned.lower(), cleaned)
    for root in ("Craft", "Health", "Leverage", "Expression"):
        if root.lower() in norm.lower():
            return root
    return "Craft"


@dataclass
class FactionBalanceReport:
    total_minutes: float
    allocations_minutes: Dict[str, float]
    actual_fractions: Dict[str, float]
    target_fractions: Dict[str, float]
    tolerances: Dict[str, float]
    under_represented: List[str]
    over_represented: List[str]
    compliant: bool

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_minutes": round(self.total_minutes, 1),
            "allocations_minutes": {k: round(v, 1) for k, v in self.allocations_minutes.items()},
            "actual_fractions": {k: round(v, 4) for k, v in self.actual_fractions.items()},
            "target_fractions": {k: round(v, 4) for k, v in self.target_fractions.items()},
            "under_represented": self.under_represented,
            "over_represented": self.over_represented,
            "compliant": self.compliant,
        }


class FactionBalancer:
    """
    Mathematical constraint solver ensuring weekly faction distribution per §25.12.
    """

    def __init__(
        self,
        targets: Optional[Dict[str, float]] = None,
        tolerance: float = FACTION_TOLERANCE,
    ) -> None:
        self.targets = targets or dict(SCHEDULER_FACTION_TARGETS)
        self.tolerance = tolerance

    def evaluate_allocations(
        self,
        allocations_minutes: Dict[str, float],
    ) -> FactionBalanceReport:
        """
        Evaluate current allocations against canonical targets and tolerances.
        """
        norm_allocs: Dict[str, float] = {k: 0.0 for k in self.targets}
        for f, mins in allocations_minutes.items():
            c_f = canonicalize_faction(f)
            norm_allocs[c_f] = norm_allocs.get(c_f, 0.0) + max(0.0, float(mins))

        total_mins = sum(norm_allocs.values())
        actual_fracs: Dict[str, float] = {}
        under_rep: List[str] = []
        over_rep: List[str] = []
        compliant = True

        for f, target in self.targets.items():
            frac = (norm_allocs[f] / total_mins) if total_mins > 0 else target
            actual_fracs[f] = frac
            min_allowed = max(0.0, target - self.tolerance)
            max_allowed = min(1.0, target + self.tolerance)

            if total_mins > 0:
                if frac < min_allowed:
                    under_rep.append(f)
                    compliant = False
                elif frac > max_allowed:
                    over_rep.append(f)
                    compliant = False

        return FactionBalanceReport(
            total_minutes=total_mins,
            allocations_minutes=norm_allocs,
            actual_fractions=actual_fracs,
            target_fractions=dict(self.targets),
            tolerances={k: self.tolerance for k in self.targets},
            under_represented=under_rep,
            over_represented=over_rep,
            compliant=compliant,
        )

    def is_assignment_allowed(
        self,
        candidate_faction: str,
        proposed_minutes: float,
        current_allocations: Dict[str, float],
        waiting_factions: Set[str],
    ) -> Tuple[bool, str]:
        """
        SPEC §25.12 line 4853:
        Greedily assign highest TWS task to next open Deep block UNLESS assigning that task
        causes that faction's weekly allocated hours to exceed Target + Tolerance while an
        under-represented faction has eligible tasks waiting.
        """
        c_cand = canonicalize_faction(candidate_faction)
        norm_waiting = {canonicalize_faction(f) for f in waiting_factions}

        # Projected allocations if candidate is assigned
        projected = dict(current_allocations)
        projected[c_cand] = projected.get(c_cand, 0.0) + proposed_minutes

        total_proj = sum(projected.values())
        if total_proj <= 0:
            return True, "No prior allocations"

        cand_target = self.targets.get(c_cand, 0.25)
        max_allowed = cand_target + self.tolerance
        proj_frac = projected[c_cand] / total_proj

        # Check if projected allocation exceeds Target + Tolerance
        if proj_frac > max_allowed:
            # Check if any under-represented faction has waiting tasks
            for other_f, other_target in self.targets.items():
                if other_f != c_cand and other_f in norm_waiting:
                    curr_other_frac = (current_allocations.get(other_f, 0.0) / total_proj) if total_proj > 0 else 0.0
                    if curr_other_frac < (other_target - self.tolerance):
                        return False, (
                            f"Assignment of {c_cand} ({proj_frac:.1%} > {max_allowed:.1%}) blocked: "
                            f"under-represented faction '{other_f}' has waiting tasks."
                        )

        return True, "Assignment complies with faction balance constraints"
