"""
Unit tests for Git Tools: status, diff, commit, log operations, and modular off-switch.
SPEC §3.7a / F-0099.
"""
from __future__ import annotations

import tempfile
from pathlib import Path
import subprocess
import pytest

from sidecar import config
from sidecar.git_tools import GitToolsProvider
from sidecar.providers.git_tools import BaseGitToolsProvider


def test_base_provider_contract():
    """SPEC modularity architecture (03): GitToolsProvider must inherit from BaseGitToolsProvider."""
    provider = GitToolsProvider()
    assert isinstance(provider, BaseGitToolsProvider)
    assert provider.is_enabled() is True


def test_provider_universal_lifecycle():
    """Universal lifecycle: initialize, health_check, shutdown."""
    provider = GitToolsProvider()
    provider.initialize()
    health = provider.health_check()

    assert health["status"] in ("healthy", "degraded")
    assert health["initialized"] is True
    assert health["git_binary"] is not None

    provider.shutdown()
    assert provider._initialized is False


def test_git_status_current_repo():
    """SPEC §3.7a: git_status returns branch, clean flag, and file status lists."""
    provider = GitToolsProvider()
    status = provider.get_status()

    assert status.branch != ""
    assert isinstance(status.staged, list)
    assert isinstance(status.unstaged, list)
    assert isinstance(status.untracked, list)
    assert status.head_commit is not None
    assert len(status.head_commit) == 40


def test_git_diff_current_repo():
    """SPEC §3.7a: git_diff returns diff text and modification statistics."""
    provider = GitToolsProvider()
    diff_res = provider.get_diff(staged=False)

    assert isinstance(diff_res.diff, str)
    assert isinstance(diff_res.files_changed, list)
    assert diff_res.insertions >= 0
    assert diff_res.deletions >= 0


def test_git_commit_empty_message_raises():
    """Commit with empty or whitespace-only message raises ValueError."""
    provider = GitToolsProvider()
    with pytest.raises(ValueError) as excinfo:
        provider.create_commit(message="   ")
    assert "Commit message cannot be empty" in str(excinfo.value)


def test_git_invalid_repo_path_raises():
    """Specifying non-existent repository path raises ValueError."""
    provider = GitToolsProvider()
    with pytest.raises(ValueError) as excinfo:
        provider.get_status(repo_path="/path/that/does/not/exist/at/all/123456")
    assert "Repository path does not exist" in str(excinfo.value)


def test_git_commit_in_isolated_temp_repo():
    """SPEC §3.7a: git_commit creates a valid commit in a temporary git repository."""
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        # Initialize temp repo
        subprocess.run(["git", "init"], cwd=str(root), check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=str(root), check=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=str(root), check=True)

        # Create a file
        test_file = root / "sample.txt"
        test_file.write_text("Hello Git Tools", encoding="utf-8")

        provider = GitToolsProvider()
        status_before = provider.get_status(repo_path=str(root))
        assert "sample.txt" in status_before.untracked

        # Commit file
        res = provider.create_commit(message="Initial test commit", repo_path=str(root), files=["sample.txt"])
        assert res.success is True
        assert res.commit_hash is not None
        assert len(res.commit_hash) == 40
        assert "sample.txt" in res.files_committed

        # Verify status after commit
        status_after = provider.get_status(repo_path=str(root))
        assert status_after.clean is True
        assert status_after.head_commit == res.commit_hash


def test_git_log_current_repo():
    """SPEC §3.7a: get_log returns structured commit history entries."""
    provider = GitToolsProvider()
    entries = provider.get_log(max_count=5)

    assert len(entries) >= 1
    first = entries[0]
    assert len(first.hash) == 40
    assert first.author != ""
    assert first.date != ""
    assert first.message != ""


def test_modular_off_switch():
    """SPEC §03: Modular off-switch disables provider and returns 503/error."""
    provider = GitToolsProvider()
    config.set("locus.git_tools.enabled", False)
    try:
        assert provider.is_enabled() is False
        health = provider.health_check()
        assert health["status"] == "disabled"

        with pytest.raises(RuntimeError) as excinfo:
            provider.get_status()
        assert "git_tools_disabled" in str(excinfo.value)

        with pytest.raises(RuntimeError) as excinfo2:
            provider.get_diff()
        assert "git_tools_disabled" in str(excinfo2.value)

        with pytest.raises(RuntimeError) as excinfo3:
            provider.create_commit(message="test")
        assert "git_tools_disabled" in str(excinfo3.value)
    finally:
        config.set("locus.git_tools.enabled", True)
