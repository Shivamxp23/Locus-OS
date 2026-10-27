"""
Life OS core modules: TWS, DCS, Operating Modes, Factions, Goal Stack, Action Gap, Deferral, Lag, and Provider.
"""
from __future__ import annotations

from sidecar.life_os.action_gap import (
    FactionActionGap,
    calculate_action_gap,
    evaluate_faction_action_gaps,
)
from sidecar.life_os.cross_faction import (
    CrossFactionAggregateResult,
    CrossFactionAllocator,
    FactionSplitResult,
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
from sidecar.life_os.emergency_protocol import (
    EmergencyAssessment,
    EmergencyLevel,
    EmergencyProtocolStatus,
    FourLevelEmergencyProtocol,
    ProtocolActivationResult,
    ProtocolDeactivationResult,
)
from sidecar.life_os.exhaustion import (
    ExhaustionMetrics,
    ExhaustionPrediction,
    ExhaustionPredictor,
)
from sidecar.life_os.faction_balancer import (
    FactionBalanceReport,
    FactionBalancer,
    SCHEDULER_FACTION_TARGETS,
    canonicalize_faction,
)
from sidecar.life_os.factions import (
    DEFAULT_FACTION_TARGETS,
    FACTION_CRISIS_HIERARCHY,
    compute_faction_lag,
)
from sidecar.life_os.goal_enforcement import (
    BriefingOrphanReport,
    EnforcementResult,
    GoalStackEnforcer,
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
from sidecar.life_os.rebalance import (
    RebalanceResult,
    STANDARD_FACTION_TARGETS,
    WeeklyFactionRebalancer,
    normalize_faction_name,
)
from sidecar.life_os.reviews import (
    CADENCE_SCHEDULE_DEFAULTS,
    ReviewCadence,
    ReviewCadenceEngine,
    ReviewPrompt,
    ReviewResult,
)
from sidecar.life_os.tws import calculate_tws, log_post_task

__all__ = [
    "DEFAULT_FACTION_TARGETS",
    "FACTION_CRISIS_HIERARCHY",
    "CRISIS_FACTION_ORDER",
    "CrossFactionAggregateResult",
    "CrossFactionAllocator",
    "FactionSplitResult",
    "EmergencyTask",
    "EmergencyTaskInjector",
    "EmergencyAssessment",
    "EmergencyLevel",
    "EmergencyProtocolStatus",
    "FourLevelEmergencyProtocol",
    "ProtocolActivationResult",
    "ProtocolDeactivationResult",
    "ExhaustionMetrics",
    "ExhaustionPrediction",
    "ExhaustionPredictor",
    "DeferralAction",
    "DeferralRecord",
    "DeferralTracker",
    "FactionActionGap",
    "FactionBalanceReport",
    "FactionBalancer",
    "FactionLagReport",
    "BriefingOrphanReport",
    "EnforcementResult",
    "GoalStackEnforcer",
    "SCHEDULER_FACTION_TARGETS",
    "canonicalize_faction",
    "GoalNode",
    "GoalStackLevel",
    "LifeOSProvider",
    "OPERATING_MODE_RULES",
    "CADENCE_SCHEDULE_DEFAULTS",
    "ReviewCadence",
    "ReviewCadenceEngine",
    "ReviewPrompt",
    "ReviewResult",
    "RebalanceResult",
    "STANDARD_FACTION_TARGETS",
    "ThreeLayerGoalStack",
    "WeeklyFactionRebalancer",
    "normalize_faction_name",
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
