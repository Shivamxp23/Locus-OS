"""
SPEC §13.7 lines 3374-3437:
Shell Blocklist Provider Interface and Implementation (F-0040 / US-72).

Implements BaseShellBlocklistProvider and DefaultShellBlocklistProvider with modular off-switches:
- locus.shell_blocklist.enabled
- locus.security.shell_blocklist.enabled
"""
from __future__ import annotations

from abc import ABC, abstractmethod
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sidecar.security.shell_policy import (
    DEFAULT_BLOCKED_PATTERNS,
    SENSITIVE_HOME_DIRS,
    SENSITIVE_HOME_FILES,
    ShellInspectionDecision,
    ShellPolicyEngine,
)
import sidecar.config as config

logger = logging.getLogger(__name__)


class BaseShellBlocklistProvider(ABC):
    """
    SPEC §13.7: Provider Interface: ShellBlocklistProvider.
    """

    @abstractmethod
    def is_available(self) -> bool:
        """Check if Shell Blocklist provider is enabled."""
        raise NotImplementedError

    @abstractmethod
    def check_command(self, command: str) -> Dict[str, Any]:
        """Inspect a shell command for dangerous or blocked patterns."""
        raise NotImplementedError

    @abstractmethod
    def is_read_blocked(self, path: str) -> Dict[str, Any]:
        """Check if read access to path is blocked."""
        raise NotImplementedError

    @abstractmethod
    def is_write_denied(self, path: str, outside_boundary: bool = False) -> Dict[str, Any]:
        """Check if write access to path is denied."""
        raise NotImplementedError

    @abstractmethod
    def list_blocked_patterns(self) -> List[Dict[str, Any]]:
        """List active blocked pattern rules."""
        raise NotImplementedError


class DefaultShellBlocklistProvider(BaseShellBlocklistProvider):
    """
    SPEC §13.7: Default implementation of ShellBlocklistProvider.
    Layers Locus' blocked patterns on top of Pi's built-in file safety.
    """

    def __init__(self, home_dir: Optional[Path] = None, custom_patterns: Optional[List[str]] = None):
        cfg_custom = custom_patterns or config.get("security.shell_blocklist") or config.get("locus.security.shell_blocklist") or []
        self.engine = ShellPolicyEngine(home_dir=home_dir, custom_patterns=list(cfg_custom))

    def is_available(self) -> bool:
        """
        Check modular off-switches:
        - locus.shell_blocklist.enabled
        - locus.security.shell_blocklist.enabled
        """
        v1 = config.get("locus.shell_blocklist.enabled")
        if v1 is not None and not config.is_enabled("locus.shell_blocklist.enabled"):
            return False

        v2 = config.get("locus.security.shell_blocklist.enabled")
        if v2 is not None and not config.is_enabled("locus.security.shell_blocklist.enabled"):
            return False

        return True

    def check_command(self, command: str) -> Dict[str, Any]:
        decision = self.engine.check_shell_command(command)
        return {
            "status": "ok",
            "decision": decision.to_dict(),
        }

    def is_read_blocked(self, path: str) -> Dict[str, Any]:
        reason = self.engine.is_read_blocked(path)
        return {
            "status": "ok",
            "blocked": reason is not None,
            "reason": reason,
        }

    def is_write_denied(self, path: str, outside_boundary: bool = False) -> Dict[str, Any]:
        reason = self.engine.is_write_denied(path, outside_boundary=outside_boundary)
        return {
            "status": "ok",
            "denied": reason is not None,
            "reason": reason,
        }

    def list_blocked_patterns(self) -> List[Dict[str, Any]]:
        rules: List[Dict[str, Any]] = []
        for r in DEFAULT_BLOCKED_PATTERNS:
            rules.append({
                "type": r["type"],
                "description": r["description"],
                "pattern": getattr(r["pattern"], "pattern", str(r["pattern"])),
            })
        for c in self.engine.custom_patterns:
            rules.append({
                "type": "custom_blocklist",
                "description": f"Custom pattern: {c}",
                "pattern": c,
            })
        return rules
