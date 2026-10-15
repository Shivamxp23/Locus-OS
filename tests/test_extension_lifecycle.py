import pytest
from sidecar.lifecycle import (
    LIFECYCLE_EVENTS,
    LifecycleEvent,
    LifecycleManager,
)


def test_25_events_supported():
    assert len(LIFECYCLE_EVENTS) >= 25
    assert "session_start" in LIFECYCLE_EVENTS
    assert "turn_start" in LIFECYCLE_EVENTS
    assert "session_shutdown" in LIFECYCLE_EVENTS


def test_event_dispatch_and_history():
    mgr = LifecycleManager()
    received = []

    mgr.subscribe("turn_start", lambda e: received.append(e.turn_id))

    ev1 = LifecycleEvent(event_type="turn_start", session_id="s1", turn_id="t1")
    ev2 = LifecycleEvent(event_type="turn_end", session_id="s1", turn_id="t1")
    ev3 = LifecycleEvent(event_type="turn_start", session_id="s1", turn_id="t2")

    mgr.dispatch(ev1)
    mgr.dispatch(ev2)
    mgr.dispatch(ev3)

    assert received == ["t1", "t2"]
    assert len(mgr.get_event_history()) == 3
    assert len(mgr.get_event_history("turn_start")) == 2


def test_invalid_event_subscription():
    mgr = LifecycleManager()
    with pytest.raises(ValueError):
        mgr.subscribe("non_existent_event", lambda e: None)
