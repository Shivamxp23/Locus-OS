"""
SPEC §27.6 lines 7254-7304: Integration tests for Link Dump Logger endpoints (F-0062 / US-99).
Tests FastAPI endpoints under /ingestion/link/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.ingestion.link_logger import LinkDumpLogger
from sidecar.providers.link_logger import DefaultLinkDumpLoggerProvider
from sidecar.service import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    logger_instance = LinkDumpLogger()
    provider = DefaultLinkDumpLoggerProvider(logger_instance=logger_instance)
    app.state.link_dump_logger_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.link_dump_logger.enabled", True)
    config.set("locus.ingestion.link_logger.enabled", True)
    yield
    config.set("locus.link_dump_logger.enabled", True)
    config.set("locus.ingestion.link_logger.enabled", True)


def test_link_logger_service_process_endpoint(client: TestClient, tmp_path: Path) -> None:
    """SPEC §27.6: POST /ingestion/link/process."""
    html_content = """
    <html>
      <head><title>Transformer Scaling Innovations</title></head>
      <body>
        <h1>Multimodal Reasoning Advances</h1>
        <p>State of the art LLM architectures utilize mixture of experts for high inference efficiency.</p>
        <p>Attention heads can be routed dynamically according to task complexity.</p>
        <p>Evaluation on competitive mathematics confirms superior generalization capability.</p>
      </body>
    </html>
    """
    payload = {
        "url": "https://arxiv.org/abs/2402.12345",
        "user_commentary": "Critical architecture for agent reasoning",
        "html_content": html_content,
        "save_to_vault": True,
        "vault_root": str(tmp_path),
    }
    res = client.post("/ingestion/link/process", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SAVED"
    assert len(data["takeaways"]) == 3
    assert data["path"] is not None
    assert Path(data["path"]).exists()
    assert data["resource"]["domain_category"] == "ai_research"


def test_link_logger_service_process_empty_bad_request(client: TestClient) -> None:
    """SPEC §27.6: POST /ingestion/link/process with empty url."""
    payload = {"url": "   "}
    res = client.post("/ingestion/link/process", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["status"] == "ERROR"
    assert "empty" in data["error"].lower()


def test_link_logger_service_status_endpoint(client: TestClient) -> None:
    """SPEC §27.6: GET /ingestion/link/status."""
    res = client.get("/ingestion/link/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider_enabled"] is True
    assert data["subsystem_enabled"] is True
    assert data["provider_name"] == "default_link_dump_logger"
    assert "ai_research" in data["supported_categories"]


def test_link_logger_service_master_off_switch_503(client: TestClient) -> None:
    """SPEC §27.6: Off-switch locus.link_dump_logger.enabled returns 503."""
    config.set("locus.link_dump_logger.enabled", False)

    res_proc = client.post("/ingestion/link/process", json={"url": "https://example.com"})
    assert res_proc.status_code == 503
    assert res_proc.json().get("disabled") == "locus.link_dump_logger.enabled"

    res_status = client.get("/ingestion/link/status")
    assert res_status.status_code == 503
    assert res_status.json().get("disabled") == "locus.link_dump_logger.enabled"
