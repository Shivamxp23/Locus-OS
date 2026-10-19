"""
Unit tests for SPEC §10.3, §10.5, §10.6-10.7: Learning, Profiling, Reward Model, Hebbian & Pattern Engine (F-0035 / US-27).
Asserts stability detection, user profile generation, tool tracking, personal reward scoring,
Hebbian plasticity with STDP, multi-horizon promotion, and modular off-switch.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Dict
import pytest

from sidecar.learning.learning_system import UnifiedLearningProvider
from sidecar.providers.learning import LearningCandidate, PatternHorizon, StableFacet


@pytest.fixture
def tmp_profile(tmp_path: Path) -> Path:
    return tmp_path / "PROFILE.md"


def test_stability_detection_convergence(tmp_profile: Path) -> None:
    """SPEC §10.3 line 2945: "recent = learning_buffer.drain_recent(window=30_minutes)"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": True},
        profile_path=tmp_profile,
    )
    now = time.time()

    # If < 3 candidates, returns empty
    provider._candidates.clear()
    provider.record_candidate(LearningCandidate("workflow", "explicit_ask", {"snippet": "git tags"}, now, value="git tags"))
    assert len(provider.check_stability(window_seconds=1800, threshold=0.7)) == 0

    # Add 2 more consistent candidates
    provider.record_candidate(LearningCandidate("workflow", "explicit_ask", {"snippet": "git tags"}, now + 1, value="git tags"))
    provider.record_candidate(LearningCandidate("workflow", "explicit_ask", {"snippet": "git tags"}, now + 2, value="git tags"))

    stabilized = provider.check_stability(window_seconds=1800, threshold=0.7)
    assert len(stabilized) >= 1
    facet = stabilized[0]
    assert facet.facet_class == "workflow"
    assert facet.value == "git tags"
    assert facet.confidence >= 0.7
    assert facet.evidence_count >= 3


def test_user_profile_markdown_generation(tmp_profile: Path) -> None:
    """SPEC §10.3 line 2974: "profile_md = render_profile_markdown(facets)"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": True},
        profile_path=tmp_profile,
    )
    provider._stable_facets.clear()
    provider._stable_facets["tone:concise"] = StableFacet(
        facet_class="tone",
        key="tone:concise",
        value="prefer concise and terse answers",
        confidence=0.95,
        evidence_count=8,
        last_updated=time.time(),
    )

    md = provider.generate_profile_markdown()
    assert "# Locus User Profile" in md
    assert "Tone Facets" in md
    assert "prefer concise and terse answers" in md
    assert "0.95" in md


def test_tool_usage_tracking(tmp_profile: Path) -> None:
    """SPEC §10.3 line 2959: "FUNCTION on_tool_call(tool_name, args, result, duration):"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": True},
        profile_path=tmp_profile,
    )
    rec = provider.record_tool_usage(
        tool_name="locus_vault",
        args={"action": "read", "path": "01-Projects/Test.md"},
        success=True,
        duration_ms=42.5,
    )
    assert rec.tool_name == "locus_vault"
    assert len(rec.args_hash) == 16
    assert rec.success is True
    assert rec.duration_ms == 42.5


def test_personal_reward_model_scoring(tmp_profile: Path) -> None:
    """SPEC §10.5 line 6234: "THRESHOLD: ≥ 0.6 for proactive output delivery"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": True},
        profile_path=tmp_profile,
    )
    # Record thumbs up reactions
    provider.record_reward_signal(features={"dcs_at_response": 85.0}, label=1)
    provider.record_reward_signal(features={"dcs_at_response": 90.0}, label=1)

    high_confidence_thought = {
        "dcs_at_response": 85.0,
        "confidence": 0.85,
        "was_proactive": True,
        "context_forge_tokens_used": 600,
    }
    score = provider.score_thought(high_confidence_thought)
    assert 0.0 <= score <= 1.0
    assert score >= 0.60  # Passes proactive output threshold


def test_hebbian_pathway_access_and_feedback(tmp_profile: Path) -> None:
    """SPEC §10.6 line 6255: "edge.weight += 0.1  // access reinforcement"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": True},
        profile_path=tmp_profile,
    )
    edge_id = "test-edge-1"
    provider._edge_weights[edge_id] = 1.0

    # Access reinforcement
    w1 = provider.update_edge_weight(edge_id)
    assert w1 == 1.1

    # Positive feedback boost (* 1.3)
    w2 = provider.update_edge_weight(edge_id, feedback="positive")
    # (1.1 + 0.1) * 1.3 = 1.2 * 1.3 = 1.56
    assert abs(w2 - 1.56) < 0.01

    # Negative feedback penalty (* 0.7)
    w3 = provider.update_edge_weight(edge_id, feedback="negative")
    # (1.56 + 0.1) * 0.7 = 1.66 * 0.7 = 1.162
    assert abs(w3 - 1.162) < 0.01


def test_stdp_reinforcement_timing(tmp_profile: Path) -> None:
    """SPEC §10.6 line 6271: "edge.weight *= 1.5  // strong reinforcement"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": True},
        profile_path=tmp_profile,
    )
    edge_id = "test-stdp-edge"
    provider._edge_weights[edge_id] = 1.0

    # User response within 2 minutes (< 120,000 ms) -> 1.5x boost
    w_fast = provider.update_edge_weight(edge_id, response_time_ms=60000)
    # (1.0 + 0.1) * 1.5 = 1.65
    assert abs(w_fast - 1.65) < 0.01

    # Weekly decay 5%
    provider.apply_weekly_decay(decay_rate=0.95)
    assert abs(provider._edge_weights[edge_id] - (1.65 * 0.95)) < 0.01


def test_multi_horizon_pattern_promotion(tmp_profile: Path) -> None:
    """SPEC §10.7 line 6299: "IF pattern.confidence > 0.75 AND pattern.count > 2:"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": True},
        profile_path=tmp_profile,
    )
    provider._tool_usage.clear()
    now = time.time()

    # Simulate 5 tool usages of memory within 1 hour (falls into H1)
    for _ in range(5):
        provider.record_tool_usage("memory", {"query": "project"}, True, 20.0)

    patterns = provider.detect_patterns()
    assert len(patterns) >= 1
    # Check that promotion to H2 occurred
    h2_patterns = [p for p in patterns if p.horizon == PatternHorizon.H2_24_HOURS and "promoted_from" in p.details]
    assert len(h2_patterns) >= 1
    assert h2_patterns[0].count >= 3
    assert h2_patterns[0].confidence > 0.75


def test_learning_off_switch(tmp_profile: Path) -> None:
    """SPEC §10.1 line 2863: "skip_memory = true,   // don't recursively trigger memory writes"."""
    provider = UnifiedLearningProvider(
        custom_config={"locus.learning_profiling_reward_model.enabled": False},
        profile_path=tmp_profile,
    )
    assert provider.is_enabled() is False

    provider.record_candidate(LearningCandidate("test", "test", {}, time.time()))
    assert len(provider.check_stability()) == 0
    assert provider.score_thought({}) == 0.5
