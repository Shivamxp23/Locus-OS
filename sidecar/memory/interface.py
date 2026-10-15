"""sidecar/memory/interface.py - Unified Memory Provider Interface.

Implements Spec §4.18:
- BaseMemory protocol defining standard operations: add, search, get_context, delete.
- MemoryEntry, Pathway, and MemoryQueryResult data models.
- Modular pluggability across graph (Neo4j), vector, and local stores.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Protocol, runtime_checkable


class EntityType(str, Enum):
    """POLE+O taxonomy entity types."""
    PERSON = "Person"
    OBJECT = "Object"
    LOCATION = "Location"
    EVENT = "Event"
    ORGANIZATION = "Organization"
    PREFERENCE = "Preference"
    FACT = "Fact"


@dataclass
class MemoryEntry:
    """Standardized memory node representation."""
    id: str
    name: str
    entity_type: EntityType
    properties: dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0
    created_at: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())


@dataclass
class Pathway:
    """Graph pathway edge between memory entities."""
    source_name: str
    relation: str
    target_name: str
    weight: float = 0.5
    last_traversed: float = field(default_factory=lambda: datetime.now(timezone.utc).timestamp())

    def format_line(self) -> str:
        """Format as 'src → REL (w) → dst'."""
        return f"{self.source_name} → {self.relation} (w:{self.weight:.2f}) → {self.target_name}"


@dataclass
class MemoryQueryResult:
    """Formatted results returned from memory queries."""
    query: str
    context_text: str
    entities: list[MemoryEntry] = field(default_factory=list)
    pathways: list[Pathway] = field(default_factory=list)
    total_tokens_est: int = 0


@runtime_checkable
class MemoryProvider(Protocol):
    """Protocol for Locus OS Memory Providers."""

    def add_entity(self, name: str, entity_type: EntityType, properties: Optional[dict[str, Any]] = None) -> MemoryEntry:
        """Add or merge an entity into the memory graph."""
        return MemoryEntry(id="default", name=name, entity_type=entity_type)

    def write_relation(self, source_name: str, relation: str, target_name: str, weight: float = 0.5) -> Pathway:
        """Write a relation edge between entities."""
        return Pathway(source_name=source_name, relation=relation, target_name=target_name, weight=weight)

    def get_context(self, query: str, max_tokens: int = 150) -> str:
        """Retrieve formatted pathway context for Context Forge Layer 4."""
        return ""


class MemoryManager:
    """Manages stackable memory providers (primary + secondary) per Spec §4.18."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._providers: list[MemoryProvider] = []

    def register_provider(self, provider: MemoryProvider) -> None:
        """Register a memory provider into the active stack."""
        if provider not in self._providers:
            self._providers.append(provider)

    def prefetch_all(self, query: str, max_tokens: int = 150) -> str:
        """Recall context from all active providers and merge results."""
        if not self.enabled:
            return ""
        blocks: list[str] = []
        for p in self._providers:
            ctx = p.get_context(query, max_tokens=max_tokens)
            if ctx.strip():
                blocks.append(ctx.strip())
        return "\n".join(blocks)

    def sync_turn_all(self, user_text: str, assistant_text: str, session_id: str = "default") -> None:
        """Sync turn across all active memory providers."""
        if not self.enabled:
            return
        for p in self._providers:
            # Sync to provider if supported
            if hasattr(p, "short_term"):
                getattr(p, "short_term").add_message(session_id, "user", user_text)
                getattr(p, "short_term").add_message(session_id, "assistant", assistant_text)
