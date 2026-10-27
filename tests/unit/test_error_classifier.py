"""
Unit tests for Error Classifier engine (F-0065 / US-102).
SPEC §29.1 lines 7435-7471.
"""
from __future__ import annotations

import pytest

from sidecar import config
from sidecar.diagnostics.error_classifier import (
    ErrorCategory,
    ErrorClassification,
    ErrorClassifier,
    RecoveryAction,
)
from sidecar.providers.error_classifier import (
    BaseErrorClassifierProvider,
    DefaultErrorClassifierProvider,
)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.error_classifier.enabled", True)
    config.set("locus.diagnostics.error_classifier.enabled", True)
    yield
    config.set("locus.error_classifier.enabled", True)
    config.set("locus.diagnostics.error_classifier.enabled", True)


def test_classify_rate_limit():
    """SPEC §29.1 line 7445: 'IF error.status == 429: RETURN \"rate_limit\"'"""
    classifier = ErrorClassifier()

    # Via HTTP 429 status int
    res1 = classifier.classify(429)
    assert res1.category == ErrorCategory.RATE_LIMIT.value
    assert res1.action == RecoveryAction.AUTO_RETRY.value
    assert res1.retryable is True
    assert res1.max_retries == 3

    # Via dict with status_code
    res2 = classifier.classify({"status_code": 429, "message": "Too Many Requests"})
    assert res2.category == ErrorCategory.RATE_LIMIT.value

    # Via message string pattern
    res3 = classifier.classify("Quota exceeded for account: rate limit reached")
    assert res3.category == ErrorCategory.RATE_LIMIT.value


def test_classify_auth_failure():
    """SPEC §29.1 line 7446: 'IF error.status IN [401, 403]: RETURN \"auth_failure\"'"""
    classifier = ErrorClassifier()

    # 401 Unauthorized
    res1 = classifier.classify({"status": 401, "message": "Invalid API key provided"})
    assert res1.category == ErrorCategory.AUTH_FAILURE.value
    assert res1.action == RecoveryAction.SURFACE_USER.value
    assert res1.retryable is False

    # 403 Forbidden
    res2 = classifier.classify(403)
    assert res2.category == ErrorCategory.AUTH_FAILURE.value

    # Exception
    res3 = classifier.classify(PermissionError("Unauthorized access attempt"))
    assert res3.category == ErrorCategory.AUTH_FAILURE.value


def test_classify_context_overflow():
    """SPEC §29.1 line 7447: 'IF \"context_length\" IN error.message: RETURN \"context_overflow\"'"""
    classifier = ErrorClassifier()

    res1 = classifier.classify({"status": 400, "message": "Error: context_length_exceeded in prompt tokens"})
    assert res1.category == ErrorCategory.CONTEXT_OVERFLOW.value
    assert res1.action == RecoveryAction.TRIGGER_COMPACTION.value
    assert res1.retryable is True

    res2 = classifier.classify("Maximum context length is 128000 tokens. Prompt is too long.")
    assert res2.category == ErrorCategory.CONTEXT_OVERFLOW.value


def test_classify_timeout():
    """SPEC §29.1 line 7449: 'IF error.type == \"timeout\": RETURN \"timeout\"'"""
    classifier = ErrorClassifier()

    # Dict with type timeout
    res1 = classifier.classify({"type": "timeout", "message": "Request timed out"})
    assert res1.category == ErrorCategory.TIMEOUT.value
    assert res1.action == RecoveryAction.RETRY_SHORTER_CONTEXT.value
    assert res1.retryable is True

    # Python TimeoutError
    res2 = classifier.classify(TimeoutError("Connection timed out after 30000ms"))
    assert res2.category == ErrorCategory.TIMEOUT.value

    # Message pattern
    res3 = classifier.classify("Gateway timeout error from inference gateway")
    assert res3.category == ErrorCategory.TIMEOUT.value


def test_classify_server_error():
    """SPEC §29.1 line 7448: 'IF error.status >= 500: RETURN \"server_error\"'"""
    classifier = ErrorClassifier()

    # Status 500
    res1 = classifier.classify(500)
    assert res1.category == ErrorCategory.SERVER_ERROR.value
    assert res1.action == RecoveryAction.RETRY_THEN_FALLBACK.value
    assert res1.retryable is True
    assert res1.fallback_model_recommended is True

    # Status 503 Bad Gateway / Service Unavailable
    res2 = classifier.classify({"status": 503, "message": "Service Unavailable"})
    assert res2.category == ErrorCategory.SERVER_ERROR.value
    assert res2.fallback_model_recommended is True


def test_classify_content_filter():
    """SPEC §29.1 line 7450: 'IF \"content_filter\" IN error.message: RETURN \"content_filter\"'"""
    classifier = ErrorClassifier()

    res1 = classifier.classify({"status": 400, "message": "Prompt triggered content_filter safety filter"})
    assert res1.category == ErrorCategory.CONTENT_FILTER.value
    assert res1.action == RecoveryAction.REPHRASE_AND_RETRY.value
    assert res1.retryable is True

    res2 = classifier.classify("Response was blocked by policy: content moderation active")
    assert res2.category == ErrorCategory.CONTENT_FILTER.value


def test_classify_unknown():
    """SPEC §29.1 line 7451: 'RETURN \"unknown\"'"""
    classifier = ErrorClassifier()

    res = classifier.classify("A strange unexpected syntax defect happened")
    assert res.category == ErrorCategory.UNKNOWN.value
    assert res.action == RecoveryAction.LOG_AND_CONTINUE.value
    assert res.retryable is False


def test_subsystem_off_switch():
    """SPEC §29.1 line 7464: Subsystem off-switch locus.diagnostics.error_classifier.enabled."""
    classifier = ErrorClassifier()
    config.set("locus.diagnostics.error_classifier.enabled", False)

    res = classifier.classify(429)
    assert res.category == ErrorCategory.UNKNOWN.value
    assert "disabled" in res.explanation.lower()


def test_provider_modular_off_switch():
    """SPEC §29.1 line 7464: Master toggle locus.error_classifier.enabled returns HTTP 503 when off."""
    provider = DefaultErrorClassifierProvider()
    config.set("locus.error_classifier.enabled", False)

    res_cls = provider.classify_error(429)
    assert res_cls["status_code"] == 503
    assert res_cls["disabled"] == "locus.error_classifier.enabled"

    res_tax = provider.get_taxonomy()
    assert res_tax["status_code"] == 503

    res_st = provider.get_status()
    assert res_st["status_code"] == 503


def test_provider_normal_delegation():
    """SPEC §29.1: Provider normal operation when enabled."""
    provider = DefaultErrorClassifierProvider()
    config.set("locus.error_classifier.enabled", True)

    res_cls = provider.classify_error({"status": 429, "message": "Rate limit reached"})
    assert res_cls["status_code"] == 200
    assert res_cls["category"] == "rate_limit"
    assert res_cls["action"] == "auto_retry"

    res_tax = provider.get_taxonomy()
    assert res_tax["status_code"] == 200
    assert len(res_tax["categories"]) == 7

    res_st = provider.get_status()
    assert res_st["status_code"] == 200
    assert res_st["provider_enabled"] is True


def test_provider_polymorphism():
    """SPEC §29.1: BaseErrorClassifierProvider polymorphic compliance."""
    class CustomErrorClassifierProvider(BaseErrorClassifierProvider):
        @property
        def name(self) -> str:
            return "custom_classifier"

        def is_feature_enabled(self):
            return True, ""

        def classify_error(self, error):
            return {"category": "custom_cat", "action": "custom_act", "status_code": 200}

        def get_taxonomy(self):
            return {"custom": True, "status_code": 200}

        def get_status(self):
            return {"custom_status": "ok", "status_code": 200}

    prov = CustomErrorClassifierProvider()
    assert prov.name == "custom_classifier"
    assert prov.classify_error("error")["category"] == "custom_cat"
