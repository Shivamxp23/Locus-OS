"""
SPEC §2.6 / F-0095 / US-35: Unit Tests for Anti-Hallucination Guard (Stage 10).
"""
import pytest
from typing import Any, Dict, List, Optional

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.providers.anti_hallucination import (
    BaseAntiHallucinationProvider,
    BrainErrorLog,
    CheckResult,
    DEFAULT_CAVEAT_MESSAGE,
    FactualClaim,
    GuardMode,
)
from sidecar.anti_hallucination import (
    AntiHallucinationProvider,
    clear_brain_errors,
    get_brain_errors,
)


@pytest.fixture(autouse=True)
def reset_state():
    clear_brain_errors()
    config._CONFIG_CACHE = None
    yield
    clear_brain_errors()
    config._CONFIG_CACHE = None


def test_anti_hallucination_check_contract():
    """SPEC §2.6 line 1821: "FUNCTION anti_hallucination_check(llm_response, context_forge_content):" """
    provider = AntiHallucinationProvider()
    res = provider.check("You completed 5 tasks yesterday.", "User completed 5 tasks yesterday in vault.")
    assert isinstance(res, CheckResult)
    assert res.block is False
    assert res.claims_detected == ["You completed 5 tasks yesterday."]
    assert res.ungrounded_claims == []


def test_after_tool_call_hook_dispatch():
    """SPEC §2.6 line 1822: "Runs as afterToolCall hook OR as post-generation check" """
    provider = AntiHallucinationProvider()
    res = provider.check("General programming advice: use list comprehensions.", "")
    assert res.block is False
    assert len(res.claims_detected) == 0


def test_extract_factual_claims():
    """SPEC §2.6 line 1825: "claims = extract_factual_claims(llm_response)" """
    provider = AntiHallucinationProvider()
    text = (
        "Hello! You completed the thesis outline project earlier today. "
        "I suggest drinking more water. "
        "Your focus score was recorded as 85."
    )
    claims = provider.extract_factual_claims(text)
    statements = [c.statement for c in claims]
    assert any("completed the thesis outline" in s for s in statements)
    assert any("focus score was recorded" in s for s in statements)
    assert not any("drinking more water" in s for s in statements)


def test_factual_claims_filter_opinions():
    """SPEC §2.6 line 1826: "A "claim" is any statement about the user, their data, or their history; NOT opinions, advice, or external knowledge" """
    provider = AntiHallucinationProvider()
    opinions = [
        "In my opinion, Python is superior to JavaScript.",
        "You should consider taking a break now.",
        "Generally, memory usage increases with large graphs.",
    ]
    for op in opinions:
        claims = provider.extract_factual_claims(op)
        assert len(claims) == 0, f"Expected 0 claims for opinion: {op}"


def test_grounding_evidence_check():
    """SPEC §2.6 line 1832: "IF NOT context_forge_content.contains_evidence_for(claim): ungrounded_claims.append(claim)" """
    provider = AntiHallucinationProvider()
    context = "Identity: Shivam. Recent tasks: completed compiler pass 2, studied neural architecture."
    grounded_claim = "You completed compiler pass 2."
    ungrounded_claim = "You visited Paris yesterday with Alice."

    assert provider.contains_evidence_for(context, grounded_claim) is True
    assert provider.contains_evidence_for(context, ungrounded_claim) is False


def test_strict_mode_rejects_and_logs():
    """SPEC §2.6 line 1838: "IF config.anti_hallucination.mode == "strict": REJECT response; LOG to brain_errors (severity=2, type="hallucination"); RETURN { block: true, reason: "Response contained ungrounded claims" }" """
    provider = AntiHallucinationProvider()
    response = "You have 10 unreviewed pull requests in your vault."
    context = "User identity: Student. No pending pull requests."

    res = provider.check(response, context, mode="strict")
    assert res.block is True
    assert res.reason == "Response contained ungrounded claims"
    assert res.output_response == ""
    assert len(res.ungrounded_claims) > 0

    errors = get_brain_errors()
    assert len(errors) == 1
    assert errors[0].error_type == "hallucination"
    assert errors[0].severity == 2


def test_warn_mode_appends_caveat_and_logs():
    """SPEC §2.6 line 1844: "ELIF config.anti_hallucination.mode == "warn": response += "\n\n⚠️ Note: I'm not fully certain about some details. Let me know if anything seems off."; LOG to brain_errors (severity=1, type="soft_hallucination")" """
    provider = AntiHallucinationProvider()
    response = "Your sleep score was 92 last night."
    context = "Circadian data unavailable."

    res = provider.check(response, context, mode="warn")
    assert res.block is False
    assert res.reason is None
    assert DEFAULT_CAVEAT_MESSAGE in res.output_response
    assert res.output_response.startswith(response)

    errors = get_brain_errors()
    assert len(errors) == 1
    assert errors[0].error_type == "soft_hallucination"
    assert errors[0].severity == 1


def test_clean_response_not_blocked():
    """SPEC §2.6 line 1848: "RETURN { block: false }" """
    provider = AntiHallucinationProvider()
    response = "You logged 45 minutes of workout in your system."
    context = "Events: user logged 45 minutes of workout in system."

    res = provider.check(response, context, mode="warn")
    assert res.block is False
    assert res.reason is None
    assert DEFAULT_CAVEAT_MESSAGE not in res.output_response
    assert res.output_response == response
    assert len(get_brain_errors()) == 0


def test_extension_component_exports():
    """SPEC §2.6 line 1856: Extension implementation in locus-extension/src/anti-hallucination.ts"""
    from pathlib import Path
    ts_file = Path("locus-extension/src/anti-hallucination.ts")
    assert ts_file.is_file()
    content = ts_file.read_text(encoding="utf-8")
    assert "export class AntiHallucinationGuardImpl" in content
    assert "extractFactualClaims" in content
    assert "containsEvidenceFor" in content


def test_anti_hallucination_provider_registration_and_swap():
    """Test provider registration and swappability per modularity architecture (03)."""
    reg = get_registry()
    provider_cls = reg.get_active_provider("anti_hallucination", default_name="default")
    assert provider_cls is AntiHallucinationProvider

    class MockCustomGuard(BaseAntiHallucinationProvider):
        def check(self, llm_response, context_forge_content, mode=None):
            return CheckResult(block=False, original_response="custom", output_response="custom")

        def extract_factual_claims(self, llm_response):
            return []

        def contains_evidence_for(self, context_content, claim):
            return True

        def get_mode(self):
            return GuardMode.OFF

    reg.register("anti_hallucination", "custom_mock", MockCustomGuard)
    try:
        custom_cls = reg.get("anti_hallucination", "custom_mock")
        assert custom_cls is MockCustomGuard
        inst = custom_cls()
        res = inst.check("test", "test")
        assert res.output_response == "custom"
    finally:
        reg._providers.get("anti_hallucination", {}).pop("custom_mock", None)
