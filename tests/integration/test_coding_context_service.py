"""
SPEC §6.3: Coding Context Engine Service Integration Tests (F-0029 / US-60).
Validates FastAPI sidecar endpoints:
  - GET /context/coding/config
  - POST /context/coding/state
  - POST /context/coding/format
  - Modular off-switch (HTTP 503) when locus.coding_context.enabled is False
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.context.coding_context import WorkspaceCodingState
from sidecar.providers.coding_context import DefaultCodingContextProvider
from sidecar.service import create_app


@pytest.fixture
def client_and_provider(tmp_path: Path) -> Generator[tuple[TestClient, DefaultCodingContextProvider], None, None]:
    sample = tmp_path / "app.py"
    sample.write_text("class Application:\n    def run(self): pass\n", encoding="utf-8")
    provider = DefaultCodingContextProvider(repo_root=tmp_path)
    app = create_app()
    app.state.registry.register("coding_context", "default_coding_context", lambda **kw: provider)
    client = TestClient(app)
    yield client, provider


def test_service_coding_context_config(client_and_provider: tuple[TestClient, DefaultCodingContextProvider]) -> None:
    """SPEC §6.3 line 2187: GET /context/coding/config returns provider status."""
    client, _ = client_and_provider
    res = client.get("/context/coding/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "default_coding_context"


def test_service_coding_context_state_and_format(client_and_provider: tuple[TestClient, DefaultCodingContextProvider]) -> None:
    """SPEC §6.3 lines 2146-2182: POST /context/coding/state and POST /context/coding/format."""
    client, _ = client_and_provider

    # 1. Get state
    res_state = client.post("/context/coding/state", json={"token_budget": 400})
    assert res_state.status_code == 200
    sdata = res_state.json()
    assert sdata["status"] == "ok"
    state = sdata["state"]
    assert "app.py:" in state["repo_map_snippet"]
    assert "class Application" in state["repo_map_snippet"]

    # 2. Format state into layer
    res_format = client.post("/context/coding/format", json={"state": state})
    assert res_format.status_code == 200
    fdata = res_format.json()
    assert fdata["status"] == "ok"
    layer = fdata["formatted_layer"]
    assert "[CODING CONTEXT]" in layer
    assert "Repo Map:" in layer


def test_service_coding_context_off_switch_503(client_and_provider: tuple[TestClient, DefaultCodingContextProvider]) -> None:
    """SPEC §6.3 line 2187: Off-switch returns 503 with disabled config key."""
    client, _ = client_and_provider

    with patch("sidecar.config.get", return_value=False), \
         patch("sidecar.config.is_enabled", return_value=False):
        res1 = client.get("/context/coding/config")
        assert res1.status_code == 503
        assert res1.json()["disabled"] == "locus.coding_context.enabled"

        res2 = client.post("/context/coding/state", json={})
        assert res2.status_code == 503

        res3 = client.post("/context/coding/format", json={"state": {}})
        assert res3.status_code == 503
