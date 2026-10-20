"""
Abstract base provider and data models for Graph-Native Memory (SPEC §4.1-4.2 / F-0021).
Implements the POLE+O (Person, Object, Location, Event, Organization) taxonomy,
relationship modeling, reasoning traces with :TOUCHED edges, and Context Forge Layer 4 integration.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class EntityType(str, Enum):
    """POLE+O entity taxonomy from SPEC §4.1-4.2."""
    PERSON = "Person"
    OBJECT = "Object"
    LOCATION = "Location"
    EVENT = "Event"
    ORGANIZATION = "Organization"
    CUSTOM = "Custom"


@dataclass(frozen=True)
class POLEEntity:
    """Graph entity conforming to the POLE+O taxonomy."""
    id: str
    name: str
    type: EntityType = EntityType.OBJECT
    properties: Dict[str, Any] = field(default_factory=dict)
    user_identifier: str = "default_user"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value if isinstance(self.type, EntityType) else str(self.type),
            "properties": dict(self.properties),
            "user_identifier": self.user_identifier,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> POLEEntity:
        raw_type = data.get("type", "Object")
        try:
            ent_type = EntityType(raw_type)
        except ValueError:
            ent_type = EntityType.CUSTOM
        return cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            type=ent_type,
            properties=data.get("properties", {}),
            user_identifier=data.get("user_identifier", "default_user"),
        )


@dataclass(frozen=True)
class Relationship:
    """Directed graph edge between two entities."""
    source_id: str
    target_id: str
    type: str  # e.g. TOUCHED, DECIDED, WORKS_AT, LOCATED_IN
    properties: Dict[str, Any] = field(default_factory=dict)
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "type": self.type,
            "properties": dict(self.properties),
            "weight": self.weight,
        }


@dataclass(frozen=True)
class MemoryEntry:
    """Unified entry across short-term, long-term, and reasoning memory."""
    entry_id: str
    content: str
    entry_type: str = "long_term"  # short_term, long_term, reasoning
    entities: List[POLEEntity] = field(default_factory=list)
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "content": self.content,
            "entry_type": self.entry_type,
            "entities": [e.to_dict() for e in self.entities],
            "timestamp": self.timestamp,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class GraphQueryResult:
    """Outcome of a graph memory traversal and hybrid search."""
    query: str
    entities: List[POLEEntity] = field(default_factory=list)
    relationships: List[Relationship] = field(default_factory=list)
    context_string: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "context_string": self.context_string,
            "latency_ms": self.latency_ms,
        }


@dataclass
class MemoryConfig:
    """Configuration for Graph-Native Memory subsystem."""
    enabled: bool = True
    provider: str = "neo4j"
    uri: str = "bolt://127.0.0.1:7687"
    user: str = "neo4j"
    database: str = "neo4j"
    default_depth: int = 2
    max_context_tokens: int = 150

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "provider": self.provider,
            "uri": self.uri,
            "user": self.user,
            "database": self.database,
            "default_depth": self.default_depth,
            "max_context_tokens": self.max_context_tokens,
        }


class BaseMemoryProvider(ABC):
    """Interface for Graph-Native Memory providers."""

    def __init__(self, name: str = "memory") -> None:
        self.name = name

    @abstractmethod
    def store(
        self,
        content: str,
        entry_type: str = "long_term",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> MemoryEntry:
        """Store a conversation turn, fact, or reflection into memory."""
        pass

    @abstractmethod
    def query(self, query: str, limit: int = 10, depth: int = 2) -> GraphQueryResult:
        """Query memory using hybrid semantic and graph traversal."""
        pass

    @abstractmethod
    def get_context(self, query: str, max_tokens: int = 150) -> str:
        """Produce formatted graph pathway context block for Context Forge Layer 4."""
        pass

    @abstractmethod
    def add_entity(self, entity: POLEEntity) -> bool:
        """Add or merge a POLE+O entity into the knowledge graph."""
        pass

    @abstractmethod
    def get_entity(self, entity_id_or_name: str) -> Optional[POLEEntity]:
        """Look up entity by id or canonical name."""
        pass

    @abstractmethod
    def add_relationship(self, rel: Relationship) -> bool:
        """Add or update an edge between two entities."""
        pass

    @abstractmethod
    def record_reasoning_step(
        self,
        step_name: str,
        touched_entities: List[str],
        tool_calls: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """Record reasoning step and create :TOUCHED audit edges to touched entities."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Inspect provider connectivity, schema indexes, and diagnostics."""
        pass

    @abstractmethod
    def get_config(self) -> MemoryConfig:
        """Return active memory configuration."""
        pass
