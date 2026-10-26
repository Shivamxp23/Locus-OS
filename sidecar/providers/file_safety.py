"""
SPEC §13.2 lines 3141-3165:
File Safety Provider Interface and Implementation (F-0107 / US-69).
Implements BaseFileSafetyProvider and DefaultFileSafetyProvider with modular off-switches:
- locus.file_safety.enabled
- locus.security.file_safety.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.security.file_safety import (
    CwdJail,
    FileStateRecord,
    FileStateTracker,
    PathValidationDecision,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseFileSafetyProvider(ABC):
    """
    SPEC §13.2: Provider Interface: FileSafetyProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if File Safety is enabled."""
        raise NotImplementedError

    @abstractmethod
    def validate_path(self, path: str, operation: str = "read", cwd: Optional[str] = None) -> Dict[str, Any]:
        """Validate path against jail and security rules."""
        raise NotImplementedError

    @abstractmethod
    def record_modification(self, path: str, operation: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Record file state modification."""
        raise NotImplementedError

    @abstractmethod
    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get file state modification history."""
        raise NotImplementedError


class DefaultFileSafetyProvider(BaseFileSafetyProvider):
    """
    SPEC §13.2: Default implementation of FileSafetyProvider.
    Confines operations to project root + allowed paths, checks blocked patterns, and tracks state.
    """

    def __init__(self, storage_dir: Optional[Path] = None, root_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".locus" / "security")
        self.tracker = FileStateTracker(storage_dir=self.storage_dir)
        self.root_dir = root_dir or Path.cwd()
        self.jail = CwdJail(root=self.root_dir)

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.file_safety.enabled
        - locus.security.file_safety.enabled
        """
        v1 = config.get("locus.file_safety.enabled")
        if v1 is not None and not config.is_enabled("locus.file_safety.enabled"):
            return False

        v2 = config.get("locus.security.file_safety.enabled")
        if v2 is not None and not config.is_enabled("locus.security.file_safety.enabled"):
            return False

        return True

    def validate_path(self, path: str, operation: str = "read", cwd: Optional[str] = None) -> Dict[str, Any]:
        """Validate path against jail and security rules."""
        if cwd:
            jail = CwdJail(root=Path(cwd))
        else:
            jail = self.jail

        decision = jail.validate(path_str=path, operation=operation)
        return {
            "status": "ok",
            "decision": decision.to_dict(),
        }

    def record_modification(self, path: str, operation: str, content: Optional[str] = None) -> Dict[str, Any]:
        """Record file state change."""
        bytes_data = content.encode("utf-8") if content is not None else None
        rec = self.tracker.record(path=path, operation=operation, content=bytes_data)
        return {
            "status": "ok",
            "record": rec.to_dict(),
        }

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return history of file modifications."""
        records = self.tracker.get_history(limit=limit)
        return [r.to_dict() for r in records]
