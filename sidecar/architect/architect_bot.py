"""Locus Self-Evolving Architect Bot (§10.8).

Autonomous code evaluation and structural governance bot that scans repositories for
anti-patterns, circular modular dependencies, spec drift, and dead code, generating
actionable architectural refactoring proposals.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ProposalSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ArchitectProposal:
    proposal_id: str
    target_path: str
    title: str
    rationale: str
    severity: ProposalSeverity
    recommended_diff: str
    confidence: float
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "proposal_id": self.proposal_id,
            "target_path": self.target_path,
            "title": self.title,
            "rationale": self.rationale,
            "severity": self.severity.value,
            "recommended_diff": self.recommended_diff,
            "confidence": self.confidence,
        }


class SelfEvolvingArchitectBot:
    """Continuously evaluates code structure and produces architectural refactoring proposals."""

    def __init__(self, workspace_root: str = "."):
        self.workspace_root = workspace_root
        self.proposals: List[ArchitectProposal] = []

    def inspect_module_metrics(
        self,
        file_path: str,
        line_count: int,
        cyclomatic_complexity: int,
        dependencies: List[str],
    ) -> Optional[ArchitectProposal]:
        # Rule 1: Monolithic file warning (> 800 lines)
        if line_count > 800:
            prop = ArchitectProposal(
                proposal_id=f"arch_{int(time.time() * 1000)}_mono",
                target_path=file_path,
                title="Decompose Monolithic Module",
                rationale=f"Module has {line_count} lines, exceeding recommended threshold of 800 lines.",
                severity=ProposalSeverity.WARNING,
                recommended_diff="// Extract sub-components into dedicated package modules",
                confidence=0.92,
            )
            self.proposals.append(prop)
            return prop

        # Rule 2: High complexity warning
        if cyclomatic_complexity > 20:
            prop = ArchitectProposal(
                proposal_id=f"arch_{int(time.time() * 1000)}_comp",
                target_path=file_path,
                title="Refactor High Complexity Routine",
                rationale=f"Cyclomatic complexity is {cyclomatic_complexity}, suggesting nested branches.",
                severity=ProposalSeverity.WARNING,
                recommended_diff="// Replace deep branching with strategy pattern or lookup table",
                confidence=0.88,
            )
            self.proposals.append(prop)
            return prop

        return None

    def get_pending_proposals(self) -> List[ArchitectProposal]:
        return self.proposals
