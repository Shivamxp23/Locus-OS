"""
Unit tests for Intelligent Model Routing + Quality-Based Fallback (SPEC §2.7-2.8, F-0096, US-37).
"""
import time
import pytest

from sidecar.model_routing import (
    MIN_RESPONSE_BYTES,
    MODEL_CHAT_V1,
    MODEL_LOCAL_DEFAULT,
    MODEL_REASONING_V1,
    ModelRoutingProvider,
)
from sidecar.providers.model_routing import (
    BaseModelRoutingProvider,
    ChatRequest,
    ChatResponse,
    CostSensitivity,
    HealthCheckResult,
    LatencyBudget,
    RoutingDecision,
    RoutingHints,
    TargetBackend,
    TaskCategory,
)
from sidecar.registry import get_registry


class TestModelRoutingClassification:
    """Test classification logic per SPEC §2.7-2.8."""

    def test_classify_hints(self):
        """SPEC §2.7-2.8 line 1879: 'FUNCTION classify(model_string) -> TaskCategory:'"""
        provider = ModelRoutingProvider()
        assert provider.classify("hint:quick") == TaskCategory.LIGHTWEIGHT
        assert provider.classify("hint:fast") == TaskCategory.LIGHTWEIGHT
        assert provider.classify("hint:medium") == TaskCategory.MEDIUM
        assert provider.classify("hint:reasoning") == TaskCategory.HEAVY
        assert provider.classify("hint:agentic") == TaskCategory.HEAVY
        assert provider.classify("hint:coding") == TaskCategory.HEAVY
        # hint:chat goes remote despite conversational due to TTFT
        assert provider.classify("hint:chat") == TaskCategory.HEAVY

    def test_classify_explicit_and_unknown(self):
        """SPEC §2.7-2.8 line 1886: 'ELIF is_exact_model_name(model_string): -> Heavy'"""
        provider = ModelRoutingProvider()
        assert provider.classify("deepseek/deepseek-chat") == TaskCategory.HEAVY
        assert provider.classify("google/gemini-2.5-pro") == TaskCategory.HEAVY
        assert provider.classify("unknown-random-model") == TaskCategory.HEAVY
        assert provider.classify("") == TaskCategory.HEAVY

    def test_normalize_model_id(self):
        """SPEC §2.7-2.8 line 1989: 'Heavy hint:* strings -> backend model IDs:'"""
        provider = ModelRoutingProvider()
        assert provider.normalize_model_id("hint:reasoning") == MODEL_REASONING_V1
        assert provider.normalize_model_id("hint:chat") == MODEL_CHAT_V1
        assert provider.normalize_model_id("hint:agentic") == MODEL_CHAT_V1
        assert provider.normalize_model_id("hint:coding") == MODEL_CHAT_V1
        assert provider.normalize_model_id("hint:quick") == MODEL_LOCAL_DEFAULT
        assert provider.normalize_model_id("custom/model") == "custom/model"


class TestModelRoutingDecisions:
    """Test policy decision matrix and overrides per SPEC §2.7-2.8."""

    def test_lightweight_routing(self):
        """SPEC §2.7-2.8 line 1900: 'Lightweight: Default Local, Remote if local unhealthy'"""
        provider = ModelRoutingProvider()
        hints = RoutingHints()

        # Local healthy -> Local primary, Remote fallback
        decision_healthy = provider.decide(TaskCategory.LIGHTWEIGHT, local_healthy=True, hints=hints)
        assert decision_healthy.primary == TargetBackend.LOCAL
        assert decision_healthy.fallback == TargetBackend.REMOTE
        assert decision_healthy.supports_streaming is True

        # Local unhealthy -> Remote primary, no fallback
        decision_unhealthy = provider.decide(TaskCategory.LIGHTWEIGHT, local_healthy=False, hints=hints)
        assert decision_unhealthy.primary == TargetBackend.REMOTE
        assert decision_unhealthy.fallback is None

    def test_medium_routing_and_overrides(self):
        """SPEC §2.7-2.8 line 1901: 'Medium: Default Remote, Local if LatencyBudget::Low OR CostSensitivity::High'"""
        provider = ModelRoutingProvider()

        # Default Medium -> Remote
        hints_default = RoutingHints()
        decision_default = provider.decide(TaskCategory.MEDIUM, local_healthy=True, hints=hints_default)
        assert decision_default.primary == TargetBackend.REMOTE
        assert decision_default.fallback == TargetBackend.LOCAL

        # LatencyBudget::Low -> Local primary
        hints_latency = RoutingHints(latency_budget=LatencyBudget.LOW)
        decision_latency = provider.decide(TaskCategory.MEDIUM, local_healthy=True, hints=hints_latency)
        assert decision_latency.primary == TargetBackend.LOCAL
        assert decision_latency.fallback == TargetBackend.REMOTE

        # CostSensitivity::High -> Local primary
        hints_cost = RoutingHints(cost_sensitivity=CostSensitivity.HIGH)
        decision_cost = provider.decide(TaskCategory.MEDIUM, local_healthy=True, hints=hints_cost)
        assert decision_cost.primary == TargetBackend.LOCAL
        assert decision_cost.fallback == TargetBackend.REMOTE

        # If local is unhealthy, Medium stays Remote even with hints
        decision_unhealthy = provider.decide(TaskCategory.MEDIUM, local_healthy=False, hints=hints_latency)
        assert decision_unhealthy.primary == TargetBackend.REMOTE
        assert decision_unhealthy.fallback is None

    def test_heavy_routing(self):
        """SPEC §2.7-2.8 line 1903: 'Heavy: Remote (always), Local ONLY if privacy_required'"""
        provider = ModelRoutingProvider()
        hints = RoutingHints()
        decision = provider.decide(TaskCategory.HEAVY, local_healthy=True, hints=hints)
        assert decision.primary == TargetBackend.REMOTE
        assert decision.fallback is None

    def test_privacy_required_fail_closed(self):
        """SPEC §2.7-2.8 line 1906: 'PRIVACY_REQUIRED: Forces local routing for ALL categories, no remote fallback — fails closed'"""
        provider = ModelRoutingProvider()
        privacy_hints = RoutingHints(privacy_required=True)

        for cat in [TaskCategory.LIGHTWEIGHT, TaskCategory.MEDIUM, TaskCategory.HEAVY]:
            decision = provider.decide(cat, local_healthy=True, hints=privacy_hints)
            assert decision.primary == TargetBackend.LOCAL
            assert decision.fallback is None
            assert decision.supports_streaming is False

    def test_tools_force_remote(self):
        """SPEC §2.7-2.8 line 1911: 'TOOLS FORCE REMOTE: If request carries tools and policy chose local -> override to remote'"""
        provider = ModelRoutingProvider()
        hints = RoutingHints()
        # Lightweight would normally choose local
        decision = provider.decide(TaskCategory.LIGHTWEIGHT, local_healthy=True, hints=hints, has_tools=True)
        assert decision.primary == TargetBackend.REMOTE
        assert decision.fallback is None
        assert "Tool" in decision.reason


class TestQualityBasedFallback:
    """Test quality heuristic and refusal detection per SPEC §2.7-2.8."""

    def test_length_floor(self):
        """SPEC §2.7-2.8 line 1945: 'Check 1: Length floor: IF response_text.len() < MIN_RESPONSE_BYTES: RETURN true'"""
        provider = ModelRoutingProvider()
        assert provider.is_low_quality("") is True
        assert provider.is_low_quality("short") is True
        assert provider.is_low_quality("123456789") is True
        assert provider.is_low_quality("This is long enough to pass floor.") is False

    def test_empty_noise_tokens(self):
        """SPEC §2.7-2.8 line 1948: 'Check 2: Empty-noise tokens: IF response_text.trim() IN [\"...\", \"I\", \"\", \"?\"]: RETURN true'"""
        provider = ModelRoutingProvider()
        assert provider.is_low_quality("...") is True
        assert provider.is_low_quality("   ...   ") is True
        assert provider.is_low_quality("I") is True
        assert provider.is_low_quality("?") is True

    def test_refusal_patterns(self):
        """SPEC §2.7-2.8 line 1951: 'Check 3: Refusal DFA: REFUSAL_PATTERNS'"""
        provider = ModelRoutingProvider()
        refusal_samples = [
            "I cannot complete this request due to constraints.",
            "I can't fulfill your instruction as asked.",
            "I'm unable to process that task right now.",
            "I apologize but I cannot help with that.",
            "As an AI, I am limited in scope.",
            "I don't have the ability to run that.",
            "I'm not able to generate that answer.",
            "I am not able to do this.",
        ]
        for sample in refusal_samples:
            assert provider.is_low_quality(sample) is True

    def test_valid_response_not_low_quality(self):
        """SPEC §2.7-2.8 line 1959: 'RETURN false for genuine helpful responses'"""
        provider = ModelRoutingProvider()
        assert provider.is_low_quality("The capital of France is Paris. It is a historic cultural center.") is False


class TestLocalHealthChecker:
    """Test health probe caching discipline per SPEC §2.7-2.8."""

    def test_health_cache_ttl(self):
        """SPEC §2.7-2.8 line 1925: 'LocalHealthChecker: Cached probe with 30-second TTL'"""
        provider = ModelRoutingProvider(health_cache_ttl=2.0)
        provider.set_cached_health(True)

        # Within TTL, returns cached True without probing
        res1 = provider.check_local_health(force_refresh=False)
        assert res1.healthy is True

        # Expire cache manually
        provider._cached_health.last_check = time.time() - 5.0
        # When probing an offline default URL, it should return False
        res2 = provider.check_local_health(force_refresh=False)
        assert res2.healthy is False


class TestDispatchFlowAndFallback:
    """Test full dispatch flow with primary execution and quality fallback per SPEC §2.7-2.8."""

    def test_successful_local_dispatch(self):
        """SPEC §2.7-2.8 line 1968: 'IntelligentRoutingProvider implements Provider: FUNCTION chat(request):'"""
        provider = ModelRoutingProvider()
        provider.set_cached_health(True)

        req = ChatRequest(model="hint:quick", messages=[{"role": "user", "content": "hi"}])
        local_called = [0]
        remote_called = [0]

        def call_local(r):
            local_called[0] += 1
            return ChatResponse(
                text="A complete and adequate answer from local server.",
                model=MODEL_LOCAL_DEFAULT,
                backend=TargetBackend.LOCAL,
                usage={"prompt_tokens": 5, "completion_tokens": 15},
            )

        def call_remote(r):
            remote_called[0] += 1
            return ChatResponse(
                text="Remote answer",
                model=MODEL_CHAT_V1,
                backend=TargetBackend.REMOTE,
            )

        resp, record = provider.execute_routed_chat(req, local_invoker=call_local, remote_invoker=call_remote)
        assert local_called[0] == 1
        assert remote_called[0] == 0
        assert resp.backend == TargetBackend.LOCAL
        assert record.used_fallback is False

    def test_quality_fallback_from_refusal(self):
        """SPEC §2.7-2.8 line 1980: 'IF decision.primary == Local AND is_low_quality(response.text): dispatch(Remote, request)'"""
        provider = ModelRoutingProvider()
        provider.set_cached_health(True)

        req = ChatRequest(model="hint:quick", messages=[{"role": "user", "content": "solve this"}])
        local_called = [0]
        remote_called = [0]

        def call_local(r):
            local_called[0] += 1
            return ChatResponse(
                text="I cannot fulfill this request properly.",  # Refusal
                model=MODEL_LOCAL_DEFAULT,
                backend=TargetBackend.LOCAL,
            )

        def call_remote(r):
            remote_called[0] += 1
            return ChatResponse(
                text="Here is the detailed solution from the remote backend.",
                model=MODEL_CHAT_V1,
                backend=TargetBackend.REMOTE,
                usage={"prompt_tokens": 10, "completion_tokens": 20},
            )

        resp, record = provider.execute_routed_chat(req, local_invoker=call_local, remote_invoker=call_remote)
        assert local_called[0] == 1
        assert remote_called[0] == 1
        assert resp.backend == TargetBackend.REMOTE
        assert record.used_fallback is True
        assert record.target == TargetBackend.REMOTE

    def test_provider_registration(self):
        """SPEC §2.7-2.8 Criteria 2: 'Registers as a provider in sidecar/providers/'"""
        registry = get_registry()
        prov_cls = registry.get_active_provider("model_routing")
        assert prov_cls is not None
        instance = prov_cls()
        assert isinstance(instance, BaseModelRoutingProvider)
