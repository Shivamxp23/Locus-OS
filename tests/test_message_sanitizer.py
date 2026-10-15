import pytest
from sidecar.security.sanitizer import MessageSanitizer


def test_sanitize_clean_text_unchanged():
    sanitizer = MessageSanitizer()
    clean = "Hello world! Valid unicode string: café 🚀"
    assert sanitizer.sanitize_text(clean) == clean


def test_sanitize_surrogate_replacement():
    sanitizer = MessageSanitizer()
    # High surrogate \ud800
    invalid_text = "Corrupt\ud800text"
    sanitized = sanitizer.sanitize_text(invalid_text)
    assert "\ud800" not in sanitized
    assert "\uFFFD" in sanitized
    assert sanitized == "Corrupt\uFFFDtext"


def test_sanitize_messages_recursive():
    sanitizer = MessageSanitizer()
    messages = [
        {"role": "user", "content": "Clean message"},
        {
            "role": "assistant",
            "content": "Message with bad surrogate \ud900 here",
            "metadata": {"nested_bad": "\udbff"},
        },
    ]
    cleaned = sanitizer.sanitize_messages(messages)
    assert cleaned[0]["content"] == "Clean message"
    assert "\ud900" not in cleaned[1]["content"]
    assert "\uFFFD" in cleaned[1]["content"]
    assert "\udbff" not in cleaned[1]["metadata"]["nested_bad"]
    assert "\uFFFD" in cleaned[1]["metadata"]["nested_bad"]
