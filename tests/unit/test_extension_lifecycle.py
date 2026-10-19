"""
Unit tests for Extension Lifecycle (SPEC §1.5, F-0005).
Asserts event catalog (25+ events), priority-ordered dispatch,
error containment, per-extension swappable off-state, and global off-switch.
"""
import pytest

from sidecar.extension_lifecycle import ExtensionLifecycleProvider
from sidecar.providers.extension_lifecycle import CANONICAL_LIFECYCLE_EVENTS


def test_canonical_lifecycle_events_catalog():
    """SPEC §1.5 line 514: "EXTENSION LIFECYCLE (25+ events):"
    Asserts that the provider supports 25+ canonical lifecycle events.
    """
    provider = ExtensionLifecycleProvider()
    events = provider.list_events()

    assert len(events) >= 25, f"Expected at least 25 canonical events, got {len(events)}"
    # Verify core lifecycle events
    expected_core = [
        "session_start",
        "turn_start",
        "message_start",
        "message_update",
        "message_end",
        "tool_execution_start",
        "tool_execution_update",
        "tool_execution_end",
        "turn_end",
        "agent_start",
        "agent_end",
        "session_shutdown",
        "before_compact",
        "after_compact",
        "before_tree",
        "session_switch",
        "replaced_session",
        "context_usage_update",
    ]
    for ev in expected_core:
        assert ev in events, f"Missing canonical lifecycle event: {ev}"


def test_default_locus_hooks_registration():
    """SPEC §1.5 line 528: "Key Locus hooks into this:"
    Asserts the 6 canonical Locus hooks are automatically registered on initialization.
    """
    provider = ExtensionLifecycleProvider()
    hooks = provider.list_hooks(extension_id="locus_core")
    events = [h.event for h in hooks]

    assert "session_start" in events
    assert "turn_start" in events
    assert "tool_execution_start" in events
    assert "tool_execution_end" in events
    assert "turn_end" in events
    assert "session_shutdown" in events


def test_priority_ordered_dispatch():
    """SPEC §1.5 line 515: "session_start → turn_start → message_start → message_update → message_end →"
    Asserts hooks for an event are executed strictly in priority order.
    """
    provider = ExtensionLifecycleProvider()
    execution_order = []

    def hook_p50(payload):
        execution_order.append("p50")
        return {"step_50": True}

    def hook_p10(payload):
        execution_order.append("p10")
        return {"step_10": True}

    def hook_p100(payload):
        execution_order.append("p100")
        return {"step_100": True}

    provider.register_hook("ext_test", "turn_start", hook_p50, priority=50)
    provider.register_hook("ext_test", "turn_start", hook_p10, priority=10)
    provider.register_hook("ext_test", "turn_start", hook_p100, priority=100)

    res = provider.dispatch_event("turn_start", {"initial": True})
    assert res.errors == []
    assert res.hooks_executed >= 3
    # Check relative ordering of our registered hooks
    assert execution_order == ["p10", "p50", "p100"]
    assert res.modified_payload.get("step_10") is True
    assert res.modified_payload.get("step_50") is True
    assert res.modified_payload.get("step_100") is True


def test_error_containment_in_dispatch():
    """SPEC §1.5 line 541: "KEEP: Pi's entire extension system, all 25+ lifecycle events, event payload structure."
    Asserts that if one hook raises an exception, other hooks continue running and error is captured.
    """
    provider = ExtensionLifecycleProvider()
    order = []

    def faulty_hook(payload):
        order.append("faulty")
        raise RuntimeError("Extension crashed unexpectedly")

    def safe_hook(payload):
        order.append("safe")
        return {"recovered": True}

    provider.register_hook("faulty_ext", "tool_execution_start", faulty_hook, priority=20)
    provider.register_hook("safe_ext", "tool_execution_start", safe_hook, priority=30)

    res = provider.dispatch_event("tool_execution_start", {"tool": "test"})
    assert "faulty" in order
    assert "safe" in order
    assert len(res.errors) == 1
    assert res.errors[0]["extension_id"] == "faulty_ext"
    assert "Extension crashed unexpectedly" in res.errors[0]["error"]
    assert res.modified_payload.get("recovered") is True


def test_extension_individual_swappable_off_state():
    """SPEC §1.5 line 540: "Swappable / off state: each Locus extension can be disabled individually via config. Off → that extension's hooks don't fire; Pi's core event loop continues unchanged."
    Asserts disabled extensions have their hooks skipped without affecting other extensions.
    """
    provider = ExtensionLifecycleProvider()
    ran = []

    provider.register_hook("ext_alpha", "turn_end", lambda p: ran.append("alpha"), priority=20)
    provider.register_hook("ext_beta", "turn_end", lambda p: ran.append("beta"), priority=30)

    # Disable ext_alpha
    provider.set_extension_enabled("ext_alpha", False)
    assert not provider.is_extension_enabled("ext_alpha")
    assert provider.is_extension_enabled("ext_beta")

    res = provider.dispatch_event("turn_end", {})
    assert "alpha" not in ran
    assert "beta" in ran
    assert res.hooks_skipped >= 1


def test_global_off_switch_behavior():
    """SPEC §1.5 line 540: "Swappable / off state: each Locus extension can be disabled individually via config. Off → that extension's hooks don't fire; Pi's core event loop continues unchanged."
    Asserts that disabling locus.extension_lifecycle.enabled bypasses all execution immediately.
    """
    provider = ExtensionLifecycleProvider(custom_config={"locus.extension_lifecycle.enabled": False})

    res = provider.dispatch_event("session_start", {"key": "val"})
    assert res.hooks_executed == 0
    assert res.errors == []
