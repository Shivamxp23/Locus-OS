"""
SPEC §1.12 / F-0012 / US-31: Unit tests for Onboarding Flow.
Asserts multi-topology setup, configuration steps across cognitive tri-stack,
live diagnostic probes, non-interactive batch setup, and modular off-switch.
"""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from sidecar import config
from sidecar.onboarding import (
    DEFAULT_CRON_SCHEDULES,
    DEFAULT_FACTIONS,
    OnboardingProvider,
    run_non_interactive_setup,
)
from sidecar.providers.onboarding import (
    BaseOnboardingProvider,
    DiagnosticProbeResult,
    OnboardingStepResult,
    TopologyType,
)
from sidecar.registry import get_registry


def test_onboarding_step_and_probe_data_structures():
    """SPEC §1.12 line 2558: "probe_results = run_live_diagnostics(config, get_all_env_secrets())"."""
    probe = DiagnosticProbeResult(
        name="neo4j",
        status="ok",
        latency_ms=12.4,
        message="Graph connected",
        details={"nodes": 1200},
    )
    d = probe.to_dict()
    assert d["name"] == "neo4j"
    assert d["status"] == "ok"
    assert d["latency_ms"] == 12.4
    assert d["details"]["nodes"] == 1200

    step = OnboardingStepResult(
        step="topology",
        status="ok",
        data={"topology": "hybrid"},
        message="Hybrid selected",
    )
    s_dict = step.to_dict()
    assert s_dict["step"] == "topology"
    assert s_dict["data"]["topology"] == "hybrid"


def test_topology_selection_and_defaults():
    """SPEC §1.12 line 2471: "topology = prompt_choice(\"Select Primary Deployment Topology:\", ["."""
    provider = OnboardingProvider()
    provider.reset()

    # Valid topologies
    res_local = provider.set_topology("local")
    assert res_local.status == "ok"
    assert res_local.data["topology"] == "local"
    assert config.get("locus.topology") == "local"

    res_vm = provider.set_topology("vm")
    assert res_vm.status == "ok"
    assert res_vm.data["topology"] == "vm"
    assert config.get("locus.topology") == "vm"

    # Fallback on invalid
    res_invalid = provider.set_topology("unsupported_cloud")
    assert res_invalid.data["topology"] == "local"


def test_step_1_llm_provider_configuration():
    """SPEC §1.12 line 2477: "provider_type = prompt_choice(\"Select Primary LLM Provider:\", ["."""
    provider = OnboardingProvider()

    res = provider.configure_llm(
        provider="ollama",
        model="deepseek-r1:14b",
        endpoint="http://localhost:11434",
        fallback_provider="openrouter",
        fallback_key="sk-test-fallback",
    )
    assert res.status == "ok"
    assert res.data["provider"] == "ollama"
    assert res.data["model"] == "deepseek-r1:14b"
    assert res.data["endpoint"] == "http://localhost:11434"

    llm_cfg = config.get("locus.providers.llm")
    assert llm_cfg["provider"] == "ollama"
    assert llm_cfg["endpoint"] == "http://localhost:11434"

    fb_cfg = config.get("locus.providers.llm_fallback")
    assert fb_cfg["provider"] == "openrouter"
    assert fb_cfg["has_api_key"] is True


def test_step_2_memory_tristack_configuration():
    """SPEC §1.12 line 2498: "enable_neo4j = prompt_yes_no(\"Enable Neo4j Graph Memory (POLE+O Schema & Hebbian reinforcement)?\", default=true)"."""
    provider = OnboardingProvider()

    # Neo4j enabled
    res_neo4j = provider.configure_memory(
        enable_neo4j=True,
        neo4j_uri="neo4j+s://locus-prod.databases.neo4j.io",
        neo4j_user="neo4j",
        neo4j_password="secretpassword",
        enable_headroom=True,
    )
    assert res_neo4j.status == "ok"
    mem_cfg = config.get("locus.providers.memory")
    assert mem_cfg["provider"] == "neo4j-agent-memory"
    assert mem_cfg["has_password"] is True
    assert config.get("locus.providers.compression.enabled") is True

    # SQLite fallback
    res_sqlite = provider.configure_memory(enable_neo4j=False, enable_headroom=False)
    assert res_sqlite.status == "ok"
    mem_cfg_sqlite = config.get("locus.providers.memory")
    assert mem_cfg_sqlite["provider"] == "sqlite-fallback"
    assert config.get("locus.providers.compression.enabled") is False


def test_step_3_vault_and_couchdb_livesync():
    """SPEC §1.12 line 2511: "vault_path = prompt_text(\"Absolute path to local Obsidian Vault:\", default=\"C:/Users/soni8/Documents/Obsidian/LocusVault\")"."""
    provider = OnboardingProvider()

    custom_vault = "C:/Users/soni8/Obsidian/CustomVault"
    res = provider.configure_vault(
        vault_path=custom_vault,
        enable_livesync=True,
        couch_url="https://couchdb.locusapp.online",
        couch_user="locus_admin",
        couch_password="couch_secret_password",
        couch_db="locus_vault",
    )
    assert res.status == "ok"
    assert config.get("locus.vault.path") == custom_vault

    sync_cfg = config.get("locus.providers.vault_sync")
    assert sync_cfg["enabled"] is True
    assert sync_cfg["provider"] == "couchdb-livesync"
    assert sync_cfg["database"] == "locus_vault"
    assert sync_cfg["has_password"] is True


def test_step_4_life_os_and_behavioral_baseline():
    """SPEC §1.12 line 2527: "timezone = prompt_text(\"User Timezone:\", default=\"Asia/Kolkata\")"."""
    provider = OnboardingProvider()

    res = provider.configure_life_os(
        timezone="America/New_York",
        morning_checkin_time="07:30",
        factions=DEFAULT_FACTIONS,
    )
    assert res.status == "ok"
    assert config.get("locus.life_os.timezone") == "America/New_York"
    assert config.get("locus.life_os.morning_checkin_time") == "07:30"
    assert "1_health_stability" in config.get("locus.life_os.factions")


def test_step_5_telegram_ambient_bot():
    """SPEC §1.12 line 2539: "enable_tg = prompt_yes_no(\"Enable Telegram Ambient Bot Interface?\", default=true)"."""
    provider = OnboardingProvider()

    res = provider.configure_telegram(
        enabled=True,
        token="123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
        owner_id="987654321",
    )
    assert res.status == "ok"
    tg_cfg = config.get("locus.providers.channels.telegram")
    assert tg_cfg["enabled"] is True
    assert tg_cfg["owner_id"] == "987654321"
    assert tg_cfg["has_token"] is True


def test_step_6_autonomous_cron_engine():
    """SPEC §1.12 line 2548: "IF topology IN [\"vm\", \"hybrid\"]: config.set(\"locus.cron.enabled\", true)"."""
    provider = OnboardingProvider()

    res = provider.configure_cron(enabled=True, schedules=DEFAULT_CRON_SCHEDULES)
    assert res.status == "ok"
    assert config.get("locus.cron.enabled") is True
    scheds = config.get("locus.cron.schedules")
    assert len(scheds) == 4
    assert any(s["name"] == "nightly_vault_crawl" for s in scheds)


def test_step_7_live_diagnostic_probes():
    """SPEC §1.12 line 2558: "probe_results = run_live_diagnostics(config, get_all_env_secrets())"."""
    provider = OnboardingProvider()
    provider.reset()

    # Before configuration, diagnostics report missing configurations
    diag_before = provider.run_diagnostics()
    assert len(diag_before["probes"]) >= 4

    # Configure subsystems
    provider.set_topology("hybrid")
    provider.configure_llm(provider="anthropic", model="claude-3-5-sonnet")
    provider.configure_memory(enable_neo4j=False)
    provider.configure_vault(vault_path="C:/Vault")
    provider.configure_life_os(timezone="Asia/Kolkata")
    provider.configure_telegram(enabled=False)

    diag_after = provider.run_diagnostics()
    assert diag_after["all_ok"] is True
    assert provider.get_status()["completed"] is True
    assert config.get("locus.onboarding.completed") is True


def test_non_interactive_batch_setup():
    """SPEC §1.12 line 2577: "Terminal Shell (locus setup): locus_cli/setup.py provides an interactive terminal prompt session"."""
    settings = {
        "topology": "vm",
        "llm": {"provider": "deepseek", "model": "deepseek-chat"},
        "memory": {"enable_neo4j": False, "enable_headroom": True},
        "vault": {"path": "/var/locus/vault", "enable_livesync": True, "couch_url": "http://127.0.0.1:5984"},
        "life_os": {"timezone": "UTC", "morning_checkin_time": "08:00"},
        "telegram": {"enabled": False},
    }

    res = run_non_interactive_setup(settings)
    assert res["ok"] is True
    assert res["topology"] == "vm"
    assert res["status"]["completed"] is True


def test_onboarding_provider_lifecycle_and_registry():
    """SPEC §1.12 line 2585: "Swappable / Off-State: locus.onboarding.completed: boolean tracks setup state."."""
    reg = get_registry()
    provider_cls = reg.get("onboarding", "default")
    assert provider_cls is not None
    provider: BaseOnboardingProvider = provider_cls()
    assert isinstance(provider, BaseOnboardingProvider)

    # Provider is registered under alias as well
    alias_cls = reg.get("onboarding_flow", "default")
    assert alias_cls is provider_cls


def test_onboarding_modular_off_switch(monkeypatch):
    """SPEC §1.12 line 2585: "Swappable / Off-State: locus.onboarding.completed: boolean tracks setup state."."""
    provider = OnboardingProvider()
    assert provider.is_enabled() is True

    monkeypatch.setattr(config, "get", lambda k, d=None: False if "onboarding" in k else True)
    assert provider.is_enabled() is False
