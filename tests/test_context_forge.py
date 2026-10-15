"""tests/test_context_forge.py - Unit & Integration Tests for Context Forge.

Tests Spec §2.5:
- 6-Layer context assembly within hard 800 token budget.
- Protection of Layer 1 (Identity) and Layer 2 (Temporal Context) from truncation.
- Headroom CCR compression of compressible layers when total exceeds 800 tokens.
- Protocol conformance: ContextForge satisfies ContextAssembler protocol.
- Modularity switch: locus.context_forge.enabled=False.
"""

import pytest

from sidecar.context_forge import (
    ANTI_HALLUCINATION_HEADER,
    LOCUS_SHORTHAND_DICTIONARY,
    AssembledContext,
    ContextAssembler,
    ContextForge,
    ContextLayers,
)


def test_context_forge_protocol_conformance():
    forge = ContextForge()
    assert isinstance(forge, ContextAssembler)


def test_context_forge_assembly_under_budget():
    forge = ContextForge(enabled=True)
    layers = ContextLayers(
        identity="Goal: Finish Locus OS. Peak window: morning.",
        temporal="Time: 2027-05-14 10:00 IST. Mode: PEAK. DCS: 8.5.",
        events="{✓:coding_sprint,dur:60,q:9}",
        neo4j_paths="task_A → outcome_B (w:0.85)",
        semantic="Locus architecture relies on sidecar FastAPI and Pi extension.",
        web="Python 3.14 release schedule overview.",
    )

    ctx = forge.assemble(layers)

    assert ANTI_HALLUCINATION_HEADER in ctx.context_text
    assert LOCUS_SHORTHAND_DICTIONARY in ctx.context_text
    assert "Finish Locus OS" in ctx.context_text
    assert "PEAK" in ctx.context_text
    assert ctx.total_tokens_est <= 800
    assert ctx.compressed is False
    assert len(ctx.layers_included) == 6


def test_context_forge_protection_and_compression():
    forge = ContextForge(enabled=True)
    # Huge compressible content
    large_events = "event_data_" * 200
    large_semantic = "semantic_vector_content_" * 300
    large_web = "web_search_snippet_" * 150

    layers = ContextLayers(
        identity="Protected Identity String 12345",
        temporal="Protected Temporal String 67890",
        events=large_events,
        neo4j_paths="task_X → outcome_Y",
        semantic=large_semantic,
        web=large_web,
    )

    ctx = forge.assemble(layers)

    # Hard budget enforced
    assert ctx.total_tokens_est <= 800
    assert ctx.compressed is True
    # Protected layers MUST remain intact
    assert "Protected Identity String 12345" in ctx.context_text
    assert "Protected Temporal String 67890" in ctx.context_text


def test_context_forge_modularity_disabled():
    forge = ContextForge(enabled=False)
    layers = ContextLayers(identity="Identity string")
    ctx = forge.assemble(layers)

    assert ctx.context_text == ""
    assert ctx.total_tokens_est == 0
    assert ctx.metadata.get("disabled") is True
