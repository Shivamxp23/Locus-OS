"""
SPEC §13.10 lines 3599-3668: Unit tests for Message Sanitization (F-0043 / US-75).
"""
from __future__ import annotations

import json
import pytest

import sidecar.config as config
from sidecar.providers.message_sanitizer import (
    BaseMessageSanitizerProvider,
    DefaultMessageSanitizerProvider,
)
from sidecar.security.sanitizer import (
    MessageSanitizer,
    SURROGATE_RE,
    sanitize_messages,
    sanitize_structure_surrogates,
    sanitize_surrogates,
)


def test_sanitize_clean_text_unchanged():
    """SPEC §13.10 line 3617: "RETURN text // fast no-op when clean" """
    clean = "Hello world! Valid unicode string: café 🚀 and symbols."
    assert sanitize_surrogates(clean) == clean


def test_sanitize_surrogate_replacement():
    """SPEC §13.10 line 3616: "RETURN SURROGATE_RE.replace_all(text, '\uFFFD') // U+FFFD replacement character" """
    corrupt = "Invalid\ud800high\udbffsurrogates\udc00and\udffflow"
    sanitized = sanitize_surrogates(corrupt)
    assert "\ud800" not in sanitized
    assert "\udbff" not in sanitized
    assert "\udc00" not in sanitized
    assert "\udfff" not in sanitized
    assert "\ufffd" in sanitized
    assert sanitized == "Invalid\ufffdhigh\ufffdsurrogates\ufffdand\ufffdlow"
    # Verify sanitized string serializes to JSON and round-trips without encoding failure
    dumped = json.dumps({"text": sanitized})
    assert json.loads(dumped)["text"] == sanitized


def test_sanitize_structure_nested_dict_and_list():
    """SPEC §13.10 line 3620: "FUNCTION sanitize_structure_surrogates(payload): Walk nested dict/list payloads IN-PLACE" """
    payload = {
        "status": "ok",
        "user": "Alice\ud800Corrupt",
        "nested": {
            "prompt": "Fix bug\ud900here",
            "tags": ["admin", "test\udbffend"],
        },
        "reasoning_details": [
            {"summary": "Normal thought"},
            {"summary": "Bad\udc00char"},
        ],
    }
    sanitized, found = sanitize_structure_surrogates(payload)
    assert found is True
    assert sanitized["user"] == "Alice\ufffdCorrupt"
    assert sanitized["nested"]["prompt"] == "Fix bug\ufffdhere"
    assert sanitized["nested"]["tags"][1] == "test\ufffdend"
    assert sanitized["reasoning_details"][1]["summary"] == "Bad\ufffdchar"


def test_sanitize_structure_clean_returns_false_found():
    """SPEC §13.10 line 3622: Fast path for clean structures."""
    payload = {
        "user": "alice",
        "items": [1, 2, "three", {"sub": "clean"}],
    }
    sanitized, found = sanitize_structure_surrogates(payload)
    assert found is False
    assert sanitized == payload


def test_sanitize_messages_array():
    """SPEC §13.10 line 3644: "FUNCTION sanitize_messages(messages): Apply to entire message list before sending to LLM API" """
    messages = [
        {"role": "user", "content": "Clean prompt"},
        {
            "role": "assistant",
            "content": "Result with corrupt\ud800char",
            "tool_calls": [
                {"id": "call_1", "function": {"arguments": "{\"query\": \"term\udbff\"}"}}
            ],
            "metadata": {"source": "test\udc00data"},
        },
    ]
    cleaned = sanitize_messages(messages)
    assert cleaned[0]["content"] == "Clean prompt"
    assert "\ud800" not in cleaned[1]["content"]
    assert "\ufffd" in cleaned[1]["content"]
    assert "\udbff" not in cleaned[1]["tool_calls"][0]["function"]["arguments"]
    assert "\ufffd" in cleaned[1]["tool_calls"][0]["function"]["arguments"]
    assert "\udc00" not in cleaned[1]["metadata"]["source"]
    assert "\ufffd" in cleaned[1]["metadata"]["source"]


def test_provider_modular_off_switches(monkeypatch: pytest.MonkeyPatch):
    """SPEC §13.10 line 3662: Modular off-switches for message sanitization."""
    provider = DefaultMessageSanitizerProvider()
    assert provider.is_enabled() is True

    # Off switch 1: locus.message_sanitization.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.message_sanitization.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.message_sanitization.enabled" else True)
    assert provider.is_enabled() is False
    # When off, raw input passes through unedited
    raw_corrupt = "bad\ud800str"
    assert provider.sanitize_text(raw_corrupt) == raw_corrupt

    # Off switch 2: locus.security.message_sanitization.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.message_sanitization.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.message_sanitization.enabled" else True)
    assert provider.is_enabled() is False


def test_swappable_provider_swap():
    """SPEC §13.10 line 3662: Modularity and swappable provider interface."""
    class CustomMessageSanitizerProvider(BaseMessageSanitizerProvider):
        def sanitize_text(self, text: str) -> str:
            return "[CUSTOM_SANITIZED]"

        def sanitize_structure(self, payload):
            return "[CUSTOM_SANITIZED_STRUCT]", True

        def sanitize_messages(self, messages):
            return [{"role": "system", "content": "custom"}]

    custom = CustomMessageSanitizerProvider()
    assert isinstance(custom, BaseMessageSanitizerProvider)
    assert custom.sanitize_text("any") == "[CUSTOM_SANITIZED]"
    assert custom.sanitize_structure({}) == ("[CUSTOM_SANITIZED_STRUCT]", True)
    assert len(custom.sanitize_messages([])) == 1
