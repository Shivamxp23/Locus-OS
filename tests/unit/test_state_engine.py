"""
Unit tests for State Engine Stage 3 (SPEC §2.4 / F-0093 / US-33).
Asserts canonical DCS formula, operating mode tier thresholds,
staleness penalties, CURRENT_STATE snapshot caching, and modular off-switches.
"""
import time
from typing import Any, Dict
import pytest

import sidecar.config as config
from sidecar.providers.state_engine import (
    BaseStateEngineProvider,
    CheckInRecord,
    CurrentState,
    OperatingMode,
)
from sidecar.registry import get_registry
from sidecar.state_engine import StateEngineProvider, DEFAULT_BASELINE


def test_state_engine_data_structures():
    """SPEC §2.4 line 1739: "Object fields: { dcs, operating_mode, energy, mood, stress, sleep, active_alerts[], inferred_cause_chain }"."""
    checkin = CheckInRecord(energy=7.5, mood=8.0, sleep=7.0, stress=3.0, timestamp=1700000000.0)
    d = checkin.to_dict()
    assert d["energy"] == 7.5
    assert d["mood"] == 8.0
    assert d["sleep"] == 7.0
    assert d["stress"] == 3.0
    assert d["timestamp"] == 1700000000.0

    restored = CheckInRecord.from_dict(d)
    assert restored.energy == 7.5
    assert restored.stress == 3.0

    state = CurrentState(
        dcs=6.5,
        operating_mode=OperatingMode.DEEP_WORK.value,
        energy=7.5,
        mood=8.0,
        sleep=7.0,
        stress=3.0,
        active_alerts=["TEST_ALERT"],
        inferred_cause_chain="High sleep sustained deep work",
        updated_at=1700000000.0,
    )
    sd = state.to_dict()
    assert sd["dcs"] == 6.5
    assert sd["operating_mode"] == "DEEP_WORK"
    assert "TEST_ALERT" in sd["active_alerts"]


def test_canonical_dcs_formula_calculation():
    """SPEC §2.4 line 1721: "Formula: DCS = ((E + M + S) / 3) × (1 - ST / 20)"."""
    provider = StateEngineProvider()

    # Zero stress (ST = 0 * 2 = 0): DCS = (10+10+10)/3 * (1 - 0) = 10.0
    dcs_max = provider.calculate_dcs(energy=10.0, mood=10.0, sleep=10.0, stress=0.0)
    assert dcs_max == 10.0

    # Max stress (input_stress = 10.0 -> ST = 20.0): stress_factor = (1 - 20/20) = 0.0 -> DCS = 0.0
    dcs_min = provider.calculate_dcs(energy=8.0, mood=8.0, sleep=8.0, stress=10.0)
    assert dcs_min == 0.0

    # Nominal: E=6, M=6, S=6 (avg=6), stress=2.5 (ST=5.0) -> factor = 1 - 5/20 = 0.75 -> DCS = 6 * 0.75 = 4.5
    dcs_nom = provider.calculate_dcs(energy=6.0, mood=6.0, sleep=6.0, stress=2.5)
    assert dcs_nom == 4.5


def test_operating_mode_thresholds():
    """SPEC §2.4 line 1730: "DCS 0.0 - 2.0  → SURVIVAL   (non-negotiables only, no cognitive strain)"."""
    provider = StateEngineProvider()

    # SURVIVAL (0.0 - 2.0)
    assert provider.determine_operating_mode(0.0) == OperatingMode.SURVIVAL.value
    assert provider.determine_operating_mode(1.8) == OperatingMode.SURVIVAL.value
    assert provider.determine_operating_mode(2.0) == OperatingMode.SURVIVAL.value

    # RECOVERY (2.1 - 4.0)
    assert provider.determine_operating_mode(2.1) == OperatingMode.RECOVERY.value
    assert provider.determine_operating_mode(3.5) == OperatingMode.RECOVERY.value
    assert provider.determine_operating_mode(4.0) == OperatingMode.RECOVERY.value

    # NORMAL (4.1 - 6.0)
    assert provider.determine_operating_mode(4.1) == OperatingMode.NORMAL.value
    assert provider.determine_operating_mode(5.5) == OperatingMode.NORMAL.value
    assert provider.determine_operating_mode(6.0) == OperatingMode.NORMAL.value

    # DEEP_WORK (6.1 - 8.0)
    assert provider.determine_operating_mode(6.1) == OperatingMode.DEEP_WORK.value
    assert provider.determine_operating_mode(7.2) == OperatingMode.DEEP_WORK.value
    assert provider.determine_operating_mode(8.0) == OperatingMode.DEEP_WORK.value

    # PEAK (8.1 - 10.0)
    assert provider.determine_operating_mode(8.1) == OperatingMode.PEAK.value
    assert provider.determine_operating_mode(9.5) == OperatingMode.PEAK.value
    assert provider.determine_operating_mode(10.0) == OperatingMode.PEAK.value


def test_process_checkin_and_state_snapshot():
    """SPEC §2.4 line 1737: "STEP 5: Update Redis CURRENT_STATE Cache"."""
    provider = StateEngineProvider()
    provider.reset()

    checkin = CheckInRecord(energy=9.0, mood=9.0, sleep=9.0, stress=1.0, timestamp=1700000000.0)
    state = provider.process_checkin(checkin, now_ts=1700000000.0)

    # DCS: avg=9, ST=2, factor=1 - 2/20 = 0.9 -> DCS = 9 * 0.9 = 8.1 -> PEAK
    assert state.dcs == 8.1
    assert state.operating_mode == OperatingMode.PEAK.value
    assert state.energy == 9.0
    assert state.mood == 9.0

    cached = provider.get_current_state(now_ts=1700000000.0)
    assert cached.dcs == state.dcs
    assert cached.operating_mode == state.operating_mode


def test_staleness_penalty_when_no_checkin_today():
    """SPEC §2.4 line 1716: "If no check-in today: apply staleness penalty (all scores × 0.9)."."""
    provider = StateEngineProvider()
    provider.reset()

    # Check-in recorded 36 hours ago (1.5 days)
    checkin_time = 1700000000.0
    provider.process_checkin(
        CheckInRecord(energy=8.0, mood=8.0, sleep=8.0, stress=2.0, timestamp=checkin_time),
        now_ts=checkin_time,
    )

    query_time = checkin_time + (36 * 3600.0)  # +36 hours
    stale_state = provider.get_current_state(now_ts=query_time)

    assert "CHECKIN_DUE_TODAY" in stale_state.active_alerts
    # Energy, mood, sleep scaled by 0.9: 8.0 * 0.9 = 7.2
    assert round(stale_state.energy, 2) == 7.2
    assert round(stale_state.mood, 2) == 7.2
    assert round(stale_state.sleep, 2) == 7.2


def test_staleness_fallback_after_three_days():
    """SPEC §2.4 line 1717: "If no check-in in 3+ days: default to baseline (5,5,5,7) & queue STALE_CHECKIN alert."."""
    provider = StateEngineProvider()
    provider.reset()

    # Check-in recorded 4 days ago
    checkin_time = 1700000000.0
    provider.process_checkin(
        CheckInRecord(energy=10.0, mood=10.0, sleep=10.0, stress=0.0, timestamp=checkin_time),
        now_ts=checkin_time,
    )

    query_time = checkin_time + (4 * 86400.0)  # +4 days
    baseline_state = provider.get_current_state(now_ts=query_time)

    assert "STALE_CHECKIN" in baseline_state.active_alerts
    assert baseline_state.energy == DEFAULT_BASELINE["energy"]
    assert baseline_state.mood == DEFAULT_BASELINE["mood"]
    assert baseline_state.sleep == DEFAULT_BASELINE["sleep"]


def test_state_engine_provider_registry():
    """SPEC §2.4 line 1709: "STEP 1: Write Trigger Reception"."""
    reg = get_registry()
    cls_provider = reg.get_active_provider("state_engine", default_name="default")
    assert cls_provider is StateEngineProvider


def test_state_engine_modular_off_switch(monkeypatch):
    """SPEC §2.4 line 1748: "Integration: Triggered by PostgreSQL LISTEN channel on every event write. Read by Context Forge & Inner Loop."."""
    provider = StateEngineProvider()
    assert provider.is_enabled() is True

    monkeypatch.setattr(config, "get", lambda k, d=None: False if "state_engine" in k else True)
    assert provider.is_enabled() is False
