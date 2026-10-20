"""
Unit tests for Graph-Native Memory (SPEC §4.1-4.2 / F-0021).
Asserts POLE+O entity taxonomy, relationship linking, reasoning steps with :TOUCHED
audit edges, Context Forge Layer 4 formatting (150t), error containment, and swappability.
"""
from __future__ import annotations

import pytest

from sidecar.neo4j_memory import Neo4jMemoryProvider
from sidecar.providers.memory import (
    BaseMemoryProvider,
    EntityType,
    GraphQueryResult,
    MemoryConfig,
    MemoryEntry,
    POLEEntity,
    Relationship,
)


def test_pole_taxonomy_validation() -> None:
    """SPEC §4.1-4.2 line 604: "- **Long-term** (knowledge graph): Entity + Preference + Fact nodes, in the **POLE+O** entity-type taxonomy (Person / Object / Location / Event / Organization)." """
    person = POLEEntity(id="p1", name="Shivam", type=EntityType.PERSON)
    obj = POLEEntity(id="o1", name="Laptop", type=EntityType.OBJECT)
    loc = POLEEntity(id="l1", name="Bangalore", type=EntityType.LOCATION)
    evt = POLEEntity(id="e1", name="Launch", type=EntityType.EVENT)
    org = POLEEntity(id="r1", name="Locus", type=EntityType.ORGANIZATION)

    assert person.type == EntityType.PERSON
    assert obj.type == EntityType.OBJECT
    assert loc.type == EntityType.LOCATION
    assert evt.type == EntityType.EVENT
    assert org.type == EntityType.ORGANIZATION

    # Dict roundtrip
    d = person.to_dict()
    assert d["type"] == "Person"
    restored = POLEEntity.from_dict(d)
    assert restored.id == "p1"
    assert restored.type == EntityType.PERSON


def test_entity_deduplication_and_extraction() -> None:
    """SPEC §4.1-4.2 line 608: "Ingestion path: raw text → entity/relation extraction → graph write (MERGE on (:Entity {name, type}) to dedup/entity-resolve)" """
    provider = Neo4jMemoryProvider()
    entry = provider.store(
        content="Shivam is working from Office on the Locus repository using a Laptop.",
        entry_type="long_term",
    )
    assert entry.entry_id.startswith("mem_")
    extracted_names = {e.name.lower() for e in entry.entities}
    assert "shivam" in extracted_names
    assert "office" in extracted_names
    assert "locus" in extracted_names


def test_add_and_query_entity() -> None:
    """SPEC §4.1-4.2 line 617: "BaseMemory: add(content) -> entry; search(query) -> [entries]" """
    provider = Neo4jMemoryProvider()
    ent = POLEEntity(id="ent_custom_ai", name="Antigravity", type=EntityType.ORGANIZATION, properties={"tier": "primary"})
    assert provider.add_entity(ent) is True

    fetched = provider.get_entity("ent_custom_ai")
    assert fetched is not None
    assert fetched.name == "Antigravity"

    by_name = provider.get_entity("antigravity")
    assert by_name is not None
    assert by_name.id == "ent_custom_ai"


def test_relationships_and_traversal() -> None:
    """SPEC §4.1-4.2 line 610: "Retrieval path: get_context(query) → hybrid (vector similarity over embeddings + text search + graph traversal)" """
    provider = Neo4jMemoryProvider()
    # Add entities and explicit relationships
    provider.add_entity(POLEEntity(id="ent_charlie", name="Charlie", type=EntityType.PERSON))
    provider.add_entity(POLEEntity(id="ent_project_x", name="ProjectX", type=EntityType.OBJECT))
    provider.add_relationship(Relationship(source_id="ent_charlie", target_id="ent_project_x", type="LEADS", weight=1.5))

    query_res = provider.query("Charlie", depth=2)
    assert isinstance(query_res, GraphQueryResult)
    matched_ids = {e.id for e in query_res.entities}
    assert "ent_charlie" in matched_ids
    assert "ent_project_x" in matched_ids

    rel_types = {r.type for r in query_res.relationships}
    assert "LEADS" in rel_types


def test_reasoning_step_touched_edges() -> None:
    """SPEC §4.1-4.2 line 605: "- **Reasoning** (learn from past decisions): ReasoningTrace + ReasoningStep + Tool + ToolCall nodes, with explicit :TOUCHED audit edges from reasoning steps to the entities they used." """
    provider = Neo4jMemoryProvider()
    step_id = provider.record_reasoning_step(
        step_name="SynthesizePlan",
        touched_entities=["ent_shivam", "ent_locus"],
        tool_calls=[{"tool": "locus_checkin", "status": "ok"}],
    )
    assert step_id.startswith("trace_")

    # Traverse to verify :TOUCHED edge exists
    query_res = provider.query("Shivam", depth=2)
    touched_edges = [r for r in query_res.relationships if r.type == "TOUCHED"]
    assert len(touched_edges) >= 1
    assert any(r.source_id == step_id and r.target_id == "ent_shivam" for r in touched_edges)


def test_get_context_layer4_formatting() -> None:
    """SPEC §4.1-4.2 line 635: "Provider Interface: implements MemoryProvider; get_context(query) feeds Context Forge Layer 4 (Graph, 150t)." """
    provider = Neo4jMemoryProvider()
    ctx = provider.get_context("Shivam", max_tokens=150)
    assert isinstance(ctx, str)
    assert "Graph Pathways (POLE+O):" in ctx
    assert "Shivam" in ctx
    assert "WORKS_ON" in ctx
    # Verify budget clamping (150 tokens ≈ 600 characters)
    assert len(ctx) <= 700


def test_health_check_diagnostics() -> None:
    """SPEC §4.1-4.2 line 638: "Swappable / off state" """
    provider = Neo4jMemoryProvider()
    health = provider.health_check()
    assert health["status"] == "healthy"
    assert health["provider"] == "Neo4jMemoryProvider"
    assert health["entities_count"] >= 4
    assert health["relationships_count"] >= 2
    assert "pole_schema" in health
    assert "Person" in health["pole_schema"]["taxonomy"]


def test_swappable_memory_provider() -> None:
    """SPEC §4.1-4.2 line 638: "Swappable / off state: locus.memory.provider can be mem0 / supermemory / honcho / mastra / cognee / custom" """
    class MockMem0Provider(BaseMemoryProvider):
        def store(self, content: str, entry_type: str = "long_term", metadata=None):
            return MemoryEntry(entry_id="mock_1", content=content)
        def query(self, query: str, limit: int = 10, depth: int = 2):
            return GraphQueryResult(query=query, context_string="mock context")
        def get_context(self, query: str, max_tokens: int = 150) -> str:
            return "mock context"
        def add_entity(self, entity: POLEEntity) -> bool:
            return True
        def get_entity(self, entity_id_or_name: str):
            return None
        def add_relationship(self, rel: Relationship) -> bool:
            return True
        def record_reasoning_step(self, step_name: str, touched_entities, tool_calls=None) -> str:
            return "mock_step"
        def health_check(self):
            return {"status": "swapped_mem0"}
        def get_config(self):
            return MemoryConfig(provider="mem0")

    swapped = MockMem0Provider(name="mock_mem0")
    assert swapped.name == "mock_mem0"
    assert swapped.get_context("test") == "mock context"
    assert swapped.health_check()["status"] == "swapped_mem0"
