"""
Unit tests for Data Redaction (SPEC §13.8 / F-0041 / US-73).
"""
import pytest

from sidecar.security.redact import (
    KEY_PATTERNS,
    SENSITIVE_BODY_KEYS,
    SENSITIVE_QUERY_PARAMS,
    DataRedactor,
    mask_token,
)
from sidecar.providers.data_redaction import (
    BaseDataRedactionProvider,
    DefaultDataRedactionProvider,
)
import sidecar.config as config


def test_mask_token_short_token():
    """SPEC §13.8 line 3486: "IF len(token) < 18: RETURN \"***REDACTED***\"" """
    assert mask_token("short_secret") == "***REDACTED***"
    assert mask_token("12345678901234567") == "***REDACTED***"  # 17 chars
    assert mask_token("") == "***REDACTED***"


def test_mask_token_long_token():
    """SPEC §13.8 line 3488: "ELSE: RETURN token[:6] + \"...\" + token[-4:]" """
    token = "sk-abcdefghijklmnopqrstuvwxyz1234"  # 34 chars
    masked = mask_token(token)
    assert masked == "sk-abc...1234"
    assert len(masked) == 13


def test_redact_sensitive_text_openai_key():
    """SPEC §13.8 line 3463: "// Vendor-specific API key patterns (regex)" """
    redactor = DataRedactor()
    raw = "Connecting with key sk-abcdef1234567890abcdef1234567890 to cluster."  # guard:allow-secret
    redacted = redactor.redact_sensitive_text(raw)
    assert "sk-abcdef1234567890" not in redacted
    assert "sk-abc...7890" in redacted


def test_redact_sensitive_text_anthropic_key():
    """SPEC §13.8 line 3463: "// Vendor-specific API key patterns (regex)" """
    redactor = DataRedactor()
    raw = "Header x-api-key: sk-ant-api03-abcdef1234567890123456789012345678901234567890"  # guard:allow-secret
    redacted = redactor.redact_sensitive_text(raw)
    assert "sk-ant-api03-abcdef1234567890" not in redacted
    assert "sk-ant...7890" in redacted


def test_redact_sensitive_text_google_key():
    """SPEC §13.8 line 3463: "// Vendor-specific API key patterns (regex)" """
    redactor = DataRedactor()
    raw = "API key AIzaSyD12345678901234567890123456789012 configured."  # guard:allow-secret
    redacted = redactor.redact_sensitive_text(raw)
    assert "AIzaSyD1234567890" not in redacted
    assert "AIzaSy...9012" in redacted


def test_redact_sensitive_text_github_token():
    """SPEC §13.8 line 3463: "// Vendor-specific API key patterns (regex)" """
    redactor = DataRedactor()
    raw = "GitHub token ghp_1234567890abcdef1234567890abcdef12 in repo settings."  # guard:allow-secret
    redacted = redactor.redact_sensitive_text(raw)
    assert "ghp_1234567890abcdef" not in redacted
    assert "ghp_12...ef12" in redacted


def test_redact_sensitive_text_slack_and_aws_keys():
    """SPEC §13.8 line 3463: "// Vendor-specific API key patterns (regex)" """
    redactor = DataRedactor()
    raw = "Slack: xoxb-123456789012-abcdef123456, AWS: AKIAIOSFODNN7EXAMPLE"  # guard:allow-secret
    redacted = redactor.redact_sensitive_text(raw)
    assert "xoxb-123456789012-abcdef123456" not in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted


def test_redact_sensitive_text_jwt_and_bearer():
    """SPEC §13.8 line 3474: "FUNCTION redact_sensitive_text(text):" """
    redactor = DataRedactor()
    raw = "Authorization: Bearer mysecrettoken1234567890abcdef"
    redacted = redactor.redact_sensitive_text(raw)
    assert "mysecrettoken1234567890abcdef" not in redacted
    assert "Bearer mysecr...cdef" in redacted


def test_redact_sensitive_query_parameters():
    """SPEC §13.8 line 3450: "SENSITIVE_QUERY_PARAMS = {\"access_token\", \"refresh_token\", \"id_token\", ...}" """
    redactor = DataRedactor()
    url = "https://api.example.com/v1/data?api_key=sk-12345678901234567890&format=json&token=short_tok"
    redacted = redactor.redact_sensitive_text(url)
    assert "api_key=sk-12345678901234567890" not in redacted
    assert "format=json" in redacted
    assert "token=***REDACTED***" in redacted


def test_redact_structure_nested_dict_and_list():
    """SPEC §13.8 line 3491: "FUNCTION redact_structure(payload):" """
    redactor = DataRedactor()
    payload = {
        "user": "alice",
        "api_key": "sk-secret12345678901234567890",
        "nested": {
            "password": "supersecretpassword123",
            "session": "short",
            "tags": ["admin", "dev"],
        },
        "log_messages": [
            "Query returned 200",
            "Auth token used: sk-abcdef12345678901234567890",
        ],
    }
    redacted = redactor.redact_structure(payload)
    assert redacted["user"] == "alice"
    assert redacted["api_key"] == "sk-sec...7890"
    assert redacted["nested"]["password"] == "supers...d123"
    assert redacted["nested"]["session"] == "***REDACTED***"
    assert redacted["nested"]["tags"] == ["admin", "dev"]
    assert "sk-abcdef12345678901234567890" not in redacted["log_messages"][1]


def test_redact_structure_preserves_benign_fields():
    """SPEC §13.8 line 3491: "FUNCTION redact_structure(payload):" """
    redactor = DataRedactor()
    payload = {"status": "ok", "count": 42, "items": [{"id": 1, "name": "widget"}]}
    assert redactor.redact_structure(payload) == payload


def test_custom_redaction_patterns():
    """SPEC §13.8 line 3498: "Component: locus-extension/src/security/redact.ts — TypeScript port of regex-based redaction" """
    redactor = DataRedactor(custom_patterns=[r"\bSECRET_CUSTOM_[0-9A-Z]{12,}\b"])
    raw = "Configured token: SECRET_CUSTOM_ABCD1234EFGH5678."
    redacted = redactor.redact_sensitive_text(raw)
    assert "SECRET_CUSTOM_ABCD1234EFGH5678" not in redacted
    assert "SECRET...5678" in redacted


def test_provider_modular_off_switches(monkeypatch):
    """SPEC §13.8 line 3502: "Swappable / off state: locus.security.redaction.enabled (ON by default — secure default)." """
    provider = DefaultDataRedactionProvider()
    assert provider.is_available() is True

    # Test locus.data_redaction.enabled: false
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.data_redaction.enabled" else default)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.data_redaction.enabled" else True)
    assert provider.is_available() is False

    # Test locus.security.redaction.enabled: false
    monkeypatch.setattr(config, "get", lambda k, default=None: False if k == "locus.security.redaction.enabled" else default)
    monkeypatch.setattr(config, "is_enabled", lambda k: False if k == "locus.security.redaction.enabled" else True)
    assert provider.is_available() is False


def test_swappable_provider_swap():
    """SPEC §13.8 line 3502: "Swappable / off state: locus.security.redaction.enabled (ON by default — secure default)." """
    class CustomRedactionProvider(BaseDataRedactionProvider):
        def is_available(self) -> bool:
            return True

        def redact_text(self, text: str) -> str:
            return "[CUSTOM_REDACTED]"

        def redact_payload(self, payload):
            return "[CUSTOM_REDACTED_PAYLOAD]"

        def mask_token(self, token: str) -> str:
            return "[MASKED]"

        def list_patterns(self):
            return []

    custom = CustomRedactionProvider()
    assert isinstance(custom, BaseDataRedactionProvider)
    assert custom.redact_text("sk-secret") == "[CUSTOM_REDACTED]"
    assert custom.redact_payload({"key": "val"}) == "[CUSTOM_REDACTED_PAYLOAD]"
