"""
SPEC §2.6a / F-0097 / US-36: Streaming (SSE) Unit Tests.
Asserts event formatting, wire parsing, keepalive heartbeats, chunk streaming,
provider registration, swappability, and modular off-switch handling.
"""
import asyncio
import pytest
from pathlib import Path

from sidecar import config
from sidecar.registry import get_registry
from sidecar.providers.streaming_sse import (
    BaseStreamingSSEProvider,
    SSEEvent,
    StreamOptions,
)
from sidecar.streaming_sse import (
    StreamingSSEProvider,
    is_streaming_enabled,
)


def test_sse_event_encoding_basic():
    """SPEC §2.6a line 2644: "Feature §2.6a: Streaming (SSE)" - Encode standard SSE frame."""
    evt = SSEEvent(data="hello world", event="delta", id="1", retry=5000)
    raw = evt.encode()
    assert "id: 1\n" in raw
    assert "event: delta\n" in raw
    assert "retry: 5000\n" in raw
    assert "data: hello world\n\n" in raw


def test_sse_event_encoding_multiline():
    """SPEC §2.6a line 2647: "Scope: Built-in SSE streaming. Inherited unchanged." - Multiline data format."""
    evt = SSEEvent(data="line 1\nline 2\nline 3")
    raw = evt.encode()
    assert "data: line 1\n" in raw
    assert "data: line 2\n" in raw
    assert "data: line 3\n\n" in raw


def test_streaming_provider_format_event_json():
    """SPEC §2.6a line 2645: "Verdict: 📦 KEEP-PI · Source: pi/stream.ts" - JSON structured streaming format."""
    provider = StreamingSSEProvider()
    out = provider.format_event({"token": "antigravity", "index": 42}, event="token")
    assert "event: token\n" in out
    assert '"token": "antigravity"' in out
    assert '"index": 42' in out


def test_streaming_provider_parse_event():
    """SPEC §2.6a line 2647: "Built-in SSE streaming. Inherited unchanged." - Frame parser logic."""
    provider = StreamingSSEProvider()
    raw = (
        ": heartbeat comment\n"
        "id: 99\n"
        "event: custom\n"
        "retry: 2500\n"
        "data: first part\n"
        "data: second part\n\n"
    )
    evt = provider.parse_event(raw)
    assert evt.id == "99"
    assert evt.event == "custom"
    assert evt.retry == 2500
    assert evt.data == "first part\nsecond part"


def test_streaming_provider_ping_heartbeat():
    """SPEC §2.6a line 2644: "Feature §2.6a: Streaming (SSE)" - Keep-alive heartbeat generation."""
    provider = StreamingSSEProvider()
    ping_frame = provider.format_ping()
    assert "event: ping\n" in ping_frame
    assert '"type": "ping"' in ping_frame


@pytest.mark.asyncio
async def test_streaming_text_chunks():
    """SPEC §2.6a line 2647: "Scope: Built-in SSE streaming. Inherited unchanged." - Text chunking stream."""
    provider = StreamingSSEProvider()
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = []
    async for chunk in provider.stream_text_chunks(text, chunk_size=10):
        chunks.append(chunk)

    # 26 chars / 10 = 3 text chunks + 1 terminal done chunk = 4 chunks
    assert len(chunks) == 4
    parsed_chunks = [provider.parse_event(c) for c in chunks]
    assert "abcdefghij" in parsed_chunks[0].data
    assert "klmnopqrst" in parsed_chunks[1].data
    assert "uvwxyz" in parsed_chunks[2].data
    assert '"done": true' in parsed_chunks[3].data


@pytest.mark.asyncio
async def test_streaming_token_generator():
    """SPEC §2.6a line 2645: "Verdict: 📦 KEEP-PI · Source: pi/stream.ts" - Token generator streaming."""
    provider = StreamingSSEProvider()

    async def token_gen():
        tokens = ["Thought: ", "Processing ", "query..."]
        for t in tokens:
            yield t

    output_events = []
    async for evt_str in provider.stream_tokens(token_gen(), event_name="delta"):
        output_events.append(provider.parse_event(evt_str))

    assert len(output_events) == 4  # 3 tokens + 1 terminal
    assert "Thought: " in output_events[0].data
    assert "Processing " in output_events[1].data
    assert "query..." in output_events[2].data
    assert '"done": true' in output_events[3].data


def test_streaming_sse_provider_registration_and_swap():
    """SPEC §2.6a: Provider registration and swappability per modularity architecture (03)."""
    reg = get_registry()
    provider_cls = reg.get_active_provider("streaming_sse", default_name="default")
    assert provider_cls is StreamingSSEProvider

    class MockCustomStreamer(BaseStreamingSSEProvider):
        def format_event(self, data, event=None, id=None, retry=None):
            return f"custom:{data}\n\n"

        def parse_event(self, raw_frame):
            return SSEEvent(data=raw_frame)

        def format_ping(self):
            return "custom:ping\n\n"

        async def stream_tokens(self, token_generator, event_name="delta"):
            yield "custom:stream\n\n"

        async def stream_text_chunks(self, text, chunk_size=16, event_name="delta"):
            yield f"custom:{text}\n\n"

    reg.register("streaming_sse", "custom", MockCustomStreamer)
    active_cls = reg.get("streaming_sse", "custom")
    assert active_cls is MockCustomStreamer

    # Restore default
    reg.register("streaming_sse", "default", StreamingSSEProvider)


def test_extension_component_exports():
    """SPEC §2.6a line 2645: Extension implementation in locus-extension/src/streaming-sse.ts"""
    ts_file = Path("locus-extension/src/streaming-sse.ts")
    assert ts_file.is_file()
    content = ts_file.read_text(encoding="utf-8")
    assert "export class SSEFrameDecoder" in content
    assert "export class StreamingSSEConsumer" in content
    assert "export const DEFAULT_STREAMING_CONFIG" in content


def test_modular_off_switch_behavior(monkeypatch):
    """SPEC §2.6a line 2646: Off state handled via locus.streaming_sse.enabled."""
    monkeypatch.setattr(config, "get", lambda key, default=None: True)
    assert is_streaming_enabled() is True

    monkeypatch.setattr(config, "get", lambda key, default=None: False if "streaming_sse" in key else True)
    assert is_streaming_enabled() is False
