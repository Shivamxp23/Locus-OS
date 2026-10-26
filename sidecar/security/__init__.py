"""
SPEC §13.1: Prompt Injection Protection module.
"""
from sidecar.security.injection_filter import (
    NormalizedPrompt,
    PromptEnforcementDecision,
    enforce_prompt_input,
    normalize_prompt,
    scan_tool_definition,
)

__all__ = [
    "NormalizedPrompt",
    "PromptEnforcementDecision",
    "enforce_prompt_input",
    "normalize_prompt",
    "scan_tool_definition",
]
