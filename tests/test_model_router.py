"""tests/test_model_router.py - Unit & Integration Tests for Model Router.

Tests Spec §2.7-2.8:
- Task classification: Lightweight, Medium, Heavy.
- Routing decision matrix:
  - Privacy required forces Local only (fail closed).
  - Tools present forces Remote.
  - Health check failure routes to Remote fallback.
- Quality-based fallback: short responses, empty noise, or refusal DFA trigger fallback.
- Protocol conformance: ModelRouter conforms to ModelRouterProvider.
- Modularity switch: locus.routing.enabled=False.
"""

import pytest

from sidecar.routing.model_router import (
    ModelRouter,
    ModelRouterProvider,
    RouteTarget,
    RoutingHints,
    TaskCategory,
)


def test_model_router_protocol_conformance():
    router = ModelRouter()
    assert isinstance(router, ModelRouterProvider)


def test_model_classification():
    router = ModelRouter()
    assert router.classify("hint:quick") == TaskCategory.LIGHTWEIGHT
    assert router.classify("hint:fast") == TaskCategory.LIGHTWEIGHT
    assert router.classify("hint:medium") == TaskCategory.MEDIUM
    assert router.classify("hint:reasoning") == TaskCategory.HEAVY
    assert router.classify("hint:coding") == TaskCategory.HEAVY
    assert router.classify("claude-3-7-sonnet") == TaskCategory.HEAVY


def test_privacy_mode_forces_local():
    router = ModelRouter(enabled=True)
    hints = RoutingHints(privacy_required=True)
    primary, fallback = router.route_request("hint:reasoning", hints)

    # Privacy required forces local with no remote fallback
    assert primary == RouteTarget.LOCAL
    assert fallback is None


def test_tools_force_remote():
    router = ModelRouter(enabled=True)
    hints = RoutingHints(has_tools=True)
    primary, fallback = router.route_request("hint:quick", hints)

    # Lightweight would normally go local, but tools force remote
    assert primary == RouteTarget.REMOTE
    assert fallback is None


def test_unhealthy_local_falls_back_to_remote():
    router = ModelRouter(enabled=True)
    router.set_local_healthy(False)
    primary, fallback = router.route_request("hint:quick")

    assert primary == RouteTarget.REMOTE
    assert fallback is None


def test_quality_based_fallback_detection():
    router = ModelRouter()
    # 1. Short noise
    assert router.is_low_quality("...") is True
    assert router.is_low_quality("short") is True

    # 2. Refusal DFA
    assert router.is_low_quality("I apologize but I cannot answer that request.") is True
    assert router.is_low_quality("As an AI model, I am not able to do that.") is True

    # 3. Valid response
    valid_text = "Here is the comprehensive plan for implementing your sprint stories."
    assert router.is_low_quality(valid_text) is False


def test_model_router_modularity_disabled():
    router = ModelRouter(enabled=False)
    hints = RoutingHints(privacy_required=True)
    primary, fallback = router.route_request("hint:quick", hints)

    assert primary == RouteTarget.REMOTE
    assert fallback is None
