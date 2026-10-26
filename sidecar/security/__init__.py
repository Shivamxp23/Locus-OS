"""
SPEC §13.1, §13.2, §13.4, §13.5: Security modules.
"""
from sidecar.security.injection_filter import (
    NormalizedPrompt,
    PromptEnforcementDecision,
    enforce_prompt_input,
    normalize_prompt,
    scan_tool_definition,
)
from sidecar.security.file_safety import (
    CwdJail,
    FileStateRecord,
    FileStateTracker,
    PathValidationDecision,
)
from sidecar.security.autonomy_tiers import (
    AutonomyTier,
    AutonomyTierManager,
    TierEvaluationDecision,
    ToolCategory,
)
from sidecar.security.approval_store import (
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStore,
)

__all__ = [
    "NormalizedPrompt",
    "PromptEnforcementDecision",
    "enforce_prompt_input",
    "normalize_prompt",
    "scan_tool_definition",
    "CwdJail",
    "FileStateRecord",
    "FileStateTracker",
    "PathValidationDecision",
    "AutonomyTier",
    "AutonomyTierManager",
    "TierEvaluationDecision",
    "ToolCategory",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalStore",
]
