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
from sidecar.providers.git_tools import (
    BaseGitToolsProvider,
    GitCommitResult,
    GitDiffResult,
    GitLogEntry,
    GitStatusResult,
)
from sidecar.providers.tool_call_validation import (
    BaseToolCallValidationProvider,
    ToolCallGuardrailConfig,
    ToolCategory,
    ValidationAction,
    ValidationDecision,
    ValidationObservation,
)
from sidecar.providers.tool_output_accumulator import (
    BaseToolOutputAccumulatorProvider,
    FullOutputResult,
    OutputAccumulatorConfig,
    OutputSnapshot,
    TruncationType,
)
from sidecar.providers.tool_result_classification import (
    BaseToolResultClassificationProvider,
    ResultClassificationType,
    ToolResultClassification,
    ToolResultClassificationConfig,
)
from sidecar.providers.tool_timeout_budget import (
    BaseToolTimeoutBudgetProvider,
    ExecutionBudgetRecord,
    TimeoutAction,
    TimeoutResolution,
    ToolTimeoutConfig,
)
from sidecar.providers.custom_locus_tools import (
    BaseCustomLocusToolsProvider,
    CustomLocusToolsConfig,
    CustomToolResult,
    CustomToolSpec,
)
from sidecar.providers.memory import (
    BaseMemoryProvider,
    EntityType,
    GraphQueryResult,
    MemoryConfig,
    MemoryEntry,
    POLEEntity,
    Relationship,
)
from sidecar.providers.memory_tree import (
    BaseMemoryTreeProvider,
    MemoryTreeConfig,
    TreeNode,
    TreeScopeConfig,
)
from sidecar.providers.memory_sync import (
    BaseMemorySyncProvider,
    BaseSyncPipeline,
    MemorySyncConfig,
    SourceScope,
    SyncOutcome,
    SyncPipelineKind,
)
from sidecar.providers.memory_queue import (
    BaseMemoryQueueProvider,
    JobKind,
    JobRecord,
    JobStatus,
    MemoryQueueConfig,
)
from sidecar.providers.memory_diff import (
    BaseMemoryDiffProvider,
    ChangeKind,
    Checkpoint,
    CrossSourceDiff,
    DiffResult,
    DiffSummary,
    ItemChange,
    MemoryDiffConfig,
    Snapshot,
    SnapshotItem,
    SnapshotTrigger,
)
from sidecar.providers.holographic import (
    BaseAssociativeMemoryProvider,
    BaseHolographicProvider,
    HolographicConfig,
    HRRVector,
)
from sidecar.providers.stdp_reinforcement import (
    A_MINUS,
    A_PLUS,
    BaseGraphPlasticityProvider,
    BaseSTDPProvider,
    OutcomeEvent,
    PRUNE_THRESHOLD,
    RetrievalEvent,
    STDPConfig,
    TAU_MINUS,
    TAU_PLUS,
    TraversedEdgeRecord,
    TurnAuditLog,
    W_MAX,
    W_MIN,
)
from sidecar.providers.spaced_repetition import (
    BaseSpacedRepetitionProvider,
    CORE_FACT_MIN_EASE,
    CORE_FACT_MIN_REPETITIONS,
    DEFAULT_EASE_FACTOR,
    DEFAULT_STABILITY,
    INITIAL_INTERVAL_FIRST,
    INITIAL_INTERVAL_SECOND,
    MIN_EASE_FACTOR,
    MemoryConsolidationProvider,
    MemoryNodeState,
    SpacedRepetitionConfig,
)
from sidecar.providers.project_memory_decay import (
    BaseMemoryDecayProvider,
    DefaultProjectMemoryDecayProvider,
    MemoryDecayProvider,
    ProjectDecayConfig,
    ProjectMemoryDecayProvider,
)
from sidecar.providers.compaction import (
    CompactionConfig,
    CompactionProvider,
    ContextEngine,
    MemoryProviderHook,
)
from sidecar.providers.headroom_ccr import (
    CompressionProvider,
    DefaultHeadroomCCRProvider,
)
from sidecar.providers.memory_provider import (
    DefaultMemoryProvider,
    MemoryManager,
    MemoryProvider,
)
from sidecar.providers.session_management import (
    BaseSessionManagementProvider,
    DefaultSessionManagementProvider,
)
from sidecar.providers.context_references import (
    BaseContextReferenceProvider,
    DefaultContextReferenceProvider,
)
from sidecar.providers.coding_context import (
    BaseCodingContextProvider,
    DefaultCodingContextProvider,
)
from sidecar.providers.tui_dashboard import (
    BaseTUIDashboardProvider,
    DefaultTUIDashboardProvider,
)
from sidecar.providers.cli_doctor_diagnostics import (
    BaseCLIDoctorDiagnosticsProvider,
    DefaultCLIDoctorDiagnosticsProvider,
)
from sidecar.providers.skill_marketplace import (
    BaseSkillMarketplaceProvider,
    DefaultSkillMarketplaceProvider,
)
from sidecar.providers.acp_protocol import (
    BaseACPClientProvider,
    DefaultACPClientProvider,
)
from sidecar.providers.plugin_llm import (
    BasePluginLLMProvider,
    DefaultPluginLLMProvider,
)
from sidecar.providers.architect import (
    BaseArchitectProvider,
    DefaultArchitectProvider,
)
from sidecar.providers.agent_experience import (
    BaseAgentExperienceProvider,
    DefaultAgentExperienceProvider,
)
from sidecar.providers.injection_filter import (
    BaseInjectionFilterProvider,
    DefaultInjectionFilterProvider,
)
from sidecar.providers.file_safety import (
    BaseFileSafetyProvider,
    DefaultFileSafetyProvider,
)
from sidecar.providers.autonomy_tiers import (
    BaseAutonomyTiersProvider,
    DefaultAutonomyTiersProvider,
)
from sidecar.providers.approval_gate import (
    BaseApprovalGateProvider,
    DefaultApprovalGateProvider,
)
from sidecar.providers.shell_blocklist import (
    BaseShellBlocklistProvider,
    DefaultShellBlocklistProvider,
)
from sidecar.providers.data_redaction import (
    BaseDataRedactionProvider,
    DefaultDataRedactionProvider,
)
from sidecar.providers.think_scrubber import (
    BaseThinkScrubberProvider,
    DefaultThinkScrubberProvider,
)
from sidecar.providers.message_sanitizer import (
    BaseMessageSanitizerProvider,
    DefaultMessageSanitizerProvider,
)
from sidecar.providers.voice import (
    BaseVoiceProvider,
    DefaultVoiceProvider,
)
from sidecar.providers.web_search import (
    BaseWebSearchProvider,
    DefaultWebSearchProvider,
)
from sidecar.providers.browser import (
    BaseBrowserProvider,
    DefaultBrowserProvider,
)
from sidecar.providers.screen import (
    BaseScreenProvider,
    DefaultScreenProvider,
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
from sidecar.providers.subagents import (
    ArchetypeCategory,
    AutoResearchRequest,
    AutoResearchResult,
    BaseSubagentProvider,
    SubagentArchetype,
    SubagentSpawnRequest,
    SubagentSpawnResult,
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
    "ArchetypeCategory",
    "AutoResearchRequest",
    "AutoResearchResult",
    "BaseSubagentProvider",
    "SubagentArchetype",
    "SubagentSpawnRequest",
    "SubagentSpawnResult",
    "BaseGitToolsProvider",
    "GitCommitResult",
    "GitDiffResult",
    "GitLogEntry",
    "GitStatusResult",
    "BaseToolCallValidationProvider",
    "ToolCallGuardrailConfig",
    "ToolCategory",
    "ValidationAction",
    "ValidationDecision",
    "ValidationObservation",
    "BaseToolOutputAccumulatorProvider",
    "FullOutputResult",
    "OutputAccumulatorConfig",
    "OutputSnapshot",
    "TruncationType",
    "BaseToolResultClassificationProvider",
    "ResultClassificationType",
    "ToolResultClassification",
    "ToolResultClassificationConfig",
    "BaseToolTimeoutBudgetProvider",
    "ExecutionBudgetRecord",
    "TimeoutAction",
    "TimeoutResolution",
    "ToolTimeoutConfig",
    "BaseCustomLocusToolsProvider",
    "CustomLocusToolsConfig",
    "CustomToolResult",
    "CustomToolSpec",
    "BaseMemoryProvider",
    "EntityType",
    "GraphQueryResult",
    "MemoryConfig",
    "MemoryEntry",
    "POLEEntity",
    "Relationship",
    "BaseMemoryTreeProvider",
    "MemoryTreeConfig",
    "TreeNode",
    "TreeScopeConfig",
    "BaseMemorySyncProvider",
    "BaseSyncPipeline",
    "MemorySyncConfig",
    "SourceScope",
    "SyncOutcome",
    "SyncPipelineKind",
    "BaseMemoryQueueProvider",
    "JobKind",
    "JobRecord",
    "JobStatus",
    "MemoryQueueConfig",
    "BaseMemoryDiffProvider",
    "ChangeKind",
    "Checkpoint",
    "CrossSourceDiff",
    "DiffResult",
    "DiffSummary",
    "ItemChange",
    "MemoryDiffConfig",
    "Snapshot",
    "SnapshotItem",
    "SnapshotTrigger",
    "BaseAssociativeMemoryProvider",
    "BaseHolographicProvider",
    "HolographicConfig",
    "HRRVector",
    "A_MINUS",
    "A_PLUS",
    "BaseGraphPlasticityProvider",
    "BaseSTDPProvider",
    "OutcomeEvent",
    "PRUNE_THRESHOLD",
    "RetrievalEvent",
    "STDPConfig",
    "TAU_MINUS",
    "TAU_PLUS",
    "TraversedEdgeRecord",
    "TurnAuditLog",
    "W_MAX",
    "W_MIN",
    "BaseSpacedRepetitionProvider",
    "CORE_FACT_MIN_EASE",
    "CORE_FACT_MIN_REPETITIONS",
    "DEFAULT_EASE_FACTOR",
    "DEFAULT_STABILITY",
    "INITIAL_INTERVAL_FIRST",
    "INITIAL_INTERVAL_SECOND",
    "MIN_EASE_FACTOR",
    "MemoryConsolidationProvider",
    "MemoryNodeState",
    "SpacedRepetitionConfig",
    "BaseMemoryDecayProvider",
    "DefaultProjectMemoryDecayProvider",
    "MemoryDecayProvider",
    "ProjectDecayConfig",
    "ProjectMemoryDecayProvider",
    "CompactionConfig",
    "CompactionProvider",
    "ContextEngine",
    "MemoryProviderHook",
    "CompressionProvider",
    "DefaultHeadroomCCRProvider",
    "DefaultMemoryProvider",
    "MemoryManager",
    "MemoryProvider",
    "BaseSessionManagementProvider",
    "DefaultSessionManagementProvider",
    "BaseContextReferenceProvider",
    "DefaultContextReferenceProvider",
    "BaseCodingContextProvider",
    "DefaultCodingContextProvider",
    "BaseTUIDashboardProvider",
    "DefaultTUIDashboardProvider",
    "BaseCLIDoctorDiagnosticsProvider",
    "DefaultCLIDoctorDiagnosticsProvider",
    "BaseSkillMarketplaceProvider",
    "DefaultSkillMarketplaceProvider",
    "BaseACPClientProvider",
    "DefaultACPClientProvider",
    "BasePluginLLMProvider",
    "DefaultPluginLLMProvider",
    "BaseArchitectProvider",
    "DefaultArchitectProvider",
    "BaseAgentExperienceProvider",
    "DefaultAgentExperienceProvider",
    "BaseInjectionFilterProvider",
    "DefaultInjectionFilterProvider",
    "BaseFileSafetyProvider",
    "DefaultFileSafetyProvider",
    "BaseAutonomyTiersProvider",
    "DefaultAutonomyTiersProvider",
    "BaseApprovalGateProvider",
    "DefaultApprovalGateProvider",
    "BaseShellBlocklistProvider",
    "DefaultShellBlocklistProvider",
    "BaseDataRedactionProvider",
    "DefaultDataRedactionProvider",
    "BaseThinkScrubberProvider",
    "DefaultThinkScrubberProvider",
    "BaseMessageSanitizerProvider",
    "DefaultMessageSanitizerProvider",
    "BaseVoiceProvider",
    "DefaultVoiceProvider",
    "BaseWebSearchProvider",
    "DefaultWebSearchProvider",
    "BaseBrowserProvider",
    "DefaultBrowserProvider",
    "BaseScreenProvider",
    "DefaultScreenProvider",
]
