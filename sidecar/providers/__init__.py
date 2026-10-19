"""
Locus Provider interfaces and implementations.
"""
from __future__ import annotations

from sidecar.providers.channel import BaseChannelProvider
from sidecar.providers.chat_archiver import (
    ArchiveResult,
    BaseChatArchiverProvider,
    ChatTurn,
    NormalizedChat,
)
from sidecar.providers.harness import (
    BaseHarnessProvider,
    DelegationResult,
    HarnessType,
    TaskBrief,
)
from sidecar.providers.extension_lifecycle import (
    BaseExtensionLifecycleProvider,
    CANONICAL_LIFECYCLE_EVENTS,
    ExtensionHookDescriptor,
    LifecycleDispatchResult,
)
from sidecar.providers.life_os import (
    BaseLifeOSProvider,
    CheckInInput,
    DCSResult,
    FactionType,
    GoalStackLevel,
    ModeConstraints,
    OperatingMode,
    PostTaskLog,
    TaskScoreInput,
    TaskScoreResult,
)
from sidecar.providers.model_manager import (
    BaseModelManagementProvider,
    ModelDescriptor,
    ModelTier,
    TurnEscalationDecision,
    TurnEscalationRequest,
)
from sidecar.providers.prompt_builder import BasePromptBuilderProvider, PromptOptions
from sidecar.providers.tool_system import (
    AgentTool,
    AgentToolResult,
    BaseToolSystemProvider,
    ExecutionMode,
)
from sidecar.providers.trajectory import BaseTrajectoryRecorder, TrajectorySession, TurnRecord
from sidecar.providers.vault_sync import BaseVaultSyncProvider, SyncState

__all__ = [
    "AgentTool",
    "AgentToolResult",
    "ArchiveResult",
    "BaseChannelProvider",
    "BaseChatArchiverProvider",
    "BaseExtensionLifecycleProvider",
    "BaseHarnessProvider",
    "BaseLifeOSProvider",
    "BaseModelManagementProvider",
    "BasePromptBuilderProvider",
    "BaseToolSystemProvider",
    "BaseTrajectoryRecorder",
    "BaseVaultSyncProvider",
    "CANONICAL_LIFECYCLE_EVENTS",
    "ChatTurn",
    "CheckInInput",
    "DCSResult",
    "DelegationResult",
    "ExecutionMode",
    "ExtensionHookDescriptor",
    "FactionType",
    "GoalStackLevel",
    "HarnessType",
    "LifecycleDispatchResult",
    "ModeConstraints",
    "ModelDescriptor",
    "ModelTier",
    "NormalizedChat",
    "OperatingMode",
    "PostTaskLog",
    "PromptOptions",
    "SyncState",
    "TaskBrief",
    "TaskScoreInput",
    "TaskScoreResult",
    "TrajectorySession",
    "TurnEscalationDecision",
    "TurnEscalationRequest",
    "TurnRecord",
]
