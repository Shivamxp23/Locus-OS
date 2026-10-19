"""
Locus sidecar Pi bridge.
Launches headless Pi turns through subprocess with mandatory security flags.
Enforces --approve and --no-context-files, and runs Pi with repo root as working folder.
"""
import os
import pathlib
import shutil
import subprocess
from typing import Optional, List, Dict, Any

from sidecar.config import get_env, get_environ


def get_node_executable() -> str:
    """Resolve the path to node.exe or node."""
    node_path = shutil.which("node")
    if not node_path:
        node_env = get_env("NODE_PATH")
        if node_env and os.path.exists(node_env):
            return node_env
        raise FileNotFoundError("Node.js executable not found in PATH")
    return node_path


def get_repo_root() -> pathlib.Path:
    """Return the absolute path to the Locus repository root."""
    return pathlib.Path(__file__).resolve().parent.parent


def run_pi_turn(
    prompt: str,
    extra_args: Optional[List[str]] = None,
    cwd: Optional[pathlib.Path] = None,
    timeout: Optional[float] = 120.0,
    session_id: Optional[str] = None,
    env: Optional[Dict[str, str]] = None,
    pi_executable: Optional[str] = None,
) -> subprocess.CompletedProcess:
    """
    Launch a headless Pi turn via subprocess with mandatory security flags.
    Enforces --approve and --no-context-files, and runs Pi with repo root as working folder.
    """
    repo_root = get_repo_root()
    working_dir = str(cwd) if cwd is not None else str(repo_root)

    cmd = []
    if pi_executable:
        cmd.append(pi_executable)
    else:
        node_bin = get_node_executable()
        cli_path = repo_root / "packages" / "coding-agent" / "dist" / "cli.js"
        cmd.extend([node_bin, str(cli_path)])

    # Security & headless execution flags:
    # --approve allows Pi to load project-local extensions (.pi/extensions) headless
    # --no-context-files prevents developer rules (AGENTS.md/CLAUDE.md) from leaking into runtime turns
    cmd.append("--approve")
    cmd.append("--no-context-files")

    if session_id:
        cmd.extend(["--session", session_id])

    cmd.extend(["-p", prompt])

    if extra_args:
        cmd.extend(extra_args)

    run_env = get_environ()
    if env:
        run_env.update(env)

    return subprocess.run(
        cmd,
        cwd=working_dir,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        shell=False,
        env=run_env,
    )
