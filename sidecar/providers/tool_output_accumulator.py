"""
Abstract base provider and data models for Tool Output Accumulator (SPEC §3.10 / F-0102).
Incrementally tracks streaming tool output with bounded memory, tail snapshots,
and disk spillover for full logs.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Optional, Union


class TruncationType(str, Enum):
    """Reason for output truncation."""
    LINES = "lines"
    BYTES = "bytes"
    NONE = "none"


@dataclass(frozen=True)
class OutputAccumulatorConfig:
    """Configuration for Tool Output Accumulator."""
    enabled: bool = True
    default_max_lines: int = 1000
    default_max_bytes: int = 100000
    temp_file_prefix: str = "locus-output"
    persist_temp_files: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class OutputSnapshot:
    """Snapshot of accumulated tool output with truncation metadata."""
    content: str
    truncated: bool
    truncated_by: Optional[TruncationType] = None
    total_lines: int = 0
    total_bytes: int = 0
    max_lines: int = 1000
    max_bytes: int = 100000
    full_output_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "truncated": self.truncated,
            "truncated_by": self.truncated_by.value if self.truncated_by else None,
            "total_lines": self.total_lines,
            "total_bytes": self.total_bytes,
            "max_lines": self.max_lines,
            "max_bytes": self.max_bytes,
            "full_output_path": self.full_output_path,
        }


@dataclass(frozen=True)
class FullOutputResult:
    """Complete output with optional head/tail preservation around an omission marker."""
    content: str
    truncated: bool
    omitted_bytes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseToolOutputAccumulatorProvider(ABC):
    """Interface for Tool Output Accumulator providers."""

    def __init__(self, name: str = "tool_output_accumulator") -> None:
        self.name = name

    @abstractmethod
    def create_accumulator(
        self,
        accumulator_id: Optional[str] = None,
        max_lines: Optional[int] = None,
        max_bytes: Optional[int] = None,
        temp_file_prefix: Optional[str] = None,
    ) -> str:
        """Create a new accumulator session and return its unique identifier."""
        pass

    @abstractmethod
    def append(
        self,
        accumulator_id: str,
        data: Union[str, bytes],
    ) -> OutputSnapshot:
        """Append raw data or text to the accumulator."""
        pass

    @abstractmethod
    def snapshot(
        self,
        accumulator_id: str,
        persist_if_truncated: bool = True,
    ) -> OutputSnapshot:
        """Get a bounded tail snapshot of current output."""
        pass

    @abstractmethod
    def finish(self, accumulator_id: str) -> OutputSnapshot:
        """Mark accumulation as finished, flushing decoders and temp streams."""
        pass

    @abstractmethod
    def read_full_output(
        self,
        accumulator_id: str,
        max_bytes: int = 50000,
    ) -> FullOutputResult:
        """Read complete output up to max_bytes with middle omission marker if exceeded."""
        pass

    @abstractmethod
    def close(self, accumulator_id: str) -> None:
        """Release session resources, closing open file streams."""
        pass

    @abstractmethod
    def get_config(self) -> OutputAccumulatorConfig:
        """Retrieve current accumulator configuration."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return diagnostic health check dict."""
        pass
