import pytest
from sidecar.security.think_scrubber import (
    ScrubState,
    ThinkTokenScrubber,
)


def test_scrubber_removes_think_block():
    scrubber = ThinkTokenScrubber()
    text = "<think>Let me evaluate the user query step by step.</think>Hello! Here is your answer."
    scrubbed = scrubber.process_complete(text)
    assert "<think>" not in scrubbed
    assert "</think>" not in scrubbed
    assert "Let me evaluate" not in scrubbed
    assert scrubbed == "Hello! Here is your answer."


def test_scrubber_removes_reasoning_and_scratchpad():
    scrubber = ThinkTokenScrubber()
    text = "<reasoning>\nInternal Chain of Thought\n</reasoning>Deterministic output."
    assert scrubber.process_complete(text) == "Deterministic output."

    scratch = "<REASONING_SCRATCHPAD>Plan: do X</REASONING_SCRATCHPAD>Final result."
    assert scrubber.process_complete(scratch) == "Final result."


def test_scrubber_unclosed_block_at_end():
    scrubber = ThinkTokenScrubber()
    text = "Intro text\n<think>Unfinished thoughts that were cut off"
    scrubbed = scrubber.process_complete(text)
    assert scrubbed == "Intro text"
