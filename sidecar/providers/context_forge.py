"""
SPEC §2.5 / F-0094 / US-34: Context Forge (Stage 6) — The 6-Layer Assembler Provider Contract.
Defines parallel retrieval containers, global relevance scoring, layer budgets,
and the assembled context result structure.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import time
from typing import Any, Dict, List, Optional


# Source priorities per SPEC §2.5 line 1766:
# Source priority: Neo4j pathways (0.4) > PG facts (0.3) > pgvector (0.2) > Web (0.1)
SOURCE_PRIORITIES: Dict[str, float] = {
    "neo4j": 0.4,
    "pg": 0.3,
    "pgvector": 0.2,
    "web": 0.1,
}

# Strict anti-hallucination instruction per SPEC §2.5 line 1796:
ANTI_HALLUCINATION_INSTRUCTION: str = (
    "If data needed to answer a question is not in this context, say you don't have it yet. Do NOT invent data."
)

LOCUS_SHORTHAND_DICTIONARY: str = (
    "LOCUS_SHORTHAND: {✓: task_completed, dur: duration_minutes, q: quality_score_1_to_10, "
    "p: priority_1_to_4, cat: category}"
)


@dataclass
class LayerBudgetConfig:
    """
    SPEC §2.5 line 1769-1784, 1807:
    Layer Budgets: Configurable via locus.brain.context_forge.layers
    (Identity 80t, Temporal 60t, Events 180t, Neo4j 150t, pgvector 200t, Web 100t; Hard total limit: 800 tokens).
    """
    identity_limit: int = 80
    temporal_limit: int = 60
    events_limit: int = 180
    neo4j_limit: int = 150
    semantic_limit: int = 200
    web_limit: int = 100
    total_limit: int = 800

    def to_dict(self) -> Dict[str, int]:
        return {
            "identity_limit": self.identity_limit,
            "temporal_limit": self.temporal_limit,
            "events_limit": self.events_limit,
            "neo4j_limit": self.neo4j_limit,
            "semantic_limit": self.semantic_limit,
            "web_limit": self.web_limit,
            "total_limit": self.total_limit,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LayerBudgetConfig:
        return cls(
            identity_limit=int(data.get("identity_limit", 80)),
            temporal_limit=int(data.get("temporal_limit", 60)),
            events_limit=int(data.get("events_limit", 180)),
            neo4j_limit=int(data.get("neo4j_limit", 150)),
            semantic_limit=int(data.get("semantic_limit", 200)),
            web_limit=int(data.get("web_limit", 100)),
            total_limit=int(data.get("total_limit", 800)),
        )


@dataclass
class AssembledLayer:
    """Represents a single assembled context layer."""
    layer_num: int
    name: str
    content: str
    token_count: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "layer_num": self.layer_num,
            "name": self.name,
            "content": self.content,
            "token_count": self.token_count,
        }


@dataclass
class RetrievalInput:
    """
    SPEC §2.5 STEP 1: Parallel retrieval results input container.
    """
    identity: Dict[str, Any] = field(default_factory=dict)
    temporal: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    neo4j_paths: List[Dict[str, Any]] = field(default_factory=list)
    semantic_snippets: List[Dict[str, Any]] = field(default_factory=list)
    web_results: List[Dict[str, Any]] = field(default_factory=list)
    intent_requires_web: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "identity": self.identity,
            "temporal": self.temporal,
            "events": self.events,
            "neo4j_paths": self.neo4j_paths,
            "semantic_snippets": self.semantic_snippets,
            "web_results": self.web_results,
            "intent_requires_web": self.intent_requires_web,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> RetrievalInput:
        return cls(
            identity=dict(data.get("identity") or {}),
            temporal=dict(data.get("temporal") or {}),
            events=list(data.get("events") or []),
            neo4j_paths=list(data.get("neo4j_paths") or []),
            semantic_snippets=list(data.get("semantic_snippets") or []),
            web_results=list(data.get("web_results") or []),
            intent_requires_web=bool(data.get("intent_requires_web", False)),
        )


@dataclass
class ContextForgeResult:
    """
    SPEC §2.5 STEP 12: Return Assembled Context Block.
    Delivers complete <=800 token context block + metadata.
    """
    assembled_prompt: str
    layers: List[AssembledLayer]
    total_tokens: int
    compression_applied: bool
    hebbian_updates: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "assembled_prompt": self.assembled_prompt,
            "layers": [layer.to_dict() for layer in self.layers],
            "total_tokens": self.total_tokens,
            "compression_applied": self.compression_applied,
            "hebbian_updates": self.hebbian_updates,
            "metadata": self.metadata,
        }


class BaseContextForgeProvider(ABC):
    """
    Abstract Base Provider for Locus Context Forge (Stage 6).
    """

    @abstractmethod
    def assemble_context(
        self,
        retrieval_input: RetrievalInput,
        budget_override: Optional[LayerBudgetConfig] = None,
    ) -> ContextForgeResult:
        """
        Assemble 6-layer context from retrieval inputs with global relevance scoring,
        layer budgets, CCR compression fallback, and anti-hallucination instructions.
        """
        raise NotImplementedError

    @abstractmethod
    def calculate_relevance_score(
        self,
        semantic_similarity: float,
        recency_weight: float,
        source_priority: float,
    ) -> float:
        """
        SPEC §2.5 STEP 2: Global Relevance Scoring.
        Unified Score = (semantic_similarity × 0.6) + (recency_weight × 0.25) + (source_priority × 0.15)
        """
        raise NotImplementedError

    @abstractmethod
    def is_enabled(self) -> bool:
        """Check modular off-switch."""
        raise NotImplementedError
