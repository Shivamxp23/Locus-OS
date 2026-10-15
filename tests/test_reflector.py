import pytest
from sidecar.learning.reflector import (
    ALLOWED_REVIEW_TOOLS,
    ReviewInsight,
    ReviewResult,
    TurnReflector,
    spawn_background_review,
)


def test_tool_whitelist_enforcement():
    reflector = TurnReflector()
    assert reflector.is_tool_allowed("memory")
    assert reflector.is_tool_allowed("skill_manage")
    assert not reflector.is_tool_allowed("bash")
    assert not reflector.is_tool_allowed("edit")
    assert not reflector.is_tool_allowed("write")


def test_insight_extraction():
    reflector = TurnReflector()
    messages = [
        {"role": "user", "content": "I prefer TypeScript over Python for frontend components."},
        {"role": "assistant", "content": "Understood."},
        {"role": "user", "content": "Remember to use single quotes in markdown tables convention."},
    ]
    res = reflector.review_turn(session_id="s1", turn_id="t1", messages=messages)

    assert res is not None
    assert len(res.insights_extracted) == 2
    cats = {i.category for i in res.insights_extracted}
    assert "preference" in cats
    assert "skill" in cats
    assert len(res.skills_updated) == 1


def test_spawn_background_review():
    messages = [{"role": "user", "content": "Standard message with no cues."}]
    res = spawn_background_review("s1", "t1", messages)
    assert res is not None
    assert len(res.insights_extracted) == 0
