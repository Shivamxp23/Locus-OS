"""
SPEC §9.2 lines 6000-6056: Unit tests for Skill System & Multi-Source Marketplace (F-0119 / US-63).
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict
import pytest

from sidecar.providers.skill_marketplace import (
    BaseSkillMarketplaceProvider,
    DefaultSkillMarketplaceProvider,
)
from sidecar.skills.marketplace import (
    INDEX_URLS,
    SkillManifest,
    SkillMarketplaceEngine,
)


def test_skill_manifest_data_structure() -> None:
    """SPEC §9.2 lines 6014-6022: "DATA STRUCTURES: SkillManifest: name: string, description: string, version: string, author: string, repository_url: string, dependencies: List[string], env_vars_required: List[string]" """
    manifest = SkillManifest(
        name="web-scraper",
        description="Extract tabular data from webpages",
        version="1.2.0",
        author="alice",
        repository_url="https://github.com/alice/web-scraper",
        dependencies=["beautifulsoup4", "requests"],
        env_vars_required=["SCRAPER_API_KEY"],
        bundle_url="https://gallery.pi.dev/api/v1/skills/web-scraper/bundle.zip",
    )
    data = manifest.to_dict()
    assert data["name"] == "web-scraper"
    assert data["version"] == "1.2.0"
    assert data["dependencies"] == ["beautifulsoup4", "requests"]
    assert data["env_vars_required"] == ["SCRAPER_API_KEY"]

    restored = SkillManifest.from_dict(data)
    assert restored.name == manifest.name
    assert restored.author == manifest.author
    assert restored.bundle_url == manifest.bundle_url


def test_skill_marketplace_index_urls() -> None:
    """SPEC §9.2 lines 6025-6031: "INDEX_URLS = { 'pi-gallery': ..., 'anthropic': ..., 'claude-skills': ..., 'openai': ..., 'lobehub': ... }" """
    engine = SkillMarketplaceEngine()
    sources = list(INDEX_URLS.keys())
    assert "pi-gallery" in sources
    assert "anthropic" in sources
    assert "claude-skills" in sources
    assert "openai" in sources
    assert "lobehub" in sources

    for src in sources:
        url = engine.get_index_url(src)
        assert url.startswith("http")


def test_skill_marketplace_build_manifest_url_and_fetch() -> None:
    """SPEC §9.2 line 6033: "target_url = INDEX_URLS[source] + skill_name + '/manifest.json'" """
    engine = SkillMarketplaceEngine()
    url = engine.build_manifest_url("pi-gallery", "arxiv-search")
    assert url == "https://gallery.pi.dev/api/v1/skills/arxiv-search/manifest.json"

    # Fetch manifest (synthetic fallback in test env)
    manifest = engine.fetch_manifest("anthropic", "code-reviewer")
    assert manifest.name == "code-reviewer"
    assert "anthropic" in manifest.author or "anthropic" in manifest.description


def test_skill_marketplace_prerequisites_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §9.2 lines 6036-6039: "FOR EACH env_var IN manifest.env_vars_required: IF env_var NOT IN env: PROMPT_USER" """
    engine = SkillMarketplaceEngine()
    manifest = SkillManifest(
        name="crypto-trader",
        env_vars_required=["BINANCE_KEY", "BINANCE_SECRET"],
    )

    # When variables are missing
    res1 = engine.validate_prerequisites(manifest)
    assert res1["valid"] is False
    assert "BINANCE_KEY" in res1["missing_env_vars"]
    assert "BINANCE_SECRET" in res1["missing_env_vars"]

    # When variables are set
    monkeypatch.setenv("BINANCE_KEY", "test_key_123")
    monkeypatch.setenv("BINANCE_SECRET", "test_sec_456")
    res2 = engine.validate_prerequisites(manifest)
    assert res2["valid"] is True
    assert len(res2["missing_env_vars"]) == 0


def test_skill_marketplace_install_and_list(tmp_path: Path) -> None:
    """SPEC §9.2 lines 6041-6047: "install_dir = f'~/.locus/skills/{skill_name}/'; download_and_extract_bundle(manifest.bundle_url, install_dir)" """
    skills_dir = tmp_path / "skills"
    engine = SkillMarketplaceEngine(skills_dir=skills_dir)

    manifest = SkillManifest(
        name="weather-forecast",
        description="Local weather updates",
        version="2.0.0",
        author="bob",
        env_vars_required=[],
    )

    success = engine.install_skill_from_marketplace(
        source="pi-gallery",
        skill_name="weather-forecast",
        manifest_override=manifest,
    )
    assert success is True

    installed_dir = skills_dir / "weather-forecast"
    assert installed_dir.is_dir()
    assert (installed_dir / "manifest.json").is_file()
    assert (installed_dir / "SKILL.md").is_file()

    installed = engine.list_installed_skills()
    assert len(installed) == 1
    assert installed[0]["name"] == "weather-forecast"


def test_skill_marketplace_provider_off_switch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SPEC §9.2 line 6055: "Swappable / off state: locus.skill_system_multi_source_marketplace.enabled" """
    skills_dir = tmp_path / "skills"
    engine = SkillMarketplaceEngine(skills_dir=skills_dir)
    provider = DefaultSkillMarketplaceProvider(engine=engine)
    assert provider.is_available() is True

    # Check sources and manifest work when enabled
    assert "pi-gallery" in provider.get_sources()
    manifest_data = provider.get_manifest("pi-gallery", "test-skill")
    assert manifest_data["name"] == "test-skill"

    # Off-switch: locus.skill_system_multi_source_marketplace.enabled = False
    monkeypatch.setattr(
        "sidecar.config.get",
        lambda key, default=None: False if key == "locus.skill_system_multi_source_marketplace.enabled" else default,
    )
    assert provider.is_available() is False

    with pytest.raises(RuntimeError, match="disabled"):
        provider.get_sources()

    with pytest.raises(RuntimeError, match="disabled"):
        provider.get_manifest("pi-gallery", "test-skill")

    with pytest.raises(RuntimeError, match="disabled"):
        provider.install_skill("pi-gallery", "test-skill")
