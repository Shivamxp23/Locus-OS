"""tests/test_state_engine.py - Unit & Integration Tests for State Engine.

Tests Spec §2.4:
- Canonical DCS calculation and operating mode resolution.
- Staleness penalties: 1 day old (scores * 0.9) vs 3+ days old (baseline fallback + STALE_CHECKIN alert).
- StateEngineProvider protocol conformance.
- Modularity switch: locus.state_engine.enabled=False.
- CurrentState serialization to dictionary.
"""

import pytest

from sidecar.life_os.modes import OperatingMode
from sidecar.state_engine import (
    CheckinRecord,
    CurrentState,
    StateEngine,
    StateEngineProvider,
)


def test_state_engine_protocol_conformance():
    engine = StateEngine()
    assert isinstance(engine, StateEngineProvider)


def test_state_engine_fresh_checkin():
    engine = StateEngine(enabled=True)
    checkin = CheckinRecord(energy=9.0, mood=9.0, sleep=9.0, stress=1.0)
    state = engine.compute_state(last_checkin=checkin, days_since_checkin=0.1)

    assert state.dcs > 8.0
    assert state.operating_mode == OperatingMode.PEAK
    assert "STALE_CHECKIN" not in state.active_alerts
    assert state.energy == 9.0


def test_state_engine_one_day_staleness_penalty():
    engine = StateEngine(enabled=True)
    checkin = CheckinRecord(energy=8.0, mood=8.0, sleep=8.0, stress=2.0)
    state = engine.compute_state(last_checkin=checkin, days_since_checkin=1.5)

    # 8.0 * 0.9 = 7.2
    assert state.energy == pytest.approx(7.2)
    assert "CHECKIN_PENDING" in state.active_alerts


def test_state_engine_three_days_staleness_baseline():
    engine = StateEngine(enabled=True)
    checkin = CheckinRecord(energy=10.0, mood=10.0, sleep=10.0, stress=0.0)
    state = engine.compute_state(last_checkin=checkin, days_since_checkin=3.5)

    # Defaults to baseline (5, 5, 5, 3.5)
    assert state.energy == 5.0
    assert state.mood == 5.0
    assert state.sleep == 5.0
    assert "STALE_CHECKIN" in state.active_alerts


def test_state_engine_survival_mode():
    engine = StateEngine(enabled=True)
    # Very high stress, low sleep/energy -> SURVIVAL
    checkin = CheckinRecord(energy=2.0, mood=2.0, sleep=2.0, stress=8.0)
    state = engine.compute_state(last_checkin=checkin, days_since_checkin=0.1)

    assert state.operating_mode == OperatingMode.SURVIVAL
    assert state.dcs <= 2.0


def test_state_engine_modularity_disabled():
    engine = StateEngine(enabled=False)
    state = engine.compute_state()
    assert state.operating_mode == OperatingMode.NORMAL
    assert "STATE_ENGINE_DISABLED" in state.active_alerts


def test_current_state_serialization():
    engine = StateEngine(enabled=True)
    state = engine.compute_state(CheckinRecord(energy=7.0, mood=7.0, sleep=7.0, stress=3.0))
    d = state.to_dict()
    assert "dcs" in d
    assert "operating_mode" in d
    assert isinstance(d["active_alerts"], list)
