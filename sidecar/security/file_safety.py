"""sidecar/security/file_safety.py - Path Safety and Access Policy Engine.

Implements Spec §13.2:
- Path traversal attack prevention (.., encoded traversals, null bytes).
- Sensitive path blocklist (.ssh, .aws, /etc/shadow, system32, credentials).
- Workspace containment enforcement.
- Read-only path enforcement (e.g. upstream packages/ is strictly READ-ONLY).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


@dataclass
class PathSafetyResult:
    is_safe: bool
    resolved_path: Optional[str]
    violation_reason: Optional[str] = None


class FileSafetyPolicy:
    """Enforces file system boundaries and prevents unauthorized path access."""

    BLOCKED_PATTERNS = [
        ".ssh", ".aws", ".gnupg", "/etc/shadow", "/etc/passwd",
        "windows/system32", "id_rsa", "id_ed25519"
    ]

    READ_ONLY_PREFIXES = [
        "packages",
        "packages/",
    ]

    def __init__(self, allowed_roots: Optional[list[str | Path]] = None) -> None:
        self.allowed_roots = [
            Path(r).resolve() for r in (allowed_roots or [Path.cwd()])
        ]

    def check_path_access(self, file_path: str, is_write: bool = False) -> PathSafetyResult:
        # Check null byte or raw traversal tricks
        if "\0" in file_path or "%2e%2e" in file_path.lower():
            return PathSafetyResult(
                is_safe=False,
                resolved_path=None,
                violation_reason="Path contains invalid characters or encoded traversal sequence.",
            )

        norm_path = os.path.normpath(file_path).replace("\\", "/").lower()

        # Sensitive blocklist
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in norm_path:
                return PathSafetyResult(
                    is_safe=False,
                    resolved_path=None,
                    violation_reason=f"Access to sensitive path containing '{pattern}' is blocked.",
                )

        # Read-only check
        if is_write:
            clean_rel = file_path.replace("\\", "/").lstrip("/")
            for ro in self.READ_ONLY_PREFIXES:
                if clean_rel == ro or clean_rel.startswith(ro.rstrip("/") + "/"):
                    return PathSafetyResult(
                        is_safe=False,
                        resolved_path=None,
                        violation_reason=f"Path '{file_path}' is protected by read-only policy.",
                    )

        # Containment check if allowed_roots specified
        try:
            resolved = Path(file_path).resolve()
            # If absolute, verify it falls within at least one allowed root
            if self.allowed_roots:
                in_root = any(
                    resolved == root or root in resolved.parents
                    for root in self.allowed_roots
                )
                if not in_root and resolved.is_absolute():
                    # If completely outside allowed roots
                    return PathSafetyResult(
                        is_safe=False,
                        resolved_path=str(resolved),
                        violation_reason=f"Path '{resolved}' is outside allowed workspace boundaries.",
                    )
            return PathSafetyResult(is_safe=True, resolved_path=str(resolved))
        except Exception as ex:
            return PathSafetyResult(
                is_safe=False,
                resolved_path=None,
                violation_reason=f"Failed to resolve path: {ex}",
            )
