"""Locus Agent Bridge — subprocess execution of agent engine with mandatory security flags.

Enforces AGENTS.md Law 7 and S-3:
- Always passes `--approve --no-context-files`
- Executes with cwd = repo root
- Captures output with timeout
- Stdin connected to DEVNULL
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

logger = logging.getLogger("sidecar.pi_bridge")

# Root directory of the repository (parent of sidecar)
REPO_ROOT = Path(__file__).resolve().parent.parent
PI_CLI_PATH = REPO_ROOT / "packages" / "coding-agent" / "dist" / "cli.js"
FORBIDDEN_FLAG = "--dangerously-skip-permissions"


@dataclass(frozen=True)
class PiTurnResult:
    """Structured result of a Pi CLI turn."""

    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def get_node_executable() -> str:
    """Resolve the Node.js executable on PATH or via environment override."""
    from sidecar.config import get_env

    override = get_env("NODE_EXECUTABLE")
    if override and shutil.which(override):
        return override
    exe = shutil.which("node") or shutil.which("node.exe")
    if exe is None:
        raise RuntimeError("Node.js executable not found on PATH. Install Node 20+ or set NODE_EXECUTABLE.")
    return exe


def run_pi_turn(
    prompt: str,
    cwd: str | Path | None = None,
    session_id: str | None = None,
    timeout: int = 300,
    extra_args: Sequence[str] | None = None,
) -> PiTurnResult:
    """Execute a single turn of Locus Agent execution engine.

    Guarantees:
    - Passes `--approve` so project extensions load headlessly
    - Passes `--no-context-files` so AGENTS.md developer rules do not leak into runtime sessions
    - Sets working directory to repo root by default
    - Disallows `--dangerously-skip-permissions`
    """
    working_dir = Path(cwd).resolve() if cwd is not None else REPO_ROOT
    node_bin = get_node_executable()
    cli_file = str(PI_CLI_PATH)

    cmd: list[str] = [
        node_bin,
        cli_file,
        "--approve",
        "--no-context-files",
    ]

    if session_id:
        cmd.extend(["--session", str(session_id)])

    if extra_args:
        for arg in extra_args:
            if FORBIDDEN_FLAG in arg:
                raise ValueError(f"Forbidden security flag detected: {FORBIDDEN_FLAG} is strictly prohibited")
            cmd.append(arg)

    cmd.extend(["-p", prompt])

    logger.info("Executing Pi turn in %s (session=%s, timeout=%ss)", working_dir, session_id, timeout)
    proc = subprocess.run(
        cmd,
        cwd=str(working_dir),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        stdin=subprocess.DEVNULL,
        shell=False,
    )

    return PiTurnResult(
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        returncode=proc.returncode,
    )
