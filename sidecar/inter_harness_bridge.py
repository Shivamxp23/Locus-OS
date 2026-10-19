"""
SPEC §3.7 + §11.5 / F-0020: Inter-Harness Bridge.
Connects Pi Agent and Locus router with external coding harnesses via HarnessProvider.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from sidecar.harness.delegation import HarnessProvider
from sidecar.providers.harness import (
    BaseHarnessProvider,
    DelegationResult,
    HarnessType,
    TaskBrief,
)
from sidecar.registry import get_registry


class InterHarnessBridge:
    """
    Bridge connecting agent sessions and API endpoints to external coding harnesses.
    """

    def __init__(self, provider: Optional[BaseHarnessProvider] = None) -> None:
        if provider:
            self._provider = provider
        else:
            registry = get_registry()
            provider_cls = registry.get_active_provider("harness", default_name="default_harness")
            if provider_cls:
                self._provider = provider_cls()
            else:
                self._provider = HarnessProvider()
        self._provider.initialize()

    def is_enabled(self) -> bool:
        """Return whether harness delegation is enabled."""
        return self._provider.is_enabled()

    def delegate_task(
        self,
        description: str,
        target_files: Optional[List[str]] = None,
        constraints: Optional[List[str]] = None,
        test_commands: Optional[List[str]] = None,
        complexity: str = "normal",
        requires_autonomous: bool = False,
        is_quick_fix: bool = False,
        harness_override: Optional[str] = None,
        repo_root: Optional[Path] = None,
    ) -> DelegationResult:
        """Construct TaskBrief and delegate task execution to the selected harness."""
        h_override = None
        if harness_override:
            try:
                h_override = HarnessType(harness_override)
            except ValueError:
                h_override = None

        brief = TaskBrief(
            description=description,
            target_files=target_files or [],
            constraints=constraints or [],
            test_commands=test_commands or [],
            complexity=complexity,
            requires_autonomous=requires_autonomous,
            is_quick_fix=is_quick_fix,
            harness_override=h_override,
        )
        return self._provider.execute_delegation(brief, repo_root=repo_root)


__all__ = [
    "BaseHarnessProvider",
    "DelegationResult",
    "HarnessProvider",
    "HarnessType",
    "InterHarnessBridge",
    "TaskBrief",
]
