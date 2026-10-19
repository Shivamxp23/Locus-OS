"""
SPEC §1.2 / §03 line 35: System Prompt Builder Service Integration Tests.
Tests HTTP endpoints on the sidecar service for system prompt construction
and modular 503 off-switch behavior.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from sidecar import config
from sidecar.prompt_builder import DEFAULT_SOUL_PERSONALITY, PromptBuilderProvider
from sidecar.registry import ProviderRegistry
from sidecar.service import create_app


def test_prompt_builder_service_endpoints():
    """SPEC §1.2 line 415: "Prompt builder service endpoints construct prompt and return personality"."""
    registry = ProviderRegistry()
    registry.register("prompt_builder", "default_prompt_builder", PromptBuilderProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # 1. Personality endpoint
    res_pers = client.get("/prompt/personality")
    assert res_pers.status_code == 200
    pers_data = res_pers.json()
    assert pers_data["status"] == "ok"
    assert "You are Locus" in pers_data["personality"]

    # 2. Build endpoint
    res_build = client.post(
        "/prompt/build",
        json={
            "cwd": "C:\\repo\\locus",
            "operating_state": {
                "dcs": 7.2,
                "operating_mode": "DEEP WORK",
                "faction_status": {"Health": 25.0, "Leverage": 25.0, "Craft": 30.0, "Expression": 20.0}
            },
            "context_forge_tokens": "Active goal: complete US-21 prompt builder",
        }
    )
    assert res_build.status_code == 200
    build_data = res_build.json()
    assert build_data["status"] == "ok"
    prompt = build_data["prompt"]
    assert "Current working directory: C:/repo/locus" in prompt
    assert "Active Operating Mode: DEEP WORK" in prompt
    assert "Active goal: complete US-21 prompt builder" in prompt


def test_prompt_builder_off_switch_503(monkeypatch):
    """SPEC §03 line 35: "modular off-switch locus.prompt_builder.enabled returns 503"."""
    registry = ProviderRegistry()
    registry.register("prompt_builder", "default_prompt_builder", PromptBuilderProvider)

    app = create_app(registry=registry)
    client = TestClient(app)

    # Disable prompt builder feature
    monkeypatch.setattr(config, "get", lambda key, default=None: False if "prompt_builder" in key else default)
    monkeypatch.setattr(config, "is_enabled", lambda key: False if "prompt_builder" in key else True)

    res_pers = client.get("/prompt/personality")
    assert res_pers.status_code == 503
    assert res_pers.json() == {"disabled": "locus.prompt_builder.enabled"}

    res_build = client.post("/prompt/build", json={"cwd": "/workspace"})
    assert res_build.status_code == 503
    assert res_build.json() == {"disabled": "locus.prompt_builder.enabled"}
