"""
SPEC §2.6 / F-0095 / US-35: Anti-Hallucination Guard (Stage 10) Provider Contract.
Defines factual claim extraction, grounding verification against Context Forge content,
strict/warn execution modes, and brain error logging structures.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import time
from typing import Any, Dict, List, Optional


class GuardMode(str, Enum):
    """
    SPEC §2.6 lines 1838-1847:
    Operating modes for anti-hallucination guard.
    """
    STRICT = "strict"
    WARN = "warn"
    OFF = "off"


DEFAULT_CAVEAT_MESSAGE: str = (
    "⚠️ Note: I'm not fully certain about some details. Let me know if anything seems off."
)


@dataclass
class FactualClaim:
    """
    SPEC §2.6 line 1826:
    A "claim" is any statement about the user, their data, or their history.
    NOT opinions, advice, or external knowledge.
    """
    statement: str
    category: str = "user_data"  # "user_data", "user_history", "user_identity", etc.
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "statement": self.statement,
            "category": self.category,
            "confidence": self.confidence,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FactualClaim:
        return cls(
            statement=data.get("statement", ""),
            category=data.get("category", "user_data"),
            confidence=float(data.get("confidence", 1.0)),
        )


@dataclass
class BrainErrorLog:
    """
    SPEC §2.6 lines 1840, 1846:
    LOG to brain_errors (severity=2, type="hallucination" in strict mode;
    severity=1, type="soft_hallucination" in warn mode).
    """
    timestamp: float
    error_type: str
    severity: int
    ungrounded_claims: List[str]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "error_type": self.error_type,
            "severity": self.severity,
            "ungrounded_claims": self.ungrounded_claims,
            "details": self.details,
        }


@dataclass
class CheckResult:
    """
    SPEC §2.6 lines 1838-1848:
    Result of anti_hallucination_check.
    """
    block: bool
    reason: Optional[str] = None
    original_response: str = ""
    output_response: str = ""
    claims_detected: List[str] = field(default_factory=list)
    ungrounded_claims: List[str] = field(default_factory=list)
    brain_error: Optional[BrainErrorLog] = None
    mode: str = GuardMode.WARN.value

    def to_dict(self) -> Dict[str, Any]:
        return {
            "block": self.block,
            "reason": self.reason,
            "original_response": self.original_response,
            "output_response": self.output_response,
            "claims_detected": self.claims_detected,
            "ungrounded_claims": self.ungrounded_claims,
            "brain_error": self.brain_error.to_dict() if self.brain_error else None,
            "mode": self.mode,
        }


class BaseAntiHallucinationProvider(ABC):
    """
    Abstract interface for Anti-Hallucination Guard provider.
    Modular, swappable component per AGENTS.md law 11 and modularity architecture (03).
    """

    @abstractmethod
    def check(
        self,
        llm_response: str,
        context_forge_content: str,
        mode: Optional[str] = None,
    ) -> CheckResult:
        """
        SPEC §2.6 line 1821:
        FUNCTION anti_hallucination_check(llm_response, context_forge_content)
        """
        pass

    @abstractmethod
    def extract_factual_claims(self, llm_response: str) -> List[FactualClaim]:
        """
        SPEC §2.6 lines 1825-1827:
        Extract factual statements about the user, their data, or their history.
        Exclude opinions, general advice, or external factual knowledge.
        """
        pass

    @abstractmethod
    def contains_evidence_for(self, context_content: str, claim: str) -> bool:
        """
        SPEC §2.6 line 1832:
        Check if context_forge_content contains supporting evidence for the claim.
        """
        pass

    @abstractmethod
    def get_mode(self) -> GuardMode:
        """Get the configured guard operating mode (strict, warn, off)."""
        pass
