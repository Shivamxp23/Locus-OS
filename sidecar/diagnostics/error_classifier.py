"""
SPEC §29.1 lines 7435-7471:
Error Classifier engine (F-0065 / US-102).
Source: Hermes error_classifier.py

Taxonomy:
- rate_limit: 429/quota exceeded -> auto-retry with backoff
- auth_failure: 401/403 -> surface to user, suggest key refresh
- context_overflow: token limit / context_length -> trigger compaction
- server_error: 500/502/503/504 -> retry 3x, then fallback model
- timeout: request timeout -> retry with shorter context
- content_filter: safety filter -> rephrase and retry
- unknown: unclassified -> log, continue

Off state:
locus.diagnostics.error_classifier.enabled: when off, classification returns unclassified/disabled.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
import logging
import re
from typing import Any, Dict, Optional, Union

from sidecar import config

logger = logging.getLogger("locus.diagnostics.error_classifier")


class ErrorCategory(str, Enum):
    RATE_LIMIT = "rate_limit"
    AUTH_FAILURE = "auth_failure"
    CONTEXT_OVERFLOW = "context_overflow"
    SERVER_ERROR = "server_error"
    TIMEOUT = "timeout"
    CONTENT_FILTER = "content_filter"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    AUTO_RETRY = "auto_retry"
    SURFACE_USER = "surface_user"
    TRIGGER_COMPACTION = "trigger_compaction"
    RETRY_THEN_FALLBACK = "retry_then_fallback"
    RETRY_SHORTER_CONTEXT = "retry_shorter_context"
    REPHRASE_AND_RETRY = "rephrase_and_retry"
    LOG_AND_CONTINUE = "log_and_continue"


@dataclass
class ErrorClassification:
    category: str
    action: str
    retryable: bool
    max_retries: int
    backoff_seconds: float
    fallback_model_recommended: bool
    explanation: str
    raw_status: Optional[int] = None
    raw_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ErrorClassifier:
    """
    SPEC §29.1: Error Classifier categorizing LLM and HTTP failures into actionable recovery strategies.
    """

    SWITCH_KEY = "locus.diagnostics.error_classifier.enabled"

    def is_enabled(self) -> bool:
        val = config.get(self.SWITCH_KEY)
        if val is not None and not config.is_enabled(self.SWITCH_KEY):
            return False
        return True

    def classify(self, error: Any) -> ErrorClassification:
        """
        Classifies errors from Exception objects, status codes, error dictionaries, or error message strings.
        SPEC §29.1:
            IF error.status == 429: RETURN "rate_limit"
            IF error.status IN [401, 403]: RETURN "auth_failure"
            IF "context_length" IN error.message: RETURN "context_overflow"
            IF error.status >= 500: RETURN "server_error"
            IF error.type == "timeout": RETURN "timeout"
            IF "content_filter" IN error.message: RETURN "content_filter"
            RETURN "unknown"
        """
        if not self.is_enabled():
            return ErrorClassification(
                category=ErrorCategory.UNKNOWN.value,
                action=RecoveryAction.LOG_AND_CONTINUE.value,
                retryable=False,
                max_retries=0,
                backoff_seconds=0.0,
                fallback_model_recommended=False,
                explanation="Error classifier subsystem is disabled",
                raw_status=None,
                raw_message=str(error),
            )

        status, error_type, message = self._extract_error_details(error)

        # 1. Rate Limit
        if status == 429 or self._match_patterns(message, [r"rate[_\s-]?limit", r"quota\s+exceeded", r"too\s+many\s+requests"]):
            return ErrorClassification(
                category=ErrorCategory.RATE_LIMIT.value,
                action=RecoveryAction.AUTO_RETRY.value,
                retryable=True,
                max_retries=3,
                backoff_seconds=2.0,
                fallback_model_recommended=False,
                explanation="Rate limit or quota threshold reached; retry with exponential backoff",
                raw_status=status or 429,
                raw_message=message,
            )

        # 2. Auth Failure
        if status in (401, 403) or self._match_patterns(message, [r"unauthorized", r"forbidden", r"invalid\s+(api\s+)?key", r"authentication\s+failed"]):
            return ErrorClassification(
                category=ErrorCategory.AUTH_FAILURE.value,
                action=RecoveryAction.SURFACE_USER.value,
                retryable=False,
                max_retries=0,
                backoff_seconds=0.0,
                fallback_model_recommended=False,
                explanation="Authentication or authorization failed; surface to user to refresh API credentials",
                raw_status=status or 401,
                raw_message=message,
            )

        # 3. Context Overflow
        if self._match_patterns(message, [r"context_length", r"maximum\s+context\s+length", r"token\s+limit", r"prompt\s+too\s+long"]):
            return ErrorClassification(
                category=ErrorCategory.CONTEXT_OVERFLOW.value,
                action=RecoveryAction.TRIGGER_COMPACTION.value,
                retryable=True,
                max_retries=1,
                backoff_seconds=0.0,
                fallback_model_recommended=False,
                explanation="Context window exceeded; trigger conversation memory compaction",
                raw_status=status,
                raw_message=message,
            )

        # 4. Timeout
        if error_type == "timeout" or isinstance(error, TimeoutError) or self._match_patterns(message, [r"timed?\s*out", r"request\s+timeout", r"gateway\s+timeout"]):
            return ErrorClassification(
                category=ErrorCategory.TIMEOUT.value,
                action=RecoveryAction.RETRY_SHORTER_CONTEXT.value,
                retryable=True,
                max_retries=2,
                backoff_seconds=1.0,
                fallback_model_recommended=False,
                explanation="Request timed out; retry with shorter context or smaller turn payload",
                raw_status=status or 504,
                raw_message=message,
            )

        # 5. Server Error
        if (status is not None and status >= 500) or self._match_patterns(message, [r"internal\s+server\s+error", r"bad\s+gateway", r"service\s+unavailable"]):
            return ErrorClassification(
                category=ErrorCategory.SERVER_ERROR.value,
                action=RecoveryAction.RETRY_THEN_FALLBACK.value,
                retryable=True,
                max_retries=3,
                backoff_seconds=1.5,
                fallback_model_recommended=True,
                explanation="Server 5xx error; retry 3 times with backoff, then escalate to fallback model",
                raw_status=status or 500,
                raw_message=message,
            )

        # 6. Content Filter
        if self._match_patterns(message, [r"content_filter", r"safety\s+filter", r"content\s+moderation", r"blocked\s+by\s+policy"]):
            return ErrorClassification(
                category=ErrorCategory.CONTENT_FILTER.value,
                action=RecoveryAction.REPHRASE_AND_RETRY.value,
                retryable=True,
                max_retries=1,
                backoff_seconds=0.0,
                fallback_model_recommended=False,
                explanation="Blocked by safety or moderation policy; rephrase prompt and retry",
                raw_status=status,
                raw_message=message,
            )

        # 7. Unknown / Fallback
        return ErrorClassification(
            category=ErrorCategory.UNKNOWN.value,
            action=RecoveryAction.LOG_AND_CONTINUE.value,
            retryable=False,
            max_retries=0,
            backoff_seconds=0.0,
            fallback_model_recommended=False,
            explanation="Unclassified failure; log diagnostics and continue",
            raw_status=status,
            raw_message=message,
        )

    def _extract_error_details(self, error: Any) -> tuple[Optional[int], Optional[str], str]:
        status: Optional[int] = None
        error_type: Optional[str] = None
        message: str = ""

        if isinstance(error, int):
            status = error
            message = f"HTTP {error}"
        elif isinstance(error, dict):
            status = error.get("status") or error.get("status_code") or error.get("code")
            if isinstance(status, str) and status.isdigit():
                status = int(status)
            elif not isinstance(status, int):
                status = None

            error_type = error.get("type") or error.get("error_type")
            message = str(error.get("message") or error.get("detail") or error.get("error") or "")
        elif isinstance(error, Exception):
            message = str(error)
            error_type = error.__class__.__name__.lower()
            if hasattr(error, "status_code"):
                status = getattr(error, "status_code")
            elif hasattr(error, "status"):
                status = getattr(error, "status")
        else:
            message = str(error)

        return status, error_type, message

    def _match_patterns(self, text: str, patterns: list[str]) -> bool:
        if not text:
            return False
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                return True
        return False

    def get_taxonomy(self) -> Dict[str, Any]:
        """Returns standard 7-category error taxonomy and recovery strategy specifications."""
        return {
            "categories": [c.value for c in ErrorCategory],
            "actions": [a.value for a in RecoveryAction],
            "strategies": {
                ErrorCategory.RATE_LIMIT.value: {
                    "action": RecoveryAction.AUTO_RETRY.value,
                    "max_retries": 3,
                    "backoff_seconds": 2.0,
                },
                ErrorCategory.AUTH_FAILURE.value: {
                    "action": RecoveryAction.SURFACE_USER.value,
                    "max_retries": 0,
                    "backoff_seconds": 0.0,
                },
                ErrorCategory.CONTEXT_OVERFLOW.value: {
                    "action": RecoveryAction.TRIGGER_COMPACTION.value,
                    "max_retries": 1,
                    "backoff_seconds": 0.0,
                },
                ErrorCategory.SERVER_ERROR.value: {
                    "action": RecoveryAction.RETRY_THEN_FALLBACK.value,
                    "max_retries": 3,
                    "backoff_seconds": 1.5,
                },
                ErrorCategory.TIMEOUT.value: {
                    "action": RecoveryAction.RETRY_SHORTER_CONTEXT.value,
                    "max_retries": 2,
                    "backoff_seconds": 1.0,
                },
                ErrorCategory.CONTENT_FILTER.value: {
                    "action": RecoveryAction.REPHRASE_AND_RETRY.value,
                    "max_retries": 1,
                    "backoff_seconds": 0.0,
                },
                ErrorCategory.UNKNOWN.value: {
                    "action": RecoveryAction.LOG_AND_CONTINUE.value,
                    "max_retries": 0,
                    "backoff_seconds": 0.0,
                },
            },
        }

    def get_status(self) -> Dict[str, Any]:
        return {
            "subsystem_enabled": self.is_enabled(),
            "classifier_name": "HermesErrorClassifier",
            "taxonomy_version": "1.0.0",
        }
