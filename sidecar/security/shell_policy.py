"""
SPEC §13.7 lines 3374-3437:
Shell Blocklist and Command Policy Engine (F-0040 / US-72).

Implements:
1. SENSITIVE_HOME_DIRS and SENSITIVE_HOME_FILES protection:
   Blocks unauthorized inspection or modification of sensitive user configurations (.ssh, .aws, .gnupg, .kube, .bashrc).
2. BLOCKED_SHELL_PATTERNS:
   Detects destructive commands (rm -rf /, rm -rf ~), fork bombs (:(){ :|:& };:), pipe-to-shell (curl | sh),
   unsafe permissions (chmod -R 777), and dangerous privilege escalations (sudo rm, sudo chmod).
3. check_shell_command evaluation engine.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Union

logger = logging.getLogger(__name__)

# Sensitive directories within user home directory
SENSITIVE_HOME_DIRS = [
    ".ssh",
    ".aws",
    ".gnupg",
    ".kube",
    ".docker",
    ".azure",
    ".config/gh",
]

# Sensitive configuration and credential files
SENSITIVE_HOME_FILES = [
    ".ssh/authorized_keys",
    ".ssh/id_rsa",
    ".ssh/id_ed25519",
    ".ssh/config",
    ".bashrc",
    ".zshrc",
    ".profile",
    ".bash_profile",
    ".zprofile",
    ".netrc",
    ".pgpass",
    ".npmrc",
    ".pypirc",
]

# Destructive and dangerous shell patterns
DEFAULT_BLOCKED_PATTERNS: List[Dict[str, Union[str, re.Pattern]]] = [
    {
        "type": "destructive_command",
        "description": "Destructive root or home recursive delete",
        "pattern": re.compile(
            r"\brm\s+.*(-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*|-r\s+-f|-f\s+-r)\s+([/~]|\$HOME|\$\{HOME\}|/\*)($|\s|[/\\])",
            re.IGNORECASE,
        ),
    },
    {
        "type": "fork_bomb",
        "description": "Bash fork bomb denial of service",
        "pattern": re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:", re.IGNORECASE),
    },
    {
        "type": "unsafe_permissions",
        "description": "Unsafe global open permissions (chmod -R 777)",
        "pattern": re.compile(r"\bchmod\s+(-[a-zA-Z]*R[a-zA-Z]*\s+)?(777|a\+rwx)\b", re.IGNORECASE),
    },
    {
        "type": "pipe_to_shell",
        "description": "Unsigned remote pipe to shell execution",
        "pattern": re.compile(r"\b(curl|wget)\s+[^|]+\|\s*(sh|bash|zsh|python|perl)\b", re.IGNORECASE),
    },
    {
        "type": "privilege_escalation",
        "description": "Dangerous privilege escalation command",
        "pattern": re.compile(r"\bsudo\s+(rm|chmod|chown|dd|mkfs)\b", re.IGNORECASE),
    },
    {
        "type": "filesystem_format",
        "description": "Destructive raw disk or filesystem format",
        "pattern": re.compile(r"\b(mkfs(\.[a-zA-Z0-9]+)?|dd\s+if=/dev/(zero|urandom))\b", re.IGNORECASE),
    },
]


@dataclass
class ShellInspectionDecision:
    """
    SPEC §13.7: Verdict of a shell command policy inspection.
    """
    allowed: bool
    command: str
    violation_type: Optional[str] = None
    reason: Optional[str] = None
    matched_pattern: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ShellPolicyEngine:
    """
    SPEC §13.7: Shell Blocklist and sensitive file policy engine.
    """

    def __init__(
        self,
        home_dir: Optional[Path] = None,
        custom_patterns: Optional[List[str]] = None,
    ):
        self.home_dir = (home_dir or Path.home()).resolve()
        self.custom_patterns = custom_patterns or []
        self._compiled_custom: List[re.Pattern] = []
        for pat in self.custom_patterns:
            try:
                self._compiled_custom.append(re.compile(pat, re.IGNORECASE))
            except Exception as e:
                logger.warning(f"Failed to compile custom pattern {pat}: {e}")

    def is_read_blocked(self, path: Union[str, Path]) -> Optional[str]:
        """
        SPEC §13.7: FUNCTION is_read_blocked(path)
        """
        target = Path(path)
        try:
            resolved = target.resolve()
        except Exception:
            resolved = target

        for s_dir in SENSITIVE_HOME_DIRS:
            sensitive_path = (self.home_dir / s_dir).resolve()
            try:
                resolved.relative_to(sensitive_path)
                return f"Access to sensitive directory '{s_dir}' is blocked"
            except ValueError:
                continue

        for s_file in SENSITIVE_HOME_FILES:
            sensitive_file = (self.home_dir / s_file).resolve()
            if resolved == sensitive_file:
                return f"Access to sensitive file '{s_file}' is blocked"

        return None

    def is_write_denied(self, path: Union[str, Path], outside_boundary: bool = False) -> Optional[str]:
        """
        SPEC §13.7: FUNCTION is_write_denied(path)
        """
        read_err = self.is_read_blocked(path)
        if read_err:
            return read_err
        if outside_boundary:
            return "Modification outside project trust boundary is denied"
        return None

    def check_shell_command(self, command: str) -> ShellInspectionDecision:
        """
        SPEC §13.7: FUNCTION check_shell_command(command)
        """
        cmd_str = (command or "").strip()
        if not cmd_str:
            return ShellInspectionDecision(allowed=True, command=cmd_str)

        # Check default blocked patterns
        for rule in DEFAULT_BLOCKED_PATTERNS:
            pat = rule["pattern"]
            assert isinstance(pat, re.Pattern)
            if pat.search(cmd_str):
                return ShellInspectionDecision(
                    allowed=False,
                    command=cmd_str,
                    violation_type=str(rule["type"]),
                    reason=str(rule["description"]),
                    matched_pattern=pat.pattern,
                )

        # Check compiled custom patterns
        for pat in self._compiled_custom:
            if pat.search(cmd_str):
                return ShellInspectionDecision(
                    allowed=False,
                    command=cmd_str,
                    violation_type="custom_blocklist",
                    reason=f"Matched custom shell blocklist pattern: {pat.pattern}",
                    matched_pattern=pat.pattern,
                )

        # Check for direct references to sensitive home directories in command
        prefix = r"(~|\$HOME|\$\{HOME\})"
        for s_dir in SENSITIVE_HOME_DIRS:
            # Check patterns like ~/.ssh, $HOME/.ssh, /home/user/.ssh
            dir_escaped = re.escape(s_dir)
            pat_dir = re.compile(prefix + rf"[/\\]{dir_escaped}\b", re.IGNORECASE)
            if pat_dir.search(cmd_str):
                return ShellInspectionDecision(
                    allowed=False,
                    command=cmd_str,
                    violation_type="sensitive_home_dir",
                    reason=f"Command attempts to access sensitive directory: {s_dir}",
                    matched_pattern=s_dir,
                )

        # Check for direct references to sensitive home files in command
        for s_file in SENSITIVE_HOME_FILES:
            file_escaped = re.escape(s_file)
            pat_file = re.compile(prefix + rf"[/\\]{file_escaped}\b", re.IGNORECASE)
            if pat_file.search(cmd_str):
                return ShellInspectionDecision(
                    allowed=False,
                    command=cmd_str,
                    violation_type="sensitive_home_file",
                    reason=f"Command attempts to access sensitive file: {s_file}",
                    matched_pattern=s_file,
                )

        return ShellInspectionDecision(
            allowed=True,
            command=cmd_str,
        )
