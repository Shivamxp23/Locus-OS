"""
SPEC §2.6 / F-0095 / US-35: Anti-Hallucination Guard (Stage 10) Implementation.
Performs claim extraction, context-grounding verification, caveat injection (warn mode),
strict rejection (strict mode), and brain error logging.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional, Set

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.providers.anti_hallucination import (
    BaseAntiHallucinationProvider,
    BrainErrorLog,
    CheckResult,
    DEFAULT_CAVEAT_MESSAGE,
    FactualClaim,
    GuardMode,
)

logger = logging.getLogger("sidecar.anti_hallucination")

# Global in-memory log of brain errors for observability
_BRAIN_ERRORS: List[BrainErrorLog] = []


def get_brain_errors() -> List[BrainErrorLog]:
    """Retrieve all recorded brain errors."""
    return list(_BRAIN_ERRORS)


def clear_brain_errors() -> None:
    """Clear recorded brain errors."""
    _BRAIN_ERRORS.clear()


# Patterns indicating statements about user identity, state, habits, goals, or history
# SPEC §2.6 line 1826: statement about user, their data, or their history.
# NOT opinions, advice, or external knowledge.
USER_CLAIM_PATTERNS = [
    re.compile(r"\b(you\s+(have|are|were|did|completed|started|worked|scheduled|logged|noted|set|finished|missed|created|visited|asked))\b", re.I),
    re.compile(r"\b(your\s+(goal|vault|project|task|habit|calendar|focus|session|sleep|energy|score|dcs|tws|streak|history|status|directive|record))\b", re.I),
    re.compile(r"\b(in\s+your\s+vault|in\s+your\s+notes|in\s+your\s+system)\b", re.I),
    re.compile(r"\b(yesterday\s+you|earlier\s+you|last\s+week\s+you)\b", re.I),
    re.compile(r"\b(according\s+to\s+your\s+(data|records|logs|history))\b", re.I),
]

# Patterns representing generic opinions, instructions, or external facts (NOT claims)
OPINION_OR_ADVICE_PATTERNS = [
    re.compile(r"^(i\s+think|i\s+recommend|i\s+suggest|in\s+my\s+opinion|perhaps|maybe)\b", re.I),
    re.compile(r"^(you\s+should|you\s+could|try\s+to|consider|make\s+sure\s+to|be\s+careful)\b", re.I),
    re.compile(r"\b(generally|usually|typically|in\s+python|in\s+typescript|for\s+example)\b", re.I),
]


class AntiHallucinationProvider(BaseAntiHallucinationProvider):
    """
    Default implementation of Anti-Hallucination Guard per SPEC §2.6.
    Runs verification of model assertions against Context Forge evidence.
    """

    def __init__(self) -> None:
        pass

    def get_mode(self) -> GuardMode:
        """
        Get guard operating mode from configuration.
        Config key: `locus.brain.anti_hallucination.mode` or `locus.anti_hallucination.mode` (default: "warn").
        """
        raw = config.get("locus.brain.anti_hallucination.mode")
        if raw is None:
            raw = config.get("locus.anti_hallucination.mode", "warn")
        val = str(raw).lower().strip()
        if val in ("strict", GuardMode.STRICT.value):
            return GuardMode.STRICT
        elif val in ("off", "disabled", GuardMode.OFF.value):
            return GuardMode.OFF
        return GuardMode.WARN

    def extract_factual_claims(self, llm_response: str) -> List[FactualClaim]:
        """
        SPEC §2.6 lines 1825-1827:
        Extract factual claims about the user, their data, or history from LLM response.
        Excludes opinions, advice, or external knowledge.
        """
        if not llm_response:
            return []

        claims: List[FactualClaim] = []
        # Split into sentences or clauses
        sentences = re.split(r"(?<=[.!?\n])\s+", llm_response.strip())

        for sent in sentences:
            cleaned = sent.strip()
            if not cleaned or len(cleaned) < 8:
                continue

            # Check if sentence is an opinion or advice
            is_opinion = any(p.search(cleaned) for p in OPINION_OR_ADVICE_PATTERNS)
            if is_opinion:
                continue

            # Check if sentence makes a statement about the user, their data, or history
            is_user_claim = any(p.search(cleaned) for p in USER_CLAIM_PATTERNS)
            if is_user_claim:
                category = "user_data"
                if re.search(r"\b(history|yesterday|earlier|previously|last\s+week)\b", cleaned, re.I):
                    category = "user_history"
                elif re.search(r"\b(goal|project|task|habit|system)\b", cleaned, re.I):
                    category = "user_data"
                claims.append(FactualClaim(statement=cleaned, category=category, confidence=1.0))

        return claims

    def contains_evidence_for(self, context_content: str, claim: str) -> bool:
        """
        SPEC §2.6 line 1832:
        Checks if context_forge_content contains evidence for the claim.
        Utilizes token/subphrase grounding check.
        """
        if not context_content:
            return False
        if not claim:
            return True

        normalized_context = context_content.lower()

        # Step 1: Check quantities / numbers (hallucinated metrics/counts are critical ungrounded claims)
        numbers = re.findall(r"\b\d+\b", claim)
        for num in numbers:
            if num not in normalized_context:
                return False

        # Step 2: Extract meaningful keywords
        stopwords = {
            "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
            "with", "by", "from", "up", "about", "into", "over", "after", "is",
            "are", "was", "were", "be", "been", "being", "have", "has", "had",
            "do", "does", "did", "you", "your", "yours", "yourself", "he", "she",
            "it", "they", "we", "i", "me", "my", "this", "that", "these", "those",
            "can", "could", "shall", "should", "will", "would", "may", "might",
            "must", "of", "off", "out", "earlier", "today", "yesterday", "completed"
        }
        tokens = [
            w for w in re.findall(r"\b[a-zA-Z0-9_\-]{3,}\b", claim.lower())
            if w not in stopwords
        ]

        if not tokens:
            words = claim.lower().split()
            if len(words) >= 3:
                for i in range(len(words) - 2):
                    phrase = " ".join(words[i : i + 3])
                    if phrase in normalized_context:
                        return True
            return False

        matches = [t for t in tokens if t in normalized_context]
        grounded_ratio = len(matches) / len(tokens)
        return grounded_ratio >= 0.5

    def check(
        self,
        llm_response: str,
        context_forge_content: str,
        mode: Optional[str] = None,
    ) -> CheckResult:
        """
        SPEC §2.6 lines 1821-1849:
        Runs anti_hallucination_check.
        """
        # Determine active mode
        active_mode = GuardMode(mode.lower()) if mode else self.get_mode()

        if active_mode == GuardMode.OFF:
            return CheckResult(
                block=False,
                original_response=llm_response,
                output_response=llm_response,
                mode=GuardMode.OFF.value,
            )

        # Step 1: Extract claims
        claims = self.extract_factual_claims(llm_response)
        claims_detected = [c.statement for c in claims]

        # Step 2: Check grounding for each claim
        ungrounded: List[str] = []
        for claim in claims:
            if not self.contains_evidence_for(context_forge_content, claim.statement):
                ungrounded.append(claim.statement)

        # Step 3: Handle ungrounded claims
        if ungrounded:
            if active_mode == GuardMode.STRICT:
                # Option A: Reject response and log severity=2 error
                err = BrainErrorLog(
                    timestamp=time.time(),
                    error_type="hallucination",
                    severity=2,
                    ungrounded_claims=ungrounded,
                    details={"original_length": len(llm_response), "claims_count": len(claims)},
                )
                _BRAIN_ERRORS.append(err)
                logger.warning(
                    f"Anti-hallucination guard [STRICT] rejected response: {len(ungrounded)} ungrounded claims"
                )
                return CheckResult(
                    block=True,
                    reason="Response contained ungrounded claims",
                    original_response=llm_response,
                    output_response="",
                    claims_detected=claims_detected,
                    ungrounded_claims=ungrounded,
                    brain_error=err,
                    mode=active_mode.value,
                )

            elif active_mode == GuardMode.WARN:
                # Option B: Add caveat note and log severity=1 error
                caveat = DEFAULT_CAVEAT_MESSAGE
                annotated_response = llm_response.rstrip() + f"\n\n{caveat}"
                err = BrainErrorLog(
                    timestamp=time.time(),
                    error_type="soft_hallucination",
                    severity=1,
                    ungrounded_claims=ungrounded,
                    details={"original_length": len(llm_response), "caveat_added": True},
                )
                _BRAIN_ERRORS.append(err)
                logger.info(
                    f"Anti-hallucination guard [WARN] injected caveat: {len(ungrounded)} ungrounded claims"
                )
                return CheckResult(
                    block=False,
                    reason=None,
                    original_response=llm_response,
                    output_response=annotated_response,
                    claims_detected=claims_detected,
                    ungrounded_claims=ungrounded,
                    brain_error=err,
                    mode=active_mode.value,
                )

        # All claims grounded or no claims detected
        return CheckResult(
            block=False,
            reason=None,
            original_response=llm_response,
            output_response=llm_response,
            claims_detected=claims_detected,
            ungrounded_claims=[],
            brain_error=None,
            mode=active_mode.value,
        )


# Canonical provider registration per modularity architecture (03)
get_registry().register("anti_hallucination", "default", AntiHallucinationProvider)
