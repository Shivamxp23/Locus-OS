"""
Unit tests for Subagent Archetypes, Spawning Lifecycle, Depth Limiting, and AutoResearch.
SPEC §11.1-11.5 + §3.7 / F-0036.
"""
from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from sidecar import config
from sidecar.providers.subagents import (
    ArchetypeCategory,
    AutoResearchRequest,
    BaseSubagentProvider,
    SubagentSpawnRequest,
)
from sidecar.subagents import MAX_SPAWN_DEPTH, SubagentProvider


def test_base_provider_contract():
    """SPEC modularity architecture (03): SubagentProvider must inherit from BaseSubagentProvider."""
    provider = SubagentProvider()
    assert isinstance(provider, BaseSubagentProvider)
    assert provider.MAX_SPAWN_DEPTH == 3
    assert provider.is_enabled() is True


def test_provider_universal_lifecycle():
    """Universal lifecycle: initialize, health_check, shutdown."""
    provider = SubagentProvider()
    provider.initialize()
    health = provider.health_check()

    assert health["status"] == "healthy"
    assert health["initialized"] is True
    assert health["max_spawn_depth"] == 3
    assert health["archetype_count"] >= 19
    assert "planner" in health["factions"]
    assert "curator" in health["factions"]
    assert "analyst" in health["factions"]
    assert "builder" in health["factions"]

    provider.shutdown()
    assert provider._initialized is False


def test_locus_four_factions():
    """SPEC §11.1: Locus 4 Faction Agents: Planner, Curator, Analyst, Builder."""
    provider = SubagentProvider()
    factions = provider.list_archetypes(category="faction")
    assert len(factions) == 4
    faction_names = {f.name for f in factions}
    assert faction_names == {"planner", "curator", "analyst", "builder"}

    planner = provider.get_archetype("planner")
    assert planner is not None
    assert "locus_goals" in planner.allowed_tools

    builder = provider.get_archetype("builder")
    assert builder is not None
    assert "locus_delegate_code" in builder.allowed_tools


def test_openhuman_fifteen_archetypes():
    """SPEC §11.1: OpenHuman 15 Archetypes."""
    provider = SubagentProvider()
    openhuman = provider.list_archetypes(category="openhuman")
    assert len(openhuman) == 15
    oh_names = {a.name for a in openhuman}

    expected_oh = {
        "orchestrator",
        "researcher",
        "critic",
        "implementer",
        "debugger",
        "reviewer",
        "documenter",
        "tester",
        "deployer",
        "security_auditor",
        "performance_analyst",
        "data_engineer",
        "designer",
        "communicator",
        "oh_planner",
    }
    assert oh_names == expected_oh


def test_subagent_spawning_lifecycle():
    """SPEC §11.1: Spawns subagent with skip_memory=True, skip_review=True, depth incremented."""
    provider = SubagentProvider()
    req = SubagentSpawnRequest(
        task="Draft quarterly roadmap milestones",
        archetype="planner",
        parent_session_id="session-root-123",
        current_depth=0,
    )
    res = provider.spawn_subagent(req)

    assert res.parent_session_id == "session-root-123"
    assert res.depth == 1
    assert res.archetype == "planner"
    assert res.status == "completed"
    assert res.skip_memory is True
    assert res.skip_review is True
    assert "PLANNER SUBAGENT" in res.output


def test_depth_limiting_enforcement():
    """SPEC §11.1: Enforces MAX_SPAWN_DEPTH = 3 strictly."""
    provider = SubagentProvider()

    # Depth 0 -> 1 is allowed
    res1 = provider.spawn_subagent(SubagentSpawnRequest(task="T1", archetype="curator", current_depth=0))
    assert res1.depth == 1

    # Depth 1 -> 2 is allowed
    res2 = provider.spawn_subagent(SubagentSpawnRequest(task="T2", archetype="curator", current_depth=1))
    assert res2.depth == 2

    # Depth 2 -> 3 is allowed
    res3 = provider.spawn_subagent(SubagentSpawnRequest(task="T3", archetype="curator", current_depth=2))
    assert res3.depth == 3

    # Depth 3 -> 4 exceeds MAX_SPAWN_DEPTH (3) and must raise ValueError
    with pytest.raises(ValueError) as excinfo:
        provider.spawn_subagent(SubagentSpawnRequest(task="T4", archetype="curator", current_depth=3))
    assert "Maximum subagent depth reached" in str(excinfo.value)

    # Depth 5 exceeds MAX_SPAWN_DEPTH (3)
    with pytest.raises(ValueError) as excinfo2:
        provider.spawn_subagent(SubagentSpawnRequest(task="T5", archetype="curator", current_depth=5))
    assert "Maximum subagent depth reached" in str(excinfo2.value)


def test_unknown_archetype_raises():
    """Attempting to spawn an unmapped archetype raises KeyError."""
    provider = SubagentProvider()
    with pytest.raises(KeyError) as excinfo:
        provider.spawn_subagent(SubagentSpawnRequest(task="T", archetype="non_existent_archetype"))
    assert "non_existent_archetype" in str(excinfo.value)


def test_memory_delegation_callback():
    """SPEC §11.1 line 6476: memory_provider.on_delegation(task, result, child_session_id)."""
    provider = SubagentProvider()
    callback = MagicMock()
    req = SubagentSpawnRequest(
        task="Audit token allocation",
        archetype="analyst",
        parent_session_id="root-sess",
        current_depth=1,
    )
    res = provider.spawn_subagent(req, memory_callback=callback)

    assert res.depth == 2
    callback.assert_called_once()
    args, _ = callback.call_args
    assert args[0] == "Audit token allocation"
    assert args[1]["session_id"] == res.session_id
    assert args[2] == res.session_id


def test_autoresearch_quick_mode():
    """AutoResearch in quick mode runs primary researcher subagent."""
    provider = SubagentProvider()
    req = AutoResearchRequest(topic="Vector embedding quantization methods", depth_mode="quick")
    res = provider.execute_autoresearch(req)

    assert res.status == "completed"
    assert res.topic == "Vector embedding quantization methods"
    assert res.subagents_spawned == 1
    assert len(res.findings) == 1
    assert res.findings[0]["archetype"] == "researcher"


def test_autoresearch_deep_mode_with_hypotheses():
    """AutoResearch in deep mode investigates hypotheses across multiple subagents."""
    provider = SubagentProvider()
    req = AutoResearchRequest(
        topic="SQLite WAL mode concurrency under high write contention",
        depth_mode="deep",
        hypotheses=["WAL mode eliminates writer starvation", "Memory mapping lowers page faults"],
    )
    res = provider.execute_autoresearch(req)

    assert res.status == "completed"
    assert res.subagents_spawned >= 3
    assert len(res.findings) >= 3
    archetypes = [f["archetype"] for f in res.findings]
    assert "researcher" in archetypes
    assert "analyst" in archetypes
    assert "critic" in archetypes


def test_autoresearch_empty_topic_raises():
    """AutoResearch with empty topic raises ValueError."""
    provider = SubagentProvider()
    req = AutoResearchRequest(topic="")
    with pytest.raises(ValueError):
        provider.execute_autoresearch(req)


def test_modular_off_switch():
    """SPEC §03 line 11: Modular off-switch disables provider and returns disabled state."""
    provider = SubagentProvider()
    config.set("locus.subagents_autoresearch.enabled", False)
    try:
        assert provider.is_enabled() is False
        health = provider.health_check()
        assert health["status"] == "disabled"

        with pytest.raises(RuntimeError) as excinfo:
            provider.spawn_subagent(SubagentSpawnRequest(task="T", archetype="planner"))
        assert "subagents_autoresearch_disabled" in str(excinfo.value)

        with pytest.raises(RuntimeError) as excinfo2:
            provider.execute_autoresearch(AutoResearchRequest(topic="AI"))
        assert "subagents_autoresearch_disabled" in str(excinfo2.value)
    finally:
        config.set("locus.subagents_autoresearch.enabled", True)
