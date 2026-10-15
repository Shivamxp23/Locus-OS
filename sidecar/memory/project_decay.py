"""Project-Specific Memory Decay Engine (§4.14).

Computes project-scoped exponential memory retention decay based on status half-lives:
ACTIVE (90d), PAUSED (30d), BACKLOG (14d), ARCHIVED (7d).
Automatically transitions clusters with retention strength < 0.10 to cold storage.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Canonical Half-Life Configuration (§4.14)
HALF_LIFE_DAYS: Dict[str, float] = {
    "ACTIVE": 90.0,
    "PAUSED": 30.0,
    "BACKLOG": 14.0,
    "ARCHIVED": 7.0,
}
DEFAULT_HALF_LIFE: float = 30.0
COLD_STORAGE_THRESHOLD: float = 0.10


def calculate_retention_strength(project_state: str, days_since_last_touch: float) -> float:
    """Compute exponential half-life decay: S(t) = S_0 * 2^(-t / T_1/2)."""
    if days_since_last_touch <= 0:
        return 1.0
    half_life = HALF_LIFE_DAYS.get(project_state.upper(), DEFAULT_HALF_LIFE)
    strength = 1.0 * (2.0 ** (-days_since_last_touch / half_life))
    return round(max(0.0, min(1.0, strength)), 4)


@dataclass
class ProjectMemoryCluster:
    project_id: str
    status: str = "ACTIVE"
    last_touched_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    nodes: List[Dict[str, Any]] = field(default_factory=list)
    retention_strength: float = 1.0
    is_cold_archived: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ColdArchiveRecord:
    project_id: str
    archived_at: str
    node_count: int
    cluster_snapshot: Dict[str, Any]


class ProjectDecayManager:
    """Manages project clusters, nightly decay sweeps, and cold storage transitions."""

    def __init__(self) -> None:
        self.clusters: Dict[str, ProjectMemoryCluster] = {}
        self.cold_archive: Dict[str, ColdArchiveRecord] = {}

    def register_project(
        self,
        project_id: str,
        status: str = "ACTIVE",
        initial_nodes: Optional[List[Dict[str, Any]]] = None,
        last_touched: Optional[datetime] = None,
    ) -> ProjectMemoryCluster:
        lt = (last_touched or datetime.now(timezone.utc)).isoformat()
        cluster = ProjectMemoryCluster(
            project_id=project_id,
            status=status.upper(),
            last_touched_at=lt,
            nodes=initial_nodes or [],
        )
        self.clusters[project_id] = cluster
        return cluster

    def touch_project(self, project_id: str) -> Optional[ProjectMemoryCluster]:
        cluster = self.clusters.get(project_id)
        if not cluster:
            return None
        cluster.last_touched_at = datetime.now(timezone.utc).isoformat()
        cluster.retention_strength = 1.0
        if cluster.is_cold_archived:
            cluster.is_cold_archived = False
            self.cold_archive.pop(project_id, None)
        return cluster

    def update_project_status(self, project_id: str, new_status: str) -> Optional[ProjectMemoryCluster]:
        cluster = self.clusters.get(project_id)
        if cluster:
            cluster.status = new_status.upper()
        return cluster

    def sweep_project_memories(
        self,
        current_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        now = current_time or datetime.now(timezone.utc)
        swept = 0
        newly_archived = 0

        for cluster in self.clusters.values():
            try:
                lt_dt = datetime.fromisoformat(cluster.last_touched_at)
                if lt_dt.tzinfo is None:
                    lt_dt = lt_dt.replace(tzinfo=timezone.utc)
            except Exception:
                lt_dt = now

            days_inactive = max(0.0, (now - lt_dt).total_seconds() / 86400.0)
            strength = calculate_retention_strength(cluster.status, days_inactive)
            cluster.retention_strength = strength
            swept += 1

            if strength < COLD_STORAGE_THRESHOLD and not cluster.is_cold_archived:
                cluster.is_cold_archived = True
                self.cold_archive[cluster.project_id] = ColdArchiveRecord(
                    project_id=cluster.project_id,
                    archived_at=now.isoformat(),
                    node_count=len(cluster.nodes),
                    cluster_snapshot=cluster.to_dict(),
                )
                newly_archived += 1

        return {
            "total_swept": swept,
            "newly_archived": newly_archived,
            "total_in_cold_storage": len(self.cold_archive),
        }
