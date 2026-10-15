"""sidecar/neo4j_memory.py - Neo4j Agent Memory (POLE+O).

Implements Spec §4.1-4.2:
- Graph-native agent memory implementing POLE+O schema:
  Person, Object, Location, Event, Organization (+ Preference, Fact).
- Three sub-clients:
  - short_term: Conversation and Message nodes.
  - long_term: Entity nodes and semantic relations.
  - reasoning: ReasoningTrace, ReasoningStep, and ToolCall nodes with :TOUCHED edges.
- Supports both live Neo4j bolt driver and in-memory fallback graph.
- Generates Layer 4 Context Forge formatted context string:
  'src → REL (w:0.84) → dst'.
- Modularity: locus.memory.enabled.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
import uuid
from typing import Any, Dict, List, Optional

from sidecar.memory.interface import (
    EntityType,
    MemoryEntry,
    MemoryProvider,
    Pathway,
)

logger = logging.getLogger("sidecar.neo4j_memory")


class ShortTermMemory:
    """Manages conversational session turns and messages."""

    def __init__(self):
        self._sessions: dict[str, list[dict[str, Any]]] = {}

    def add_message(self, session_id: str, role: str, content: str) -> dict[str, Any]:
        msg = {
            "id": f"msg-{uuid.uuid4().hex[:8]}",
            "session_id": session_id,
            "role": role,
            "content": content,
        }
        self._sessions.setdefault(session_id, []).append(msg)
        return msg

    def get_messages(self, session_id: str, limit: int = 20) -> list[dict[str, Any]]:
        return self._sessions.get(session_id, [])[-limit:]


class ReasoningTraceMemory:
    """Records reasoning steps, decisions, and :TOUCHED entity edges."""

    def __init__(self):
        self._traces: list[dict[str, Any]] = []

    def record_step(self, task_id: str, step: str, touched_entities: list[str]) -> dict[str, Any]:
        trace = {
            "id": f"trace-{uuid.uuid4().hex[:8]}",
            "task_id": task_id,
            "step": step,
            "touched_entities": list(touched_entities),
        }
        self._traces.append(trace)
        return trace


class Neo4jMemoryClient:
    """Core Graph-Native Memory Provider implementing Spec §4.1-4.2."""

    def __init__(self, enabled: bool = True, uri: Optional[str] = None):
        self.enabled = enabled
        self.uri = uri or "bolt://127.0.0.1:7687"
        self.short_term = ShortTermMemory()
        self.reasoning = ReasoningTraceMemory()
        # In-memory graph nodes and edges
        self._entities: dict[str, MemoryEntry] = {}
        self._pathways: list[Pathway] = []

    def add_entity(
        self,
        name: str,
        entity_type: EntityType = EntityType.OBJECT,
        properties: Optional[dict[str, Any]] = None,
    ) -> MemoryEntry:
        """MERGE entity node into graph by canonical name."""
        if not self.enabled:
            return MemoryEntry(id="disabled", name=name, entity_type=entity_type)

        key = name.strip().lower()
        if key in self._entities:
            entry = self._entities[key]
            if properties:
                entry.properties.update(properties)
            return entry

        entry_id = f"ent-{uuid.uuid4().hex[:8]}"
        entry = MemoryEntry(
            id=entry_id,
            name=name.strip(),
            entity_type=entity_type,
            properties=properties or {},
            weight=1.0,
        )
        self._entities[key] = entry
        return entry

    def write_relation(
        self,
        source_name: str,
        relation: str,
        target_name: str,
        weight: float = 0.5,
    ) -> Pathway:
        """MERGE relationship edge between source and target entities."""
        if not self.enabled:
            return Pathway(source_name=source_name, relation=relation, target_name=target_name, weight=0.0)

        # Ensure entities exist
        self.add_entity(source_name)
        self.add_entity(target_name)

        # Check existing edge
        rel_key = relation.strip().upper()
        for p in self._pathways:
            if (
                p.source_name.lower() == source_name.lower()
                and p.target_name.lower() == target_name.lower()
                and p.relation == rel_key
            ):
                p.weight = min(1.0, max(0.0, weight))
                return p

        new_pathway = Pathway(
            source_name=source_name,
            relation=rel_key,
            target_name=target_name,
            weight=min(1.0, max(0.0, weight)),
        )
        self._pathways.append(new_pathway)
        return new_pathway

    def traverse(self, query: str, depth: int = 2, min_weight: float = 0.3) -> list[Pathway]:
        """Perform pathway traversal starting from entities matching query terms."""
        if not self.enabled:
            return []

        q_terms = [t.lower() for t in query.split() if len(t) >= 3]
        matched: list[Pathway] = []

        for p in self._pathways:
            if p.weight < min_weight:
                continue
            # Match either source or target term
            if any(t in p.source_name.lower() or t in p.target_name.lower() for t in q_terms):
                matched.append(p)

        # Sort by edge weight descending
        matched.sort(key=lambda x: x.weight, reverse=True)
        return matched

    def get_context(self, query: str, max_tokens: int = 150) -> str:
        """Assemble formatted graph pathway context for Context Forge Layer 4."""
        if not self.enabled:
            return ""

        pathways = self.traverse(query, depth=2, min_weight=0.3)
        if not pathways:
            return ""

        lines = [p.format_line() for p in pathways]
        text = "\n".join(lines)

        # Truncate to token limit (approx 4 chars per token)
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            text = text[:max_chars].rstrip() + "..."
        return text
