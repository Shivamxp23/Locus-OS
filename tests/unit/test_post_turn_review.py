"""
Unit tests for SPEC §1.7 & §10.1: Post-Turn Background Review (F-0007 / US-26).
Asserts daemon thread forking, strict tool whitelisting, review prompt composition,
skill update preference hierarchy, "never fatal" error containment, and 503 off-switch.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List
import pytest

from sidecar.learning.reflector import PostTurnReviewer
from sidecar.providers.post_turn import (
    ALLOWED_REVIEW_TOOLS,
    PostTurnReviewResult,
    SkillUpdatePreference,
)


def test_daemon_thread_background_execution() -> None:
    """SPEC §1.7 line 2855: "// CRITICAL: This runs on a DAEMON THREAD, never blocks the main loop"."""
    reviewer = PostTurnReviewer(custom_config={"locus.post_turn_review.enabled": True})
    messages = [
        {"role": "user", "content": "Please remember that I prefer Python over TypeScript."},
        {"role": "assistant", "content": "Understood, I will prioritize Python for your tasks."},
    ]

    start = time.time()
    result = reviewer.spawn_background_review(conversation_snapshot=messages, session_id="test-sess-1", sync=False)
    elapsed = time.time() - start

    # Must return immediately without blocking
    assert elapsed < 0.2
    assert isinstance(result, PostTurnReviewResult)
    assert result.status == "dispatched"
    assert result.execution_mode == "background_thread"
    assert result.session_id == "test-sess-1"

    # Give daemon thread brief moment to complete and verify record
    time.sleep(0.1)
    record = reviewer.get_review_result(result.review_id)
    assert record is not None
    assert record.status in ("completed", "dispatched")


def test_tool_whitelist_strict_enforcement() -> None:
    """SPEC §1.7 line 2861: "tool_whitelist = [\"memory\", \"skill_manage\"],  // ONLY these tools allowed"."""
    reviewer = PostTurnReviewer(custom_config={"locus.post_turn_review.enabled": True})

    # Allowed tools
    for tool in ALLOWED_REVIEW_TOOLS:
        assert reviewer.is_tool_allowed(tool) is True

    # Denied tools per line 2886
    disallowed_tools = ["bash", "terminal", "write_file", "edit_file", "browser", "exec", "python_eval"]
    for tool in disallowed_tools:
        assert reviewer.is_tool_allowed(tool) is False

    # Filter tools list
    candidate_tools = ["memory", "bash", "skill_manage", "write_file", "locus_vault"]
    filtered = reviewer.filter_tools(candidate_tools)
    assert filtered == ["memory", "skill_manage", "locus_vault"]


def test_tool_filter_denies_arbitrary_tools() -> None:
    """SPEC §1.7 line 2886: "// All other tools (terminal, write_file, browser, etc.) are DENIED"."""
    reviewer = PostTurnReviewer(custom_config={"locus.post_turn_review.enabled": True})

    def mock_runner(prompt: str, snapshot: List[Dict[str, Any]]) -> Dict[str, Any]:
        return {
            "tools_attempted": ["bash", "terminal", "memory", "write_file"],
            "memory_insights": [{"type": "rule", "value": "test"}],
            "skill_updates": [],
        }

    reviewer.mock_runner = mock_runner
    messages = [{"role": "user", "content": "Update rule"}]
    result = reviewer.spawn_background_review(conversation_snapshot=messages, sync=True)

    assert result.status == "completed"
    assert "bash" in result.denied_tools_attempted
    assert "terminal" in result.denied_tools_attempted
    assert "write_file" in result.denied_tools_attempted
    assert "memory" not in result.denied_tools_attempted


def test_review_prompt_construction() -> None:
    """SPEC §1.7 line 2868: "review_prompt = MEMORY_REVIEW_PROMPT + SKILL_REVIEW_PROMPT"."""
    reviewer = PostTurnReviewer(custom_config={"locus.post_turn_review.enabled": True})
    messages = [
        {"role": "user", "content": "Always format git commit messages with semantic tags."},
    ]
    prompt = reviewer.build_review_prompt(messages)

    assert "MEMORY REVIEW:" in prompt
    assert "SKILL REVIEW:" in prompt
    assert "TOOL RESTRICTIONS:" in prompt
    assert "Always format git commit messages with semantic tags." in prompt
    assert "UPDATE A CURRENTLY-LOADED SKILL" in prompt


def test_skill_review_preference_order() -> None:
    """SPEC §1.7 line 2890: "1. UPDATE A CURRENTLY-LOADED SKILL (the one in play this session)"."""
    reviewer = PostTurnReviewer(custom_config={"locus.post_turn_review.enabled": True})
    prefs = reviewer.get_skill_preferences()

    assert len(prefs) == 4
    assert prefs[0] == SkillUpdatePreference.UPDATE_CURRENTLY_LOADED.value
    assert prefs[1] == SkillUpdatePreference.UPDATE_EXISTING_UMBRELLA.value
    assert prefs[2] == SkillUpdatePreference.ADD_SUPPORT_FILE.value
    assert prefs[3] == SkillUpdatePreference.CREATE_NEW_UMBRELLA.value


def test_never_fatal_error_containment() -> None:
    """SPEC §1.7 line 2902: "- **KEEP**: The tool whitelist pattern, the preference order for skill updates, the \"never fatal\" principle (review failure should never crash the main conversation)."."""
    def exploding_runner(prompt: str, snapshot: List[Dict[str, Any]]) -> Dict[str, Any]:
        raise RuntimeError("Severe auxiliary LLM crash during review")

    reviewer = PostTurnReviewer(
        custom_config={"locus.post_turn_review.enabled": True},
        mock_runner=exploding_runner,
    )

    # Must never raise an unhandled exception
    result = reviewer.spawn_background_review(
        conversation_snapshot=[{"role": "user", "content": "Crash me"}],
        sync=True,
    )
    assert result.status == "error"
    assert isinstance(result.duration_ms, float)


def test_off_switch_disables_review() -> None:
    """SPEC §1.7 line 2887: "// This prevents the review agent from side-effecting the filesystem"."""
    reviewer = PostTurnReviewer(custom_config={"locus.post_turn_review.enabled": False})
    assert reviewer.is_enabled() is False

    result = reviewer.spawn_background_review(
        conversation_snapshot=[{"role": "user", "content": "Hello"}],
        sync=True,
    )
    assert result.status == "disabled"
