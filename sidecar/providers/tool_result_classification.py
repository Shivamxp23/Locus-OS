"""
Abstract base provider and data models for Tool Result Classification (SPEC §3.9 / F-0101).
Classifies tool execution results into SUCCESS, FAILURE, or PARTIAL, and detects
side-effects and landed file mutations.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, Mapping, Optional


class ResultClassificationType(str, Enum):
    """Classification category for a tool execution result."""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"


@dataclass(frozen=True)
class ToolResultClassificationConfig:
    """Configuration for Tool Result Classification."""
    enabled: bool = True
    detect_file_mutations: bool = True
    detect_side_effects: bool = True
    strict_exit_codes: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ToolResultClassification:
    """Structured classification outcome for a tool result."""
    status: ResultClassificationType
    tool_name: str
    is_success: bool
    is_failure: bool
    is_partial: bool
    has_side_effect: bool
    file_mutation_landed: bool
    error_message: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "tool_name": self.tool_name,
            "is_success": self.is_success,
            "is_failure": self.is_failure,
            "is_partial": self.is_partial,
            "has_side_effect": self.has_side_effect,
            "file_mutation_landed": self.file_mutation_landed,
            "error_message": self.error_message,
            "details": dict(self.details),
        }


class BaseToolResultClassificationProvider(ABC):
    """Interface for Tool Result Classification providers."""

    def __init__(self, name: str = "tool_result_classification") -> None:
        self.name = name

    @abstractmethod
    def classify_result(
        self,
        tool_name: str,
        result: Any,
        error: Optional[str] = None,
        exit_code: Optional[int] = None,
        params: Optional[Mapping[str, Any]] = None,
    ) -> ToolResultClassification:
        """
        Classify tool execution outcome as SUCCESS, FAILURE, or PARTIAL.
        Also evaluates side effects and file mutation landing.
        """
        pass

    @abstractmethod
    def tool_may_have_side_effect(self, tool_name: str) -> bool:
        """Return True if tool may mutate external or session state."""
        pass

    @abstractmethod
    def file_mutation_result_landed(self, tool_name: str, result: Any) -> bool:
        """Return True when a file mutation result proves the write landed."""
        pass

    @abstractmethod
    def get_config(self) -> ToolResultClassificationConfig:
        """Retrieve current classification configuration."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return diagnostic health check dict."""
        pass
