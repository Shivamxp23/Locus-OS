import pytest
from sidecar.prompt_builder import (
    PromptOptions,
    PromptContextFile,
    SystemPromptBuilder,
    build_system_prompt,
    DEFAULT_LOCUS_SOUL,
)


def test_default_prompt_contains_soul_and_cwd():
    prompt = build_system_prompt(PromptOptions(cwd="/workspace/project"))
    assert DEFAULT_LOCUS_SOUL in prompt
    assert "Working Directory: /workspace/project" in prompt
    assert "Available Tools:" in prompt
    assert "Guidelines:" in prompt


def test_prompt_injection_with_context_forge_and_state():
    opts = PromptOptions(
        cwd="C:\\Users\\Locus",
        state_injection="DCS: 82.5 | Mode: FLOW",
        context_forge_injection="[L1 Identity] Active session locus-main",
        context_files=[PromptContextFile(path="AGENTS.md", content="# Project Agents")],
    )
    prompt = build_system_prompt(opts)

    # Windows slashes normalized
    assert "Working Directory: C:/Users/Locus" in prompt
    assert "<locus_state>\nDCS: 82.5 | Mode: FLOW\n</locus_state>" in prompt
    assert "<context_forge>\n[L1 Identity] Active session locus-main\n</context_forge>" in prompt
    assert "<file path='AGENTS.md'>\n# Project Agents\n</file>" in prompt


def test_soul_override():
    custom_soul = "You are an assistant specializing only in code refactoring."
    prompt = build_system_prompt(PromptOptions(soul_override=custom_soul))
    assert custom_soul in prompt
    assert DEFAULT_LOCUS_SOUL not in prompt
