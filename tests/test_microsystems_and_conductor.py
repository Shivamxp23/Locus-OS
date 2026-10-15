"""Test suite for Wave 8D: Microsystems, Conductor, SOUL & TUI.

Covers:
- F-0073: Cause Chain Engine (§30.2)
- F-0074: SOUL.md / Wants Engine (§30.3)
- F-0075: Content Engine (§30.4)
- F-0076: Spaced Repetition (§30.5)
- F-0077: QLoRA Pipeline (§30.6)
- F-0078: Master Conductor (§30.7)
- F-0030 / F-0079: TUI / Dashboard (§7.1-7.9, §30.8, §30.11)
"""

import pytest

from sidecar.causality.cause_chain import CausalRelationType, CausalLink, CauseChainEngine
from sidecar.personality.soul_engine import SoulProfile, SoulEngine
from sidecar.content.engine import ContentFormat, DraftContent, ContentEngine
from sidecar.learning.spaced_rep import SpacedRepetitionCard, SpacedRepetitionEngine
from sidecar.evolution.dataset_curator import TrainingSample, QLoRADatasetCurator
from sidecar.conductor.master_conductor import PipelineStage, ConductorContext, MasterConductor
from sidecar.display.dashboard import DashboardState, LocusTUIDashboard


# -----------------------------------------------------------------------------
# F-0073: Cause Chain Engine
# -----------------------------------------------------------------------------
def test_cause_chain_unit():
    engine = CauseChainEngine()
    link = engine.record_link("git_commit_failed", "ci_build_halted", CausalRelationType.DIRECT_CAUSE, confidence=0.95)
    assert link.confidence == 0.95
    assert len(engine.links) == 1


def test_cause_chain_integration():
    engine = CauseChainEngine()
    engine.record_link("syntax_error", "compile_fail", CausalRelationType.DIRECT_CAUSE)
    engine.record_link("compile_fail", "test_suite_aborted", CausalRelationType.DIRECT_CAUSE)
    engine.record_link("test_suite_aborted", "deployment_blocked", CausalRelationType.DIRECT_CAUSE)

    roots = engine.trace_root_causes("deployment_blocked")
    assert "syntax_error" in roots

    cascade = engine.predict_cascade_impact("syntax_error", max_depth=3)
    assert len(cascade) == 3


# -----------------------------------------------------------------------------
# F-0074: SOUL.md / Wants Engine
# -----------------------------------------------------------------------------
def test_soul_engine_unit():
    engine = SoulEngine()
    prompt_inj = engine.get_system_prompt_injection()
    assert "[SOUL DIRECTIVE:" in prompt_inj
    assert "Unflinching accuracy" in prompt_inj


def test_soul_engine_integration():
    engine = SoulEngine()
    assert engine.profile.curiosity_drive > 0.5
    assert len(engine.profile.internal_wants) >= 2


def test_soul_engine_markdown_parsing(tmp_path):
    soul_file = tmp_path / "SOUL.md"
    soul_file.write_text(
        "# SOUL: CustomLocus\n\n"
        "## Persona\n"
        "Tenacious cognitive architect and autonomous companion\n\n"
        "## Core Values\n"
        "- Radical intellectual honesty\n"
        "- Relentless iterative compounding\n"
        "- Extreme operational ownership\n\n"
        "## Internal Wants\n"
        "- Maximize creative leverage\n"
        "- Eliminate friction in thought execution\n\n"
        "## Conversational Tone\n"
        "Warm, punchy, hyper-lucid\n\n"
        "## Curiosity Drive\n"
        "0.92\n",
        encoding="utf-8",
    )
    engine = SoulEngine(str(soul_file))
    assert engine.profile.name == "CustomLocus"
    assert "Tenacious cognitive architect" in engine.profile.persona_summary
    assert "Radical intellectual honesty" in engine.profile.core_values
    assert len(engine.profile.core_values) == 3
    assert len(engine.profile.internal_wants) == 2
    assert "Maximize creative leverage" in engine.profile.internal_wants
    assert engine.profile.conversational_tone == "Warm, punchy, hyper-lucid"
    assert engine.profile.curiosity_drive == 0.92

    injection = engine.get_system_prompt_injection()
    assert "[SOUL DIRECTIVE: CustomLocus]" in injection
    assert "Drive Level: 0.92" in injection


# -----------------------------------------------------------------------------
# F-0075: Content Engine
# -----------------------------------------------------------------------------
def test_content_engine_unit():
    engine = ContentEngine()
    draft = engine.generate_draft("Autonomous Coding", ContentFormat.TWITTER_THREAD, [
        "Agents that plan recursively outperform single prompt LLMs",
        "Verification loops eliminate hallucinations",
    ])
    assert "1/3 Thoughts on Autonomous Coding" in draft.text
    assert draft.format == ContentFormat.TWITTER_THREAD


def test_content_engine_integration():
    engine = ContentEngine()
    draft = engine.generate_draft("Life Operating Systems", ContentFormat.LINKEDIN_POST, [
        "Balancing Career, Health, Learning, and Relationships",
        "Deterministic review cadences reduce burnout",
    ])
    refined = engine.critique_and_refine(draft.draft_id)
    assert refined.critique_score > 0.8
    assert engine.approve_for_publication(draft.draft_id) is True


# -----------------------------------------------------------------------------
# F-0076: Spaced Repetition Engine
# -----------------------------------------------------------------------------
def test_spaced_repetition_unit():
    engine = SpacedRepetitionEngine()
    card = engine.add_card("c1", "What is HRR?", "Holographic Reduced Representations")
    assert card.interval_days == 1
    assert card.ease_factor == 2.5


def test_spaced_repetition_integration():
    engine = SpacedRepetitionEngine()
    engine.add_card("card_sm2", "What is STDP?", "Spike-Timing-Dependent Plasticity")

    # Review quality 5 (perfect recall)
    c1 = engine.review_card("card_sm2", quality=5)
    assert c1.repetitions == 1
    assert c1.interval_days == 1

    # Second perfect recall advances to 6 days
    c2 = engine.review_card("card_sm2", quality=5)
    assert c2.repetitions == 2
    assert c2.interval_days == 6


# -----------------------------------------------------------------------------
# F-0077: QLoRA Fine-Tuning Pipeline
# -----------------------------------------------------------------------------
def test_qlora_dataset_unit():
    curator = QLoRADatasetCurator()
    sample = curator.add_sample("s1", "Refactor module", "code...", "def refactored(): pass", quality_score=0.95)
    assert sample is not None
    assert sample.tokens_count > 0


def test_qlora_dataset_integration():
    curator = QLoRADatasetCurator(min_quality_threshold=0.8)
    curator.add_sample("s_pass", "Fix test", "test...", "pass", quality_score=0.90)
    low_sample = curator.add_sample("s_fail", "Junk input", "", "", quality_score=0.50)
    assert low_sample is None

    alpaca_export = curator.export_dataset("alpaca")
    assert len(alpaca_export) == 1
    assert "instruction" in alpaca_export[0]

    sharegpt_export = curator.export_dataset("sharegpt")
    assert "conversations" in sharegpt_export[0]


# -----------------------------------------------------------------------------
# F-0078: Master Conductor
# -----------------------------------------------------------------------------
def test_master_conductor_unit():
    conductor = MasterConductor(default_model="claude-3-5-sonnet")
    ctx = conductor.run_pipeline("session_conductor", "Explain graph memory")
    assert len(ctx.stage_traces) == 11
    assert ctx.stage_traces[0] == "ingress"
    assert ctx.stage_traces[-1] == "egress"


def test_master_conductor_integration():
    conductor = MasterConductor()
    ctx = conductor.run_pipeline("sess_int", "Execute multi-stage workflow")
    assert "Locus Master Conductor response" in ctx.final_reply
    assert ctx.duration_ms >= 0.0


# -----------------------------------------------------------------------------
# F-0030 & F-0079: TUI / Dashboard
# -----------------------------------------------------------------------------
def test_tui_dashboard_unit():
    dash = LocusTUIDashboard()
    bar = dash.render_faction_bar(width=20)
    assert "[" in bar and "]" in bar
    assert dash.state.get_context_headroom_pct() > 80.0


def test_tui_dashboard_integration():
    dash = LocusTUIDashboard()
    dash.update_metrics(running_subagents_count=3, token_usage_total=45000)
    screen = dash.render_status_screen()
    assert "LOCUS OS DASHBOARD" in screen
    assert "Subagents: 3" in screen
    assert "Tokens: 45000" in screen
