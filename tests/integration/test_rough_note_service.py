"""
SPEC §27.5 lines 7192-7251: Integration tests for Rough Note Parser endpoints (F-0061 / US-98).
Tests FastAPI endpoints under /ingestion/rough-note/ and modular off-switches returning HTTP 503.
"""
from __future__ import annotations

from pathlib import Path
import pytest
from starlette.testclient import TestClient

import sidecar.config as config
from sidecar.ingestion.rough_note_parser import RoughNoteParser
from sidecar.providers.rough_note_parser import DefaultRoughNoteParserProvider
from sidecar.service import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app = create_app()
    parser = RoughNoteParser()
    provider = DefaultRoughNoteParserProvider(parser=parser)
    app.state.rough_note_parser_provider = provider
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_config():
    config.set("locus.rough_note_parser.enabled", True)
    config.set("locus.ingestion.rough_note_parser.enabled", True)
    yield
    config.set("locus.rough_note_parser.enabled", True)
    config.set("locus.ingestion.rough_note_parser.enabled", True)


def test_rough_note_service_parse_endpoint(client: TestClient, tmp_path: Path) -> None:
    """SPEC §27.5: POST /ingestion/rough-note/parse."""
    raw_text = (
        "Brain dump regarding Telegram bot router architecture.\n"
        "Need to connect with @shivam on the new Docker deployment.\n"
        "- [ ] Test end-to-end ingestion flow\n"
        "- [ ] Verify webhook resilience"
    )
    payload = {
        "raw_text": raw_text,
        "source": "telegram",
        "save_to_vault": True,
        "vault_root": str(tmp_path),
    }
    res = client.post("/ingestion/rough-note/parse", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["tasks_created"] >= 2
    assert data["path"] is not None
    assert Path(data["path"]).exists()
    assert data["note"]["title"] != ""
    assert data["note"]["primary_tag"] == "#domain/craft"


def test_rough_note_service_parse_empty_bad_request(client: TestClient) -> None:
    """SPEC §27.5: POST /ingestion/rough-note/parse with empty text."""
    payload = {"raw_text": "   "}
    res = client.post("/ingestion/rough-note/parse", json=payload)
    assert res.status_code == 400
    data = res.json()
    assert data["success"] is False
    assert "empty" in data["error"].lower()


def test_rough_note_service_status_endpoint(client: TestClient) -> None:
    """SPEC §27.5: GET /ingestion/rough-note/status."""
    res = client.get("/ingestion/rough-note/status")
    assert res.status_code == 200
    data = res.json()
    assert data["provider_enabled"] is True
    assert data["subsystem_enabled"] is True
    assert data["provider_name"] == "default_rough_note_parser"
    assert "craft" in data["faction_categories"]


def test_rough_note_service_master_off_switch_503(client: TestClient) -> None:
    """SPEC §27.5: Off-switch locus.rough_note_parser.enabled returns 503."""
    config.set("locus.rough_note_parser.enabled", False)

    res_parse = client.post("/ingestion/rough-note/parse", json={"raw_text": "Sample text"})
    assert res_parse.status_code == 503
    assert res_parse.json().get("disabled") == "locus.rough_note_parser.enabled"

    res_status = client.get("/ingestion/rough-note/status")
    assert res_status.status_code == 503
    assert res_status.json().get("disabled") == "locus.rough_note_parser.enabled"
