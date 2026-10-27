"""
Unit tests for Rough Note Parser & Idea Tracker (F-0061 / US-98).
"""
from pathlib import Path
import pytest
from typing import Any, Dict, List, Optional

from sidecar import config
from sidecar.ingestion.rough_note_parser import (
    ParseRoughNoteResult,
    RoughNote,
    RoughNoteParser,
    slugify,
)
from sidecar.providers.rough_note_parser import (
    BaseRoughNoteParserProvider,
    DefaultRoughNoteParserProvider,
)


def test_slugify_utility():
    """
    SPEC §27.5 line 7243: "vault_path = f\"/vault/04-Captures/Inbox/{slugify(structured_json.title)}.md\""
    """
    assert slugify("Build Locus Architecture") == "build-locus-architecture"
    assert slugify("Feature 27.5: Rough Note / Idea Parser!") == "feature-275-rough-note-idea-parser"
    assert slugify("   Multiple   Spaces   ") == "multiple-spaces"
    assert slugify("") == "untitled-note"


def test_canonical_title_and_faction_tag_extraction():
    """
    SPEC §27.5 line 7210: "Extract: 1. Canonical Title (3-6 words) 2. Primary Faction Tag (#domain/craft, #domain/health, etc.)"
    """
    parser = RoughNoteParser()

    # Craft text
    craft_text = (
        "Refactor Locus Python API routes and Neo4j database models.\n"
        "Need to fix the FastAPI middleware and improve test coverage."
    )
    title_craft = parser.extract_title(craft_text)
    tag_craft = parser.extract_faction_tag(craft_text)
    words = title_craft.split()
    assert 3 <= len(words) <= 6
    assert tag_craft == "#domain/craft"

    # Health text
    health_text = (
        "Morning workout routine and recovery tracking.\n"
        "Did 45 minutes of cardio and gym training today. Sleep was 8 hours."
    )
    title_health = parser.extract_title(health_text)
    tag_health = parser.extract_faction_tag(health_text)
    assert tag_health == "#domain/health"

    # Leverage text
    leverage_text = (
        "Quarterly business revenue and investor updates.\n"
        "Meeting with prospective client regarding SaaS contract and pricing model."
    )
    tag_leverage = parser.extract_faction_tag(leverage_text)
    assert tag_leverage == "#domain/leverage"

    # Expression text
    expression_text = (
        "Writing YouTube script for next week's release.\n"
        "Creative article about cognitive operating systems and digital art."
    )
    tag_expression = parser.extract_faction_tag(expression_text)
    assert tag_expression == "#domain/expression"


def test_core_proposition_and_entity_extraction():
    """
    SPEC §27.5 line 7213: "3. Core Proposition (1-2 sentences) ... 5. Named Entities (people, tools, concepts)"
    """
    parser = RoughNoteParser()

    raw_text = (
        "Exploring Neo4j graph storage with Obsidian LiveSync.\n"
        "This architectural shift enables instant bidirectional link traversal.\n"
        "Connect with @shivam regarding Python sidecar changes."
    )

    core_prop = parser.extract_core_proposition(raw_text)
    assert "Neo4j" in core_prop or "Obsidian" in core_prop
    assert len(core_prop) > 10

    entities = parser.extract_entities(raw_text)
    assert "Neo4j" in entities
    assert "Obsidian" in entities
    assert "LiveSync" in entities
    assert "@shivam" in entities
    assert "Python" in entities


def test_action_item_extraction():
    """
    SPEC §27.5 line 7214: "4. Extracted Action Items (with checkboxes)"
    """
    parser = RoughNoteParser()

    raw_text = """
Random thoughts on system design:
- [ ] Implement rough note parser endpoint
- [ ] Add integration test suite
TODO: Review weekly faction balance
Remember: send invoice to client
- Review PR on github
"""
    items = parser.extract_action_items(raw_text)
    assert len(items) >= 4
    assert any("rough note parser" in it.lower() for it in items)
    assert any("integration test" in it.lower() for it in items)
    assert any("faction balance" in it.lower() for it in items)
    assert any("send invoice" in it.lower() for it in items)


def test_markdown_rendering_and_frontmatter():
    """
    SPEC §27.5 line 7223: "// Construct Obsidian Markdown note"
    """
    note = RoughNote(
        title="Automated Life System",
        primary_tag="#domain/craft",
        core_proposition="An autonomous multi-agent operating system coordinates daily workflows.",
        action_items=["Verify unit tests", "Deploy FastAPI sidecar"],
        entities=["Obsidian", "FastAPI"],
        raw_text="Brain dump on automated life systems. Need to verify unit tests and deploy FastAPI sidecar.",
        source="telegram",
    )

    md = note.to_markdown()
    assert md.startswith("---")
    assert 'title: "Automated Life System"' in md
    assert 'tags: ["#domain/craft"]' in md
    assert 'entities: ["FastAPI", "Obsidian"]' in md or 'entities: ["Obsidian", "FastAPI"]' in md
    assert "# Automated Life System" in md
    assert "## Summary" in md
    assert "An autonomous multi-agent operating system coordinates daily workflows." in md
    assert "## Action Items" in md
    assert "- [ ] Verify unit tests" in md
    assert "- [ ] Deploy FastAPI sidecar" in md
    assert "## Raw Capture" in md
    assert "> Brain dump on automated life systems." in md


def test_vault_persistence_inbox(tmp_path):
    """
    SPEC §27.5 line 7243: "vault_path = f\"/vault/04-Captures/Inbox/{slugify(structured_json.title)}.md\""
    """
    parser = RoughNoteParser()
    raw = (
        "Refactoring Locus Knowledge Graph Engine.\n"
        "We are integrating graphify MCP server.\n"
        "- [ ] Write unit tests\n"
        "TODO: Update documentation"
    )

    res = parser.parse_rough_note_stream(
        raw_text=raw,
        source="voice_stt",
        save_to_vault=True,
        vault_root=tmp_path,
    )

    assert res.success is True
    assert res.tasks_created >= 2
    assert res.path is not None
    assert Path(res.path).exists()
    assert "04-Captures" in res.path
    assert "Inbox" in res.path

    content = Path(res.path).read_text(encoding="utf-8")
    assert 'source: "voice_stt"' in content
    assert "- [ ] Write unit tests" in content


def test_modular_subsystem_off_switch(monkeypatch):
    """
    SPEC §27.5 line 7203: "Converts raw unstructured brain dumps from Telegram or mobile into structured Obsidian atomic notes"
    """
    parser = RoughNoteParser()
    switch = parser.SWITCH_KEY

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    assert parser.is_enabled() is False

    res = parser.parse_rough_note_stream("Some brain dump")
    assert res.success is False
    assert "disabled" in (res.error or "").lower()


def test_provider_master_off_switch_503(monkeypatch):
    """
    SPEC §27.5 line 7203: "Registers as a provider in sidecar/providers/ with modular off-switch locus.rough_note_parser.enabled returning 503."
    """
    provider = DefaultRoughNoteParserProvider()
    switch = "locus.rough_note_parser.enabled"

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    enabled, sw = provider.is_feature_enabled()
    assert enabled is False
    assert sw == switch

    res_parse = provider.parse_note("Some thought stream")
    assert res_parse.get("status_code") == 503
    assert res_parse.get("disabled") == switch

    res_status = provider.get_status()
    assert res_status.get("status_code") == 503
    assert res_status.get("disabled") == switch


def test_provider_swap_polymorphism():
    """
    SPEC §27.5 line 7203: "Registers as a provider in sidecar/providers/ with modular off-switch locus.rough_note_parser.enabled returning 503."
    """
    class MockRoughNoteParserProvider(BaseRoughNoteParserProvider):
        @property
        def name(self) -> str:
            return "mock_rough_note_parser"

        def is_feature_enabled(self):
            return True, "mock.switch"

        def parse_note(self, raw_text, source=None, save_to_vault=True, vault_root=None):
            return {"status_code": 200, "success": True, "path": "/mock/path.md", "tasks_created": 3}

        def get_status(self):
            return {"status_code": 200, "mock": True}

    provider: BaseRoughNoteParserProvider = MockRoughNoteParserProvider()
    assert provider.name == "mock_rough_note_parser"
    res = provider.parse_note("raw note")
    assert res["status_code"] == 200
    assert res["tasks_created"] == 3
