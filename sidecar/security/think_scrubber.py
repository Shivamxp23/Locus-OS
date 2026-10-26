"""
SPEC §13.9 lines 3513-3598:
Think Token Scrubbing (F-0042 / US-74).

Stateful streaming state machine that strips <think>, <thinking>, <reasoning>,
<thought>, <REASONING_SCRATCHPAD> blocks from streamed assistant text.
Handles partial tags at delta boundaries, preventing reasoning leakage.
"""
from __future__ import annotations

from enum import Enum
import logging
import re
from typing import List, Optional

logger = logging.getLogger(__name__)

SUPPORTED_TAGS: List[str] = [
    "think",
    "thinking",
    "reasoning",
    "thought",
    "REASONING_SCRATCHPAD",
]


class ScrubState(Enum):
    NORMAL = "NORMAL"
    PENDING_TAG = "PENDING_TAG"
    INSIDE_BLOCK = "INSIDE_BLOCK"


class StreamingThinkScrubber:
    """
    SPEC §13.9: Stateful streaming state machine for scrubbing thinking tokens.
    """

    def __init__(self, tags: Optional[List[str]] = None) -> None:
        self.tags = [t.lower() for t in (tags or SUPPORTED_TAGS)]
        self.state: ScrubState = ScrubState.NORMAL
        self.held_back: str = ""
        self.current_close_tag: Optional[str] = None
        self.line_prefix: str = ""  # Characters on current line prior to the pending tag

    def reset(self) -> None:
        """SPEC §13.9: Call at start of each new turn."""
        self.state = ScrubState.NORMAL
        self.held_back = ""
        self.current_close_tag = None
        self.line_prefix = ""

    def _is_block_boundary(self) -> bool:
        """
        SPEC §13.9: Only suppress if tag is at start of stream,
        after newline, or only whitespace on current line.
        """
        return self.line_prefix == "" or self.line_prefix.strip() == "" or self.line_prefix.endswith("\n")

    def feed(self, delta_text: str) -> str:
        """
        SPEC §13.9: FUNCTION feed(delta_text) -> visible_text
        """
        if not delta_text:
            return ""

        result: List[str] = []
        i = 0
        n = len(delta_text)

        while i < n:
            char = delta_text[i]

            if self.state == ScrubState.NORMAL:
                if char == "<":
                    self.state = ScrubState.PENDING_TAG
                    self.held_back = "<"
                else:
                    result.append(char)
                    if char == "\n":
                        self.line_prefix = ""
                    else:
                        self.line_prefix += char
                i += 1

            elif self.state == ScrubState.PENDING_TAG:
                self.held_back += char
                i += 1
                hb_lower = self.held_back.lower()

                # Check if matches any full open tag: <tag>
                matched_tag = None
                for t in self.tags:
                    if hb_lower == f"<{t}>":
                        matched_tag = t
                        break

                if matched_tag:
                    if self._is_block_boundary():
                        self.state = ScrubState.INSIDE_BLOCK
                        self.current_close_tag = f"</{matched_tag}>"
                        self.held_back = ""
                    else:
                        # Prose mention (e.g. "use <think> tags here") - emit as text
                        result.append(self.held_back)
                        self.line_prefix += self.held_back
                        self.held_back = ""
                        self.state = ScrubState.NORMAL

                elif any(f"<{t}>".startswith(hb_lower) for t in self.tags):
                    # Potentially matching a tag, keep buffering in PENDING_TAG
                    pass
                else:
                    # Clearly not a tag - flush held_back to output
                    result.append(self.held_back)
                    self.line_prefix += self.held_back
                    self.held_back = ""
                    self.state = ScrubState.NORMAL

            elif self.state == ScrubState.INSIDE_BLOCK:
                # Buffer looking for closing tag
                self.held_back += char
                i += 1
                hb_lower = self.held_back.lower()

                # Determine if closing tag is found
                close_target = self.current_close_tag or "</think>"
                if close_target in hb_lower:
                    self.state = ScrubState.NORMAL
                    self.held_back = ""
                    self.current_close_tag = None
                    self.line_prefix = ""
                else:
                    # Keep held_back bounded to length of longest closing tag to prevent memory growth
                    max_close_len = max(len(t) for t in self.tags) + 3
                    if len(self.held_back) > max_close_len * 2:
                        self.held_back = self.held_back[-max_close_len:]

        return "".join(result)

    def flush(self) -> str:
        """
        SPEC §13.9: End-of-stream: emit any held-back text that turned out not to be a tag.
        """
        if self.held_back and self.state == ScrubState.PENDING_TAG:
            result = self.held_back
            self.held_back = ""
            self.state = ScrubState.NORMAL
            return result
        # If stream ended inside a block without closing tag, swallow content
        self.held_back = ""
        self.state = ScrubState.NORMAL
        return ""

    def process_complete(self, text: str) -> str:
        """Helper to scrub full strings in a single call."""
        self.reset()
        visible = self.feed(text) + self.flush()
        return visible.strip()


# Convenience alias
ThinkTokenScrubber = StreamingThinkScrubber
