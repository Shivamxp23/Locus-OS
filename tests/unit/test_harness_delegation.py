"""
Unit tests for Coding Harness Delegation: interface, selection, command argument construction,
permission guards, scratch worktree isolation, and modular off-switch.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sidecar import config
from sidecar.harness.delegation import HarnessProvider
from sidecar.inter_harness_bridge import InterHarnessBridge
from sidecar.providers.harness import (
    BaseHarnessProvider,
    DelegationResult,
    HarnessType,
    TaskBrief,
)
from sidecar.registry import get_registry


def test_base_harness_provider_interface():
    """SPEC §03 line 18: "HarnessProvider registered behind BaseHarnessProvider interface."."""
    with pytest.raises(TypeError):
        # Base class is abstract and cannot be directly instantiated
        BaseHarnessProvider()  # type: ignore

    provider = HarnessProvider()
    assert isinstance(provider, BaseHarnessProvider)
    assert provider.is_enabled() is True


def test_harness_provider_universal_pattern():
    """SPEC §03 line 11: "initialize at start, run methods, stop shutdown, health returns status and latency."."""
    provider = HarnessProvider()
    provider.initialize()
    health = provider.health_check()

    assert health["status"] == "healthy"
    assert health["initialized"] is True
    assert "available_harnesses" in health
    assert HarnessType.PI.value in health["available_harnesses"]

    provider.shutdown()
    assert provider._initialized is False


def test_harness_selection_matrix():
    """SPEC §3.7 line 2760: "Select harness based on availability and task type (Antigravity, Claude Code, OpenCode, Pi)"."""
    provider = HarnessProvider()

    # 1. High complexity -> Antigravity
    brief_high = TaskBrief(description="Refactor core architecture", complexity="high")
    assert provider.select_harness(brief_high) == HarnessType.ANTIGRAVITY

    # 2. Autonomous multi-step -> Claude Code
    brief_auto = TaskBrief(description="Implement full feature loop", requires_autonomous=True)
    assert provider.select_harness(brief_auto) == HarnessType.CLAUDE

    # 3. Quick fix -> OpenCode
    brief_quick = TaskBrief(description="Fix typo in docstring", is_quick_fix=True)
    assert provider.select_harness(brief_quick) == HarnessType.OPENCODE

    # 4. Fallback -> Pi
    brief_default = TaskBrief(description="General workspace query")
    assert provider.select_harness(brief_default) == HarnessType.PI

    # 5. Explicit override
    brief_override = TaskBrief(description="Run custom", harness_override=HarnessType.OPENCODE)
    assert provider.select_harness(brief_override) == HarnessType.OPENCODE


def test_format_command_args_construction():
    """SPEC §3.7 line 2765: "Build CLI command arguments for selected harness."."""
    provider = HarnessProvider()
    prompt = "TASK: Fix bug in tokenizer"
    brief = TaskBrief(description="Fix bug")

    # Pi
    pi_args = provider.format_command_args(HarnessType.PI, brief, prompt)
    assert pi_args == ["pi", "--print", "--no-context-files", prompt]

    # Claude Code
    claude_args = provider.format_command_args(HarnessType.CLAUDE, brief, prompt)
    assert claude_args == ["claude", "-p", prompt]
    assert "--dangerously-skip-permissions" not in claude_args

    # OpenCode
    opencode_args = provider.format_command_args(HarnessType.OPENCODE, brief, prompt)
    assert opencode_args == ["opencode", prompt]

    # Antigravity
    anti_args = provider.format_command_args(HarnessType.ANTIGRAVITY, brief, prompt)
    assert anti_args == ["antigravity", prompt]


def test_forbidden_permission_flag_rejection():
    """SPEC §10 line 45 / S-3: "--dangerously-skip-permissions is rejected per security policy."."""
    provider = HarnessProvider()
    prompt = "TASK: Risky delegation"

    # Attempting to inject --dangerously-skip-permissions in constraints must raise ValueError
    brief_bad = TaskBrief(
        description="Exploit task",
        constraints=["--dangerously-skip-permissions", "fast mode"],
    )
    with pytest.raises(ValueError, match="Forbidden security flag"):
        provider.format_command_args(HarnessType.CLAUDE, brief_bad, prompt)


def test_execute_delegation_in_scratch_worktree(monkeypatch, tmp_path: Path):
    """SPEC §3.7 line 2785: "Execute harness as subprocess in scratch worktree and capture diffs."."""
    calls = []

    def fake_subprocess_run(cmd, *args, **kwargs):
        calls.append(cmd)
        mock = MagicMock()
        mock.returncode = 0
        if "worktree" in cmd:
            mock.stdout = "Preparing worktree..."
            mock.stderr = ""
        elif "diff" in cmd and "--name-only" in cmd:
            mock.stdout = "sidecar/parser.py\ntests/test_parser.py\n"
            mock.stderr = ""
        elif "diff" in cmd:
            mock.stdout = "+ def parse(): pass\n"
            mock.stderr = ""
        else:
            mock.stdout = "Harness completed task successfully."
            mock.stderr = ""
        return mock

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    provider = HarnessProvider()
    brief = TaskBrief(
        description="Add parser function",
        target_files=["sidecar/parser.py"],
        constraints=["Preserve existing docstrings"],
        test_commands=["pytest tests/test_parser.py"],
        complexity="normal",
    )

    res = provider.execute_delegation(brief, repo_root=tmp_path)
    assert res.status == "success"
    assert res.exit_code == 0
    assert "sidecar/parser.py" in res.modified_files
    assert "+ def parse(): pass" in res.diff
    assert "Harness completed task successfully." in res.stdout

    # Verify worktree add and remove were both called
    has_worktree_add = any("worktree" in cmd and "add" in cmd for cmd in calls)
    has_worktree_remove = any("worktree" in cmd and "remove" in cmd for cmd in calls)
    assert has_worktree_add is True
    assert has_worktree_remove is True


def test_execute_delegation_subprocess_failure(monkeypatch, tmp_path: Path):
    """SPEC §3.7 line 2800: "Return error and stderr when harness subprocess exits non-zero."."""
    def fake_subprocess_run(cmd, *args, **kwargs):
        mock = MagicMock()
        if "worktree" in cmd:
            mock.returncode = 0
            mock.stdout = "ok"
            mock.stderr = ""
        else:
            mock.returncode = 2
            mock.stdout = ""
            mock.stderr = "SyntaxError in generated code"
        return mock

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    provider = HarnessProvider()
    brief = TaskBrief(description="Failing coding task")
    res = provider.execute_delegation(brief, repo_root=tmp_path)

    assert res.status == "error"
    assert res.exit_code == 2
    assert "SyntaxError" in res.stderr
    assert res.error is not None


def test_inter_harness_bridge_integration(monkeypatch, tmp_path: Path):
    """SPEC §3.7 line 2810: "InterHarnessBridge delegates task via active provider."."""
    def fake_subprocess_run(cmd, *args, **kwargs):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "ok"
        mock.stderr = ""
        return mock

    monkeypatch.setattr(subprocess, "run", fake_subprocess_run)

    bridge = InterHarnessBridge()
    assert bridge.is_enabled() is True

    res = bridge.delegate_task(
        description="Quick fix via bridge",
        is_quick_fix=True,
        repo_root=tmp_path,
    )
    assert res.status == "success"
    assert res.harness_used == HarnessType.OPENCODE.value


def test_harness_delegation_off_switch(monkeypatch):
    """SPEC §03 line 35: "a disabled feature's provider methods report disabled status"."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if k == "locus.harness.enabled" else d)

    provider = HarnessProvider()
    assert provider.is_enabled() is False

    health = provider.health_check()
    assert health["status"] == "disabled"

    res = provider.execute_delegation(TaskBrief(description="Disabled test"))
    assert res.status == "skipped"
    assert res.error == "harness_disabled"


def test_harness_delegation_provider_swap(monkeypatch):
    """SPEC §03 line 41: "register a second fake provider under another name, set provider, assert fake is called."."""
    registry = get_registry()

    class FakeHarnessProvider(BaseHarnessProvider):
        def initialize(self): pass
        def shutdown(self): pass
        def health_check(self): return {"status": "mock_ok", "latency_ms": 0.05}
        def select_harness(self, brief): return HarnessType.PI
        def format_command_args(self, harness, brief, prompt): return ["mock", prompt]
        def execute_delegation(self, brief, repo_root=None):
            return DelegationResult(
                status="success",
                harness_used="mock_harness",
                exit_code=0,
                diff="mock diff",
                modified_files=["mock.py"],
                execution_time_seconds=0.1,
            )

    registry.register("harness", "mock_harness_provider", FakeHarnessProvider)
    monkeypatch.setattr(config, "get", lambda k, d=None: "mock_harness_provider" if k == "locus.harness.provider" else d)

    active_cls = registry.get_active_provider("harness", default_name="default_harness")
    assert active_cls is FakeHarnessProvider

    inst = active_cls()
    res = inst.execute_delegation(TaskBrief(description="Test swap"))
    assert res.harness_used == "mock_harness"
    assert res.diff == "mock diff"
