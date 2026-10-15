"""System Prompt Construction (§1.2).

Constructs the multi-layer Locus system prompt:
1. Base SOUL.md / personality definition.
2. Active tools manifest and execution guidelines.
3. Project context files (AGENTS.md, docs).
4. Injected Context Forge (6-layer context <= 800 tokens).
5. State Engine dynamics (DCS, active operating mode, faction lag).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


DEFAULT_LOCUS_SOUL: str = (
    "You are Locus, a sovereign cognitive operating system and autonomous pair programmer. "
    "Operate deterministically, respect user autonomy tiers, and maintain persistent state."
)


@dataclass
class PromptContextFile:
    path: str
    content: str


@dataclass
class PromptOptions:
    cwd: str = "/"
    soul_override: Optional[str] = None
    append_system_prompt: Optional[str] = None
    context_files: List[PromptContextFile] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    selected_tools: List[str] = field(default_factory=list)
    prompt_guidelines: List[str] = field(default_factory=list)
    context_forge_injection: Optional[str] = None
    state_injection: Optional[str] = None


class SystemPromptBuilder:
    """Builds composite system prompts with structured boundaries and token discipline."""

    def __init__(self, default_soul: str = DEFAULT_LOCUS_SOUL) -> None:
        self.default_soul = default_soul

    def build(self, options: Optional[PromptOptions] = None) -> str:
        opts = options or PromptOptions()
        normalized_cwd = opts.cwd.replace("\\", "/")
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        sections: List[str] = []

        # 1. Personality / SOUL
        sections.append(opts.soul_override or self.default_soul)

        # 2. Operating Environment
        sections.append(f"Working Directory: {normalized_cwd}\nCurrent Date: {current_date}")

        # 3. Dynamic State Injection (DCS, Operating Mode)
        if opts.state_injection:
            sections.append(f"<locus_state>\n{opts.state_injection}\n</locus_state>")

        # 4. Context Forge Injected Context
        if opts.context_forge_injection:
            sections.append(f"<context_forge>\n{opts.context_forge_injection}\n</context_forge>")

        # 5. Tools & Guidelines
        tools = opts.selected_tools or ["read", "bash", "edit", "write"]
        sections.append("Available Tools:\n" + "\n".join(f"- {t}" for t in tools))

        guidelines = list(opts.prompt_guidelines)
        guidelines.append("Be concise and avoid sycophancy.")
        sections.append("Guidelines:\n" + "\n".join(f"- {g}" for g in guidelines))

        # 6. Context Files (e.g., AGENTS.md)
        if opts.context_files:
            cf_text = "<project_context>\n"
            for cf in opts.context_files:
                cf_text += f"<file path='{cf.path}'>\n{cf.content}\n</file>\n"
            cf_text += "</project_context>"
            sections.append(cf_text)

        # 7. Append Custom Section
        if opts.append_system_prompt:
            sections.append(opts.append_system_prompt)

        return "\n\n".join(sections)


def build_system_prompt(options: Optional[PromptOptions] = None) -> str:
    return SystemPromptBuilder().build(options)
