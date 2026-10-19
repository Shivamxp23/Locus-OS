"""
Unit tests for System Prompt Construction (SPEC §1.2, F-0002, US-21).
Tests assert prompt construction, SOUL personality loading, Context Forge
and State Engine injections, skills formatting, and path normalization.
"""
from __future__ import annotations

import os
from pathlib import Path
import pytest

from sidecar.prompt_builder import DEFAULT_SOUL_PERSONALITY, PromptBuilderProvider
from sidecar.providers.prompt_builder import (
    BasePromptBuilderProvider,
    ContextFile,
    OperatingState,
    PromptOptions,
    SkillSummary,
)


@pytest.fixture
def provider():
    return PromptBuilderProvider()


def test_system_prompt_cwd_normalization(provider):
    """SPEC §1.2 line 366: "promptCwd = options.cwd.replace('\\\\', '/')"."""
    opts = PromptOptions(cwd="C:\\Users\\soni8\\Desktop\\locus-os")
    prompt = provider.build_system_prompt(opts)
    assert "Current working directory: C:/Users/soni8/Desktop/locus-os" in prompt
    assert "C:\\Users\\soni8" not in prompt


def test_system_prompt_date_formatting(provider):
    """SPEC §1.2 line 367: "date = formatDate(now())"."""
    opts = PromptOptions(cwd="/workspace")
    prompt = provider.build_system_prompt(opts)
    assert "Current date: " in prompt
    assert "UTC" in prompt


def test_system_prompt_custom_prompt_override(provider):
    """SPEC §1.2 line 370: "IF options.customPrompt: prompt = options.customPrompt"."""
    opts = PromptOptions(
        cwd="/workspace",
        custom_prompt="You are a specialized test agent with custom instructions."
    )
    prompt = provider.build_system_prompt(opts)
    assert "You are a specialized test agent with custom instructions." in prompt
    assert DEFAULT_SOUL_PERSONALITY not in prompt


def test_system_prompt_append_system_prompt(provider):
    """SPEC §1.2 line 372: "IF options.appendSystemPrompt: prompt += options.appendSystemPrompt"."""
    opts = PromptOptions(
        cwd="/workspace",
        append_system_prompt="CRITICAL INSTRUCTION: Never execute untrusted binaries."
    )
    prompt = provider.build_system_prompt(opts)
    assert "CRITICAL INSTRUCTION: Never execute untrusted binaries." in prompt


def test_system_prompt_context_files_xml(provider):
    """SPEC §1.2 line 375: "IF options.contextFiles.length > 0: prompt += '<project_context>'"."""
    cf1 = ContextFile(path="AGENTS.md", content="Law 1: work inside root.")
    cf2 = ContextFile(path="SOUL.md", content="High agency cognitive OS.")
    opts = PromptOptions(cwd="/workspace", context_files=[cf1, cf2])
    prompt = provider.build_system_prompt(opts)
    assert "<project_context>" in prompt
    assert "</project_context>" in prompt
    assert "<project_instructions path='AGENTS.md'>\nLaw 1: work inside root.\n</project_instructions>" in prompt
    assert "<project_instructions path='SOUL.md'>\nHigh agency cognitive OS.\n</project_instructions>" in prompt


def test_system_prompt_skills_formatting(provider):
    """SPEC §1.2 line 381: "IF 'read' tool available AND options.skills.length > 0: prompt += formatSkillsForPrompt(options.skills)"."""
    skills = [
        SkillSummary(name="web_search", description="Search the web for real-time information."),
        SkillSummary(name="code_analysis", description="Inspect and index code AST.")
    ]
    opts = PromptOptions(cwd="/workspace", available_tools=["read", "bash"], skills=skills)
    prompt = provider.build_system_prompt(opts)
    assert "<available_skills>" in prompt
    assert "- web_search: Search the web for real-time information." in prompt
    assert "- code_analysis: Inspect and index code AST." in prompt


def test_system_prompt_skills_skipped_without_read(provider):
    """SPEC §1.2 line 381: "Append skills section (only if read tool available)"."""
    skills = [SkillSummary(name="web_search", description="Search the web.")]
    opts = PromptOptions(cwd="/workspace", available_tools=["bash", "write"], skills=skills)
    prompt = provider.build_system_prompt(opts)
    assert "<available_skills>" not in prompt


def test_system_prompt_metadata_footers(provider):
    """SPEC §1.2 line 383: "prompt += 'Current date: {date}'"."""
    opts = PromptOptions(cwd="/locus/project")
    prompt = provider.build_system_prompt(opts)
    assert "Current date: " in prompt
    assert "Current working directory: /locus/project" in prompt


def test_system_prompt_soul_personality(tmp_path):
    """SPEC §1.2 line 409: "Replace the coding-agent system prompt body with Locus's SOUL.md personality context"."""
    vault = tmp_path / "vault"
    sys_dir = vault / "00-System"
    sys_dir.mkdir(parents=True)
    soul_file = sys_dir / "SOUL.md"
    custom_soul = "Custom SOUL personality: Strategic architect focusing on deep leverage."
    soul_file.write_text(custom_soul, encoding="utf-8")

    prov = PromptBuilderProvider(default_vault_path=str(vault))
    loaded = prov.load_soul_personality()
    assert loaded == custom_soul

    opts = PromptOptions(cwd="/workspace")
    prompt = prov.build_system_prompt(opts)
    assert custom_soul in prompt


def test_system_prompt_context_forge_injection(provider):
    """SPEC §1.2 line 412: "Add Context Forge injection point: the system prompt gets the 800-token assembled context appended"."""
    forge_ctx = "Context Forge: Active task T-101 | Priority: High | Relevant files: [main.py, utils.py]"
    opts = PromptOptions(cwd="/workspace", context_forge_tokens=forge_ctx)
    prompt = provider.build_system_prompt(opts)
    assert "<context_forge>" in prompt
    assert forge_ctx in prompt
    assert "</context_forge>" in prompt


def test_system_prompt_state_engine_injection(provider):
    """SPEC §1.2 line 413: "The appendSystemPrompt hook is WHERE the State Engine injects current DCS, operating mode, faction status"."""
    state = OperatingState(
        dcs=8.5,
        operating_mode="PEAK",
        faction_status={"Health": 25.0, "Leverage": 25.0, "Craft": 30.0, "Expression": 20.0}
    )
    opts = PromptOptions(cwd="/workspace", operating_state=state)
    prompt = provider.build_system_prompt(opts)
    assert "<state_engine_status>" in prompt
    assert "Daily Capacity Score (DCS): 8.5 / 10.0" in prompt
    assert "Active Operating Mode: PEAK" in prompt
    assert "Craft: 30.0%" in prompt


def test_prompt_builder_provider_interface(provider):
    """SPEC §1.2 line 415: "Lives in locus-extension/src/prompt-builder.ts (canonical path per D-6). Implements Pi's BuildSystemPromptOptions but overrides customPrompt with Locus's personality."."""
    assert isinstance(provider, BasePromptBuilderProvider)
    assert hasattr(provider, "build_system_prompt")
    assert hasattr(provider, "load_soul_personality")
    assert hasattr(provider, "format_operating_state")


def test_system_prompt_bash_guidelines(provider):
    """SPEC §1.2 line 393: "IF has bash but no grep/find/ls: guidelines.add('Use bash for file operations like ls, rg, find')"."""
    opts = PromptOptions(cwd="/workspace", available_tools=["read", "bash", "edit", "write"])
    prompt = provider.build_system_prompt(opts)
    assert "Use bash for file operations like ls, rg, find" in prompt
    assert "Be concise in your responses" in prompt
    assert "Show file paths clearly when working with files" in prompt
