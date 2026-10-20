"""
SPEC §3.7a: Git Tools Provider Interface.
Declares abstract contracts for git status inspection, diff extraction,
commit authoring, and commit history log queries.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GitStatusResult:
    """Working tree and staging area state."""
    branch: str
    clean: bool
    staged: List[str] = field(default_factory=list)
    unstaged: List[str] = field(default_factory=list)
    untracked: List[str] = field(default_factory=list)
    head_commit: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "branch": self.branch,
            "clean": self.clean,
            "staged": self.staged,
            "unstaged": self.unstaged,
            "untracked": self.untracked,
            "head_commit": self.head_commit,
        }


@dataclass
class GitDiffResult:
    """Diff content and file alteration statistics."""
    diff: str
    files_changed: List[str] = field(default_factory=list)
    insertions: int = 0
    deletions: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "diff": self.diff,
            "files_changed": self.files_changed,
            "insertions": self.insertions,
            "deletions": self.deletions,
        }


@dataclass
class GitCommitResult:
    """Outcome of git commit command execution."""
    success: bool
    commit_hash: Optional[str]
    message: str
    files_committed: List[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "commit_hash": self.commit_hash,
            "message": self.message,
            "files_committed": self.files_committed,
            "error": self.error,
        }


@dataclass
class GitLogEntry:
    """Single commit historical record."""
    hash: str
    author: str
    date: str
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "hash": self.hash,
            "author": self.author,
            "date": self.date,
            "message": self.message,
        }


class BaseGitToolsProvider(ABC):
    """Abstract base provider for Git Operations."""

    def __init__(self, name: str = "git_tools") -> None:
        self.name = name

    @abstractmethod
    def is_enabled(self) -> bool:
        """Return whether git tools operations are enabled in configuration."""
        pass

    @abstractmethod
    def initialize(self) -> None:
        """Initialize provider lifecycle and verify git availability."""
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Perform health check and return provider status, binary presence, and latency."""
        pass

    @abstractmethod
    def shutdown(self) -> None:
        """Gracefully release provider resources."""
        pass

    @abstractmethod
    def get_status(self, repo_path: Optional[str] = None) -> GitStatusResult:
        """Query working tree status, branch, staged/unstaged changes."""
        pass

    @abstractmethod
    def get_diff(
        self,
        repo_path: Optional[str] = None,
        staged: bool = False,
        path: Optional[str] = None,
    ) -> GitDiffResult:
        """Retrieve git diff for working tree or staged changes."""
        pass

    @abstractmethod
    def create_commit(
        self,
        message: str,
        repo_path: Optional[str] = None,
        files: Optional[List[str]] = None,
    ) -> GitCommitResult:
        """Create a new commit in the repository."""
        pass

    @abstractmethod
    def get_log(
        self,
        repo_path: Optional[str] = None,
        max_count: int = 10,
    ) -> List[GitLogEntry]:
        """Query recent git commit history."""
        pass
