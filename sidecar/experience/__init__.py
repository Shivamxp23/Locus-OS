"""
SPEC §10.9: Agent Experience Tracking (Procedural Memory) module.
"""
from sidecar.experience.procedural import (
    AgentExperience,
    AgentExperienceCaptureHook,
    ExperienceStore,
    prepend_experience_block,
    redact_text,
    render_experience_hits,
    stable_experience_id,
)

__all__ = [
    "AgentExperience",
    "AgentExperienceCaptureHook",
    "ExperienceStore",
    "prepend_experience_block",
    "redact_text",
    "render_experience_hits",
    "stable_experience_id",
]
