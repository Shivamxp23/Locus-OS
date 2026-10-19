"""
Unit tests for Life OS: Task Weight Score (TWS), Daily Capacity Score (DCS),
Operating Modes, Four Factions, and Universal Provider Pattern adherence.
"""
from __future__ import annotations

import pytest
from sidecar import config
from sidecar.life_os import (
    DEFAULT_FACTION_TARGETS,
    FACTION_CRISIS_HIERARCHY,
    calculate_dcs,
    calculate_tws,
    compute_faction_lag,
    log_post_task,
    resolve_operating_mode,
)
from sidecar.life_os.factions import compute_faction_lag_from_total
from sidecar.life_os.tws import calculate_tws_from_input
from sidecar.life_os.dcs import calculate_dcs_from_input
from sidecar.life_os import LifeOSProvider
from sidecar.providers.life_os import (
    BaseLifeOSProvider,
    CheckInInput,
    FactionType,
    GoalStackLevel,
    OperatingMode,
    TaskScoreInput,
)
from sidecar.registry import get_registry


def test_base_life_os_provider_interface():
    """SPEC §03 line 15: "LifeOSProvider registered behind BaseLifeOSProvider interface."."""
    with pytest.raises(TypeError):
        # Base class is abstract and cannot be directly instantiated
        BaseLifeOSProvider()  # type: ignore

    provider = LifeOSProvider()
    assert isinstance(provider, BaseLifeOSProvider)
    assert provider.is_enabled() is True


def test_life_os_provider_universal_pattern(monkeypatch):
    """SPEC §03 line 11: "initialize at start, run methods, stop shutdown, health returns status and latency."."""
    provider = LifeOSProvider()
    provider.initialize()
    health = provider.health_check()

    assert health["status"] == "healthy"
    assert health["initialized"] is True
    assert "latency_ms" in health
    assert FactionType.HEALTH.value in health["factions"]

    provider.shutdown()
    assert provider._initialized is False


def test_tws_base_formula_calculation():
    """SPEC §25.4 line 4636: "TWS = (P × 0.4) + (U × 0.4) + (D × 0.2)"."""
    # Max scores: P=10, U=10, D=10 -> 4.0 + 4.0 + 2.0 = 10.0
    res_max = calculate_tws(priority=10, urgency=10, difficulty=10)
    assert res_max.base_tws == 10.0
    assert res_max.final_tws == 10.0
    assert res_max.lag_bonus == 0.0

    # Intermediate scores: P=5, U=8, D=3 -> 2.0 + 3.2 + 0.6 = 5.8
    res_mid = calculate_tws(priority=5, urgency=8, difficulty=3)
    assert res_mid.base_tws == 5.8
    assert res_mid.final_tws == 5.8

    # Min scores: P=1, U=1, D=1 -> 0.4 + 0.4 + 0.2 = 1.0
    res_min = calculate_tws(priority=1, urgency=1, difficulty=1)
    assert res_min.base_tws == 1.0
    assert res_min.final_tws == 1.0


def test_tws_lag_bonuses_d1_option_a():
    """SPEC §25.4 line 4641: "LAG BONUS: faction Lag Score > 3h → TWS + 2, > 6h → TWS + 4, ahead → TWS − 1"."""
    # Crisis bonus: lag > 6h -> +4
    res_crisis = calculate_tws(priority=5, urgency=5, difficulty=5, faction_lag_hours=6.5)
    assert res_crisis.base_tws == 5.0
    assert res_crisis.lag_bonus == 4.0
    assert res_crisis.final_tws == 9.0

    # Elevated bonus: lag > 3h and <= 6h -> +2
    res_lag = calculate_tws(priority=5, urgency=5, difficulty=5, faction_lag_hours=4.0)
    assert res_lag.base_tws == 5.0
    assert res_lag.lag_bonus == 2.0
    assert res_lag.final_tws == 7.0

    # Normal progress: 0 <= lag <= 3h -> 0
    res_norm = calculate_tws(priority=5, urgency=5, difficulty=5, faction_lag_hours=1.5)
    assert res_norm.base_tws == 5.0
    assert res_norm.lag_bonus == 0.0
    assert res_norm.final_tws == 5.0

    # Ahead of target: lag < 0 -> -1
    res_ahead = calculate_tws(priority=5, urgency=5, difficulty=5, faction_lag_hours=-1.0)
    assert res_ahead.base_tws == 5.0
    assert res_ahead.lag_bonus == -1.0
    assert res_ahead.final_tws == 4.0


def test_tws_multi_scale_scoring_rollup():
    """SPEC §25.5 line 4664 / D-3 Option a: "scale = goal-stack level, with parent-child roll-up"."""
    # Daily task: score unaffected by child_scores
    res_daily = calculate_tws(
        priority=6, urgency=6, difficulty=6, scale=GoalStackLevel.DAILY, child_scores=[9.0, 8.0]
    )
    assert res_daily.scale == "daily"
    assert res_daily.base_tws == 6.0
    assert res_daily.final_tws == 6.0

    # Milestone roll-up: combines base score with high priority children
    res_milestone = calculate_tws(
        priority=5, urgency=5, difficulty=5, scale=GoalStackLevel.MILESTONE, child_scores=[9.0, 7.0]
    )
    assert res_milestone.scale == "milestone"
    # Child component: max(9)*0.7 + avg(8)*0.3 = 6.3 + 2.4 = 8.7
    # final_tws: base(5)*0.7 + child(8.7)*0.3 = 3.5 + 2.61 = 6.11
    assert res_milestone.final_tws == 6.11
    assert res_milestone.final_tws > res_milestone.base_tws


def test_post_task_logging_and_reason_enforcement():
    """SPEC §25.4 line 4646: "POST-TASK LOG: A (actual time), Q (quality 1-10), R (reason if |A − Est| > 50%)"."""
    # Under 50% deviation: no reason required
    log_ok = log_post_task(actual_time_minutes=55, estimated_time_minutes=50, quality=9)
    assert log_ok.actual_time_minutes == 55
    assert log_ok.estimated_time_minutes == 50
    assert log_ok.quality == 9
    assert log_ok.reason is None

    # Over 50% deviation without reason: raises ValueError
    with pytest.raises(ValueError, match="Reason required"):
        log_post_task(actual_time_minutes=120, estimated_time_minutes=60, quality=8)

    # Over 50% deviation with reason: accepted
    log_with_reason = log_post_task(
        actual_time_minutes=120, estimated_time_minutes=60, quality=8, reason="Compiler cache rebuild required"
    )
    assert log_with_reason.reason == "Compiler cache rebuild required"


def test_dcs_standard_calculation():
    """SPEC §25.2 line 4592: "DCS = ((E + M + S) / 3) × (1 − ST/20)"."""
    # High capacity: E=8, M=7, S=9, ST=4 -> ((8+7+9)/3) * (1 - 4/20) = 8.0 * 0.8 = 6.4
    res = calculate_dcs(energy=8, mood=7, sleep=9, stress=4, days_since_last_checkin=0)
    assert res.dcs == 6.4
    assert res.staleness_applied is False
    assert res.mode == OperatingMode.DEEP_WORK


def test_dcs_staleness_penalty():
    """SPEC §25.2 line 4596: "If no check-in today: apply staleness penalty (all scores × 0.9)"."""
    # Same inputs as above (raw 6.4) with 1 day missed checkin -> 6.4 * 0.9 = 5.76
    res_stale = calculate_dcs(energy=8, mood=7, sleep=9, stress=4, days_since_last_checkin=1)
    assert res_stale.dcs == 5.76
    assert res_stale.staleness_applied is True
    assert res_stale.mode == OperatingMode.NORMAL


def test_dcs_stale_fallback_after_three_days():
    """SPEC §25.2 line 4597: "If no check-in in 3+ days: default to baseline (5,5,5,7) & queue STALE_CHECKIN alert"."""
    res_baseline = calculate_dcs(energy=10, mood=10, sleep=10, stress=1, days_since_last_checkin=3)
    # Baseline (5,5,5,7): ((5+5+5)/3) * (1 - 7/20) = 5.0 * 0.65 = 3.25
    assert res_baseline.dcs == 3.25
    assert res_baseline.staleness_applied is True
    assert res_baseline.alert == "STALE_CHECKIN"
    assert res_baseline.mode == OperatingMode.RECOVERY


def test_five_operating_modes_resolution():
    """SPEC §25.3 line 4614: "Five Operating Modes: SURVIVAL, RECOVERY, NORMAL, DEEP WORK, PEAK"."""
    # Survival
    mode1, c1 = resolve_operating_mode(1.5)
    assert mode1 == OperatingMode.SURVIVAL
    assert c1.max_difficulty == 2
    assert c1.max_discretionary_tasks == 0

    # Recovery
    mode2, c2 = resolve_operating_mode(3.0)
    assert mode2 == OperatingMode.RECOVERY
    assert c2.max_difficulty == 4
    assert c2.max_discretionary_tasks == 2

    # Normal
    mode3, c3 = resolve_operating_mode(5.0)
    assert mode3 == OperatingMode.NORMAL
    assert c3.max_difficulty == 7
    assert c3.max_discretionary_tasks == 4

    # Deep Work
    mode4, c4 = resolve_operating_mode(7.0)
    assert mode4 == OperatingMode.DEEP_WORK
    assert c4.max_difficulty == 9

    # Peak
    mode5, c5 = resolve_operating_mode(9.0)
    assert mode5 == OperatingMode.PEAK
    assert c5.max_difficulty == 10
    assert c5.max_discretionary_tasks == 6


def test_four_factions_targets_and_lag_calculation():
    """SPEC §25.1 line 4572: "Weekly target allocation: Health 25% · Leverage 25% · Craft 30% · Expression 20%"."""
    assert DEFAULT_FACTION_TARGETS[FactionType.HEALTH.value] == 0.25
    assert DEFAULT_FACTION_TARGETS[FactionType.LEVERAGE.value] == 0.25
    assert DEFAULT_FACTION_TARGETS[FactionType.CRAFT.value] == 0.30
    assert DEFAULT_FACTION_TARGETS[FactionType.EXPRESSION.value] == 0.20

    # Crisis priority ordering
    assert FACTION_CRISIS_HIERARCHY == [
        FactionType.HEALTH.value,
        FactionType.LEVERAGE.value,
        FactionType.CRAFT.value,
        FactionType.EXPRESSION.value,
    ]

    # Target: 10h total -> Craft target is 3.0h. Actual logged is 1.0h -> lag is 2.0h
    lag = compute_faction_lag_from_total(FactionType.CRAFT.value, actual_hours=1.0, total_hours=10.0)
    assert lag == 2.0

    # Target: 10h total -> Health target is 2.5h. Actual logged is 3.5h -> lag is -1.0h (ahead)
    lag_ahead = compute_faction_lag_from_total(FactionType.HEALTH.value, actual_hours=3.5, total_hours=10.0)
    assert lag_ahead == -1.0


def test_life_os_off_switch(monkeypatch):
    """SPEC §03 line 35: "a disabled feature's routes/services reflect off-switch behavior"."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if k == "locus.life_os.enabled" else d)

    provider = LifeOSProvider()
    assert provider.is_enabled() is False

    health = provider.health_check()
    assert health["status"] == "disabled"


def test_life_os_swap(monkeypatch):
    """SPEC §03 line 41: "register a second fake provider under another name, set provider, assert fake is called."."""
    registry = get_registry()

    class FakeLifeOS(BaseLifeOSProvider):
        def initialize(self): pass
        def shutdown(self): pass
        def health_check(self): return {"status": "fake_ok", "latency_ms": 0.1}
        def calculate_tws(self, task_input):
            return calculate_tws(priority=1, urgency=1, difficulty=1)
        def calculate_dcs(self, checkin):
            return calculate_dcs(energy=1, mood=1, sleep=1, stress=1)
        def resolve_mode(self, dcs):
            return resolve_operating_mode(dcs)
        def compute_faction_lag(self, faction, target_pct, actual_hours, total_hours):
            return 0.0

    registry.register("life_os", "mock_life_os", FakeLifeOS)
    monkeypatch.setattr(config, "get", lambda k, d=None: "mock_life_os" if k == "locus.life_os.provider" else d)

    active_cls = registry.get_active_provider("life_os", default_name="default_life_os")
    assert active_cls is FakeLifeOS

    inst = active_cls()
    health = inst.health_check()
    assert health["status"] == "fake_ok"
