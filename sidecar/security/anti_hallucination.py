"""sidecar/security/anti_hallucination.py - Anti-Hallucination Guard (Stage 10).

Implements Spec §2.6:
- Post-generation verification of LLM responses against assembled Context Forge content.
- Extracts factual assertions and verifies grounding in retrieved context.
- Configurable modes:
  - "warn" (default): Appends caveat and logs soft hallucination.
  - "strict": Blocks ungrounded response and logs severity-2 hallucination error.
- Cost: ~0 tokens via string/token heuristics.
- Modularity switch: locus.anti_hallucination.enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import re
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

logger = logging.getLogger("sidecar.security.anti_hallucination")

DEFAULT_CAVEAT = "\n\n⚠️ Note: I'm not fully certain about some details. Let me know if anything seems off."


@dataclass
class VerificationResult:
    """Result of anti-hallucination verification."""

    blocked: bool
    sanitized_response: str
    ungrounded_claims: list[str] = field(default_factory=list)
    mode: str = "warn"
    logged_error: Optional[dict[str, Any]] = None

    @property
    def ok(self) -> bool:
        return not self.blocked


@runtime_checkable
class AntiHallucinationProvider(Protocol):
    """Protocol for anti-hallucination providers."""

    def verify(self, response: str, context: str, mode: str = "warn") -> VerificationResult:
        """Verify LLM response against assembled context."""
        return VerificationResult(
            blocked=False,
            sanitized_response=response,
            ungrounded_claims=[],
        )


class AntiHallucinationGuard:
    """Core Anti-Hallucination Guard implementing Spec §2.6."""

    def __init__(self, enabled: bool = True, default_mode: str = "warn"):
        self.enabled = enabled
        self.default_mode = default_mode
        self.error_logs: list[dict[str, Any]] = []

    @staticmethod
    def extract_claims(text: str) -> list[str]:
        """Extract candidate factual assertions about user or history."""
        sentences = [s.strip() for s in re.split(r"[.!?\n]+", text) if len(s.strip()) > 15]
        # Filter for sentences asserting personal data, metrics, or completed events
        claim_markers = ["you have", "you completed", "your goal", "your dcs", "you said", "your habit", "yesterday you", "today you"]
        claims = []
        for s in sentences:
            s_lower = s.lower()
            if any(m in s_lower for m in claim_markers) or re.search(r"\b(dcs|tws|score|hours|streak)\s*[:=]?\s*\d+", s_lower):
                claims.append(s)
        return claims

    @staticmethod
    def is_claim_grounded(claim: str, context: str) -> bool:
        """Check if claim's key terms or metrics exist in context."""
        ctx_lower = context.lower()
        # Extract significant words (length >= 4, alphanumeric)
        words = [w for w in re.findall(r"\b[a-zA-Z0-9_-]+\b", claim.lower()) if len(w) >= 4]
        if not words:
            return True
        # If at least 40% of significant words or numerical values appear in context, consider grounded
        matches = sum(1 for w in words if w in ctx_lower)
        return (matches / len(words)) >= 0.35

    def verify(self, response: str, context: str, mode: Optional[str] = None) -> VerificationResult:
        """Verify LLM response against context."""
        if not self.enabled:
            return VerificationResult(
                blocked=False,
                sanitized_response=response,
                ungrounded_claims=[],
                mode="disabled",
            )

        active_mode = mode or self.default_mode
        claims = self.extract_claims(response)
        ungrounded: list[str] = []

        for claim in claims:
            if not self.is_claim_grounded(claim, context):
                ungrounded.append(claim)

        if not ungrounded:
            return VerificationResult(
                blocked=False,
                sanitized_response=response,
                ungrounded_claims=[],
                mode=active_mode,
            )

        # Handle ungrounded claims based on active mode
        if active_mode == "strict":
            err = {
                "severity": 2,
                "type": "hallucination",
                "claims": ungrounded,
                "reason": "Response contained ungrounded claims",
            }
            self.error_logs.append(err)
            return VerificationResult(
                blocked=True,
                sanitized_response="Response blocked: Contains ungrounded personal data claims not present in context.",
                ungrounded_claims=ungrounded,
                mode="strict",
                logged_error=err,
            )
        else:
            # Mode "warn" (default)
            err = {
                "severity": 1,
                "type": "soft_hallucination",
                "claims": ungrounded,
            }
            self.error_logs.append(err)
            sanitized = response.rstrip() + DEFAULT_CAVEAT
            return VerificationResult(
                blocked=False,
                sanitized_response=sanitized,
                ungrounded_claims=ungrounded,
                mode="warn",
                logged_error=err,
            )
