"""
SPEC §13.1, §13.2, §13.4, §13.5, §13.7, §13.8: Security modules.
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
from sidecar.security.shell_policy import (
    DEFAULT_BLOCKED_PATTERNS as DEFAULT_BLOCKED_SHELL_PATTERNS,
    SENSITIVE_HOME_DIRS,
    SENSITIVE_HOME_FILES,
    ShellInspectionDecision,
    ShellPolicyEngine,
)
from sidecar.security.redact import (
    KEY_PATTERNS,
    SENSITIVE_BODY_KEYS,
    SENSITIVE_QUERY_PARAMS,
    DataRedactor,
    mask_token,
)
from sidecar.security.think_scrubber import (
    SUPPORTED_TAGS as SUPPORTED_THINK_TAGS,
    ScrubState,
    StreamingThinkScrubber,
    ThinkTokenScrubber,
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
    "DEFAULT_BLOCKED_SHELL_PATTERNS",
    "SENSITIVE_HOME_DIRS",
    "SENSITIVE_HOME_FILES",
    "ShellInspectionDecision",
    "ShellPolicyEngine",
    "KEY_PATTERNS",
    "SENSITIVE_BODY_KEYS",
    "SENSITIVE_QUERY_PARAMS",
    "DataRedactor",
    "mask_token",
    "SUPPORTED_THINK_TAGS",
    "ScrubState",
    "StreamingThinkScrubber",
    "ThinkTokenScrubber",
]
