"""
SPEC §4.14: Project-Specific Memory Decay Engine.
Calculates exponential retention strength S(t) for project-associated knowledge graph clusters
based on lifecycle state (ACTIVE, MAINTENANCE, PAUSED, ABANDONED, ARCHIVED) per SPEC §4.14 lines 1428-1466.
"""
from __future__ import annotations

import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from sidecar.memory.cold_archiver import (
    archive_cluster_to_cold_storage,
    load_cold_archive,
)

# SPEC §4.14 lines 1429-1437: Lifecycle Half-Life Parameters & Cold Storage Threshold
HALF_LIFE_DAYS: Dict[str, float] = {
    "ACTIVE": 90.0,       # Active projects: very slow decay
    "MAINTENANCE": 45.0,  # Finished/sustaining: medium decay
    "PAUSED": 30.0,       # Temporarily halted: faster decay
    "ABANDONED": 14.0,    # Dropped projects: fast decay
    "ARCHIVED": 7.0,      # Completed & closed: rapid transition to cold storage
}

DEFAULT_HALF_LIFE: float = 30.0
COLD_STORAGE_THRESHOLD: float = 0.10  # Retention strength S(t) < 0.10 triggers cold archive
SECONDS_PER_DAY: float = 86400.0


def calculate_retention_strength(
    project_state: str,
    days_since_last_touch: float,
    s_0: float = 1.0,
    half_life_table: Optional[Dict[str, float]] = None,
) -> float:
    """
    SPEC §4.14 lines 1439-1443:
    FUNCTION calculate_retention_strength(project_state: string, days_since_last_touch: float) -> float:
        half_life = HALF_LIFE_DAYS.get(project_state, 30.0)
        // Exponential half-life decay formula: S(t) = S_0 * 2^(-t / T_1/2)
        strength = 1.0 * (2.0 ** (-days_since_last_touch / half_life))
        RETURN strength
    """
    table = half_life_table or HALF_LIFE_DAYS
    normalized_state = str(project_state).strip().upper()
    half_life = table.get(normalized_state, DEFAULT_HALF_LIFE)

    # Days inactive cannot be negative in the past
    days = max(0.0, float(days_since_last_touch))
    initial_strength = max(0.0, float(s_0))

    if half_life <= 0:
        return 0.0

    strength = initial_strength * (2.0 ** (-days / half_life))
    # Bound within [0.0, initial_strength]
    return float(max(0.0, min(initial_strength, strength)))


@dataclass
class ProjectNode:
    """A memory node linked to a project in the cognitive knowledge graph."""
    node_id: str
    project_id: str
    content: str
    relation: str = "BELONGS_TO"  # BELONGS_TO or SUBTASK_OF
    retention_strength: float = 1.0
    last_decay_sweep: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectNode:
        return cls(
            node_id=str(data.get("node_id", "")),
            project_id=str(data.get("project_id", "")),
            content=str(data.get("content", "")),
            relation=str(data.get("relation", "BELONGS_TO")),
            retention_strength=float(data.get("retention_strength", 1.0)),
            last_decay_sweep=float(data.get("last_decay_sweep", 0.0)),
            metadata=dict(data.get("metadata", {})),
        )


@dataclass
class ProjectRecord:
    """A project tracked in the Locus workspace/knowledge graph."""
    project_id: str
    name: str
    status: str = "ACTIVE"  # ACTIVE, MAINTENANCE, PAUSED, ABANDONED, ARCHIVED
    last_touched_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectRecord:
        return cls(
            project_id=str(data.get("project_id", "")),
            name=str(data.get("name", "")),
            status=str(data.get("status", "ACTIVE")).upper(),
            last_touched_at=float(data.get("last_touched_at", time.time())),
            metadata=dict(data.get("metadata", {})),
        )


class ProjectDecayEngine:
    """
    SPEC §4.14 lines 1445-1466:
    Nightly Project Decay Sweep Worker & In-Memory Graph Simulation.
    Evaluates project clusters, updates node retention strengths, and sweeps
    nodes falling below COLD_STORAGE_THRESHOLD into cold storage.
    """

    def __init__(
        self,
        half_life_table: Optional[Dict[str, float]] = None,
        cold_threshold: float = COLD_STORAGE_THRESHOLD,
        storage_dir: Optional[Path | str] = None,
    ) -> None:
        self.half_life_table = dict(half_life_table or HALF_LIFE_DAYS)
        self.cold_threshold = float(cold_threshold)
        self.storage_dir = storage_dir
        self._projects: Dict[str, ProjectRecord] = {}
        self._nodes: Dict[str, ProjectNode] = {}  # node_id -> ProjectNode

    def register_project(self, project: ProjectRecord) -> None:
        """Register or update a project record."""
        self._projects[project.project_id] = project

    def get_project(self, project_id: str) -> Optional[ProjectRecord]:
        """Retrieve a project by ID."""
        return self._projects.get(project_id)

    def list_projects(self) -> List[ProjectRecord]:
        """List all tracked projects."""
        return list(self._projects.values())

    def add_node(self, node: ProjectNode) -> None:
        """Add a memory node linked to a project."""
        self._nodes[node.node_id] = node

    def get_node(self, node_id: str) -> Optional[ProjectNode]:
        """Fetch a specific node by ID."""
        return self._nodes.get(node_id)

    def get_project_nodes(self, project_id: str) -> List[ProjectNode]:
        """Return all active memory nodes linked to a project via BELONGS_TO or SUBTASK_OF."""
        return [
            node for node in self._nodes.values()
            if node.project_id == project_id and node.relation in ("BELONGS_TO", "SUBTASK_OF")
        ]

    def remove_project_nodes(self, project_id: str) -> List[ProjectNode]:
        """Detach and delete all active memory nodes belonging to a project."""
        removed: List[ProjectNode] = []
        for nid in list(self._nodes.keys()):
            if self._nodes[nid].project_id == project_id:
                removed.append(self._nodes.pop(nid))
        return removed

    def sweep_project_memories(
        self,
        current_timestamp: Optional[float] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        SPEC §4.14 lines 1445-1466:
        NIGHTLY PROJECT DECAY SWEEP:
            projects = neo4j.query("MATCH (p:Project) RETURN p")
            FOR EACH project IN projects:
                days_inactive = (now() - project.last_touched_at).days
                strength = calculate_retention_strength(project.status, days_inactive)
                SET n.retention_strength = $strength, n.last_decay_sweep = datetime()
                IF strength < COLD_STORAGE_THRESHOLD:
                    archive_cluster_to_cold_storage(project.id)
                    DETACH DELETE n
        """
        now = time.time() if current_timestamp is None else float(current_timestamp)
        results: Dict[str, Any] = {
            "timestamp": now,
            "projects_evaluated": 0,
            "nodes_updated": 0,
            "projects_archived": [],
            "nodes_archived": 0,
            "details": {},
        }

        for project_id, project in list(self._projects.items()):
            results["projects_evaluated"] += 1
            days_inactive = max(0.0, (now - project.last_touched_at) / SECONDS_PER_DAY)
            strength = calculate_retention_strength(
                project_state=project.status,
                days_since_last_touch=days_inactive,
                half_life_table=self.half_life_table,
            )

            child_nodes = self.get_project_nodes(project_id)
            for node in child_nodes:
                if not dry_run:
                    node.retention_strength = strength
                    node.last_decay_sweep = now
                results["nodes_updated"] += 1

            project_detail: Dict[str, Any] = {
                "project_id": project_id,
                "status": project.status,
                "days_inactive": round(days_inactive, 3),
                "retention_strength": round(strength, 4),
                "active_nodes_count": len(child_nodes),
                "archived": False,
            }

            if strength < self.cold_threshold and child_nodes:
                # SPEC §4.14 lines 1459-1465: Trigger cold archive
                if not dry_run:
                    archive_path = archive_cluster_to_cold_storage(
                        project_id=project_id,
                        nodes=[n.to_dict() for n in child_nodes],
                        override_dir=self.storage_dir,
                        metadata={
                            "project_name": project.name,
                            "project_status": project.status,
                            "days_inactive": days_inactive,
                            "retention_strength": strength,
                        },
                    )
                    self.remove_project_nodes(project_id)
                    project_detail["archive_path"] = str(archive_path)

                project_detail["archived"] = True
                results["projects_archived"].append(project_id)
                results["nodes_archived"] += len(child_nodes)

            results["details"][project_id] = project_detail

        return results
