"""Think token scrubber module for Locus OS sidecar."""

from enum import Enum


class ScrubState(Enum):
    NORMAL = 1
    PENDING_TAG = 2
    INSIDE_BLOCK = 3


class ThinkTokenScrubber:
    OPEN_TAGS = ["<think>", "<thinking>", "<reasoning>", "<thought>", "<REASONING_SCRATCHPAD>"]
    CLOSE_TAGS = ["</think>", "</thinking>", "</reasoning>", "</thought>", "</REASONING_SCRATCHPAD>"]

    def __init__(self) -> None:
        self.state = ScrubState.NORMAL
        self.pending_buffer = ""
        self.current_close_tag = None

    def _is_block_boundary(self, text: str, tag_pos: int) -> bool:
        if tag_pos == 0:
            return True
        before = text[:tag_pos]
        return before.endswith("\n") or before.strip() == ""

    def process_chunk(self, chunk: str) -> str:
        self.pending_buffer += chunk
        return ""

    def reset(self) -> None:
        self.state = ScrubState.NORMAL
        self.pending_buffer = ""
        self.current_close_tag = None

    def process_complete(self, text: str) -> str:
        result = text
        for tag in self.OPEN_TAGS:
            while True:
                start_idx = result.find(tag)
                if start_idx == -1:
                    break

                if not self._is_block_boundary(result, start_idx):
                    result = result[:start_idx] + "|||TEMP_TAG|||" + result[start_idx + len(tag) :]
                    continue

                close_tag = tag.replace("<", "</")
                end_idx = result.find(close_tag, start_idx)

                if end_idx != -1:
                    result = result[:start_idx] + result[end_idx + len(close_tag) :]
                else:
                    result = result[:start_idx]
                    break

        result = result.replace("|||TEMP_TAG|||", "<think>")
        return result.strip()
