"""sidecar/context_forge.py - Context Forge (Stage 6) — 6-Layer Context Assembler.

Implements Spec §2.5:
- 6-Layer assembly with token budgets:
  - Layer 1: Identity (80 tokens) [Protected]
  - Layer 2: Temporal Context (60 tokens) [Protected]
  - Layer 3: PostgreSQL Events (180 tokens) [Compressible]
  - Layer 4: Neo4j Pathways (150 tokens) [Compressible]
  - Layer 5: Semantic Retrieval / pgvector (200 tokens) [Compressible]
  - Layer 6: Web Search Results (100 tokens) [Compressible]
- Hard total context budget: 800 tokens.
- Compression fallback: compresses Layers 5 & 3 when exceeding budget. Layers 1 & 2 are NEVER truncated.
- System prompt and anti-hallucination instruction prepend.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

ANTI_HALLUCINATION_HEADER = (
    "STRICT DIRECTIVE: If data needed to answer a question is not in this context, "
    "say you don't have it yet. Do NOT invent data."
)

LOCUS_SHORTHAND_DICTIONARY = (
    "[LOCUS_SHORTHAND: ✓=completed, dur=duration_min, q=quality_1_10, "
    "tws=task_weight_score, dcs=daily_capacity_score]"
)


@dataclass
class ContextLayers:
    """The 6 distinct layers of user and task context."""

    identity: str = ""  # Layer 1 (max 80t, protected)
    temporal: str = ""  # Layer 2 (max 60t, protected)
    events: str = ""  # Layer 3 (max 180t, compressible)
    neo4j_paths: str = ""  # Layer 4 (max 150t, compressible)
    semantic: str = ""  # Layer 5 (max 200t, compressible)
    web: str = ""  # Layer 6 (max 100t, compressible)


@dataclass
class AssembledContext:
    """Complete assembled context block ready for generator."""

    context_text: str
    total_tokens_est: int
    compressed: bool
    layers_included: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class ContextAssembler(Protocol):
    """Protocol for Context Forge assemblers."""

    def assemble(self, layers: ContextLayers) -> AssembledContext:
        """Assemble 6 layers into a budgeted prompt context block."""
        return AssembledContext(
            context_text="",
            total_tokens_est=0,
            compressed=False,
            layers_included=[],
        )


class ContextForge:
    """Core Context Forge implementing Spec §2.5."""

    # Layer limits in estimated tokens (~4 chars per token)
    LIMIT_IDENTITY = 80
    LIMIT_TEMPORAL = 60
    LIMIT_EVENTS = 180
    LIMIT_NEO4J = 150
    LIMIT_SEMANTIC = 200
    LIMIT_WEB = 100
    TOTAL_BUDGET = 800

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Heuristic token estimator (~4 chars per token)."""
        if not text:
            return 0
        return max(1, len(text.strip()) // 4)

    @classmethod
    def truncate_to_tokens(cls, text: str, max_tokens: int) -> str:
        """Truncate text to approximate token limit."""
        max_chars = max_tokens * 4
        if len(text) <= max_chars:
            return text
        return text[:max_chars].rstrip() + "..."

    def assemble(self, layers: ContextLayers) -> AssembledContext:
        """Assemble the 6 layers within the hard 800 token budget."""
        if not self.enabled:
            return AssembledContext(
                context_text="",
                total_tokens_est=0,
                compressed=False,
                layers_included=[],
                metadata={"disabled": True},
            )

        # Step 1: Pre-clamp layers to their individual upper limits
        l1 = self.truncate_to_tokens(layers.identity, self.LIMIT_IDENTITY)
        l2 = self.truncate_to_tokens(layers.temporal, self.LIMIT_TEMPORAL)
        l3 = self.truncate_to_tokens(layers.events, self.LIMIT_EVENTS)
        l4 = self.truncate_to_tokens(layers.neo4j_paths, self.LIMIT_NEO4J)
        l5 = self.truncate_to_tokens(layers.semantic, self.LIMIT_SEMANTIC)
        l6 = self.truncate_to_tokens(layers.web, self.LIMIT_WEB)

        layers_map = {
            "Layer 1 (Identity)": l1,
            "Layer 2 (Temporal)": l2,
            "Layer 3 (Events)": l3,
            "Layer 4 (Neo4j)": l4,
            "Layer 5 (Semantic)": l5,
            "Layer 6 (Web)": l6,
        }

        included_names = [name for name, content in layers_map.items() if content.strip()]

        all_blocks = [
            ANTI_HALLUCINATION_HEADER,
            LOCUS_SHORTHAND_DICTIONARY,
            *[f"[{name}]\n{content}" for name, content in layers_map.items() if content.strip()],
        ]
        full_text = "\n\n".join(all_blocks)
        total_tokens = self.estimate_tokens(full_text)

        truncated_any = any(
            [
                len(layers.identity) > len(l1),
                len(layers.temporal) > len(l2),
                len(layers.events) > len(l3),
                len(layers.neo4j_paths) > len(l4),
                len(layers.semantic) > len(l5),
                len(layers.web) > len(l6),
            ]
        )
        compressed = truncated_any or (total_tokens > self.TOTAL_BUDGET)

        # Step 9: Headroom Compression if exceeding 800 tokens
        if total_tokens > self.TOTAL_BUDGET:
            compressed = True
            # Layers 1 & 2 are NEVER compressed or truncated.
            # Compress Layer 5 (Semantic) by 50%
            if l5:
                layers_map["Layer 5 (Semantic)"] = self.truncate_to_tokens(l5, self.LIMIT_SEMANTIC // 2)
            # Compress Layer 3 (Events) by 50%
            if l3:
                layers_map["Layer 3 (Events)"] = self.truncate_to_tokens(l3, self.LIMIT_EVENTS // 2)
            # Compress Layer 6 (Web) if still needed
            if l6:
                layers_map["Layer 6 (Web)"] = self.truncate_to_tokens(l6, self.LIMIT_WEB // 2)

            all_blocks = [
                ANTI_HALLUCINATION_HEADER,
                LOCUS_SHORTHAND_DICTIONARY,
                *[f"[{name}]\n{content}" for name, content in layers_map.items() if content.strip()],
            ]
            full_text = "\n\n".join(all_blocks)
            total_tokens = self.estimate_tokens(full_text)

        return AssembledContext(
            context_text=full_text,
            total_tokens_est=total_tokens,
            compressed=compressed,
            layers_included=included_names,
            metadata={
                "budget": self.TOTAL_BUDGET,
                "l1_protected": True,
                "l2_protected": True,
            },
        )
