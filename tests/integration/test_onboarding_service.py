"""
Integration tests for Onboarding Flow FastAPI endpoints (SPEC §1.12 / F-0012 / US-31).
Asserts stepped onboarding configuration, live diagnostic probes, status, reset, and 503 off-switch.
"""
from typing import Any, Dict
import pytest
from fastapi.testclient import TestClient

import sidecar.config as config
from sidecar.service import create_app
from sidecar.onboarding import OnboardingProvider, run_non_interactive_setup
from sidecar.providers.onboarding import (
    BaseOnboardingProvider,
    DiagnosticProbeResult,
    OnboardingStepResult,
    TopologyType,
)


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_onboarding_start_endpoint(client):
    """SPEC §1.12 line 2464: "topology = prompt_choice(\"Select Locus Deployment Topology:\", ["."""
    res = client.post("/onboarding/start", json={"topology": "hybrid"})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["result"]["step"] == "topology"
    assert data["result"]["data"]["topology"] == "hybrid"


def test_onboarding_steps_endpoints(client):
    """SPEC §1.12 line 2486: "provider_type = prompt_choice(\"Select Primary LLM Provider:\", ["."""
    # Step 1: LLM
    res_llm = client.post(
        "/onboarding/step",
        json={
            "step": "llm",
            "payload": {
                "provider": "deepseek",
                "model": "deepseek-chat",
                "api_key": "sk-deepseek-test-key",
            },
        },
    )
    assert res_llm.status_code == 200
    assert res_llm.json()["result"]["step"] == "llm"

    # Step 2: Memory
    res_mem = client.post(
        "/onboarding/step",
        json={
            "step": "memory",
            "payload": {
                "enable_neo4j": True,
                "neo4j_uri": "bolt://localhost:7687",
                "neo4j_user": "neo4j",
                "neo4j_password": "password",
                "enable_headroom": True,
            },
        },
    )
    assert res_mem.status_code == 200
    assert res_mem.json()["result"]["step"] == "memory"

    # Step 3: Vault
    res_vault = client.post(
        "/onboarding/step",
        json={
            "step": "vault",
            "payload": {
                "vault_path": "/var/locus/vault",
                "enable_livesync": True,
                "couch_url": "http://127.0.0.1:5984",
            },
        },
    )
    assert res_vault.status_code == 200
    assert res_vault.json()["result"]["step"] == "vault"

    # Step 4: Life OS
    res_life = client.post(
        "/onboarding/step",
        json={
            "step": "life_os",
            "payload": {
                "timezone": "America/New_York",
                "morning_checkin_time": "07:30",
            },
        },
    )
    assert res_life.status_code == 200
    assert res_life.json()["result"]["step"] == "life_os"

    # Step 5: Telegram
    res_tg = client.post(
        "/onboarding/step",
        json={
            "step": "telegram",
            "payload": {
                "enabled": True,
                "token": "123456:fake-token",
                "owner_id": "999888777",
            },
        },
    )
    assert res_tg.status_code == 200
    assert res_tg.json()["result"]["step"] == "telegram"

    # Step 6: Cron
    res_cron = client.post(
        "/onboarding/step",
        json={
            "step": "cron",
            "payload": {
                "enabled": True,
            },
        },
    )
    assert res_cron.status_code == 200
    assert res_cron.json()["result"]["step"] == "cron"


def test_onboarding_diagnostics_endpoint(client):
    """SPEC §1.12 line 2584: "probe_results = run_live_diagnostics(config, get_all_env_secrets())"."""
    res = client.post("/onboarding/diagnostics", json={"probes": ["llm", "memory", "vault"]})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "diagnostics" in data
    assert "summary" in data["diagnostics"]
    assert "probes" in data["diagnostics"]


def test_onboarding_status_and_reset_endpoints(client):
    """SPEC §1.12 line 2608: "locus.onboarding.completed: boolean tracks setup state. Re-running locus setup --reconfigure allows editing any single section without erasing the others."."""
    status_res = client.get("/onboarding/status")
    assert status_res.status_code == 200
    st_data = status_res.json()
    assert st_data["status"] == "ok"
    assert "onboarding" in st_data
    assert "topology" in st_data["onboarding"]

    reset_res = client.post("/onboarding/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["status"] == "ok"


def test_onboarding_invalid_step(client):
    """SPEC §1.12 line 2603: "Strict Modularity Contract: Every subsystem implements enabled: boolean, provider: string, and options: object."."""
    res = client.post("/onboarding/step", json={"step": "non_existent_step"})
    assert res.status_code == 400


def test_onboarding_503_off_switch(client, monkeypatch):
    """SPEC §1.12 line 2608: "Swappable / Off-State: locus.onboarding.completed: boolean tracks setup state."."""
    monkeypatch.setattr(config, "get", lambda k, d=None: False if "onboarding" in k else True)

    res_start = client.post("/onboarding/start", json={"topology": "local"})
    assert res_start.status_code == 503
    assert res_start.json()["disabled"] == "locus.onboarding_flow.enabled"

    res_step = client.post("/onboarding/step", json={"step": "llm", "payload": {}})
    assert res_step.status_code == 503

    res_diag = client.post("/onboarding/diagnostics", json={})
    assert res_diag.status_code == 503

    res_status = client.get("/onboarding/status")
    assert res_status.status_code == 503

    res_reset = client.post("/onboarding/reset")
    assert res_reset.status_code == 503
