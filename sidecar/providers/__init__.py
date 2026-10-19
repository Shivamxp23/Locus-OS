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
from sidecar.providers.cost_tracker import (
    BaseCostTrackerProvider,
    CanonicalUsage,
    CostResult,
    PricingEntry,
)
from sidecar.providers.title_generator import (
    BaseTitleGeneratorProvider,
    TitleGenerationRequest,
    TitleGenerationResult,
)
from sidecar.providers.context_compression import (
    BaseCompressionProvider,
    CompactionResult,
    CompressionMode,
    ContextMessage,
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
from sidecar.providers.learning import (
    BaseLearningProvider,
    LearningCandidate,
    PatternHorizon,
    PatternRecord,
    RewardSignal,
    StableFacet,
    ToolUsageRecord,
)
from sidecar.providers.model_manager import (
    BaseModelManagementProvider,
    ModelDescriptor,
    ModelTier,
    TurnEscalationDecision,
    TurnEscalationRequest,
)
from sidecar.providers.post_turn import (
    ALLOWED_REVIEW_TOOLS,
    BasePostTurnProvider,
    PostTurnReviewResult,
    SkillUpdatePreference,
)
from sidecar.providers.prompt_builder import BasePromptBuilderProvider, PromptOptions
from sidecar.providers.rate_limit import (
    BaseRateLimitProvider,
    RateLimitBucket,
    RateLimitState,
)
from sidecar.providers.tool_system import (
    AgentTool,
    AgentToolResult,
    BaseToolSystemProvider,
    ExecutionMode,
)
from sidecar.providers.trajectory import BaseTrajectoryRecorder, TrajectorySession, TurnRecord
from sidecar.providers.vault_sync import BaseVaultSyncProvider, SyncState

__all__ = [
    "ALLOWED_REVIEW_TOOLS",
    "AgentTool",
    "AgentToolResult",
    "ArchiveResult",
    "BaseChannelProvider",
    "BaseChatArchiverProvider",
    "BaseCompressionProvider",
    "BaseCostTrackerProvider",
    "BaseExtensionLifecycleProvider",
    "BaseHarnessProvider",
    "BaseLearningProvider",
    "BaseLifeOSProvider",
    "BaseModelManagementProvider",
    "BasePostTurnProvider",
    "BasePromptBuilderProvider",
    "BaseRateLimitProvider",
    "BaseTitleGeneratorProvider",
    "BaseToolSystemProvider",
    "BaseTrajectoryRecorder",
    "BaseVaultSyncProvider",
    "CANONICAL_LIFECYCLE_EVENTS",
    "CanonicalUsage",
    "ChatTurn",
    "CheckInInput",
    "CompactionResult",
    "CompressionMode",
    "CostResult",
    "ContextMessage",
    "DCSResult",
    "DelegationResult",
    "ExecutionMode",
    "ExtensionHookDescriptor",
    "FactionType",
    "GoalStackLevel",
    "HarnessType",
    "LifecycleDispatchResult",
    "LearningCandidate",
    "ModeConstraints",
    "ModelDescriptor",
    "ModelTier",
    "NormalizedChat",
    "OperatingMode",
    "PatternHorizon",
    "PatternRecord",
    "PostTaskLog",
    "PostTurnReviewResult",
    "PricingEntry",
    "PromptOptions",
    "RateLimitBucket",
    "RateLimitState",
    "RewardSignal",
    "SkillUpdatePreference",
    "StableFacet",
    "SyncState",
    "TaskBrief",
    "TaskScoreInput",
    "TaskScoreResult",
    "TitleGenerationRequest",
    "TitleGenerationResult",
    "ToolUsageRecord",
    "TrajectorySession",
    "TurnEscalationDecision",
    "TurnEscalationRequest",
    "TurnRecord",
]
