"""
SPEC §13.1, §13.2, §13.4: Security modules.
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
]
