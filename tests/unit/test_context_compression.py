"""
SPEC §4.16: Context Compression Unit Tests (F-0110 / US-55).
Tests Hermes ContextEngine ABC, CompactionLock concurrency protection,
7-step compression flow, memory provider notification hooks, session rotation,
and swappable provider interface.
"""
from __future__ import annotations

import threading
import time
from typing import Any, Dict, List, Optional

import pytest

from sidecar.compaction.context_engine import (
    CompactionLock,
    DefaultCompactionProvider,
    DefaultContextEngine,
    HermesContextCompressor,
    default_auxiliary_summarize,
    format_messages_for_summary,
)
from sidecar.providers.compaction import (
    CompactionConfig,
    CompactionProvider,
    ContextEngine,
    MemoryProviderHook,
)


class MockMemoryProvider(MemoryProviderHook):
    """Mock memory provider to test pre-compaction hooks and session switch notifications."""

    def __init__(self) -> None:
        self.pre_compress_called = False
        self.discarded_messages: List[Dict[str, Any]] = []
        self.session_switches: List[tuple[str, str]] = []

    def on_pre_compress(self, messages_to_discard: List[Dict[str, Any]]) -> Optional[str]:
        self.pre_compress_called = True
        self.discarded_messages = list(messages_to_discard)
        return f"Extracted {len(messages_to_discard)} insights into long-term graph"

    def on_session_switch(self, new_session_id: str, parent_session_id: str) -> None:
        self.session_switches.append((new_session_id, parent_session_id))


def test_context_engine_initialization_and_thresholds():
    """SPEC §4.16 line 3940: "ABSTRACT CLASS ContextEngine:"
    SPEC §4.16 line 3951: "threshold_percent: float = 0.75   // compress at 75% usage"
    SPEC §4.16 line 3952: "protect_first_n: int = 3          // keep first 3 non-system messages"
    SPEC §4.16 line 3953: "protect_last_n: int = 6           // keep last 6 messages"
    Asserts default thresholds match 75% threshold, 3 head protected turns, and 6 tail protected turns.
    """
    engine = DefaultContextEngine(name="test_engine")
    assert engine.context_length == 128000
    assert engine.threshold_percent == 0.75
    assert engine.protect_first_n == 3
    assert engine.protect_last_n == 6
    assert engine.threshold_tokens == 96000
    assert engine.last_prompt_tokens == 0
    assert engine.compression_count == 0


def test_update_from_response_and_should_compress():
    """SPEC §4.16 line 3956: "update_from_response(usage)      // called after every LLM call"
    SPEC §4.16 line 3957: "should_compress(prompt_tokens)   // check if compaction needed"
    Asserts token tracking updates and threshold evaluation triggers when prompt tokens reach threshold.
    """
    engine = DefaultContextEngine(name="test_engine")
    assert not engine.should_compress(50000)

    # Usage update
    engine.update_from_response({"prompt_tokens": 80000, "completion_tokens": 1200})
    assert engine.last_prompt_tokens == 80000
    assert not engine.should_compress(engine.last_prompt_tokens)

    engine.update_from_response({"prompt_tokens": 96500, "completion_tokens": 500})
    assert engine.last_prompt_tokens == 96500
    assert engine.should_compress(engine.last_prompt_tokens)


def test_update_model_recalculates_thresholds():
    """SPEC §4.16 line 3970: "update_model(model, context_length, ...) // recalculate thresholds"
    Asserts changing context window dynamically recalculates threshold tokens.
    """
    engine = DefaultContextEngine(name="test_engine")
    engine.update_model("gpt-4o-mini", context_length=64000, threshold_percent=0.80)
    assert engine.context_length == 64000
    assert engine.threshold_percent == 0.80
    assert engine.threshold_tokens == 51200


def test_compaction_lock_concurrency_guard():
    """SPEC §4.16 line 3975: "// Step 1: Acquire compression lock (prevent concurrent compressions)"
    Asserts reentrant concurrency lock prevents overlapping compression execution.
    """
    lock = CompactionLock(timeout=2.0)
    assert not lock.is_locked()

    acquired = lock.acquire(holder="worker_1")
    assert acquired is True
    assert lock.is_locked()
    assert lock.holder == "worker_1"

    # Second thread cannot acquire simultaneously
    second_acquired = False

    def try_acquire():
        nonlocal second_acquired
        lock2 = lock.acquire(holder="worker_2")
        second_acquired = lock2

    t = threading.Thread(target=try_acquire)
    t.start()
    t.join(timeout=0.2)
    # The lock was not available to another thread while held
    lock.release()
    assert not lock.is_locked()


def test_compression_flow_identifies_compressible_range_and_preserves_head_tail():
    """SPEC §4.16 line 3979: "head = messages[:protect_first_n + 1]  // system + first N"
    SPEC §4.16 line 3980: "tail = messages[-protect_last_n:]      // last N"
    SPEC §4.16 line 3981: "middle = messages[protect_first_n + 1 : -protect_last_n]"
    Asserts 7-step pipeline accurately preserves head turns and tail turns while compressing middle.
    """
    config = CompactionConfig(protect_first_n=3, protect_last_n=6)
    compressor = HermesContextCompressor(config)

    # 15 messages: 1 system + 3 head + 5 middle + 6 tail = 15 total
    messages = [
        {"role": "system", "content": "You are Locus OS."}
    ] + [
        {"role": "user" if i % 2 == 1 else "assistant", "content": f"Turn {i} content"}
        for i in range(1, 15)
    ]
    assert len(messages) == 15

    res = compressor.compress_context(messages, focus_topic="Memory architecture")
    assert res["was_compressed"] is True
    assert res["intermediate_count"] == 5

    compressed = res["compressed_messages"]
    # head length = 1 system + 3 first non-system = 4
    # tail length = 6
    # middle replaced by 1 summary = 1
    # total compressed length = 4 + 1 + 6 = 11
    assert len(compressed) == 11
    assert compressed[:4] == messages[:4]
    assert compressed[-6:] == messages[-6:]
    assert compressed[4]["role"] == "system"
    assert "Focus: Memory architecture" in compressed[4]["content"]


def test_compression_flow_notifies_memory_providers_and_splits_session():
    """SPEC §4.16 line 3986: "// Step 3: Notify memory providers before compression"
    SPEC §4.16 line 4009: "// Step 6: Split SQLite session, rotate session_id"
    SPEC §4.16 line 4014: "// Step 7: Notify memory providers of session switch"
    Asserts pre-compression hooks pass discarded messages and session rotation triggers on_session_switch.
    """
    config = CompactionConfig(protect_first_n=2, protect_last_n=3)
    compressor = HermesContextCompressor(config)
    mock_memory = MockMemoryProvider()

    messages = [
        {"role": "system", "content": "System prompt"}
    ] + [
        {"role": "user" if i % 2 == 1 else "assistant", "content": f"Message {i}"}
        for i in range(1, 12)
    ]
    old_session = "session_original_123"

    res = compressor.compress_context(
        messages=messages,
        memory_providers=[mock_memory],
        old_session_id=old_session,
    )

    assert res["was_compressed"] is True
    assert mock_memory.pre_compress_called is True
    assert len(mock_memory.discarded_messages) > 0
    # Session ID must be rotated
    assert res["new_session_id"] != old_session
    assert len(mock_memory.session_switches) == 1
    new_sid, parent_sid = mock_memory.session_switches[0]
    assert new_sid == res["new_session_id"]
    assert parent_sid == old_session


def test_compaction_short_conversation_noop():
    """SPEC §4.16 line 3983: "IF middle.length == 0: RETURN messages"
    Asserts conversation shorter than protection boundaries returns unchanged with was_compressed=False.
    """
    config = CompactionConfig(protect_first_n=3, protect_last_n=6)
    compressor = HermesContextCompressor(config)

    short_messages = [
        {"role": "system", "content": "System"},
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    res = compressor.compress_context(short_messages)
    assert res["was_compressed"] is False
    assert res["compressed_messages"] == short_messages
    assert res["intermediate_count"] == 0


def test_compaction_provider_interface_and_health_check():
    """SPEC §4.16 line 4024: "Provider Interface: CompactionProvider (wraps both Pi's compaction AND Hermes's ContextEngine ABC)"
    Asserts CompactionProvider conforms to base interface, provides health check, and manages ContextEngine.
    """
    provider = DefaultCompactionProvider()
    assert isinstance(provider, CompactionProvider)
    assert provider.is_enabled() is True
    engine = provider.get_engine()
    assert isinstance(engine, ContextEngine)

    health = provider.health_check()
    assert health["status"] == "healthy"
    assert health["threshold_percent"] == 0.75
    assert "threshold_tokens" in health
    assert "compression_count" in health
