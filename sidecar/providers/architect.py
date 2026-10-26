"""
SPEC §10.8 lines 6306-6355:
Self-Evolving Architect Bot Provider Interface and Implementation (F-0120 / US-66).
Implements BaseArchitectProvider and DefaultArchitectProvider with modular off-switch:
- locus.architect.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.architect.engine import (
    ArchitectCandidate,
    ArchitectEngine,
    RiskClass,
    SignalBundle,
    TargetClass,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseArchitectProvider(ABC):
    """
    SPEC §10.8: Provider Interface: ArchitectProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Self-Evolving Architect Bot is enabled."""
        raise NotImplementedError

    @abstractmethod
    def scan(
        self,
        reward_model: Optional[List[Dict[str, Any]]] = None,
        hebbian_weights: Optional[Dict[str, float]] = None,
        experiences: Optional[List[Dict[str, Any]]] = None,
        life_os_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Scan reward, pattern, experience, and Life OS signals and generate candidate patches."""
        raise NotImplementedError

    @abstractmethod
    def get_candidates(self) -> List[Dict[str, Any]]:
        """List active/pending candidate patches."""
        raise NotImplementedError

    @abstractmethod
    def apply_candidate(self, candidate_id: str) -> Dict[str, Any]:
        """Apply, stage, or delegate a candidate patch based on risk gate."""
        raise NotImplementedError

    @abstractmethod
    def get_history(self) -> List[Dict[str, Any]]:
        """Get history of applied patches and recorded outcomes."""
        raise NotImplementedError


class DefaultArchitectProvider(BaseArchitectProvider):
    """
    SPEC §10.8: Default implementation of ArchitectProvider.
    Self-improvement loop with risk gating and Philosophy Point 7 coding harness delegation.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".locus" / "architect")
        self.engine = ArchitectEngine(storage_dir=self.storage_dir)

    def is_available(self) -> bool:
        """Check modular off-switch locus.architect.enabled."""
        val = config.get("locus.architect.enabled")
        if val is not None and not config.is_enabled("locus.architect.enabled"):
            return False
        return True

    def scan(
        self,
        reward_model: Optional[List[Dict[str, Any]]] = None,
        hebbian_weights: Optional[Dict[str, float]] = None,
        experiences: Optional[List[Dict[str, Any]]] = None,
        life_os_metrics: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Scan signals and propose improvement candidates."""
        signals = self.engine.gather_signals(
            reward_model=reward_model,
            hebbian_weights=hebbian_weights,
            experiences=experiences,
            life_os_metrics=life_os_metrics,
        )
        candidates = self.engine.propose_improvements(signals)
        return {
            "status": "ok",
            "candidates_count": len(candidates),
            "candidates": [c.to_dict() for c in candidates],
        }

    def get_candidates(self) -> List[Dict[str, Any]]:
        """Return all proposed/staged improvement candidates."""
        return [c.to_dict() for c in self.engine.get_candidates()]

    def apply_candidate(self, candidate_id: str) -> Dict[str, Any]:
        """Apply or stage candidate subject to risk gate."""
        risk_gate_mode = str(config.get("locus.architect.risk_gate") or "approval")
        outcome = self.engine.apply_patch(candidate_id=candidate_id, risk_gate_mode=risk_gate_mode)
        return {
            "status": "ok",
            "outcome": outcome,
        }

    def get_history(self) -> List[Dict[str, Any]]:
        """Return history log."""
        return self.engine.get_history()
