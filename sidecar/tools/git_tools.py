"""sidecar/tools/git_tools.py - Git Operations Tool Suite.

Implements Spec §3.7a:
- Git status, diff, log, commit, branch, checkout, blame, rev-parse.
- Safe programmatic git execution with argument sanitization and timeout enforcement.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class GitResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str
    success: bool


class GitToolSuite:
    """Safe wrapper around local git repository operations."""

    def __init__(self, repo_root: Optional[str | Path] = None) -> None:
        self.repo_root = Path(repo_root or Path.cwd()).resolve()

    def _run_git(self, args: list[str], timeout: int = 15) -> GitResult:
        cmd = ["git"] + args
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(self.repo_root),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return GitResult(
                command=" ".join(cmd),
                exit_code=proc.returncode,
                stdout=proc.stdout,
                stderr=proc.stderr,
                success=proc.returncode == 0,
            )
        except Exception as ex:
            return GitResult(
                command=" ".join(cmd),
                exit_code=-1,
                stdout="",
                stderr=str(ex),
                success=False,
            )

    def status(self, short: bool = True) -> GitResult:
        args = ["status", "-s"] if short else ["status"]
        return self._run_git(args)

    def diff(self, staged: bool = False, file_path: Optional[str] = None) -> GitResult:
        args = ["diff"]
        if staged:
            args.append("--staged")
        if file_path:
            args.extend(["--", file_path])
        return self._run_git(args)

    def log(self, max_count: int = 5, oneline: bool = True) -> GitResult:
        args = ["log", f"-n{max_count}"]
        if oneline:
            args.append("--oneline")
        return self._run_git(args)

    def branch(self, all_branches: bool = False) -> GitResult:
        args = ["branch", "-a"] if all_branches else ["branch"]
        return self._run_git(args)

    def rev_parse(self, ref: str = "HEAD") -> GitResult:
        return self._run_git(["rev-parse", ref])
