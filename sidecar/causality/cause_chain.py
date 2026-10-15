"""Locus Cause Chain Engine (§30.2 / §30.3).

Infers, traces, and evaluates causal chains across agent events, state mutations,
and environmental triggers to provide causal explanation and predict cascading impact.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class CausalRelationType(str, Enum):
    DIRECT_CAUSE = "direct_cause"
    ENABLER = "enabler"
    TRIGGER = "trigger"
    INHIBITOR = "inhibitor"


@dataclass
class CausalLink:
    source_event: str
    target_event: str
    relation_type: CausalRelationType
    confidence: float  # 0.0 to 1.0
    evidence: str
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_event": self.source_event,
            "target_event": self.target_event,
            "relation_type": self.relation_type.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "timestamp": self.timestamp,
        }


class CauseChainEngine:
    """Maintains a directed causal graph and infers root causes and cascade risks."""

    def __init__(self):
        self.links: List[CausalLink] = []
        self.forward_graph: Dict[str, List[CausalLink]] = {}
        self.backward_graph: Dict[str, List[CausalLink]] = {}

    def record_link(
        self,
        source_event: str,
        target_event: str,
        relation_type: CausalRelationType = CausalRelationType.DIRECT_CAUSE,
        confidence: float = 0.9,
        evidence: str = "",
    ) -> CausalLink:
        link = CausalLink(
            source_event=source_event,
            target_event=target_event,
            relation_type=relation_type,
            confidence=confidence,
            evidence=evidence,
        )
        self.links.append(link)

        if source_event not in self.forward_graph:
            self.forward_graph[source_event] = []
        self.forward_graph[source_event].append(link)

        if target_event not in self.backward_graph:
            self.backward_graph[target_event] = []
        self.backward_graph[target_event].append(link)

        return link

    def trace_root_causes(self, effect_event: str, max_depth: int = 5) -> List[str]:
        roots: Set[str] = set()
        visited: Set[str] = set()

        def dfs(current: str, depth: int):
            if depth >= max_depth or current in visited:
                return
            visited.add(current)

            parents = self.backward_graph.get(current, [])
            if not parents:
                roots.add(current)
            else:
                for p in parents:
                    dfs(p.source_event, depth + 1)

        dfs(effect_event, 0)
        return list(roots)

    def predict_cascade_impact(self, trigger_event: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        cascade: List[Dict[str, Any]] = []
        visited: Set[str] = {trigger_event}
        current_layer = [trigger_event]

        for step in range(1, max_depth + 1):
            next_layer = []
            for ev in current_layer:
                links = self.forward_graph.get(ev, [])
                for l in links:
                    if l.target_event not in visited:
                        visited.add(l.target_event)
                        cascade.append({
                            "step": step,
                            "source": ev,
                            "target": l.target_event,
                            "confidence": l.confidence,
                        })
                        next_layer.append(l.target_event)
            current_layer = next_layer
            if not current_layer:
                break

        return cascade
