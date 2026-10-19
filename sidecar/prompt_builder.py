"""Implementation of System Prompt Construction (SPEC §1.2, F-0002).

Augments Pi's system-prompt logic by replacing generic coding-agent body
with Locus SOUL personality, injecting Context Forge context and State Engine
operating mode / faction status.
"""
from __future__ import annotations

import datetime
from pathlib import Path
from typing import List, Optional

from sidecar.providers.prompt_builder import (
    BasePromptBuilderProvider,
    ContextFile,
    OperatingState,
    PromptOptions,
    SkillSummary,
)


DEFAULT_SOUL_PERSONALITY = (
    "You are Locus, a personal cognitive operating system and autonomous intelligence partner.\n"
    "You operate in high-agency, low-friction alignment with your owner's long-term outcomes and daily priorities.\n"
    "Communicate directly, concisely, and execute tasks with rigorous precision."
)


class PromptBuilderProvider(BasePromptBuilderProvider):
    """Concrete provider implementing Locus system prompt construction."""

    def __init__(self, default_vault_path: Optional[str] = None):
        self.default_vault_path = default_vault_path

    def load_soul_personality(self, vault_path: Optional[str] = None) -> str:
        """Load SOUL.md personality from the vault or return default SOUL personality."""
        path_to_try = vault_path or self.default_vault_path
        if path_to_try:
            soul_file = Path(path_to_try) / "00-System" / "SOUL.md"
            if soul_file.is_file():
                try:
                    content = soul_file.read_text(encoding="utf-8").strip()
                    if content:
                        return content
                except Exception:
                    pass
        return DEFAULT_SOUL_PERSONALITY

    def format_operating_state(self, state: OperatingState) -> str:
        """Format State Engine DCS, mode, and factions per §1.2 and §25."""
        lines = [
            "<state_engine_status>",
            f"Daily Capacity Score (DCS): {state.dcs:.1f} / 10.0",
            f"Active Operating Mode: {state.operating_mode}",
            "Faction Allocation: " + ", ".join(f"{k}: {v:.1f}%" for k, v in state.faction_status.items()),
            "</state_engine_status>",
        ]
        return "\n".join(lines)

    def format_skills_for_prompt(self, skills: List[SkillSummary]) -> str:
        """Format available skills into a prompt section per Pi convention."""
        if not skills:
            return ""
        lines = ["<available_skills>"]
        for s in skills:
            lines.append(f"- {s.name}: {s.description}")
        lines.append("</available_skills>")
        return "\n".join(lines)

    def build_system_prompt(self, options: PromptOptions) -> str:
        """SPEC §1.2 line 364: FUNCTION buildSystemPrompt(options)."""
        # SPEC §1.2 line 366: Resolve CWD with forward slashes
        prompt_cwd = options.cwd.replace("\\", "/")

        # SPEC §1.2 line 367: date = formatDate(now())
        now = datetime.datetime.now(datetime.timezone.utc)
        date_str = now.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Determine primary persona/body
        if options.custom_prompt:
            body = options.custom_prompt
        else:
            # SPEC §1.2 line 409: Replace the coding-agent prompt body with Locus's SOUL.md personality
            body = options.soul_context or self.load_soul_personality()

        sections: List[str] = [body]

        # SPEC §1.2 line 388-397: Dynamic guidelines & tools if not custom prompt
        if not options.custom_prompt:
            tools = options.available_tools or ["read", "bash", "edit", "write"]
            tools_list = "\n".join(f"- {t}" for t in tools)
            sections.append(f"Available tools:\n{tools_list}")

            guidelines = []
            if "bash" in tools and not any(t in tools for t in ["grep", "find", "ls"]):
                guidelines.append("Use bash for file operations like ls, rg, find")
            guidelines.extend(options.prompt_guidelines)
            guidelines.append("Be concise in your responses")
            guidelines.append("Show file paths clearly when working with files")
            sections.append("Guidelines:\n" + "\n".join(f"- {g}" for g in guidelines))

        # SPEC §1.2 line 413: State Engine injection (current DCS, mode, factions)
        if options.operating_state:
            state_text = self.format_operating_state(options.operating_state)
            sections.append(state_text)

        # SPEC §1.2 line 412: Context Forge injection (assembled context tokens)
        if options.context_forge_tokens:
            sections.append(f"<context_forge>\n{options.context_forge_tokens}\n</context_forge>")

        # SPEC §1.2 line 372: Append extra system prompt if provided
        if options.append_system_prompt:
            sections.append(options.append_system_prompt)

        # SPEC §1.2 line 375-379: Project context files wrapped in XML
        if options.context_files:
            ctx_lines = ["<project_context>"]
            for cf in options.context_files:
                ctx_lines.append(f"<project_instructions path='{cf.path}'>\n{cf.content}\n</project_instructions>")
            ctx_lines.append("</project_context>")
            sections.append("\n".join(ctx_lines))

        # SPEC §1.2 line 381: Skills section (only if read tool available)
        if "read" in options.available_tools and options.skills:
            sections.append(self.format_skills_for_prompt(options.skills))

        # SPEC §1.2 line 383-384: Metadata footers
        sections.append(f"Current date: {date_str}")
        sections.append(f"Current working directory: {prompt_cwd}")

        return "\n\n".join(sections)
