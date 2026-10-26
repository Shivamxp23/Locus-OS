"""
SPEC §13.9 lines 3513-3598: Unit tests for Think Token Scrubbing (F-0042 / US-74).
"""
from __future__ import annotations

import pytest

import sidecar.config as config
from sidecar.providers.think_scrubber import (
    BaseThinkScrubberProvider,
    DefaultThinkScrubberProvider,
)
from sidecar.security.think_scrubber import (
    SUPPORTED_TAGS,
    ScrubState,
    StreamingThinkScrubber,
    ThinkTokenScrubber,
)


def test_streaming_scrubber_removes_think_block():
    """SPEC §13.9 line 3530: "Stateful streaming state machine that strips <think> blocks" """
    scrubber = StreamingThinkScrubber()
    chunks = ["<think>Internal reasoning step</think>", "Hello world!"]
    visible = "".join(scrubber.feed(c) for c in chunks) + scrubber.flush()
    assert "<think>" not in visible
    assert "</think>" not in visible
    assert "Internal reasoning" not in visible
    assert visible == "Hello world!"


def test_streaming_scrubber_all_supported_tags():
    """SPEC §13.9 line 3532: "SUPPORTED_TAGS = ['think', 'thinking', 'reasoning', 'thought', 'REASONING_SCRATCHPAD']" """
    scrubber = StreamingThinkScrubber()
    for tag in SUPPORTED_TAGS:
        scrubber.reset()
        raw = f"<{tag}>secret thought inside {tag}</{tag}>Visible answer for {tag}"
        res = scrubber.process_complete(raw)
        assert f"<{tag}>" not in res
        assert f"</{tag}>" not in res
        assert f"secret thought inside {tag}" not in res
        assert res == f"Visible answer for {tag}"


def test_streaming_scrubber_partial_tags_across_deltas():
    """SPEC §13.9 line 3530: "Handles partial tags at delta boundaries, preventing reasoning leakage." """
    scrubber = StreamingThinkScrubber()
    # Tag split into partial deltas: "<thi", "nk>", "reasoning here", "</thi", "nk>", " Clean text"
    deltas = ["<thi", "nk>", "reasoning here", "</thi", "nk>", " Clean text"]
    emitted = []
    for d in deltas:
        emitted.append(scrubber.feed(d))
    emitted.append(scrubber.flush())
    combined = "".join(emitted)
    assert "<think>" not in combined
    assert "</think>" not in combined
    assert "reasoning here" not in combined
    assert combined == " Clean text"


def test_block_boundary_prose_mention_preserved():
    """SPEC §13.9 line 3557: "Prose mention (e.g. 'use <think> tags here') — emit as text" """
    scrubber = StreamingThinkScrubber()
    raw = "You can write <think> tags in your prompt."
    res = scrubber.process_complete(raw)
    # Because <think> is preceded by non-whitespace prose on the current line, it is preserved
    assert res == "You can write <think> tags in your prompt."


def test_block_boundary_newline_triggers_block():
    """SPEC §13.9 line 3554: "only suppress if tag is at start of stream, after newline, or only whitespace" """
    scrubber = StreamingThinkScrubber()
    raw = "First line.\n<think>\nsecret thoughts\n</think>\nSecond line."
    res = scrubber.process_complete(raw)
    assert "secret thoughts" not in res
    assert "<think>" not in res
    assert "</think>" not in res
    assert "First line." in res
    assert "Second line." in res


def test_unclosed_block_at_end_of_stream():
    """SPEC §13.9 line 3564: "Swallow entire block content — never reaches user" """
    scrubber = StreamingThinkScrubber()
    raw = "Start text\n<think>Model response was truncated mid-thought"
    res = scrubber.process_complete(raw)
    assert "<think>" not in res
    assert "Model response was truncated" not in res
    assert res == "Start text"


def test_incomplete_tag_flushed_as_plain_text():
    """SPEC §13.9 line 3568: "FUNCTION flush() -> visible_text: emit any held-back text that turned out not to be a tag" """
    scrubber = StreamingThinkScrubber()
    # Emits text ending with '<thi' where stream terminates without completing '<think>'
    part1 = scrubber.feed("Look at this equation: x < 5 and y < thi")
    part2 = scrubber.flush()
    total = part1 + part2
    assert total == "Look at this equation: x < 5 and y < thi"


def test_provider_modular_off_switches(monkeypatch: pytest.MonkeyPatch):
    """SPEC §13.9 line 3591: "Swappable / off state: locus.security.think_scrubbing.enabled." """
    provider = DefaultThinkScrubberProvider()
    assert provider.is_enabled() is True

    # Off switch 1: locus.think_token_scrubbing.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.think_token_scrubbing.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.think_token_scrubbing.enabled" else True)
    assert provider.is_enabled() is False
    # When off, raw text passes through untouched
    assert provider.scrub_text("<think>leak</think>hello") == "<think>leak</think>hello"
    assert provider.feed_chunk("<think>leak") == "<think>leak"

    # Off switch 2: locus.security.think_scrubbing.enabled
    monkeypatch.setattr(config, "get", lambda key: False if key == "locus.security.think_scrubbing.enabled" else True)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == "locus.security.think_scrubbing.enabled" else True)
    assert provider.is_enabled() is False


def test_swappable_provider_swap():
    """SPEC §13.9 line 3591: Modularity and swappable provider interface."""
    class CustomThinkScrubberProvider(BaseThinkScrubberProvider):
        def feed_chunk(self, delta_text: str) -> str:
            return delta_text.replace("<custom_think>", "").replace("</custom_think>", "")

        def flush(self) -> str:
            return ""

        def scrub_text(self, text: str) -> str:
            return text.replace("<custom_think>", "").replace("</custom_think>", "")

        def reset(self) -> None:
            pass

        def list_tags(self) -> list[str]:
            return ["custom_think"]

    custom = CustomThinkScrubberProvider()
    assert isinstance(custom, BaseThinkScrubberProvider)
    assert custom.scrub_text("<custom_think>test</custom_think>msg") == "testmsg"
    assert custom.feed_chunk("<custom_think>delta</custom_think>") == "delta"
    assert custom.list_tags() == ["custom_think"]
