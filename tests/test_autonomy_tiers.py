import pytest
from sidecar.security.autonomy_tiers import (
    AutonomyTier,
    READ_ONLY_TOOLS,
    MUTATING_TOOLS,
    AutonomyManager,
)


def test_readonly_tier_blocks_mutating_tools():
    mgr = AutonomyManager(current_tier=AutonomyTier.READONLY)

    # Read tools allowed
    allowed, req_app, _ = mgr.can_execute_tool("read")
    assert allowed
    assert not req_app

    # Mutating tools denied
    allowed_w, _, reason_w = mgr.can_execute_tool("write")
    assert not allowed_w
    assert "READONLY" in reason_w

    allowed_b, _, _ = mgr.can_execute_tool("bash")
    assert not allowed_b


def test_supervised_tier_requires_approval_for_mutating():
    mgr = AutonomyManager(current_tier=AutonomyTier.SUPERVISED)

    # Read tool allowed freely
    allowed_r, req_r, _ = mgr.can_execute_tool("grep")
    assert allowed_r
    assert not req_r

    # Write tool allowed but requires approval
    allowed_w, req_w, _ = mgr.can_execute_tool("write")
    assert allowed_w
    assert req_w


def test_full_tier_allows_everything_without_approval():
    mgr = AutonomyManager(current_tier=AutonomyTier.FULL)

    allowed, req_app, _ = mgr.can_execute_tool("bash")
    assert allowed
    assert not req_app
