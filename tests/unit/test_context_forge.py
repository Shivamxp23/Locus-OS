"""
Unit tests for Context Forge (Stage 6) — The 6-Layer Assembler (F-0094 / US-34).
Asserts provider registration, global relevance scoring, layer budgeting,
Headroom CCR compression, Hebbian edge weight updates, and modular off-switch.
"""
from __future__ import annotations

import time
import pytest

import sidecar.config as config
from sidecar.registry import get_registry
from sidecar.providers.context_forge import (
    ANTI_HALLUCINATION_INSTRUCTION,
    AssembledLayer,
    BaseContextForgeProvider,
    ContextForgeResult,
    LOCUS_SHORTHAND_DICTIONARY,
    LayerBudgetConfig,
    RetrievalInput,
    SOURCE_PRIORITIES,
)
from sidecar.context_forge import ContextForgeProvider, estimate_tokens, truncate_to_tokens


@pytest.fixture(autouse=True)
def clean_config():
    """Ensure clean configuration state for each test."""
    original_enabled = config.get("locus.brain.context_forge.enabled")
    original_legacy = config.get("locus.context_forge.enabled")
    original_layers = config.get("locus.brain.context_forge.layers")
    config.set("locus.brain.context_forge.enabled", True)
    config.set("locus.context_forge.enabled", True)
    yield
    config.set("locus.brain.context_forge.enabled", original_enabled)
    config.set("locus.context_forge.enabled", original_legacy)
    config.set("locus.brain.context_forge.layers", original_layers)


def test_context_forge_provider_registration():
    """
    SPEC §2.5 line 1805: "Provider Interface: Implements ContextAssembler"
    """
    registry = get_registry()
    provider_cls = registry.get_active_provider("context_forge", default_name="default")
    assert provider_cls is not None, "Context Forge provider should be registered in registry"
    provider = provider_cls()
    assert isinstance(provider, BaseContextForgeProvider)
    assert provider.is_enabled() is True


def test_global_relevance_scoring_formula():
    """
    SPEC §2.5 line 1765: "Unified Score = (semantic_similarity × 0.6) + (recency_weight × 0.25) + (source_priority × 0.15)"
    """
    provider = ContextForgeProvider()
    score = provider.calculate_relevance_score(
        semantic_similarity=0.8,
        recency_weight=1.0,
        source_priority=0.4,
    )
    # Expected: (0.8 * 0.6) + (1.0 * 0.25) + (0.4 * 0.15) = 0.48 + 0.25 + 0.06 = 0.79
    assert score == pytest.approx(0.79, rel=1e-3)


def test_source_priorities_values():
    """
    SPEC §2.5 line 1766: "Source priority: Neo4j pathways (0.4) > PG facts (0.3) > pgvector (0.2) > Web (0.1)"
    """
    provider = ContextForgeProvider()
    assert provider.get_source_priority("neo4j") == 0.4
    assert provider.get_source_priority("pg") == 0.3
    assert provider.get_source_priority("pgvector") == 0.2
    assert provider.get_source_priority("web") == 0.1
    assert provider.get_source_priority("unknown") == 0.1


def test_recency_weight_thresholds():
    """
    SPEC §2.5 line 1767: "Recency weight: last 6h = 1.0, last 24h = 0.8, last 7d = 0.5, older = 0.2."
    """
    provider = ContextForgeProvider()
    assert provider.calculate_recency_weight(2 * 3600) == 1.0  # 2h <= 6h
    assert provider.calculate_recency_weight(12 * 3600) == 0.8  # 12h <= 24h
    assert provider.calculate_recency_weight(3 * 86400) == 0.5  # 3d <= 7d
    assert provider.calculate_recency_weight(10 * 86400) == 0.2  # 10d > 7d


def test_layer_budgets_defaults_and_override():
    """
    SPEC §2.5 line 1807: "Layer Budgets: Configurable via locus.brain.context_forge.layers (Identity 80t, Temporal 60t, Events 180t, Neo4j 150t, pgvector 200t, Web 100t; Hard total limit: 800 tokens)."
    """
    default_budgets = LayerBudgetConfig()
    assert default_budgets.identity_limit == 80
    assert default_budgets.temporal_limit == 60
    assert default_budgets.events_limit == 180
    assert default_budgets.neo4j_limit == 150
    assert default_budgets.semantic_limit == 200
    assert default_budgets.web_limit == 100
    assert default_budgets.total_limit == 800

    custom = LayerBudgetConfig.from_dict({
        "identity_limit": 100,
        "total_limit": 900,
    })
    assert custom.identity_limit == 100
    assert custom.total_limit == 900


def test_neo4j_pathways_and_hebbian_increment():
    """
    SPEC §2.5 line 1792: "For every Neo4j path included in Layer 4, increment edge weights by +0.1 in Neo4j (Hebbian traversal signal)."
    """
    provider = ContextForgeProvider()
    input_data = RetrievalInput(
        neo4j_paths=[
            {"from_node": "task_A", "to_node": "behavior_B", "weight": 0.84, "path_str": "task_A → behavior_B (w:0.84) → outcome_C"},
            {"from_node": "low_A", "to_node": "low_B", "weight": 0.20, "path_str": "low_A → low_B (w:0.20)"},  # Should be filtered out (weight <= 0.3)
        ]
    )
    result = provider.assemble_context(input_data)
    # Check that low weight path was excluded
    assert "low_A" not in result.assembled_prompt
    assert "task_A" in result.assembled_prompt

    # Check Hebbian update
    assert len(result.hebbian_updates) == 1
    update = result.hebbian_updates[0]
    assert update["old_weight"] == 0.84
    assert update["new_weight"] == 0.94


def test_headroom_compression_never_truncates_layers_1_and_2():
    """
    SPEC §2.5 line 1789: "Layers 1 & 2 are NEVER truncated."
    """
    provider = ContextForgeProvider()
    # Create large contents that exceed total_limit (800)
    identity_data = {
        "life_goals": ["Build personal cognitive operating system", "Master systems programming"],
        "active_factions": ["Architect", "Scientist"],
    }
    temporal_data = {
        "operating_mode": "DEEP_WORK",
        "dcs": 8.5,
        "active_exam_flags": ["Finals_Q4"],
    }
    large_events = [
        {"task": f"Deep task {i} with extensive descriptions of all operations", "dur": 60, "q": 9}
        for i in range(20)
    ]
    large_semantic = [
        {"text": f"Semantic memory chunk {i}: Extensive historical trajectory logs and cognitive models " * 4, "similarity": 0.9}
        for i in range(10)
    ]

    input_data = RetrievalInput(
        identity=identity_data,
        temporal=temporal_data,
        events=large_events,
        semantic_snippets=large_semantic,
    )

    # Set total_limit to 300 so that uncompressed layers (396 tokens) exceed the total headroom limit
    budget = LayerBudgetConfig(total_limit=300)
    result = provider.assemble_context(input_data, budget_override=budget)
    assert result.total_tokens <= 300
    assert result.compression_applied is True

    # Layer 1 and Layer 2 must NOT be empty or truncated away
    l1 = next(l for l in result.layers if l.layer_num == 1)
    l2 = next(l for l in result.layers if l.layer_num == 2)
    assert l1.token_count > 0
    assert "Build personal cognitive operating system" in l1.content
    assert l2.token_count > 0
    assert "DEEP_WORK" in l2.content


def test_anti_hallucination_and_locus_shorthand_prepended():
    """
    SPEC §2.5 line 1795: "Prepends identity system prompt + LOCUS_SHORTHAND decoder dictionary + strict anti-hallucination instruction:"
    """
    provider = ContextForgeProvider()
    input_data = RetrievalInput(
        identity={"life_goals": ["Continuous learning"]},
        temporal={"operating_mode": "NORMAL", "dcs": 6.0},
    )
    result = provider.assemble_context(input_data)
    prompt = result.assembled_prompt

    assert ANTI_HALLUCINATION_INSTRUCTION in prompt
    assert "LOCUS_SHORTHAND:" in prompt
    assert "You are Locus OS" in prompt
    assert "--- BEGIN CONTEXT BLOCK ---" in prompt
    assert "--- END CONTEXT BLOCK ---" in prompt


def test_web_results_conditional_injection():
    """
    SPEC §2.5 line 1784: "Populated ONLY if intent requires external knowledge or retrieval returned empty. Top 3 snippets."
    """
    provider = ContextForgeProvider()
    web_items = [
        {"snippet": f"Web knowledge snippet {i}"} for i in range(5)
    ]

    # Case 1: has other retrievals and intent_requires_web is False -> Web layer empty
    res_no_web = provider.assemble_context(RetrievalInput(
        events=[{"task": "coding", "dur": 30, "q": 8}],
        web_results=web_items,
        intent_requires_web=False,
    ))
    l6_no_web = next(l for l in res_no_web.layers if l.layer_num == 6)
    assert l6_no_web.token_count == 0

    # Case 2: intent_requires_web is True -> Web layer populated with top 3
    res_with_web = provider.assemble_context(RetrievalInput(
        events=[{"task": "coding", "dur": 30, "q": 8}],
        web_results=web_items,
        intent_requires_web=True,
    ))
    l6_with_web = next(l for l in res_with_web.layers if l.layer_num == 6)
    assert l6_with_web.token_count > 0
    assert "Web knowledge snippet 0" in l6_with_web.content
    assert "Web knowledge snippet 2" in l6_with_web.content
    assert "Web knowledge snippet 4" not in l6_with_web.content  # Top 3 limit


def test_context_forge_modular_off_switch():
    """
    SPEC §2.5 line 1799: "Delivers complete <=800 token context block + metadata to Conductor."
    """
    provider = ContextForgeProvider()
    config.set("locus.brain.context_forge.enabled", False)
    assert provider.is_enabled() is False

    with pytest.raises(RuntimeError, match="disabled by configuration"):
        provider.assemble_context(RetrievalInput())


def test_context_forge_swap_provider():
    """
    SPEC §2.5 line 1805: "Provider Interface: Implements ContextAssembler"
    """
    registry = get_registry()

    class CustomMockForge(BaseContextForgeProvider):
        def assemble_context(self, retrieval_input, budget_override=None):
            return ContextForgeResult(
                assembled_prompt="MOCK ASSEMBLED CONTEXT",
                layers=[],
                total_tokens=3,
                compression_applied=False,
                hebbian_updates=[],
                metadata={"mock": True},
            )

        def calculate_relevance_score(self, sem, rec, src):
            return 1.0

        def is_enabled(self):
            return True

    registry.register("context_forge", "custom_mock", CustomMockForge)
    config.set("locus.context_forge.provider", "custom_mock")
    try:
        active_cls = registry.get_active_provider("context_forge", default_name="default")
        assert active_cls is CustomMockForge
        active_provider = active_cls()
        res = active_provider.assemble_context(RetrievalInput())
        assert res.assembled_prompt == "MOCK ASSEMBLED CONTEXT"
        assert res.metadata.get("mock") is True
    finally:
        config.set("locus.context_forge.provider", "default")
