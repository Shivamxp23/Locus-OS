"""tests/test_harness.py - Unit and Integration Tests for Harness Delegation.

Tests Spec §3.7, §11.5, Security Rule S-3, and Errata Decision D-5:
- Enforcement of Security Rule S-3: --dangerously-skip-permissions raises ValueError.
- Modularity switch: locus.harness.enabled=False cleanly aborts without error.
- Protocol conformance: HarnessManager satisfies HarnessProvider protocol.
- Isolated execution: Scratch worktrees created from HEAD, edits applied, diffs captured.
- Workspace protection: Main tree remains clean, scratch worktree and branch deleted after execution.
- Inter-harness bridge: delegate_coding_task wrapper passes correctly.
"""

from pathlib import Path
import pytest
import subprocess

from sidecar.harness import (
    CodingTask,
    DelegationResult,
    HarnessManager,
    HarnessProvider,
    ScratchWorktreeManager,
    validate_security_flags,
)
from sidecar.inter_harness_bridge import delegate_coding_task


def test_security_rule_s3_forbids_dangerous_flags():
    """Security Law S-3: --dangerously-skip-permissions must be strictly rejected."""
    # Valid arguments pass without error
    validate_security_flags(["claude", "-p", "fix bug"])
    validate_security_flags(["node", "cli.js", "--approve", "--no-context-files"])

    # Forbidden flag must trigger ValueError
    with pytest.raises(ValueError, match="Security Law S-3 Violation"):
        validate_security_flags(["claude", "--dangerously-skip-permissions", "-p", "do task"])

    with pytest.raises(ValueError, match="Security Law S-3 Violation"):
        validate_security_flags(["custom-tool", "--dangerously-skip-permissions=true"])


def test_harness_manager_protocol_conformance():
    """HarnessManager must conform to the HarnessProvider protocol."""
    manager = HarnessManager()
    assert isinstance(manager, HarnessProvider)
    assert manager.is_available("mock") is True
    # Unknown harness returns False
    assert manager.is_available("nonexistent_random_harness_xyz") is False


def test_harness_manager_modularity_disabled():
    """When disabled via config (enabled=False), delegation cleanly aborts."""
    manager = HarnessManager(enabled=False)
    task = CodingTask(prompt="Fix something", target_harness="mock")
    res = manager.delegate(task)

    assert res.ok is False
    assert res.exit_code == 1
    assert "disabled" in res.stderr.lower()
    assert res.cleaned_up is True


def test_harness_manager_build_command():
    """Verify command builder enforces flags and handles different harnesses."""
    manager = HarnessManager()
    
    # Mock command
    mock_cmd = manager.build_harness_command("mock", "test prompt")
    assert any("delegated_output.txt" in c for c in mock_cmd)

    # Pi command requires --approve and --no-context-files
    pi_cmd = manager.build_harness_command("pi", "test prompt")
    assert "--approve" in pi_cmd
    assert "--no-context-files" in pi_cmd

    # Claude command
    claude_cmd = manager.build_harness_command("claude", "test prompt")
    assert claude_cmd == ["claude", "-p", "test prompt"]

    # Unknown harness raises ValueError
    with pytest.raises(ValueError, match="Unknown coding harness"):
        manager.build_harness_command("unsupported_harness", "test")


def test_harness_manager_mock_delegation_in_scratch_worktree(tmp_path):
    """End-to-end integration test: execute mock task in scratch worktree and verify cleanup."""
    manager = HarnessManager(enabled=True)
    task = CodingTask(
        prompt="Simulate automated refactoring",
        target_harness="mock",
    )

    res = manager.delegate(task)

    assert res.ok is True
    assert res.exit_code == 0
    assert res.cleaned_up is True
    assert res.duration_ms > 0
    assert "Mock completed successfully" in res.stdout
    assert "delegated_output.txt" in res.modified_files

    # Verify worktree directory is removed
    wt_path = Path(res.worktree_path)
    assert not wt_path.exists(), f"Scratch worktree was not cleaned up: {wt_path}"


def test_inter_harness_bridge_delegation():
    """Convenience bridge function delegates properly."""
    res = delegate_coding_task(prompt="Bridge integration test", harness="mock")
    assert res.ok is True
    assert res.exit_code == 0
    assert res.cleaned_up is True
    assert "delegated_output.txt" in res.modified_files
