"""
SPEC §3.7 + §11.5 / §03 line 18 / F-0020: Coding Harness Delegation.
Delegates coding tasks to external harnesses (Pi, Claude Code, OpenCode, Antigravity)
running in an isolated scratch git worktree without dangerous permissions.
"""
from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.providers.harness import (
    BaseHarnessProvider,
    DelegationResult,
    HarnessType,
    TaskBrief,
)

logger = logging.getLogger(__name__)

FORBIDDEN_FLAGS = ["--dangerously-skip-permissions"]


class HarnessProvider(BaseHarnessProvider):
    """
    Standard provider delegating coding tasks to external coding harnesses.
    Enforces worktree isolation, permission guards, and output capture.
    """

    def __init__(self, name: str = "default_harness") -> None:
        super().__init__(name=name)
        self._initialized: bool = False

    def is_enabled(self) -> bool:
        """Check whether coding harness delegation is enabled in configuration."""
        return config.get("locus.harness.enabled", True) is not False

    def initialize(self) -> None:
        """Initialize provider lifecycle."""
        self._initialized = True

    def health_check(self) -> Dict[str, Any]:
        """Perform health check returning status, latency, and available harnesses."""
        start = time.time()
        latency = (time.time() - start) * 1000.0
        enabled = self.is_enabled()

        available = [HarnessType.PI.value]
        # Probe PATH for available CLI tools
        for h, binary in [
            (HarnessType.CLAUDE.value, "claude"),
            (HarnessType.OPENCODE.value, "opencode"),
            (HarnessType.ANTIGRAVITY.value, "antigravity"),
        ]:
            if shutil.which(binary):
                available.append(h)

        return {
            "status": "healthy" if enabled else "disabled",
            "latency_ms": round(latency, 2),
            "provider": self.name,
            "initialized": self._initialized,
            "available_harnesses": available,
        }

    def shutdown(self) -> None:
        """Gracefully release provider resources."""
        self._initialized = False

    def select_harness(self, brief: TaskBrief) -> HarnessType:
        """
        Select harness based on task complexity and requirements:
        - high complexity -> Antigravity (IDE-native, complex multi-file edits)
        - requires autonomous -> Claude Code (multi-step coding)
        - quick fix -> OpenCode (lightweight, fast)
        - fallback -> Pi
        """
        if brief.harness_override:
            return brief.harness_override

        if brief.complexity.lower() == "high":
            return HarnessType.ANTIGRAVITY
        elif brief.requires_autonomous:
            return HarnessType.CLAUDE
        elif brief.is_quick_fix or brief.complexity.lower() == "quick_fix":
            return HarnessType.OPENCODE

        return HarnessType.PI

    def format_command_args(self, harness: HarnessType, brief: TaskBrief, prompt: str) -> List[str]:
        """
        Build CLI arguments for the target harness.
        STRICT SECURITY GUARD: Rejects --dangerously-skip-permissions per 10-security.md S-3.
        """
        for flag in FORBIDDEN_FLAGS:
            for constraint in brief.constraints:
                if flag in constraint:
                    raise ValueError(f"Forbidden security flag '{flag}' detected in constraints (10-security.md S-3)")

        if harness == HarnessType.PI:
            args = ["pi", "--print", "--no-context-files", prompt]
        elif harness == HarnessType.CLAUDE:
            args = ["claude", "-p", prompt]
        elif harness == HarnessType.OPENCODE:
            args = ["opencode", prompt]
        elif harness == HarnessType.ANTIGRAVITY:
            args = ["antigravity", prompt]
        else:
            args = [str(harness.value), prompt]

        # Final verification: ensure no forbidden flags slipped in
        for arg in args:
            for flag in FORBIDDEN_FLAGS:
                if flag in arg:
                    raise ValueError(f"Forbidden security flag '{flag}' detected in args (10-security.md S-3)")

        return args

    def execute_delegation(
        self, brief: TaskBrief, repo_root: Optional[Path] = None
    ) -> DelegationResult:
        """
        Execute delegated coding task in an isolated scratch git worktree.
        Captures diff, modified files, stdout/stderr, and cleans up scratch worktree.
        """
        start_time = time.time()
        if not self.is_enabled():
            return DelegationResult(
                status="skipped",
                harness_used="",
                exit_code=1,
                diff="",
                modified_files=[],
                execution_time_seconds=0.0,
                error="harness_disabled",
            )

        root = (repo_root or Path.cwd()).resolve()
        scratch_id = f"wt-scratch-{int(time.time())}-{uuid.uuid4().hex[:6]}"
        scratch_dir = root / "tracker" / ".cache" / scratch_id
        scratch_dir.parent.mkdir(parents=True, exist_ok=True)

        # 1. Create isolated scratch worktree
        try:
            add_proc = subprocess.run(
                ["git", "worktree", "add", "--detach", str(scratch_dir), "HEAD"],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=30,
            )
            if add_proc.returncode != 0:
                return DelegationResult(
                    status="error",
                    harness_used="",
                    exit_code=add_proc.returncode,
                    diff="",
                    modified_files=[],
                    execution_time_seconds=round(time.time() - start_time, 2),
                    stderr=add_proc.stderr,
                    error=f"Failed to create scratch worktree: {add_proc.stderr}",
                )
        except Exception as ex:
            return DelegationResult(
                status="error",
                harness_used="",
                exit_code=1,
                diff="",
                modified_files=[],
                execution_time_seconds=round(time.time() - start_time, 2),
                error=f"Exception creating scratch worktree: {ex}",
            )

        # 2. Build task prompt and select harness
        harness = self.select_harness(brief)
        prompt_lines = [
            f"TASK: {brief.description}",
            f"CODEBASE: {scratch_dir}",
            f"FILES TO MODIFY: {', '.join(brief.target_files) if brief.target_files else 'Any relevant'}",
            f"CONSTRAINTS: {', '.join(brief.constraints) if brief.constraints else 'None'}",
            f"TESTS: {', '.join(brief.test_commands) if brief.test_commands else 'None'}",
        ]
        prompt = "\n".join(prompt_lines)

        try:
            cmd_args = self.format_command_args(harness, brief, prompt)
        except ValueError as ex:
            # Clean up worktree before returning security error
            self._cleanup_worktree(root, scratch_dir)
            return DelegationResult(
                status="error",
                harness_used=harness.value,
                exit_code=1,
                diff="",
                modified_files=[],
                execution_time_seconds=round(time.time() - start_time, 2),
                error=str(ex),
            )

        # 3. Execute harness subprocess
        stdout = ""
        stderr = ""
        exit_code = 0
        diff = ""
        modified_files: List[str] = []

        try:
            sub_proc = subprocess.run(
                cmd_args,
                cwd=str(scratch_dir),
                capture_output=True,
                text=True,
                timeout=brief.timeout,
            )
            exit_code = sub_proc.returncode
            stdout = sub_proc.stdout
            stderr = sub_proc.stderr

            if exit_code == 0:
                diff_proc = subprocess.run(
                    ["git", "diff", "HEAD"],
                    cwd=str(scratch_dir),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                diff = diff_proc.stdout

                names_proc = subprocess.run(
                    ["git", "diff", "--name-only", "HEAD"],
                    cwd=str(scratch_dir),
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                modified_files = [f.strip() for f in names_proc.stdout.splitlines() if f.strip()]
        except subprocess.TimeoutExpired:
            exit_code = 124
            stderr = f"Subprocess timed out after {brief.timeout} seconds"
        except Exception as ex:
            exit_code = 1
            stderr = f"Subprocess execution error: {ex}"
        finally:
            # 4. Always clean up scratch worktree
            self._cleanup_worktree(root, scratch_dir)

        duration = round(time.time() - start_time, 2)
        status = "success" if exit_code == 0 else "error"

        return DelegationResult(
            status=status,
            harness_used=harness.value,
            exit_code=exit_code,
            diff=diff,
            modified_files=modified_files,
            execution_time_seconds=duration,
            stdout=stdout,
            stderr=stderr,
            error=None if status == "success" else stderr,
        )

    def _cleanup_worktree(self, root: Path, scratch_dir: Path) -> None:
        """Remove scratch worktree cleanly."""
        try:
            subprocess.run(
                ["git", "worktree", "remove", "--force", str(scratch_dir)],
                cwd=str(root),
                capture_output=True,
                text=True,
                timeout=20,
            )
        except Exception as ex:
            logger.debug("Failed to remove worktree %s: %s", scratch_dir, ex)
        if scratch_dir.exists():
            shutil.rmtree(scratch_dir, ignore_errors=True)
