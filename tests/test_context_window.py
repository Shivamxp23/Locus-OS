import pytest
from sidecar.context.headroom_adapter import (
    CompactionOptions,
    CompactionResult,
    estimate_context_tokens,
    should_compact,
    HeadroomCompactionAdapter,
)


def test_estimate_and_threshold():
    messages = [
        {"role": "user", "content": "Hello Locus!"},
        {"role": "assistant", "content": "Hello! How can I help you today?"},
    ]
    tokens = estimate_context_tokens(messages)
    assert tokens > 0
    assert not should_compact(tokens, threshold_tokens=1000)
    assert should_compact(tokens, threshold_tokens=5)


def test_headroom_compaction_adapter():
    adapter = HeadroomCompactionAdapter()
    long_code = "def process_data():\n\n\n    pass\n\n\n" * 15
    messages = [
        {"role": "system", "content": "System prompt."},
        {"role": "user", "content": "First instruction"},
        {"role": "assistant", "content": long_code},
        {"role": "user", "content": "Recent question?"},
        {"role": "assistant", "content": "Recent answer."},
    ]

    res = adapter.compact(messages, CompactionOptions(protect_first_n=1, protect_last_n=2))
    assert res.compacted_tokens <= res.original_tokens
    assert len(res.compacted_messages) == len(messages)
