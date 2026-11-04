"""
SPEC §29.6 lines 7672-7745: Code Graph Analysis Provider (F-0069 / US-107).

Modular off-switch:
- locus.code_graph.enabled (master toggle, returns 503 when off)
- swappable provider interface BaseCodeGraphProvider
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from sidecar import config
from sidecar.codegraph.analyzer import CodeGraphAnalyzer

logger = logging.getLogger("locus.providers.codegraph")


class BaseCodeGraphProvider(ABC):
    """
    Abstract contract for Code Graph Analysis Provider.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider identifier."""

    @abstractmethod
    def is_feature_enabled(self) -> Tuple[bool, str]:
        """Check master modular off-switch."""

    @abstractmethod
    def analyze_codebase(
        self,
        project_path: str,
    ) -> Dict[str, Any]:
        """Build dependency graph from AST scanning."""

    @abstractmethod
    def scope_task_files(
        self,
        task_description: str,
        project_path: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        """Identify minimal file set and expand with transitive dependents."""

    @abstractmethod
    def get_or_build_graph(
        self,
        project_path: str,
        max_age_hours: float = 24.0,
    ) -> Dict[str, Any]:
        """Get pre-built /graphify graph if fresh, or build via AST scanner."""

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Get diagnostic status of code graph subsystem."""


class DefaultCodeGraphProvider(BaseCodeGraphProvider):
    """
    Standard implementation wrapping CodeGraphAnalyzer with configuration
    and 503 off-switch.
    """

    def __init__(
        self,
        analyzer: Optional[CodeGraphAnalyzer] = None,
        config_prefix: str = "locus.code_graph",
    ) -> None:
        self._analyzer = analyzer or CodeGraphAnalyzer()
        self._prefix = config_prefix

    @property
    def name(self) -> str:
        return "default_code_graph_provider"

    def is_feature_enabled(self) -> Tuple[bool, str]:
        """
        Check master toggle `locus.code_graph.enabled` (or fallback `locus.codegraph.enabled`).
        """
        enabled = config.get(f"{self._prefix}.enabled", None)
        if enabled is None:
            # Check alias
            enabled = config.get("locus.codegraph.enabled", True)

        if isinstance(enabled, str):
            enabled = enabled.lower() not in ("false", "0", "no", "off")
        elif not isinstance(enabled, bool):
            enabled = bool(enabled)

        if not enabled:
            return False, f"Feature {self._prefix} is disabled via configuration"
        return True, "Enabled"

    def analyze_codebase(
        self,
        project_path: str,
    ) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {"error": reason, "status_code": 503, "files": [], "edges": []}

        try:
            g = self._analyzer.build_dependency_graph(project_path)
            res = g.to_dict()
            res["status"] = "success"
            res["provider"] = self.name
            return res
        except Exception as e:
            logger.error(f"Error analyzing codebase at {project_path}: {e}")
            return {"error": str(e), "status_code": 500, "files": [], "edges": []}

    def scope_task_files(
        self,
        task_description: str,
        project_path: str,
        depth: int = 2,
    ) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {"error": reason, "status_code": 503, "seed_files": [], "expanded_files": []}

        try:
            g = self._analyzer.get_or_build_graph(project_path)
            scoped = self._analyzer.scope_task_files(task_description, g, depth=depth)
            scoped["status"] = "success"
            scoped["provider"] = self.name
            return scoped
        except Exception as e:
            logger.error(f"Error scoping task '{task_description}' in {project_path}: {e}")
            return {"error": str(e), "status_code": 500, "seed_files": [], "expanded_files": []}

    def get_or_build_graph(
        self,
        project_path: str,
        max_age_hours: float = 24.0,
    ) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {"error": reason, "status_code": 503, "files": [], "edges": []}

        try:
            g = self._analyzer.get_or_build_graph(project_path, max_age_hours=max_age_hours)
            res = g.to_dict()
            res["status"] = "success"
            res["provider"] = self.name
            return res
        except Exception as e:
            logger.error(f"Error fetching/building graph for {project_path}: {e}")
            return {"error": str(e), "status_code": 500, "files": [], "edges": []}

    def get_status(self) -> Dict[str, Any]:
        ok, reason = self.is_feature_enabled()
        if not ok:
            return {"error": reason, "status_code": 503, "enabled": False}

        return {
            "status": "online",
            "provider": self.name,
            "prefix": self._prefix,
            "enabled": True,
            "supported_extensions": sorted(list(self._analyzer.extensions)),
            "excluded_directories": sorted(list(self._analyzer.exclude)),
        }
