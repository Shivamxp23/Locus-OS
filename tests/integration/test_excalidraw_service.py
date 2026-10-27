"""
SPEC §27.7 lines 7305-7378: Integration tests for Excalidraw Diagram Generator endpoints (F-0063 / US-100).
Tests FastAPI endpoints under /diagrams/excalidraw/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.display.excalidraw_builder import ExcalidrawDiagramBuilder
from sidecar.providers.excalidraw import DefaultDiagramGeneratorProvider
from sidecar.service import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    builder = ExcalidrawDiagramBuilder()
    provider = DefaultDiagramGeneratorProvider(builder=builder)
    app.state.diagram_generator_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.tools.excalidraw.enabled", True)
    config.set("locus.display.excalidraw.enabled", True)
    yield
    config.set("locus.tools.excalidraw.enabled", True)
    config.set("locus.display.excalidraw.enabled", True)


def test_excalidraw_service_generate_endpoint(client: TestClient, tmp_path: Path) -> None:
    """SPEC §27.7: POST /diagrams/excalidraw/generate."""
    spec = """
    Mobile Client -> Telegram Router
    Telegram Router -> Sidecar FastApi
    Sidecar FastApi -> Vault Synchronizer
    """
    payload = {
        "system_spec": spec,
        "output_filename": "Test Architecture",
        "save_to_vault": True,
        "vault_root": str(tmp_path),
    }
    res = client.post("/diagrams/excalidraw/generate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SAVED"
    assert data["elements_count"] >= 5
    assert data["path"] is not None
    assert Path(data["path"]).exists()
    assert "03-Resources" in data["path"]
    assert "Diagrams" in data["path"]


def test_excalidraw_service_generate_empty_bad_request(client: TestClient) -> None:
    """SPEC §27.7: POST /diagrams/excalidraw/generate with empty spec."""
    payload = {"system_spec": "   "}
    res = client.post("/diagrams/excalidraw/generate", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["status"] == "ERROR"
    assert "empty" in data["error"].lower()


def test_excalidraw_service_status_endpoint(client: TestClient) -> None:
    """SPEC §27.7: GET /diagrams/excalidraw/status."""
    res = client.get("/diagrams/excalidraw/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider_enabled"] is True
    assert data["subsystem_enabled"] is True
    assert data["provider_name"] == "default_diagram_generator"
    assert data["excalidraw_version"] == 2


def test_excalidraw_service_master_off_switch_503(client: TestClient) -> None:
    """SPEC §27.7: Off-switch locus.tools.excalidraw.enabled returns 503."""
    config.set("locus.tools.excalidraw.enabled", False)

    res_gen = client.post("/diagrams/excalidraw/generate", json={"system_spec": "A -> B"})
    assert res_gen.status_code == 503
    assert res_gen.json().get("disabled") == "locus.tools.excalidraw.enabled"

    res_status = client.get("/diagrams/excalidraw/status")
    assert res_status.status_code == 503
    assert res_status.json().get("disabled") == "locus.tools.excalidraw.enabled"
