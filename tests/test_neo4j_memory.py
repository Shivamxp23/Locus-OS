"""tests/test_neo4j_memory.py - Unit & Integration Tests for Neo4j Agent Memory.

Tests Spec §4.1-4.2 & §4.18:
- POLE+O Entity creation and deduplication.
- Relationship edge creation and pathway traversal.
- Formatted Layer 4 Context Forge generation: 'src → REL (w) → dst'.
- Short-term session messages and reasoning trace recording.
- Protocol conformance to MemoryProvider.
- Modularity switch: locus.memory.enabled=False.
"""

import pytest

from sidecar.memory.interface import EntityType, MemoryProvider, Pathway
from sidecar.neo4j_memory import Neo4jMemoryClient


def test_memory_client_protocol_conformance():
    client = Neo4jMemoryClient()
    assert isinstance(client, MemoryProvider)


def test_pole_plus_o_entity_deduplication():
    client = Neo4jMemoryClient(enabled=True)

    # Add Person
    p1 = client.add_entity("Shivam", entity_type=EntityType.PERSON, properties={"role": "owner"})
    assert p1.name == "Shivam"
    assert p1.entity_type == EntityType.PERSON

    # Merge same Person (case-insensitive deduplication)
    p2 = client.add_entity("shivam", entity_type=EntityType.PERSON, properties={"status": "active"})
    assert p1.id == p2.id
    assert p2.properties["status"] == "active"
    assert p2.properties["role"] == "owner"


def test_relationship_writing_and_pathway_traversal():
    client = Neo4jMemoryClient(enabled=True)

    client.add_entity("Task_Refactoring", entity_type=EntityType.EVENT)
    client.add_entity("DeepWorkMode", entity_type=EntityType.OBJECT)
    client.add_entity("HighQualityCode", entity_type=EntityType.FACT)

    # Write edges
    client.write_relation("Task_Refactoring", "TRIGGERED_IN", "DeepWorkMode", weight=0.85)
    client.write_relation("DeepWorkMode", "YIELDED", "HighQualityCode", weight=0.92)

    # Traverse
    pathways = client.traverse("DeepWorkMode", depth=2, min_weight=0.3)
    assert len(pathways) == 2
    assert any("TRIGGERED_IN" in p.relation for p in pathways)
    assert any("YIELDED" in p.relation for p in pathways)


def test_context_forge_layer4_formatting():
    client = Neo4jMemoryClient(enabled=True)
    client.write_relation("MorningRoutine", "ENABLES", "ProductiveSprint", weight=0.88)

    ctx = client.get_context("MorningRoutine", max_tokens=150)
    assert "MorningRoutine → ENABLES (w:0.88) → ProductiveSprint" in ctx


def test_short_term_and_reasoning_traces():
    client = Neo4jMemoryClient(enabled=True)

    # Short-term messages
    client.short_term.add_message("session-1", "user", "Hello Locus")
    msgs = client.short_term.get_messages("session-1")
    assert len(msgs) == 1
    assert msgs[0]["content"] == "Hello Locus"

    # Reasoning trace
    trace = client.reasoning.record_step("task-123", "Search graph for entities", ["MorningRoutine"])
    assert trace["task_id"] == "task-123"
    assert "MorningRoutine" in trace["touched_entities"]


def test_memory_client_modularity_disabled():
    client = Neo4jMemoryClient(enabled=False)
    ent = client.add_entity("Test", entity_type=EntityType.OBJECT)
    assert ent.id == "disabled"

    ctx = client.get_context("Test")
    assert ctx == ""
