import pytest
from sidecar.context_compressor import (
    ContextEngine,
    compress_context,
)


def test_should_compress_threshold():
    eng = ContextEngine(context_length=1000, threshold_percent=0.75)
    assert eng.threshold_tokens == 750
    assert not eng.should_compress(700)
    assert eng.should_compress(750)
    assert eng.should_compress(800)


def test_short_messages_not_compressed():
    messages = [
        {"role": "system", "content": "You are Locus."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there"},
    ]
    eng = ContextEngine(protect_first_n=2, protect_last_n=2)
    result = eng.compress(messages)
    assert len(result) == len(messages)
    assert eng.compression_count == 0


def test_middle_compaction_with_preserved_boundaries():
    eng = ContextEngine(protect_first_n=2, protect_last_n=2)
    messages = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "First user msg"},
        {"role": "assistant", "content": "First asst msg"},
        # Middle to compress
        {"role": "user", "content": "Mid 1"},
        {"role": "assistant", "content": "Mid 2"},
        {"role": "user", "content": "Mid 3"},
        # Tail to preserve
        {"role": "user", "content": "Tail user msg"},
        {"role": "assistant", "content": "Tail asst msg"},
    ]

    result = eng.compress(messages, focus_topic="Memory tri-stack")
    # Expected: 3 head (sys + 2) + 1 summary + 2 tail = 6 messages
    assert len(result) == 6
    assert result[0]["content"] == "System prompt"
    assert result[1]["content"] == "First user msg"
    assert result[2]["content"] == "First asst msg"
    assert result[3]["role"] == "system"
    assert "[Previous context summary]" in result[3]["content"]
    assert "Memory tri-stack" in result[3]["content"]
    assert result[4]["content"] == "Tail user msg"
    assert result[5]["content"] == "Tail asst msg"
    assert eng.compression_count == 1
