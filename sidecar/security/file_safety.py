"""
SPEC §13.2 lines 3141-3165:
File Safety (F-0107 / US-69).

Implements:
1. cwd_jail: confine file operations to project root + allowed paths (path traversal prevention)
2. BLOCKED_PATTERNS: layered safety blocking sensitive files (.git, .env, private keys, system files)
3. file_state tracking: track file modifications across tool calls
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import datetime
import hashlib
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

# Patterns blocked for destructive or unauthorized access
DEFAULT_BLOCKED_PATTERNS = [
    # Git database protection
    re.compile(r"(^|[/\\])\.git([/\\]|$)", re.IGNORECASE),
    # Credentials and secrets
    re.compile(r"(^|[/\\])\.env(\.[a-zA-Z0-9_\-]+)?$", re.IGNORECASE),
    re.compile(r"(^|[/\\])id_(rsa|dsa|ecdsa|ed25519)(\.pub)?$", re.IGNORECASE),
    re.compile(r"\.(pem|key|pfx|p12|pkcs12)$", re.IGNORECASE),
    # Unix system files
    re.compile(r"^/(etc|var/run|proc|sys)/", re.IGNORECASE),
    re.compile(r"(^|[/\\])(shadow|sudoers|master\.passwd)$", re.IGNORECASE),
    # Windows system hives & system32
    re.compile(r"^[A-Za-z]:[/\\]Windows[/\\](System32|SysWOW64)", re.IGNORECASE),
    re.compile(r"(^|[/\\])(SAM|SYSTEM|SECURITY)$", re.IGNORECASE),
]


@dataclass
class PathValidationDecision:
    """SPEC §13.2: Path safety verdict."""
    allowed: bool
    path: str
    resolved_path: str
    operation: str  # read | write | create | delete
    reason: Optional[str] = None
    violation_type: Optional[str] = None  # path_traversal | blocked_pattern | outside_jail | None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class CwdJail:
    """
    SPEC §13.2: cwd_jail.
    Confines file operations to project root + explicitly allowed paths.
    """

    def __init__(self, root: Optional[Path] = None, allowed_paths: Optional[List[Path]] = None):
        self.root = (root or Path.cwd()).resolve()
        self.allowed_paths = [self.root]
        if allowed_paths:
            for p in allowed_paths:
                self.allowed_paths.append(p.resolve())

    def is_within_jail(self, target: Path) -> bool:
        """Check if resolved path is within project root or allowed paths."""
        try:
            resolved = target.resolve()
        except Exception:
            return False

        for allowed in self.allowed_paths:
            try:
                # If target is inside allowed directory or is the allowed path
                resolved.relative_to(allowed)
                return True
            except ValueError:
                continue
        return False

    def validate(self, path_str: str, operation: str = "read") -> PathValidationDecision:
        """
        Validate path against path traversal, jail boundaries, and blocked patterns.
        """
        if not path_str or not path_str.strip():
            return PathValidationDecision(
                allowed=False,
                path=path_str,
                resolved_path="",
                operation=operation,
                reason="Empty path provided",
                violation_type="invalid_path",
            )

        # Check for null-byte injection
        if "\0" in path_str:
            return PathValidationDecision(
                allowed=False,
                path=path_str,
                resolved_path="",
                operation=operation,
                reason="Null byte detected in path",
                violation_type="path_traversal",
            )

        # Normalize relative to project root if relative
        raw_path = Path(path_str)
        if not raw_path.is_absolute():
            target_path = (self.root / raw_path).resolve()
        else:
            target_path = raw_path.resolve()

        resolved_str = str(target_path)

        # 1. Path traversal / Jail boundary check
        if not self.is_within_jail(target_path):
            return PathValidationDecision(
                allowed=False,
                path=path_str,
                resolved_path=resolved_str,
                operation=operation,
                reason=f"Path '{resolved_str}' escapes project jail '{self.root}'",
                violation_type="outside_jail",
            )

        # 2. Blocked patterns check
        norm_forward = resolved_str.replace("\\", "/")
        for pat in DEFAULT_BLOCKED_PATTERNS:
            if pat.search(norm_forward) or pat.search(resolved_str):
                # For read operations on .env or git status, we differentiate:
                # .git is strictly protected against write/delete
                # private keys are blocked for read/write/delete
                is_git = bool(re.search(r"(^|[/\\])\.git([/\\]|$)", norm_forward))
                if is_git and operation == "read":
                    # Allow reading git metadata if inside jail, but block writes
                    continue

                return PathValidationDecision(
                    allowed=False,
                    path=path_str,
                    resolved_path=resolved_str,
                    operation=operation,
                    reason=f"Operation '{operation}' blocked by security rule for pattern '{pat.pattern}'",
                    violation_type="blocked_pattern",
                )

        return PathValidationDecision(
            allowed=True,
            path=path_str,
            resolved_path=resolved_str,
            operation=operation,
            reason="Path is within jail and passes security patterns",
            violation_type=None,
        )


@dataclass
class FileStateRecord:
    """SPEC §13.2: Record of a tracked file modification."""
    path: str
    operation: str  # create | modify | delete | read
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> FileStateRecord:
        return cls(
            path=data["path"],
            operation=data["operation"],
            timestamp=data.get(
                "timestamp",
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
            size_bytes=data.get("size_bytes"),
            sha256=data.get("sha256"),
        )


class FileStateTracker:
    """
    SPEC §13.2: file_state tracking.
    Tracks file modifications across tool calls in a session.
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or (Path.home() / ".locus" / "security")
        self.storage_file = self.storage_dir / "file_state.json"
        self._history: List[FileStateRecord] = []
        self._load()

    def _load(self) -> None:
        if not self.storage_file.exists():
            return
        try:
            with open(self.storage_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._history = [FileStateRecord.from_dict(d) for d in data]
        except Exception as e:
            logger.warning("Failed to load file state history: %s", e)

    def _persist(self) -> None:
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
            with open(self.storage_file, "w", encoding="utf-8") as f:
                json.dump([r.to_dict() for r in self._history[-100:]], f, indent=2)
        except Exception as e:
            logger.error("Failed to persist file state history: %s", e)

    def record(
        self,
        path: str,
        operation: str,
        content: Optional[bytes] = None,
    ) -> FileStateRecord:
        """Record file state change."""
        size_bytes = None
        digest = None

        target = Path(path)
        if content is not None:
            size_bytes = len(content)
            digest = hashlib.sha256(content).hexdigest()
        elif target.is_file():
            try:
                data = target.read_bytes()
                size_bytes = len(data)
                digest = hashlib.sha256(data).hexdigest()
            except Exception:
                pass

        record = FileStateRecord(
            path=str(path),
            operation=operation,
            size_bytes=size_bytes,
            sha256=digest,
        )
        self._history.append(record)
        self._persist()
        return record

    def get_history(self, limit: int = 50) -> List[FileStateRecord]:
        """Return history of file modifications."""
        return list(reversed(self._history[-limit:]))
