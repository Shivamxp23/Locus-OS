"""
Unit tests for Context Window Management & Headroom CCR (SPEC §1.6 & §4.17, F-0006).
Asserts token estimation, shouldCompact thresholding, preservation of first-3 and last-6 messages,
CCR reversibility, inflation guard, and modular off-switch behavior.
"""
import pytest

from sidecar.context.headroom_adapter import HeadroomCCRAdapter
from sidecar.providers.context_compression import CompactionResult


def test_estimate_context_tokens():
    """SPEC §1.6 line 560: "estimateContextTokens(messages) → rough count"
    Asserts token estimation calculates expected counts for strings and message lists.
    """
    adapter = HeadroomCCRAdapter()
    # String estimation
    assert adapter.estimate_tokens("") == 0
    assert adapter.estimate_tokens("Hello world") >= 2
    long_text = "This is a detailed sentence describing architectural requirements. " * 10
    tokens = adapter.estimate_tokens(long_text)
    assert tokens > 50

    # Message list estimation
    messages = [
        {"role": "user", "content": "How do I build Locus?"},
        {"role": "assistant", "content": "Follow the agile spec protocol step by step."},
    ]
    total_tokens = adapter.estimate_tokens(messages)
    assert total_tokens > 15


def test_should_compact_threshold_evaluation():
    """SPEC §1.6 line 561: "shouldCompact(promptTokens, threshold) → bool"
    Asserts threshold evaluation correctly identifies when context needs compaction.
    """
    adapter = HeadroomCCRAdapter()
    assert not adapter.should_compact(current_tokens=5000, threshold=8000)
    assert adapter.should_compact(current_tokens=8000, threshold=8000)
    assert adapter.should_compact(current_tokens=9500, threshold=8000)


def test_compaction_preservation_bounds():
    """SPEC §1.6 line 565: "- protect_first_n = 3 (first 3 non-system messages)"
    Asserts compaction preserves first 3 messages and last 6 messages uncompressed.
    """
    adapter = HeadroomCCRAdapter()
    # Create 15 conversational turns
    messages = [
        {"role": "user", "content": f"Turn {i} question: What is step {i}?"}
        if i % 2 == 1
        else {"role": "assistant", "content": f"Turn {i} answer: This is step {i} explanation with details."}
        for i in range(1, 16)
    ]
    assert len(messages) == 15

    res = adapter.compact(messages, protect_first_n=3, protect_last_n=6)
    assert isinstance(res, CompactionResult)
    # First 3 messages must match original
    assert res.compressed_messages[:3] == messages[:3]
    # Last 6 messages must match original
    assert res.compressed_messages[-6:] == messages[-6:]
    # Middle 6 messages (turns 4 to 9) were compressed into a summary entry
    assert len(res.compressed_messages) == 3 + 1 + 6
    summary_entry = res.compressed_messages[3]
    assert summary_entry["role"] == "system"
    assert "Headroom CCR" in summary_entry["content"]
    assert len(res.cached_keys) == 1
    assert res.ratio < 1.0


def test_ccr_reversible_retrieval(tmp_path):
    """SPEC §1.6 line 577: "Locus replaces Pi's default compaction with Headroom CCR (§4.17)"
    Asserts original content is cached and retrievable via cache key.
    """
    adapter = HeadroomCCRAdapter(cache_dir=tmp_path)
    original_text = "Important architecture details that must not be permanently lost from memory."
    comp_res = adapter.compress_text(original_text)

    cache_key = comp_res["cache_key"]
    assert cache_key != ""
    # Retrieve original text using cache key
    retrieved = adapter.retrieve_original(cache_key)
    assert retrieved == original_text


def test_inflation_guard_protection():
    """SPEC §1.6 line 577: "Locus replaces Pi's default compaction with Headroom CCR (§4.17)"
    Asserts inflation guard reverts to original if compression would increase tokens.
    """
    adapter = HeadroomCCRAdapter()
    # A short text where wrapping in metadata or CCR headers would increase tokens
    tiny_text = "Hi"
    res = adapter.compress_text(tiny_text)
    # Inflation guard triggers, keeping original text
    assert res["inflated"] is True
    assert res["compressed"] == tiny_text
    assert res["compressed_tokens"] == res["original_tokens"]


def test_context_compression_disabled_passthrough():
    """SPEC §1.6 line 579: "Swappable / off state: locus.compaction.provider (headroom-ccr | pi-default | simple-summarize). Off → raw message history grows unbounded until the LLM's context limit is hit."
    Asserts disabled context compaction leaves raw message history unbounded and unmodified.
    """
    adapter = HeadroomCCRAdapter(custom_config={"locus.context_window_management.enabled": False})
    messages = [
        {"role": "user", "content": f"Turn {i}"}
        for i in range(12)
    ]
    res = adapter.compact(messages, protect_first_n=3, protect_last_n=6)
    assert res.compressed_messages == messages
    assert res.ratio == 1.0
    assert "disabled" in res.summary.lower()
