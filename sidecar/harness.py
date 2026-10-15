"""sidecar/harness.py - Coding Harness Delegation & Isolated Worktree Engine.

Implements Spec §3.7, §11.5, Security Rule S-3, and Errata Decision D-5:
- Delegates coding subtasks to external subprocess agents (Pi, Claude Code, OpenCode, Mock).
- Executes tasks inside isolated temporary git worktrees, preventing contamination
  of the primary workspace or vault.
- Strictly enforces Security Rule S-3: `--dangerously-skip-permissions` is banned.
- Ensures scratch worktrees and temporary branches are safely cleaned up post-execution.
- Returns structured execution results: exit code, git diff, modified files, logs, duration.
- Modular switch: locus.harness.enabled (True | False).
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
import logging
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Dict, List, Optional, Protocol, Sequence, runtime_checkable
import uuid

logger = logging.getLogger("sidecar.harness")

FORBIDDEN_FLAG = "--dangerously-skip-permissions"
REPO_ROOT = Path(__file__).resolve().parent.parent


@dataclass
class CodingTask:
    """Specification of a coding subtask to be delegated."""

    task_id: str = field(default_factory=lambda: f"task-{uuid.uuid4().hex[:8]}")
    prompt: str = ""
    target_harness: str = "mock"  # "pi", "claude", "opencode", "mock"
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)
    branch_prefix: str = "scratch/delegate"
    timeout_seconds: int = 120
    preserve_worktree: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationResult:
    """Structured result returned from delegated coding execution."""

    task_id: str
    harness: str
    worktree_path: str
    exit_code: int
    diff: str = ""
    modified_files: list[str] = field(default_factory=list)
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
    cleaned_up: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0


@runtime_checkable
class HarnessProvider(Protocol):
    """Protocol for coding harness delegation providers."""

    def is_available(self, harness_name: str) -> bool:
        """Check if target CLI harness is installed on PATH."""
        return False

    def delegate(self, task: CodingTask) -> DelegationResult:
        """Execute a coding task in an isolated scratch worktree."""
        return DelegationResult(
            task_id="",
            harness="",
            worktree_path="",
            exit_code=1,
            cleaned_up=True,
        )


def validate_security_flags(args: Sequence[str]) -> None:
    """Enforce Security Law S-3: forbid dangerous permission bypass flags."""
    for arg in args:
        if FORBIDDEN_FLAG in arg:
            raise ValueError(
                f"Security Law S-3 Violation: {FORBIDDEN_FLAG} is strictly prohibited "
                "across all Locus harness invocations."
            )


class ScratchWorktreeManager:
    """Manages ephemeral git worktrees for isolated task execution."""

    @staticmethod
    def create(repo_root: Path, branch_name: str, target_dir: Path) -> Path:
        """Create a detached or branched worktree from HEAD."""
        repo_root = Path(repo_root).resolve()
        target_dir = Path(target_dir).resolve()
        target_dir.parent.mkdir(parents=True, exist_ok=True)

        cmd = ["git", "worktree", "add", "-b", branch_name, str(target_dir), "HEAD"]
        proc = subprocess.run(
            cmd,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Failed to create git worktree at {target_dir}: {proc.stderr}")
        return target_dir

    @staticmethod
    def cleanup(repo_root: Path, branch_name: str, target_dir: Path) -> bool:
        """Safely remove a scratch worktree and its branch."""
        repo_root = Path(repo_root).resolve()
        target_dir = Path(target_dir).resolve()

        if not target_dir.exists():
            return True

        # Remove git worktree
        subprocess.run(
            ["git", "worktree", "remove", str(target_dir), "--force"],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )

        # Delete scratch branch
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
        )

        # Ensure directory is gone
        if target_dir.exists():
            shutil.rmtree(str(target_dir), ignore_errors=True)

        return not target_dir.exists()


class HarnessManager:
    """Universal Harness Provider coordinating delegation and worktrees."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def is_available(self, harness_name: str) -> bool:
        """Check if named harness CLI exists on system PATH."""
        h = harness_name.lower()
        if h == "mock":
            return True
        elif h == "pi":
            return shutil.which("node") is not None
        elif h in ("claude", "claude-code"):
            return shutil.which("claude") is not None or shutil.which("claude.cmd") is not None
        elif h == "opencode":
            return shutil.which("opencode") is not None
        return False

    def build_harness_command(self, harness: str, prompt: str) -> list[str]:
        """Construct CLI command for target harness, strictly enforcing S-3."""
        h = harness.lower()
        if h == "claude" or h == "claude-code":
            cmd = ["claude", "-p", prompt]
        elif h == "opencode":
            cmd = ["opencode", prompt]
        elif h == "pi":
            node_bin = shutil.which("node") or "node"
            cli_path = REPO_ROOT / "packages" / "coding-agent" / "dist" / "cli.js"
            cmd = [node_bin, str(cli_path), "--approve", "--no-context-files", "-p", prompt]
        elif h == "mock":
            # In mock mode, execute Python command that simulates an edit
            cmd = [
                shutil.which("python") or "py",
                "-c",
                "import sys; from pathlib import Path; (Path('delegated_output.txt')).write_text('Mock harness executed\\n'); print('Mock completed successfully')",
            ]
        else:
            raise ValueError(f"Unknown coding harness: {harness}")

        validate_security_flags(cmd)
        return cmd

    def delegate(self, task: CodingTask) -> DelegationResult:
        """Run coding task in a scratch git worktree with full telemetry."""
        if not self.enabled:
            return DelegationResult(
                task_id=task.task_id,
                harness=task.target_harness,
                worktree_path="",
                exit_code=1,
                stderr="Harness delegation is disabled by locus.harness.enabled configuration.",
                cleaned_up=True,
            )

        start_time = time.time()
        scratch_id = f"wt-{uuid.uuid4().hex[:8]}"
        scratch_branch = f"{task.branch_prefix}/{scratch_id}"
        worktree_dir = (task.repo_root.parent / f"locus-scratch-{scratch_id}").resolve()

        # Step 1: Create scratch worktree
        ScratchWorktreeManager.create(task.repo_root, scratch_branch, worktree_dir)

        stdout_buf, stderr_buf, exit_code = "", "", 0
        diff_output, modified_files = "", []

        try:
            # Step 2: Build command & validate S-3
            cmd = self.build_harness_command(task.target_harness, task.prompt)

            # Step 3: Execute in scratch worktree
            proc = subprocess.run(
                cmd,
                cwd=str(worktree_dir),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=task.timeout_seconds,
            )
            stdout_buf = proc.stdout or ""
            stderr_buf = proc.stderr or ""
            exit_code = proc.returncode

            # Step 4: Extract git diff and modified files
            diff_proc = subprocess.run(
                ["git", "diff", "HEAD"],
                cwd=str(worktree_dir),
                capture_output=True,
                text=True,
            )
            diff_output = diff_proc.stdout or ""

            names_proc = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(worktree_dir),
                capture_output=True,
                text=True,
            )
            if names_proc.stdout:
                for line in names_proc.stdout.splitlines():
                    if len(line) > 3:
                        modified_files.append(line[3:].strip())

        except Exception as exc:
            exit_code = 1
            stderr_buf += f"\nDelegation error: {exc}"
        finally:
            # Step 5: Clean up worktree unless explicitly preserved
            cleaned = False
            if not task.preserve_worktree:
                cleaned = ScratchWorktreeManager.cleanup(task.repo_root, scratch_branch, worktree_dir)

        duration_ms = (time.time() - start_time) * 1000.0

        return DelegationResult(
            task_id=task.task_id,
            harness=task.target_harness,
            worktree_path=str(worktree_dir),
            exit_code=exit_code,
            diff=diff_output,
            modified_files=modified_files,
            stdout=stdout_buf,
            stderr=stderr_buf,
            duration_ms=duration_ms,
            cleaned_up=cleaned,
        )


def main() -> int:
    """CLI demo runner for Sprint Review verification."""
    parser = argparse.ArgumentParser(description="Locus OS Coding Harness Delegation")
    parser.add_argument("--harness", type=str, default="mock", help="Target harness (mock, pi, claude, opencode)")
    parser.add_argument("--prompt", type=str, default="Fix issue #42", help="Task description")
    args = parser.parse_args()

    manager = HarnessManager()
    task = CodingTask(
        prompt=args.prompt,
        target_harness=args.harness,
    )
    print(f"Delegating task to {task.target_harness} in scratch worktree...")
    res = manager.delegate(task)

    print("=" * 60)
    print("DELEGATION EXECUTION SUMMARY (Spec §3.7 / §11.5 / S-3 / D-5)")
    print("=" * 60)
    print(f"Task ID:         {res.task_id}")
    print(f"Harness:         {res.harness}")
    print(f"Exit Code:       {res.exit_code} ({'SUCCESS' if res.ok else 'FAIL'})")
    print(f"Duration:        {res.duration_ms:.1f}ms")
    print(f"Cleaned Up:      {res.cleaned_up}")
    print(f"Files Modified:  {res.modified_files}")
    if res.diff:
        print(f"Diff lines:      {len(res.diff.splitlines())}")
    print("=" * 60)
    return 0 if res.ok else 1


if __name__ == "__main__":
    import sys

    sys.exit(main())
