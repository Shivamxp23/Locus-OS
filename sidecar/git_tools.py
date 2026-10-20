"""
SPEC §3.7a / F-0099: Git Tools Provider Implementation.
Provides programmatic Git operations (status, diff, commit, log) with parameter validation,
error containment, and modular off-switch.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.providers.git_tools import (
    BaseGitToolsProvider,
    GitCommitResult,
    GitDiffResult,
    GitLogEntry,
    GitStatusResult,
)

logger = logging.getLogger(__name__)


class GitToolsProvider(BaseGitToolsProvider):
    """
    Standard provider implementing programmatic Git operations.
    Supports repository status inspection, diff extraction, commit generation,
    and history logging with safety checks.
    """

    def __init__(self, name: str = "default_git_tools") -> None:
        super().__init__(name=name)
        self._initialized: bool = False

    def is_enabled(self) -> bool:
        """Check whether git tools operations are enabled in configuration."""
        if config.get("locus.git_tools.enabled", True) is False:
            return False
        if config.get("locus.tools.git.enabled", True) is False:
            return False
        return True

    def initialize(self) -> None:
        """Initialize provider lifecycle and verify git availability."""
        self._initialized = True

    def health_check(self) -> Dict[str, Any]:
        """Perform health check and return provider status, binary presence, and latency."""
        start = time.time()
        git_bin = shutil.which("git")
        latency = (time.time() - start) * 1000.0
        enabled = self.is_enabled()
        return {
            "status": "healthy" if (enabled and git_bin) else ("disabled" if not enabled else "degraded"),
            "latency_ms": round(latency, 2),
            "provider": self.name,
            "initialized": self._initialized,
            "git_binary": git_bin,
        }

    def shutdown(self) -> None:
        """Gracefully release provider resources."""
        self._initialized = False

    def _resolve_root(self, repo_path: Optional[str] = None) -> Path:
        """Resolve and validate target repository path."""
        root = Path(repo_path).resolve() if repo_path else Path.cwd().resolve()
        if not root.exists() or not root.is_dir():
            raise ValueError(f"Repository path does not exist: {root}")
        return root

    def _run_git(self, args: List[str], cwd: Path, timeout: int = 30) -> subprocess.CompletedProcess[str]:
        """Run git command subprocess with safety timeout."""
        return subprocess.run(
            ["git", *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )

    def get_status(self, repo_path: Optional[str] = None) -> GitStatusResult:
        """Query working tree status, branch, staged/unstaged changes."""
        if not self.is_enabled():
            raise RuntimeError("git_tools_disabled")

        root = self._resolve_root(repo_path)
        proc = self._run_git(["status", "--porcelain=v1", "-b"], cwd=root)
        if proc.returncode != 0:
            raise RuntimeError(f"git status failed: {proc.stderr.strip()}")

        lines = proc.stdout.splitlines()
        branch = "unknown"
        staged: List[str] = []
        unstaged: List[str] = []
        untracked: List[str] = []

        if lines and lines[0].startswith("## "):
            branch_info = lines[0][3:].split("...")[0].strip()
            branch = branch_info.replace("HEAD (no branch)", "DETACHED")
            lines = lines[1:]

        for line in lines:
            if not line or len(line) < 3:
                continue
            index_status = line[0]
            worktree_status = line[1]
            file_name = line[3:].strip()
            if " -> " in file_name:
                file_name = file_name.split(" -> ")[-1].strip()

            if index_status == "?" and worktree_status == "?":
                untracked.append(file_name)
            else:
                if index_status not in (" ", "?"):
                    staged.append(file_name)
                if worktree_status not in (" ", "?"):
                    unstaged.append(file_name)

        # Retrieve current head commit hash
        rev_proc = self._run_git(["rev-parse", "HEAD"], cwd=root)
        head_commit = rev_proc.stdout.strip() if rev_proc.returncode == 0 else None

        clean = (len(staged) == 0 and len(unstaged) == 0 and len(untracked) == 0)

        return GitStatusResult(
            branch=branch,
            clean=clean,
            staged=staged,
            unstaged=unstaged,
            untracked=untracked,
            head_commit=head_commit,
        )

    def get_diff(
        self,
        repo_path: Optional[str] = None,
        staged: bool = False,
        path: Optional[str] = None,
    ) -> GitDiffResult:
        """Retrieve git diff for working tree or staged changes."""
        if not self.is_enabled():
            raise RuntimeError("git_tools_disabled")

        root = self._resolve_root(repo_path)
        cmd = ["diff"]
        if staged:
            cmd.append("--cached")
        if path:
            cmd.extend(["--", path])

        diff_proc = self._run_git(cmd, cwd=root)
        diff_text = diff_proc.stdout

        # Numstat for metrics
        stat_cmd = ["diff", "--numstat"]
        if staged:
            stat_cmd.append("--cached")
        if path:
            stat_cmd.extend(["--", path])

        stat_proc = self._run_git(stat_cmd, cwd=root)
        files_changed: List[str] = []
        insertions = 0
        deletions = 0

        for line in stat_proc.stdout.splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                ins_str, del_str, fname = parts[0], parts[1], parts[2]
                files_changed.append(fname.strip())
                if ins_str.isdigit():
                    insertions += int(ins_str)
                if del_str.isdigit():
                    deletions += int(del_str)

        return GitDiffResult(
            diff=diff_text,
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
        )

    def create_commit(
        self,
        message: str,
        repo_path: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> GitCommitResult:
        """Create a new commit in the repository."""
        if not self.is_enabled():
            raise RuntimeError("git_tools_disabled")

        if not message or not message.strip():
            raise ValueError("Commit message cannot be empty")

        root = self._resolve_root(repo_path)

        # Stage files if specified
        if files:
            add_proc = self._run_git(["add", "--", *files], cwd=root)
            if add_proc.returncode != 0:
                return GitCommitResult(
                    success=False,
                    commit_hash=None,
                    message=message,
                    files_committed=[],
                    error=f"git add failed: {add_proc.stderr.strip()}",
                )

        commit_proc = self._run_git(["commit", "-m", message.strip()], cwd=root)
        if commit_proc.returncode != 0:
            return GitCommitResult(
                success=False,
                commit_hash=None,
                message=message,
                files_committed=[],
                error=commit_proc.stderr.strip() or commit_proc.stdout.strip(),
            )

        # Extract committed commit hash
        rev_proc = self._run_git(["rev-parse", "HEAD"], cwd=root)
        commit_hash = rev_proc.stdout.strip() if rev_proc.returncode == 0 else None

        # Extract list of files changed in commit
        names_proc = self._run_git(["diff-tree", "--no-commit-id", "--name-only", "-r", "--root", "HEAD"], cwd=root)
        committed_files = [f.strip() for f in names_proc.stdout.splitlines() if f.strip()]

        return GitCommitResult(
            success=True,
            commit_hash=commit_hash,
            message=message.strip(),
            files_committed=committed_files,
            error=None,
        )

    def get_log(
        self,
        repo_path: Optional[str] = None,
        max_count: int = 10,
    ) -> List[GitLogEntry]:
        """Query recent git commit history."""
        if not self.is_enabled():
            raise RuntimeError("git_tools_disabled")

        root = self._resolve_root(repo_path)
        log_cmd = [
            "log",
            f"-n{max(1, min(max_count, 100))}",
            "--pretty=format:%H%x00%an%x00%ad%x00%s",
        ]
        proc = self._run_git(log_cmd, cwd=root)
        if proc.returncode != 0:
            return []

        entries: List[GitLogEntry] = []
        for line in proc.stdout.splitlines():
            if not line.strip():
                continue
            parts = line.split("\x00")
            if len(parts) >= 4:
                entries.append(
                    GitLogEntry(
                        hash=parts[0].strip(),
                        author=parts[1].strip(),
                        date=parts[2].strip(),
                        message=parts[3].strip(),
                    )
                )

        return entries
