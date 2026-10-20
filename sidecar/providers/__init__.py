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
from sidecar.providers.context_forge import (
    ANTI_HALLUCINATION_INSTRUCTION,
    AssembledLayer,
    BaseContextForgeProvider,
    ContextForgeResult,
    LOCUS_SHORTHAND_DICTIONARY,
    LayerBudgetConfig,
    RetrievalInput,
    SOURCE_PRIORITIES,
)
from sidecar.providers.anti_hallucination import (
    BaseAntiHallucinationProvider,
    BrainErrorLog,
    CheckResult,
    DEFAULT_CAVEAT_MESSAGE,
    FactualClaim,
    GuardMode,
)
from sidecar.providers.extension_lifecycle import (
    BaseExtensionLifecycleProvider,
    CANONICAL_LIFECYCLE_EVENTS,
    ExtensionHookDescriptor,
    LifecycleDispatchResult,
)
from sidecar.providers.image_generation import (
    BaseImageGenerationProvider,
    ImageGenerationRequest,
    ImageGenerationResult,
    ImageModelDescriptor,
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
from sidecar.providers.model_routing import (
    BaseModelRoutingProvider,
    ChatRequest,
    ChatResponse,
    CostSensitivity,
    HealthCheckResult,
    LatencyBudget,
    RoutingDecision,
    RoutingHints,
    RoutingRecord,
    TargetBackend,
    TaskCategory,
)
from sidecar.providers.onboarding import (
    BaseOnboardingProvider,
    DiagnosticProbeResult,
    OnboardingStepResult,
    TopologyType,
)
from sidecar.providers.post_turn import (
    ALLOWED_REVIEW_TOOLS,
    BasePostTurnProvider,
    PostTurnReviewResult,
    SkillUpdatePreference,
)
from sidecar.providers.prompt_builder import BasePromptBuilderProvider, PromptOptions
from sidecar.providers.query_router import (
    ALL_RETRIEVAL_SOURCES,
    BaseQueryRouterProvider,
    IntentType,
    RoutingManifest,
    TemporalScope,
)
from sidecar.providers.rate_limit import (
    BaseRateLimitProvider,
    RateLimitBucket,
    RateLimitState,
)
from sidecar.providers.state_engine import (
    BaseStateEngineProvider,
    CheckInRecord,
    CurrentState,
    OperatingMode as StateOperatingMode,
)
from sidecar.providers.tool_system import (
    AgentTool,
    AgentToolResult,
    BaseToolSystemProvider,
    ExecutionMode,
)
from sidecar.providers.streaming_sse import (
    BaseStreamingSSEProvider,
    SSEEvent,
    StreamOptions,
)
from sidecar.providers.trajectory import BaseTrajectoryRecorder, TrajectorySession, TurnRecord
from sidecar.providers.vault_sync import BaseVaultSyncProvider, SyncState

__all__ = [
    "ALL_RETRIEVAL_SOURCES",
    "ALLOWED_REVIEW_TOOLS",
    "ANTI_HALLUCINATION_INSTRUCTION",
    "AgentTool",
    "AgentToolResult",
    "ArchiveResult",
    "AssembledLayer",
    "BaseAntiHallucinationProvider",
    "BaseChannelProvider",
    "BaseChatArchiverProvider",
    "BaseCompressionProvider",
    "BaseContextForgeProvider",
    "BaseCostTrackerProvider",
    "BrainErrorLog",
    "CheckResult",
    "DEFAULT_CAVEAT_MESSAGE",
    "FactualClaim",
    "GuardMode",
    "BaseExtensionLifecycleProvider",
    "BaseHarnessProvider",
    "BaseImageGenerationProvider",
    "BaseLearningProvider",
    "BaseLifeOSProvider",
    "BaseModelManagementProvider",
    "BaseModelRoutingProvider",
    "BaseOnboardingProvider",
    "BasePostTurnProvider",
    "BasePromptBuilderProvider",
    "BaseQueryRouterProvider",
    "BaseRateLimitProvider",
    "BaseStateEngineProvider",
    "BaseStreamingSSEProvider",
    "BaseTitleGeneratorProvider",
    "BaseToolSystemProvider",
    "BaseTrajectoryRecorder",
    "BaseVaultSyncProvider",
    "CANONICAL_LIFECYCLE_EVENTS",
    "CanonicalUsage",
    "ChatTurn",
    "ChatRequest",
    "ChatResponse",
    "CheckInInput",
    "CheckInRecord",
    "CompactionResult",
    "CompressionMode",
    "CostResult",
    "CostSensitivity",
    "ContextForgeResult",
    "ContextMessage",
    "CurrentState",
    "DCSResult",
    "DelegationResult",
    "DiagnosticProbeResult",
    "ExecutionMode",
    "ExtensionHookDescriptor",
    "FactionType",
    "GoalStackLevel",
    "HarnessType",
    "HealthCheckResult",
    "ImageGenerationRequest",
    "ImageGenerationResult",
    "ImageModelDescriptor",
    "IntentType",
    "LatencyBudget",
    "LayerBudgetConfig",
    "LifecycleDispatchResult",
    "LearningCandidate",
    "LOCUS_SHORTHAND_DICTIONARY",
    "ModeConstraints",
    "ModelDescriptor",
    "ModelTier",
    "NormalizedChat",
    "OnboardingStepResult",
    "OperatingMode",
    "PatternHorizon",
    "PatternRecord",
    "PostTaskLog",
    "PostTurnReviewResult",
    "PricingEntry",
    "PromptOptions",
    "RateLimitBucket",
    "RateLimitState",
    "RetrievalInput",
    "RewardSignal",
    "RoutingDecision",
    "RoutingHints",
    "RoutingManifest",
    "RoutingRecord",
    "SOURCE_PRIORITIES",
    "SSEEvent",
    "SkillUpdatePreference",
    "StableFacet",
    "StreamOptions",
    "SyncState",
    "TargetBackend",
    "TaskBrief",
    "TaskCategory",
    "TaskScoreInput",
    "TaskScoreResult",
    "TemporalScope",
    "TitleGenerationRequest",
    "TitleGenerationResult",
    "ToolUsageRecord",
    "TopologyType",
    "TrajectorySession",
    "TurnEscalationDecision",
    "TurnEscalationRequest",
    "TurnRecord",
]
