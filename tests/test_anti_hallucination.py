"""tests/test_anti_hallucination.py - Unit & Integration Tests for Anti-Hallucination Guard.

Tests Spec §2.6:
- Factual claim extraction and grounding against context.
- Warn mode (default): appends caveat when ungrounded claims are detected.
- Strict mode: blocks ungrounded response and logs severity-2 error.
- Grounded claims pass through without modification.
- Modularity switch: locus.anti_hallucination.enabled=False.
"""

import pytest

from sidecar.security.anti_hallucination import (
    DEFAULT_CAVEAT,
    AntiHallucinationGuard,
    AntiHallucinationProvider,
    VerificationResult,
)


def test_anti_hallucination_protocol_conformance():
    guard = AntiHallucinationGuard()
    assert isinstance(guard, AntiHallucinationProvider)


def test_grounded_response_passes_cleanly():
    guard = AntiHallucinationGuard(enabled=True)
    context = "User completed task_A in 45 minutes with DCS score of 8.2."
    response = "Great job today! You completed task_A with a DCS score of 8.2."

    res = guard.verify(response, context, mode="warn")
    assert res.ok is True
    assert res.blocked is False
    assert res.sanitized_response == response
    assert len(res.ungrounded_claims) == 0


def test_ungrounded_response_warn_mode():
    guard = AntiHallucinationGuard(enabled=True, default_mode="warn")
    context = "Context contains nothing about running or marathons."
    response = "Yesterday you completed a 10km marathon in 45 minutes."

    res = guard.verify(response, context, mode="warn")
    assert res.ok is True
    assert res.blocked is False
    assert DEFAULT_CAVEAT in res.sanitized_response
    assert len(res.ungrounded_claims) > 0
    assert len(guard.error_logs) == 1
    assert guard.error_logs[0]["severity"] == 1


def test_ungrounded_response_strict_mode():
    guard = AntiHallucinationGuard(enabled=True)
    context = "Context only mentions reading books."
    response = "Your goal is to build a rocket engine by tomorrow."

    res = guard.verify(response, context, mode="strict")
    assert res.ok is False
    assert res.blocked is True
    assert "Response blocked" in res.sanitized_response
    assert len(res.ungrounded_claims) > 0
    assert len(guard.error_logs) == 1
    assert guard.error_logs[0]["severity"] == 2


def test_anti_hallucination_modularity_disabled():
    guard = AntiHallucinationGuard(enabled=False)
    response = "Your DCS is 9.9."
    res = guard.verify(response, "Empty context", mode="strict")

    assert res.ok is True
    assert res.blocked is False
    assert res.mode == "disabled"
    assert res.sanitized_response == response
