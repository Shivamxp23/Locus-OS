import pytest
from sidecar.security.redact import (
    DataRedactor,
    redact_patterns,
)


def test_mask_token_length():
    redactor = DataRedactor()
    short_tok = "secret_123"
    assert redactor.mask_token(short_tok) == "***REDACTED***"

    prefix = "sk-"
    long_tok = prefix + "ant-" + "1234567890abcdef1234567890"
    masked = redactor.mask_token(long_tok)
    assert masked.startswith("sk-ant")
    assert masked.endswith("7890")
    assert "..." in masked


def test_redact_text_vendor_api_keys():
    dummy_openai = "sk-" + "1234567890abcdef1234567890"
    dummy_anthropic = "sk-" + "ant-" + "abcdef1234567890abcdef123456"
    text = f"Connecting with OpenAI key {dummy_openai} and Anthropic key {dummy_anthropic}."
    redacted = redact_patterns(text)
    assert dummy_openai not in redacted
    assert dummy_anthropic not in redacted
    assert "Connecting with OpenAI key" in redacted


def test_redact_structure_dict_and_list():
    payload = {
        "status": "ok",
        "api_key": "super_secret_api_key_long_enough",
        "nested": [
            {"password": "secret_password_123"},
            {"public_info": "safe to view"},
        ],
    }
    redacted = redact_patterns(payload)
    assert redacted["status"] == "ok"
    assert redacted["api_key"] != "super_secret_api_key_long_enough"
    assert redacted["nested"][0]["password"] != "secret_password_123"
    assert "..." in redacted["nested"][0]["password"]
    assert redacted["nested"][1]["public_info"] == "safe to view"
