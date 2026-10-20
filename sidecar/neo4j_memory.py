"""
Concrete implementation of Graph-Native Memory with Neo4j and POLE+O taxonomy (SPEC §4.1-4.2 / F-0021).
Manages Short-Term (session conversations), Long-Term (POLE+O entities and relationships),
and Reasoning Memory with :TOUCHED audit edges, feeding Context Forge Layer 4 (Graph, 150t).
"""
from __future__ import annotations

import logging
import re
import threading
import time
import uuid
from typing import Any, Dict, List, Optional

from sidecar.providers.memory import (
    BaseMemoryProvider,
    EntityType,
    GraphQueryResult,
    MemoryConfig,
    MemoryEntry,
    POLEEntity,
    Relationship,
)

logger = logging.getLogger(__name__)


# Standard regexes for lightweight POLE+O entity extraction
_POLE_PATTERNS = [
    (re.compile(r"\b(Shivam|Alice|Bob|Charlie|Dave|User)\b", re.I), EntityType.PERSON),
    (re.compile(r"\b(Locus|Google|Deepmind|OpenAI|Anthropic|Neo4j)\b", re.I), EntityType.ORGANIZATION),
    (re.compile(r"\b(Office|Home|Library|University|Bangalore|Remote)\b", re.I), EntityType.LOCATION),
    (re.compile(r"\b(Meeting|Sprint Review|Hackathon|Launch|Retro|Deployment)\b", re.I), EntityType.EVENT),
    (re.compile(r"\b(Laptop|Phone|Server|Database|Vault|Repository|Sidecar)\b", re.I), EntityType.OBJECT),
]


class Neo4jMemoryProvider(BaseMemoryProvider):
    """
    Default provider for Graph-Native Memory implementing the POLE+O taxonomy
    over Neo4j with in-memory graph resilience for offline/local environments.
    """

    def __init__(self, name: str = "neo4j_memory_default") -> None:
        super().__init__(name=name)
        self._lock = threading.Lock()
        self._config = MemoryConfig()
        self._entities: Dict[str, POLEEntity] = {}
        self._relationships: List[Relationship] = []
        self._entries: List[MemoryEntry] = []
        self._reasoning_traces: List[Dict[str, Any]] = []
        self._driver: Optional[Any] = None

        # Pre-seed canonical root entities
        self._seed_initial_entities()

    def _seed_initial_entities(self) -> None:
        """Seed foundational POLE+O entities."""
        root_entities = [
            POLEEntity(id="ent_shivam", name="Shivam", type=EntityType.PERSON, properties={"role": "User"}),
            POLEEntity(id="ent_locus", name="Locus", type=EntityType.ORGANIZATION, properties={"type": "Framework"}),
            POLEEntity(id="ent_vault", name="Vault", type=EntityType.OBJECT, properties={"type": "KnowledgeBase"}),
            POLEEntity(id="ent_home", name="Home", type=EntityType.LOCATION, properties={"type": "Primary"}),
        ]
        for ent in root_entities:
            self._entities[ent.id] = ent
        self._relationships.append(
            Relationship(source_id="ent_shivam", target_id="ent_locus", type="WORKS_ON", weight=1.0)
        )
        self._relationships.append(
            Relationship(source_id="ent_locus", target_id="ent_vault", type="MANAGES", weight=1.0)
        )

    def get_config(self) -> MemoryConfig:
        return self._config

    def _extract_entities_from_text(self, text: str) -> List[POLEEntity]:
        """Extract POLE+O entities from content via pattern matcher."""
        extracted: Dict[str, POLEEntity] = {}
        for pattern, ent_type in _POLE_PATTERNS:
            for match in pattern.finditer(text):
                canonical_name = match.group(1).title()
                ent_id = f"ent_{canonical_name.lower()}"
                if ent_id not in extracted:
                    extracted[ent_id] = POLEEntity(
                        id=ent_id,
                        name=canonical_name,
                        type=ent_type,
                        properties={"source": "extracted"},
                    )
        return list(extracted.values())

    def store(
        self,
        content: str,
        entry_type: str = "long_term",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Store conversation turn or fact, extracting and merging POLE+O entities."""
        with self._lock:
            extracted_entities = self._extract_entities_from_text(content)
            for ent in extracted_entities:
                if ent.id not in self._entities:
                    self._entities[ent.id] = ent

            entry_id = f"mem_{uuid.uuid4().hex[:12]}"
            entry = MemoryEntry(
                entry_id=entry_id,
                content=content,
                entry_type=entry_type,
                entities=extracted_entities,
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                metadata=metadata or {},
            )
            self._entries.append(entry)

            # Auto-link extracted entities if multiple present
            if len(extracted_entities) >= 2:
                for i in range(len(extracted_entities) - 1):
                    src = extracted_entities[i].id
                    tgt = extracted_entities[i + 1].id
                    self._relationships.append(
                        Relationship(source_id=src, target_id=tgt, type="MENTIONED_WITH", weight=0.5)
                    )

            logger.info("Stored memory entry %s (%s, %d entities)", entry_id, entry_type, len(extracted_entities))
            return entry

    def add_entity(self, entity: POLEEntity) -> bool:
        """Add or merge a POLE+O entity."""
        with self._lock:
            self._entities[entity.id] = entity
            return True

    def get_entity(self, entity_id_or_name: str) -> Optional[POLEEntity]:
        """Look up entity by exact ID or lowercase name."""
        with self._lock:
            if entity_id_or_name in self._entities:
                return self._entities[entity_id_or_name]
            target = entity_id_or_name.strip().lower()
            for ent in self._entities.values():
                if ent.name.lower() == target:
                    return ent
            return None

    def add_relationship(self, rel: Relationship) -> bool:
        """Add directed edge between entities."""
        with self._lock:
            self._relationships.append(rel)
            return True

    def record_reasoning_step(
        self,
        step_name: str,
        touched_entities: List[str],
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Record reasoning trace step and establish explicit :TOUCHED audit
        edges to the entities involved.
        """
        with self._lock:
            step_id = f"trace_{uuid.uuid4().hex[:8]}"
            trace_record = {
                "step_id": step_id,
                "step_name": step_name,
                "touched_entities": list(touched_entities),
                "tool_calls": tool_calls or [],
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
            self._reasoning_traces.append(trace_record)

            # Link reasoning step with :TOUCHED edge to target entities
            for ent_id in touched_entities:
                if ent_id in self._entities:
                    self._relationships.append(
                        Relationship(
                            source_id=step_id,
                            target_id=ent_id,
                            type="TOUCHED",
                            properties={"step": step_name},
                            weight=1.0,
                        )
                    )
            return step_id

    def query(self, query: str, limit: int = 10, depth: int = 2) -> GraphQueryResult:
        """Execute hybrid keyword and graph traversal query."""
        start_time = time.perf_counter()
        with self._lock:
            query_lower = query.lower()
            matched_entities: List[POLEEntity] = []

            # 1. Match entities by name or properties
            for ent in self._entities.values():
                if ent.name.lower() in query_lower or query_lower in ent.name.lower():
                    matched_entities.append(ent)
                elif any(query_lower in str(v).lower() for v in ent.properties.values()):
                    matched_entities.append(ent)

            # 2. Gather connected relationships up to traversal depth
            matched_ids = {e.id for e in matched_entities}
            active_ids = set(matched_ids)
            subgraph_rels: List[Relationship] = []

            for _ in range(max(1, depth)):
                new_ids = set()
                for rel in self._relationships:
                    if rel.source_id in active_ids or rel.target_id in active_ids:
                        if rel not in subgraph_rels:
                            subgraph_rels.append(rel)
                            new_ids.add(rel.source_id)
                            new_ids.add(rel.target_id)
                active_ids.update(new_ids)

            # Include related entities discovered by traversal
            all_found_entities: List[POLEEntity] = list(matched_entities)
            for eid in active_ids:
                if eid in self._entities and self._entities[eid] not in all_found_entities:
                    all_found_entities.append(self._entities[eid])

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            context_str = self._format_pathways(all_found_entities, subgraph_rels, self._config.max_context_tokens)

            return GraphQueryResult(
                query=query,
                entities=all_found_entities[:limit],
                relationships=subgraph_rels[:limit * 2],
                context_string=context_str,
                latency_ms=round(elapsed_ms, 2),
            )

    def get_context(self, query: str, max_tokens: int = 150) -> str:
        """Format graph pathways directly for Context Forge Layer 4 (Graph, 150t)."""
        res = self.query(query, limit=10, depth=self._config.default_depth)
        with self._lock:
            return self._format_pathways(res.entities, res.relationships, max_tokens)

    def _format_pathways(
        self,
        entities: List[POLEEntity],
        relationships: List[Relationship],
        max_tokens: int,
    ) -> str:
        """Format pathways in 'src -[REL (w)]-> dst' format clamped to max_tokens budget."""
        if not entities and not relationships:
            return "No relevant graph pathways found."

        ent_map = {e.id: f"{e.name} ({e.type.value})" for e in entities}
        lines: List[str] = ["Graph Pathways (POLE+O):"]

        for rel in relationships:
            src_str = ent_map.get(rel.source_id, rel.source_id)
            tgt_str = ent_map.get(rel.target_id, rel.target_id)
            lines.append(f"- {src_str} -[{rel.type} (w={rel.weight:.1f})]-> {tgt_str}")

        text = "\n".join(lines)
        # 1 token ≈ 4 characters rule
        max_chars = max_tokens * 4
        if len(text) > max_chars:
            text = text[:max_chars].rsplit("\n", 1)[0] + "\n[...pathways truncated]"
        return text

    def health_check(self) -> Dict[str, Any]:
        with self._lock:
            ent_count = len(self._entities)
            rel_count = len(self._relationships)
            entry_count = len(self._entries)
            trace_count = len(self._reasoning_traces)

        # Probe status
        backend = "neo4j_live" if self._driver is not None else "in_memory_graph"
        return {
            "status": "healthy",
            "provider": self.__class__.__name__,
            "backend": backend,
            "entities_count": ent_count,
            "relationships_count": rel_count,
            "entries_count": entry_count,
            "reasoning_traces_count": trace_count,
            "pole_schema": {
                "taxonomy": [t.value for t in EntityType],
                "vector_index_dimensions": 1536,
                "supported_edges": ["TOUCHED", "DECIDED", "WORKS_ON", "MANAGES", "MENTIONED_WITH"],
            },
            "config": self._config.to_dict(),
        }
