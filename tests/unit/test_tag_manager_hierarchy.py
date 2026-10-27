"""
Unit tests for 3-Level Tag Hierarchy & Semantic Indexing (F-0123 / US-97).
"""
import pytest
from typing import Any, Dict, List, Optional, Tuple

from sidecar import config
from sidecar.vault.tag_manager import (
    DEFAULT_CATEGORY_TO_DOMAIN,
    VALID_DOMAINS,
    TagIndexRecord,
    TagManager,
    TagValidationResult,
    lookup_domain_for_category,
    validate_and_normalize_tags,
)
from sidecar.providers.tag_manager import (
    BaseTagHierarchyProvider,
    DefaultTagHierarchyProvider,
)


def test_bare_tag_auto_resolution_to_domain():
    """
    SPEC §27.4 line 7170: "Auto-resolve bare tag to domain hierarchy: domain = lookup_domain_for_category(parts[0])"
    """
    manager = TagManager()

    raw_tags = ["#coding", "#exercise", "#business", "#youtube"]
    normalized = manager.normalize(raw_tags)

    assert "#craft/coding" in normalized
    assert "#health/exercise" in normalized
    assert "#leverage/business" in normalized
    assert "#expression/youtube" in normalized


def test_two_level_and_three_level_tag_normalization():
    """
    SPEC §27.4 line 7156: "Enforces strict 3-level domain/category/instance tag taxonomy across vault notes"
    """
    manager = TagManager()

    tags = [
        "#craft/coding",
        "#craft/coding/locus-os",
        "#health/sleep/recovery",
        "#expression/art/cinematography",
    ]
    normalized = manager.normalize(tags)

    assert "#craft/coding" in normalized
    assert "#craft/coding/locus-os" in normalized
    assert "#health/sleep/recovery" in normalized
    assert "#expression/art/cinematography" in normalized


def test_single_tag_validation_and_level_parsing():
    """
    SPEC §27.4 line 7160: "Level 1: Domain (#domain/health, #domain/craft, #domain/leverage, #domain/expression)"
    """
    manager = TagManager()

    # Level 1: Domain
    v1 = manager.validate_tag("#health")
    assert v1.is_valid is True
    assert v1.level == 1
    assert v1.domain == "health"
    assert v1.category is None

    # Level 2: Domain/Category
    v2 = manager.validate_tag("#craft/coding")
    assert v2.is_valid is True
    assert v2.level == 2
    assert v2.domain == "craft"
    assert v2.category == "coding"
    assert v2.instance is None

    # Level 3: Domain/Category/Instance
    v3 = manager.validate_tag("#leverage/investing/crypto")
    assert v3.is_valid is True
    assert v3.level == 3
    assert v3.domain == "leverage"
    assert v3.category == "investing"
    assert v3.instance == "crypto"


def test_note_tag_indexing_and_domain_distribution():
    """
    SPEC §27.4 line 7156: "Enforces strict 3-level domain/category/instance tag taxonomy across vault notes"
    """
    manager = TagManager()

    tags = ["#coding", "#typescript", "#workout", "#content"]
    rec = manager.index_note("02_PROJECTS/CRAFT/Locus.md", tags)

    assert rec.note_path == "02_PROJECTS/CRAFT/Locus.md"
    assert len(rec.normalized_tags) == 4
    # Coding and typescript are craft -> 2
    assert rec.domain_distribution["craft"] == 2
    # Workout is health -> 1
    assert rec.domain_distribution["health"] == 1
    # Content is expression -> 1
    assert rec.domain_distribution["expression"] == 1
    # Leverage -> 0
    assert rec.domain_distribution["leverage"] == 0


def test_custom_category_domain_registration():
    """
    SPEC §27.4 line 7170: "Auto-resolve bare tag to domain hierarchy: domain = lookup_domain_for_category(parts[0])"
    """
    manager = TagManager()
    manager.register_category_domain("neuroscience", "craft")

    norm = manager.normalize(["#neuroscience"])
    assert norm == ["#craft/neuroscience"]


def test_modular_subsystem_off_switch(monkeypatch):
    """
    SPEC §27.4 line 7156: "Enforces strict 3-level domain/category/instance tag taxonomy across vault notes"
    """
    manager = TagManager()
    switch = manager.SWITCH_KEY

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    assert manager.is_tag_manager_enabled() is False

    raw = ["#bare_tag", "#coding"]
    assert manager.normalize(raw) == raw


def test_provider_master_off_switch_503(monkeypatch):
    """
    SPEC §27.4 line 7156: "Registers as a provider in sidecar/providers/ with modular off-switch locus.3_level_tag_hierarchy_semantic_indexing.enabled returning 503."
    """
    provider = DefaultTagHierarchyProvider()
    switch = "locus.3_level_tag_hierarchy_semantic_indexing.enabled"

    monkeypatch.setattr(config, "get", lambda key: "false" if key == switch else None)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if key == switch else True)

    enabled, sw = provider.is_feature_enabled()
    assert enabled is False
    assert sw == switch

    res_norm = provider.normalize_tags(["#coding"])
    assert res_norm.get("status_code") == 503

    res_val = provider.validate_tag("#coding")
    assert res_val.get("status_code") == 503

    res_idx = provider.index_note("note.md", ["#coding"])
    assert res_idx.get("status_code") == 503

    res_st = provider.get_status()
    assert res_st.get("status_code") == 503


def test_provider_swap_polymorphism():
    """
    SPEC §27.4 line 7156: "Registers as a provider in sidecar/providers/ with modular off-switch locus.3_level_tag_hierarchy_semantic_indexing.enabled returning 503."
    """
    class MockCustomTagProvider(BaseTagHierarchyProvider):
        @property
        def name(self) -> str:
            return "mock_tag_provider"

        def is_feature_enabled(self) -> Tuple[bool, str]:
            return True, ""

        def normalize_tags(self, tags: List[str]) -> Dict[str, Any]:
            return {"mock": True, "tags": tags}

        def validate_tag(self, tag: str) -> Dict[str, Any]:
            return {"mock": True, "tag": tag}

        def index_note(self, note_path: str, tags: List[str]) -> Dict[str, Any]:
            return {"mock": True, "note_path": note_path}

        def get_status(self) -> Dict[str, Any]:
            return {"mock": True, "name": self.name}

    prov: BaseTagHierarchyProvider = MockCustomTagProvider()
    assert prov.name == "mock_tag_provider"
    assert prov.normalize_tags(["#a"])["mock"] is True
    assert prov.validate_tag("#a")["mock"] is True
