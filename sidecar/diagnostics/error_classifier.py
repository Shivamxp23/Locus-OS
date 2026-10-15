"""Locus Error Classifier (§29.1).

Classifies runtime, API, execution, and model errors into actionable categories,
providing automated mitigation strategies, retry policies, and fallback actions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ErrorCategory(str, Enum):
    TRANSIENT = "transient"
    RATE_LIMIT = "rate_limit"
    CONTEXT_OVERFLOW = "context_overflow"
    AUTH_FAILURE = "auth_failure"
    PERMISSION_DENIED = "permission_denied"
    SYNTAX_ERROR = "syntax_error"
    TOOL_EXECUTION_FAILURE = "tool_execution_failure"
    TIMEOUT = "timeout"
    MODEL_UNAVAILABLE = "model_unavailable"
    UNKNOWN = "unknown"


@dataclass
class ClassifiedError:
    category: ErrorCategory
    raw_message: str
    is_retryable: bool
    retry_delay_seconds: float
    suggested_action: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "raw_message": self.raw_message,
            "is_retryable": self.is_retryable,
            "retry_delay_seconds": self.retry_delay_seconds,
            "suggested_action": self.suggested_action,
            "metadata": self.metadata,
        }


class ErrorClassifier:
    """Classifies application and LLM errors to drive autonomous resilience."""

    _PATTERNS = [
        (ErrorCategory.RATE_LIMIT, [
            r"rate limit", r"429", r"too many requests", r"quota exceeded", r"tpm", r"rpm"
        ], True, 30.0, "Wait for rate limit window to reset or fallback to alternative model provider"),
        (ErrorCategory.CONTEXT_OVERFLOW, [
            r"context length", r"maximum context length", r"token count exceeded",
            r"prompt is too long", r"tokens.*exceeded limit"
        ], False, 0.0, "Compress context, summarize conversation history, or switch to large-window model"),
        (ErrorCategory.AUTH_FAILURE, [
            r"invalid api key", r"unauthorized", r"401", r"authentication failed", r"invalid_grant"
        ], False, 0.0, "Verify credentials and refresh API keys or OAuth tokens"),
        (ErrorCategory.PERMISSION_DENIED, [
            r"permission denied", r"access denied", r"403", r"eacces", r"eperm"
        ], False, 0.0, "Check file system permissions or request human elevation approval"),
        (ErrorCategory.TIMEOUT, [
            r"timed out", r"timeout", r"etimedout", r"deadline exceeded", r"gateway timeout", r"504"
        ], True, 5.0, "Retry operation with increased timeout budget"),
        (ErrorCategory.MODEL_UNAVAILABLE, [
            r"model unavailable", r"service unavailable", r"503", r"server error", r"500", r"bad gateway", r"502"
        ], True, 10.0, "Failover to backup model endpoint"),
        (ErrorCategory.SYNTAX_ERROR, [
            r"syntaxerror", r"invalid syntax", r"unexpected token", r"parse error"
        ], False, 0.0, "Analyze syntax tree and repair malformed code"),
        (ErrorCategory.TOOL_EXECUTION_FAILURE, [
            r"tool error", r"command failed with exit code", r"non-zero exit code"
        ], False, 0.0, "Inspect stderr, adjust tool parameters, and retry with corrected arguments"),
    ]

    def classify(self, error: Exception | str, context: Optional[Dict[str, Any]] = None) -> ClassifiedError:
        msg = str(error)
        msg_lower = msg.lower()

        for category, patterns, retryable, delay, action in self._PATTERNS:
            for pat in patterns:
                if re.search(pat, msg_lower):
                    # Check for explicit retry-after headers or seconds
                    m = re.search(r"retry after\s*(\d+)", msg_lower)
                    override_delay = float(m.group(1)) if m else delay
                    return ClassifiedError(
                        category=category,
                        raw_message=msg,
                        is_retryable=retryable,
                        retry_delay_seconds=override_delay,
                        suggested_action=action,
                        metadata=context or {},
                    )

        return ClassifiedError(
            category=ErrorCategory.UNKNOWN,
            raw_message=msg,
            is_retryable=False,
            retry_delay_seconds=0.0,
            suggested_action="Escalate to user or log diagnostic report",
            metadata=context or {},
        )
