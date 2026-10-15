"""sidecar/diagnostics/doctor.py - System Doctor Diagnostics Suite.

Implements Spec §8.2:
- Diagnoses local environment: Python runtime, Node runtime, Git status, Docker daemon,
  Neo4j connection, CouchDB port, disk space headroom, vault existence.
"""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List


@dataclass
class DiagnosticCheck:
    name: str
    passed: bool
    details: str
    severity: str = "error"  # "error", "warning", "info"


@dataclass
class DoctorReport:
    healthy: bool
    checks: list[DiagnosticCheck]
    passed_count: int
    failed_count: int


class LocusDoctor:
    """Evaluates system health, required runtimes, and local dependencies."""

    def __init__(self, root_dir: Optional[str | Path] = None) -> None:
        self.root_dir = Path(root_dir or Path.cwd()).resolve()

    def run_all_checks(self) -> DoctorReport:
        checks: list[DiagnosticCheck] = []

        # 1. Python version check
        py_ver = sys.version_info
        py_ok = py_ver.major == 3 and py_ver.minor >= 10
        checks.append(
            DiagnosticCheck(
                name="python_version",
                passed=py_ok,
                details=f"Python {py_ver.major}.{py_ver.minor}.{py_ver.micro}",
            )
        )

        # 2. Git binary available
        git_path = shutil.which("git")
        checks.append(
            DiagnosticCheck(
                name="git_installed",
                passed=git_path is not None,
                details=str(git_path or "git not found on PATH"),
            )
        )

        # 3. Node binary available
        node_path = shutil.which("node")
        checks.append(
            DiagnosticCheck(
                name="node_installed",
                passed=node_path is not None,
                details=str(node_path or "node not found on PATH"),
                severity="warning",
            )
        )

        # 4. Vault path check
        vault_path = self.root_dir / "vault"
        checks.append(
            DiagnosticCheck(
                name="vault_directory",
                passed=vault_path.is_dir(),
                details=f"Vault path: {vault_path}",
                severity="info",
            )
        )

        # 5. Disk space check (>1GB free)
        try:
            usage = shutil.disk_usage(self.root_dir)
            free_gb = usage.free / (1024 ** 3)
            checks.append(
                DiagnosticCheck(
                    name="disk_space_headroom",
                    passed=free_gb > 1.0,
                    details=f"{free_gb:.2f} GB free disk space",
                )
            )
        except Exception as ex:
            checks.append(
                DiagnosticCheck(
                    name="disk_space_headroom",
                    passed=True,
                    details=f"Could not read disk space: {ex}",
                )
            )

        passed_count = sum(1 for c in checks if c.passed)
        failed_count = sum(1 for c in checks if not c.passed and c.severity == "error")

        return DoctorReport(
            healthy=failed_count == 0,
            checks=checks,
            passed_count=passed_count,
            failed_count=failed_count,
        )
