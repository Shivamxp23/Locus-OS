"""
SPEC §4.14 line 1470:
Provider Interface: MemoryDecayProvider
Defines configuration, abstract base provider, and default implementation for
project-specific memory decay and cold archival.
"""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.memory.cold_archiver import (
    get_cold_archive_dir,
    get_cold_archive_path,
    list_cold_archives,
    load_cold_archive,
)
from sidecar.memory.project_decay import (
    COLD_STORAGE_THRESHOLD,
    DEFAULT_HALF_LIFE,
    HALF_LIFE_DAYS,
    ProjectDecayEngine,
    ProjectNode,
    ProjectRecord,
    calculate_retention_strength,
)


@dataclass
class ProjectDecayConfig:
    """
    Configuration parameters and modular off-switch for Project Memory Decay Engine.
    """
    enabled: bool = True
    half_life_days: Dict[str, float] = field(default_factory=lambda: dict(HALF_LIFE_DAYS))
    default_half_life: float = DEFAULT_HALF_LIFE
    cold_storage_threshold: float = COLD_STORAGE_THRESHOLD
    storage_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProjectDecayConfig:
        return cls(
            enabled=bool(data.get("enabled", True)),
            half_life_days=dict(data.get("half_life_days", HALF_LIFE_DAYS)),
            default_half_life=float(data.get("default_half_life", DEFAULT_HALF_LIFE)),
            cold_storage_threshold=float(data.get("cold_storage_threshold", COLD_STORAGE_THRESHOLD)),
            storage_dir=data.get("storage_dir"),
        )


class MemoryDecayProvider(ABC):
    """
    SPEC §4.14 line 1470:
    Abstract Provider Interface: MemoryDecayProvider
    """

    def __init__(self, name: str = "default", config: Optional[ProjectDecayConfig] = None) -> None:
        self.name = name
        self.config = config or ProjectDecayConfig()

    @abstractmethod
    def calculate_retention(
        self,
        project_state: str,
        days_since_last_touch: float,
        s_0: float = 1.0,
    ) -> float:
        """Calculate exponential retention strength S(t)."""
        pass

    @abstractmethod
    def register_project(self, project: ProjectRecord) -> None:
        """Track a project with its lifecycle state and last touched timestamp."""
        pass

    @abstractmethod
    def add_project_node(self, node: ProjectNode) -> None:
        """Add a memory node linked to a project."""
        pass

    @abstractmethod
    def sweep(
        self,
        current_timestamp: Optional[float] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Perform project memory decay sweep and cold archival."""
        pass

    @abstractmethod
    def get_archive(self, project_id: str) -> Dict[str, Any]:
        """Retrieve decompressed cold archive for a project."""
        pass

    @abstractmethod
    def list_archives(self) -> List[Dict[str, Any]]:
        """List all available cold archives."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return provider health status, latency, and metrics."""
        pass


class DefaultProjectMemoryDecayProvider(MemoryDecayProvider):
    """
    Default in-process implementation of MemoryDecayProvider using ProjectDecayEngine.
    """

    def __init__(self, name: str = "default", config: Optional[ProjectDecayConfig] = None) -> None:
        super().__init__(name=name, config=config)
        self.engine = ProjectDecayEngine(
            half_life_table=self.config.half_life_days,
            cold_threshold=self.config.cold_storage_threshold,
            storage_dir=self.config.storage_dir,
        )

    def calculate_retention(
        self,
        project_state: str,
        days_since_last_touch: float,
        s_0: float = 1.0,
    ) -> float:
        return calculate_retention_strength(
            project_state=project_state,
            days_since_last_touch=days_since_last_touch,
            s_0=s_0,
            half_life_table=self.config.half_life_days,
        )

    def register_project(self, project: ProjectRecord) -> None:
        self.engine.register_project(project)

    def add_project_node(self, node: ProjectNode) -> None:
        self.engine.add_node(node)

    def sweep(
        self,
        current_timestamp: Optional[float] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        return self.engine.sweep_project_memories(
            current_timestamp=current_timestamp,
            dry_run=dry_run,
        )

    def get_archive(self, project_id: str) -> Dict[str, Any]:
        return load_cold_archive(project_id, override_dir=self.config.storage_dir)

    def list_archives(self) -> List[Dict[str, Any]]:
        return list_cold_archives(override_dir=self.config.storage_dir)

    def health_check(self) -> Dict[str, Any]:
        start = time.perf_counter()
        try:
            # Check calculation logic
            test_val = self.calculate_retention("ACTIVE", 10.0)
            # Check archive dir writable
            archive_dir = get_cold_archive_dir(self.config.storage_dir)
            dir_ok = archive_dir.exists() and archive_dir.is_dir()
            elapsed_ms = (time.perf_counter() - start) * 1000.0

            return {
                "status": "healthy" if dir_ok and test_val > 0 else "degraded",
                "latency_ms": round(elapsed_ms, 3),
                "archive_dir": str(archive_dir),
                "tracked_projects": len(self.engine.list_projects()),
                "tracked_nodes": len(self.engine._nodes),
            }
        except Exception as e:
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            return {
                "status": "unhealthy",
                "latency_ms": round(elapsed_ms, 3),
                "error": str(e),
            }


# Aliases
BaseMemoryDecayProvider = MemoryDecayProvider
ProjectMemoryDecayProvider = DefaultProjectMemoryDecayProvider
