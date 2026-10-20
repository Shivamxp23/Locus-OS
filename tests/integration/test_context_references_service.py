"""
SPEC §6.2: Dynamic Context References Service Integration Tests (F-0028 / US-59).
Validates FastAPI sidecar endpoints:
  - GET /context/references/config
  - POST /context/references/resolve
  - POST /context/references/format-xml
  - Modular off-switch (HTTP 503) when locus.context_references.enabled is False
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Generator
from unittest.mock import patch

import pytest
from starlette.testclient import TestClient

from sidecar.providers.context_references import DefaultContextReferenceProvider
from sidecar.service import create_app


@pytest.fixture
def client_and_provider(tmp_path: Path) -> Generator[tuple[TestClient, DefaultContextReferenceProvider], None, None]:
    sample = tmp_path / "hello.py"
    sample.write_text("print('hello locus context references')\n", encoding="utf-8")
    provider = DefaultContextReferenceProvider(repo_root=tmp_path)
    app = create_app()
    app.state.registry.register("context_references", "default_context_references", lambda **kw: provider)
    client = TestClient(app)
    yield client, provider


def test_service_context_references_config(client_and_provider: tuple[TestClient, DefaultContextReferenceProvider]) -> None:
    """SPEC §6.2 line 2115: GET /context/references/config returns provider status."""
    client, _ = client_and_provider
    res = client.get("/context/references/config")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["enabled"] is True
    assert data["provider"] == "default_context_references"


def test_service_context_references_resolve(client_and_provider: tuple[TestClient, DefaultContextReferenceProvider]) -> None:
    """SPEC §6.2 lines 2062-2101: POST /context/references/resolve."""
    client, _ = client_and_provider
    res = client.post(
        "/context/references/resolve",
        json={"prompt": "Inspect @file:hello.py for context", "max_budget": 1000},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "[FILE: hello.py]" in data["clean_prompt"]
    assert len(data["references"]) == 1
    assert data["references"][0]["target_path"] == "hello.py"
    assert "print('hello locus context references')" in data["references"][0]["content"]
    assert "<context_ref" in data["xml_enclosure"]


def test_service_context_references_format_xml(client_and_provider: tuple[TestClient, DefaultContextReferenceProvider]) -> None:
    """SPEC §6.2 lines 2104-2110: POST /context/references/format-xml."""
    client, _ = client_and_provider
    refs = [
        {"ref_type": "@file", "target_path": "a.txt", "content": "text content", "token_count": 5, "truncated": False}
    ]
    res = client.post("/context/references/format-xml", json={"references": refs})
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert '<context_ref type="@file" target="a.txt">' in data["xml"]
    assert "text content" in data["xml"]


def test_service_context_references_off_switch_503(client_and_provider: tuple[TestClient, DefaultContextReferenceProvider]) -> None:
    """SPEC §6.2 line 2115: Off-switch returns 503 with disabled config key."""
    client, _ = client_and_provider

    with patch("sidecar.config.get", return_value=False), \
         patch("sidecar.config.is_enabled", return_value=False):
        res1 = client.get("/context/references/config")
        assert res1.status_code == 503
        assert res1.json()["disabled"] == "locus.context_references.enabled"

        res2 = client.post("/context/references/resolve", json={"prompt": "test @file:a.txt"})
        assert res2.status_code == 503

        res3 = client.post("/context/references/format-xml", json={"references": []})
        assert res3.status_code == 503
