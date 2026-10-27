"""
Life OS core modules: TWS, DCS, Operating Modes, Factions, Goal Stack, Action Gap, Deferral, Lag, and Provider.
"""
from __future__ import annotations

from sidecar.life_os.action_gap import (
    FactionActionGap,
    calculate_action_gap,
    evaluate_faction_action_gaps,
)
from sidecar.life_os.dcs import calculate_dcs
from sidecar.life_os.deferral import (
    DeferralAction,
    DeferralRecord,
    DeferralTracker,
)
from sidecar.life_os.emergency import (
    CRISIS_FACTION_ORDER,
    EmergencyTask,
    EmergencyTaskInjector,
)
from sidecar.life_os.factions import (
    DEFAULT_FACTION_TARGETS,
    FACTION_CRISIS_HIERARCHY,
    compute_faction_lag,
)
from sidecar.life_os.goal_stack import (
    GoalNode,
    GoalStackLevel,
    ThreeLayerGoalStack,
)
from sidecar.life_os.lag import (
    FactionLagReport,
    calculate_lag_score,
    calculate_tws_lag_bonus,
    compute_faction_lag_report,
)
from sidecar.life_os.modes import OPERATING_MODE_RULES, resolve_operating_mode
from sidecar.life_os.provider import LifeOSProvider
from sidecar.life_os.tws import calculate_tws, log_post_task

__all__ = [
    "DEFAULT_FACTION_TARGETS",
    "FACTION_CRISIS_HIERARCHY",
    "CRISIS_FACTION_ORDER",
    "EmergencyTask",
    "EmergencyTaskInjector",
    "DeferralAction",
    "DeferralRecord",
    "DeferralTracker",
    "FactionActionGap",
    "FactionLagReport",
    "GoalNode",
    "GoalStackLevel",
    "LifeOSProvider",
    "OPERATING_MODE_RULES",
    "ThreeLayerGoalStack",
    "calculate_action_gap",
    "calculate_dcs",
    "calculate_lag_score",
    "calculate_tws",
    "calculate_tws_lag_bonus",
    "compute_faction_lag",
    "compute_faction_lag_report",
    "evaluate_faction_action_gaps",
    "log_post_task",
    "resolve_operating_mode",
]
