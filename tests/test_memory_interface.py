"""tests/test_memory_interface.py - Unit Tests for Memory Provider Interface.

Tests Spec §4.18:
- EntityType enum, MemoryEntry, and Pathway data models.
- MemoryProvider protocol compliance.
- MemoryManager stackable provider registration, prefetch_all, and sync_turn_all.
- Modularity switch: MemoryManager(enabled=False).
"""

from sidecar.memory.interface import (
    EntityType,
    MemoryEntry,
    MemoryManager,
    MemoryProvider,
    Pathway,
)
from sidecar.neo4j_memory import Neo4jMemoryClient


def test_memory_interface_models():
    entry = MemoryEntry(id="ent-1", name="Alice", entity_type=EntityType.PERSON)
    assert entry.name == "Alice"
    assert entry.entity_type == EntityType.PERSON

    pathway = Pathway(source_name="Alice", relation="KNOWS", target_name="Bob", weight=0.9)
    assert pathway.format_line() == "Alice → KNOWS (w:0.90) → Bob"


def test_memory_manager_stackable_providers():
    manager = MemoryManager(enabled=True)
    p1 = Neo4jMemoryClient(enabled=True)
    p2 = Neo4jMemoryClient(enabled=True)

    p1.write_relation("NodeA", "CONNECTS", "NodeB", weight=0.8)
    p2.write_relation("NodeB", "CONNECTS", "NodeC", weight=0.7)

    manager.register_provider(p1)
    manager.register_provider(p2)

    # Prefetch from all providers
    merged = manager.prefetch_all("NodeB")
    assert "NodeA → CONNECTS (w:0.80) → NodeB" in merged
    assert "NodeB → CONNECTS (w:0.70) → NodeC" in merged

    # Sync turn
    manager.sync_turn_all("Hello", "Hi there", session_id="test-session")
    assert len(p1.short_term.get_messages("test-session")) == 2
    assert len(p2.short_term.get_messages("test-session")) == 2


def test_memory_manager_modularity_disabled():
    manager = MemoryManager(enabled=False)
    p = Neo4jMemoryClient(enabled=True)
    p.write_relation("A", "REL", "B", weight=0.9)
    manager.register_provider(p)

    assert manager.prefetch_all("A") == ""
