"""Shell Blocklist & File Safety Engine (§13.7).

Enforces path-level and command-level safety boundaries:
- Denies read/write access to sensitive system directories (.ssh, .aws, .gnupg, .kube, credentials).
- Intercepts destructive, unbounded, or forkbomb shell commands before execution.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple


SENSITIVE_HOME_DIRS: Set[str] = {
    ".ssh",
    ".aws",
    ".gnupg",
    ".kube",
    ".docker",
    ".azure",
    ".config/gh",
}

SENSITIVE_HOME_FILES: Set[str] = {
    ".bashrc",
    ".zshrc",
    ".profile",
    ".bash_profile",
    ".zprofile",
    ".netrc",
    ".pgpass",
    ".npmrc",
    ".pypirc",
    "id_rsa",
    "id_ed25519",
    "authorized_keys",
}

BLOCKED_COMMAND_PATTERNS: List[re.Pattern] = [
    re.compile(r"\brm\s+-[rRfF\s]*\s*(/|~|\$HOME|\*|\.)(\s|$)"),
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),  # fork bomb
    re.compile(r"\bmkfs\b"),
    re.compile(r"\bdd\s+if="),
    re.compile(r">\s*/dev/(sd[a-z]|nvme|hd[a-z])"),
    re.compile(r"\bshutdown\b|\breboot\b|\binit\s+0\b"),
]


class ShellBlocklist:
    """Enforces file path protections and shell command execution blocklists."""

    def __init__(
        self,
        home_dir: Optional[str] = None,
        custom_blocked_patterns: Optional[List[str]] = None,
    ) -> None:
        self.home_dir = os.path.abspath(home_dir or os.path.expanduser("~")).replace("\\", "/")
        self.patterns = list(BLOCKED_COMMAND_PATTERNS)
        if custom_blocked_patterns:
            for p in custom_blocked_patterns:
                self.patterns.append(re.compile(p))

    def _normalize_path(self, path: str) -> str:
        abs_p = os.path.abspath(path).replace("\\", "/")
        return abs_p

    def is_read_blocked(self, path: str) -> bool:
        norm = self._normalize_path(path)
        base = os.path.basename(norm).lower()

        # Check sensitive file names
        if base in SENSITIVE_HOME_FILES:
            return True

        # Check sensitive directory containment
        for sdir in SENSITIVE_HOME_DIRS:
            target_dir = f"{self.home_dir}/{sdir}"
            if norm == target_dir or norm.startswith(f"{target_dir}/"):
                return True
            if f"/{sdir}/" in norm or norm.endswith(f"/{sdir}"):
                return True

        return False

    def is_write_denied(self, path: str) -> bool:
        # Any read-blocked path is strictly write-denied
        if self.is_read_blocked(path):
            return True

        norm = self._normalize_path(path)
        # Block writing directly into system roots
        if norm in ["/", "C:", "C:/", "/etc", "/usr", "/bin", "/System"]:
            return True

        return False

    def is_command_blocked(self, command: str) -> bool:
        cmd_clean = command.strip()
        for pat in self.patterns:
            if pat.search(cmd_clean):
                return True
        return False

    def evaluate_command(self, command: str) -> Dict[str, Any]:
        blocked = self.is_command_blocked(command)
        return {
            "command": command,
            "allowed": not blocked,
            "reason": "Destructive shell command pattern detected" if blocked else "ok",
        }
